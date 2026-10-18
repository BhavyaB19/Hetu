"""API response models: what the dashboard receives."""

import datetime as dt
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.bundle import ClaimVerdict, Framing, OutcomeDirection, Phase, Sentiment, SourceType


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


class CaseRequest(BaseModel):
    name: str = Field(min_length=3, max_length=300, description='Case name, e.g. "State v. Example"')
    court: str | None = Field(default=None, max_length=200)
    category: str = "Criminal Law"


class JobEventView(BaseModel):
    at: dt.datetime
    message: str
    level: Literal["info", "warning", "error"]


class JobView(BaseModel):
    id: str
    name: str
    status: Literal["collecting", "analysing", "done", "failed"]
    slug: str | None
    error: str | None
    events: list[JobEventView]
