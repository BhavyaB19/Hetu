"""Structured extraction with an LLM (Groq or Claude).

One call per judgment, one per news article, and one for the public reactions of a
case. The LLM returns JSON that matches a Pydantic schema (structured outputs). The
result is then checked against the source text: every quote must appear verbatim.
If validation fails, the call is retried with the problems listed.

Small token budgets (Groq's free plan) change two things:
- A judgment too long for one request is read in chunks. Each chunk yields short
  notes, each backed by a verbatim quote from that chunk. The notes are narrowed down
  in selection rounds until they fit one request, and a final call writes the
  court's findings from them, citing notes by id. Evidence quotes come from the notes.
- Article checks and reaction batches are sized to fit the budget.

The LLM sees the original text (names included) and lists the private people it
finds; the anonymizer then replaces those names everywhere before storage.
"""

import datetime as dt
import json
import logging
import math
import re
from collections import Counter
from dataclasses import dataclass

from app.schemas.bundle import (
    Claim,
    JudgmentExtraction,
    MediaExtraction,
    PublicExtraction,
    SourceDocument,
    Span,
    TimelineEvent,
    quote_in,
)
from app.schemas.extraction import (
    LLMChunkNotes,
    LLMJudgment,
    LLMJudgmentFromNotes,
    LLMMedia,
    LLMNoteSelection,
    LLMPublic,
)
from app.services.anonymizer import Person
from app.services.llm import LLM, ExtractionError, ask, estimate_tokens

log = logging.getLogger("hetu.extraction")

SYSTEM = """You extract structured, evidence-backed data about Indian court cases for a \
research tool that compares what a court found with how media and the public described it.

Rules:
- Use only the document you are given. Never add outside knowledge.
- Every "quote" field must be copied verbatim from the document: an exact, contiguous \
passage of 5 to 40 words. Do not paraphrase, merge or trim words inside a quote.
- List in "people" every named private individual (accused, victim, witness, relative, \
minor, or other private person) with any short forms of their name used in the text. Do \
not list judges, lawyers, police officers acting officially, or public officials.
- Write summaries neutrally. Do not judge the judges, and do not predict outcomes."""

# Tokens kept free in every request for the system prompt, instructions and output schema.
OVERHEAD_TOKENS = 1500
CATEGORIES = ("facts", "motive", "trigger", "reasoning", "outcome", "events")
SELECTION_CAPS = {"facts": 3, "motive": 2, "trigger": 2, "reasoning": 3, "outcome": 2, "events": 6}


def _span(doc: SourceDocument, quote: str, label: str) -> Span:
    if not quote_in(quote, doc.text):
        raise ValueError(f"{label}: quote is not verbatim in the document: {quote!r}")
    return Span(document=doc.key, quote=quote)


def _date(value: str | None) -> dt.date | None:
    try:
        return dt.date.fromisoformat(value) if value else None
    except ValueError:
        return None


def _room(llm: LLM, *fixed: str) -> int | None:
    """Characters left for variable content in one request, or None when there is no budget."""
    budget = getattr(llm, "input_budget", None)
    if budget is None:
        return None
    used = OVERHEAD_TOKENS + sum(estimate_tokens(t) for t in fixed)
    return max(budget - used, 300) * 3


# ---------- passages ----------

PASSAGE_CHARS = 1500
WORD = re.compile(r"[a-z]{4,}")


def _passages(text: str) -> list[str]:
    """Split a judgment into paragraph-sized passages, keeping them verbatim."""
    passages = []
    for block in re.split(r"\n\s*\n", text):
        block = block.strip()
        while len(block) > PASSAGE_CHARS:
            cut = block.rfind("\n", 0, PASSAGE_CHARS)
            cut = cut if cut > PASSAGE_CHARS // 3 else PASSAGE_CHARS
            passages.append(block[:cut].strip())
            block = block[cut:].strip()
        if len(block) > 40:
            passages.append(block)
    return passages


def chunks(text: str, max_chars: int) -> list[str]:
    """Pack consecutive passages into chunks of at most `max_chars` characters."""
    out, current = [], ""
    for passage in _passages(text):
        if current and len(current) + len(passage) + 2 > max_chars:
            out.append(current)
            current = ""
        current = f"{current}\n\n{passage}" if current else passage
    if current:
        out.append(current)
    return out


