"""Tests run against a throwaway SQLite database; no Postgres or API key needed."""

import os
import tempfile
from pathlib import Path

DB_PATH = Path(tempfile.mkdtemp()) / "test.db"
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{DB_PATH}"
os.environ["ANTHROPIC_API_KEY"] = ""

import pytest  # noqa: E402

from app.schemas.bundle import CaseBundle  # noqa: E402

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "jan-mat-v-state.json"


@pytest.fixture
def demo() -> CaseBundle:
    return CaseBundle.model_validate_json(FIXTURE.read_text(encoding="utf-8"))
