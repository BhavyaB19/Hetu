"""Live Docket storage: cause lists, their listings, and tracked matters.

A date can have both an advance list (published days ahead, tentative) and the daily list
(final). Readers see the daily list when it exists and the advance list otherwise.
"""

import datetime as dt
import re
import uuid
from collections.abc import Sequence
from dataclasses import dataclass

from sqlalchemy import Integer, String, cast, delete, distinct, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import models
from app.schemas.views import DocketDayView, ListingView, TrackedMatterView


def case_key(case_number: str) -> str:
    """'SLP(Crl) No. 7857/2022' and 'slp crl 7857/2022' both become 'slpcrl78572022'."""
    text = re.sub(r"\bnos?\b\.?", " ", case_number.lower())
    return re.sub(r"[^a-z0-9]", "", text)


@dataclass
class CauseListMeta:
    court_code: str
    list_date: dt.date
    kind: str
    part: str
    source_url: str
    content_hash: str


async def cause_list_hash(session: AsyncSession, source_url: str) -> str | None:
    return await session.scalar(
        select(models.CauseList.content_hash).where(models.CauseList.source_url == source_url)
    )


async def replace_cause_list(
    session: AsyncSession, meta: CauseListMeta, listings: Sequence[dict[str, object]]
) -> None:
    """Store a cause list and its listings, replacing an earlier copy of the same file."""
    existing = await session.scalar(
        select(models.CauseList).where(models.CauseList.source_url == meta.source_url)
    )
    if existing is None:
        existing = models.CauseList(source_url=meta.source_url)
        session.add(existing)
    else:
        await session.execute(delete(models.Listing).where(models.Listing.cause_list_id == existing.id))
    existing.court_code = meta.court_code
    existing.list_date = meta.list_date
    existing.kind = meta.kind
    existing.part = meta.part
    existing.content_hash = meta.content_hash
    existing.item_count = len(listings)
    existing.fetched_at = dt.datetime.now(dt.UTC)
    await session.flush()
    session.add_all(
        models.Listing(cause_list_id=existing.id, list_date=meta.list_date, kind=meta.kind, **row)
        for row in listings
    )
    await session.commit()


async def touch_cause_list(session: AsyncSession, source_url: str) -> None:
    """Record that an unchanged list was checked again."""
    row = await session.scalar(select(models.CauseList).where(models.CauseList.source_url == source_url))
    if row is not None:
        row.fetched_at = dt.datetime.now(dt.UTC)
        await session.commit()


async def prune_cause_lists(session: AsyncSession, before: dt.date) -> int:
    result = await session.execute(delete(models.CauseList).where(models.CauseList.list_date < before))
    await session.commit()
    return result.rowcount or 0


async def last_checked(session: AsyncSession) -> dt.datetime | None:
    return await session.scalar(select(func.max(models.CauseList.fetched_at)))


def _daily_dates():
    return select(models.CauseList.list_date).where(models.CauseList.kind == "daily").distinct()


def _effective():
    """Daily listings, plus advance listings for dates that have no daily list yet."""
    return or_(models.Listing.kind == "daily", models.Listing.list_date.not_in(_daily_dates()))


def _view(row: models.Listing, source_url: str) -> ListingView:
    return ListingView(
        list_date=row.list_date,
        tentative=row.kind == "advance",
        court=row.court,
        bench=list(row.bench),
        bench_size=row.bench_size,
        sitting_time=row.sitting_time,
        time_note=row.time_note,
        item_no=row.item_no,
        case_number=row.case_number,
        case_type=row.case_type,
        is_criminal=row.is_criminal,
        petitioner=row.petitioner,
        respondent=row.respondent,
        advocates=list(row.advocates),
        stage=row.stage,
        notable=row.notable,
        source_url=source_url,
    )


def _ordered(query):
    item = cast(func.split_part(models.Listing.item_no, ".", 1), Integer)
    return query.order_by(models.Listing.list_date, models.Listing.court, item, models.Listing.item_no)


