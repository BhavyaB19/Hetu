"""Settings from environment variables and the repo-root .env file."""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=(BACKEND_DIR.parent / ".env", ".env"), extra="ignore")

    # PostgreSQL is the single database across development, testing, and production.
    database_url: str = "postgresql+asyncpg://hetu:hetu@localhost:5432/hetu"
    test_database_url: str = "postgresql+asyncpg://hetu:hetu@localhost:5432/hetu_test"
    redis_url: str | None = None

    # Admin API key for protected administration endpoints.
    admin_api_key: SecretStr = SecretStr("hetu-dev-admin-key")
    # Which LLM extracts structured data. Only this provider is used, and only its key is needed.
    llm_provider: Literal["groq", "openai", "anthropic"] = "anthropic"
    anthropic_api_key: SecretStr | None = None
    anthropic_model: str = "claude-opus-5-5"
    groq_api_key: SecretStr | None = None
    groq_model: str = "openai/gpt-oss-120b"
    # free: about 8,000 tokens per minute, so long judgments are read in chunks and calls
    # are paced. developer: 250,000 tokens per minute, whole documents in one call.
    groq_plan: Literal["free", "developer"] = "free"
    openai_api_key: SecretStr | None = None
    openai_model: str = "gpt-6.1-sol"

    # TinyFish web agents collect judgments, news coverage and public comments.
    tinyfish_api_key: SecretStr | None = None
    tinyfish_base_url: str = "https://agent.tinyfish.ai"
    tinyfish_concurrency: int = 3
    agent_timeout_seconds: int = 600
    # true: never call TinyFish; replay collections cached in fixtures/collected/.
    use_fixtures: bool = False
    collected_dir: Path = BACKEND_DIR / "fixtures" / "collected"


def secret(value: SecretStr | None) -> str | None:
    """The secret's value, or None when it is unset or empty."""
    return value.get_secret_value() or None if value else None


@lru_cache
def get_settings() -> Settings:
    return Settings()
