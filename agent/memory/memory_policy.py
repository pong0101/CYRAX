"""Conservative policy for deciding what CYRAX should retain long-term."""
from __future__ import annotations

from dataclasses import dataclass
import re


@dataclass
class MemoryDecision:
    should_save: bool
    category: str = "context"
    title: str = "Memory"
    reason: str = ""
    confidence: str = "HIGH"


class MemoryPolicy:
    def classify(self, text: str) -> MemoryDecision:
        value = text.strip()
        lower = value.lower()
        if len(value) < 8:
            return MemoryDecision(False, reason="too short")

        explicit = any(marker in lower for marker in (
            "จำไว้", "จำว่า", "remember this", "remember that", "เก็บไว้", "บันทึกไว้",
        ))
        preference = any(marker in lower for marker in (
            "ฉันชอบ", "ผมชอบ", "ต้องการให้", "อยากให้", "ไม่ต้อง", "prefer", "i want",
        ))
        project = any(marker in lower for marker in (
            "โปรเจกต์", "project", "cyrAX", "cyrax", "โมเดลหลัก", "architecture",
        ))
        decision = any(marker in lower for marker in (
            "ตัดสินใจ", "สรุปว่า", "เลือกใช้", "decision", "we will use",
        ))
        task = any(marker in lower for marker in (
            "ต้องทำ", "todo", "task", "งานต่อไป", "next step",
        ))

        if not any((explicit, preference, project, decision, task)):
            return MemoryDecision(False, reason="no durable-memory signal")

        if decision:
            category = "decision"
        elif preference:
            category = "preference"
        elif project:
            category = "project"
        elif task:
            category = "task"
        else:
            category = "fact"

        clean = re.sub(r"[^\w\u0E00-\u0E7F ]+", " ", value, flags=re.UNICODE).strip()
        title = " ".join(clean.split())[:70] or "Memory"
        return MemoryDecision(True, category=category, title=title, reason="durable fact/preference/project/decision signal", confidence="HIGH")
