"""FastAPI application: wires the routers to the database lifecycle."""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.api import admin, cases, health, polls
from app.core.config import get_settings, secret
from app.core.limiter import limiter
from app.db.session import engine
from app.services.jobs import install_log_capture

log = logging.getLogger("hetu.main")


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    if secret(settings.admin_api_key) == "hetu-dev-admin-key":
        log.warning(
            "SECURITY WARNING: ADMIN_API_KEY is set to the default development value. "
            "Set a strong random key before deploying to production!"
        )
    install_log_capture()
    yield
    await engine.dispose()


app = FastAPI(
    title="Hetu API",
    version="0.1.0",
    description="One verdict. Three stories. One connected view.",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.include_router(health.router)
app.include_router(cases.router)
app.include_router(admin.router)
app.include_router(polls.router)