async def docket_days(session: AsyncSession, from_date: dt.date) -> list[DocketDayView]:
    rows = await session.execute(
        select(
            models.Listing.list_date,
            func.bool_and(models.Listing.kind == "advance"),
            func.count(),
            func.count(distinct(models.Listing.court)),
        )
        .where(_effective(), models.Listing.list_date >= from_date)
        .group_by(models.Listing.list_date)
        .order_by(models.Listing.list_date)
    )
    return [
        DocketDayView(list_date=d, tentative=bool(tentative), matters=n, courts=courts)
        for d, tentative, n, courts in rows
    ]


async def search_listings(
    session: AsyncSession,
    *,
    from_date: dt.date,
    on_date: dt.date | None = None,
    q: str | None = None,
    court: str | None = None,
    criminal: bool = False,
    notable: bool = False,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[ListingView], int]:
    on_or_after = models.Listing.list_date >= from_date
    conditions = [_effective(), models.Listing.list_date == on_date if on_date else on_or_after]
    if court:
        conditions.append(models.Listing.court == court)
    if criminal:
        conditions.append(models.Listing.is_criminal.is_(True))
    if notable:
        conditions.append(models.Listing.notable.is_(True))
    if q and q.strip():
        term = f"%{q.strip()}%"
        options = [
            models.Listing.case_number.ilike(term),
            models.Listing.petitioner.ilike(term),
            models.Listing.respondent.ilike(term),
            cast(models.Listing.bench, String).ilike(term),
            cast(models.Listing.advocates, String).ilike(term),
        ]
        key = case_key(q)
        if len(key) >= 3:
            options.append(models.Listing.case_key.contains(key))
        conditions.append(or_(*options))

    total = await session.scalar(select(func.count()).select_from(models.Listing).where(*conditions)) or 0
    rows = await session.execute(
        _ordered(
            select(models.Listing, models.CauseList.source_url)
            .join(models.CauseList, models.CauseList.id == models.Listing.cause_list_id)
            .where(*conditions)
        )
        .limit(limit)
        .offset(offset)
    )
    return [_view(listing, url) for listing, url in rows], total


async def next_listing(session: AsyncSession, key: str, from_date: dt.date) -> ListingView | None:
    row = (
        await session.execute(
            _ordered(
                select(models.Listing, models.CauseList.source_url)
                .join(models.CauseList, models.CauseList.id == models.Listing.cause_list_id)
                .where(_effective(), models.Listing.case_key == key, models.Listing.list_date >= from_date)
            ).limit(1)
        )
    ).first()
    return _view(row[0], row[1]) if row else None


async def list_tracked(session: AsyncSession, from_date: dt.date) -> list[TrackedMatterView]:
    rows = await session.execute(
        select(models.TrackedMatter, models.Case.slug)
        .outerjoin(models.Case, models.Case.id == models.TrackedMatter.case_id)
        .order_by(models.TrackedMatter.created_at)
    )
    return [
        TrackedMatterView(
            id=str(tracked.id),
            case_number=tracked.case_number,
            title=tracked.title,
            note=tracked.note,
            case_slug=slug,
            next_listing=await next_listing(session, tracked.case_key, from_date),
        )
        for tracked, slug in rows
    ]


async def add_tracked(
    session: AsyncSession, case_number: str, title: str, note: str | None, case_slug: str | None
) -> models.TrackedMatter:
    key = case_key(case_number)
    tracked = await session.scalar(select(models.TrackedMatter).where(models.TrackedMatter.case_key == key))
    if tracked is None:
        tracked = models.TrackedMatter(case_key=key)
        session.add(tracked)
    tracked.case_number = case_number.strip()
    tracked.title = title.strip()
    tracked.note = note
    linked = select(models.Case.id).where(models.Case.slug == case_slug)
    tracked.case_id = await session.scalar(linked) if case_slug else None
    await session.commit()
    return tracked


async def remove_tracked(session: AsyncSession, tracked_id: uuid.UUID) -> bool:
    result = await session.execute(delete(models.TrackedMatter).where(models.TrackedMatter.id == tracked_id))
    await session.commit()
    return bool(result.rowcount)
