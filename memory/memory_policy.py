"""Memory classification policy for CYRAX second brain."""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class MemoryDecision:
    should_save: bool
    category: str = "temporary"
    reason: str = ""
    title: str = ""


class MemoryPolicy:
    """Conservative local memory classifier.

    The policy intentionally prefers forgetting over storing noise. Explicit
    requests such as 'remember this' always win; otherwise only high-confidence
    project facts/preferences are persisted.
    """

    EXPLICIT = re.compile(
        r"\b(?:remember|memorize|save this|don't forget|do not forget|จำไว้|จำเรื่องนี้|บันทึกไว้|อย่าลืม)\b",
        re.IGNORECASE,
    )
    PROJECT = re.compile(
        r"\b(?:project|repo|repository|vault|workspace|model|stack|version|uses|use|ตั้งชื่อ|โปรเจกต์|โมเดล|vault)\b",
        re.IGNORECASE,
    )
    PREFERENCE = re.compile(
        r"\b(?:i want|i prefer|my preference|always|never|ต้องการ|ชอบ|ไม่ต้องการ|อยากให้|ตั้งค่า)\b",
        re.IGNORECASE,
    )

    @classmethod
    def classify(cls, text: str) -> MemoryDecision:
        clean = " ".join(text.strip().split())
        if not clean:
            return MemoryDecision(False, reason="empty")

        if cls.EXPLICIT.search(clean):
            return MemoryDecision(
                True,
                category="explicit",
                reason="explicit memory request",
                title=cls._title(clean),
            )

        if cls.PROJECT.search(clean) or cls.PREFERENCE.search(clean):
            # Require a reasonably factual statement instead of a short question.
            if len(clean) >= 25 and not clean.endswith("?") and not clean.endswith("？"):
                category = "project" if cls.PROJECT.search(clean) else "preference"
                return MemoryDecision(
                    True,
                    category=category,
                    reason="high-confidence project/preference fact",
                    title=cls._title(clean),
                )

        return MemoryDecision(False, reason="temporary conversation")

    @staticmethod
    def _title(text: str) -> str:
        # Stable, readable titles without exposing raw path characters.
        title = re.sub(r"[<>:\"/\\|?*]", "", text)
        title = re.sub(r"\s+", " ", title).strip()
        return title[:90] or "CYRAX Memory"
