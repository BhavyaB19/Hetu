"""Structured extraction with Claude.

One call per judgment, one per news article, and one for all public reactions of a
case. Claude returns JSON that matches a Pydantic schema (structured outputs). The
result is then checked against the source text: every quote must appear verbatim.
If validation fails, the call is retried with the problems listed.

Claude sees the original text (names included) and lists the private people it
finds; the anonymizer then replaces those names everywhere before storage.
"""

import datetime as dt
import json
import logging
from collections.abc import Callable
from typing import Protocol, TypeVar

from anthropic import AsyncAnthropic
from pydantic import BaseModel, Field, ValidationError

from app.anonymizer import Person
from app.schemas import (
    Claim,
    ClaimVerdict,
    Framing,
    JudgmentExtraction,
    MediaExtraction,
    OutcomeDirection,
    Phase,
    PublicExtraction,
    Sentiment,
    SourceDocument,
    Span,
    TimelineEvent,
    quote_in,
)

log = logging.getLogger(__name__)
T = TypeVar("T", bound=BaseModel)
R = TypeVar("R")
MAX_ATTEMPTS = 3

SYSTEM = """You extract structured, evidence-backed data about Indian court cases for a \
research tool that compares what a court found with how media and the public described it.

Rules:
- Use only the document you are given. Never add outside knowledge.
- Every "quote" field must be copied verbatim from the document: an exact, contiguous \
passage of 5 to 40 words. Do not paraphrase, merge or trim words inside a quote.
- List in "people" every named private individual (accused, victim, witness, relative, \
minor, or other private person) with any short forms of their name used in the text. Do \
not list judges, lawyers, police officers acting officially, or public officials.
- Write summaries neutrally. Do not judge the judges, and do not predict outcomes."""


# ---------- what Claude returns ----------


class LLMTimelineEvent(BaseModel):
    date: str | None = Field(description="YYYY-MM-DD, or null if the document gives no date")
    label: str = Field(description="2 to 5 words, e.g. 'Trial court acquittal'")
    description: str
    phase: Phase
    court_weight: float = Field(description="0 to 1: how central this event is to the court's reasoning")
    quote: str


class LLMJudgment(BaseModel):
    people: list[Person]
    facts: str = Field(description="The facts the court accepted, in 2 to 4 sentences")
    facts_quote: str
    motive: str = Field(description="The motive the court found, or that none was established")
    motive_quote: str
    trigger: str = Field(description="The immediate trigger of the incident")
    trigger_quote: str
    court_reasoning: str = Field(description="Why the court decided as it did, in 2 to 4 sentences")
    court_reasoning_quote: str
    outcome: str = Field(description="The final outcome, including sentence if any")
    outcome_quote: str
    outcome_direction: OutcomeDirection
    legal_provisions: list[str] = Field(description="Statutory sections, e.g. 'Section 304 Part I IPC'")
    timeline: list[LLMTimelineEvent] = Field(description="3 to 8 key events, oldest first")


class LLMClaim(BaseModel):
    text: str = Field(description="One factual claim the article makes, in your own words")
    quote: str = Field(description="Verbatim passage from the article that makes the claim")
    verdict: ClaimVerdict = Field(
        description="supported / contradicted by the court findings, or absent from them"
    )
    rationale: str = Field(description="One sentence comparing the claim with the court findings")
    judgment_quote: str | None = Field(
        description="Verbatim passage from the court findings that supports or contradicts the "
        "claim, or null when the claim is absent from them"
    )


class LLMMedia(BaseModel):
    people: list[Person]
    framing: Framing
    tone: float = Field(description="-1 (hostile, alarmed) to 1 (approving), 0 neutral")
    narratives: list[str] = Field(description="1 to 3 short phrases naming the story's angle")
    claims: list[LLMClaim] = Field(description="Up to 5 checkable factual claims")
    events_mentioned: list[int] = Field(description="Indexes of court timeline events the article discusses")


class LLMReaction(BaseModel):
    key: str
    sentiment: Sentiment
    themes: list[str] = Field(description="1 to 2 theme labels from the shared list")


class LLMPublic(BaseModel):
    people: list[Person]
    reactions: list[LLMReaction]


# ---------- client ----------


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


async def _ask(
    llm: LLM,
    prompt: str,
    output_format: type[T],
    convert: Callable[[T], R],
) -> tuple[T, R]:
    """Call the LLM, convert and validate; retry with the problems listed."""
    feedback = ""
    for attempt in range(1, MAX_ATTEMPTS + 1):
        raw = await llm.parse(SYSTEM, prompt + feedback, output_format)
        try:
            return raw, convert(raw)
        except (ValidationError, ValueError) as err:
            log.warning("Extraction attempt %d failed validation: %s", attempt, err)
            feedback = (
                "\n\nYour previous answer was rejected. Fix these problems and answer again:\n"
                f"{err}\n\nPrevious answer:\n{raw.model_dump_json()}"
            )
    raise ExtractionError(f"Extraction failed validation after {MAX_ATTEMPTS} attempts.")


