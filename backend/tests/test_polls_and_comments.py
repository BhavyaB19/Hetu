import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.db import models
from app.db.repository import create_poll, save_case
from app.db.session import SessionLocal
from app.main import app
from app.schemas.views import CommentView, CorrectionView, VoteView
from app.services.moderation import moderate_comment
from app.services.pipeline import anonymize
from app.services.scoring import perception_gap

pytestmark = pytest.mark.usefixtures("clean_database")

ADMIN_HEADERS = {"X-Admin-Key": "hetu-dev-admin-key"}


@pytest.fixture
async def published_case(demo):
    bundle = anonymize(demo, [])
    async with SessionLocal() as session:
        await save_case(session, bundle, perception_gap(bundle), status="decided", review_state="published")
    return bundle.case.slug


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


async def test_auto_poll_on_publish(client, demo):
    # 1. Save case as draft initially
    bundle = anonymize(demo, [])
    async with SessionLocal() as session:
        await save_case(session, bundle, perception_gap(bundle), status="decided", review_state="draft")

        # Verify no poll exists for draft case
        case = await session.scalar(select(models.Case).where(models.Case.slug == bundle.case.slug))
        poll = await session.scalar(select(models.Poll).where(models.Poll.case_id == case.id))
        assert poll is None

    # 2. Admin publishes the case via PATCH
    res = await client.patch(
        f"/admin/cases/{bundle.case.slug}",
        headers=ADMIN_HEADERS,
        json={"review_state": "published"},
    )
    assert res.status_code == 200

    # 3. Verify poll was auto-created
    async with SessionLocal() as session:
        case = await session.scalar(select(models.Case).where(models.Case.slug == bundle.case.slug))
        poll = await session.scalar(select(models.Poll).where(models.Poll.case_id == case.id))
        assert poll is not None
        assert poll.question == "Do you agree with the court's verdict?"
        assert poll.status == "open"


async def test_poll_on_ongoing_case_rejected_by_database(client, demo):
    bundle = anonymize(demo, [])
    async with SessionLocal() as session:
        await save_case(session, bundle, perception_gap(bundle), status="ongoing", review_state="draft")
        case = await session.scalar(select(models.Case).where(models.Case.slug == bundle.case.slug))

        # Attempting to create poll on ongoing case violates DB trigger trg_poll_case_eligible
        async with session.begin_nested():
            with pytest.raises(Exception, match="A poll can only be created for a decided, published case"):
                await create_poll(session, case_id=case.id, question="Invalid poll")


async def test_list_polls_includes_closed_polls_read_only(client, published_case):
    # Fetch public polls list
    res = await client.get("/polls")
    assert res.status_code == 200
    polls = res.json()
    assert len(polls) == 1
    poll_id = polls[0]["id"]
    assert polls[0]["status"] == "open"

    # Close poll via database
    async with SessionLocal() as session:
        poll = await session.scalar(select(models.Poll).where(models.Poll.case_id == models.Case.id))
        poll.status = "closed"
        await session.commit()

    # Closed poll remains visible in public listing
    res2 = await client.get("/polls")
    assert res2.status_code == 200
    assert len(res2.json()) == 1
    assert res2.json()[0]["status"] == "closed"

    # Voting on closed poll is rejected
    vote_res = await client.post(
        f"/polls/{poll_id}/vote",
        json={"choice": "agree", "reasons": ["Valid reason"]},
    )
    assert vote_res.status_code == 400
    assert "closed" in vote_res.json()["detail"].lower()


