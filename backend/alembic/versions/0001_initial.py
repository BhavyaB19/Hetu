"""Initial schema.

Revision ID: 0001
Revises:
Create Date: 2026-10-17
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

Json = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")


def case_fk(unique: bool = False) -> sa.Column:
    return sa.Column(
        "case_id", sa.Uuid(), sa.ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, unique=unique
    )


def upgrade() -> None:
    op.create_table(
        "cases",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("slug", sa.String(200), nullable=False, unique=True),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("category", sa.String(100), nullable=False),
        sa.Column("court", sa.String(200)),
        sa.Column("summary", sa.Text()),
        sa.Column("is_illustrative", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        "documents",
        sa.Column("id", sa.Uuid(), primary_key=True),
        case_fk(),
        sa.Column("key", sa.String(100), nullable=False),
        sa.Column("source_type", sa.String(20), nullable=False),
        sa.Column("source_name", sa.String(200), nullable=False),
        sa.Column("url", sa.Text()),
        sa.Column("published_at", sa.Date()),
        sa.Column("language", sa.String(20), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.UniqueConstraint("case_id", "key"),
        sa.UniqueConstraint("case_id", "content_hash"),
    )
    op.create_index("ix_documents_case_id", "documents", ["case_id"])
    op.create_index("ix_documents_published_at", "documents", ["published_at"])
    op.create_table(
        "judgments",
        sa.Column("id", sa.Uuid(), primary_key=True),
        case_fk(unique=True),
        sa.Column("document_key", sa.String(100), nullable=False),
        sa.Column("facts", sa.Text(), nullable=False),
        sa.Column("motive", sa.Text(), nullable=False),
        sa.Column("trigger", sa.Text(), nullable=False),
        sa.Column("court_reasoning", sa.Text(), nullable=False),
        sa.Column("outcome", sa.Text(), nullable=False),
        sa.Column("outcome_direction", sa.String(20), nullable=False),
        sa.Column("legal_provisions", Json, nullable=False),
        sa.Column("timeline", Json, nullable=False),
        sa.Column("evidence", Json, nullable=False),
    )
    op.create_table(
        "media_articles",
        sa.Column("id", sa.Uuid(), primary_key=True),
        case_fk(),
        sa.Column("document_key", sa.String(100), nullable=False),
        sa.Column("headline", sa.Text(), nullable=False),
        sa.Column("framing", sa.String(30), nullable=False),
        sa.Column("tone", sa.Float(), nullable=False),
        sa.Column("narratives", Json, nullable=False),
        sa.Column("claims", Json, nullable=False),
        sa.Column("events_mentioned", Json, nullable=False),
    )
    op.create_index("ix_media_articles_case_id", "media_articles", ["case_id"])
    op.create_table(
        "public_reactions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        case_fk(),
        sa.Column("document_key", sa.String(100), nullable=False),
        sa.Column("sentiment", sa.String(30), nullable=False),
        sa.Column("themes", Json, nullable=False),
    )
    op.create_index("ix_public_reactions_case_id", "public_reactions", ["case_id"])
    op.create_table(
        "gap_scores",
        sa.Column("id", sa.Uuid(), primary_key=True),
        case_fk(unique=True),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("components", Json, nullable=False),
        sa.Column("weights", Json, nullable=False),
        sa.Column("computed_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    for table in ("gap_scores", "public_reactions", "media_articles", "judgments", "documents", "cases"):
        op.drop_table(table)
