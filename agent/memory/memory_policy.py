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

        # Questions and requests for information are not durable memories by
        # themselves. This prevents CYRAX from filling the vault with files
        # such as "โปรเจกต์หลักของเราชื่ออะไร".
        question_markers = (
            "?", "？", "อะไร", "ไหน", "เท่าไหร่", "เท่าไร", "กี่", "ไหม", "หรือไม่",
            "อย่างไร", "ยังไง", "ทำไม", "เมื่อไหร่", "เมื่อไร", "how ", "what ",
            "where ", "when ", "why ", "which ", "who ",
        )
        if any(marker in lower for marker in question_markers):
            return MemoryDecision(False, reason="informational question")

        # Runtime inspection and read-only actions are ephemeral observations,
        # not durable memories. In particular, never save a read_file request
        # merely because its path contains the word "CYRAX" or "project".
        runtime_action_markers = (
            "อ่านไฟล์", "อ่าน ", "read file", "read ", "ดูไฟล์", "ดูเนื้อหา",
            "ตรวจสอบไฟล์", "ตรวจสอบ ", "file content", "list directory", "directory",
            "ตอนนี้", "ปัจจุบัน", "ล่าสุด", "สถานะ", "มีอะไรติดตั้ง", "ติดตั้งอยู่",
            "ollama", "gpu", "ram", "cpu", "process", "running", "version", "เวอร์ชัน",
        )
        if any(marker in lower for marker in runtime_action_markers):
            return MemoryDecision(False, reason="ephemeral runtime/read-only action")

        explicit = any(marker in lower for marker in (
            "จำไว้", "จำว่า", "remember this", "remember that", "เก็บไว้", "บันทึกไว้",
        ))
        preference = any(marker in lower for marker in (
            "ฉันชอบ", "ผมชอบ", "ต้องการให้", "อยากให้", "ไม่ต้อง", "prefer", "i want",
        ))
        project = any(marker in lower for marker in (
            "โปรเจกต์", "project", "cyrax", "โมเดลหลัก", "architecture",
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
