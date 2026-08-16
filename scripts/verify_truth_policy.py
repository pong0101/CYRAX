"""Verify deterministic evidence authority and conflict resolution."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "agent"))

from truth_policy import TruthPolicy  # noqa: E402

policy = TruthPolicy()
passed = failed = 0


def check(label: str, ok: bool, detail: str = "") -> None:
    global passed, failed
    print(f"[{'PASS' if ok else 'FAIL'}] {label}" + (f" — {detail}" if detail else ""))
    if ok:
        passed += 1
    else:
        failed += 1


live = policy.evidence("live_tool", "qwen3:8b")
memory = policy.evidence("memory", "qwen3:7b")
runtime = policy.evidence("runtime", "qwen3:8b")
history = policy.evidence("history", "qwen2:7b")

check("Live tool outranks memory", policy.choose(live, memory) == live)
check("Runtime outranks memory", policy.choose(runtime, memory) == runtime)
check("Live tool outranks runtime", policy.choose(live, runtime) == live)
check("Conflict is detected", policy.conflict(live, memory))
check("No conflict for equal values", not policy.conflict(live, runtime))
check("Historical evidence is lower authority", history.authority < memory.authority)
resolution = policy.resolution(live, memory)
check("Conflict resolution names live source", "Source: live_tool" in resolution, resolution)
check("Conflict resolution marks lower evidence stale", "stale" in resolution, resolution)

print(f"\n=== RESULT: {passed} passed / {failed} failed ===")
raise SystemExit(1 if failed else 0)
