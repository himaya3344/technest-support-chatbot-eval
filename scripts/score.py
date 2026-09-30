"""Score raw evaluation results with rules and an LLM judge."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

from dotenv import load_dotenv
import yaml

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")
if str(ROOT) not in sys.path:
	sys.path.insert(0, str(ROOT))

from src.llm_client import get_client
from src.scorers.judge import judge_result, load_judge_rubric
from src.schemas import RawResult, TestCase


def load_settings(path: Path) -> SimpleNamespace:
	"""Load YAML settings into an attribute-accessible object."""
	with path.open(encoding="utf-8") as file:
		values = yaml.safe_load(file) or {}
	if not isinstance(values, dict):
		raise ValueError("config.yaml must contain a mapping.")
	return SimpleNamespace(**values)


def newest_raw_file(raw_dir: Path) -> Path:
	"""Return the newest raw JSONL file."""
	files = sorted(raw_dir.glob("run_*.jsonl"), key=lambda path: path.stat().st_mtime)
	if not files:
		raise FileNotFoundError(f"No raw JSONL files found in {raw_dir}.")
	return files[-1]


def load_raw_results(path: Path) -> list[RawResult]:
	"""Load raw result records from JSONL."""
	with path.open(encoding="utf-8") as file:
		return [RawResult.model_validate(json.loads(line)) for line in file if line.strip()]


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
	"""Write scored records as a flat CSV file."""
	path.parent.mkdir(parents=True, exist_ok=True)
	fieldnames = sorted({key for row in rows for key in row})
	with path.open("w", newline="", encoding="utf-8") as file:
		writer = csv.DictWriter(file, fieldnames=fieldnames)
		writer.writeheader()
		writer.writerows(rows)


def parse_args() -> argparse.Namespace:
	"""Parse scoring CLI options."""
	parser = argparse.ArgumentParser(description="Score TechNest raw evaluation results.")
	parser.add_argument("--config", type=Path, default=ROOT / "config.yaml")
	parser.add_argument("--input", type=Path, help="Raw JSONL file; defaults to the newest run.")
	return parser.parse_args()


def main() -> int:
	"""Score raw results and write a timestamped CSV."""
	args = parse_args()
	settings = load_settings(args.config)
	data_dir = ROOT / getattr(settings, "data_path", "data")
	results_dir = ROOT / getattr(settings, "results_path", "results")
	raw_path = args.input or newest_raw_file(results_dir / "raw")
	with (data_dir / "test_cases.json").open(encoding="utf-8") as file:
		cases = {case.id: case for case in (TestCase.model_validate(item) for item in json.load(file))}
	knowledge_base = (data_dir / "knowledge_base.md").read_text(encoding="utf-8")
	rubric = load_judge_rubric(data_dir / "judge_rubric.md")
	judge_values = vars(settings).copy()
	judge_values["model"] = getattr(settings, "judge_model")
	judge_values["temperature"] = 0
	judge_settings = SimpleNamespace(**judge_values)
	judge_client = get_client(judge_settings)
	judge_run_index_only = getattr(settings, "judge_run_index_only", True)
	rows: list[dict[str, object]] = []
	for raw in load_raw_results(raw_path):
		case = cases.get(raw.case_id)
		if case is None:
			continue
		if judge_run_index_only and raw.run_index != 0:
			from src.scorers.rule_scorer import score_result
			scored = score_result(raw, case)
		else:
			scored = judge_result(raw, case, judge_client, knowledge_base, rubric)
		row = scored.model_dump()
		row["parsed_output"] = json.dumps(row["parsed_output"], ensure_ascii=False) if row["parsed_output"] else ""
		row["must_include_hits"] = json.dumps(row["must_include_hits"])
		row["must_not_include_violations"] = json.dumps(row["must_not_include_violations"])
		rows.append(row)

	stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
	output = results_dir / "scored" / f"scored_{stamp}.csv"
	write_csv(output, rows)
	print(f"Scored {len(rows)} results: {output}")
	return 0


if __name__ == "__main__":
	raise SystemExit(main())