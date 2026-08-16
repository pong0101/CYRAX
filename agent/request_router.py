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

        # A size question is a live fact, but it does not need the model
        # inventory tool. The caller can answer from the runtime model-size
        # context without treating it as an installed/uninstalled query.
        if (
            any(x in t for x in ("ขนาด", "size", "ใหญ่แค่ไหน", "กี่ gb", "กี่ gib"))
            and any(x in t for x in ("โมเดล", "model", "qwen", "ollama"))
        ):
            return Route("live", None, "live model size question")

        # Current installed-model state is a live runtime fact. This must
        # outrank the generic ACTION keyword "ติดตั้ง".
        if (
            any(x in t for x in ("ตอนนี้", "ปัจจุบัน", "ล่าสุด", "มีอยู่ไหม", "ติดตั้งอยู่ไหม", "ติดตั้งไหม"))
            and any(x in t for x in ("โมเดล", "model", "qwen", "ollama"))
        ):
            return Route("live", "ollama_models", "live installed-model state")

        # Explicit installed-model queries must hit Ollama, not memory.
        if "ollama" in t and any(x in t for x in ("โมเดล", "model", "ติดตั้ง", "installed", "มีอะไร")):
            return Route("live", "ollama_models", "live Ollama inventory")

        # Read-only file access is a live query routed to the narrow native
        # read tool rather than the write/action path.
        if ("ไฟล์" in t or "file" in t) and any(
            x in t for x in ("อ่าน", "read", "ดู", "ตรวจสอบ", "content", "เนื้อหา")
        ):
            return Route("live", "read_file", "live file content")

        if any(x in t for x in self.ACTION):
            if "ไฟล์" in t or "file" in t:
                return Route("action", "write_file", "file mutation")
            return Route("action", "execute_powershell", "machine action; native narrow tool preferred")

        if any(x in t for x in self.MEMORY):
            return Route("memory", "memory_search", "historical/persistent context request")

        if any(x in t for x in self.LIVE):
            return Route("live", None, "current machine/project state")

        return Route("general", None, "no strong live/memory/action signal")
