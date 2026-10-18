"""JudgmentAgent: finds the final judgment on Indian Kanoon, then reads its exact text.

A TinyFish browser agent works through Indian Kanoon's search results to pick the
right judgment (the final, highest-court decision) and returns its document URL.
The judgment page itself is then downloaded directly and parsed, so the text is
exactly as published: evidence quotes are checked word for word against it.
"""

import datetime as dt
import logging
from urllib.parse import quote_plus

from app.agents.base import AgentError, BaseAgent, CaseQuery
from app.agents.indiankanoon import DOC_URL, parse_judgment
from app.agents.tinyfish import TinyFish, obj, string
from app.schemas.bundle import SourceDocument

log = logging.getLogger("hetu.agents.judgment")

SEARCH_URL = "https://indiankanoon.org/search/?formInput={}"

SCHEMA = obj(
    {"found": {"type": "boolean"}, "doc_url": string(nullable=True), "reason": string()},
    required=["found", "doc_url", "reason"],
)


def parse_date(value: str | None) -> dt.date | None:
    try:
        return dt.date.fromisoformat(value[:10]) if value else None
    except ValueError:
        return None


class JudgmentAgent(BaseAgent):
    name = "judgment"

    def __init__(self, tinyfish: TinyFish, timeout: float) -> None:
        self._tf = tinyfish
        self._timeout = timeout

    async def run(self, query: CaseQuery) -> list[SourceDocument]:
        court_hint = f" decided by or appealed to {query.court}" if query.court else ""
        goal = (
            f"These are Indian Kanoon search results for the case '{query.name}'{court_hint}. "
            "Find the judgment that decides this case. If there are several (for example a trial "
            "court judgment and an appeal), choose the final one: the highest court's latest decision. "
            "You may refine the search or open result pages to check, but stay on indiankanoon.org "
            "and do not copy the judgment text. Return the URL of its Indian Kanoon document page, "
            "which looks like https://indiankanoon.org/doc/<number>/, and one sentence on why it "
            "matches. If no judgment matches this case, set found to false."
        )
        result = await self._tf.run(
            SEARCH_URL.format(quote_plus(query.search_text)), goal, SCHEMA, timeout=self._timeout
        )
        url = (result.get("doc_url") or "").strip()
        if not result.get("found") or not DOC_URL.match(url):
            raise AgentError(f"No judgment found on Indian Kanoon for '{query.name}'.")

        judgment = parse_judgment(await self._tf.fetch(url))
        if len(judgment.text) < 500:
            raise AgentError(f"The Indian Kanoon page {url} has no readable judgment text.")
        log.info(
            "Found the judgment (%s), %d words",
            judgment.court or "court not stated",
            len(judgment.text.split()),
        )

        details = [d for d in (judgment.citations, judgment.bench and f"Bench: {judgment.bench}") if d]
        return [
            SourceDocument(
                key="judgment",
                source_type="judgment",
                source_name=judgment.court or "Court",
                title=" · ".join([judgment.title, *details]),
                url=url,
                published_at=judgment.decided_on,
                text=judgment.text,
            )
        ]
