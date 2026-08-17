"""Verify runtime model evidence can supersede stale main-model memory."""
from __future__ import annotations

import sys
import types

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "agent"))

# The reconciliation contract only needs interpreter.llm.model. Keep this
# verification deterministic and independent from the full Open Interpreter
# dependency graph and semantic indexing used by the Windows runtime.
fake_interpreter = types.ModuleType("interpreter")
fake_interpreter.interpreter = types.SimpleNamespace(
    llm=types.SimpleNamespace(model="ollama_chat/qwen3:14b"),
)
sys.modules["interpreter"] = fake_interpreter

from memory import MemoryManager  # noqa: E402
from memory.reconciler import reconcile_main_model  # noqa: E402

passed = failed = 0


def check(label: str, ok: bool, detail: str = "") -> None:
    global passed, failed
    print(f"[{'PASS' if ok else 'FAIL'}] {label}" + (f" — {detail}" if detail else ""))
    if ok:
        passed += 1
    else:
        failed += 1


class StubMemory:
    """Deterministic memory surface for testing reconciliation itself."""

    def __init__(self, content: str):
        self.item = {
            "path": "01_Memory/main-model.md",
            "content": content,
            "evidence": {"status": "active"},
        }
        self.marked: list[tuple[str, str, str | None]] = []

    def search(self, _query: str, limit: int = 10):
        return [self.item]

    def mark_status(self, path: str, status: str, superseded_by: str | None = None):
        self.marked.append((path, status, superseded_by))
        self.item["evidence"]["status"] = status


# Runtime model discovery is tested through the actual runtime-aware manager.
runtime_manager = MemoryManager("unused")
check(
    "Runtime model is discovered from interpreter",
    runtime_manager._runtime_model() == "qwen3:14b",
)

# Conflicting English claim must be reconciled without semantic/Ollama indexing.
english = StubMemory("CYRAX main model is qwen3:8b.")
reconciled = reconcile_main_model(english, "qwen3:14b")
check("Conflicting main-model memory is reconciled", len(reconciled) == 1)
check("Conflicting memory becomes stale", english.item["evidence"]["status"] == "stale")
check(
    "Stale memory records runtime replacement",
    english.marked == [
        (
            "01_Memory/main-model.md",
            "stale",
            "runtime:main_model=qwen3:14b",
        )
    ],
)

# Thai explicit claim must follow the same policy.
thai = StubMemory("โมเดลหลักของ CYRAX คือ qwen3:8b")
thai_reconciled = reconcile_main_model(thai, "qwen3:14b")
check("Thai main-model claim is detected", len(thai_reconciled) == 1)
check("Thai conflicting memory becomes stale", thai.item["evidence"]["status"] == "stale")

# Equal-value evidence is a no-op and must never mark memory stale.
matching = StubMemory("CYRAX main model is qwen3:14b.")
matching_reconciled = reconcile_main_model(matching, "qwen3:14b")
check("Matching runtime evidence produces no new conflict", len(matching_reconciled) == 0)
check("Matching runtime evidence is not marked stale", matching.marked == [])

# Casual model mentions are intentionally ignored by the claim extractor.
casual = StubMemory("We previously tested qwen3:8b and qwen3:14b during development.")
casual_reconciled = reconcile_main_model(casual, "qwen3:14b")
check("Casual model mentions are ignored", len(casual_reconciled) == 0)
check("Casual model memory remains active", casual.item["evidence"]["status"] == "active")

print(f"\n=== RESULT: {passed} passed / {failed} failed ===")
raise SystemExit(1 if failed else 0)
