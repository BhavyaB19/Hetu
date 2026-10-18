"""MediaAgent: finds news coverage of a case and reads each article and its public comments.

Step 1 searches Bing News for the case. Step 2 visits each article in parallel and
extracts the article body plus reader comments that are publicly visible on the
page. Comments become `public` documents; commenter names and handles are never
requested, and the anonymizer removes any that appear inside comment text.
"""

import asyncio
import logging
from urllib.parse import quote_plus

from app.agents.base import AgentError, BaseAgent, CaseQuery
from app.agents.judgment import parse_date
from app.agents.tinyfish import TinyFish, obj, string
from app.schemas.bundle import SourceDocument

log = logging.getLogger("hetu.agents.media")

SEARCH_URL = "https://www.bing.com/news/search?q={}"
MAX_ARTICLES = 6
MAX_COMMENTS_PER_ARTICLE = 15

SEARCH_SCHEMA = obj(
    {
        "articles": {
            "type": "array",
            "maxItems": MAX_ARTICLES,
            "items": obj(
                {
                    "headline": string(),
                    "url": string(),
                    "outlet": string(),
                    "published_date": string(nullable=True),
                },
                required=["headline", "url", "outlet"],
            ),
        }
    }
)

ARTICLE_SCHEMA = obj(
    {
        "headline": string(),
        "outlet": string(),
        "published_date": string(nullable=True),
        "body": string(),
        "comments": {
            "type": "array",
            "maxItems": MAX_COMMENTS_PER_ARTICLE,
            "items": obj(
                {"text": string(), "posted_date": string(nullable=True)},
                required=["text"],
            ),
        },
    },
    required=["headline", "outlet", "body", "comments"],
)


class MediaAgent(BaseAgent):
    name = "media"

    def __init__(self, tinyfish: TinyFish, timeout: float) -> None:
        self._tf = tinyfish
        self._timeout = timeout

    async def run(self, query: CaseQuery) -> list[SourceDocument]:
        hits = await self._search(query)
        if not hits:
            raise AgentError(f"No news coverage found for '{query.name}'.")
        log.info("Found %d news articles; reading them in parallel", len(hits))
        results = await asyncio.gather(*(self._read(query, hit) for hit in hits), return_exceptions=True)

        docs: list[SourceDocument] = []
        for i, (hit, result) in enumerate(zip(hits, results, strict=True), start=1):
            if isinstance(result, BaseException):
                log.warning("Skipped article %s: %s", hit["url"], result)
                continue
            found = self._documents(i, hit, result)
            if found:
                log.info("Read %s: %d public comments", found[0].source_name, len(found) - 1)
            docs += found
        if not any(d.source_type == "media" for d in docs):
            raise AgentError("Found news results but could not read any article.")
        return docs

    async def _search(self, query: CaseQuery) -> list[dict]:
        goal = (
            f"From these news search results, list up to {MAX_ARTICLES} news articles about the Indian "
            f"court case '{query.name}': the incident, investigation, trial, verdict or appeal. Prefer "
            "different outlets and different stages of the case. Give each article's own URL on the "
            "publisher's site, not a search-engine redirect. Skip videos, live blogs and pages that are "
            "not about this case."
        )
        result = await self._tf.run(
            SEARCH_URL.format(quote_plus(query.search_text)), goal, SEARCH_SCHEMA, timeout=self._timeout
        )
        seen: set[str] = set()
        hits = []
        for hit in result.get("articles", []):
            url = hit.get("url", "")
            if url.startswith("http") and url not in seen and await self._tf.allows(url):
                seen.add(url)
                hits.append(hit)
        return hits[:MAX_ARTICLES]

    async def _read(self, query: CaseQuery, hit: dict) -> dict:
        goal = (
            f"This is a news article about the court case '{query.name}'. Return its headline, outlet "
            "name, publication date as YYYY-MM-DD, and the full article body exactly as written. Then "
            "open the reader comments if the page has a public comment section, and return up to "
            f"{MAX_COMMENTS_PER_ARTICLE} comments with their text and posted date if shown. "
            "Do not return commenter names, usernames or profile links. If there are no public "
            "comments, return an empty list."
        )
        return await self._tf.run(hit["url"], goal, ARTICLE_SCHEMA, timeout=self._timeout)

    @staticmethod
    def _documents(i: int, hit: dict, article: dict) -> list[SourceDocument]:
        body = (article.get("body") or "").strip()
        if not body:
            return []
        outlet = article.get("outlet") or hit["outlet"]
        published = parse_date(article.get("published_date") or hit.get("published_date"))
        docs = [
            SourceDocument(
                key=f"media-{i}",
                source_type="media",
                source_name=outlet,
                title=article.get("headline") or hit["headline"],
                url=hit["url"],
                published_at=published,
                text=body,
            )
        ]
        for j, comment in enumerate(article.get("comments") or [], start=1):
            text = (comment.get("text") or "").strip()
            if text:
                docs.append(
                    SourceDocument(
                        key=f"public-{i}-{j}",
                        source_type="public",
                        source_name=f"Reader comments, {outlet}",
                        url=hit["url"],
                        published_at=parse_date(comment.get("posted_date")) or published,
                        text=text,
                    )
                )
        return docs
