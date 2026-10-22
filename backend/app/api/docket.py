"""Live Docket: read-only views of court cause lists. Never fetches from a court."""

import datetime as dt
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import docket_repository as repo
from app.db.session import get_session
from app.schemas.views import DocketHighlightsView, DocketView
from app.services.docket import today_ist

router = APIRouter(prefix="/docket", tags=["docket"])
Session = Annotated[AsyncSession, Depends(get_session)]

HIGHLIGHT_DAYS = 14


@router.get("", response_model=DocketView)
async def search_docket(
    session: Session,
    q: Annotated[str | None, Query(max_length=120, description="Case number, judge or advocate")] = None,
    date: Annotated[dt.date | None, Query(description="One listing date")] = None,
    court: Annotated[str | None, Query(max_length=60, description='e.g. "Court 4"')] = None,
    criminal: bool = False,
    notable: bool = False,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0, le=5000)] = 0,
) -> DocketView:
    today = today_ist()
    days = await repo.docket_days(session, today)
    # Without a search, show the next day the court sits rather than every future day.
    on_date = date or (days[0].list_date if days and not q else None)
    results, total = await repo.search_listings(
        session,
        from_date=today,
        on_date=on_date,
        q=q,
        court=court,
        criminal=criminal,
        notable=notable,
        limit=limit,
        offset=offset,
    )
    return DocketView(days=days, results=results, total=total, last_checked=await repo.last_checked(session))


@router.get("/highlights", response_model=DocketHighlightsView)
async def docket_highlights(session: Session) -> DocketHighlightsView:
    """Tracked matters' next hearings and the coming Constitution and larger benches."""
    today = today_ist()
    days = await repo.docket_days(session, today)
    notable, _ = await repo.search_listings(session, from_date=today, notable=True, limit=6)
    notable = [n for n in notable if n.list_date <= today + dt.timedelta(days=HIGHLIGHT_DAYS)]
    return DocketHighlightsView(
        tracked=await repo.list_tracked(session, today),
        notable=notable,
        next_day=days[0] if days else None,
        last_checked=await repo.last_checked(session),
    )