async def test_vote_upsert_and_signed_cookie(client, published_case):
    res = await client.get("/polls")
    poll_id = res.json()[0]["id"]

    # 1. First vote without cookie: response must set hetu_voter cookie
    vote_res1 = await client.post(
        f"/polls/{poll_id}/vote",
        json={"choice": "agree", "reasons": ["Sentence was appropriate"]},
    )
    assert vote_res1.status_code == 200
    assert "hetu_voter" in vote_res1.cookies
    results1 = vote_res1.json()
    assert results1["total_votes"] == 1
    assert results1["agree"] == 1
    assert results1["agree_pct"] == 100.0

    # 2. Changing vote with same cookie updates existing vote (upsert)
    cookie_val = vote_res1.cookies["hetu_voter"]
    vote_res2 = await client.post(
        f"/polls/{poll_id}/vote",
        cookies={"hetu_voter": cookie_val},
        json={"choice": "disagree", "reasons": ["Procedure was unfair"]},
    )
    assert vote_res2.status_code == 200
    results2 = vote_res2.json()
    assert results2["total_votes"] == 1
    assert results2["agree"] == 0
    assert results2["disagree"] == 1
    assert results2["disagree_pct"] == 100.0


async def test_moderation_rules_and_held_visibility(client, published_case):
    res = await client.get("/polls")
    poll_id = res.json()[0]["id"]

    # Validation: too short
    short_res = await client.post(f"/polls/{poll_id}/comments", json={"body": "no"})
    assert short_res.status_code == 422

    # Validation: too long
    long_res = await client.post(f"/polls/{poll_id}/comments", json={"body": "x" * 801})
    assert long_res.status_code == 422

    # PII stripping: email and phone stripped to tags
    pii_res = await client.post(
        f"/polls/{poll_id}/comments",
        json={"body": "Contact me at advocate@example.com or call 9876543210 immediately."},
    )
    assert pii_res.status_code == 201
    assert "[EMAIL]" in pii_res.json()["body"]
    assert "[PHONE]" in pii_res.json()["body"]
    assert pii_res.json()["status"] == "visible"

    # Abuse / Judge attack keyword: marked held
    attack_res = await client.post(
        f"/polls/{poll_id}/comments",
        json={"body": "The corrupt judge was bribed to give this judgment!"},
    )
    assert attack_res.status_code == 201
    assert attack_res.json()["status"] == "held"

    # Hindi Hinglish attack keyword: marked held
    hinglish_res = await client.post(
        f"/polls/{poll_id}/comments",
        json={"body": "Yeh sab bikau judge hain aur gaddar hain."},
    )
    assert hinglish_res.status_code == 201
    assert hinglish_res.json()["status"] == "held"

    # Public comments list only returns status='visible', held comments are invisible
    list_res = await client.get(f"/polls/{poll_id}/comments")
    assert list_res.status_code == 200
    comment_bodies = [c["body"] for c in list_res.json()]
    assert any("[EMAIL]" in b for b in comment_bodies)
    assert not any("corrupt judge" in b for b in comment_bodies)
    assert not any("bikau judge" in b for b in comment_bodies)


def test_moderation_masks_registered_private_names():
    res = moderate_comment(
        body="Ravi Sharma told Pooja Verma that he was innocent.",
        private_names=["Ravi Sharma", "Pooja Verma"],
    )
    assert res.clean_body == "[ANONYMIZED] told [ANONYMIZED] that he was innocent."
    assert res.status == "visible"


async def test_comments_one_level_replies(client, published_case):
    res = await client.get("/polls")
    poll_id = res.json()[0]["id"]

    # Post top-level comment
    top_res = await client.post(
        f"/polls/{poll_id}/comments",
        json={"body": "This is a thoughtful analysis of the court's reasoning."},
    )
    assert top_res.status_code == 201
    parent_id = top_res.json()["id"]

    # Reply to top-level comment (depth 1)
    reply_res = await client.post(
        f"/polls/{poll_id}/comments",
        json={"body": "I agree with your point about the evidence.", "parent_id": parent_id},
    )
    assert reply_res.status_code == 201
    reply_id = reply_res.json()["id"]

    # Verify reply appears under parent in list
    list_res = await client.get(f"/polls/{poll_id}/comments")
    top_comment = next(c for c in list_res.json() if c["id"] == parent_id)
    assert len(top_comment["replies"]) == 1
    assert top_comment["replies"][0]["id"] == reply_id

    # Nested reply to reply (depth 2) is rejected
    nested_res = await client.post(
        f"/polls/{poll_id}/comments",
        json={"body": "Replying to a reply is not allowed.", "parent_id": reply_id},
    )
    assert nested_res.status_code == 422
    assert "depth is 1" in nested_res.json()["detail"]


