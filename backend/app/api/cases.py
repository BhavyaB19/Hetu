from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import repository
from app.db.session import get_session
from app.schemas.views import CaseSummary, CaseView

router = APIRouter(prefix="/cases", tags=["cases"])

Session = Annotated[AsyncSession, Depends(get_session)]


@router.get("", response_model=list[CaseSummary])
async def list_cases(session: Session) -> list[CaseSummary]:
    return await repository.list_cases(session)


@router.get("/{slug}", response_model=CaseView)
async def get_case(slug: str, session: Session) -> CaseView:
    view = await repository.get_case(session, slug)
    if view is None:
        raise HTTPException(status_code=404, detail="Case not found")
    return view
