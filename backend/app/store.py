"""Write case bundles to the database and read them back as dashboard views."""

from collections import Counter

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app import models
from app.schemas import (
    CaseBundle,
    CaseSummary,
    CaseView,
    ClaimView,
    Evidence,
    GapComponentView,
    GapView,
    JudgmentView,
    MediaView,
    PublicView,
    ReactionView,
    Share,
    SourceView,
    TimelineEventView,
    content_hash,
)
from app.scoring import LABELS, GapScore, media_weights

ALL_RELATIONS = (
    selectinload(models.Case.documents),
    selectinload(models.Case.judgment),
    selectinload(models.Case.media),
    selectinload(models.Case.reactions),
    selectinload(models.Case.gap_score),
)
SENTIMENT_ORDER = ["support_victim", "support_accused", "neutral_uncertain", "against_media_bias"]


async def save_case(session: AsyncSession, bundle: CaseBundle, gap: GapScore) -> None:
    """Replace any stored version of this case with the bundle."""
    existing = await session.scalar(
        select(models.Case).where(models.Case.slug == bundle.case.slug).options(*ALL_RELATIONS)
    )
    if existing:
        await session.delete(existing)
        await session.flush()

    info = bundle.case
    case = models.Case(
        slug=info.slug,
        title=info.title,
        category=info.category,
        court=info.court,
        summary=info.summary,
        is_illustrative=info.is_illustrative,
    )
    case.documents = [
        models.Document(
            key=d.key,
            source_type=d.source_type,
            source_name=d.source_name,
            url=d.url,
            published_at=d.published_at,
            language=d.language,
            text=d.text,
            content_hash=content_hash(d.text),
        )
        for d in bundle.documents
    ]
    if j := bundle.judgment:
        timeline = [
            {**e.model_dump(mode="json"), "media_weight": w}
            for e, w in zip(j.timeline, media_weights(bundle), strict=True)
        ]
        case.judgment = models.Judgment(
            document_key=j.document,
            facts=j.facts,
            motive=j.motive,
            trigger=j.trigger,
            court_reasoning=j.court_reasoning,
            outcome=j.outcome,
            outcome_direction=j.outcome_direction,
            legal_provisions=j.legal_provisions,
            timeline=timeline,
            evidence={k: v.model_dump() for k, v in j.evidence.items()},
        )
    case.media = [
        models.MediaArticle(
            document_key=m.document,
            headline=m.headline,
            framing=m.framing,
            tone=m.tone,
            narratives=m.narratives,
            claims=[c.model_dump(mode="json") for c in m.claims],
            events_mentioned=m.events_mentioned,
        )
        for m in bundle.media
    ]
    case.reactions = [
        models.PublicReaction(document_key=p.document, sentiment=p.sentiment, themes=p.themes)
        for p in bundle.public
    ]
    case.gap_score = models.GapScore(
        score=gap.score,
        components=[
            {"key": c.key, "value": round(c.value, 4), "explanation": c.explanation} for c in gap.components
        ],
        weights=gap.weights,
    )
    session.add(case)
    await session.commit()


async def list_cases(session: AsyncSession) -> list[CaseSummary]:
    cases = await session.scalars(
        select(models.Case).options(selectinload(models.Case.gap_score)).order_by(models.Case.title)
    )
    return [_summary(c) for c in cases]


async def get_case(session: AsyncSession, slug: str) -> CaseView | None:
    case = await session.scalar(select(models.Case).where(models.Case.slug == slug).options(*ALL_RELATIONS))
    if case is None:
        return None
    docs = {d.key: d for d in case.documents}

    def evidence(span: dict | None) -> Evidence | None:
        if not span or span["document"] not in docs:
            return None
        doc = docs[span["document"]]
        return Evidence(
            document=doc.key,
            source_name=doc.source_name,
            url=doc.url,
            published_at=doc.published_at,
            quote=span["quote"],
        )

    j = case.judgment
    judgment = (
        JudgmentView(
            facts=j.facts,
            motive=j.motive,
            trigger=j.trigger,
            court_reasoning=j.court_reasoning,
            outcome=j.outcome,
            outcome_direction=j.outcome_direction,
            legal_provisions=j.legal_provisions,
            evidence={k: e for k, v in j.evidence.items() if (e := evidence(v))},
        )
        if j
        else None
    )
    timeline = [
        TimelineEventView(
            date=e["date"],
            label=e["label"],
            description=e["description"],
            phase=e["phase"],
            court_weight=e["court_weight"],
            media_weight=e["media_weight"],
            evidence=evidence(e.get("evidence")),
        )
        for e in (j.timeline if j else [])
    ]
    media = sorted(
        (
            MediaView(
                document=m.document_key,
                outlet=docs[m.document_key].source_name,
                url=docs[m.document_key].url,
                published_at=docs[m.document_key].published_at,
                headline=m.headline,
                framing=m.framing,
                tone=m.tone,
                narratives=m.narratives,
                claims=[
                    ClaimView(
                        text=c["text"],
                        verdict=c["verdict"],
                        rationale=c["rationale"],
                        evidence=evidence(c["evidence"]),
                        judgment_evidence=evidence(c.get("judgment_evidence")),
                    )
                    for c in m.claims
                ],
            )
            for m in case.media
        ),
        key=lambda m: (m.published_at is None, m.published_at),
    )
    return CaseView(
        case=_summary(case),
        gap=_gap(case.gap_score),
        judgment=judgment,
        timeline=timeline,
        media=media,
        public=_public(case.reactions, docs),
        sources=[
            SourceView(
                key=d.key,
                source_type=d.source_type,
                source_name=d.source_name,
                url=d.url,
                published_at=d.published_at,
            )
            for d in sorted(
                case.documents, key=lambda d: (d.source_type, d.published_at is None, d.published_at)
            )
        ],
    )


def _summary(case: models.Case) -> CaseSummary:
    return CaseSummary(
        slug=case.slug,
        title=case.title,
        category=case.category,
        court=case.court,
        summary=case.summary,
        is_illustrative=case.is_illustrative,
        gap_score=case.gap_score.score if case.gap_score else None,
    )


def _gap(gap: models.GapScore | None) -> GapView | None:
    if gap is None:
        return None
    total = sum(gap.weights.values())
    components = [
        GapComponentView(
            key=c["key"],
            label=LABELS[c["key"]],
            value=c["value"],
            weight=gap.weights[c["key"]] / total,
            contribution=round(100 * gap.weights[c["key"]] * c["value"] / total, 1),
            explanation=c["explanation"],
        )
        for c in gap.components
    ]
    return GapView(score=gap.score, components=components)


def _public(reactions: list[models.PublicReaction], docs: dict[str, models.Document]) -> PublicView:
    total = len(reactions)
    sentiments = Counter(r.sentiment for r in reactions)
    themes = Counter(t for r in reactions for t in set(r.themes))
    return PublicView(
        total=total,
        sentiment=[
            Share(key=s, count=sentiments[s], share=sentiments[s] / total if total else 0)
            for s in SENTIMENT_ORDER
        ],
        themes=[Share(key=t, count=n, share=n / total) for t, n in themes.most_common()],
        reactions=[
            ReactionView(
                platform=docs[r.document_key].source_name,
                text=docs[r.document_key].text,
                sentiment=r.sentiment,
                themes=r.themes,
            )
            for r in reactions
        ],
    )
