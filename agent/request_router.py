"""Deterministic request classification for CYRAX.

The router is deliberately conservative: it chooses the source/tool class,
not the final answer. Live/current machine facts outrank memory, explicit
memory requests save to memory, and actions prefer narrow native tools.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Route:
    kind: str
    tool: str | None = None
    reason: str = ""


class RequestRouter:
    LIVE = (
        "ตอนนี้", "ปัจจุบัน", "ล่าสุด", "สถานะ", "มีอะไรติดตั้ง", "ติดตั้งอยู่",
        "ollama", "gpu", "ram", "cpu", "process", "running", "version", "เวอร์ชัน",
        "ไฟล์นี้มี", "ไฟล์อะไร", "โฟลเดอร์", "directory", "installed", "current",
    )
    MEMORY = (
        "ก่อนหน้านี้", "เมื่อก่อน", "เคยคุย", "จำได้ไหม", "จำได้มั้ย", "ความทรงจำ",
        "memory", "ประวัติ", "ที่เคยบอก", "ที่เคยคุย",
    )
    ACTION = (
        "สร้าง", "เขียน", "แก้ไข", "ลบ", "ย้าย", "เปลี่ยนชื่อ", "รัน", "execute",
        "run ", "ติดตั้ง", "ถอนการติดตั้ง", "เปิด", "ปิด", "ตรวจสอบไฟล์", "เขียนไฟล์",
        "อ่านไฟล์", "อ่าน", "read file", "read", "ดูไฟล์", "ดูเนื้อหา", "เนื้อหาไฟล์",
    )
    EXPLICIT_MEMORY = (
        "จำไว้ว่", "จำไว้ว่า", "จดจำ", "บันทึกความจำ", "remember that", "remember this",
    )

    def classify(self, text: str) -> Route:
        t = text.strip().lower()
        if any(x in t for x in self.EXPLICIT_MEMORY):
            return Route("memory_save", "memory_save", "explicit memory request")

        # Explicit installed-model queries must hit Ollama, not memory.
        if "ollama" in t and any(x in t for x in ("โมเดล", "model", "ติดตั้ง", "installed", "มีอะไร")):
            return Route("live", "ollama_models", "live Ollama inventory")

        # Read-only file access is an action routed to the narrow native read tool.
        if ("ไฟล์" in t or "file" in t) and any(
            x in t for x in ("อ่าน", "read", "ดู", "ตรวจสอบ", "content", "เนื้อหา")
        ):
            return Route("action", "read_file", "read-only file access")

        if any(x in t for x in self.ACTION):
            if "ไฟล์" in t or "file" in t:
                return Route("action", "write_file", "file mutation")
            return Route("action", "execute_powershell", "machine action; native narrow tool preferred")

        if any(x in t for x in self.MEMORY):
            return Route("memory", "memory_search", "historical/persistent context request")

        if any(x in t for x in self.LIVE):
            return Route("live", None, "current machine/project state")

        return Route("general", None, "no strong live/memory/action signal")
