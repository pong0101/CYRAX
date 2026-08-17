"""Deterministic conflict detection between current evidence and memories."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from truth_policy import Evidence, TruthPolicy


@dataclass(frozen=True)
class Conflict:
    field: str
    winner: Evidence
    losing: tuple[Evidence, ...]

    @property
    def detected(self) -> bool:
        return bool(self.losing)


class MemoryConflictResolver:
    """Resolve fact conflicts without asking the LLM to choose a source."""

    def __init__(self, truth_policy: TruthPolicy | None = None):
        self.truth_policy = truth_policy or TruthPolicy()

    def detect(self, field: str, evidence: Iterable[Evidence]) -> Conflict | None:
        items = tuple(item for item in evidence if item.value != "")
        if not items:
            return None
        winner = self.truth_policy.choose(*items)
        if winner is None:
            return None
        losing = tuple(item for item in items if item.value != winner.value)
        return Conflict(field=field, winner=winner, losing=losing)

    def resolve(self, field: str, evidence: Iterable[Evidence]) -> str:
        conflict = self.detect(field, evidence)
        if conflict is None:
            return "No evidence available."
        if not conflict.detected:
            return f"Use {conflict.winner.value} [Source: {conflict.winner.source}]."
        losers = ", ".join(
            f"{item.value} [{item.source}]" for item in conflict.losing
        )
        return (
            f"Use {conflict.winner.value} [Source: {conflict.winner.source}]. "
            f"Conflicting evidence: {losers}. Lower-authority evidence is stale or historical."
        )

    @staticmethod
    def memory_evidence(value: str, path: str, authority: int = 50) -> Evidence:
        """Create memory evidence while retaining its file path for resolution logs."""
        return Evidence(source="memory", value=value, authority=authority, note=path)
