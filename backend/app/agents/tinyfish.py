"""Client for the TinyFish Agent API (https://docs.tinyfish.ai/agent-api/reference).

A run is started with POST /v1/automation/run-async and polled with
GET /v1/runs/{id} until it is COMPLETED, FAILED or CANCELLED. A run that exceeds
our timeout is cancelled with POST /v1/runs/{id}/cancel.

Every start URL is checked against the site's robots.txt first. Goals tell the
agent never to log in, solve CAPTCHAs or get past paywalls.
"""

import asyncio
import logging
import urllib.robotparser
from typing import Any
from urllib.parse import urlsplit

import httpx

from app.agents.base import AgentError

log = logging.getLogger("hetu.tinyfish")

USER_AGENT = "HetuResearchBot/0.1 (research and education)"
TERMINAL = {"COMPLETED", "FAILED", "CANCELLED"}
RETRYABLE_HTTP = {429, 500, 502, 503, 504}
MAX_ATTEMPTS = 3

# Appended to every goal.
GROUND_RULES = (
    " Only read content that is publicly visible. Never log in, create accounts, solve CAPTCHAs "
    "or get past paywalls; if one blocks you, return what is visible."
)

Schema = dict[str, Any]


def obj(properties: Schema, required: list[str] | None = None) -> Schema:
    """A JSON Schema object node, using only keywords TinyFish's output_schema accepts."""
    return {"type": "object", "properties": properties, "required": required or list(properties)}


def string(nullable: bool = False) -> Schema:
    return {"type": "string", "nullable": True} if nullable else {"type": "string"}


class RobotsChecker:
    """Caches robots.txt per host. Unreachable robots.txt files are treated as allow-all."""

    def __init__(self, http: httpx.AsyncClient) -> None:
        self._http = http
        self._parsers: dict[str, urllib.robotparser.RobotFileParser] = {}

    async def allows(self, url: str) -> bool:
        parts = urlsplit(url)
        host = f"{parts.scheme}://{parts.netloc}"
        if host not in self._parsers:
            parser = urllib.robotparser.RobotFileParser()
            try:
                res = await self._http.get(f"{host}/robots.txt", headers={"User-Agent": USER_AGENT})
                parser.parse(res.text.splitlines() if res.status_code == 200 else [])
            except httpx.HTTPError:
                parser.parse([])
            self._parsers[host] = parser
        return self._parsers[host].can_fetch(USER_AGENT, url)


class TinyFish:
    def __init__(
        self,
        api_key: str,
        base_url: str = "https://agent.tinyfish.ai",
        *,
        concurrency: int = 3,
        poll_seconds: float = 3.0,
        http: httpx.AsyncClient | None = None,
        robots: RobotsChecker | None = None,
    ) -> None:
        self._http = http or httpx.AsyncClient(timeout=60)
        self._api = base_url.rstrip("/")
        self._headers = {"X-API-Key": api_key}
        self._slots = asyncio.Semaphore(concurrency)
        self._poll_seconds = poll_seconds
        self._robots = robots or RobotsChecker(self._http)

    async def aclose(self) -> None:
        await self._http.aclose()

    async def allows(self, url: str) -> bool:
        return await self._robots.allows(url)

    async def fetch(self, url: str) -> str:
        """Download a public page directly (no browser agent), respecting robots.txt."""
        if not await self.allows(url):
            raise AgentError(f"robots.txt disallows automated access to {url}")
        try:
            res = await self._http.get(url, headers={"User-Agent": USER_AGENT}, follow_redirects=True)
            res.raise_for_status()
        except httpx.HTTPError as err:
            raise AgentError(f"Could not download {url}: {err}") from err
        return res.text

    async def run(self, url: str, goal: str, schema: Schema, *, timeout: float) -> dict[str, Any]:
        """Run one browser agent and return its structured result."""
        if not await self.allows(url):
            raise AgentError(f"robots.txt disallows automated access to {url}")
        body = {"url": url, "goal": goal + GROUND_RULES, "output_schema": schema, "browser_profile": "lite"}
        async with self._slots:
            log.info("Browser agent opened %s", urlsplit(url).netloc)
            for attempt in range(1, MAX_ATTEMPTS + 1):
                run_id = await self._start(body)
                try:
                    run = await asyncio.wait_for(self._wait(run_id, urlsplit(url).netloc), timeout)
                except TimeoutError:
                    await self._cancel(run_id)
                    raise AgentError(f"TinyFish run timed out after {timeout:.0f}s on {url}") from None
                except asyncio.CancelledError:
                    # Our side gave up (another agent failed, or the job stopped): stop the remote
                    # run too, so it does not keep spending credits.
                    await asyncio.shield(self._cancel(run_id))
                    raise
                if run["status"] == "COMPLETED":
                    return run.get("result") or {}
                error = run.get("error") or {}
                if error.get("category") == "SYSTEM_FAILURE" and attempt < MAX_ATTEMPTS:
                    await asyncio.sleep(error.get("retry_after") or 2**attempt)
                    continue
                raise AgentError(f"TinyFish run {run['status']} on {url}: {error.get('message') or error}")
        raise AgentError("unreachable")

    async def _start(self, body: Schema) -> str:
        res = await self._request("POST", "/v1/automation/run-async", json=body)
        if res.get("error"):
            raise AgentError(f"TinyFish rejected the run: {res['error']}")
        return res["run_id"]

    async def _wait(self, run_id: str, site: str) -> dict[str, Any]:
        """Poll until the run ends, logging each new step the browser agent takes."""
        seen: set[str] = set()
        while True:
            run = await self._request("GET", f"/v1/runs/{run_id}")
            for step in run.get("steps") or []:
                key = step.get("id") or step.get("timestamp") or str(step)
                action = step.get("action") or step.get("purpose")
                if key not in seen and action:
                    seen.add(key)
                    log.info("%s: %s", site, action)
            if run["status"] in TERMINAL:
                return run
            await asyncio.sleep(self._poll_seconds)

    async def _cancel(self, run_id: str) -> None:
        try:
            await self._request("POST", f"/v1/runs/{run_id}/cancel")
        except (AgentError, httpx.HTTPError):
            log.warning("Could not cancel TinyFish run %s", run_id)

    async def _request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        """HTTP call with exponential backoff on rate limits, server errors and network errors."""
        for attempt in range(1, MAX_ATTEMPTS + 1):
            try:
                res = await self._http.request(method, self._api + path, headers=self._headers, **kwargs)
            except httpx.TransportError as err:
                if attempt == MAX_ATTEMPTS:
                    raise AgentError(f"Cannot reach TinyFish: {err}") from err
                await asyncio.sleep(2**attempt)
                continue
            if res.status_code in RETRYABLE_HTTP and attempt < MAX_ATTEMPTS:
                await asyncio.sleep(float(res.headers.get("retry-after", 2**attempt)))
                continue
            if res.status_code >= 400:
                raise AgentError(f"TinyFish {method} {path} failed ({res.status_code}): {res.text[:300]}")
            return res.json()
        raise AgentError("unreachable")
