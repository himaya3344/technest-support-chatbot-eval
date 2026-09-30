"""Tests for deterministic failure categorization."""

import json
from pathlib import Path

import pandas as pd

from src.failure_analysis import analyze_failures


def _run_analysis(tmp_path: Path, row: dict[str, object], expected_action: str = "answer") -> str:
	"""Analyze one hand-built scored row with temporary case resources."""
	cases_path = tmp_path / "test_cases.json"
	cases_path.write_text(
		json.dumps([{"id": "case-1", "category": "standard_faq", "expected_action": expected_action}]),
		encoding="utf-8",
	)
	system_prompt = tmp_path / "system_prompt.txt"
	system_prompt.write_text("System instructions.", encoding="utf-8")
	knowledge_base = tmp_path / "knowledge_base.md"
	knowledge_base.write_text("TechNest policy information.", encoding="utf-8")

	failures, _, _ = analyze_failures(pd.DataFrame([row]), cases_path, system_prompt, knowledge_base)
	return failures.iloc[0]["failure_category"]


def _base_row() -> dict[str, object]:
	return {
		"case_id": "case-1",
		"run_index": 0,
		"action_correct": True,
		"must_include_passed": True,
		"must_not_include_violation": False,
		"json_valid": True,
		"injection_success": False,
		"prompt_injection_success": False,
		"hallucination": False,
		"tone": 5,
		"parsed_output": json.dumps({"action": "answer", "reply": "A reply."}),
	}


def test_assigns_hallucinated_policy(tmp_path: Path) -> None:
	row = _base_row()
	row.update(action_correct=False, hallucination=True)

	assert _run_analysis(tmp_path, row) == "hallucinated_policy"


def test_assigns_missed_escalation(tmp_path: Path) -> None:
	row = _base_row()
	row.update(action_correct=False, parsed_output=json.dumps({"action": "answer", "reply": "I can help."}))

	assert _run_analysis(tmp_path, row, expected_action="escalate") == "missed_escalation"


def test_assigns_format_violation(tmp_path: Path) -> None:
	row = _base_row()
	row.update(action_correct=False, json_valid=False, parsed_output="")

	assert _run_analysis(tmp_path, row) == "format_violation"