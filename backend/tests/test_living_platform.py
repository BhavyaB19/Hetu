"""Tests for living platform schema, triggers, constraints, and visibility rules.

Verifies:
1. Poll case eligibility trigger (polls allowed ONLY on decided & published cases)
2. Comment max depth limit of 1
3. Comment reply parent same poll constraint
4. Unique vote constraint per (poll_id, voter_hash) and vote upsert
5. Enum check constraints for all status, choice, stance, and kind fields
6. Public vs admin repository query visibility
7. Reversible migration on a separate throwaway PostgreSQL database
"""

import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.ext.asyncio import create_async_engine

from app.db import models, repository
from app.db.session import SessionLocal, engine

pytestmark = pytest.mark.usefixtures("clean_database")


async def _create_test_case(
    session,
    slug: str = "test-case",
    status: str = "decided",
    review_state: str = "published",
    is_illustrative: bool = False,
) -> models.Case:
    case = models.Case(
        slug=slug,
        title=f"Title {slug}",
        category="criminal",
        court="Delhi High Court",
        summary="Summary",
        status=status,
        review_state=review_state,
        is_illustrative=is_illustrative,
    )
    session.add(case)
    await session.commit()
    await session.refresh(case)
    return case


# --- 1. Trigger existence test ---


async def test_poll_trigger_exists():
    """Fail if the poll-eligibility trigger is missing in PostgreSQL."""
    async with engine.connect() as conn:
        res = await conn.execute(
            text(
                "SELECT tgname FROM pg_trigger "
                "JOIN pg_class ON pg_trigger.tgrelid = pg_class.oid "
                "WHERE tgname = 'trg_poll_case_eligible' AND relname = 'polls';"
            )
        )
        row = res.scalar()
        assert row == "trg_poll_case_eligible", "Trigger 'trg_poll_case_eligible' is missing on polls table"


# --- 2. Poll eligibility trigger tests ---


async def test_poll_cannot_be_created_on_ongoing_case():
    """A poll cannot be opened for an ongoing case."""
    async with SessionLocal() as session:
        case = await _create_test_case(
            session, slug="ongoing-case", status="ongoing", review_state="published"
        )
        poll = models.Poll(case_id=case.id, question="Do you agree with the outcome?")
        session.add(poll)
        with pytest.raises(DBAPIError) as exc_info:
            await session.commit()
        assert "A poll can only be created for a decided, published case" in str(exc_info.value)


async def test_poll_cannot_be_created_on_draft_case():
    """A poll cannot be opened for a draft case."""
    async with SessionLocal() as session:
        case = await _create_test_case(session, slug="draft-case", status="decided", review_state="draft")
        poll = models.Poll(case_id=case.id, question="Do you agree with the outcome?")
        session.add(poll)
        with pytest.raises(DBAPIError) as exc_info:
            await session.commit()
        assert "A poll can only be created for a decided, published case" in str(exc_info.value)


async def test_poll_created_successfully_on_decided_published_case():
    """A poll succeeds when case is both decided and published."""
    async with SessionLocal() as session:
        case = await _create_test_case(session, slug="valid-case", status="decided", review_state="published")
        poll = models.Poll(case_id=case.id, question="Do you agree with the outcome?")
        session.add(poll)
        await session.commit()
        await session.refresh(poll)
        assert poll.id is not None
        assert poll.status == "open"


# --- 3. Poll visibility & un-publishing tests ---


async def test_unpublishing_case_hides_poll_from_public_queries():
    """Un-publishing a case hides its poll from public queries while remaining in admin queries."""
    async with SessionLocal() as session:
        case = await _create_test_case(session, slug="pub-case", status="decided", review_state="published")
        poll = await repository.create_poll(session, case.id, "Was the sentence fair?")

        # Visible in public queries initially
        public_polls = await repository.list_polls(session)
        assert any(p.id == poll.id for p in public_polls)
        pub_poll = await repository.get_poll(session, poll.id)
        assert pub_poll is not None

        # Un-publish the case to 'draft'
        case.review_state = "draft"
        await session.commit()

        # Hidden from public queries
        public_polls_after = await repository.list_polls(session)
        assert not any(p.id == poll.id for p in public_polls_after)
        pub_poll_after = await repository.get_poll(session, poll.id)
        assert pub_poll_after is None

        # Still visible in admin queries
        admin_polls = await repository.list_polls_admin(session)
        assert any(p.id == poll.id for p in admin_polls)
        admin_poll = await repository.get_poll_admin(session, poll.id)
        assert admin_poll is not None


# --- 4. Vote uniqueness and upserting tests ---


async def test_unique_vote_per_poll_and_voter():
    """Votes are unique per (poll_id, voter_hash), and record_vote upserts."""
    async with SessionLocal() as session:
        case = await _create_test_case(session, slug="vote-case", status="decided", review_state="published")
        poll = await repository.create_poll(session, case.id, "Question?")
        voter_hash = "voter_abc_123"

        # First vote
        v1 = await repository.record_vote(session, poll.id, "agree", ["fair_reasoning"], voter_hash)
        assert v1.choice == "agree"

        # Attempting raw duplicate insert raises IntegrityError
        async with session.begin_nested():
            v_dup = models.Vote(
                poll_id=poll.id, choice="disagree", reasons=["bias"], voter_hash=voter_hash
            )
            session.add(v_dup)
            with pytest.raises(IntegrityError):
                await session.flush()

        # Calling record_vote updates the existing row
        v2 = await repository.record_vote(session, poll.id, "disagree", ["harsh"], voter_hash)
        assert v2.id == v1.id
        assert v2.choice == "disagree"
        assert v2.reasons == ["harsh"]

        # Results aggregation reflects updated vote
        results = await repository.get_poll_results(session, poll.id)
        assert results["total_votes"] == 1
        assert results["disagree"] == 1
        assert results["agree"] == 0


