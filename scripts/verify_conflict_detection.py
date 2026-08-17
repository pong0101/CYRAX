"""Verify deterministic conflict detection and durable stale-memory transitions."""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "agent"))

from memory.conflict import MemoryConflictResolver  # noqa: E402
from memory.manager import MemoryManager  # noqa: E402
from truth_policy import TruthPolicy  # noqa: E402

passed = failed = 0


def check(label: str, ok: bool, detail: str = "") -> None:
    global passed, failed
    print(f"[{'PASS' if ok else 'FAIL'}] {label}" + (f" — {detail}" if detail else ""))
    if ok:
        passed += 1
    else:
        failed += 1


policy = TruthPolicy()
resolver = MemoryConflictResolver(policy)
live = policy.evidence("live_tool", "qwen3:14b")
memory = resolver.memory_evidence("qwen3:8b", "01_Memory/main-model.md")
conflict = resolver.detect("main_model", [memory, live])

check("Conflict detector finds disagreement", conflict is not None and conflict.detected)
check("Live evidence wins", conflict is not None and conflict.winner == live)
check(
    "Lower memory evidence is identified",
    conflict is not None and len(conflict.losing) == 1 and conflict.losing[0] == memory,
)
resolution = resolver.resolve("main_model", [memory, live])
check("Resolution names live source", "Source: live_tool" in resolution, resolution)
check("Resolution marks lower evidence stale", "stale" in resolution, resolution)

with tempfile.TemporaryDirectory() as temp:
    manager = MemoryManager(temp)
    path = manager.remember(
        "main-model",
        "CYRAX main model is qwen3:8b.",
        memory_type="project",
    )
    manager.mark_status(path, "stale", superseded_by="live_tool:main_model=qwen3:14b")
    evidence = manager._parse_frontmatter(path.read_text(encoding="utf-8"))
    check("Memory status becomes stale", evidence.status == "stale")
    check(
        "Stale memory records its replacement",
        evidence.superseded_by == "live_tool:main_model=qwen3:14b",
    )
    results, _ = manager.search("main model")
    check("Search exposes evidence metadata", bool(results) and results[0]["evidence"]["status"] == "stale")

print(f"\n=== RESULT: {passed} passed / {failed} failed ===")
raise SystemExit(1 if failed else 0)
