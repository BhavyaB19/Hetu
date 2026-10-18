"""Extraction validators and the retry loop, with a scripted fake LLM."""

import pytest

from app.schemas.extraction import (
    LLMClaim,
    LLMJudgment,
    LLMMedia,
    LLMPublic,
    LLMReaction,
    LLMTimelineEvent,
)
from app.services.anonymizer import Person
from app.services.extraction import classify_public, extract_judgment, extract_media
from app.services.llm import MAX_ATTEMPTS, ExtractionError
from app.services.pipeline import process


class FakeLLM:
    """Returns queued answers per output type and records each prompt."""

    def __init__(self, answers: dict[type, list]):
        self.answers = answers
        self.prompts: list[str] = []

    async def parse(self, system, prompt, output_format):
        self.prompts.append(prompt)
        return self.answers[output_format].pop(0)


def judgment_answer(quote="The trigger was the parking dispute alone.") -> LLMJudgment:
    q = "The hostility of one witness does not erase the evidence of another."
    return LLMJudgment(
        people=[Person(name="Ravi Kumar", role="accused", aliases=["Ravi"])],
        facts="Ravi Kumar struck the shopkeeper once.",
        facts_quote=q,
        motive="None established.",
        motive_quote=q,
        trigger="A parking dispute.",
        trigger_quote=quote,
        court_reasoning="Independent evidence outweighs one hostile witness.",
        court_reasoning_quote=q,
        outcome="Convicted under Section 304 Part I.",
        outcome_quote="The acquittal is set aside.",
        outcome_direction="conviction",
        legal_provisions=["Section 304 Part I IPC"],
        timeline=[
            LLMTimelineEvent(
                date="2019-03-14",
                label="Quarrel",
                description="d",
                phase="incident",
                court_weight=1.0,
                quote=quote,
            ),
            LLMTimelineEvent(
                date="not a date",
                label="Appeal",
                description="d",
                phase="appeal",
                court_weight=0.9,
                quote="The acquittal is set aside.",
            ),
        ],
    )


def media_answer(quote: str) -> LLMMedia:
    return LLMMedia(
        people=[],
        framing="sensational",
        tone=-0.7,
        narratives=["Justice denied"],
        claims=[
            LLMClaim(
                text="Repeated blows.",
                quote=quote,
                verdict="contradicted",
                rationale="Single blow.",
                judgment_quote="consistent with a single blow from a blunt object",
            )
        ],
        events_mentioned=[0, 1, 99],
    )


async def test_judgment_is_converted_with_spans(demo):
    doc = demo.document("judgment-hc")
    llm = FakeLLM({LLMJudgment: [judgment_answer()]})
    result, people = await extract_judgment(llm, doc)
    assert result.evidence["trigger"].document == "judgment-hc"
    assert result.timeline[0].date.isoformat() == "2019-03-14"
    assert result.timeline[1].date is None  # unparseable dates become null, not errors
    assert people[0].name == "Ravi Kumar"


async def test_invented_quote_triggers_retry_with_feedback(demo):
    doc = demo.document("judgment-hc")
    llm = FakeLLM({LLMJudgment: [judgment_answer("an invented quote"), judgment_answer()]})
    result, _ = await extract_judgment(llm, doc)
    assert result.evidence["trigger"].quote == "The trigger was the parking dispute alone."
    assert len(llm.prompts) == 2
    assert "rejected" in llm.prompts[1] and "an invented quote" in llm.prompts[1]


async def test_gives_up_after_max_attempts(demo):
    doc = demo.document("judgment-hc")
    llm = FakeLLM({LLMJudgment: [judgment_answer("made up")] * MAX_ATTEMPTS})
    with pytest.raises(ExtractionError):
        await extract_judgment(llm, doc)


async def test_out_of_range_values_are_rejected(demo):
    doc = demo.document("judgment-hc")
    bad = judgment_answer()
    bad.timeline[0].court_weight = 1.7
    llm = FakeLLM({LLMJudgment: [bad, judgment_answer()]})
    await extract_judgment(llm, doc)
    assert len(llm.prompts) == 2


async def test_media_claims_link_both_documents(demo):
    judgment_doc = demo.document("judgment-hc")
    article = demo.document("media-1")
    llm = FakeLLM({LLMMedia: [media_answer("the victim was beaten repeatedly with an iron rod")]})
    result, _ = await extract_media(llm, article, demo.judgment, judgment_doc)
    claim = result.claims[0]
    assert claim.evidence.document == "media-1"
    assert claim.judgment_evidence.document == "judgment-hc"
    assert result.events_mentioned == [0, 1]  # index 99 is dropped
    assert result.headline == article.title