async def test_comment_upvote_toggle(client, published_case):
    res = await client.get("/polls")
    poll_id = res.json()[0]["id"]

    comment_res = await client.post(
        f"/polls/{poll_id}/comments",
        json={"body": "Upvote test comment for checking toggle behavior."},
    )
    comment_id = comment_res.json()["id"]
    cookie = comment_res.cookies["hetu_voter"]

    # First upvote: adds vote
    up_res1 = await client.post(f"/comments/{comment_id}/upvote", cookies={"hetu_voter": cookie})
    assert up_res1.status_code == 200
    assert up_res1.json() == {"upvoted": True, "upvotes": 1}

    # Second upvote: removes vote (toggle)
    up_res2 = await client.post(f"/comments/{comment_id}/upvote", cookies={"hetu_voter": cookie})
    assert up_res2.status_code == 200
    assert up_res2.json() == {"upvoted": False, "upvotes": 0}


async def test_three_reports_auto_hide_comment(client, published_case):
    res = await client.get("/polls")
    poll_id = res.json()[0]["id"]

    comment_res = await client.post(
        f"/polls/{poll_id}/comments",
        json={"body": "Harassing or inappropriate comment to be reported by community."},
    )
    comment_id = comment_res.json()["id"]

    from app.core.voter import get_voter_secret, sign_token

    secret_bytes = get_voter_secret()
    cookie1 = sign_token("voter1", secret_bytes)
    cookie2 = sign_token("voter2", secret_bytes)
    cookie3 = sign_token("voter3", secret_bytes)

    # Voter 1 reports
    rep1 = await client.post(
        f"/comments/{comment_id}/report",
        cookies={"hetu_voter": cookie1},
        json={"reason": "Spam and inappropriate"},
    )
    assert rep1.status_code == 200

    # Duplicate report from same voter is rejected
    dup = await client.post(
        f"/comments/{comment_id}/report",
        cookies={"hetu_voter": cookie1},
        json={"reason": "Spam again"},
    )
    assert dup.status_code == 400

    # Voter 2 reports
    rep2 = await client.post(
        f"/comments/{comment_id}/report",
        cookies={"hetu_voter": cookie2},
        json={"reason": "Harassment"},
    )
    assert rep2.status_code == 200

    # Still visible after 2 reports
    list1 = await client.get(f"/polls/{poll_id}/comments")
    assert any(c["id"] == comment_id for c in list1.json())

    # Voter 3 reports -> hits 3 reports threshold
    rep3 = await client.post(
        f"/comments/{comment_id}/report",
        cookies={"hetu_voter": cookie3},
        json={"reason": "Violation of community rules"},
    )
    assert rep3.status_code == 200

    # Auto-hidden: no longer visible publicly
    list2 = await client.get(f"/polls/{poll_id}/comments")
    assert not any(c["id"] == comment_id for c in list2.json())

    # Status in database is held
    async with SessionLocal() as session:
        db_comment = await session.scalar(select(models.Comment).where(models.Comment.id == comment_id))
        assert db_comment.status == "held"
        assert "3 community reports" in db_comment.hold_reason


async def test_home_summary_endpoint(client, published_case):
    res = await client.get("/home")
    assert res.status_code == 200
    data = res.json()
    assert "featured_cases" in data
    assert "poll_of_the_week" in data
    assert "counters" in data
    assert data["counters"]["total_cases"] >= 1


def test_response_models_never_leak_voter_hash_or_contact():
    # Rule 7: Response models must never include corrections.contact or voter_hash
    assert "voter_hash" not in VoteView.model_fields
    assert "voter_hash" not in CommentView.model_fields
    assert "contact" not in CorrectionView.model_fields
    assert "voter_hash" not in CorrectionView.model_fields
