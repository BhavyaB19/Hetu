"""Extraction under small token budgets (Groq's free plan): pacing, chunked judgments,
note selection, budget-sized prompts, and tolerance of single failures."""

import re

import pytest

from app.core.config import Settings
from app.schemas.bundle import quote_in
from app.schemas.extraction import (
    LLMChunkEvent,
    LLMChunkNotes,
    LLMJudgmentFromNotes,
    LLMMedia,
    LLMNote,
    LLMNoteSelection,
    LLMPublic,
    LLMReaction,
    LLMTimelineFromNote,
)
from app.services import llm as llm_module
from app.services.extraction import OVERHEAD_TOKENS, chunks, classify_public, extract_judgment, extract_media
from app.services.llm import ExtractionError, GroqLLM, TokenRateLimiter, estimate_tokens, make_llm
from app.services.pipeline import process

# ---------- rate limiter ----------


async def test_rate_limiter_waits_for_the_window(monkeypatch):
    now = [0.0]
    waits: list[float] = []

    async def fake_sleep(seconds):
        waits.append(seconds)
        now[0] += seconds

    monkeypatch.setattr(llm_module.asyncio, "sleep", fake_sleep)
    limiter = TokenRateLimiter(100, clock=lambda: now[0])
    await limiter.reserve(60)
    await limiter.reserve(30)
    assert waits == []
    await limiter.reserve(30)  # 120 > 100 within the minute: must wait for the first to expire
    assert len(waits) == 1 and 59 < waits[0] <= 60.2
    await limiter.reserve(500)  # larger than the whole limit: capped, still goes through eventually
    assert len(waits) >= 2


# ---------- chunking ----------


def test_chunks_are_bounded_and_verbatim(demo):
    text = demo.document("judgment-hc").text
    parts = chunks(text, 900)
    assert len(parts) > 2
    assert all(len(p) <= 1500 for p in parts)  # one passage may exceed a tiny limit, never PASSAGE_CHARS
    for part in parts:
        for passage in part.split("\n\n"):
            assert passage in text


# ---------- a scripted LLM that answers from the prompt ----------

SENTENCE = re.compile(r"[A-Z][^.]{20,160}\.")
NOTE_LINE = re.compile(r"^\[(\d+)\] (\w+):", re.M)


class BudgetLLM:
    """Answers each schema from the prompt itself, like a well-behaved model would."""

    def __init__(self, input_budget: int, fail_media_for: str | None = None):
        self.input_budget = input_budget
        self.fail_media_for = fail_media_for
        self.calls: dict[str, int] = {}
        self.prompts: list[str] = []

    async def parse(self, system, prompt, output_format):
        name = output_format.__name__
        self.calls[name] = self.calls.get(name, 0) + 1
        self.prompts.append(prompt)
        return getattr(self, name)(prompt)

    def LLMChunkNotes(self, prompt):
        part = prompt.split("<part>\n", 1)[1].rsplit("\n</part>", 1)[0]
        sentences = SENTENCE.findall(part) or [part[:60]]
        last = re.search(r"part (\d+) of (\d+)", prompt).groups()
        is_last = last[0] == last[1]
        note = LLMNote(point="A finding.", quote=sentences[0])
        return LLMChunkNotes(
            people=[],
            facts=[note, LLMNote(point="Invented.", quote="this sentence is not in the judgment at all")],
            motive=[],
            trigger=[],
            reasoning=[note],
            outcome=[note] if is_last else [],
            events=[
                LLMChunkEvent(
                    date="2023-02-10",
                    label="An event",
                    description="d",
                    phase="appeal",
                    court_weight=0.8,
                    quote=sentences[-1],
                )
            ],
            legal_provisions=["Section 304 Part I IPC"],
        )

    def LLMNoteSelection(self, prompt):
        found = NOTE_LINE.findall(prompt)
        pick = {c: [int(i) for i, cat in found if cat == c][:1] for c in ("facts", "reasoning", "outcome")}
        events = [int(i) for i, cat in found if cat == "event"][:2]
        return LLMNoteSelection(
            facts=pick["facts"],
            motive=[],
            trigger=[],
            reasoning=pick["reasoning"],
            outcome=pick["outcome"],
            events=events,
        )

    def LLMJudgmentFromNotes(self, prompt):
        found = NOTE_LINE.findall(prompt)
        first = {}
        for i, cat in found:
            first.setdefault(cat, int(i))
        any_id = int(found[0][0])
        return LLMJudgmentFromNotes(
            facts="Facts.",
            facts_note=first.get("facts", any_id),
            motive="None found.",
            motive_note=first.get("facts", any_id),
            trigger="A dispute.",
            trigger_note=first.get("facts", any_id),
            court_reasoning="Reasons.",
            court_reasoning_note=first.get("reasoning", any_id),
            outcome="Convicted.",
            outcome_note=first["outcome"],
            outcome_direction="conviction",
            legal_provisions=["Section 304 Part I IPC"],
            timeline=[
                LLMTimelineFromNote(
                    note=first["event"],
                    date=None,
                    label="Appeal",
                    description="d",
                    phase="appeal",
                    court_weight=1.0,
                )
            ],
        )

    def LLMMedia(self, prompt):
        if self.fail_media_for and self.fail_media_for in prompt:
            raise ExtractionError("model failed")
        return LLMMedia(
            people=[], framing="procedural", tone=0.0, narratives=["x"], claims=[], events_mentioned=[]
        )

    def LLMPublic(self, prompt):
        keys = re.findall(r'<reaction key="([^"]+)">', prompt)
        reactions = [LLMReaction(key=k, sentiment="neutral_uncertain", themes=["x"]) for k in keys]
        return LLMPublic(people=[], reactions=reactions)


