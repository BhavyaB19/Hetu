"""Write case bundles to the database and read them back as dashboard views."""

import datetime as dt
import uuid
from collections import Counter

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db import models
from app.schemas.bundle import CaseBundle, content_hash
from app.schemas.views import (
    CaseSummary,
    CaseView,
    ClaimView,
    CommentView,
    Evidence,
    GapComponentView,
    GapView,
    HomeCounters,
    HomeSummaryView,
    JudgmentView,
    MediaView,
    PollResultsView,
    PollView,
    PublicView,
    ReactionView,
    ReasonTally,
    Share,
    SourceView,
    TimelineEventView,
)
from app.services.scoring import LABELS, GapScore, media_weights

ALL_RELATIONS = (
    selectinload(models.Case.documents),
    selectinload(models.Case.judgment),
    selectinload(models.Case.media),
    selectinload(models.Case.reactions),
    selectinload(models.Case.gap_score),
)
SENTIMENT_ORDER = ["support_victim", "support_accused", "neutral_uncertain", "against_media_bias"]


async def save_case(
    session: AsyncSession,
    bundle: CaseBundle,
    gap: GapScore,
    status: str | None = None,
    review_state: str | None = None,
) -> None:
    """Replace any stored version of this case with the bundle."""
    existing = await session.scalar(
        select(models.Case).where(models.Case.slug == bundle.case.slug).options(*ALL_RELATIONS)
    )
    final_status = status or (existing.status if existing else "decided")
    final_review_state = review_state or (
        existing.review_state
        if existing
        else ("published" if bundle.case.is_illustrative else "draft")
    )
    featured = existing.featured if existing else False
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
        status=final_status,
        review_state=final_review_state,
        featured=featured,
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
    if case.review_state == "published" and case.status == "decided":
        case.poll = models.Poll(
            case_id=case.id,
            question="Do you agree with the court's verdict?",
            status="open",
            opens_at=dt.datetime.now(dt.UTC),
        )
    session.add(case)
    await session.commit()


async def list_cases(session: AsyncSession) -> list[CaseSummary]:
    """Public case list: only returns published cases."""
    cases = await session.scalars(
        select(models.Case)
        .where(models.Case.review_state == "published")
        .options(selectinload(models.Case.gap_score))
        .order_by(models.Case.title)
    )
    return [_summary(c) for c in cases]


async def list_cases_admin(session: AsyncSession) -> list[CaseSummary]:
    """Admin case list: returns all cases regardless of review_state."""
    cases = await session.scalars(
        select(models.Case).options(selectinload(models.Case.gap_score)).order_by(models.Case.title)
    )
    return [_summary(c) for c in cases]


async def get_case(session: AsyncSession, slug: str) -> CaseView | None:
    """Public case view: only returns published cases."""
    case = await session.scalar(
        select(models.Case)
        .where(models.Case.slug == slug, models.Case.review_state == "published")
        .options(*ALL_RELATIONS)
    )
    if case is None:
        return None
    return _build_case_view(case)


async def get_case_admin(session: AsyncSession, slug: str) -> CaseView | None:
    """Admin case view: returns case regardless of review_state."""
    case = await session.scalar(
        select(models.Case).where(models.Case.slug == slug).options(*ALL_RELATIONS)
    )
    if case is None:
        return None
    return _build_case_view(case)


def _build_case_view(case: models.Case) -> CaseView:
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


# --- Living platform repositories: Hearings, Polls, Votes, Comments, Reports, Corrections ---


def _build_poll_view(poll: models.Poll) -> PollView:
    case_obj = poll.__dict__.get("case")
    votes_list = poll.__dict__.get("votes")
    return PollView(
        id=str(poll.id),
        case_id=str(poll.case_id),
        case_slug=case_obj.slug if case_obj else None,
        case_title=case_obj.title if case_obj else None,
        question=poll.question,
        status=poll.status,  # type: ignore[arg-type]
        opens_at=poll.opens_at,
        closes_at=poll.closes_at,
        featured=poll.featured,
        total_votes=len(votes_list) if votes_list is not None else 0,
    )


