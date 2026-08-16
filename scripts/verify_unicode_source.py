"""Verify CYRAX source files contain real UTF-8 Thai markers, not mojibake."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

CASES = {
    "agent/cyrax.py": (
        "ตอนนี้",
        "ปัจจุบัน",
        "ล่าสุด",
        "CYRAX ใช้โมเดลหลัก",
        "บิต",
    ),
    "agent/memory/memory_policy.py": (
        "อะไร",
        "ไหม",
        "จำไว้",
        "อ่านไฟล์",
        "โปรเจกต์",
    ),
    "agent/request_router.py": (
        "ตอนนี้",
        "ก่อนหน้านี้",
        "จำไว้ว่",
        "สร้าง",
        "อ่านไฟล์",
    ),
}

BAD_MARKER = "à¸"
passed = failed = 0

for relative, markers in CASES.items():
    path = ROOT / relative
    try:
        text = path.read_text(encoding="utf-8")
    except Exception as exc:
        print(f"[FAIL] {relative} — cannot decode as UTF-8: {exc}")
        failed += 1
        continue

    missing = [marker for marker in markers if marker not in text]
    has_mojibake = BAD_MARKER in text
    ok = not missing and not has_mojibake
    if ok:
        print(f"[PASS] {relative} — UTF-8 Thai markers are intact")
        passed += 1
    else:
        details = []
        if missing:
            details.append(f"missing: {missing}")
        if has_mojibake:
            details.append("contains mojibake marker 'à¸'")
        print(f"[FAIL] {relative} — {'; '.join(details)}")
        failed += 1

print(f"\n=== RESULT: {passed} passed / {failed} failed ===")
raise SystemExit(1 if failed else 0)
