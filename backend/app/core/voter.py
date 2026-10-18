"""Voter identification via signed HttpOnly cookie and HMAC hash.

Never stores raw IPs or personal identifiers.
"""

import hashlib
import hmac
import secrets
import uuid

from fastapi import Request, Response

from app.core.config import get_settings, secret

COOKIE_NAME = "hetu_voter"
COOKIE_MAX_AGE = 365 * 24 * 3600  # 1 year


def get_voter_secret() -> bytes:
    settings = get_settings()
    val = secret(settings.voter_hash_secret) or "hetu-dev-voter-secret"
    return val.encode("utf-8")


def sign_token(raw_id: str, secret_bytes: bytes) -> str:
    sig = hmac.new(secret_bytes, raw_id.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"{raw_id}.{sig}"


def verify_token(token: str, secret_bytes: bytes) -> str | None:
    if not token or "." not in token:
        return None
    raw_id, sig = token.split(".", 1)
    expected = hmac.new(secret_bytes, raw_id.encode("utf-8"), hashlib.sha256).hexdigest()
    if secrets.compare_digest(sig, expected):
        return raw_id
    return None


def get_voter_hash_from_id(raw_id: str, secret_bytes: bytes) -> str:
    """HMAC-SHA256 hash of the voter ID."""
    return hmac.new(secret_bytes, f"voter:{raw_id}".encode(), hashlib.sha256).hexdigest()


def resolve_voter(request: Request, response: Response) -> tuple[str, str]:
    """Retrieve or create signed voter cookie, returning (voter_hash, raw_id).

    Sets the `hetu_voter` cookie on the response if not already present or invalid.
    """
    secret_bytes = get_voter_secret()
    raw_cookie = request.cookies.get(COOKIE_NAME)
    raw_id = verify_token(raw_cookie, secret_bytes) if raw_cookie else None

    if not raw_id:
        raw_id = uuid.uuid4().hex
        cookie_value = sign_token(raw_id, secret_bytes)
        response.set_cookie(
            key=COOKIE_NAME,
            value=cookie_value,
            max_age=COOKIE_MAX_AGE,
            httponly=True,
            samesite="lax",
            path="/",
        )

    voter_hash = get_voter_hash_from_id(raw_id, secret_bytes)
    return voter_hash, raw_id


def generate_anonymous_handle(voter_hash: str) -> str:
    """Deterministic, dignified anonymous civic handle (e.g. 'Citizen 4821')."""
    num = int(voter_hash[:4], 16) % 9000 + 1000
    return f"Citizen {num}"
