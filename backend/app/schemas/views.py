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
    status: str = "decided"
    review_state: str = "draft"
    featured: bool = False
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
    status: Literal["ongoing", "decided"] = "decided"


class CasePatchRequest(BaseModel):
    review_state: Literal["draft", "reviewed", "published"] | None = None
    featured: bool | None = None
    status: Literal["ongoing", "decided"] | None = None


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


class PollView(BaseModel):
    id: str
    case_id: str
    case_slug: str | None = None
    case_title: str | None = None
    question: str
    status: Literal["open", "closed"]
    opens_at: dt.datetime
    closes_at: dt.datetime | None = None
    featured: bool = False
    total_votes: int = 0


class VoteRequest(BaseModel):
    choice: Literal["agree", "partial", "disagree"]
    reasons: list[str] = Field(default_factory=list)


class VoteView(BaseModel):
    choice: Literal["agree", "partial", "disagree"]
    reasons: list[str]
    updated_at: dt.datetime


class ReasonTally(BaseModel):
    reason: str
    count: int


class PollResultsView(BaseModel):
    poll_id: str
    total_votes: int
    agree: int
    partial: int
    disagree: int
    agree_pct: float
    partial_pct: float
    disagree_pct: float
    top_reasons: list[ReasonTally]

    def __getitem__(self, item: str) -> object:
        return getattr(self, item)


class CommentRequest(BaseModel):
    body: str = Field(min_length=3, max_length=800)
    parent_id: str | None = None
    handle: str | None = Field(default=None, max_length=50)


class CommentView(BaseModel):
    id: str
    poll_id: str
    parent_id: str | None = None
    handle: str
    body: str
    status: str
    stance: str | None = None
    upvotes: int = 0
    created_at: dt.datetime
    replies: list["CommentView"] = Field(default_factory=list)


class CommentVoteView(BaseModel):
    upvoted: bool
    upvotes: int


class ReportRequest(BaseModel):
    reason: str = Field(min_length=3, max_length=500)


class ReportView(BaseModel):
    status: str = "reported"
    comment_id: str


class CorrectionView(BaseModel):
    id: str
    case_id: str | None
    kind: str
    message: str
    status: str
    created_at: dt.datetime


class HomeCounters(BaseModel):
    total_cases: int
    total_votes: int
    total_comments: int
    avg_perception_gap: float | None


class HomeSummaryView(BaseModel):
    featured_cases: list[CaseSummary]
    poll_of_the_week: PollView | None
    counters: HomeCounters


class ListingView(BaseModel):
    """One matter in a court's cause list. Private parties appear only by their role."""

    list_date: dt.date
    tentative: bool = Field(description="True for advance lists: likely, not confirmed.")
    court: str | None
    bench: list[str]
    bench_size: int
    sitting_time: str | None
    time_note: str | None
    item_no: str
    case_number: str
    case_type: str
    is_criminal: bool
    petitioner: str
    respondent: str
    advocates: list[str]
    stage: str | None
    notable: bool
    source_url: str


class DocketDayView(BaseModel):
    list_date: dt.date
    tentative: bool
    matters: int
    courts: int


class DocketView(BaseModel):
    days: list[DocketDayView]
    results: list[ListingView]
    total: int
    last_checked: dt.datetime | None


class TrackedMatterView(BaseModel):
    id: str
    case_number: str
    title: str
    note: str | None
    case_slug: str | None
    next_listing: ListingView | None


class DocketHighlightsView(BaseModel):
    tracked: list[TrackedMatterView]
    notable: list[ListingView]
    next_day: DocketDayView | None
    last_checked: dt.datetime | None


class TrackedMatterRequest(BaseModel):
    case_number: str = Field(min_length=4, max_length=160, description='e.g. "SLP(Crl) No. 7857/2022"')
    title: str = Field(min_length=3, max_length=200, description="Public title; no private names.")
    note: str | None = Field(default=None, max_length=1000)
    case_slug: str | None = None


class DocketRefreshView(BaseModel):
    started: bool
    message: str
