"""Structured provenance metadata for durable CYRAX memory."""
from __future__ import annotations

from dataclasses import dataclass


VALID_STATUSES = {"active", "stale", "contradicted"}


@dataclass(frozen=True)
class MemoryEvidence:
    """Human-readable provenance attached to a durable memory."""

    source: str = "CYRAX"
    created: str = ""
    updated: str = ""
    last_verified: str = ""
    memory_type: str = "memory"
    confidence: str = "HIGH"
    status: str = "active"
    superseded_by: str = ""

    def normalized(self) -> "MemoryEvidence":
        status = self.status.strip().lower() or "active"
        if status not in VALID_STATUSES:
            status = "active"
        return MemoryEvidence(
            source=self.source.strip() or "CYRAX",
            created=self.created.strip(),
            updated=self.updated.strip(),
            last_verified=self.last_verified.strip(),
            memory_type=self.memory_type.strip() or "memory",
            confidence=self.confidence.strip().upper() or "HIGH",
            status=status,
            superseded_by=self.superseded_by.strip(),
        )

    def to_frontmatter(self) -> str:
        value = self.normalized()
        return (
            "---\n"
            f"created: {value.created}\n"
            f"updated: {value.updated}\n"
            f"last_verified: {value.last_verified}\n"
            f"type: {value.memory_type}\n"
            f"confidence: {value.confidence}\n"
            f"source: {value.source}\n"
            f"status: {value.status}\n"
            f"superseded_by: {value.superseded_by}\n"
            "---\n\n"
        )
