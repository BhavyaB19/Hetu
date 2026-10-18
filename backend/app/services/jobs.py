"""Background jobs: collect a case with TinyFish, then extract, score and save it.

Jobs run as in-process asyncio tasks, which is enough for a single API process.
Progress is the job's own log: log records emitted while a job runs (by the
agents and the pipeline) are captured through a context variable, so concurrent
jobs never mix their messages. Swap `start_job` for a real queue (Redis + arq)
if the API ever runs as several processes.
"""

import asyncio
import contextvars
import datetime as dt
import logging
import uuid
from dataclasses import dataclass, field
from typing import Literal

from app.agents import collect
from app.agents.base import AgentError, CaseQuery
from app.services.llm import ExtractionError
from app.services.pipeline import PipelineError, run

log = logging.getLogger("hetu.jobs")

Status = Literal["collecting", "analysing", "done", "failed"]


@dataclass
class Event:
    at: dt.datetime
    message: str
    level: Literal["info", "warning", "error"]


@dataclass
class Job:
    id: str
    query: CaseQuery
    status: Status = "collecting"
    events: list[Event] = field(default_factory=list)
    slug: str | None = None
    error: str | None = None

    def add(self, message: str, level: Literal["info", "warning", "error"] = "info") -> None:
        self.events.append(Event(dt.datetime.now(dt.UTC), message, level))


_current: contextvars.ContextVar[Job | None] = contextvars.ContextVar("current_job", default=None)
_jobs: dict[str, Job] = {}
_tasks: set[asyncio.Task] = set()


class _JobLogHandler(logging.Handler):
    """Copies log records into the job that is running in the current context."""

    def emit(self, record: logging.LogRecord) -> None:
        job = _current.get()
        if job is not None and record.levelno >= logging.INFO:
            level = (
                "error"
                if record.levelno >= logging.ERROR
                else "warning"
                if record.levelno >= logging.WARNING
                else "info"
            )
            job.add(record.getMessage(), level)


def install_log_capture() -> None:
    for name in ("hetu", "app"):
        logger = logging.getLogger(name)
        logger.setLevel(logging.INFO)
        if not any(isinstance(h, _JobLogHandler) for h in logger.handlers):
            logger.addHandler(_JobLogHandler())


def get_job(job_id: str) -> Job | None:
    return _jobs.get(job_id)


def start_job(query: CaseQuery) -> Job:
    """Start collecting a case, or return the job already running for it."""
    for job in _jobs.values():
        if job.query.slug == query.slug and job.status in ("collecting", "analysing"):
            return job
    job = Job(id=uuid.uuid4().hex[:12], query=query)
    _jobs[job.id] = job
    task = asyncio.create_task(_run(job))
    _tasks.add(task)
    task.add_done_callback(_tasks.discard)
    return job


async def _run(job: Job) -> None:
    _current.set(job)
    try:
        job.add(f"Collecting sources for '{job.query.name}' with TinyFish browser agents")
        _, path = await collect(job.query)
        job.status = "analysing"
        job.add("Sources collected. Extracting and checking evidence with the LLM")
        job.slug = await run(path, force_extract=False)
        job.status = "done"
        job.add("Done. The case is ready.")
    except (AgentError, PipelineError, ExtractionError) as err:
        _fail(job, str(err))
    except Exception as err:  # keep the job record useful even for unexpected failures
        log.exception("Job %s crashed", job.id)
        _fail(job, f"Unexpected error: {err}")


def _fail(job: Job, message: str) -> None:
    job.status = "failed"
    job.error = message
    job.add(message, "error")