def _span(doc: SourceDocument, quote: str, label: str) -> Span:
    if not quote_in(quote, doc.text):
        raise ValueError(f"{label}: quote is not verbatim in the document: {quote!r}")
    return Span(document=doc.key, quote=quote)


def _date(value: str | None) -> dt.date | None:
    try:
        return dt.date.fromisoformat(value) if value else None
    except ValueError:
        return None


async def extract_judgment(llm: LLM, doc: SourceDocument) -> tuple[JudgmentExtraction, list[Person]]:
    prompt = f"Extract the court's findings from this judgment.\n\n<document>\n{doc.text}\n</document>"

    def convert(r: LLMJudgment) -> JudgmentExtraction:
        fields = ["facts", "motive", "trigger", "court_reasoning", "outcome"]
        return JudgmentExtraction(
            document=doc.key,
            facts=r.facts,
            motive=r.motive,
            trigger=r.trigger,
            court_reasoning=r.court_reasoning,
            outcome=r.outcome,
            outcome_direction=r.outcome_direction,
            legal_provisions=r.legal_provisions,
            timeline=[
                TimelineEvent(
                    date=_date(e.date),
                    label=e.label,
                    description=e.description,
                    phase=e.phase,
                    court_weight=e.court_weight,
                    evidence=_span(doc, e.quote, f"timeline[{i}]"),
                )
                for i, e in enumerate(r.timeline)
            ],
            evidence={f: _span(doc, getattr(r, f"{f}_quote"), f) for f in fields},
        )

    raw, result = await _ask(llm, prompt, LLMJudgment, convert)
    return result, raw.people


async def extract_media(
    llm: LLM, doc: SourceDocument, judgment: JudgmentExtraction, judgment_doc: SourceDocument
) -> tuple[MediaExtraction, list[Person]]:
    findings = {
        "facts": judgment.facts,
        "motive": judgment.motive,
        "trigger": judgment.trigger,
        "court_reasoning": judgment.court_reasoning,
        "outcome": judgment.outcome,
        "timeline": [f"{i}: {e.date or 'undated'} {e.label}" for i, e in enumerate(judgment.timeline)],
    }
    prompt = (
        "Analyse how this news article frames the case, and check each factual claim it makes "
        "against the court's findings.\n\n"
        f"<court_findings>\n{json.dumps(findings, indent=2, default=str)}\n</court_findings>\n\n"
        f"<judgment_text>\n{judgment_doc.text}\n</judgment_text>\n\n"
        f"<article outlet={doc.source_name!r} date={doc.published_at}>\n{doc.text}\n</article>\n\n"
        "Article quotes come from <article>; judgment quotes come from <judgment_text>."
    )

    def convert(r: LLMMedia) -> MediaExtraction:
        events = [i for i in r.events_mentioned if 0 <= i < len(judgment.timeline)]
        return MediaExtraction(
            document=doc.key,
            headline=doc.title or doc.text.strip().splitlines()[0],
            framing=r.framing,
            tone=r.tone,
            narratives=r.narratives,
            claims=[
                Claim(
                    text=c.text,
                    evidence=_span(doc, c.quote, f"claims[{i}]"),
                    verdict=c.verdict,
                    rationale=c.rationale,
                    judgment_evidence=(
                        _span(judgment_doc, c.judgment_quote, f"claims[{i}].judgment_quote")
                        if c.judgment_quote
                        else None
                    ),
                )
                for i, c in enumerate(r.claims)
            ],
            events_mentioned=events,
        )

    raw, result = await _ask(llm, prompt, LLMMedia, convert)
    return result, raw.people


async def classify_public(
    llm: LLM, docs: list[SourceDocument]
) -> tuple[list[PublicExtraction], list[Person]]:
    if not docs:
        return [], []
    items = "\n".join(f'<reaction key="{d.key}">{d.text}</reaction>' for d in docs)
    prompt = (
        "Classify each public reaction to this court case. Sentiment means which side the "
        "writer leans towards. First settle on 3 to 6 short theme labels that cover these "
        "reactions, then tag each reaction with 1 or 2 of them, using the exact same wording "
        f"every time. Return one entry per reaction key.\n\n{items}"
    )
    keys = {d.key for d in docs}

    def convert(r: LLMPublic) -> list[PublicExtraction]:
        got = {x.key for x in r.reactions}
        if got != keys:
            raise ValueError(f"Expected one entry per key. Missing: {keys - got}, unknown: {got - keys}")
        return [PublicExtraction(document=x.key, sentiment=x.sentiment, themes=x.themes) for x in r.reactions]

    raw, result = await _ask(llm, prompt, LLMPublic, convert)
    return result, raw.people
