"""Verify runtime model evidence can supersede stale main-model memory."""
from __future__ import annotations

import sys
import tempfile
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "agent"))

# The reconciliation contract only needs interpreter.llm.model. Keep this
# verification deterministic and independent from the full Open Interpreter
# dependency graph used by the Windows runtime.
fake_interpreter = types.ModuleType("interpreter")
fake_interpreter.interpreter = types.SimpleNamespace(
    llm=types.SimpleNamespace(model=""),
)
sys.modules["interpreter"] = fake_interpreter

from memory import MemoryManager  # noqa: E402

passed = failed = 0


def check(label: str, ok: bool, detail: str = "") -> None:
    global passed, failed
    print(f"[{'PASS' if ok else 'FAIL'}] {label}" + (f" — {detail}" if detail else ""))
    if ok:
        passed += 1
    else:
        failed += 1


with tempfile.TemporaryDirectory() as temp:
    manager = MemoryManager(temp)
    old_path = manager.remember(
        "main-model",
        "CYRAX main model is qwen3:8b.",
        memory_type="project",
    )

    fake_interpreter.interpreter.llm.model = "ollama_chat/qwen3:14b"
    reconciled = manager.reconcile_runtime_model()
    evidence = manager._parse_frontmatter(old_path.read_text(encoding="utf-8"))

    check("Runtime model is discovered from interpreter", manager._runtime_model() == "qwen3:14b")
    check("Conflicting main-model memory is reconciled", len(reconciled) == 1)
    check("Conflicting memory becomes stale", evidence.status == "stale")
    check(
        "Stale memory records runtime replacement",
        evidence.superseded_by == "runtime:main_model=qwen3:14b",
    )

    thai_path = manager.remember(
        "thai-main-model",
        "โมเดลหลักของ CYRAX คือ qwen3:8b",
        memory_type="project",
    )
    thai_reconciled = manager.reconcile_runtime_model()
    thai_evidence = manager._parse_frontmatter(thai_path.read_text(encoding="utf-8"))
    check("Thai main-model claim is detected", len(thai_reconciled) == 1)
    check("Thai conflicting memory becomes stale", thai_evidence.status == "stale")

    # Use a fresh manager for the matching-value contract so the assertion
    # cannot be affected by unrelated stale/conflicting memories from the
    # preceding English/Thai reconciliation cases.
    matching_manager = MemoryManager(tempfile.mkdtemp(prefix="cyrax-matching-"))
    try:
        same_path = matching_manager.remember(
            "main-model",
            "CYRAX main model is qwen3:14b.",
            memory_type="project",
        )
        reconciled_again = matching_manager.reconcile_runtime_model()
        same_evidence = matching_manager._parse_frontmatter(same_path.read_text(encoding="utf-8"))
        check("Matching runtime evidence is not marked stale", same_evidence.status == "active")
        check("Matching runtime evidence produces no new conflict", len(reconciled_again) == 0)
    finally:
        import shutil

        shutil.rmtree(matching_manager.vault, ignore_errors=True)

    casual_path = manager.remember(
        "model-note",
        "We previously tested qwen3:8b and qwen3:14b during development.",
        memory_type="project",
    )
    manager.reconcile_runtime_model()
    casual_evidence = manager._parse_frontmatter(casual_path.read_text(encoding="utf-8"))
    check("Casual model mentions are ignored", casual_evidence.status == "active")

print(f"\n=== RESULT: {passed} passed / {failed} failed ===")
raise SystemExit(1 if failed else 0)
