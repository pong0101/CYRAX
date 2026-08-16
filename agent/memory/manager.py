"""Persistent Markdown memory with Ollama semantic embeddings and JSON index."""
from __future__ import annotations

import hashlib
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import ollama


class MemoryManager:
    def __init__(self, vault_path: str, embedding_model: str | None = None):
        self.vault = Path(vault_path).expanduser().resolve()
        self.embedding_model = embedding_model or os.getenv("CYRAX_EMBEDDING_MODEL", "qwen3-embedding:0.6b")
        self.meta_dir = self.vault / ".cyrax"
        self.index_path = self.meta_dir / "memory_index.json"
        self.vault.mkdir(parents=True, exist_ok=True)
        self.meta_dir.mkdir(parents=True, exist_ok=True)
        self._index: dict[str, Any] = self._load_index()

    @staticmethod
    def _now() -> str:
        return datetime.now().astimezone().isoformat(timespec="seconds")

    def _load_index(self) -> dict[str, Any]:
        if not self.index_path.exists():
            return {"version": 2, "embedding_model": self.embedding_model, "items": {}}
        try:
            data = json.loads(self.index_path.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                raise ValueError("invalid index")
            data.setdefault("version", 2)
            data.setdefault("embedding_model", self.embedding_model)
            data.setdefault("items", {})
            return data
        except (OSError, json.JSONDecodeError, ValueError):
            return {"version": 2, "embedding_model": self.embedding_model, "items": {}}

    def _save_index(self) -> None:
        self.index_path.write_text(json.dumps(self._index, ensure_ascii=False, indent=2), encoding="utf-8")

    @staticmethod
    def _slug(text: str) -> str:
        text = re.sub(r"[^\w\-\u0E00-\u0E7F ]+", "", text, flags=re.UNICODE).strip()
        text = re.sub(r"\s+", " ", text)
        return text[:80] or "memory"

    @staticmethod
    def _hash(content: str) -> str:
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def _embed(self, text: str) -> list[float]:
        response = ollama.embed(model=self.embedding_model, input=text)
        if isinstance(response, dict):
            embeddings = response.get("embeddings") or []
            if embeddings:
                return [float(x) for x in embeddings[0]]
            embedding = response.get("embedding") or []
            return [float(x) for x in embedding]
        embeddings = getattr(response, "embeddings", None) or []
        if embeddings:
            return [float(x) for x in embeddings[0]]
        return [float(x) for x in (getattr(response, "embedding", None) or [])]

    @staticmethod
    def _cosine(a: list[float], b: list[float]) -> float:
        if not a or not b or len(a) != len(b):
            return 0.0
        dot = sum(x * y for x, y in zip(a, b))
        na = sum(x * x for x in a) ** 0.5
        nb = sum(y * y for y in b) ** 0.5
        return dot / (na * nb) if na and nb else 0.0

    def _relative(self, path: Path) -> str:
        return path.relative_to(self.vault).as_posix()

    def _readable_items(self) -> list[tuple[str, str]]:
        items: list[tuple[str, str]] = []
        for path in self.vault.rglob("*.md"):
            if ".cyrax" in path.parts:
                continue
            try:
                items.append((self._relative(path), path.read_text(encoding="utf-8")))
            except (OSError, UnicodeDecodeError):
                continue
        return items

    def _ensure_index(self) -> None:
        changed = False
        known = self._index["items"]
        current_paths = set()
        for rel, content in self._readable_items():
            current_paths.add(rel)
            digest = self._hash(content)
            item = known.get(rel)
            if item and item.get("hash") == digest and item.get("embedding_model") == self.embedding_model:
                continue
            try:
                vector = self._embed(content[:12000])
                known[rel] = {
                    "hash": digest,
                    "embedding_model": self.embedding_model,
                    "updated": self._now(),
                    "embedding": vector,
                }
                changed = True
            except Exception:
                # Semantic search can still fall back to keyword search.
                continue
        for rel in list(known):
            if rel not in current_paths:
                del known[rel]
                changed = True
        if changed:
            self._save_index()

    def semantic_search(self, query: str, limit: int = 5) -> tuple[list[dict[str, Any]], str]:
        self._ensure_index()
        try:
            qv = self._embed(query)
            scored: list[dict[str, Any]] = []
            for rel, item in self._index["items"].items():
                path = self.vault / rel
                if not path.exists():
                    continue
                content = path.read_text(encoding="utf-8")
                score = self._cosine(qv, item.get("embedding", []))
                scored.append({"path": rel, "score": round(score, 4), "content": content})
            scored.sort(key=lambda x: x["score"], reverse=True)
            return scored[:limit], "semantic"
        except Exception:
            return self.search(query, limit=limit), "keyword-fallback"

    def search(self, query: str, limit: int = 5) -> list[dict[str, Any]]:
        terms = [t.lower() for t in re.findall(r"[\w\u0E00-\u0E7F]+", query) if len(t) > 1]
        scored: list[dict[str, Any]] = []
        for rel, content in self._readable_items():
            lower = content.lower()
            score = sum(lower.count(term) for term in terms)
            if score:
                scored.append({"path": rel, "score": score, "content": content})
        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[:limit]

    def remember(self, title: str, content: str, folder: str = "01_Memory", memory_type: str = "memory", confidence: str = "HIGH") -> Path:
        target_dir = self.vault / folder
        target_dir.mkdir(parents=True, exist_ok=True)
        path = target_dir / f"{self._slug(title)}.md"
        now = self._now()
        existing = ""
        if path.exists():
            try:
                existing = path.read_text(encoding="utf-8")
            except OSError:
                pass
        created = now
        match = re.search(r"^created:\s*(.+)$", existing, flags=re.MULTILINE)
        if match:
            created = match.group(1).strip()
        frontmatter = (
            "---\n"
            f"created: {created}\n"
            f"updated: {now}\n"
            f"last_verified: {now}\n"
            f"type: {memory_type}\n"
            f"confidence: {confidence}\n"
            "source: CYRAX\n"
            "---\n\n"
        )
        path.write_text(frontmatter + f"# {title}\n\n{content.strip()}\n", encoding="utf-8")
        self._ensure_index()
        return path

    def log(self, text: str) -> Path:
        day = datetime.now().astimezone().strftime("%Y-%m-%d")
        folder = self.vault / "04_Logs"
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / f"{day}.md"
        if not path.exists():
            path.write_text(f"---\ndate: {day}\ntype: cyrax-log\n---\n\n# CYRAX Log — {day}\n", encoding="utf-8")
        with path.open("a", encoding="utf-8") as fh:
            fh.write(f"\n## {datetime.now().astimezone().strftime('%H:%M:%S')}\n\n{text}\n")
        return path
