"""Run the source agents for a case and assemble an unextracted case bundle.

Agents run concurrently. Each TinyFish run has its own timeout and retries
(see tinyfish.py); each agent also has an overall time limit. A missing judgment
is fatal; missing coverage is logged and the case continues without it.

Every collection is cached in fixtures/collected/<slug>.json. With
USE_FIXTURES=true, TinyFish is never called and the cache is replayed, so a demo
works without network access.
"""

import asyncio
import logging
from pathlib import Path

from app.agents.base import AgentError, BaseAgent, CaseQuery
from app.agents.judgment import JudgmentAgent
from app.agents.media import MediaAgent
from app.agents.tinyfish import TinyFish
from app.core.config import get_settings, secret
from app.schemas.bundle import CaseBundle, CaseInfo, SourceDocument

log = logging.getLogger("hetu.agents")


def cache_path(query: CaseQuery) -> Path:
    return get_settings().collected_dir / f"{query.slug}.json"


async def run_agents(query: CaseQuery, agents: list[BaseAgent], agent_timeout: float) -> CaseBundle:
    """Run agents in parallel and combine their documents into one bundle."""
    log.info("Collecting '%s' with %s", query.name, ", ".join(a.name for a in agents))
    tasks = [asyncio.create_task(asyncio.wait_for(agent.run(query), agent_timeout)) for agent in agents]
    judgment_task = next(t for t, a in zip(tasks, agents, strict=True) if a.name == "judgment")
    try:
        await judgment_task
    except Exception as err:
        # Without the judgment there is no case: stop the other agents instead of paying for them.
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        raise AgentError(f"Judgment collection failed: {err}") from err
    results = await asyncio.gather(*tasks, return_exceptions=True)

    documents: list[SourceDocument] = []
    for agent, result in zip(agents, results, strict=True):
        if isinstance(result, BaseException):
            log.warning("%s agent failed, continuing without it: %s", agent.name, result)
            continue
        log.info("%s agent: %d documents", agent.name, len(result))
        documents += result

    judgment = next(d for d in documents if d.source_type == "judgment")
    return CaseBundle(
        case=CaseInfo(slug=query.slug, title=query.name, category=query.category, court=judgment.source_name),
        documents=documents,
    )


async def collect(query: CaseQuery, refresh: bool = False) -> tuple[CaseBundle, Path]:
    """Collect a case with TinyFish and return the bundle and its cache file. A case collected
    before is reused (no TinyFish calls) unless `refresh` is set."""
    settings = get_settings()
    path = cache_path(query)

    if path.exists() and (settings.use_fixtures or not refresh):
        log.info("Using the sources collected earlier for this case")
        return CaseBundle.model_validate_json(path.read_text(encoding="utf-8")), path
    if settings.use_fixtures:
        raise AgentError(f"USE_FIXTURES is on, but this case has no cached collection ({path.name}).")

    api_key = secret(settings.tinyfish_api_key)
    if not api_key:
        raise AgentError("Set TINYFISH_API_KEY in .env to collect cases (or USE_FIXTURES=true to replay).")

    tinyfish = TinyFish(api_key, settings.tinyfish_base_url, concurrency=settings.tinyfish_concurrency)
    timeout = settings.agent_timeout_seconds
    try:
        agents: list[BaseAgent] = [JudgmentAgent(tinyfish, timeout), MediaAgent(tinyfish, timeout)]
        bundle = await run_agents(query, agents, agent_timeout=timeout * 3)
    finally:
        await tinyfish.aclose()

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(bundle.model_dump_json(indent=2), encoding="utf-8")
    log.info("Cached collection at %s", path)
    return bundle, path
