"""Case pipeline: source documents -> extraction -> anonymizer -> score -> database.

Usage (from backend/):
    python -m app.pipeline fixtures/jan-mat-v-state.json
    python -m app.pipeline my-case.json --extract

The input is a case bundle (see app.schemas.CaseBundle). If it has no extraction
yet, or --extract is given, Claude extracts it (needs ANTHROPIC_API_KEY) and the
extracted, anonymized bundle is also written next to the input so later runs
need no API calls.
"""

import argparse
import asyncio
import logging
from pathlib import Path

from app.anonymizer import Anonymizer, Person
from app.config import get_settings
from app.db import SessionLocal
from app.extraction import LLM, ClaudeLLM, classify_public, extract_judgment, extract_media
from app.schemas import CaseBundle, SourceDocument, content_hash
from app.scoring import perception_gap
from app.store import save_case

log = logging.getLogger("hetu.pipeline")

# Bundle fields that are identifiers or enums, never free text, so never anonymized.
NOT_TEXT = frozenset(
    {
        "slug",
        "key",
        "document",
        "url",
        "source_type",
        "published_at",
        "date",
        "phase",
        "framing",
        "verdict",
        "sentiment",
        "outcome_direction",
        "language",
    }
)
MAX_PARALLEL_CALLS = 4


class PipelineError(RuntimeError):
    pass


def dedupe(documents: list[SourceDocument]) -> list[SourceDocument]:
    """Drop documents whose normalized text was already seen."""
    seen: set[str] = set()
    unique = []
    for doc in documents:
        digest = content_hash(doc.text)
        if digest not in seen:
            seen.add(digest)
            unique.append(doc)
    return unique


async def extract(bundle: CaseBundle, llm: LLM) -> tuple[CaseBundle, list[Person]]:
    docs = dedupe(bundle.documents)
    judgments = [d for d in docs if d.source_type == "judgment"]
    if len(judgments) != 1:
        raise PipelineError("A case needs exactly one judgment document: the final judgment.")
    judgment_doc = judgments[0]
    limit = asyncio.Semaphore(MAX_PARALLEL_CALLS)

    async def limited(coro):
        async with limit:
            return await coro

    log.info("Extracting judgment %s", judgment_doc.key)
    judgment, people = await extract_judgment(llm, judgment_doc)

    media_docs = [d for d in docs if d.source_type == "media"]
    public_docs = [d for d in docs if d.source_type == "public"]
    log.info("Extracting %d articles and %d reactions", len(media_docs), len(public_docs))
    media_results, (public, public_people) = await asyncio.gather(
        asyncio.gather(*(limited(extract_media(llm, d, judgment, judgment_doc)) for d in media_docs)),
        limited(classify_public(llm, public_docs)),
    )
    for _, found in media_results:
        people += found
    people += public_people

    extracted = CaseBundle(
        case=bundle.case,
        documents=docs,
        judgment=judgment,
        media=[m for m, _ in media_results],
        public=public,
    )
    return extracted, people


def anonymize(bundle: CaseBundle, people: list[Person]) -> CaseBundle:
    """Replace private names and contact details in every text field."""
    anonymizer = Anonymizer()
    for person in people:
        anonymizer.register(person)
    data = anonymizer.deep(bundle.model_dump(mode="json"), skip=NOT_TEXT)
    return CaseBundle.model_validate(data)


async def process(bundle: CaseBundle, llm: LLM | None, force_extract: bool = False) -> CaseBundle:
    people: list[Person] = []
    if force_extract or not bundle.is_extracted:
        if llm is None:
            raise PipelineError("This case needs extraction: set ANTHROPIC_API_KEY in .env.")
        bundle, people = await extract(bundle, llm)
    return anonymize(bundle, people)


async def run(path: Path, force_extract: bool) -> None:
    settings = get_settings()
    key = settings.anthropic_api_key
    llm = ClaudeLLM(key.get_secret_value(), settings.anthropic_model) if key else None

    raw = CaseBundle.model_validate_json(path.read_text(encoding="utf-8"))
    bundle = await process(raw, llm, force_extract)
    if not raw.is_extracted or force_extract:
        out = path.with_name(f"{path.stem}.extracted.json")
        out.write_text(bundle.model_dump_json(indent=2), encoding="utf-8")
        log.info("Wrote extracted bundle to %s", out)

    gap = perception_gap(bundle)
    async with SessionLocal() as session:
        await save_case(session, bundle, gap)
    log.info("Saved %s: Perception Gap Index %.1f", bundle.case.slug, gap.score)


def main() -> None:
    parser = argparse.ArgumentParser(description="Process case bundles into the database.")
    parser.add_argument("files", nargs="+", type=Path)
    parser.add_argument("--extract", action="store_true", help="Re-extract even if already extracted")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    for path in args.files:
        asyncio.run(run(path, args.extract))


if __name__ == "__main__":
    main()
