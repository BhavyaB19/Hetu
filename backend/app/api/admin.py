"""Admin API: protected endpoints for case ingestion, review, and job tracking.

Requires X-Admin-Key header validated via constant-time comparison.
Keys and unvetted content are never logged.
"""

import logging
import secrets
import uuid
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.base import CaseQuery
from app.core.config import Settings, get_settings, secret
from app.core.limiter import limiter
from app.db import docket_repository, repository
from app.db.session import SessionLocal, get_session
from app.docket.sci import SciSource
from app.schemas.views import (
    CasePatchRequest,
    CaseRequest,
    CaseSummary,
    CaseView,
    DocketRefreshView,
    JobEventView,
    JobView,
    TrackedMatterRequest,
    TrackedMatterView,
)
from app.services import docket, jobs

log = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])
Session = Annotated[AsyncSession, Depends(get_session)]


def verify_admin_key(
    x_admin_key: Annotated[str | None, Header()] = None,
    settings: Annotated[Settings, Depends(get_settings)] = None,
) -> str:
    """Validate X-Admin-Key using constant-time comparison."""
    expected = secret(settings.admin_api_key) if settings else None
    if not x_admin_key or not expected or not secrets.compare_digest(x_admin_key, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized: invalid or missing admin key",
        )
    return x_admin_key


AdminAuth = Annotated[str, Depends(verify_admin_key)]


def _job_view(job: jobs.Job) -> JobView:
    return JobView(
        id=job.id,
        name=job.query.name,
        status=job.status,
        slug=job.slug,
        error=job.error,
        events=[JobEventView(at=e.at, message=e.message, level=e.level) for e in job.events],
    )


@router.post("/cases", response_model=JobView, status_code=status.HTTP_202_ACCEPTED)
@limiter.limit("10/minute")
async def start_case(
    request: Request,
    body: CaseRequest,
    _: AdminAuth,
) -> JobView:
    """Start background collection and analysis for a case. Admin only."""
    query = CaseQuery(body.name.strip(), body.court or None, body.category)
    if not query.slug:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="The case name needs letters or numbers.",
        )
    return _job_view(jobs.start_job(query))


@router.get("/jobs/{job_id}", response_model=JobView)
async def get_job(job_id: str, _: AdminAuth) -> JobView:
    """Fetch status and log events for a background job. Admin only."""
    job = jobs.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return _job_view(job)


@router.get("/cases", response_model=list[CaseSummary])
async def list_cases_admin(session: Session, _: AdminAuth) -> list[CaseSummary]:
    """List all cases including draft and reviewed cases. Admin only."""
    return await repository.list_cases_admin(session)


@router.get("/cases/{slug}/preview", response_model=CaseView)
async def preview_case(slug: str, session: Session, _: AdminAuth) -> CaseView:
    """Preview case dashboard regardless of review state. Admin only."""
    view = await repository.get_case_admin(session, slug)
    if view is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")
    return view


@router.patch("/cases/{slug}", response_model=CaseSummary)
async def patch_case(
    slug: str,
    patch: CasePatchRequest,
    session: Session,
    _: AdminAuth,
) -> CaseSummary:
    """Update publication state, status, or featured flag. Admin only."""
    case = await repository.patch_case(
        session,
        slug=slug,
        review_state=patch.review_state,
        featured=patch.featured,
        status=patch.status,
    )
    if case is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")
    return repository._summary(case)


async def _refresh_docket() -> None:
    source = SciSource(docket.today_ist())
    try:
        async with SessionLocal() as session:
            await docket.refresh(session, source)
    except Exception as err:  # a background task has nowhere else to report
        log.warning("Docket refresh failed: %s", type(err).__name__)
    finally:
        await source.close()


@router.post("/docket/refresh", response_model=DocketRefreshView, status_code=status.HTTP_202_ACCEPTED)
@limiter.limit("2/minute")
async def refresh_docket(request: Request, background: BackgroundTasks, _: AdminAuth) -> DocketRefreshView:
    """Fetch the Supreme Court's current cause lists in the background. Admin only."""
    background.add_task(_refresh_docket)
    return DocketRefreshView(
        started=True,
        message="Reading the Supreme Court's cause lists. This takes a few minutes.",
    )


@router.get("/docket/tracked", response_model=list[TrackedMatterView])
async def list_tracked(session: Session, _: AdminAuth) -> list[TrackedMatterView]:
    return await docket_repository.list_tracked(session, docket.today_ist())


@router.post("/docket/tracked", response_model=TrackedMatterView, status_code=status.HTTP_201_CREATED)
@limiter.limit("30/minute")
async def track_matter(
    request: Request, body: TrackedMatterRequest, session: Session, _: AdminAuth
) -> TrackedMatterView:
    """Follow a Supreme Court matter by its case number. Admin only."""
    if len(docket_repository.case_key(body.case_number)) < 4:
        raise HTTPException(status_code=422, detail='Give a case number such as "SLP(Crl) No. 7857/2022".')
    tracked = await docket_repository.add_tracked(
        session, body.case_number, body.title, body.note, body.case_slug
    )
    views = await docket_repository.list_tracked(session, docket.today_ist())
    return next(v for v in views if v.id == str(tracked.id))


@router.delete("/docket/tracked/{tracked_id}", status_code=status.HTTP_204_NO_CONTENT)
async def untrack_matter(tracked_id: uuid.UUID, session: Session, _: AdminAuth) -> None:
    if not await docket_repository.remove_tracked(session, tracked_id):
        raise HTTPException(status_code=404, detail="Tracked matter not found")
