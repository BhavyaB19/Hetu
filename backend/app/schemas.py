"""Pydantic models.

Two groups:
- The *case bundle*: what the pipeline reads and writes. A bundle holds a case's
  source documents plus the structured extraction for each. Fixtures are bundles.
- The *case view*: what the API returns to the dashboard.
"""

import datetime as dt
import hashlib
import re
from typing import Literal

from pydantic import BaseModel, Field, model_validator

SourceType = Literal["judgment", "media", "public"]
Phase = Literal["incident", "investigation", "trial", "verdict", "media", "appeal", "other"]
Framing = Literal["sensational", "procedural", "victim_centric", "accused_centric", "other"]
ClaimVerdict = Literal["supported", "contradicted", "absent"]
Sentiment = Literal["support_victim", "support_accused", "neutral_uncertain", "against_media_bias"]
OutcomeDirection = Literal["conviction", "acquittal", "other"]


# ---------- case bundle ----------


class Span(BaseModel):
    """A verbatim quote from one source document: the evidence for a claim."""

    document: str
    quote: str


class SourceDocument(BaseModel):
    key: str
    source_type: SourceType
    source_name: str
    title: str | None = None
    url: str | None = None
    published_at: dt.date | None = None
    language: str = "en"
    text: str


class TimelineEvent(BaseModel):
    date: dt.date | None = None
    label: str
    description: str
    phase: Phase
    court_weight: float = Field(ge=0, le=1, description="How central the court treated this event.")
    evidence: Span | None = None


class JudgmentExtraction(BaseModel):
    document: str
    facts: str
    motive: str
    trigger: str
    court_reasoning: str
    outcome: str
    outcome_direction: OutcomeDirection
    legal_provisions: list[str]
    timeline: list[TimelineEvent]
    evidence: dict[str, Span] = Field(
        description="Field name (facts, motive, trigger, court_reasoning, outcome) -> quote."
    )


class Claim(BaseModel):
    text: str
    evidence: Span
    verdict: ClaimVerdict
    rationale: str
    judgment_evidence: Span | None = None


class MediaExtraction(BaseModel):
    document: str
    headline: str
    framing: Framing
    tone: float = Field(ge=-1, le=1)
    narratives: list[str]
    claims: list[Claim]
    events_mentioned: list[int] = Field(description="Indexes into the judgment timeline.")


class PublicExtraction(BaseModel):
    document: str
    sentiment: Sentiment
    themes: list[str]


class CaseInfo(BaseModel):
    slug: str
    title: str
    category: str
    court: str | None = None
    summary: str | None = None
    is_illustrative: bool = False


class CaseBundle(BaseModel):
    case: CaseInfo
    documents: list[SourceDocument]
    judgment: JudgmentExtraction | None = None
    media: list[MediaExtraction] = []
    public: list[PublicExtraction] = []

    @property
    def is_extracted(self) -> bool:
        return self.judgment is not None

    def document(self, key: str) -> SourceDocument:
        for doc in self.documents:
            if doc.key == key:
                return doc
        raise KeyError(key)

    @model_validator(mode="after")
    def _check_evidence(self) -> "CaseBundle":
        problems = evidence_problems(self)
        if problems:
            raise ValueError("Evidence does not match the source documents:\n" + "\n".join(problems))
        return self


CURLY_QUOTES = str.maketrans({0x2018: "'", 0x2019: "'", 0x201C: '"', 0x201D: '"'})


def normalize(text: str) -> str:
    """Collapse whitespace and unify quotes so quote matching ignores formatting."""
    text = text.translate(CURLY_QUOTES)
    return re.sub(r"\s+", " ", text).strip().lower()


def content_hash(text: str) -> str:
    """Used to drop duplicate documents (same text, different formatting)."""
    return hashlib.sha256(normalize(text).encode()).hexdigest()


def quote_in(quote: str, text: str) -> bool:
    return bool(quote.strip()) and normalize(quote) in normalize(text)


def iter_spans(bundle: CaseBundle):
    """Yield (label, span) for every piece of evidence in the bundle."""
    j = bundle.judgment
    if j:
        for field, span in j.evidence.items():
            yield f"judgment.{field}", span
        for i, event in enumerate(j.timeline):
            if event.evidence:
                yield f"timeline[{i}]", event.evidence
    for m in bundle.media:
        for i, claim in enumerate(m.claims):
            yield f"{m.document}.claims[{i}]", claim.evidence
            if claim.judgment_evidence:
                yield f"{m.document}.claims[{i}].judgment", claim.judgment_evidence


def evidence_problems(bundle: CaseBundle) -> list[str]:
    """Every span must point at a real document and quote it verbatim."""
    texts = {d.key: d.text for d in bundle.documents}
    problems = []
    for label, span in iter_spans(bundle):
        if span.document not in texts:
            problems.append(f"{label}: unknown document {span.document!r}")
        elif not quote_in(span.quote, texts[span.document]):
            problems.append(f"{label}: quote not found in {span.document!r}: {span.quote[:60]!r}")
    for ref in [m.document for m in bundle.media] + [p.document for p in bundle.public]:
        if ref not in texts:
            problems.append(f"extraction refers to unknown document {ref!r}")
    return problems


# ---------- API view ----------


class Evidence(BaseModel):
    document: str
    source_name: str
    url: str | None
    published_at: dt.date | None
    quote: str


class CaseSummary(BaseModel):
    slug: str
    title: str
    category: str
    court: str | None
    summary: str | None
    is_illustrative: bool
    gap_score: float | None


class GapComponentView(BaseModel):
    key: str
    label: str
    value: float
    weight: float
    contribution: float
    explanation: str


class GapView(BaseModel):
    score: float
    components: list[GapComponentView]


class TimelineEventView(BaseModel):
    date: dt.date | None
    label: str
    description: str
    phase: Phase
    court_weight: float
    media_weight: float
    evidence: Evidence | None


class JudgmentView(BaseModel):
    facts: str
    motive: str
    trigger: str
    court_reasoning: str
    outcome: str
    outcome_direction: OutcomeDirection
    legal_provisions: list[str]
    evidence: dict[str, Evidence]


class ClaimView(BaseModel):
    text: str
    verdict: ClaimVerdict
    rationale: str
    evidence: Evidence
    judgment_evidence: Evidence | None


class MediaView(BaseModel):
    document: str
    outlet: str
    url: str | None
    published_at: dt.date | None
    headline: str
    framing: Framing
    tone: float
    narratives: list[str]
    claims: list[ClaimView]


class Share(BaseModel):
    key: str
    count: int
    share: float


class ReactionView(BaseModel):
    platform: str
    text: str
    sentiment: Sentiment
    themes: list[str]


class PublicView(BaseModel):
    total: int
    sentiment: list[Share]
    themes: list[Share]
    reactions: list[ReactionView]


class SourceView(BaseModel):
    key: str
    source_type: SourceType
    source_name: str
    url: str | None
    published_at: dt.date | None


class CaseView(BaseModel):
    case: CaseSummary
    gap: GapView | None
    judgment: JudgmentView | None
    timeline: list[TimelineEventView]
    media: list[MediaView]
    public: PublicView
    sources: list[SourceView]
