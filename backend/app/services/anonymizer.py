"""Remove personal data before anything is stored.

Two passes:
1. Named private individuals (accused, victims, witnesses, relatives, minors)
   become stable placeholders such as [VICTIM_1]. The names come from the LLM
   extraction step, which lists every private person it sees.
2. Contact details and identifiers (phones, emails, social handles, Aadhaar-style
   numbers) are replaced by type tags such as [PHONE].

The same Anonymizer instance is used for a whole case so a person keeps one
placeholder across the judgment, the news coverage and public reactions.
"""

import re
from typing import Any, Literal

from pydantic import BaseModel

Role = Literal["accused", "victim", "witness", "relative", "minor", "other"]

PII_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("[EMAIL]", re.compile(r"\b[\w.+-]+@[\w-]+(?:\.[\w-]+)+\b")),
    ("[AADHAAR]", re.compile(r"\b\d{4}[ -]\d{4}[ -]\d{4}\b")),
    # Indian mobile numbers: optional +91/0 prefix, 10 digits starting 6-9, with spaces or dashes.
    ("[PHONE]", re.compile(r"(?<![\w+])(?:\+91[\s-]?|0)?[6-9]\d{4}[\s-]?\d{5}\b")),
    ("[HANDLE]", re.compile(r"(?<![\w@])@[A-Za-z0-9_]{3,30}\b")),
]


class Person(BaseModel):
    name: str
    role: Role
    aliases: list[str] = []


class Anonymizer:
    def __init__(self) -> None:
        self._placeholder_for: dict[str, str] = {}
        self._counts: dict[str, int] = {}

    def register(self, person: Person) -> str:
        """Assign (or reuse) a placeholder for a person and all their aliases."""
        names = [person.name, *person.aliases]
        for name in names:
            existing = self._placeholder_for.get(_key(name))
            if existing:
                break
        else:
            role = person.role.upper()
            self._counts[role] = self._counts.get(role, 0) + 1
            existing = f"[{role}_{self._counts[role]}]"
        for name in names:
            if len(_key(name)) >= 3:
                self._placeholder_for.setdefault(_key(name), existing)
        return existing

    def text(self, value: str) -> str:
        # Longest names first so "Ravi Kumar" wins over "Ravi".
        for name in sorted(self._placeholder_for, key=len, reverse=True):
            # Any run of whitespace between name parts: judgments often wrap a name across lines.
            parts = r"\s+".join(re.escape(part) for part in name.split())
            pattern = re.compile(rf"(?<!\w){parts}(?!\w)", re.IGNORECASE)
            value = pattern.sub(self._placeholder_for[name], value)
        for tag, pattern in PII_PATTERNS:
            value = pattern.sub(tag, value)
        return value

    def deep(self, value: Any, skip: frozenset[str] = frozenset()) -> Any:
        """Apply `text` to every string in nested dicts and lists, except under `skip` keys."""
        if isinstance(value, str):
            return self.text(value)
        if isinstance(value, list):
            return [self.deep(v, skip) for v in value]
        if isinstance(value, dict):
            return {k: v if k in skip else self.deep(v, skip) for k, v in value.items()}
        return value


def _key(name: str) -> str:
    return re.sub(r"\s+", " ", name).strip().lower()
