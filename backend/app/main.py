"""FastAPI application: wires the routers to the database lifecycle."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api import cases, health, jobs
from app.db.session import engine
from app.services.jobs import install_log_capture


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    install_log_capture()
    yield
    await engine.dispose()


app = FastAPI(
    title="Hetu API",
    version="0.1.0",
    description="One verdict. Three stories. One connected view.",
    lifespan=lifespan,
)
app.include_router(health.router)
app.include_router(cases.router)
app.include_router(jobs.router)
