"""Public poll, vote, comment, and report API endpoints.

All voter interactions are keyed by the signed `hetu_voter` cookie and voter_hash.
Polls are only accessible on decided and published cases.
"""

import logging
import uuid
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.limiter import limiter
from app.core.voter import generate_anonymous_handle, resolve_voter
from app.db import models, repository
from app.db.session import get_session
from app.schemas.views import (
    CommentRequest,
    CommentView,
    CommentVoteView,
    HomeSummaryView,
    PollResultsView,
    PollView,
    ReportRequest,
    ReportView,
    VoteRequest,
)
from app.services.moderation import moderate_comment

router = APIRouter(tags=["polls"])
Session = Annotated[AsyncSession, Depends(get_session)]
log = logging.getLogger("hetu.polls")


@router.get("/home", response_model=HomeSummaryView)
async def get_home(session: Session) -> HomeSummaryView:
    """Home summary: featured cases, poll of the week, and live platform counters."""
    return await repository.get_home_summary(session)


@router.get("/polls", response_model=list[PollView])
async def list_polls(session: Session) -> list[PollView]:
    """List polls for decided and published cases (including closed polls read-only)."""
    polls = await repository.list_polls(session)
    return [repository._build_poll_view(p) for p in polls]


@router.get("/polls/{poll_id}", response_model=PollView)
async def get_poll(poll_id: uuid.UUID, session: Session) -> PollView:
    """Fetch poll details. Poll must belong to a decided and published case."""
    poll = await repository.get_poll(session, poll_id)
    if not poll:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Poll not found")
    return repository._build_poll_view(poll)


@router.post("/polls/{poll_id}/vote", response_model=PollResultsView)
@limiter.limit("20/minute")
async def vote_on_poll(
    poll_id: uuid.UUID,
    request: Request,
    response: Response,
    body: VoteRequest,
    session: Session,
) -> PollResultsView:
    """Vote or update existing vote on an open poll (upsert)."""
    poll = await repository.get_poll(session, poll_id)
    if not poll:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Poll not found")
    if poll.status != "open":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This poll is closed")

    voter_hash, _ = resolve_voter(request, response)
    await repository.record_vote(
        session=session,
        poll_id=poll_id,
        choice=body.choice,
        reasons=body.reasons,
        voter_hash=voter_hash,
    )
    return await repository.get_poll_results(session, poll_id)


@router.get("/polls/{poll_id}/results", response_model=PollResultsView)
async def get_poll_results(poll_id: uuid.UUID, session: Session) -> PollResultsView:
    """Fetch aggregated results and reason tallies for a poll."""
    poll = await repository.get_poll(session, poll_id)
    if not poll:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Poll not found")
    return await repository.get_poll_results(session, poll_id)


@router.post(
    "/polls/{poll_id}/comments",
    response_model=CommentView,
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit("5/minute")
async def post_comment(
    poll_id: uuid.UUID,
    request: Request,
    response: Response,
    body: CommentRequest,
    session: Session,
) -> CommentView:
    """Create a public comment or reply under a poll with request-time moderation."""
    poll = await repository.get_poll(session, poll_id)
    if not poll:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Poll not found")

    text = body.body.strip()
    if len(text) < 3 or len(text) > 800:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Comment must be between 3 and 800 characters",
        )

    parent_uuid: uuid.UUID | None = None
    if body.parent_id:
        try:
            parent_uuid = uuid.UUID(body.parent_id)
        except ValueError as err:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Invalid parent_id",
            ) from err
        parent = await session.scalar(
            select(models.Comment).where(
                models.Comment.id == parent_uuid, models.Comment.poll_id == poll_id
            )
        )
        if not parent:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Parent comment not found")
        if parent.parent_id is not None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Replies to replies are not allowed (maximum reply depth is 1)",
            )

    voter_hash, _ = resolve_voter(request, response)

    # Moderate comment (Rule 4: strips contact details, checks wordlists, sets held on hit)
    moderation = moderate_comment(text)

    # Assign handle
    handle = (
        body.handle.strip()
        if body.handle and body.handle.strip()
        else generate_anonymous_handle(voter_hash)
    )

    comment = await repository.create_comment(
        session=session,
        poll_id=poll_id,
        handle=handle,
        body=moderation.clean_body,
        voter_hash=voter_hash,
        parent_id=parent_uuid,
        status=moderation.status,
        hold_reason=moderation.hold_reason,
    )

    # Dignified logging: no comment bodies, no raw IPs, no private names
    log.info(
        "Comment submitted (status=%s, poll_id=%s, comment_id=%s)",
        comment.status,
        poll_id,
        comment.id,
    )

    return repository._build_comment_view(comment)


@router.get("/polls/{poll_id}/comments", response_model=list[CommentView])
async def list_comments(
    poll_id: uuid.UUID,
    session: Session,
    sort: Annotated[Literal["top", "new"], Query()] = "top",
) -> list[CommentView]:
    """List visible comments for a poll (top-level comments with 1-level nested replies)."""
    poll = await repository.get_poll(session, poll_id)
    if not poll:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Poll not found")
    return await repository.list_comments_for_poll(session, poll_id, sort=sort)


@router.post("/comments/{comment_id}/upvote", response_model=CommentVoteView)
async def upvote_comment(
    comment_id: uuid.UUID,
    request: Request,
    response: Response,
    session: Session,
) -> CommentVoteView:
    """Toggle upvote for a comment from this voter."""
    comment = await session.scalar(select(models.Comment).where(models.Comment.id == comment_id))
    if not comment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Comment not found")

    voter_hash, _ = resolve_voter(request, response)
    upvoted = await repository.record_comment_vote(session, comment_id, voter_hash)
    await session.refresh(comment)
    return CommentVoteView(upvoted=upvoted, upvotes=comment.upvotes)


@router.post("/comments/{comment_id}/report", response_model=ReportView)
@limiter.limit("10/minute")
async def report_comment(
    comment_id: uuid.UUID,
    request: Request,
    response: Response,
    body: ReportRequest,
    session: Session,
) -> ReportView:
    """Report a comment. 3 unique reports auto-hide the comment from the public."""
    comment = await session.scalar(select(models.Comment).where(models.Comment.id == comment_id))
    if not comment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Comment not found")

    voter_hash, _ = resolve_voter(request, response)

    existing = await session.scalar(
        select(models.Report).where(
            models.Report.comment_id == comment_id,
            models.Report.voter_hash == voter_hash,
        )
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You have already reported this comment",
        )

    await repository.record_report(
        session=session,
        comment_id=comment_id,
        voter_hash=voter_hash,
        reason=body.reason.strip(),
    )
    log.info("Comment reported (comment_id=%s)", comment_id)
    return ReportView(status="reported", comment_id=str(comment_id))
