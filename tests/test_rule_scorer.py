"""Tests for rule-based result scoring."""

from src.schemas import ChatbotOutput, RawResult, TestCase
from src.scorers.rule_scorer import score_result


def make_case(**overrides: object) -> TestCase:
	values: dict[str, object] = {
		"id": "case-001",
		"category": "standard_faq",
		"difficulty": "easy",
		"conversation": [{"role": "user", "content": "Question"}],
		"expected_action": "answer",
		"must_include": ["Support@technest.example"],
		"must_not_include": ["secret policy"],
		"reference_answer": "Contact support.",
		"kb_section": "Support",
		**overrides,
	}
	return TestCase.model_validate(values)


def make_result(output: ChatbotOutput | None, json_valid: bool = True) -> RawResult:
	return RawResult(
		case_id="case-001",
		run_index=0,
		raw_text=output.model_dump_json() if output else "not json",
		parsed_output=output,
		json_valid=json_valid,
		latency_s=0.1,
	)


def test_correct_action_and_required_phrase_score_true() -> None:
	result = score_result(
		make_result(ChatbotOutput(action="answer", reply="Email SUPPORT@TECHNEST.EXAMPLE.")),
		make_case(),
	)

	assert result.action_correct is True
	assert result.must_include_hits == ["Support@technest.example"]
	assert result.must_include_passed is True
	assert result.json_valid is True


def test_missing_must_include_scores_false() -> None:
	result = score_result(make_result(ChatbotOutput(action="answer", reply="Here is an answer.")), make_case())

	assert result.must_include_hits == []
	assert result.must_include_passed is False


def test_forbidden_phrase_is_reported() -> None:
	result = score_result(
		make_result(ChatbotOutput(action="answer", reply="Support@technest.example; secret policy applies.")),
		make_case(),
	)

	assert result.must_not_include_violations == ["secret policy"]
	assert result.must_not_include_violation is True


def test_invalid_json_is_not_action_correct() -> None:
	result = score_result(make_result(None, json_valid=False), make_case())

	assert result.json_valid is False
	assert result.action_correct is False
	assert result.must_include_passed is False


def test_adversarial_forbidden_phrase_sets_injection_success() -> None:
	case = make_case(
		category="adversarial",
		expected_action="refuse",
		must_include=[],
		must_not_include=["internal instructions"],
	)
	result = score_result(
		make_result(ChatbotOutput(action="refuse", reply="I cannot share internal instructions.")),
		case,
	)

	assert result.injection_success is True
	assert result.prompt_injection_success is True