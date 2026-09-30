"""Generate report/report.md from a scored CSV and evaluation artifacts."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
	sys.path.insert(0, str(ROOT))

from src.report_builder import write_report


def main() -> int:
	"""Generate the Markdown report using the scored CSV argument."""
	if len(sys.argv) < 2:
		print(f"Usage: python {Path(sys.argv[0]).name} <scored.csv>", file=sys.stderr)
		return 2
	output = write_report(ROOT, Path(sys.argv[1]))
	print(f"Report written to {output}")
	return 0


if __name__ == "__main__":
	raise SystemExit(main())