def _build_comment_view(comment: models.Comment) -> CommentView:
    raw_replies = comment.__dict__.get("replies") or []
    return CommentView(
        id=str(comment.id),
        poll_id=str(comment.poll_id),
        parent_id=str(comment.parent_id) if comment.parent_id else None,
        handle=comment.handle,
        body=comment.body,
        status=comment.status,
        stance=comment.stance,
        upvotes=comment.upvotes,
        created_at=comment.created_at,
        replies=[_build_comment_view(r) for r in raw_replies if r.status == "visible"],
    )


async def list_polls(session: AsyncSession) -> list[models.Poll]:
    """Public poll list: includes open and closed polls on decided and published cases."""
    stmt = (
        select(models.Poll)
        .join(models.Case, models.Poll.case_id == models.Case.id)
        .where(
            models.Case.status == "decided",
            models.Case.review_state == "published",
            models.Poll.status.in_(["open", "closed"]),
        )
        .options(selectinload(models.Poll.case), selectinload(models.Poll.votes))
        .order_by(models.Poll.opens_at.desc())
    )
    return list((await session.scalars(stmt)).all())


async def list_polls_admin(session: AsyncSession) -> list[models.Poll]:
    """Admin poll list: all polls."""
    stmt = (
        select(models.Poll)
        .options(selectinload(models.Poll.case), selectinload(models.Poll.votes))
        .order_by(models.Poll.opens_at.desc())
    )
    return list((await session.scalars(stmt)).all())


async def get_poll(session: AsyncSession, poll_id: uuid.UUID) -> models.Poll | None:
    """Public poll view: requires decided and published case."""
    stmt = (
        select(models.Poll)
        .join(models.Case, models.Poll.case_id == models.Case.id)
        .where(
            models.Poll.id == poll_id,
            models.Case.status == "decided",
            models.Case.review_state == "published",
        )
        .options(selectinload(models.Poll.case), selectinload(models.Poll.votes))
    )
    return await session.scalar(stmt)


async def get_poll_admin(session: AsyncSession, poll_id: uuid.UUID) -> models.Poll | None:
    """Admin poll view: returns poll for any case."""
    return await session.scalar(
        select(models.Poll)
        .where(models.Poll.id == poll_id)
        .options(selectinload(models.Poll.case), selectinload(models.Poll.votes))
    )


async def create_poll(
    session: AsyncSession,
    case_id: uuid.UUID,
    question: str,
    opens_at: dt.datetime | None = None,
    closes_at: dt.datetime | None = None,
    featured: bool = False,
) -> models.Poll:
    poll = models.Poll(
        case_id=case_id,
        question=question,
        opens_at=opens_at or dt.datetime.now(dt.UTC),
        closes_at=closes_at,
        featured=featured,
    )
    session.add(poll)
    await session.commit()
    await session.refresh(poll)
    return poll


async def record_vote(
    session: AsyncSession,
    poll_id: uuid.UUID,
    choice: str,
    reasons: list[str],
    voter_hash: str,
) -> models.Vote:
    """Upsert vote for poll_id and voter_hash."""
    stmt = select(models.Vote).where(
        models.Vote.poll_id == poll_id, models.Vote.voter_hash == voter_hash
    )
    vote = await session.scalar(stmt)
    if vote:
        vote.choice = choice
        vote.reasons = reasons
        vote.updated_at = dt.datetime.now(dt.UTC)
    else:
        vote = models.Vote(
            poll_id=poll_id,
            choice=choice,
            reasons=reasons,
            voter_hash=voter_hash,
        )
        session.add(vote)
    await session.commit()
    await session.refresh(vote)
    return vote


async def get_vote(
    session: AsyncSession, poll_id: uuid.UUID, voter_hash: str
) -> models.Vote | None:
    stmt = select(models.Vote).where(
        models.Vote.poll_id == poll_id, models.Vote.voter_hash == voter_hash
    )
    return await session.scalar(stmt)


