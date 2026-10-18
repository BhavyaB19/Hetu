"""Case pipeline: source documents -> extraction -> anonymizer -> score -> database.

The input is a case bundle (see app.schemas.bundle.CaseBundle). If it has no
extraction yet, or a re-extract is requested, the configured LLM extracts it (needs
an LLM API key) and the extracted, anonymized bundle is also written next to
the input so later runs need no API calls. Run it with `python -m app.cli`.
"""

import asyncio
import hashlib
import logging
import re
from pathlib import Path

from pydantic import BaseModel

from app.core.config import get_settings
from app.db.repository import save_case
from app.db.session import SessionLocal
from app.schemas.bundle import CaseBundle, JudgmentExtraction, PublicExtraction, SourceDocument, content_hash
from app.services.anonymizer import Anonymizer, Person
from app.services.extraction import classify_public, extract_judgment, extract_media
from app.services.llm import LLM, make_llm
from app.services.scoring import perception_gap

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


class JudgmentCheckpoint(BaseModel):
    """The court's findings, saved as soon as they are written. Reading a long judgment is the
    slowest step, so a re-run after a crash or a failed article starts from the articles."""

    content_hash: str
    judgment: JudgmentExtraction
    people: list[Person]


async def extract(
    bundle: CaseBundle, llm: LLM, checkpoint: Path | None = None, reuse_checkpoint: bool = True
) -> tuple[CaseBundle, list[Person]]:
    docs = dedupe(bundle.documents)
    judgments = [d for d in docs if d.source_type == "judgment"]
    if len(judgments) != 1:
        raise PipelineError("A case needs exactly one judgment document: the final judgment.")
    judgment_doc = judgments[0]
    limit = asyncio.Semaphore(MAX_PARALLEL_CALLS)

    async def limited(coro):
        async with limit:
            return await coro

    judgment, people = await _judgment_findings(llm, judgment_doc, checkpoint, reuse_checkpoint)

    media_docs = [d for d in docs if d.source_type == "media"]
    public_docs = [d for d in docs if d.source_type == "public"]
    log.info(
        "Checking %d articles against the judgment and classifying %d public comments",
        len(media_docs),
        len(public_docs),
    )
    media_outcomes, public_outcome = await asyncio.gather(
        asyncio.gather(
            *(limited(extract_media(llm, d, judgment, judgment_doc)) for d in media_docs),
            return_exceptions=True,
        ),
        limited(classify_public(llm, public_docs)),
        return_exceptions=True,
    )
    # One unreadable article or reaction batch should not sink the whole case.
    media_results = []
    for doc, outcome in zip(media_docs, media_outcomes, strict=True):
        if isinstance(outcome, BaseException):
            log.warning("Left out the article from %s: %s", doc.source_name, outcome)
            continue
        media_results.append(outcome)
        people += outcome[1]
    if isinstance(public_outcome, BaseException):
        log.warning("Left out public reactions: %s", public_outcome)
        public: list[PublicExtraction] = []
    else:
        public, public_people = public_outcome
        people += public_people

    extracted = CaseBundle(
        case=bundle.case,
        documents=docs,
        judgment=judgment,
        media=[m for m, _ in media_results],
        public=public,
    )
    return extracted, people


async def _judgment_findings(
    llm: LLM, judgment_doc: SourceDocument, checkpoint: Path | None, reuse: bool
) -> tuple[JudgmentExtraction, list[Person]]:
    digest = content_hash(judgment_doc.text)
    if checkpoint and reuse and checkpoint.exists():
        saved = JudgmentCheckpoint.model_validate_json(checkpoint.read_text(encoding="utf-8"))
        if saved.content_hash == digest:
            log.info("Reusing the court's findings saved earlier for this judgment")
            return saved.judgment, saved.people

    log.info("Extracting the court's findings from the judgment")
    judgment, people = await extract_judgment(llm, judgment_doc)
    if checkpoint:
        saved = JudgmentCheckpoint(content_hash=digest, judgment=judgment, people=people)
        checkpoint.write_text(saved.model_dump_json(indent=2), encoding="utf-8")
        log.info("Saved the court's findings, so a re-run starts from the articles")
    return judgment, people


def anonymize(bundle: CaseBundle, people: list[Person]) -> CaseBundle:
    """Replace private names and contact details in every text field."""
    anonymizer = Anonymizer()
    for person in people:
        anonymizer.register(person)
    data = anonymizer.deep(bundle.model_dump(mode="json"), skip=NOT_TEXT)
    case = data["case"]
    if case["title"] != bundle.case.title:
        # The title named someone, so the slug (a URL) would too: rebuild it from the anonymized
        # title, with a short hash of the original so different cases stay distinct.
        digest = hashlib.sha1(bundle.case.slug.encode()).hexdigest()[:6]
        case["slug"] = f"{re.sub(r'[^a-z0-9]+', '-', case['title'].lower()).strip('-')}-{digest}"
    return CaseBundle.model_validate(data)


async def process(
    bundle: CaseBundle, llm: LLM | None, force_extract: bool = False, checkpoint: Path | None = None
) -> CaseBundle:
    people: list[Person] = []
    if force_extract or not bundle.is_extracted:
        if llm is None:
            raise PipelineError(
                "This case needs extraction: set the API key for your LLM_PROVIDER in .env "
                "(GROQ_API_KEY, OPENAI_API_KEY or ANTHROPIC_API_KEY)."
            )
        bundle, people = await extract(bundle, llm, checkpoint, reuse_checkpoint=not force_extract)
    log.info("Removing names and contact details of private individuals")
    return anonymize(bundle, people)


async def run(path: Path, force_extract: bool) -> str:
    """Process a bundle file into the database and return the stored case slug."""
    settings = get_settings()
    llm = make_llm(settings)

    extracted = path.with_name(f"{path.stem}.extracted.json")
    # Holds the original names (before anonymizing): it stays next to the collection.
    checkpoint = path.with_name(f"{path.stem}.judgment.json")
    if not force_extract and not path.stem.endswith(".extracted") and extracted.exists():
        log.info("Reusing the earlier extraction for this case")
        path = extracted

    raw = CaseBundle.model_validate_json(path.read_text(encoding="utf-8"))
    bundle = await process(raw, llm, force_extract, checkpoint)
    if not raw.is_extracted or force_extract:
        extracted.write_text(bundle.model_dump_json(indent=2), encoding="utf-8")
        log.info("Saved the extraction so the LLM is not called again for this case")

    gap = perception_gap(bundle)
    async with SessionLocal() as session:
        await save_case(session, bundle, gap)
    log.info("Saved %s: Perception Gap Index %.1f", bundle.case.slug, gap.score)
    return bundle.case.slug
