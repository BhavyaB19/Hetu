"""Database tables.

Types are portable: JSONB on Postgres, JSON elsewhere (SQLite is used in tests).
Every child row belongs to a case and is deleted with it.
"""

import datetime as dt
import uuid
from typing import Any

from sqlalchemy import (
    JSON,
    CheckConstraint,
    Date,
    DateTime,
    Float,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

Json = JSON().with_variant(JSONB(), "postgresql")


class Base(DeclarativeBase):
    pass


def _id() -> Mapped[uuid.UUID]:
    return mapped_column(primary_key=True, default=uuid.uuid4)


def _case_fk() -> Mapped[uuid.UUID]:
    return mapped_column(ForeignKey("cases.id", ondelete="CASCADE"), index=True)


class Case(Base):
    __tablename__ = "cases"
    __table_args__ = (
        CheckConstraint("status IN ('ongoing', 'decided')", name="ck_cases_status"),
        CheckConstraint(
            "review_state IN ('draft', 'reviewed', 'published')",
            name="ck_cases_review_state",
        ),
        Index("idx_cases_status_review_featured", "status", "review_state", "featured"),
    )

    id: Mapped[uuid.UUID] = _id()
    slug: Mapped[str] = mapped_column(String(200), unique=True)
    title: Mapped[str] = mapped_column(String(300))
    category: Mapped[str] = mapped_column(String(100))
    court: Mapped[str | None] = mapped_column(String(200))
    summary: Mapped[str | None] = mapped_column(Text)
    is_illustrative: Mapped[bool] = mapped_column(default=False)
    status: Mapped[str] = mapped_column(String(20), default="decided", server_default="decided")
    review_state: Mapped[str] = mapped_column(String(20), default="draft", server_default="draft")
    featured: Mapped[bool] = mapped_column(default=False, server_default="false")
    decided_on: Mapped[dt.date | None] = mapped_column(Date, nullable=True)
    next_hearing_on: Mapped[dt.date | None] = mapped_column(Date, nullable=True)
    stage: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    documents: Mapped[list["Document"]] = relationship(cascade="all, delete-orphan")
    judgment: Mapped["Judgment | None"] = relationship(cascade="all, delete-orphan")
    media: Mapped[list["MediaArticle"]] = relationship(cascade="all, delete-orphan")
    reactions: Mapped[list["PublicReaction"]] = relationship(cascade="all, delete-orphan")
    gap_score: Mapped["GapScore | None"] = relationship(cascade="all, delete-orphan")
    hearings: Mapped[list["Hearing"]] = relationship(cascade="all, delete-orphan")
    poll: Mapped["Poll | None"] = relationship(cascade="all, delete-orphan", uselist=False)
    corrections: Mapped[list["Correction"]] = relationship()


class Document(Base):
    """A source text (anonymized). Evidence quotes point into these."""

    __tablename__ = "documents"
    __table_args__ = (
        UniqueConstraint("case_id", "key"),
        UniqueConstraint("case_id", "content_hash"),
    )

    id: Mapped[uuid.UUID] = _id()
    case_id: Mapped[uuid.UUID] = _case_fk()
    key: Mapped[str] = mapped_column(String(100))
    source_type: Mapped[str] = mapped_column(String(20))
    source_name: Mapped[str] = mapped_column(String(200))
    url: Mapped[str | None] = mapped_column(Text)
    published_at: Mapped[dt.date | None] = mapped_column(Date, index=True)
    language: Mapped[str] = mapped_column(String(20))
    text: Mapped[str] = mapped_column(Text)
    content_hash: Mapped[str] = mapped_column(String(64))


class Judgment(Base):
    __tablename__ = "judgments"

    id: Mapped[uuid.UUID] = _id()
    case_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"), unique=True)
    document_key: Mapped[str] = mapped_column(String(100))
    facts: Mapped[str] = mapped_column(Text)
    motive: Mapped[str] = mapped_column(Text)
    trigger: Mapped[str] = mapped_column(Text)
    court_reasoning: Mapped[str] = mapped_column(Text)
    outcome: Mapped[str] = mapped_column(Text)
    outcome_direction: Mapped[str] = mapped_column(String(20))
    legal_provisions: Mapped[list[str]] = mapped_column(Json)
    timeline: Mapped[list[dict[str, Any]]] = mapped_column(Json)
    evidence: Mapped[dict[str, Any]] = mapped_column(Json)


class MediaArticle(Base):
    __tablename__ = "media_articles"

    id: Mapped[uuid.UUID] = _id()
    case_id: Mapped[uuid.UUID] = _case_fk()
    document_key: Mapped[str] = mapped_column(String(100))
    headline: Mapped[str] = mapped_column(Text)
    framing: Mapped[str] = mapped_column(String(30))
    tone: Mapped[float] = mapped_column(Float)
    narratives: Mapped[list[str]] = mapped_column(Json)
    claims: Mapped[list[dict[str, Any]]] = mapped_column(Json)
    events_mentioned: Mapped[list[int]] = mapped_column(Json)


class PublicReaction(Base):
    """One public post or comment. No author, handle or profile is stored."""

    __tablename__ = "public_reactions"

    id: Mapped[uuid.UUID] = _id()
    case_id: Mapped[uuid.UUID] = _case_fk()
    document_key: Mapped[str] = mapped_column(String(100))
    sentiment: Mapped[str] = mapped_column(String(30))
    themes: Mapped[list[str]] = mapped_column(Json)


class GapScore(Base):
    __tablename__ = "gap_scores"

    id: Mapped[uuid.UUID] = _id()
    case_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"), unique=True)
    score: Mapped[float] = mapped_column(Float)
    components: Mapped[list[dict[str, Any]]] = mapped_column(Json)
    weights: Mapped[dict[str, float]] = mapped_column(Json)
    computed_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Hearing(Base):
    """Procedural hearings for ongoing cases in the Live Docket."""

    __tablename__ = "hearings"
    __table_args__ = (
        UniqueConstraint("case_id", "hearing_date", "source_url", name="uq_hearings_case_date_url"),
        Index("idx_hearings_case_date", "case_id", text("hearing_date DESC")),
    )

    id: Mapped[uuid.UUID] = _id()
    case_id: Mapped[uuid.UUID] = _case_fk()
    hearing_date: Mapped[dt.date] = mapped_column(Date)
    stage: Mapped[str] = mapped_column(String(50))
    summary: Mapped[str] = mapped_column(Text)
    source_url: Mapped[str] = mapped_column(Text)
    source_name: Mapped[str] = mapped_column(String(200))
    observed_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Poll(Base):
    """First-party public polls. Allowed only on decided, published cases."""

    __tablename__ = "polls"
    __table_args__ = (CheckConstraint("status IN ('open', 'closed')", name="ck_polls_status"),)

    id: Mapped[uuid.UUID] = _id()
    case_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("cases.id", ondelete="CASCADE"), unique=True, index=True
    )
    question: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="open", server_default="open")
    opens_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    closes_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    featured: Mapped[bool] = mapped_column(default=False, server_default="false")

    case: Mapped["Case"] = relationship(back_populates="poll")
    votes: Mapped[list["Vote"]] = relationship(cascade="all, delete-orphan")
    comments: Mapped[list["Comment"]] = relationship(cascade="all, delete-orphan")