async def test_long_judgment_is_read_in_chunks_and_narrowed(demo):
    doc = demo.document("judgment-hc")
    llm = BudgetLLM(input_budget=OVERHEAD_TOKENS + 420)
    result, _ = await extract_judgment(llm, doc)

    assert llm.calls["LLMChunkNotes"] > 2
    assert llm.calls["LLMJudgmentFromNotes"] == 1
    assert result.outcome_direction == "conviction"
    for span in [*result.evidence.values(), *(e.evidence for e in result.timeline)]:
        assert quote_in(span.quote, doc.text)
    assert not any("not in the judgment" in s.quote for s in result.evidence.values())
    for prompt in llm.prompts:
        assert estimate_tokens(prompt) <= llm.input_budget


async def test_notes_are_narrowed_until_they_fit():
    from app.services.extraction import Note, select_notes

    notes = [
        Note(
            i, ["facts", "reasoning", "outcome", "events"][i % 4], f"Finding number {i} about the case.", "q"
        )
        for i in range(200)
    ]
    llm = BudgetLLM(input_budget=OVERHEAD_TOKENS + 600)
    kept = await select_notes(llm, notes)
    assert llm.calls["LLMNoteSelection"] > 1
    assert sum(len(n.line()) + 1 for n in kept) <= (llm.input_budget - OVERHEAD_TOKENS) * 3
    assert {n.category for n in kept} >= {"facts", "reasoning", "outcome"}


async def test_short_judgment_still_uses_one_call(demo):
    from app.schemas.extraction import LLMJudgment
    from tests.test_extraction import FakeLLM, judgment_answer

    fake = FakeLLM({LLMJudgment: [judgment_answer()]})
    fake.input_budget = 100_000
    await extract_judgment(fake, demo.document("judgment-hc"))
    assert len(fake.prompts) == 1


async def test_media_prompt_fits_the_budget(demo):
    llm = BudgetLLM(input_budget=OVERHEAD_TOKENS + 1500)
    long_judgment = demo.document("judgment-hc").model_copy(
        update={"text": demo.document("judgment-hc").text * 20}
    )
    article = demo.document("media-1").model_copy(update={"text": demo.document("media-1").text * 10})
    await extract_media(llm, article, demo.judgment, long_judgment)
    assert estimate_tokens(llm.prompts[0]) <= llm.input_budget


async def test_reactions_are_batched_to_fit(demo):
    llm = BudgetLLM(input_budget=OVERHEAD_TOKENS + 250)
    docs = [d for d in demo.documents if d.source_type == "public"]
    results, _ = await classify_public(llm, docs)
    assert llm.calls["LLMPublic"] > 1
    assert sorted(r.document for r in results) == sorted(d.key for d in docs)


async def test_one_failed_article_does_not_sink_the_case(demo):
    raw = demo.model_copy(deep=True)
    raw.judgment, raw.media, raw.public = None, [], []
    failing = raw.document("media-2")
    llm = BudgetLLM(input_budget=OVERHEAD_TOKENS + 420, fail_media_for=failing.text[:80])
    out = await process(raw, llm)
    assert {m.document for m in out.media} == {"media-1", "media-3", "media-4", "media-5"}
    assert len(out.public) == 16


def test_groq_plans():
    free = make_llm(Settings(_env_file=None, llm_provider="groq", groq_api_key="gsk"))
    paid = make_llm(Settings(_env_file=None, llm_provider="groq", groq_api_key="gsk", groq_plan="developer"))
    assert isinstance(free, GroqLLM) and free.input_budget == llm_module.FREE_GROQ_INPUT_BUDGET
    assert isinstance(paid, GroqLLM) and paid.input_budget is None


@pytest.mark.parametrize("text", ["", "x" * 3000])
def test_estimate_tokens_is_cautious(text):
    assert estimate_tokens(text) >= len(text) / 4
