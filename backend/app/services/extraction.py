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

from app.schemas.bundle import (
    Claim,
    JudgmentExtraction,
    MediaExtraction,
    PublicExtraction,
    SourceDocument,
    Span,
    TimelineEvent,
    quote_in,
)
from app.schemas.extraction import LLMJudgment, LLMMedia, LLMPublic
from app.services.anonymizer import Person
from app.services.llm import LLM, ask

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

    raw, result = await ask(llm, SYSTEM, prompt, LLMJudgment, convert)
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

    raw, result = await ask(llm, SYSTEM, prompt, LLMMedia, convert)
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

    raw, result = await ask(llm, SYSTEM, prompt, LLMPublic, convert)
    return result, raw.people
