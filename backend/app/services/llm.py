"""LLM clients (Groq, OpenAI or Claude) and the validate-and-retry loop used by every extraction call.

Each client does one thing: send a prompt and return JSON that matches a Pydantic
schema. Pick one with LLM_PROVIDER in .env.
"""

import asyncio
import json
import logging
import time
from collections import deque
from collections.abc import Callable
from typing import Any, Literal, Protocol, TypeVar

import groq
import openai
from anthropic import AsyncAnthropic
from pydantic import BaseModel, ValidationError

from app.core.config import Settings, secret

log = logging.getLogger(__name__)
T = TypeVar("T", bound=BaseModel)
R = TypeVar("R")
MAX_ATTEMPTS = 3

# Groq free plan: requests must fit well inside its ~8,000 tokens-per-minute limit.
FREE_GROQ_INPUT_BUDGET = 4500
FREE_GROQ_OUTPUT_TOKENS = 2500
FREE_GROQ_TOKENS_PER_MINUTE = 7500

# Seconds before one request is abandoned (then retried by the SDK). Small requests answer in
# well under a minute; a whole long judgment in one call can take a few minutes.
SMALL_REQUEST_TIMEOUT = 120
LARGE_REQUEST_TIMEOUT = 600


def estimate_tokens(text: str) -> int:
    """A cautious token estimate (about 3 characters per token) for budgeting requests."""
    return len(text) // 3 + 1


class LLM(Protocol):
    # Largest prompt (in estimated tokens) one request may carry, or None for no limit.
    input_budget: int | None

    async def parse(self, system: str, prompt: str, output_format: type[T]) -> T: ...


class TokenRateLimiter:
    """Spaces requests so the tokens sent in any 60-second window stay under a limit."""

    def __init__(self, tokens_per_minute: int, clock: Callable[[], float] = time.monotonic) -> None:
        self._limit = tokens_per_minute
        self._clock = clock
        self._sent: deque[tuple[float, int]] = deque()
        self._lock = asyncio.Lock()

    async def reserve(self, tokens: int) -> None:
        tokens = min(tokens, self._limit)
        async with self._lock:
            while True:
                now = self._clock()
                while self._sent and now - self._sent[0][0] >= 60:
                    self._sent.popleft()
                if sum(t for _, t in self._sent) + tokens <= self._limit:
                    self._sent.append((now, tokens))
                    return
                wait = 60 - (now - self._sent[0][0]) + 0.1
                log.info("Pacing LLM calls for the provider's rate limit: waiting %.0fs", wait)
                await asyncio.sleep(wait)


class ExtractionError(RuntimeError):
    pass


class ClaudeLLM:
    """Calls Claude with structured outputs. Server-side fallback is on, so a
    safety-classifier decline on a sensitive case is retried on another model."""

    input_budget: int | None = None  # 1M-token context: whole judgments fit in one call

    def __init__(self, api_key: str, model: str) -> None:
        self._client = AsyncAnthropic(api_key=api_key)
        self._model = model

    async def parse(self, system: str, prompt: str, output_format: type[T]) -> T:
        response = await self._client.beta.messages.parse(
            model=self._model,
            max_tokens=16000,
            system=system,
            messages=[{"role": "user", "content": prompt}],
            output_format=output_format,
            output_config={"effort": "medium"},
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
        )
        if response.stop_reason == "refusal":
            raise ExtractionError("Claude declined to process this document.")
        if response.stop_reason == "max_tokens" or response.parsed_output is None:
            raise ExtractionError(f"No structured output (stop_reason={response.stop_reason}).")
        return response.parsed_output


def strict_schema(model: type[BaseModel]) -> dict[str, Any]:
    """Pydantic JSON schema adapted to strict mode (Groq and OpenAI): every object lists all of its
    properties as required and forbids extra ones. Optional fields stay nullable."""

    def fix(node: Any) -> Any:
        if isinstance(node, dict):
            node = {k: fix(v) for k, v in node.items() if k not in ("title", "default")}
            if "properties" in node:
                node["required"] = list(node["properties"])
                node["additionalProperties"] = False
            return node
        if isinstance(node, list):
            return [fix(v) for v in node]
        return node

    return fix(model.model_json_schema())


