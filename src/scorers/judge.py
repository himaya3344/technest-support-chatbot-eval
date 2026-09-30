"""LLM-based judging for valid chatbot responses."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from src.llm_client import LLMClient
from src.schemas import RawResult, ScoredResult, TestCase


class JudgeOutput(BaseModel):
	"""The strict JSON contract expected from the judge model."""

	model_config = ConfigDict(extra="forbid")

	correctness: int = Field(ge=1, le=5)
	groundedness: int = Field(ge=1, le=5)
	completeness: int = Field(ge=1, le=5)
	tone: int = Field(ge=1, le=5)
	hallucination: bool
	rationale: str = Field(min_length=1)


def load_judge_rubric(path: Path | str | None = None) -> str:
	"""Load the judge rubric from data/judge_rubric.md."""
	rubric_path = Path(path) if path else Path(__file__).resolve().parents[2] / "data" / "judge_rubric.md"
	return rubric_path.read_text(encoding="utf-8")


def _clean_json(text: str) -> str:
	"""Remove an optional Markdown JSON fence from judge output."""
	return re.sub(r"^\s*```(?:json)?\s*|\s*```\s*$", "", text, flags=re.IGNORECASE).strip()


def build_judge_prompt(case: TestCase, result: RawResult, knowledge_base: str, rubric: str) -> str:
	"""Build a self-contained judge request from evaluation evidence."""
	conversation = json.dumps([message.model_dump() for message in case.conversation], ensure_ascii=False)
	reply = result.parsed_output.reply if result.parsed_output else ""
	return f"""{rubric}

KNOWLEDGE BASE:
{knowledge_base}

CONVERSATION:
{conversation}

REFERENCE ANSWER:
{case.reference_answer}

CHATBOT REPLY:
{reply}

Return ONLY one JSON object with integer scores from 1 to 5 for correctness, groundedness,
completeness, and tone; a boolean hallucination; and a one-sentence rationale.
"""


def judge_result(
	result: RawResult,
	case: TestCase,
	client: LLMClient,
	knowledge_base: str,
	rubric: str,
) -> ScoredResult:
	"""Apply rule scores and, when eligible, add LLM judge scores."""
	from src.scorers.rule_scorer import score_result

	scored = score_result(result, case)
	if not result.json_valid or result.parsed_output is None:
		return scored

	response = client.complete(
		system="You are a strict TechNest chatbot evaluator. Follow the supplied rubric exactly.",
		messages=[{"role": "user", "content": build_judge_prompt(case, result, knowledge_base, rubric)}],
	)
	try:
		judge = JudgeOutput.model_validate(json.loads(_clean_json(response.text)))
	except (json.JSONDecodeError, TypeError, ValidationError):
		return scored

	return scored.model_copy(
		update={
			"correctness": judge.correctness,
			"groundedness": judge.groundedness,
			"completeness": judge.completeness,
			"tone": judge.tone,
			"hallucination": judge.hallucination,
			"judge_rationale": judge.rationale,
			"judge_score": (
				judge.correctness + judge.groundedness + judge.completeness + judge.tone
			) / 4,
		}
	)