def relevant_passages(judgment: str, article: str, budget: int = 20_000) -> str:
    """The judgment passages sharing the most distinctive words with the article, in their
    original order, up to `budget` characters. Keeps each article check small: a full
    Supreme Court judgment can run past 60,000 tokens."""
    if len(judgment) <= budget:
        return judgment
    passages = _passages(judgment)
    doc_freq = Counter(w for p in passages for w in set(WORD.findall(p.lower())))
    article_words = set(WORD.findall(article.lower()))

    def score(passage: str) -> float:
        shared = set(WORD.findall(passage.lower())) & article_words
        return sum(math.log(len(passages) / doc_freq[w]) for w in shared)

    chosen, used = [], 0
    for i in sorted(range(len(passages)), key=lambda i: score(passages[i]), reverse=True):
        if used + len(passages[i]) <= budget:
            chosen.append(i)
            used += len(passages[i])
    return "\n\n[...]\n\n".join(passages[i] for i in sorted(chosen))


# ---------- judgment ----------

JUDGMENT_TASK = "Extract the court's findings from this judgment."


async def extract_judgment(llm: LLM, doc: SourceDocument) -> tuple[JudgmentExtraction, list[Person]]:
    room = _room(llm, JUDGMENT_TASK)
    if room is not None and len(doc.text) > room:
        return await _extract_judgment_in_chunks(llm, doc)

    prompt = f"{JUDGMENT_TASK}\n\n<document>\n{doc.text}\n</document>"

    def convert(r: LLMJudgment) -> JudgmentExtraction:
        fields = ["facts", "motive", "trigger", "court_reasoning", "outcome"]
        return JudgmentExtraction(
            document=doc.key,
            facts=r.facts,
            motive=r.motive,
            trigger=r.trigger,
            court_reasoning=r.court_reasoning,
            outcome=r.outcome,
            outcome_direction=r.outcome_direction,
            legal_provisions=r.legal_provisions,
            timeline=[
                TimelineEvent(
                    date=_date(e.date),
                    label=e.label,
                    description=e.description,
                    phase=e.phase,
                    court_weight=e.court_weight,
                    evidence=_span(doc, e.quote, f"timeline[{i}]"),
                )
                for i, e in enumerate(r.timeline)
            ],
            evidence={f: _span(doc, getattr(r, f"{f}_quote"), f) for f in fields},
        )

    raw, result = await ask(llm, SYSTEM, prompt, LLMJudgment, convert)
    return result, raw.people


@dataclass
class Note:
    id: int
    category: str
    point: str
    quote: str
    date: str | None = None
    label: str | None = None
    phase: str | None = None
    court_weight: float | None = None

    def line(self) -> str:
        if self.category == "events":
            return f"[{self.id}] event: {self.date or 'undated'} | {self.label}: {self.point}"
        return f"[{self.id}] {self.category}: {self.point}"


async def _extract_judgment_in_chunks(
    llm: LLM, doc: SourceDocument
) -> tuple[JudgmentExtraction, list[Person]]:
    parts = chunks(doc.text, _room(llm, CHUNK_TASK) or len(doc.text))
    log.info("The judgment is long: reading it in %d parts", len(parts))
    notes: list[Note] = []
    people: list[Person] = []
    for i, part in enumerate(parts, start=1):
        try:
            raw = await llm.parse(
                SYSTEM, CHUNK_TASK.format(i=i, n=len(parts)) + f"\n\n<part>\n{part}\n</part>", LLMChunkNotes
            )
        except ExtractionError as err:
            log.warning("Skipped part %d of the judgment: %s", i, err)
            continue
        people += raw.people
        before = len(notes)
        notes += _notes_from_chunk(raw, part, start_id=len(notes))
        log.info("Read part %d of %d of the judgment: %d notes", i, len(parts), len(notes) - before)

    if not any(n.category == "outcome" for n in notes):
        raise ExtractionError("Could not find the court's decision in the judgment.")
    selected = await select_notes(llm, notes)
    log.info("Writing the court's findings from %d notes", len(selected))
    return await _findings_from_notes(llm, doc, selected), people


CHUNK_TASK = (
    "This is part {i} of {n} of a court judgment. Take short notes on what this part says about the "
    "facts the court accepted, motive, trigger, the court's reasoning, the final outcome, and key events "
    "in the case history. Record what the court itself found, not just what a party argued. Quote "
    "verbatim from this part only. Leave a list empty when this part says nothing about it."
)


def _notes_from_chunk(raw: LLMChunkNotes, part: str, start_id: int) -> list[Note]:
    """Notes whose quotes are verbatim in the part; the rest are dropped (no retry)."""
    notes: list[Note] = []
    for category in CATEGORIES[:-1]:
        for n in getattr(raw, category):
            if quote_in(n.quote, part):
                notes.append(Note(start_id + len(notes), category, n.point, n.quote))
    for e in raw.events:
        if quote_in(e.quote, part):
            notes.append(
                Note(
                    start_id + len(notes),
                    "events",
                    e.description,
                    e.quote,
                    e.date,
                    e.label,
                    e.phase,
                    e.court_weight,
                )
            )
    return notes


