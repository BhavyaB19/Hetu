"""What the LLM returns for each extraction call (structured output schemas).

Field descriptions are sent to the model as part of the JSON schema.
"""

from pydantic import BaseModel, Field

from app.schemas.bundle import ClaimVerdict, Framing, OutcomeDirection, Phase, Sentiment
from app.services.anonymizer import Person


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


# ---------- long judgments, read in chunks (small token budgets) ----------


class LLMNote(BaseModel):
    point: str = Field(description="One finding in at most 25 words")
    quote: str = Field(description="Verbatim passage from this part of the judgment, 5 to 30 words")


class LLMChunkEvent(BaseModel):
    date: str | None = Field(description="YYYY-MM-DD, or null if not stated")
    label: str = Field(description="2 to 5 words")
    description: str = Field(description="At most 20 words")
    phase: Phase
    court_weight: float = Field(description="0 to 1: how central this event is to the court's reasoning")
    quote: str


class LLMChunkNotes(BaseModel):
    """Notes from one part of a judgment. Empty lists where the part says nothing relevant."""

    people: list[Person]
    facts: list[LLMNote] = Field(description="At most 2 facts the court accepted")
    motive: list[LLMNote] = Field(description="At most 1: the motive the court found or rejected")
    trigger: list[LLMNote] = Field(description="At most 1: the immediate trigger of the incident")
    reasoning: list[LLMNote] = Field(description="At most 2: the court's key reasoning")
    outcome: list[LLMNote] = Field(description="At most 1: the court's final decision or sentence")
    events: list[LLMChunkEvent] = Field(description="At most 2 key events in the case history")
    legal_provisions: list[str]


class LLMNoteSelection(BaseModel):
    """Ids of the notes to keep, most important first."""

    facts: list[int] = Field(description="At most 3")
    motive: list[int] = Field(description="At most 2")
    trigger: list[int] = Field(description="At most 2")
    reasoning: list[int] = Field(description="At most 3")
    outcome: list[int] = Field(description="At most 2")
    events: list[int] = Field(description="At most 6")


class LLMTimelineFromNote(BaseModel):
    note: int = Field(description="Id of the event note this entry is based on")
    date: str | None = Field(description="YYYY-MM-DD, or null")
    label: str
    description: str
    phase: Phase
    court_weight: float


class LLMJudgmentFromNotes(BaseModel):
    """The court's findings written from selected notes; evidence is given as note ids."""

    facts: str = Field(description="The facts the court accepted, in 2 to 4 sentences")
    facts_note: int
    motive: str
    motive_note: int
    trigger: str
    trigger_note: int
    court_reasoning: str = Field(description="Why the court decided as it did, in 2 to 4 sentences")
    court_reasoning_note: int
    outcome: str
    outcome_note: int
    outcome_direction: OutcomeDirection
    legal_provisions: list[str]
    timeline: list[LLMTimelineFromNote] = Field(description="3 to 8 key events, oldest first")
