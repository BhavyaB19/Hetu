from fastapi import APIRouter, HTTPException

from app.agents.base import CaseQuery
from app.schemas.views import CaseRequest, JobEventView, JobView
from app.services import jobs

router = APIRouter(tags=["jobs"])


def _view(job: jobs.Job) -> JobView:
    return JobView(
        id=job.id,
        name=job.query.name,
        status=job.status,
        slug=job.slug,
        error=job.error,
        events=[JobEventView(at=e.at, message=e.message, level=e.level) for e in job.events],
    )


@router.post("/cases", response_model=JobView, status_code=202)
async def start_case(request: CaseRequest) -> JobView:
    """Start collecting and analysing a case in the background. Poll /jobs/{id} for progress."""
    query = CaseQuery(request.name.strip(), request.court or None, request.category)
    if not query.slug:
        raise HTTPException(status_code=422, detail="The case name needs letters or numbers.")
    return _view(jobs.start_job(query))


@router.get("/jobs/{job_id}", response_model=JobView)
async def get_job(job_id: str) -> JobView:
    job = jobs.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return _view(job)
