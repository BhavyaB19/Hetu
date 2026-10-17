"""FastAPI app: health check, case list and the case dashboard view."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated, Literal

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app import store
from app.db import engine, get_session
from app.schemas import CaseSummary, CaseView

Session = Annotated[AsyncSession, Depends(get_session)]


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    yield
    await engine.dispose()


app = FastAPI(
    title="Hetu API",
    version="0.1.0",
    description="One verdict. Three stories. One connected view.",
    lifespan=lifespan,
)


class Health(BaseModel):
    status: Literal["ok"]
    db: Literal["ok", "unreachable"]


@app.get("/health", response_model=Health)
async def health() -> Health:
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        db = "ok"
    except (SQLAlchemyError, OSError):
        db = "unreachable"
    return Health(status="ok", db=db)


@app.get("/cases", response_model=list[CaseSummary])
async def list_cases(session: Session) -> list[CaseSummary]:
    return await store.list_cases(session)


@app.get("/cases/{slug}", response_model=CaseView)
async def get_case(slug: str, session: Session) -> CaseView:
    view = await store.get_case(session, slug)
    if view is None:
        raise HTTPException(status_code=404, detail="Case not found")
    return view
