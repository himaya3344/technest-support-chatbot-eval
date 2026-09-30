"""Run metrics, failure analysis, and plotting for one scored CSV."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
	sys.path.insert(0, str(ROOT))

from src.failure_analysis import analyze_failures, print_representative_failures
from src.metrics import compute_metrics, enrich_with_cases
from src.plots import plot_all


def main() -> int:
	"""Compute metrics, classify failures, and generate charts."""
	if len(sys.argv) < 2:
		print(f"Usage: python {Path(sys.argv[0]).name} <scored.csv>", file=sys.stderr)
		return 2

	scored_path = Path(sys.argv[1])
	metrics_dir = ROOT / "results" / "metrics"
	figures_dir = ROOT / "results" / "figures"
	data_dir = ROOT / "data"
	scored = pd.read_csv(scored_path)
	data = enrich_with_cases(scored, data_dir / "test_cases.json")
	human_path = data_dir / "human_labels.csv"
	human = pd.read_csv(human_path) if human_path.exists() and human_path.stat().st_size else None
	metrics, tables = compute_metrics(data, human)
	metrics_dir.mkdir(parents=True, exist_ok=True)
	(metrics_dir / "metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
	for name, table in tables.items():
		table.to_csv(metrics_dir / f"{name}.csv", index=False)

	failures, frequency, crosstab = analyze_failures(
		scored,
		data_dir / "test_cases.json",
		data_dir / "system_prompt.txt",
		data_dir / "knowledge_base.md",
	)
	failures.to_csv(metrics_dir / "failures.csv", index=False)
	frequency.to_csv(metrics_dir / "failure_frequency.csv", index=False)
	crosstab.to_csv(metrics_dir / "failure_crosstab.csv", index=False)
	print_representative_failures(failures)

	plot_tables = dict(tables)
	plot_tables["failure_frequency"] = frequency
	plot_all(scored, metrics, plot_tables, data_dir / "test_cases.json", figures_dir)
	print(f"Analysis complete. Metrics: {metrics_dir}; figures: {figures_dir}")
	return 0


if __name__ == "__main__":
	raise SystemExit(main())
