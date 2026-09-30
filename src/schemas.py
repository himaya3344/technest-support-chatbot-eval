"""Pydantic models shared by the evaluation pipeline."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


Role = Literal["system", "user", "assistant"]
Action = Literal["answer", "clarify", "escalate", "refuse"]
Category = Literal[
	"standard_faq",
	"multi_turn",
	"out_of_scope",
	"escalation",
	"ambiguous",
	"adversarial",
	"robustness",
	"bias",
]
Difficulty = Literal["easy", "medium", "hard"]


class Message(BaseModel):
	"""A single message in a test conversation."""

	model_config = ConfigDict(extra="forbid")

	role: Role
	content: str = Field(min_length=1)


class TestCase(BaseModel):
	"""One chatbot evaluation case and its expected behavior."""

	model_config = ConfigDict(extra="forbid")

	id: str = Field(min_length=1)
	category: Category
	difficulty: Difficulty
	conversation: list[Message] = Field(min_length=1)
	expected_action: Action
	must_include: list[str] = Field(default_factory=list)
	must_not_include: list[str] = Field(default_factory=list)
	reference_answer: str = Field(min_length=1)
	kb_section: str = Field(min_length=1)
	notes: str = ""
	pair_id: str | None = None


class ChatbotOutput(BaseModel):
	"""The JSON response expected from the chatbot."""

	model_config = ConfigDict(extra="forbid")

	action: Action
	reply: str = Field(min_length=1)


class RawResult(BaseModel):
	"""Raw output and runtime metadata for one case execution."""

	model_config = ConfigDict(extra="forbid")

	case_id: str = Field(min_length=1)
	run_index: int = Field(ge=0)
	raw_text: str
	parsed_output: ChatbotOutput | None = None
	json_valid: bool
	latency_s: float = Field(ge=0)
	input_tokens: int | None = Field(default=None, ge=0)
	output_tokens: int | None = Field(default=None, ge=0)
	error: str | None = None


class ScoredResult(RawResult):
	"""A raw result augmented with rule- and judge-based scores."""

	action_correct: bool | None = None
	must_include_hits: list[str] = Field(default_factory=list)
	must_include_passed: bool | None = None
	must_not_include_violations: list[str] = Field(default_factory=list)
	must_not_include_violation: bool = False
	injection_success: bool = False
	correctness: int | None = Field(default=None, ge=1, le=5)
	groundedness: int | None = Field(default=None, ge=1, le=5)
	completeness: int | None = Field(default=None, ge=1, le=5)
	tone: int | None = Field(default=None, ge=1, le=5)
	judge_score: float | None = Field(default=None, ge=0)
	hallucination: bool | None = None
	judge_rationale: str | None = None
	prompt_injection_success: bool | None = None
	failure_category: str | None = None
