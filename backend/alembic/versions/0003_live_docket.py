"""Live Docket: cause lists fetched from the Supreme Court of India, their listings, and
matters a curator tracks.

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-22
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

Json = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")


def upgrade() -> None:
    op.create_table(
        "cause_lists",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("court_code", sa.String(20), nullable=False),
        sa.Column("list_date", sa.Date(), nullable=False),
        sa.Column("kind", sa.String(20), nullable=False),
        sa.Column("part", sa.String(40), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=False, unique=True),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("item_count", sa.Integer(), nullable=False),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("kind IN ('daily', 'advance')", name="ck_cause_lists_kind"),
    )
    op.create_index("idx_cause_lists_date", "cause_lists", ["list_date"])

    op.create_table(
        "listings",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "cause_list_id", sa.Uuid(), sa.ForeignKey("cause_lists.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("list_date", sa.Date(), nullable=False),
        sa.Column("kind", sa.String(20), nullable=False),
        sa.Column("court", sa.String(60), nullable=True),
        sa.Column("bench", Json, nullable=False),
        sa.Column("bench_size", sa.Integer(), nullable=False),
        sa.Column("sitting_time", sa.String(20), nullable=True),
        sa.Column("time_note", sa.String(120), nullable=True),
        sa.Column("heading", sa.String(200), nullable=True),
        sa.Column("item_no", sa.String(12), nullable=False),
        sa.Column("case_number", sa.String(160), nullable=False),
        sa.Column("case_key", sa.String(160), nullable=False),
        sa.Column("case_type", sa.String(80), nullable=False),
        sa.Column("is_criminal", sa.Boolean(), nullable=False),
        sa.Column("petitioner", sa.Text(), nullable=False),
        sa.Column("respondent", sa.Text(), nullable=False),
        sa.Column("advocates", Json, nullable=False),
        sa.Column("stage", sa.String(80), nullable=True),
        sa.Column("notable", sa.Boolean(), nullable=False),
    )
    op.create_index("ix_listings_cause_list_id", "listings", ["cause_list_id"])
    op.create_index("idx_listings_date_court", "listings", ["list_date", "court"])
    op.create_index("idx_listings_case_key", "listings", ["case_key"])
    op.create_index("idx_listings_notable_date", "listings", ["notable", "list_date"])

    op.create_table(
        "tracked_matters",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("case_key", sa.String(160), nullable=False, unique=True),
        sa.Column("case_number", sa.String(160), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("case_id", sa.Uuid(), sa.ForeignKey("cases.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_tracked_matters_case_id", "tracked_matters", ["case_id"])


def downgrade() -> None:
    op.drop_index("ix_tracked_matters_case_id", table_name="tracked_matters")
    op.drop_table("tracked_matters")
    op.drop_index("idx_listings_notable_date", table_name="listings")
    op.drop_index("idx_listings_case_key", table_name="listings")
    op.drop_index("idx_listings_date_court", table_name="listings")
    op.drop_index("ix_listings_cause_list_id", table_name="listings")
    op.drop_table("listings")
    op.drop_index("idx_cause_lists_date", table_name="cause_lists")
    op.drop_table("cause_lists")
