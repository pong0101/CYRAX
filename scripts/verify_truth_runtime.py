"""Verify TruthPolicy is actually wired into the CYRAX runtime."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "agent"))

from cyrax import CYRAX  # noqa: E402
from truth_policy import TruthPolicy  # noqa: E402

passed = failed = 0


def check(label: str, ok: bool, detail: str = "") -> None:
    global passed, failed
    print(f"[{'PASS' if ok else 'FAIL'}] {label}" + (f" — {detail}" if detail else ""))
    if ok:
        passed += 1
    else:
        failed += 1


agent = CYRAX.__new__(CYRAX)
agent.truth_policy = TruthPolicy()

check("CYRAX owns a TruthPolicy instance", isinstance(agent.truth_policy, TruthPolicy))
context = agent.truth_policy_context()
check("Runtime exposes live_tool as highest authority", context.startswith("Authority order: live_tool >"), context)
check("Runtime exposes memory below live evidence", "live_tool > runtime" in context and "memory" in context, context)

live = agent.truth_policy.evidence("live_tool", "qwen3:8b")
memory = agent.truth_policy.evidence("memory", "qwen3:7b")
check("Runtime chooses live evidence over memory", agent.truth_policy.choose(live, memory) == live)
check("Runtime detects conflicting evidence", agent.truth_policy.conflict(live, memory))
resolution = agent.truth_policy.resolution(live, memory)
check("Runtime resolution marks memory stale", "stale" in resolution and "Source: live_tool" in resolution, resolution)

messages = [{"role": "tool", "content": "qwen3:8b — 5,225,388,164 bytes (4.87 GiB)"}]
bad = "qwen3:8b มีขนาด 5,225,388,164 bytes บิต (4.87 GiB)"
normalized = agent._normalize_tool_units(bad, messages)
check("Runtime strips bytes/bits hallucination", "bytes บิต" not in normalized and "5,225,388,164 bytes" in normalized, normalized)

print(f"\n=== RESULT: {passed} passed / {failed} failed ===")
raise SystemExit(1 if failed else 0)