async def test_public_needs_one_entry_per_reaction(demo):
    docs = [d for d in demo.documents if d.source_type == "public"][:2]
    partial = LLMPublic(
        people=[], reactions=[LLMReaction(key=docs[0].key, sentiment="neutral_uncertain", themes=["x"])]
    )
    full = LLMPublic(
        people=[],
        reactions=[LLMReaction(key=d.key, sentiment="support_victim", themes=["x"]) for d in docs],
    )
    llm = FakeLLM({LLMPublic: [partial, full]})
    result, _ = await classify_public(llm, docs)
    assert [r.document for r in result] == [d.key for d in docs]
    assert len(llm.prompts) == 2


async def test_pipeline_anonymizes_names_found_by_the_llm(demo):
    # Put a real-looking name into the raw text, as a scraped judgment would have.
    raw = demo.model_copy(deep=True)
    raw.judgment, raw.media, raw.public = None, [], []
    raw.documents = [d for d in raw.documents if d.source_type == "judgment"]
    raw.documents[0].text = raw.documents[0].text.replace("[ACCUSED_1]", "Ravi Kumar")
    llm = FakeLLM({LLMJudgment: [judgment_answer()]})
    out = await process(raw, llm)
    assert "Ravi Kumar" not in out.documents[0].text
    assert "Ravi Kumar" not in out.judgment.facts
    assert out.judgment.facts.startswith("[ACCUSED_1]")


async def test_pipeline_without_key_refuses_unextracted_case(demo):
    raw = demo.model_copy(deep=True)
    raw.judgment, raw.media, raw.public = None, [], []
    with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY"):
        await process(raw, None)


def test_relevant_passages_keep_long_judgments_small_and_verbatim():
    from app.services.extraction import relevant_passages

    filler = [f"{i}. The witness examined the documentary record in detail on that date." for i in range(400)]
    key = "401. The licensed pistol recovered from the accused matched the bullet found at the restaurant."
    judgment = "\n\n".join([*filler[:200], key, *filler[200:]])
    article = "Police say the pistol and the bullet from the restaurant were the key evidence."

    excerpt = relevant_passages(judgment, article, budget=2000)
    assert len(excerpt) <= 2000 + 200  # budget plus separators
    assert key in excerpt
    for passage in excerpt.split("\n\n[...]\n\n"):
        assert passage in judgment  # passages are verbatim slices, so quotes still verify

    short = "1. A short judgment."
    assert relevant_passages(short, article) == short


async def test_unverifiable_claims_are_dropped_without_retry(demo):
    judgment_doc = demo.document("judgment-hc")
    article = demo.document("media-1")
    real_article = "the victim was beaten repeatedly with an iron rod"
    real_judgment = "consistent with a single blow from a blunt object"
    answer = LLMMedia(
        people=[],
        framing="sensational",
        tone=-0.7,
        narratives=["x"],
        claims=[
            LLMClaim(
                text="kept",
                quote=real_article,
                verdict="contradicted",
                rationale="r",
                judgment_quote=real_judgment,
            ),
            LLMClaim(
                text="fake article quote",
                quote="not in the article",
                verdict="absent",
                rationale="r",
                judgment_quote=None,
            ),
            LLMClaim(
                text="fake judgment quote",
                quote=real_article,
                verdict="supported",
                rationale="r",
                judgment_quote="invented",
            ),
            LLMClaim(
                text="absent, bad link",
                quote=real_article,
                verdict="absent",
                rationale="r",
                judgment_quote="invented",
            ),
        ],
        events_mentioned=[],
    )
    llm = FakeLLM({LLMMedia: [answer]})
    result, _ = await extract_media(llm, article, demo.judgment, judgment_doc)
    assert len(llm.prompts) == 1  # no retry
    assert [c.text for c in result.claims] == ["kept", "absent, bad link"]
    assert result.claims[1].judgment_evidence is None


async def test_judgment_findings_are_checkpointed(demo, tmp_path):
    raw = demo.model_copy(deep=True)
    raw.judgment, raw.media, raw.public = None, [], []
    raw.documents = [d for d in raw.documents if d.source_type == "judgment"]
    checkpoint = tmp_path / "case.judgment.json"

    await process(raw, FakeLLM({LLMJudgment: [judgment_answer()]}), checkpoint=checkpoint)
    assert checkpoint.exists()

    # A second run reuses the saved findings: the LLM is not asked about the judgment again.
    no_judgment_calls = FakeLLM({LLMJudgment: []})
    out = await process(raw, no_judgment_calls, checkpoint=checkpoint)
    assert no_judgment_calls.prompts == [] and out.judgment is not None

    # Forcing re-extraction, or a changed judgment, ignores the checkpoint.
    forced = FakeLLM({LLMJudgment: [judgment_answer()]})
    await process(raw, forced, force_extract=True, checkpoint=checkpoint)
    assert len(forced.prompts) == 1
    raw.documents[0].text += "\n\n10. A later paragraph."
    changed = FakeLLM({LLMJudgment: [judgment_answer()]})
    await process(raw, changed, checkpoint=checkpoint)
    assert len(changed.prompts) == 1
