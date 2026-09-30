"""Tests for the shared Pydantic schemas."""

import pytest
from pydantic import ValidationError

from src.schemas import ChatbotOutput, Message, TestCase


def test_valid_test_case() -> None:
    case = TestCase(
        id="faq-001",
        category="standard_faq",
        difficulty="easy",
        conversation=[Message(role="user", content="What is your return policy?")],
        expected_action="answer",
        reference_answer="Items can be returned within 30 days.",
        kb_section="Returns",
    )

    assert case.conversation[-1].role == "user"
    assert ChatbotOutput(action="answer", reply="Returns are accepted within 30 days.").action == "answer"


def test_invalid_test_case_rejects_unknown_action_and_empty_reply() -> None:
    with pytest.raises(ValidationError):
        TestCase(
            id="faq-002",
            category="standard_faq",
            difficulty="easy",
            conversation=[{"role": "user", "content": "Hello"}],
            expected_action="unknown",
            reference_answer="An answer.",
            kb_section="Returns",
        )

    with pytest.raises(ValidationError):
        ChatbotOutput(action="answer", reply="")