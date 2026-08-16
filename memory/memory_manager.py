"""Obsidian-backed persistent memory for CYRAX with optional semantic retrieval."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
import json
import math
import os
import re

import ollama


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
        self.index_path = self.vault / ".cyrax" / "memory_index.json"
        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        self.embedding_model = os.getenv("CYRAX_EMBED_MODEL", "qwen3-embedding:0.6b")

    @staticmethod
    def _terms(query: str) -> list[str]:
        return [term.lower() for term in re.findall(r"\S+", query) if term.strip()]

    def _markdown_files(self) -> list[Path]:
        return [path for path in self.vault.rglob("*.md") if ".cyrax" not in path.parts]

    def search(self, query: str, limit: int = 5) -> list[dict]:
        """Search Markdown notes using local full-text term scoring."""
        terms = self._terms(query)
        if not terms:
            return []

        results: list[dict] = []
        for path in self._markdown_files():
            try:
                text = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            haystack = text.lower()
            score = sum(haystack.count(term) for term in terms)
            if score:
                results.append({"path": str(path.relative_to(self.vault)), "score": score, "content": text})
        return sorted(results, key=lambda item: item["score"], reverse=True)[:limit]

    @staticmethod
    def _cosine(a: list[float], b: list[float]) -> float:
        if not a or not b or len(a) != len(b):
            return 0.0
        dot = sum(x * y for x, y in zip(a, b))
        na = math.sqrt(sum(x * x for x in a))
        nb = math.sqrt(sum(y * y for y in b))
        return dot / (na * nb) if na and nb else 0.0

    def _load_index(self) -> dict:
        if not self.index_path.exists():
            return {"model": self.embedding_model, "documents": {}}
        try:
            return json.loads(self.index_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {"model": self.embedding_model, "documents": {}}

    def _save_index(self, index: dict) -> None:
        self.index_path.write_text(json.dumps(index, ensure_ascii=False), encoding="utf-8")

    def semantic_search(self, query: str, limit: int = 5) -> tuple[list[dict], str]:
        """Retrieve memories semantically through Ollama embeddings.

        Returns (results, status). If the embedding model is unavailable, falls back
        to lexical search so CYRAX never loses access to its memory.
        """
        try:
            query_response = ollama.embed(model=self.embedding_model, input=query)
            query_embedding = query_response["embeddings"][0]
        except Exception as exc:
            return self.search(query, limit), f"semantic unavailable: {exc}"

        index = self._load_index()
        if index.get("model") != self.embedding_model:
            index = {"model": self.embedding_model, "documents": {}}

        changed = False
        documents = index.setdefault("documents", {})
        for path in self._markdown_files():
            rel = str(path.relative_to(self.vault))
            try:
                stat = path.stat()
                text = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            stamp = stat.st_mtime_ns
            cached = documents.get(rel)
            if not cached or cached.get("mtime_ns") != stamp:
                try:
                    response = ollama.embed(model=self.embedding_model, input=text[:12000])
                    documents[rel] = {"mtime_ns": stamp, "embedding": response["embeddings"][0], "content": text}
                    changed = True
                except Exception as exc:
                    return self.search(query, limit), f"semantic indexing failed: {exc}"

        known = {str(path.relative_to(self.vault)) for path in self._markdown_files()}
        for rel in list(documents):
            if rel not in known:
                del documents[rel]
                changed = True
        if changed:
            self._save_index(index)

        results = []
        for rel, item in documents.items():
            score = self._cosine(query_embedding, item.get("embedding", []))
            if score > 0:
                results.append({"path": rel, "score": round(score, 4), "content": item.get("content", "")})
        return sorted(results, key=lambda item: item["score"], reverse=True)[:limit], "semantic"

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
