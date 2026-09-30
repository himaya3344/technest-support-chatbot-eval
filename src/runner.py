"""Run chatbot evaluation cases and persist raw results as JSONL."""

from __future__ import annotations

import json
import time
from collections.abc import Iterable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from tqdm import tqdm

from src.chatbot import TechNestChatbot
from src.schemas import RawResult, TestCase


def load_test_cases(path: Path) -> list[TestCase]:
	"""Load and validate test cases from a JSON list."""
	with path.open(encoding="utf-8") as file:
		data = json.load(file)
	if not isinstance(data, list):
		raise ValueError("Test cases must be a JSON list.")
	return [TestCase.model_validate(item) for item in data]


def load_completed_pairs(path: Path) -> set[tuple[str, int]]:
	"""Read completed case/run pairs from an existing JSONL file."""
	completed: set[tuple[str, int]] = set()
	if not path.exists():
		return completed
	with path.open(encoding="utf-8") as file:
		for line_number, line in enumerate(file, start=1):
			if not line.strip():
				continue
			try:
				result = json.loads(line)
				completed.add((str(result["case_id"]), int(result["run_index"])))
			except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
				raise ValueError(f"Invalid JSONL record at line {line_number} in {path}.") from exc
	return completed


def _setting(settings: Any, name: str, default: Any = None) -> Any:
	"""Read a setting from either a model-like object or a mapping."""
	if isinstance(settings, dict):
		return settings.get(name, default)
	return getattr(settings, name, default)


def _path_setting(settings: Any, name: str, default: str) -> str:
	"""Read a path from flat settings or an optional nested paths mapping."""
	value = _setting(settings, name, None)
	if value is not None:
		return str(value)
	paths = _setting(settings, "paths", {})
	if isinstance(paths, dict):
		return str(paths.get(name.removesuffix("_path"), default))
	return default


def output_path(results_dir: Path, timestamp: datetime | None = None) -> Path:
	"""Build a UTC-stamped raw result filename."""
	stamp = (timestamp or datetime.now(timezone.utc)).strftime("%Y%m%d_%H%M%S")
	return results_dir / f"run_{stamp}.jsonl"


def _raw_result(case: TestCase, run_index: int, chatbot: TechNestChatbot) -> RawResult:
	"""Execute one case and convert success or failure into a RawResult."""
	started = time.perf_counter()
	try:
		parsed, json_valid, response = chatbot.complete(case)
		return RawResult(
			case_id=case.id,
			run_index=run_index,
			raw_text=response.text,
			parsed_output=parsed,
			json_valid=json_valid,
			latency_s=response.latency_s,
			input_tokens=response.input_tokens,
			output_tokens=response.output_tokens,
			error=None,
		)
	except Exception as exc:  # API errors must not stop the remaining evaluation.
		return RawResult(
			case_id=case.id,
			run_index=run_index,
			raw_text="",
			parsed_output=None,
			json_valid=False,
			latency_s=time.perf_counter() - started,
			input_tokens=None,
			output_tokens=None,
			error=f"{type(exc).__name__}: {exc}",
		)


def run_evaluation(
	settings: Any,
	client: Any,
	output_file: Path | None = None,
	resume_file: Path | None = None,
	limit: int | None = None,
	category: str | None = None,
) -> tuple[Path, list[RawResult]]:
	"""Run selected cases, append results, and return the output path and results."""
	root = Path(__file__).resolve().parents[1]
	data_path = root / _path_setting(settings, "data_path", "data") / "test_cases.json"
	results_dir = root / _path_setting(settings, "results_path", "results") / "raw"
	results_dir.mkdir(parents=True, exist_ok=True)
	output_file = output_file or resume_file or output_path(results_dir)
	output_file.parent.mkdir(parents=True, exist_ok=True)
	completed = load_completed_pairs(resume_file) if resume_file else set()

	cases = load_test_cases(data_path)
	if category:
		cases = [case for case in cases if case.category == category]
	if limit is not None:
		cases = cases[:limit]

	chatbot = TechNestChatbot(client)
	runs = max(0, int(_setting(settings, "runs_per_case", 1)))
	delay = max(0.0, float(_setting(settings, "sleep_between_calls_s", 0.0)))
	results: list[RawResult] = []
	with output_file.open("a", encoding="utf-8") as file:
		for case in tqdm(cases, desc="Evaluating cases", unit="case"):
			for run_index in range(runs):
				if (case.id, run_index) in completed:
					continue
				result = _raw_result(case, run_index, chatbot)
				file.write(result.model_dump_json() + "\n")
				file.flush()
				results.append(result)
				if delay:
					time.sleep(delay)

	print_statistics(results, settings)
	return output_file, results


def print_statistics(results: Iterable[RawResult], settings: Any) -> None:
	"""Print cost and latency totals for the records written in this run."""
	items = list(results)
	latencies = [result.latency_s for result in items]
	input_tokens = sum(result.input_tokens or 0 for result in items)
	output_tokens = sum(result.output_tokens or 0 for result in items)
	input_rate = float(_setting(settings, "input_cost_per_1k_tokens", 0.0))
	output_rate = float(_setting(settings, "output_cost_per_1k_tokens", 0.0))
	cost = input_tokens / 1000 * input_rate + output_tokens / 1000 * output_rate
	mean_latency = sum(latencies) / len(latencies) if latencies else 0.0
	print(f"Total cost: ${cost:.6f}")
	print(f"Latency: total={sum(latencies):.3f}s mean={mean_latency:.3f}s calls={len(items)}")
