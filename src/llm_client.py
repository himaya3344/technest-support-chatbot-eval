"""Provider clients used by the TechNest evaluation pipeline."""

from __future__ import annotations

import os
import re
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class LLMResponse:
	"""Text returned by an LLM and request-level usage metadata."""

	text: str
	latency_s: float
	input_tokens: int | None = None
	output_tokens: int | None = None


class LLMClient(ABC):
	"""Abstract interface implemented by each supported LLM provider."""

	@abstractmethod
	def complete(self, system: str, messages: list[dict[str, str]]) -> LLMResponse:
		"""Complete a conversation using the supplied system instruction."""


class GeminiClient(LLMClient):
	"""Google Gemini client with retry handling for transient failures."""

	def __init__(
		self,
		model: str,
		temperature: float = 0.0,
		max_tokens: int | None = None,
	) -> None:
		try:
			from google import genai
			from google.genai import types
		except ImportError as exc:
			raise RuntimeError("Install the google-genai package to use the Gemini provider.") from exc

		key = os.getenv("GEMINI_API_KEY")
		if not key:
			raise RuntimeError("GEMINI_API_KEY must be set in the environment.")
		self._client = genai.Client(api_key=key)
		self._types = types
		self.model = model
		self.temperature = temperature
		self.max_tokens = max_tokens

	def complete(self, system: str, messages: list[dict[str, str]]) -> LLMResponse:
		"""Call Gemini, retrying transient 429 and 503 failures."""
		started = time.perf_counter()
		response = self._complete_with_retry(system, messages)
		usage = getattr(response, "usage_metadata", None)
		return LLMResponse(
			text=getattr(response, "text", "") or "",
			latency_s=time.perf_counter() - started,
			input_tokens=getattr(usage, "prompt_token_count", None),
			output_tokens=getattr(usage, "candidates_token_count", None),
		)

	def _complete_with_retry(self, system: str, messages: list[dict[str, str]]) -> Any:
		"""Execute one request under tenacity's exponential retry policy."""
		from google.genai.errors import ClientError, ServerError
		from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential
		from tenacity.wait import wait_base

		base_wait = wait_exponential(multiplier=2, min=5, max=90)

		class RetryDelayWait(wait_base):
			"""Use a provider retry delay when it exceeds tenacity's base wait."""

			def __call__(self, retry_state: Any) -> float:
				exception = retry_state.outcome.exception() if retry_state.outcome else None
				provider_delay = _retry_delay_seconds(exception)
				return max(base_wait(retry_state), provider_delay or 0.0)

		@retry(
			retry=retry_if_exception(
				lambda error: _is_retryable_error(error, ClientError, ServerError)
			),
			wait=RetryDelayWait(),
			stop=stop_after_attempt(5),
			reraise=True,
		)
		def request() -> Any:
			contents = [
				self._types.Content(
					role="user" if message["role"] == "user" else "model",
					parts=[self._types.Part(text=message["content"])],
				)
				for message in messages
			]
			config = self._types.GenerateContentConfig(
				system_instruction=system,
				temperature=self.temperature,
				max_output_tokens=self.max_tokens,
				response_mime_type="application/json",
			)
			return self._client.models.generate_content(
				model=self.model,
				contents=contents,
				config=config,
			)

		return request()


def _is_retryable_error(
	error: BaseException,
	client_error_type: type[BaseException],
	server_error_type: type[BaseException],
) -> bool:
	"""Retry only Gemini 429 client errors and 503 server errors."""
	status = getattr(error, "code", None) or getattr(error, "status_code", None)
	if hasattr(status, "value"):
		status = status.value
	return (isinstance(error, client_error_type) and status == 429) or (
		isinstance(error, server_error_type) and status == 503
	)


def _retry_delay_seconds(error: BaseException | None) -> float | None:
	"""Parse a Gemini 429 retryDelay value such as ``12s`` from an error."""
	if error is None:
		return None
	message = str(getattr(error, "message", "") or error)
	match = re.search(r"retryDelay\s*[=:]\s*[\"']?(\d+(?:\.\d+)?)\s*s?", message)
	return float(match.group(1)) if match else None


def get_client(settings: Any) -> LLMClient:
	"""Create the configured Gemini client without accepting API keys from config."""
	provider = getattr(settings, "provider", "gemini").lower()
	if provider != "gemini":
		raise ValueError(f"Unsupported LLM provider: {provider}")
	return GeminiClient(
		model=getattr(settings, "model"),
		temperature=getattr(settings, "temperature", 0.0),
		max_tokens=getattr(settings, "max_tokens", None),
	)
