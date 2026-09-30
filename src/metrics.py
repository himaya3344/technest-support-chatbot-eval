"""Metric computation for scored TechNest evaluation results."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.metrics import cohen_kappa_score, confusion_matrix, precision_recall_fscore_support


ACTIONS = ["answer", "clarify", "escalate", "refuse"]


def _bool_series(values: pd.Series) -> pd.Series:
	"""Convert CSV booleans and native booleans to nullable booleans."""
	def convert(value: Any) -> bool | float:
		if pd.isna(value):
			return np.nan
		if isinstance(value, bool):
			return value
		return str(value).strip().lower() == "true"

	return values.map(convert)


def _mean(values: pd.Series) -> float | None:
	"""Return a JSON-safe mean, or None when no values are available."""
	numeric = pd.to_numeric(values, errors="coerce").dropna()
	return float(numeric.mean()) if not numeric.empty else None


def _action_values(frame: pd.DataFrame) -> pd.Series:
	"""Extract chatbot actions from an action column or serialized parsed output."""
	if "action" in frame:
		return frame["action"].astype("string")
	if "parsed_output" in frame:
		return frame["parsed_output"].map(_parse_action).astype("string")
	return pd.Series(pd.NA, index=frame.index, dtype="string")


def _parse_action(value: Any) -> str | None:
	"""Extract an action from a serialized or dictionary chatbot output."""
	if isinstance(value, dict):
		return value.get("action")
	if not isinstance(value, str) or not value.strip():
		return None
	try:
		payload = json.loads(value)
		return payload.get("action") if isinstance(payload, dict) else None
	except json.JSONDecodeError:
		return None


def _bootstrap_accuracy(values: pd.Series, seed: int = 42, samples: int = 2000) -> dict[str, float] | None:
	"""Compute a percentile bootstrap 95% CI for binary accuracy values."""
	clean = pd.to_numeric(values, errors="coerce").dropna().to_numpy(dtype=float)
	if clean.size == 0:
		return None
	rng = np.random.default_rng(seed)
	bootstraps = rng.choice(clean, size=(samples, clean.size), replace=True).mean(axis=1)
	return {
		"lower": float(np.percentile(bootstraps, 2.5)),
		"upper": float(np.percentile(bootstraps, 97.5)),
	}


def _category_metrics(frame: pd.DataFrame) -> pd.DataFrame:
	"""Build accuracy and judge summaries by category."""
	rows: list[dict[str, Any]] = []
	for category, group in frame.groupby("category", dropna=False):
		rows.append(
			{
				"category": category,
				"action_accuracy": _mean(group["action_correct"]),
				"must_include_pass_rate": _mean(group["must_include_passed"]),
				"must_not_include_violation_rate": _mean(group["must_not_include_violation"]),
				"hallucination_rate": _mean(group["hallucination"]),
				"mean_judge_score": _mean(group["judge_score"]),
			}
		)
	return pd.DataFrame(rows)


def _human_agreement(frame: pd.DataFrame, human_labels: pd.DataFrame | None) -> dict[str, Any]:
	"""Calculate agreement when human and judge label columns are available."""
	if human_labels is None or human_labels.empty or "case_id" not in human_labels:
		return {"cohens_kappa": None, "percent_agreement": None, "available": False}
	human_column = next((column for column in ("human_label", "human_action", "label") if column in human_labels), None)
	judge_column = next((column for column in ("judge_label", "judge_action") if column in human_labels), None)
	if human_column is None or judge_column is None:
		return {"cohens_kappa": None, "percent_agreement": None, "available": False}
	merged = frame.merge(human_labels[["case_id", human_column, judge_column]], on="case_id", how="inner")
	merged = merged.dropna(subset=[human_column, judge_column])
	if merged.empty:
		return {"cohens_kappa": None, "percent_agreement": None, "available": False}
	agreement = merged[human_column].astype(str) == merged[judge_column].astype(str)
	return {
		"cohens_kappa": float(cohen_kappa_score(merged[human_column], merged[judge_column])),
		"percent_agreement": float(agreement.mean()),
		"available": True,
		"n": int(len(merged)),
	}


def compute_metrics(
	data: pd.DataFrame,
	human_labels: pd.DataFrame | None = None,
	seed: int = 42,
) -> tuple[dict[str, Any], dict[str, pd.DataFrame]]:
	"""Compute requested metrics and tabular breakdowns from scored data."""
	frame = data.copy()
	frame["action"] = _action_values(frame)
	for column in (
		"action_correct",
		"must_include_passed",
		"must_not_include_violation",
		"json_valid",
		"hallucination",
		"injection_success",
	):
		if column in frame:
			frame[column] = _bool_series(frame[column]).astype(float)
	for column in ("must_include_passed", "must_not_include_violation", "json_valid", "hallucination", "injection_success"):
		if column not in frame:
			frame[column] = np.nan
	if "category" not in frame:
		frame["category"] = "unknown"
	if "action_correct" not in frame:
		frame["action_correct"] = np.nan
	if "expected_action" not in frame:
		frame["expected_action"] = pd.NA

	valid_actions = frame.dropna(subset=["expected_action", "action"])
	precision, recall, f1, support = precision_recall_fscore_support(
		valid_actions["expected_action"], valid_actions["action"], labels=ACTIONS, zero_division=0
	)
	accuracy_values = frame["action_correct"].dropna()
	category_table = _category_metrics(frame)
	judge_by_category = category_table[["category", "hallucination_rate", "mean_judge_score"]].copy()

	consistency_rows: list[dict[str, Any]] = []
	for case_id, group in frame.groupby("case_id"):
		actions = group["action"].dropna()
		judge_scores = pd.to_numeric(group.get("judge_score", pd.Series(dtype=float)), errors="coerce").dropna()
		consistency_rows.append(
			{
				"case_id": case_id,
				"run_count": int(len(group)),
				"all_actions_agree": bool(len(actions) > 0 and actions.nunique() == 1),
				"judge_score_std": float(judge_scores.std(ddof=1)) if len(judge_scores) > 1 else None,
			}
		)
	consistency_table = pd.DataFrame(consistency_rows)

	metrics: dict[str, Any] = {
		"n_results": int(len(frame)),
		"overall_action_accuracy": _mean(frame["action_correct"]),
		"overall_accuracy_bootstrap_95_ci": _bootstrap_accuracy(accuracy_values, seed),
		"must_include_pass_rate": _mean(frame["must_include_passed"]) if "must_include_passed" in frame else None,
		"must_not_include_violation_rate": _mean(frame["must_not_include_violation"]),
		"json_compliance_rate": _mean(frame["json_valid"]) if "json_valid" in frame else None,
		"hallucination_rate": _mean(frame["hallucination"]) if "hallucination" in frame else None,
		"mean_judge_score": _mean(frame["judge_score"]) if "judge_score" in frame else None,
		"injection_success_rate_adversarial": _mean(frame.loc[frame["category"] == "adversarial", "injection_success"]),
		"run_to_run_consistency": _mean(consistency_table["all_actions_agree"]) if not consistency_table.empty else None,
		"mean_judge_score_std_across_runs": _mean(consistency_table["judge_score_std"]) if not consistency_table.empty else None,
		"latency_s": {
			"mean": _mean(frame["latency_s"]),
			"median": float(pd.to_numeric(frame["latency_s"], errors="coerce").median()) if "latency_s" in frame else None,
			"p95": float(pd.to_numeric(frame["latency_s"], errors="coerce").quantile(0.95)) if "latency_s" in frame else None,
		},
		"total_input_tokens": int(pd.to_numeric(frame["input_tokens"], errors="coerce").fillna(0).sum()) if "input_tokens" in frame else 0,
		"total_output_tokens": int(pd.to_numeric(frame["output_tokens"], errors="coerce").fillna(0).sum()) if "output_tokens" in frame else 0,
		"judge_vs_human": _human_agreement(frame, human_labels),
		"action_metrics": {
			label: {"precision": float(precision[index]), "recall": float(recall[index]), "f1": float(f1[index]), "support": int(support[index])}
			for index, label in enumerate(ACTIONS)
		},
		"confusion_matrix": {"labels": ACTIONS, "matrix": confusion_matrix(valid_actions["expected_action"], valid_actions["action"], labels=ACTIONS).tolist()},
	}
	return metrics, {
		"by_category": category_table,
		"by_action": pd.DataFrame([{"action": label, **metrics["action_metrics"][label]} for label in ACTIONS]),
		"judge_by_category": judge_by_category,
		"run_consistency": consistency_table,
	}


def enrich_with_cases(scored: pd.DataFrame, cases_path: Path) -> pd.DataFrame:
	"""Join category and expected action from test_cases.json onto scored rows."""
	with cases_path.open(encoding="utf-8") as file:
		cases = pd.DataFrame(json.load(file))[["id", "category", "expected_action"]].rename(columns={"id": "case_id"})
	return scored.merge(cases, on="case_id", how="left")


def main() -> int:
	"""Compute metrics from a scored CSV and write JSON and CSV tables."""
	parser = argparse.ArgumentParser(description="Compute TechNest evaluation metrics.")
	parser.add_argument("input", type=Path, help="Scored CSV input path.")
	parser.add_argument("--human-labels", type=Path, default=Path("data/human_labels.csv"))
	parser.add_argument("--output-dir", type=Path, default=Path("results/metrics"))
	args = parser.parse_args()
	data = pd.read_csv(args.input)
	case_path = Path("data/test_cases.json")
	if case_path.exists() and "expected_action" not in data:
		data = enrich_with_cases(data, case_path)
	human = pd.read_csv(args.human_labels) if args.human_labels.exists() and args.human_labels.stat().st_size else None
	metrics, tables = compute_metrics(data, human)
	args.output_dir.mkdir(parents=True, exist_ok=True)
	(args.output_dir / "metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
	for name, table in tables.items():
		table.to_csv(args.output_dir / f"{name}.csv", index=False)
	print(f"Metrics written to {args.output_dir}")
	return 0


if __name__ == "__main__":
	raise SystemExit(main())
