"""Database tables.

Types are portable: JSONB on Postgres, JSON elsewhere (SQLite is used in tests).
Every child row belongs to a case and is deleted with it.
"""

import datetime as dt
import uuid
from typing import Any

from sqlalchemy import JSON, Date, DateTime, Float, ForeignKey, String, Text, UniqueConstraint, func
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

    id: Mapped[uuid.UUID] = _id()
    slug: Mapped[str] = mapped_column(String(200), unique=True)
    title: Mapped[str] = mapped_column(String(300))
    category: Mapped[str] = mapped_column(String(100))
    court: Mapped[str | None] = mapped_column(String(200))
    summary: Mapped[str | None] = mapped_column(Text)
    is_illustrative: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    documents: Mapped[list["Document"]] = relationship(cascade="all, delete-orphan")
    judgment: Mapped["Judgment | None"] = relationship(cascade="all, delete-orphan")
    media: Mapped[list["MediaArticle"]] = relationship(cascade="all, delete-orphan")
    reactions: Mapped[list["PublicReaction"]] = relationship(cascade="all, delete-orphan")
    gap_score: Mapped["GapScore | None"] = relationship(cascade="all, delete-orphan")


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
