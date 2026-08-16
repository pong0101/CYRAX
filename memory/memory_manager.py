"""Simple Obsidian-backed long-term memory for CYRAX."""

from pathlib import Path
from datetime import datetime


class MemoryManager:
    """Read and write Markdown notes in an Obsidian vault."""

    def __init__(self, vault_path: str):
        self.vault = Path(vault_path).expanduser().resolve()
        self.vault.mkdir(parents=True, exist_ok=True)

    def search(self, query: str, limit: int = 10) -> list[dict]:
        """Return Markdown notes containing the query terms."""
        terms = [term.lower() for term in query.split() if term.strip()]
        results = []

        for path in self.vault.rglob("*.md"):
            try:
                text = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue

            haystack = text.lower()
            score = sum(haystack.count(term) for term in terms)
            if score:
                results.append({
                    "path": str(path.relative_to(self.vault)),
                    "score": score,
                    "content": text,
                })

        return sorted(results, key=lambda item: item["score"], reverse=True)[:limit]

    def remember(self, title: str, content: str, folder: str = "Inbox") -> Path:
        """Create a new Markdown memory note."""
        safe_title = "".join(c for c in title if c not in '<>:"/\\|?*').strip()
        if not safe_title:
            raise ValueError("Memory title cannot be empty")

        target_dir = self.vault / folder
        target_dir.mkdir(parents=True, exist_ok=True)
        path = target_dir / f"{safe_title}.md"

        timestamp = datetime.now().astimezone().isoformat(timespec="seconds")
        note = f"---\ncreated: {timestamp}\ntype: memory-candidate\n---\n\n# {safe_title}\n\n{content.strip()}\n"
        path.write_text(note, encoding="utf-8")
        return path

    def read(self, relative_path: str) -> str:
        """Read a note safely from inside the configured vault."""
        path = (self.vault / relative_path).resolve()
        if self.vault not in path.parents and path != self.vault:
            raise ValueError("Path escapes the configured Obsidian vault")
        return path.read_text(encoding="utf-8")
