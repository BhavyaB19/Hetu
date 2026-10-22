"""Refresh the Live Docket from the Supreme Court's published cause lists.

Runs from the CLI or an admin request, never from a public page. It is safe to run any
number of times: unchanged files are skipped by their hash, changed files replace their
earlier listings, and lists older than the retention window are removed.
"""

import asyncio
import datetime as dt
import hashlib
import logging
import tempfile
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from sqlalchemy.ext.asyncio import AsyncSession

from app.db import docket_repository as repo
from app.docket.parser import ParsedList, parse_lines, read_pdf_lines
from app.docket.parties import anonymise_party
from app.docket.sci import PublishedList

log = logging.getLogger(__name__)

# Courts publish in Indian Standard Time; "today" follows the courts, not the server.
IST = dt.timezone(dt.timedelta(hours=5, minutes=30))


def today_ist() -> dt.date:
    return dt.datetime.now(IST).date()


# Days of past lists kept, so "what was heard last week" still answers.
RETENTION_DAYS = 14
# A bench of five or more judges is a Constitution Bench or a larger bench.
NOTABLE_BENCH = 5


class Source(Protocol):
    async def published_lists(self) -> list[PublishedList]: ...
    async def download(self, url: str) -> bytes: ...


def parse_pdf(data: bytes) -> ParsedList:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "list.pdf"
        path.write_bytes(data)
        return parse_lines(read_pdf_lines(path))


def listing_rows(parsed: ParsedList) -> list[dict[str, object]]:
    rows = []
    for item in parsed.listings:
        rows.append(
            {
                "court": item.court,
                "bench": item.bench,
                "bench_size": len(item.bench),
                "sitting_time": item.time,
                "time_note": item.time_note,
                "heading": item.heading,
                "item_no": item.item_no,
                "case_number": item.case_number,
                "case_key": repo.case_key(item.case_number),
                "case_type": item.case_type,
                "is_criminal": "CRL" in item.case_type.upper(),
                "petitioner": anonymise_party(item.petitioner, "Petitioner"),
                "respondent": anonymise_party(item.respondent, "Respondent"),
                "advocates": item.advocates,
                "stage": item.stage,
                "notable": len(item.bench) >= NOTABLE_BENCH,
            }
        )
    return rows


@dataclass
class RefreshReport:
    checked: int = 0
    updated: int = 0
    unchanged: int = 0
    failed: int = 0
    listings: int = 0
    pruned: int = 0


async def refresh(
    session: AsyncSession,
    source: Source,
    *,
    today: dt.date | None = None,
    parse: Callable[[bytes], ParsedList | Awaitable[ParsedList]] | None = None,
) -> RefreshReport:
    today = today or today_ist()
    report = RefreshReport()
    published = [p for p in await source.published_lists() if p.list_date >= today - dt.timedelta(days=1)]
    log.info("Found %d current cause lists on the Supreme Court's site", len(published))

    for item in published:
        report.checked += 1
        try:
            data = await source.download(item.url)
            digest = hashlib.sha256(data).hexdigest()
            if await repo.cause_list_hash(session, item.url) == digest:
                await repo.touch_cause_list(session, item.url)
                report.unchanged += 1
                continue
            # PDF parsing is slow and CPU-bound; keep it off the event loop.
            parsed = parse(data) if parse else await asyncio.to_thread(parse_pdf, data)
            if isinstance(parsed, Awaitable):
                parsed = await parsed
            rows = listing_rows(parsed)
            await repo.replace_cause_list(
                session,
                repo.CauseListMeta(
                    court_code="SCI",
                    list_date=parsed.list_date or item.list_date,
                    kind=item.kind,
                    part=item.part,
                    source_url=item.url,
                    content_hash=digest,
                ),
                rows,
            )
            report.updated += 1
            report.listings += len(rows)
            log.info("Read %s %s list %s: %d matters", item.list_date, item.kind, item.part, len(rows))
        except Exception as err:  # one bad file must not stop the rest
            await session.rollback()
            report.failed += 1
            log.warning("Could not read cause list %s: %s", item.url, type(err).__name__)

    report.pruned = await repo.prune_cause_lists(session, today - dt.timedelta(days=RETENTION_DAYS))
    log.info(
        "Docket refresh: %d updated, %d unchanged, %d failed, %d matters stored",
        report.updated,
        report.unchanged,
        report.failed,
        report.listings,
    )
    return report
