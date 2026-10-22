"""The Supreme Court of India's published cause lists.

The court publishes each day's cause lists, and advance lists for the coming days, as plain
PDF files on api.sci.gov.in at predictable addresses:

    https://api.sci.gov.in/jonew/cl/<YYYY-MM-DD>/<part>.pdf          daily lists
    https://api.sci.gov.in/jonew/cl/advance/<YYYY-MM-DD>/M_J.pdf     advance list

Hetu reads only those files. The main website (www.sci.gov.in) refuses self-identified
bots, so Hetu does not use it at all, and never its CAPTCHA-protected search. The file
server's robots.txt is checked before every request, requests are spaced out, and each one
names Hetu honestly. A date or part that has not been published answers with a non-PDF
page, which is simply skipped.
"""

import asyncio
import datetime as dt
import re
from dataclasses import dataclass
from urllib import robotparser
from urllib.parse import urlsplit

import httpx

FILE_HOST = "https://api.sci.gov.in"
USER_AGENT = "HetuResearchBot/0.1 (public-interest research on Indian court listings)"
# Seconds between requests to the court's server.
POLITE_DELAY = 2.0
# Daily list file codes seen on the court's site: main ("M_J"), chamber, registrar, supplementary,
# and the codes used on regular-hearing days.
DAILY_PARTS = ("M_J_1", "M_J_2", "M_J_3", "M_C_1", "M_R_1", "M_S_1", "F_J_1", "R_J_1", "L_J_1")
DAILY_DAYS_AHEAD = 2  # daily lists appear a day or two before the sitting
ADVANCE_DAYS_AHEAD = 14

_PDF_LINK = re.compile(
    r"https://api\.sci\.gov\.in/jonew/cl/(?:(advance)/)?(\d{4}-\d{2}-\d{2})/([A-Za-z0-9_]+)\.pdf"
)


@dataclass(frozen=True)
class PublishedList:
    url: str
    list_date: dt.date
    kind: str  # "daily" or "advance"
    part: str  # file code, e.g. "M_J_1"


def list_url(list_date: dt.date, kind: str, part: str) -> str:
    folder = "advance/" if kind == "advance" else ""
    return f"{FILE_HOST}/jonew/cl/{folder}{list_date.isoformat()}/{part}.pdf"


def find_lists(page_html: str) -> list[PublishedList]:
    """Every cause-list PDF linked from a page, once each, in date order."""
    seen: dict[str, PublishedList] = {}
    for match in _PDF_LINK.finditer(page_html):
        advance, date, part = match.groups()
        seen[match.group(0)] = PublishedList(
            url=match.group(0),
            list_date=dt.date.fromisoformat(date),
            kind="advance" if advance else "daily",
            part=part,
        )
    return sorted(seen.values(), key=lambda p: (p.list_date, p.kind, p.part))


def candidate_lists(today: dt.date) -> list[PublishedList]:
    """Every address a current list could be at: today and the next days, each known part."""
    found = [
        PublishedList(list_url(day, "daily", part), day, "daily", part)
        for offset in range(DAILY_DAYS_AHEAD + 1)
        for day in [today + dt.timedelta(days=offset)]
        for part in DAILY_PARTS
    ]
    found += [
        PublishedList(list_url(day, "advance", "M_J"), day, "advance", "M_J")
        for offset in range(1, ADVANCE_DAYS_AHEAD + 1)
        for day in [today + dt.timedelta(days=offset)]
    ]
    # The court does not sit on Sundays.
    return [p for p in found if p.list_date.weekday() != 6]


class SciSource:
    """Downloads from the court's file server, one request at a time, within robots.txt."""

    def __init__(self, today: dt.date, client: httpx.AsyncClient | None = None) -> None:
        self._today = today
        self._client = client or httpx.AsyncClient(
            headers={"User-Agent": USER_AGENT}, timeout=httpx.Timeout(60.0), follow_redirects=True
        )
        self._robots: dict[str, robotparser.RobotFileParser] = {}
        self._last_request = 0.0
        self._files: dict[str, bytes] = {}

    async def close(self) -> None:
        await self._client.aclose()

    async def _allowed(self, url: str) -> bool:
        host = urlsplit(url)
        origin = f"{host.scheme}://{host.netloc}"
        if origin not in self._robots:
            parser = robotparser.RobotFileParser()
            response = await self._get(f"{origin}/robots.txt", check_robots=False)
            if response.status_code in (401, 403):
                parser.disallow_all = True  # a server that refuses us its rules refuses us
            else:
                # A missing robots.txt means everything is allowed.
                parser.parse(response.text.splitlines() if response.status_code == 200 else [])
            self._robots[origin] = parser
        return self._robots[origin].can_fetch(USER_AGENT, url)

    async def _get(self, url: str, *, check_robots: bool = True) -> httpx.Response:
        if check_robots and not await self._allowed(url):
            raise PermissionError(f"robots.txt does not allow fetching {url}")
        wait = POLITE_DELAY - (asyncio.get_running_loop().time() - self._last_request)
        if wait > 0:
            await asyncio.sleep(wait)
        try:
            return await self._client.get(url)
        finally:
            self._last_request = asyncio.get_running_loop().time()

    async def published_lists(self) -> list[PublishedList]:
        """The candidate addresses that hold a real PDF; their contents are kept for `download`."""
        found = []
        for candidate in candidate_lists(self._today):
            response = await self._get(candidate.url)
            if response.status_code == 200 and response.content.startswith(b"%PDF"):
                self._files[candidate.url] = response.content
                found.append(candidate)
        return found

    async def download(self, url: str) -> bytes:
        if url in self._files:
            return self._files.pop(url)
        response = await self._get(url)
        response.raise_for_status()
        if not response.content.startswith(b"%PDF"):
            raise ValueError(f"Not a PDF: {url}")
        return response.content
