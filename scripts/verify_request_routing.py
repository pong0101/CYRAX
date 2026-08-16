"""Verify CYRAX deterministic request classification."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AGENT = ROOT / "agent"
sys.path.insert(0, str(AGENT))

from request_router import RequestRouter  # noqa: E402

router = RequestRouter()
cases = [
    ("ตอนนี้ Ollama มีโมเดลอะไรติดตั้งอยู่?", "live", "ollama_models"),
    ("ตอนนี้ qwen3:8b มีขนาดเท่าไหร่?", "live", None),
    ("ก่อนหน้านี้เราเคยคุยเรื่องอะไรเกี่ยวกับ qwen3:8b บ้าง?", "memory", "memory_search"),
    ("จำไว้ว่าชื่อโปรเจกต์ของฉันคือ CYRAX", "memory_save", "memory_save"),
    ("สร้างไฟล์ F:\\AI\\CYRAX\\ROUTER_TEST.txt", "action", "write_file"),
    ("อ่านไฟล์ F:\\AI\\CYRAX\\TEST_TOOL.txt", "live", "read_file"),
]

failed = 0
for text, expected_kind, expected_tool in cases:
    route = router.classify(text)
    ok = route.kind == expected_kind and route.tool == expected_tool
    print(f"[{'PASS' if ok else 'FAIL'}] {text} -> kind={route.kind}, tool={route.tool}")
    failed += not ok

print(f"\n=== RESULT: {len(cases) - failed} passed / {failed} failed ===")
raise SystemExit(1 if failed else 0)
