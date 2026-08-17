"""Focused verification for Phase 2 memory provenance."""
from __future__ import annotations

from memory.evidence import MemoryEvidence
from memory.manager import MemoryManager


def check(name: str, condition: bool, detail: str = "") -> bool:
    if condition:
        print(f"[PASS] {name}" + (f" — {detail}" if detail else ""))
        return True
    print(f"[FAIL] {name}" + (f" — {detail}" if detail else ""))
    return False


def main() -> int:
    total = 0
    passed = 0

    sample = (
        "---\n"
        "created: 2026-08-17T09:00:00+07:00\n"
        "updated: 2026-08-17T09:10:00+07:00\n"
        "last_verified: 2026-08-17T09:10:00+07:00\n"
        "type: project\n"
        "confidence: HIGH\n"
        "source: user\n"
        "status: stale\n"
        "superseded_by: live://machine-state/123\n"
        "---\n\n# Example\n\nCYRAX memory.\n"
    )
    evidence = MemoryManager._parse_frontmatter(sample)

    tests = [
        ("Frontmatter source is preserved", evidence.source == "user", evidence.source),
        ("Verification timestamp is preserved", evidence.last_verified.startswith("2026-08-17"), evidence.last_verified),
        ("Memory type is preserved", evidence.memory_type == "project", evidence.memory_type),
        ("Confidence is normalized", evidence.confidence == "HIGH", evidence.confidence),
        ("Stale status is preserved", evidence.status == "stale", evidence.status),
        ("Superseding evidence is preserved", evidence.superseded_by.startswith("live://"), evidence.superseded_by),
    ]

    for name, condition, detail in tests:
        total += 1
        passed += int(check(name, condition, detail))

    active = MemoryEvidence(status="UNKNOWN", confidence="low").normalized()
    total += 1
    passed += int(check("Invalid status normalizes to active", active.status == "active", active.status))

    serialized = active.to_frontmatter()
    total += 1
    passed += int(check("Serialized metadata contains status", "status: active" in serialized))
    total += 1
    passed += int(check("Serialized metadata contains confidence", "confidence: LOW" in serialized))

    print(f"\n=== RESULT: {passed} passed / {total - passed} failed ===")
    return 0 if passed == total else 1


if __name__ == "__main__":
    raise SystemExit(main())