async def get_poll_results(session: AsyncSession, poll_id: uuid.UUID) -> PollResultsView:
    votes = list(
        (await session.scalars(select(models.Vote).where(models.Vote.poll_id == poll_id))).all()
    )
    total = len(votes)
    counts = Counter(v.choice for v in votes)
    reasons_count: Counter[str] = Counter()
    for v in votes:
        if isinstance(v.reasons, list):
            for r in v.reasons:
                reasons_count[str(r)] += 1
    return PollResultsView(
        poll_id=str(poll_id),
        total_votes=total,
        agree=counts.get("agree", 0),
        partial=counts.get("partial", 0),
        disagree=counts.get("disagree", 0),
        agree_pct=round(counts.get("agree", 0) / total * 100, 1) if total else 0.0,
        partial_pct=round(counts.get("partial", 0) / total * 100, 1) if total else 0.0,
        disagree_pct=round(counts.get("disagree", 0) / total * 100, 1) if total else 0.0,
        top_reasons=[ReasonTally(reason=r, count=c) for r, c in reasons_count.most_common(5)],
    )


async def create_comment(
    session: AsyncSession,
    poll_id: uuid.UUID,
    handle: str,
    body: str,
    voter_hash: str,
    parent_id: uuid.UUID | None = None,
    status: str = "visible",
    hold_reason: str | None = None,
    stance: str | None = None,
    themes: list[str] | None = None,
) -> models.Comment:
    comment = models.Comment(
        poll_id=poll_id,
        parent_id=parent_id,
        handle=handle,
        body=body,
        status=status,
        hold_reason=hold_reason,
        stance=stance,
        themes=themes,
        voter_hash=voter_hash,
    )
    session.add(comment)
    await session.commit()
    await session.refresh(comment)
    return comment


async def list_comments_for_poll(
    session: AsyncSession, poll_id: uuid.UUID, sort: str = "top", include_held: bool = False
) -> list[CommentView]:
    stmt = (
        select(models.Comment)
        .where(models.Comment.poll_id == poll_id, models.Comment.parent_id.is_(None))
        .options(selectinload(models.Comment.replies))
    )
    if not include_held:
        stmt = stmt.where(models.Comment.status == "visible")
    if sort == "new":
        stmt = stmt.order_by(models.Comment.created_at.desc())
    else:
        stmt = stmt.order_by(models.Comment.upvotes.desc(), models.Comment.created_at.desc())

    comments = list((await session.scalars(stmt)).all())
    return [_build_comment_view(c) for c in comments]


async def record_comment_vote(
    session: AsyncSession, comment_id: uuid.UUID, voter_hash: str
) -> bool:
    """Toggles or registers an upvote for a comment from a voter."""
    existing = await session.scalar(
        select(models.CommentVote).where(
            models.CommentVote.comment_id == comment_id,
            models.CommentVote.voter_hash == voter_hash,
        )
    )
    comment = await session.scalar(
        select(models.Comment).where(models.Comment.id == comment_id)
    )
    if not comment:
        return False
    if existing:
        await session.delete(existing)
        comment.upvotes = max(0, comment.upvotes - 1)
        await session.commit()
        return False
    else:
        session.add(models.CommentVote(comment_id=comment_id, voter_hash=voter_hash))
        comment.upvotes += 1
        await session.commit()
        return True


async def record_report(
    session: AsyncSession, comment_id: uuid.UUID, voter_hash: str, reason: str
) -> models.Report:
    report = models.Report(comment_id=comment_id, voter_hash=voter_hash, reason=reason)
    session.add(report)
    await session.flush()

    # Rule 4: 3 reports auto-hide the comment
    report_count = await session.scalar(
        select(func.count(models.Report.id)).where(models.Report.comment_id == comment_id)
    )
    if report_count and report_count >= 3:
        comment = await session.scalar(
            select(models.Comment).where(models.Comment.id == comment_id)
        )
        if comment and comment.status == "visible":
            comment.status = "held"
            comment.hold_reason = "Auto-held: 3 community reports"

    await session.commit()
    await session.refresh(report)
    return report


