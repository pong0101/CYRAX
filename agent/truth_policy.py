"""Explicit source-authority policy for CYRAX.

The policy is intentionally small and deterministic. It describes which source
wins when facts conflict; it does not fetch data or decide what a user means.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Evidence:
    source: str
    value: str
    authority: int
    note: str = ""


class TruthPolicy:
    """Rank evidence sources for current-vs-historical CYRAX facts."""

    AUTHORITY = {
        "live_tool": 100,
        "runtime": 90,
        "project_file": 80,
        "user_statement": 70,
        "memory": 50,
        "history": 30,
        "llm_knowledge": 20,
    }

    def evidence(self, source: str, value: str, note: str = "") -> Evidence:
        return Evidence(source, value, self.AUTHORITY.get(source, 0), note)

    def choose(self, *evidence: Evidence) -> Evidence | None:
        """Return the highest-authority evidence, preserving input order on ties."""
        if not evidence:
            return None
        return max(enumerate(evidence), key=lambda item: (item[1].authority, -item[0]))[1]

    def conflict(self, *evidence: Evidence) -> bool:
        """Return True when evidence disagrees on value."""
        values = {item.value for item in evidence if item.value != ""}
        return len(values) > 1

    def resolution(self, *evidence: Evidence) -> str:
        """Return a deterministic human-readable resolution for conflicting facts."""
        winner = self.choose(*evidence)
        if winner is None:
            return "No evidence available."
        if not self.conflict(*evidence):
            return f"Use {winner.value} [Source: {winner.source}]."
        return (
            f"Use {winner.value} [Source: {winner.source}]. "
            f"Conflicting lower-authority evidence should be treated as stale or historical."
        )
