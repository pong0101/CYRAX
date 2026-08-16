"""Obsidian-backed persistent memory for CYRAX."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
import re


class MemoryManager:
    """Manage CYRAX long-term memory as normal Markdown files in Obsidian."""

    DEFAULT_FOLDERS = (
        "00_CYRAX",
        "01_Memory",
        "02_Projects",
        "03_Knowledge",
        "04_Logs",
        "99_Inbox",
    )

    def __init__(self, vault_path: str):
        self.vault = Path(vault_path).expanduser().resolve()
        self.vault.mkdir(parents=True, exist_ok=True)
        for folder in self.DEFAULT_FOLDERS:
            (self.vault / folder).mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _terms(query: str) -> list[str]:
        return [term.lower() for term in re.findall(r"\S+", query) if term.strip()]

    def search(self, query: str, limit: int = 5) -> list[dict]:
        """Search Markdown notes using simple local full-text term scoring."""
        terms = self._terms(query)
        if not terms:
            return []

        results: list[dict] = []
        for path in self.vault.rglob("*.md"):
            try:
                text = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue

            haystack = text.lower()
            score = sum(haystack.count(term) for term in terms)
            if score:
                results.append(
                    {
                        "path": str(path.relative_to(self.vault)),
                        "score": score,
                        "content": text,
                    }
                )

        return sorted(results, key=lambda item: item["score"], reverse=True)[:limit]

    def remember(
        self,
        title: str,
        content: str,
        folder: str = "01_Memory",
        memory_type: str = "memory",
    ) -> Path:
        """Create a durable Markdown memory note that remains editable in Obsidian."""
        safe_title = re.sub(r'[<>:"/\\|?*]', "", title).strip()
        if not safe_title:
            raise ValueError("Memory title cannot be empty")

        target_dir = (self.vault / folder).resolve()
        if self.vault not in target_dir.parents and target_dir != self.vault:
            raise ValueError("Memory folder escapes the configured Obsidian vault")
        target_dir.mkdir(parents=True, exist_ok=True)

        path = target_dir / f"{safe_title}.md"
        timestamp = datetime.now().astimezone().isoformat(timespec="seconds")
        note = (
            "---\n"
            f"created: {timestamp}\n"
            f"type: {memory_type}\n"
            "source: CYRAX\n"
            "---\n\n"
            f"# {safe_title}\n\n"
            f"{content.strip()}\n"
        )
        path.write_text(note, encoding="utf-8")
        return path

    def log(self, content: str) -> Path:
        """Append a timestamped entry to today's CYRAX log."""
        now = datetime.now().astimezone()
        path = self.vault / "04_Logs" / f"{now:%Y-%m-%d}.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            path.write_text(
                f"---\ndate: {now:%Y-%m-%d}\ntype: cyrax-log\n---\n\n"
                f"# CYRAX Log — {now:%Y-%m-%d}\n",
                encoding="utf-8",
            )
        with path.open("a", encoding="utf-8") as handle:
            handle.write(f"\n## {now:%H:%M:%S}\n\n{content.strip()}\n")
        return path

    def read(self, relative_path: str) -> str:
        """Read a note safely from inside the configured vault."""
        path = (self.vault / relative_path).resolve()
        if self.vault not in path.parents:
            raise ValueError("Path escapes the configured Obsidian vault")
        return path.read_text(encoding="utf-8")