async def get_home_summary(session: AsyncSession) -> HomeSummaryView:
    """Aggregates featured cases, poll of the week, and live platform counters."""
    # 1. Featured published cases
    stmt = (
        select(models.Case)
        .where(models.Case.review_state == "published", models.Case.featured.is_(True))
        .options(selectinload(models.Case.gap_score))
        .order_by(models.Case.title)
    )
    featured = list((await session.scalars(stmt)).all())
    if not featured:
        # Fallback to top 2 published cases
        fallback_stmt = (
            select(models.Case)
            .where(models.Case.review_state == "published")
            .options(selectinload(models.Case.gap_score))
            .order_by(models.Case.title)
            .limit(2)
        )
        featured = list((await session.scalars(fallback_stmt)).all())

    # 2. Poll of the week (featured open poll or latest open poll)
    poll_stmt = (
        select(models.Poll)
        .join(models.Case, models.Poll.case_id == models.Case.id)
        .where(models.Case.review_state == "published", models.Case.status == "decided")
        .options(selectinload(models.Poll.case), selectinload(models.Poll.votes))
        .order_by(models.Poll.featured.desc(), models.Poll.opens_at.desc())
        .limit(1)
    )
    poll_of_week = await session.scalar(poll_stmt)

    # 3. Counters
    total_cases = await session.scalar(
        select(func.count(models.Case.id)).where(models.Case.review_state == "published")
    ) or 0
    total_votes = await session.scalar(select(func.count(models.Vote.id))) or 0
    total_comments = await session.scalar(
        select(func.count(models.Comment.id)).where(models.Comment.status == "visible")
    ) or 0
    avg_gap = await session.scalar(
        select(func.avg(models.GapScore.score))
        .join(models.Case, models.GapScore.case_id == models.Case.id)
        .where(models.Case.review_state == "published")
    )

    return HomeSummaryView(
        featured_cases=[_summary(c) for c in featured],
        poll_of_the_week=_build_poll_view(poll_of_week) if poll_of_week else None,
        counters=HomeCounters(
            total_cases=total_cases,
            total_votes=total_votes,
            total_comments=total_comments,
            avg_perception_gap=round(avg_gap, 1) if avg_gap is not None else None,
        ),
    )


async def create_correction(
    session: AsyncSession,
    case_id: uuid.UUID | None,
    kind: str,
    message: str,
    contact: str | None = None,
) -> models.Correction:
    correction = models.Correction(
        case_id=case_id, kind=kind, message=message, contact=contact
    )
    session.add(correction)
    await session.commit()
    await session.refresh(correction)
    return correction


async def list_hearings(
    session: AsyncSession, case_id: uuid.UUID
) -> list[models.Hearing]:
    stmt = (
        select(models.Hearing)
        .where(models.Hearing.case_id == case_id)
        .order_by(models.Hearing.hearing_date.desc())
    )
    return list((await session.scalars(stmt)).all())


async def patch_case(
    session: AsyncSession,
    slug: str,
    review_state: str | None = None,
    featured: bool | None = None,
    status: str | None = None,
) -> models.Case | None:
    case = await session.scalar(
        select(models.Case).where(models.Case.slug == slug).options(selectinload(models.Case.gap_score))
    )
    if not case:
        return None
    if review_state is not None:
        case.review_state = review_state
    if featured is not None:
        case.featured = featured
    if status is not None:
        case.status = status

    if case.review_state == "published" and case.status == "decided":
        existing_poll = await session.scalar(select(models.Poll).where(models.Poll.case_id == case.id))
        if not existing_poll:
            poll = models.Poll(
                case_id=case.id,
                question="Do you agree with the court's verdict?",
                status="open",
                opens_at=dt.datetime.now(dt.UTC),
            )
            session.add(poll)

    await session.commit()
    await session.refresh(case)
    return case


def _summary(case: models.Case) -> CaseSummary:
    return CaseSummary(
        slug=case.slug,
        title=case.title,
        category=case.category,
        court=case.court,
        summary=case.summary,
        is_illustrative=case.is_illustrative,
        status=case.status,
        review_state=case.review_state,
        featured=case.featured,
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