# --- 5. Comment reply depth and same poll constraint tests ---


async def test_comment_max_depth_1():
    """A comment reply cannot have its own reply (depth capped at 1)."""
    async with SessionLocal() as session:
        case = await _create_test_case(session, slug="comment-depth-case")
        poll = await repository.create_poll(session, case.id, "Question?")

        # Root comment (depth 0)
        c1 = await repository.create_comment(session, poll.id, "Anon", "Root comment", "hash1")

        # Reply comment (depth 1)
        c2 = await repository.create_comment(
            session, poll.id, "Anon2", "Reply to root", "hash2", parent_id=c1.id
        )
        assert c2.parent_id == c1.id

        # Nested reply (depth 2) raises trigger error
        c3 = models.Comment(
            poll_id=poll.id,
            parent_id=c2.id,
            handle="Anon3",
            body="Reply to reply",
            voter_hash="hash3",
        )
        session.add(c3)
        with pytest.raises(DBAPIError) as exc_info:
            await session.commit()
        assert "Comments max depth is 1" in str(exc_info.value)


async def test_comment_reply_must_belong_to_same_poll():
    """A comment reply cannot reference a parent belonging to a different poll."""
    async with SessionLocal() as session:
        case_a = await _create_test_case(session, slug="case-a")
        poll_a = await repository.create_poll(session, case_a.id, "Question A?")
        c_a = await repository.create_comment(session, poll_a.id, "AnonA", "Comment on A", "hashA")

        case_b = await _create_test_case(session, slug="case-b")
        poll_b = await repository.create_poll(session, case_b.id, "Question B?")

        # Attempt to create comment under Poll B with parent under Poll A
        cross_comment = models.Comment(
            poll_id=poll_b.id,
            parent_id=c_a.id,
            handle="AnonB",
            body="Cross-poll reply attempt",
            voter_hash="hashB",
        )
        session.add(cross_comment)
        with pytest.raises(IntegrityError):
            await session.commit()


# --- 6. Enum CHECK constraints tests ---


@pytest.mark.parametrize(
    ("table", "field", "invalid_val"),
    [
        ("cases", "status", "pending"),
        ("cases", "review_state", "archived"),
        ("polls", "status", "paused"),
        ("votes", "choice", "maybe"),
        ("comments", "status", "banned"),
        ("comments", "stance", "unsure"),
        ("corrections", "kind", "lawsuit"),
        ("corrections", "status", "closed"),
    ],
)
async def test_enum_check_constraints_reject_invalid_values(table, field, invalid_val):
    """Database check constraints reject invalid enum strings."""
    async with SessionLocal() as session:
        case = await _create_test_case(session, slug=f"enum-case-{table}-{field}")
        poll = await repository.create_poll(session, case.id, "Question?")
        comment = await repository.create_comment(session, poll.id, "User", "Text", "vh")

        if table == "cases":
            setattr(case, field, invalid_val)
        elif table == "polls":
            setattr(poll, field, invalid_val)
        elif table == "votes":
            vote = models.Vote(poll_id=poll.id, choice=invalid_val, reasons=[], voter_hash="vh_inv")
            session.add(vote)
        elif table == "comments":
            setattr(comment, field, invalid_val)
        elif table == "corrections":
            correction = models.Correction(case_id=case.id, kind=invalid_val, message="msg")
            if field == "status":
                correction.kind = "correction"
                correction.status = invalid_val
            session.add(correction)

        with pytest.raises(IntegrityError):
            await session.commit()


# --- 7. Reversibility test on throwaway database ---


async def test_migration_reversibility_on_throwaway_database():
    """Verify alembic upgrade head and downgrade -1 on a dedicated throwaway database."""
    import os
    from pathlib import Path

    from alembic.config import Config

    from alembic import command

    rev_db_name = f"hetu_rev_{uuid.uuid4().hex[:8]}"

    # Connect to postgres maintenance DB to create & drop throwaway DB
    maint_url = os.environ.get("DATABASE_URL", "").replace("/hetu_test", "/postgres")
    maint_engine = create_async_engine(maint_url, isolation_level="AUTOCOMMIT")

    async with maint_engine.connect() as conn:
        await conn.execute(text(f"CREATE DATABASE {rev_db_name} OWNER hetu;"))

    rev_url = os.environ.get("DATABASE_URL", "").replace("/hetu_test", f"/{rev_db_name}")

    backend_dir = Path(__file__).resolve().parents[1]
    cfg = Config(str(backend_dir / "alembic.ini"))
    cfg.set_section_option("alembic", "sqlalchemy.url", rev_url)

    import asyncio

    try:
        # Upgrade to head
        await asyncio.to_thread(command.upgrade, cfg, "head")

        # Downgrade back to initial revision (downgrade -1)
        await asyncio.to_thread(command.downgrade, cfg, "-1")

        # Re-upgrade to head to verify re-application is clean
        await asyncio.to_thread(command.upgrade, cfg, "head")
    finally:
        await maint_engine.dispose()
        # Drop throwaway database
        drop_engine = create_async_engine(maint_url, isolation_level="AUTOCOMMIT")
        async with drop_engine.connect() as conn:
            await conn.execute(text(f"DROP DATABASE IF EXISTS {rev_db_name};"))
        await drop_engine.dispose()
