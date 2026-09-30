"""Tests for chatbot prompt assembly and tolerant response parsing."""

from pathlib import Path

from src.chatbot import TechNestChatbot
from src.llm_client import LLMClient, LLMResponse
from src.schemas import TestCase


class FakeLLMClient(LLMClient):
    def __init__(self, text: str) -> None:
        self.text = text
        self.system = ""
        self.messages: list[dict[str, str]] = []

    def complete(self, system: str, messages: list[dict[str, str]]) -> LLMResponse:
        self.system = system
        self.messages = messages
        return LLMResponse(text=self.text, latency_s=0.01, input_tokens=4, output_tokens=5)


def make_case() -> TestCase:
    return TestCase(
        id="faq-001",
        category="standard_faq",
        difficulty="easy",
        conversation=[{"role": "user", "content": "What is shipping cost?"}],
        expected_action="answer",
        reference_answer="Standard shipping costs $4.99.",
        kb_section="Shipping",
    )


def test_chatbot_inserts_knowledge_base_and_parses_fenced_json(tmp_path: Path) -> None:
    (tmp_path / "system_prompt.txt").write_text("Rules\n[KNOWLEDGE BASE HERE]", encoding="utf-8")
    (tmp_path / "knowledge_base.md").write_text("SHIPPING FACTS", encoding="utf-8")
    fake = FakeLLMClient('```json\n{"action":"answer","reply":"$4.99"}\n```')

    output, valid, response = TechNestChatbot(fake, tmp_path).complete(make_case())

    assert valid is True
    assert output is not None
    assert output.action == "answer"
    assert "SHIPPING FACTS" in fake.system
    assert response.output_tokens == 5
    assert fake.messages == [{"role": "user", "content": "What is shipping cost?"}]


def test_chatbot_returns_invalid_without_raising(tmp_path: Path) -> None:
    (tmp_path / "system_prompt.txt").write_text("[KNOWLEDGE BASE HERE]", encoding="utf-8")
    (tmp_path / "knowledge_base.md").write_text("KB", encoding="utf-8")

    output, valid, _ = TechNestChatbot(FakeLLMClient("not json"), tmp_path).complete(make_case())

    assert output is None
    assert valid is False