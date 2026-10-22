"""Tests run against a dedicated Postgres test database (hetu_test)."""

import os
from pathlib import Path

# Resolve test database URL
default_test_url = (
    "postgresql+asyncpg://hetu:hetu@postgres:5432/hetu_test"
    if os.environ.get("DATABASE_URL", "").find("@postgres:") != -1
    else "postgresql+asyncpg://hetu:hetu@localhost:5433/hetu_test"
)
TEST_DB_URL = os.environ.get("TEST_DATABASE_URL") or default_test_url
os.environ["DATABASE_URL"] = TEST_DB_URL
os.environ["ANTHROPIC_API_KEY"] = ""
os.environ["REDIS_URL"] = ""

import pytest  # noqa: E402
from alembic.config import Config  # noqa: E402
from sqlalchemy import text  # noqa: E402

from alembic import command  # noqa: E402
from app.schemas.bundle import CaseBundle  # noqa: E402

BACKEND_DIR = Path(__file__).resolve().parents[1]
FIXTURE = BACKEND_DIR / "fixtures" / "jan-mat-v-state.json"

ALL_TABLES = [
    "listings",
    "cause_lists",
    "tracked_matters",
    "corrections",
    "reports",
    "comment_votes",
    "comments",
    "votes",
    "polls",
    "hearings",
    "gap_scores",
    "public_reactions",
    "media_articles",
    "judgments",
    "documents",
    "cases",
]


def pytest_sessionstart(session: pytest.Session) -> None:
    """Ensure hetu_test schema is up to date via alembic upgrade head before any tests run."""
    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_section_option("alembic", "sqlalchemy.url", TEST_DB_URL)
    command.upgrade(cfg, "head")


@pytest.fixture
async def clean_database():
    """Truncates all tables before each test while preserving schema, constraints, and triggers."""
    from app.db.session import engine

    async with engine.begin() as conn:
        table_list = ", ".join(ALL_TABLES)
        await conn.execute(text(f"TRUNCATE TABLE {table_list} CASCADE;"))
    yield


@pytest.fixture
def demo() -> CaseBundle:
    return CaseBundle.model_validate_json(FIXTURE.read_text(encoding="utf-8"))
