"""Runtime-to-memory reconciliation for high-confidence CYRAX facts."""
from __future__ import annotations

import re
from dataclasses import dataclass

from memory.conflict import MemoryConflictResolver
from memory.manager import MemoryManager
from truth_policy import TruthPolicy


MODEL_CLAIM_PATTERNS = (
    re.compile(r"\bmain\s+(?:model|llm)\b\s*(?:is|=|:)\s*([A-Za-z0-9._/-]+:[A-Za-z0-9._-]+)", re.IGNORECASE),
    re.compile(r"\b(?:active|current)\s+model\b\s*(?:is|=|:)\s*([A-Za-z0-9._/-]+:[A-Za-z0-9._-]+)", re.IGNORECASE),
    re.compile(r"โมเดลหลัก(?:ของ\s*CYRAX)?\s*(?:คือ|=|:)\s*([A-Za-z0-9._/-]+:[A-Za-z0-9._-]+)", re.IGNORECASE),
    re.compile(r"(?:CYRAX\s+)?ใช้โมเดลหลัก\s*(?:คือ|=|:)\s*([A-Za-z0-9._/-]+:[A-Za-z0-9._-]+)", re.IGNORECASE),
)


@dataclass(frozen=True)
class Reconciliation:
    path: str
    claimed_value: str
    runtime_value: str
    status: str


def extract_main_model_claims(text: str) -> tuple[str, ...]:
    """Extract only explicit main/current-model claims; ignore casual model mentions."""
    claims: list[str] = []
    for pattern in MODEL_CLAIM_PATTERNS:
        claims.extend(pattern.findall(text))
    return tuple(dict.fromkeys(claims))


def reconcile_main_model(
    memory: MemoryManager,
    runtime_model: str,
    *,
    limit: int = 10,
    resolver: MemoryConflictResolver | None = None,
) -> list[Reconciliation]:
    """Mark active memories stale when runtime model evidence supersedes them."""
    policy = resolver or MemoryConflictResolver(TruthPolicy())
    reconciled: list[Reconciliation] = []
    for item in memory.search("main model", limit=max(1, min(limit, 25))):
        evidence = item.get("evidence", {})
        if evidence.get("status", "active") != "active":
            continue
        claims = extract_main_model_claims(str(item.get("content", "")))
        for claimed in claims:
            if claimed == runtime_model:
                continue
            conflict = policy.detect(
                "main_model",
                [
                    policy.memory_evidence(claimed, str(item["path"])),
                    policy.truth_policy.evidence("runtime", runtime_model),
                ],
            )
            if conflict is None or not conflict.detected or conflict.winner.source != "runtime":
                continue
            memory.mark_status(
                str(item["path"]),
                "stale",
                superseded_by=f"runtime:main_model={runtime_model}",
            )
            reconciled.append(
                Reconciliation(
                    path=str(item["path"]),
                    claimed_value=claimed,
                    runtime_value=runtime_model,
                    status="stale",
                )
            )
    return reconciled
