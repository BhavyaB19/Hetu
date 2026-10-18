"""The interface every source agent implements."""

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass

from app.schemas.bundle import SourceDocument


class AgentError(RuntimeError):
    """An agent could not collect its sources."""


@dataclass(frozen=True)
class CaseQuery:
    name: str
    court: str | None = None
    category: str = "Criminal Law"

    @property
    def slug(self) -> str:
        return re.sub(r"[^a-z0-9]+", "-", self.name.lower()).strip("-")

    @property
    def search_text(self) -> str:
        return f"{self.name} {self.court}" if self.court else self.name


class BaseAgent(ABC):
    """Collects source documents for a case. Swappable for a fake in tests."""

    name: str

    @abstractmethod
    async def run(self, query: CaseQuery) -> list[SourceDocument]: ...
