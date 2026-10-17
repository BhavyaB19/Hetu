"""Claude client and the validate-and-retry loop used by every extraction call."""

import logging
from collections.abc import Callable
from typing import Protocol, TypeVar

from anthropic import AsyncAnthropic
from pydantic import BaseModel, ValidationError

log = logging.getLogger(__name__)
T = TypeVar("T", bound=BaseModel)
R = TypeVar("R")
MAX_ATTEMPTS = 3


class LLM(Protocol):
    async def parse(self, system: str, prompt: str, output_format: type[T]) -> T: ...


class ExtractionError(RuntimeError):
    pass


class ClaudeLLM:
    """Calls Claude with structured outputs. Server-side fallback is on, so a
    safety-classifier decline on a sensitive case is retried on another model."""

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
