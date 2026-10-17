from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.db.session import engine

router = APIRouter(tags=["health"])


class Health(BaseModel):
    status: Literal["ok"]
    db: Literal["ok", "unreachable"]


@router.get("/health", response_model=Health)
async def health() -> Health:
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        db = "ok"
    except (SQLAlchemyError, OSError):
        db = "unreachable"
    return Health(status="ok", db=db)
