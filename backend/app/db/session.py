"""Async SQLAlchemy engine and session factory."""

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import get_settings

is_test = "test" in get_settings().database_url
engine = create_async_engine(
    get_settings().database_url,
    pool_pre_ping=True,
    poolclass=NullPool if is_test else None,
)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def get_session() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency yielding one session per request."""
    async with SessionLocal() as session:
        yield session
