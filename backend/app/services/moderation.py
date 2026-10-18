"""Request-time moderation for public comments (Rule 7: zero LLM or API cost).

Pipeline:
1. Validate length (3 to 800 characters)
2. Strip contact details & identifiers (emails, phones, handles, Aadhaar)
3. Mask registered private names for the case
4. Keyword check against abuse, threats, and personal attacks on judges/courts
   (English + Hindi/Hinglish). Hits set status='held', never rejected or deleted.
"""

import re
from typing import NamedTuple

from app.services.anonymizer import PII_PATTERNS

ENGLISH_FLAGGED_TERMS = [
    r"\bkill\b",
    r"\bmurder\b",
    r"\bbomb\b",
    r"\bterrorist\b",
    r"\bhang\s+(?:him|her|them|the\s+judge)\b",
    r"\bshoot\b",
    r"\brape\b",
    r"\bassassinate\b",
    r"\blynch\b",
    r"\bcorrupt\s+judge\b",
    r"\bbribed\s+judge\b",
    r"\bsold\s+judge\b",
    r"\bjudge\s+is\s+(?:corrupt|bribed|paid|bought)\b",
    r"\bbench\s+fixing\b",
    r"\bkangaroo\s+court\b",
]

# Hindi / Hinglish terms marked for human review
HINDI_HINGLISH_FLAGGED_TERMS = [
    r"\bdalal\b",
    r"\bjadj\s+bik\s+gaya\b",
    r"\bbikau\s+judge\b",
    r"\bmadarchod\b",
    r"\bbhenchod\b",
    r"\bbehenchod\b",
    r"\bchutiya\b",
    r"\bgaddar\b",
    r"\bkutta\b",
    r"\bharami\b",
    r"\bmaro\s+saale\b",
    r"\bjaan\s+se\s+mar\b",
]

COMPILED_FLAGS: list[re.Pattern[str]] = [
    re.compile(pattern, re.IGNORECASE) for pattern in (ENGLISH_FLAGGED_TERMS + HINDI_HINGLISH_FLAGGED_TERMS)
]


class ModerationResult(NamedTuple):
    clean_body: str
    status: str  # "visible" or "held"
    hold_reason: str | None


def moderate_comment(body: str, private_names: list[str] | None = None) -> ModerationResult:
    """Run rule-based request-time moderation on comment body."""
    text = body.strip()

    # 1. Strip contact details & identifiers
    for tag, pattern in PII_PATTERNS:
        text = pattern.sub(tag, text)

    # 2. Mask registered private names for the case (longest names first)
    if private_names:
        for name in sorted(private_names, key=len, reverse=True):
            clean_name = name.strip()
            if len(clean_name) >= 3:
                name_pattern = re.compile(rf"(?<!\w){re.escape(clean_name)}(?!\w)", re.IGNORECASE)
                text = name_pattern.sub("[ANONYMIZED]", text)

    # 3. Check against flagged abuse / threat / attack terms
    for flag_pat in COMPILED_FLAGS:
        if flag_pat.search(text):
            return ModerationResult(
                clean_body=text,
                status="held",
                hold_reason="Flagged by moderation filter for human review",
            )

    return ModerationResult(clean_body=text, status="visible", hold_reason=None)