class Vote(Base):
    """Anonymous verified poll vote keyed by voter_hash."""

    __tablename__ = "votes"
    __table_args__ = (
        UniqueConstraint("poll_id", "voter_hash", name="uq_votes_poll_voter"),
        CheckConstraint("choice IN ('agree', 'partial', 'disagree')", name="ck_votes_choice"),
        Index("idx_votes_poll_id", "poll_id"),
    )

    id: Mapped[uuid.UUID] = _id()
    poll_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("polls.id", ondelete="CASCADE"), index=True)
    choice: Mapped[str] = mapped_column(String(20))
    reasons: Mapped[list[str]] = mapped_column(Json)
    voter_hash: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Comment(Base):
    """Public comment thread under a poll. Max reply depth is 1."""

    __tablename__ = "comments"
    __table_args__ = (
        UniqueConstraint("id", "poll_id", name="uq_comments_id_poll"),
        ForeignKeyConstraint(
            ["parent_id", "poll_id"],
            ["comments.id", "comments.poll_id"],
            ondelete="CASCADE",
            name="fk_comments_parent_same_poll",
        ),
        CheckConstraint("status IN ('visible', 'held', 'removed')", name="ck_comments_status"),
        CheckConstraint(
            "stance IS NULL OR stance IN ('agree', 'disagree', 'neutral')",
            name="ck_comments_stance",
        ),
        Index("idx_comments_poll_status_created", "poll_id", "status", "created_at"),
    )

    id: Mapped[uuid.UUID] = _id()
    poll_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("polls.id", ondelete="CASCADE"), index=True)
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("comments.id", ondelete="CASCADE"), nullable=True, index=True
    )
    handle: Mapped[str] = mapped_column(String(100))
    body: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="visible", server_default="visible")
    hold_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    stance: Mapped[str | None] = mapped_column(String(20), nullable=True)
    themes: Mapped[list[str] | None] = mapped_column(Json, nullable=True)
    upvotes: Mapped[int] = mapped_column(default=0, server_default="0")
    voter_hash: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    replies: Mapped[list["Comment"]] = relationship(
        "Comment",
        cascade="all, delete-orphan",
        foreign_keys=[parent_id],
        order_by="Comment.created_at.asc()",
    )


class CommentVote(Base):
    """Tracks upvotes per comment and voter_hash."""

    __tablename__ = "comment_votes"

    comment_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("comments.id", ondelete="CASCADE"), primary_key=True
    )
    voter_hash: Mapped[str] = mapped_column(String(64), primary_key=True)


class Report(Base):
    """User report against a comment."""

    __tablename__ = "reports"
    __table_args__ = (UniqueConstraint("comment_id", "voter_hash", name="uq_reports_comment_voter"),)

    id: Mapped[uuid.UUID] = _id()
    comment_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("comments.id", ondelete="CASCADE"), index=True)
    voter_hash: Mapped[str] = mapped_column(String(64))
    reason: Mapped[str] = mapped_column(Text)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Correction(Base):
    """Public reader correction or takedown request."""

    __tablename__ = "corrections"
    __table_args__ = (
        CheckConstraint("kind IN ('correction', 'takedown', 'other')", name="ck_corrections_kind"),
        CheckConstraint("status IN ('pending', 'reviewed', 'resolved')", name="ck_corrections_status"),
    )

    id: Mapped[uuid.UUID] = _id()
    case_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("cases.id", ondelete="SET NULL"), nullable=True, index=True
    )
    kind: Mapped[str] = mapped_column(String(20))
    message: Mapped[str] = mapped_column(Text)
    contact: Mapped[str | None] = mapped_column(Text, nullable=True)  # Personal data: never expose or log
    status: Mapped[str] = mapped_column(String(20), default="pending", server_default="pending")
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

