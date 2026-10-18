"""TinyFish web agents that collect a case's sources: the judgment, news coverage and
public reader comments. `collect()` runs them and returns an unextracted case bundle."""

from app.agents.runner import collect

__all__ = ["collect"]