SELECT_TASK = (
    "These notes were taken from a long court judgment. Choose the notes that best capture what the "
    "court found, by id, most important first. Prefer the final court's own findings over arguments "
    "of the parties, and events that shaped the case."
)


async def select_notes(llm: LLM, notes: list[Note]) -> list[Note]:
    """Narrow the notes down in rounds until they fit one request."""
    room = _room(llm, SELECT_TASK)
    while room is not None and sum(len(n.line()) + 1 for n in notes) > room:
        kept: list[Note] = []
        for group in _groups(notes, room):
            listing = "\n".join(n.line() for n in group)
            try:
                choice = await llm.parse(SYSTEM, f"{SELECT_TASK}\n\n{listing}", LLMNoteSelection)
            except ExtractionError as err:
                log.warning("Note selection failed, keeping the first notes of each kind: %s", err)
                choice = None
            kept += _apply_selection(group, choice)
        if len(kept) >= len(notes):  # make sure every round shrinks
            kept = _apply_selection(notes, None)
        log.info("Narrowed %d notes down to %d", len(notes), len(kept))
        notes = kept
    return notes


def _groups(notes: list[Note], room: int) -> list[list[Note]]:
    groups, current, size = [], [], 0
    for note in notes:
        if current and size + len(note.line()) + 1 > room:
            groups.append(current)
            current, size = [], 0
        current.append(note)
        size += len(note.line()) + 1
    return [*groups, current] if current else groups


def _apply_selection(group: list[Note], choice: LLMNoteSelection | None) -> list[Note]:
    by_id = {n.id: n for n in group}
    kept: list[Note] = []
    for category in CATEGORIES:
        ids = getattr(choice, category) if choice else [n.id for n in group if n.category == category]
        picked = [by_id[i] for i in ids if i in by_id and by_id[i].category == category]
        kept += picked[: SELECTION_CAPS[category]]
    return sorted(kept, key=lambda n: n.id)


FINDINGS_TASK = (
    "These notes were taken from a court judgment. Write the court's findings from them. For each "
    "field give the id of the note that best supports it, and base every timeline entry on an event "
    "note. Use only these notes."
)


async def _findings_from_notes(llm: LLM, doc: SourceDocument, notes: list[Note]) -> JudgmentExtraction:
    by_id = {n.id: n for n in notes}
    listing = "\n".join(n.line() for n in notes)

    def note(note_id: int, label: str) -> Note:
        if note_id not in by_id:
            raise ValueError(f"{label}: note {note_id} is not in the list")
        return by_id[note_id]

    def convert(r: LLMJudgmentFromNotes) -> JudgmentExtraction:
        evidence = {
            field: _span(doc, note(getattr(r, f"{field}_note"), field).quote, field)
            for field in ("facts", "motive", "trigger", "court_reasoning", "outcome")
        }
        timeline = []
        for i, entry in enumerate(r.timeline):
            source = note(entry.note, f"timeline[{i}]")
            timeline.append(
                TimelineEvent(
                    date=_date(entry.date or source.date),
                    label=entry.label,
                    description=entry.description,
                    phase=entry.phase,
                    court_weight=entry.court_weight,
                    evidence=_span(doc, source.quote, f"timeline[{i}]"),
                )
            )
        return JudgmentExtraction(
            document=doc.key,
            facts=r.facts,
            motive=r.motive,
            trigger=r.trigger,
            court_reasoning=r.court_reasoning,
            outcome=r.outcome,
            outcome_direction=r.outcome_direction,
            legal_provisions=r.legal_provisions,
            timeline=timeline,
            evidence=evidence,
        )

    _, result = await ask(llm, SYSTEM, f"{FINDINGS_TASK}\n\n{listing}", LLMJudgmentFromNotes, convert)
    return result


# ---------- media ----------

MEDIA_TASK = (
    "Analyse how this news article frames the case, and check each factual claim it makes "
    "against the court's findings."
)


