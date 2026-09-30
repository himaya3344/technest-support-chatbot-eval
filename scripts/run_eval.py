"""Command-line entry point for the TechNest evaluation runner."""
from __future__ import annotations
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

import argparse
import sys
from pathlib import Path
from types import SimpleNamespace

import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
	sys.path.insert(0, str(ROOT))

from src.llm_client import get_client
from src.runner import run_evaluation


def load_settings(path: Path) -> SimpleNamespace:
	"""Load YAML settings for the evaluation run."""
	with path.open(encoding="utf-8") as file:
		values = yaml.safe_load(file) or {}
	if not isinstance(values, dict):
		raise ValueError("config.yaml must contain a mapping.")
	return SimpleNamespace(**values)


def parse_args() -> argparse.Namespace:
	"""Parse command-line options."""
	parser = argparse.ArgumentParser(description="Run TechNest chatbot evaluation.")
	parser.add_argument("--config", type=Path, default=Path("config.yaml"))
	parser.add_argument("--resume", type=Path, help="Resume from an existing raw JSONL file.")
	parser.add_argument("--limit", type=int, help="Run only the first N selected cases.")
	parser.add_argument("--category", help="Run only cases in this category.")
	return parser.parse_args()


def main() -> int:
	"""Load settings, create the LLM client, and run the evaluation."""
	args = parse_args()
	settings = load_settings(args.config)
	client = get_client(settings)
	output_file, _ = run_evaluation(
		settings,
		client,
		resume_file=args.resume,
		limit=args.limit,
		category=args.category,
	)
	print(f"Raw results: {output_file}")
	return 0


if __name__ == "__main__":
	raise SystemExit(main())
