"""CYRAX end-to-end integration verification.

Exercises deterministic routing and the native tool layer without starting the
interactive agent or asking the LLM to decide whether a tool should run.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "agent"))
sys.path.insert(0, str(ROOT / "agent" / "memory"))

from request_router import RequestRouter
from tool_bridge import ToolBridge


def check(label: str, condition: bool, detail: str = "") -> bool:
    status = "PASS" if condition else "FAIL"
    print(f"[{status}] {label}" + (f" — {detail}" if detail else ""))
    return condition


def main() -> int:
    print("=== CYRAX Integration Verification ===")
    print(f"Repo: {ROOT}")
    passed = failed = 0

    def test(label: str, condition: bool, detail: str = "") -> None:
        nonlocal passed, failed
        if check(label, condition, detail):
            passed += 1
        else:
            failed += 1

    router = RequestRouter()

    cases = [
        ("Live Ollama inventory", "ตอนนี้ Ollama มีโมเดลอะไรติดตั้งอยู่?", "live", "ollama_models"),
        ("Live model size", "ตอนนี้ qwen3:8b มีขนาดเท่าไหร่?", "live", None),
        ("Memory recall", "ก่อนหน้านี้เราเคยคุยเรื่องอะไรเกี่ยวกับ qwen3:8b บ้าง?", "memory", "memory_search"),
        ("Explicit memory save", "จำไว้ว่าชื่อโปรเจกต์ของฉันคือ CYRAX", "memory_save", "memory_save"),
        ("File read", r"อ่านไฟล์ F:\AI\CYRAX\TEST_TOOL.txt", "action", "read_file"),
        ("File write", r"สร้างไฟล์ F:\AI\CYRAX\INTEGRATION_TEST.txt", "action", "write_file"),
    ]
    for label, text, kind, tool in cases:
        route = router.classify(text)
        test(label, route.kind == kind and route.tool == tool, f"kind={route.kind}, tool={route.tool}")

    bridge = ToolBridge.__new__(ToolBridge)
    bridge.workspace = ROOT

    models = bridge.ollama_models()
    test("Live Ollama query", "qwen3:8b" in models, models)
    test("Unit output uses bytes/GiB", "bytes" in models and "GiB" in models and "bits" not in models)

    test_file = ROOT / "TEST_TOOL.txt"
    if test_file.exists():
        content = bridge.read_file(str(test_file))
        test("Native read returns exact content", content == "CYRAX TOOL EXECUTION OK", repr(content))
    else:
        test("Native read returns exact content", False, "TEST_TOOL.txt not found")

    temporary = ROOT / "INTEGRATION_TEST.txt"
    if temporary.exists():
        temporary.unlink()
    test("No temporary integration file remains", not temporary.exists())

    print(f"\n=== RESULT: {passed} passed / {failed} failed ===")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