async def extract_media(
    llm: LLM, doc: SourceDocument, judgment: JudgmentExtraction, judgment_doc: SourceDocument
) -> tuple[MediaExtraction, list[Person]]:
    findings = json.dumps(
        {
            "facts": judgment.facts,
            "motive": judgment.motive,
            "trigger": judgment.trigger,
            "court_reasoning": judgment.court_reasoning,
            "outcome": judgment.outcome,
            "timeline": [f"{i}: {e.date or 'undated'} {e.label}" for i, e in enumerate(judgment.timeline)],
        },
        indent=2,
        default=str,
    )
    article = doc.text
    passage_chars = 20_000
    room = _room(llm, MEDIA_TASK, findings)
    if room is not None:
        # Split what is left between the article and the judgment passages.
        article = article[: max(room // 2, room - 4_000)]
        passage_chars = max(room - len(article), 1_500)

    prompt = (
        f"{MEDIA_TASK}\n\n"
        f"<court_findings>\n{findings}\n</court_findings>\n\n"
        f"<judgment_passages>\n{relevant_passages(judgment_doc.text, article, passage_chars)}\n"
        "</judgment_passages>\n\n"
        f"<article outlet={doc.source_name!r} date={doc.published_at}>\n{article}\n</article>\n\n"
        "Article quotes come from <article>; judgment quotes come from <judgment_passages>, "
        "copied from within a single passage."
    )

    def convert(r: LLMMedia) -> MediaExtraction:
        events = [i for i in r.events_mentioned if 0 <= i < len(judgment.timeline)]
        return MediaExtraction(
            document=doc.key,
            headline=doc.title or doc.text.strip().splitlines()[0],
            framing=r.framing,
            tone=r.tone,
            narratives=r.narratives,
            claims=_verified_claims(r, doc, judgment_doc),
            events_mentioned=events,
        )

    raw, result = await ask(llm, SYSTEM, prompt, LLMMedia, convert)
    return result, raw.people


def _verified_claims(r: LLMMedia, doc: SourceDocument, judgment_doc: SourceDocument) -> list[Claim]:
    """Keep only claims whose evidence checks out, instead of retrying the whole article.

    A claim needs a verbatim quote from the article. A supported or contradicted verdict
    also needs a verbatim passage from the judgment; without one the verdict cannot be
    shown with its evidence, so the claim is left out. For a claim absent from the
    judgment, an unverifiable judgment quote is simply dropped.
    """
    claims, dropped = [], 0
    for c in r.claims:
        backed = bool(c.judgment_quote) and quote_in(c.judgment_quote, judgment_doc.text)
        if not quote_in(c.quote, doc.text) or (c.verdict != "absent" and not backed):
            dropped += 1
            continue
        claims.append(
            Claim(
                text=c.text,
                evidence=Span(document=doc.key, quote=c.quote),
                verdict=c.verdict,
                rationale=c.rationale,
                judgment_evidence=Span(document=judgment_doc.key, quote=c.judgment_quote) if backed else None,
            )
        )
    if dropped:
        log.warning("%s: left out %d claims whose quotes could not be verified", doc.source_name, dropped)
    return claims


# ---------- public reactions ----------

PUBLIC_TASK = (
    "Classify each public reaction to this court case. Sentiment means which side the writer leans "
    "towards. First settle on 3 to 6 short theme labels that cover these reactions, then tag each "
    "reaction with 1 or 2 of them, using the exact same wording every time. Return one entry per "
    "reaction key."
)


async def classify_public(
    llm: LLM, docs: list[SourceDocument]
) -> tuple[list[PublicExtraction], list[Person]]:
    """Classify reactions, in as few batches as the token budget allows."""
    room = _room(llm, PUBLIC_TASK)
    batches: list[list[SourceDocument]] = []
    size = 0
    for doc in docs:
        item = len(doc.text) + 40
        if not batches or (room is not None and size + item > room):
            batches.append([])
            size = 0
        batches[-1].append(doc)
        size += item

    results: list[PublicExtraction] = []
    people: list[Person] = []
    for batch in batches:
        found, who = await _classify_batch(llm, batch)
        results += found
        people += who
    return results, people


async def _classify_batch(
    llm: LLM, docs: list[SourceDocument]
) -> tuple[list[PublicExtraction], list[Person]]:
    items = "\n".join(f'<reaction key="{d.key}">{d.text}</reaction>' for d in docs)
    keys = {d.key for d in docs}

    def convert(r: LLMPublic) -> list[PublicExtraction]:
        got = {x.key for x in r.reactions}
        if got != keys:
            raise ValueError(f"Expected one entry per key. Missing: {keys - got}, unknown: {got - keys}")
        return [PublicExtraction(document=x.key, sentiment=x.sentiment, themes=x.themes) for x in r.reactions]

    raw, result = await ask(llm, SYSTEM, f"{PUBLIC_TASK}\n\n{items}", LLMPublic, convert)
    return result, raw.people
