"""Command-line entry point for deterministic failure analysis."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
	sys.path.insert(0, str(ROOT))

from src.failure_analysis import analyze_failures, print_representative_failures


def main() -> int:
	"""Analyze the scored CSV supplied as the first command-line argument."""
	if len(sys.argv) < 2:
		print(f"Usage: python {Path(sys.argv[0]).name} <scored.csv>", file=sys.stderr)
		return 2

	scored_path = Path(sys.argv[1])
	data_dir = ROOT / "data"
	output_dir = ROOT / "results" / "metrics"
	failures, frequency, crosstab = analyze_failures(
		pd.read_csv(scored_path),
		data_dir / "test_cases.json",
		data_dir / "system_prompt.txt",
		data_dir / "knowledge_base.md",
	)
	output_dir.mkdir(parents=True, exist_ok=True)
	failures.to_csv(output_dir / "failures.csv", index=False)
	frequency.to_csv(output_dir / "failure_frequency.csv", index=False)
	crosstab.to_csv(output_dir / "failure_crosstab.csv", index=False)
	print_representative_failures(failures)
	return 0


if __name__ == "__main__":
	raise SystemExit(main())