class GroqLLM:
    """Calls an open-weight model on Groq with strict structured outputs
    (https://console.groq.com/docs/structured-outputs)."""

    def __init__(
        self,
        api_key: str,
        model: str,
        *,
        input_budget: int | None = None,
        max_output_tokens: int = 32000,
        tokens_per_minute: int | None = None,
        reasoning_effort: Literal["low", "medium", "high"] | None = None,
    ) -> None:
        # The SDK retries rate limits and server errors, honouring retry-after.
        timeout = SMALL_REQUEST_TIMEOUT if input_budget else LARGE_REQUEST_TIMEOUT
        self._client = groq.AsyncGroq(api_key=api_key, max_retries=5, timeout=timeout)
        self._model = model
        self.input_budget = input_budget
        self._max_output = max_output_tokens
        self._limiter = TokenRateLimiter(tokens_per_minute) if tokens_per_minute else None
        self._reasoning = reasoning_effort

    async def parse(self, system: str, prompt: str, output_format: type[T]) -> T:
        schema = strict_schema(output_format)
        if self._limiter:
            # Replies are usually far below the output cap; Groq's own 429 retries cover the rest.
            expected_output = min(self._max_output, 1000)
            await self._limiter.reserve(
                estimate_tokens(system + prompt + json.dumps(schema)) + expected_output
            )
        extra: dict[str, Any] = {"reasoning_effort": self._reasoning} if self._reasoning else {}
        try:
            response = await self._client.chat.completions.create(
                model=self._model,
                messages=[{"role": "system", "content": system}, {"role": "user", "content": prompt}],
                response_format={
                    "type": "json_schema",
                    "json_schema": {"name": output_format.__name__, "strict": True, "schema": schema},
                },
                max_completion_tokens=self._max_output,
                **extra,
            )
        except groq.RateLimitError as err:
            raise ExtractionError(
                f"Groq rate limit reached ({err.message}). Long documents may exceed the free plan's "
                "tokens-per-minute limit; wait and retry, or use a paid plan."
            ) from err
        except groq.APIStatusError as err:
            if err.status_code == 413:
                raise ExtractionError(
                    "Document too large for this Groq plan's tokens-per-minute limit."
                ) from err
            raise ExtractionError(f"Groq request failed ({err.status_code}): {err.message}") from err
        except groq.APIConnectionError as err:  # includes timeouts, after the SDK's retries
            raise ExtractionError(f"Could not get a response from Groq: {err}") from err

        choice = response.choices[0]
        if choice.finish_reason == "length":
            raise ExtractionError("Groq output was cut off at the token limit.")
        try:
            return output_format.model_validate(json.loads(choice.message.content or ""))
        except (json.JSONDecodeError, ValidationError) as err:
            raise ExtractionError(f"Groq returned output that does not match the schema: {err}") from err


class OpenAILLM:
    """Calls OpenAI's Responses API with strict structured outputs
    (https://developers.openai.com/api/docs/guides/structured-outputs)."""

    input_budget: int | None = None  # 1M-token context: whole judgments fit in one call

    def __init__(self, api_key: str, model: str) -> None:
        # The SDK retries rate limits and server errors, honouring retry-after.
        self._client = openai.AsyncOpenAI(api_key=api_key, max_retries=5, timeout=LARGE_REQUEST_TIMEOUT)
        self._model = model

    async def parse(self, system: str, prompt: str, output_format: type[T]) -> T:
        try:
            response = await self._client.responses.create(
                model=self._model,
                instructions=system,
                input=prompt,
                text={
                    "format": {
                        "type": "json_schema",
                        "name": output_format.__name__,
                        "schema": strict_schema(output_format),
                        "strict": True,
                    }
                },
                max_output_tokens=32000,
            )
        except openai.RateLimitError as err:
            raise ExtractionError(f"OpenAI rate limit reached: {err.message}") from err
        except openai.APIStatusError as err:
            raise ExtractionError(f"OpenAI request failed ({err.status_code}): {err.message}") from err
        except openai.APIConnectionError as err:  # includes timeouts, after the SDK's retries
            raise ExtractionError(f"Could not get a response from OpenAI: {err}") from err

        if response.status == "incomplete":
            reason = response.incomplete_details.reason if response.incomplete_details else "unknown"
            raise ExtractionError(f"OpenAI output was cut off ({reason}).")
        for item in response.output:
            for part in getattr(item, "content", None) or []:
                if part.type == "refusal":
                    raise ExtractionError(f"OpenAI declined to process this document: {part.refusal}")
        try:
            return output_format.model_validate(json.loads(response.output_text))
        except (json.JSONDecodeError, ValidationError) as err:
            raise ExtractionError(f"OpenAI returned output that does not match the schema: {err}") from err


def make_llm(settings: Settings) -> LLM | None:
    """The LLM client for LLM_PROVIDER, or None if that provider's API key is not set."""
    provider = settings.llm_provider
    if provider == "groq":
        key = secret(settings.groq_api_key)
        if not key:
            return None
        log.info("Extracting with Groq (%s, %s plan)", settings.groq_model, settings.groq_plan)
        if settings.groq_plan == "free":
            return GroqLLM(
                key,
                settings.groq_model,
                input_budget=FREE_GROQ_INPUT_BUDGET,
                max_output_tokens=FREE_GROQ_OUTPUT_TOKENS,
                tokens_per_minute=FREE_GROQ_TOKENS_PER_MINUTE,
                reasoning_effort="low",
            )
        return GroqLLM(key, settings.groq_model)
    if provider == "openai":
        key = secret(settings.openai_api_key)
        if not key:
            return None
        log.info("Extracting with OpenAI (%s)", settings.openai_model)
        return OpenAILLM(key, settings.openai_model)
    key = secret(settings.anthropic_api_key)
    if not key:
        return None
    log.info("Extracting with Claude (%s)", settings.anthropic_model)
    return ClaudeLLM(key, settings.anthropic_model)


async def ask(
    llm: LLM,
    system: str,
    prompt: str,
    output_format: type[T],
    convert: Callable[[T], R],
) -> tuple[T, R]:
    """Call the LLM, convert and validate; retry with the problems listed."""
    feedback = ""
    for attempt in range(1, MAX_ATTEMPTS + 1):
        raw = await llm.parse(system, prompt + feedback, output_format)
        try:
            return raw, convert(raw)
        except (ValidationError, ValueError) as err:
            log.warning("Extraction attempt %d failed validation: %s", attempt, err)
            feedback = (
                "\n\nYour previous answer was rejected. Fix these problems and answer again:\n"
                f"{err}\n\nPrevious answer:\n{raw.model_dump_json()}"
            )
    raise ExtractionError(f"Extraction failed validation after {MAX_ATTEMPTS} attempts.")
