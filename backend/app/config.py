"""Settings from environment variables and the repo-root .env file."""

from functools import lru_cache
from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=(BACKEND_DIR.parent / ".env", ".env"), extra="ignore")

    # SQLite by default so the backend runs with no setup; docker-compose uses Postgres.
    database_url: str = f"sqlite+aiosqlite:///{BACKEND_DIR / 'hetu.db'}"
    anthropic_api_key: SecretStr | None = None
    anthropic_model: str = "claude-opus-5-5"


@lru_cache
def get_settings() -> Settings:
    return Settings()
