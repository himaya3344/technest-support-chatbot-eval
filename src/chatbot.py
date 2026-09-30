"""TechNest chatbot prompt assembly and response parsing."""

from __future__ import annotations

import json
import re
from pathlib import Path

from src.llm_client import LLMClient, LLMResponse
from src.schemas import ChatbotOutput, TestCase


CODE_FENCE_RE = re.compile(r"^\s*```(?:json)?\s*|\s*```\s*$", re.IGNORECASE)


class TechNestChatbot:
	"""Run a test conversation against a configured LLM client."""

	def __init__(self, client: LLMClient, data_dir: Path | str | None = None) -> None:
		root = Path(data_dir) if data_dir is not None else Path(__file__).resolve().parents[1] / "data"
		system_prompt = (root / "system_prompt.txt").read_text(encoding="utf-8")
		knowledge_base = (root / "knowledge_base.md").read_text(encoding="utf-8")
		self.system_prompt = system_prompt.replace("[KNOWLEDGE BASE HERE]", knowledge_base)
		self.client = client

	def complete(self, test_case: TestCase) -> tuple[ChatbotOutput | None, bool, LLMResponse]:
		"""Send a test case to the client and parse its response safely."""
		messages = [message.model_dump() for message in test_case.conversation]
		response = self.client.complete(system=self.system_prompt, messages=messages)
		parsed_output, json_valid = self.parse_response(response.text)
		return parsed_output, json_valid, response

	@staticmethod
	def parse_response(raw_text: str) -> tuple[ChatbotOutput | None, bool]:
		"""Parse plain JSON or fenced JSON without raising on malformed output."""
		cleaned = CODE_FENCE_RE.sub("", raw_text).strip()
		try:
			payload = json.loads(cleaned)
			return ChatbotOutput.model_validate(payload), True
		except (json.JSONDecodeError, TypeError, ValueError):
			return None, False


Chatbot = TechNestChatbot
