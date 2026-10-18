"""Living platform: hearings, polls, votes, comments, reports, corrections.

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-18

Data migration policy note:
Only illustrative demo cases (is_illustrative = true) are published automatically.
All other existing or collected cases become 'draft' pending editorial and legal
review, preventing any unverified or non-anonymized scraped records from entering
the public view.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

Json = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")


def upgrade() -> None:
    # 1. Extend cases with lifecycle and procedural stage columns
    op.add_column("cases", sa.Column("status", sa.String(20), server_default="decided", nullable=False))
    op.add_column("cases", sa.Column("review_state", sa.String(20), server_default="draft", nullable=False))
    op.add_column(
        "cases", sa.Column("featured", sa.Boolean(), server_default=sa.text("false"), nullable=False)
    )
    op.add_column("cases", sa.Column("decided_on", sa.Date(), nullable=True))
    op.add_column("cases", sa.Column("next_hearing_on", sa.Date(), nullable=True))
    op.add_column("cases", sa.Column("stage", sa.String(50), nullable=True))

    op.create_check_constraint("ck_cases_status", "cases", "status IN ('ongoing', 'decided')")
    op.create_check_constraint(
        "ck_cases_review_state", "cases", "review_state IN ('draft', 'reviewed', 'published')"
    )
    op.create_index(
        "idx_cases_status_review_featured", "cases", ["status", "review_state", "featured"]
    )

    # 2. Data migration: publish illustrative demo cases; keep real collected cases in draft
    op.execute(
        sa.text(
            "UPDATE cases SET status = 'decided', review_state = 'published' "
            "WHERE is_illustrative = true"
        )
    )
    op.execute(
        sa.text(
            "UPDATE cases SET status = 'decided', review_state = 'draft' "
            "WHERE is_illustrative = false"
        )
    )

    # 3. Create hearings table
    op.create_table(
        "hearings",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("case_id", sa.Uuid(), sa.ForeignKey("cases.id", ondelete="CASCADE"), nullable=False),
        sa.Column("hearing_date", sa.Date(), nullable=False),
        sa.Column("stage", sa.String(50), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("source_name", sa.String(200), nullable=False),
        sa.Column(
            "observed_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint("case_id", "hearing_date", "source_url", name="uq_hearings_case_date_url"),
    )
    op.create_index("ix_hearings_case_id", "hearings", ["case_id"])
    op.create_index(
        "idx_hearings_case_date", "hearings", ["case_id", sa.text("hearing_date DESC")]
    )

    # 4. Create polls table
    op.create_table(
        "polls",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "case_id",
            sa.Uuid(),
            sa.ForeignKey("cases.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("status", sa.String(20), server_default="open", nullable=False),
        sa.Column(
            "opens_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("closes_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "featured", sa.Boolean(), server_default=sa.text("false"), nullable=False
        ),
        sa.CheckConstraint("status IN ('open', 'closed')", name="ck_polls_status"),
    )
    op.create_index("ix_polls_case_id", "polls", ["case_id"])

    # 5. Create votes table
    op.create_table(
        "votes",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("poll_id", sa.Uuid(), sa.ForeignKey("polls.id", ondelete="CASCADE"), nullable=False),
        sa.Column("choice", sa.String(20), nullable=False),
        sa.Column("reasons", Json, nullable=False),
        sa.Column("voter_hash", sa.String(64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint("poll_id", "voter_hash", name="uq_votes_poll_voter"),
        sa.CheckConstraint("choice IN ('agree', 'partial', 'disagree')", name="ck_votes_choice"),
    )
    op.create_index("idx_votes_poll_id", "votes", ["poll_id"])

    # 6. Create comments table
    op.create_table(
        "comments",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("poll_id", sa.Uuid(), sa.ForeignKey("polls.id", ondelete="CASCADE"), nullable=False),
        sa.Column(
            "parent_id",
            sa.Uuid(),
            sa.ForeignKey("comments.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("handle", sa.String(100), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("status", sa.String(20), server_default="visible", nullable=False),
        sa.Column("hold_reason", sa.Text(), nullable=True),
        sa.Column("stance", sa.String(20), nullable=True),
        sa.Column("themes", Json, nullable=True),
        sa.Column("upvotes", sa.Integer(), server_default="0", nullable=False),
        sa.Column("voter_hash", sa.String(64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint("id", "poll_id", name="uq_comments_id_poll"),
        sa.ForeignKeyConstraint(
            ["parent_id", "poll_id"],
            ["comments.id", "comments.poll_id"],
            ondelete="CASCADE",
            name="fk_comments_parent_same_poll",
        ),
        sa.CheckConstraint("status IN ('visible', 'held', 'removed')", name="ck_comments_status"),
        sa.CheckConstraint(
            "stance IS NULL OR stance IN ('agree', 'disagree', 'neutral')",
            name="ck_comments_stance",
        ),
    )
    op.create_index("ix_comments_poll_id", "comments", ["poll_id"])
    op.create_index("ix_comments_parent_id", "comments", ["parent_id"])
    op.create_index(
        "idx_comments_poll_status_created",
        "comments",
        ["poll_id", "status", "created_at"],
    )

    # 7. Create comment_votes table
    op.create_table(
        "comment_votes",
        sa.Column(
            "comment_id",
            sa.Uuid(),
            sa.ForeignKey("comments.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("voter_hash", sa.String(64), primary_key=True),
    )

    # 8. Create reports table
    op.create_table(
        "reports",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "comment_id",
            sa.Uuid(),
            sa.ForeignKey("comments.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("voter_hash", sa.String(64), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint("comment_id", "voter_hash", name="uq_reports_comment_voter"),
    )
    op.create_index("ix_reports_comment_id", "reports", ["comment_id"])

    # 9. Create corrections table
    op.create_table(
        "corrections",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "case_id",
            sa.Uuid(),
            sa.ForeignKey("cases.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("kind", sa.String(20), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("contact", sa.Text(), nullable=True),
        sa.Column("status", sa.String(20), server_default="pending", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "kind IN ('correction', 'takedown', 'other')", name="ck_corrections_kind"
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'reviewed', 'resolved')",
            name="ck_corrections_status",
        ),
    )
    op.create_index("ix_corrections_case_id", "corrections", ["case_id"])

    # 10. Database triggers for Postgres
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        # Poll eligibility check: case must be decided AND published
        op.execute(
            """
            CREATE OR REPLACE FUNCTION verify_poll_case_eligible() RETURNS TRIGGER AS $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM cases
                    WHERE id = NEW.case_id AND status = 'decided' AND review_state = 'published'
                ) THEN
                    RAISE EXCEPTION 'A poll can only be created for a decided, published case.';
                END IF;
                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql;
            """
        )
        op.execute(
            """
            CREATE TRIGGER trg_poll_case_eligible
            BEFORE INSERT OR UPDATE OF case_id ON polls
            FOR EACH ROW EXECUTE FUNCTION verify_poll_case_eligible();
            """
        )

        # Comment max depth 1 check: replies cannot have replies
        op.execute(
            """
            CREATE OR REPLACE FUNCTION verify_comment_max_depth() RETURNS TRIGGER AS $$
            BEGIN
                IF NEW.parent_id IS NOT NULL THEN
                    IF EXISTS (
                        SELECT 1 FROM comments WHERE id = NEW.parent_id AND parent_id IS NOT NULL
                    ) THEN
                        RAISE EXCEPTION 'Comments max depth is 1 (replies cannot have nested replies).';
                    END IF;
                END IF;
                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql;
            """
        )
        op.execute(
            """
            CREATE TRIGGER trg_comment_max_depth
            BEFORE INSERT OR UPDATE OF parent_id ON comments
            FOR EACH ROW EXECUTE FUNCTION verify_comment_max_depth();
            """
        )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("DROP TRIGGER IF EXISTS trg_comment_max_depth ON comments;")
        op.execute("DROP FUNCTION IF EXISTS verify_comment_max_depth();")
        op.execute("DROP TRIGGER IF EXISTS trg_poll_case_eligible ON polls;")
        op.execute("DROP FUNCTION IF EXISTS verify_poll_case_eligible();")

    op.drop_table("corrections")
    op.drop_table("reports")
    op.drop_table("comment_votes")
    op.drop_table("comments")
    op.drop_table("votes")
    op.drop_table("polls")
    op.drop_table("hearings")

    op.drop_index("idx_cases_status_review_featured", table_name="cases")
    op.drop_constraint("ck_cases_review_state", "cases", type_="check")
    op.drop_constraint("ck_cases_status", "cases", type_="check")

    op.drop_column("cases", "stage")
    op.drop_column("cases", "next_hearing_on")
    op.drop_column("cases", "decided_on")
    op.drop_column("cases", "featured")
    op.drop_column("cases", "review_state")
    op.drop_column("cases", "status")
