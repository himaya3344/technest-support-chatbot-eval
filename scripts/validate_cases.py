"""Validate the evaluation cases and print a compact coverage summary."""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

from pydantic import ValidationError

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
	sys.path.insert(0, str(ROOT))

from src.schemas import Category, TestCase  # noqa: E402


VALID_CATEGORIES = set(Category.__args__)
VALID_ACTIONS = {"answer", "clarify", "escalate", "refuse"}
VALID_DIFFICULTIES = {"easy", "medium", "hard"}


def load_cases(path: Path) -> tuple[Any, list[str]]:
	"""Load JSON cases and return parsing errors without raising."""
	try:
		with path.open(encoding="utf-8") as file:
			return json.load(file), []
	except (OSError, json.JSONDecodeError) as exc:
		return None, [f"Could not load {path}: {exc}"]


def validate_cases(data: Any) -> tuple[list[TestCase], list[str]]:
	"""Validate all cases and return valid models plus all discovered errors."""
	errors: list[str] = []
	if not isinstance(data, list):
		return [], ["Top-level test-case data must be a JSON list."]

	cases: list[TestCase] = []
	seen_ids: set[str] = set()
	for index, raw_case in enumerate(data):
		if not isinstance(raw_case, dict):
			errors.append(f"Case {index + 1}: expected a JSON object.")
			continue

		case_id = raw_case.get("id", f"case {index + 1}")
		display_id = repr(case_id)
		if isinstance(case_id, str) and case_id in seen_ids:
			errors.append(f"Case {display_id}: duplicate ID.")
		if isinstance(case_id, str):
			seen_ids.add(case_id)

		if raw_case.get("category") not in VALID_CATEGORIES:
			errors.append(f"Case {display_id}: invalid category.")
		if raw_case.get("expected_action") not in VALID_ACTIONS:
			errors.append(f"Case {display_id}: invalid expected_action.")
		if raw_case.get("difficulty") not in VALID_DIFFICULTIES:
			errors.append(f"Case {display_id}: invalid difficulty.")

		conversation = raw_case.get("conversation")
		if not isinstance(conversation, list) or not conversation:
			errors.append(f"Case {display_id}: conversation must be non-empty.")
		elif not isinstance(conversation[-1], dict) or conversation[-1].get("role") != "user":
			errors.append(f"Case {display_id}: conversation must end with a user message.")

		try:
			cases.append(TestCase.model_validate(raw_case))
		except ValidationError as exc:
			errors.append(f"Case {display_id}: {exc.errors()[0]['msg']}.")

	return cases, errors


def print_summary(cases: list[TestCase]) -> None:
	"""Print category and difficulty counts for validated cases."""
	counts = Counter((case.category, case.difficulty) for case in cases)
	print("Category        easy  medium  hard  total")
	print("------------------------------------------")
	for category in sorted(VALID_CATEGORIES):
		values = [counts[(category, difficulty)] for difficulty in ("easy", "medium", "hard")]
		print(f"{category:<15} {values[0]:>4}  {values[1]:>6}  {values[2]:>4}  {sum(values):>5}")
	print(f"Total cases: {len(cases)}")


def main() -> int:
	"""Run validation for data/test_cases.json."""
	data, errors = load_cases(ROOT / "data" / "test_cases.json")
	cases, validation_errors = validate_cases(data)
	errors.extend(validation_errors)

	print_summary(cases)
	if len(cases) < 50:
		errors.append(f"Expected at least 50 cases; found {len(cases)}.")
	missing_categories = VALID_CATEGORIES - {case.category for case in cases}
	if missing_categories:
		errors.append(f"Missing categories: {', '.join(sorted(missing_categories))}.")

	if errors:
		print("\nValidation errors:")
		print("\n".join(f"- {error}" for error in errors))
		return 1
	print("Validation passed.")
	return 0


if __name__ == "__main__":
	raise SystemExit(main())
