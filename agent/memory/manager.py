"""Persistent Markdown memory with Ollama semantic embeddings and JSON index."""
from __future__ import annotations

import hashlib
import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any

import ollama

from memory.evidence import MemoryEvidence


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

    @staticmethod
    def _parse_frontmatter(content: str) -> MemoryEvidence:
        """Parse simple Markdown frontmatter without adding a YAML dependency."""
        if not content.startswith("---"):
            return MemoryEvidence()
        lines = content.splitlines()
        values: dict[str, str] = {}
        for line in lines[1:]:
            if line.strip() == "---":
                break
            key, separator, value = line.partition(":")
            if separator:
                values[key.strip().lower()] = value.strip()
        return MemoryEvidence(
            source=values.get("source", "CYRAX"),
            created=values.get("created", ""),
            updated=values.get("updated", ""),
            last_verified=values.get("last_verified", ""),
            memory_type=values.get("type", "memory"),
            confidence=values.get("confidence", "HIGH"),
            status=values.get("status", "active"),
            superseded_by=values.get("superseded_by", ""),
        ).normalized()

    @classmethod
    def _result(cls, path: str, score: float | int, content: str) -> dict[str, Any]:
        evidence = cls._parse_frontmatter(content)
        return {
            "path": path,
            "score": score,
            "content": content,
            "evidence": evidence.__dict__,
        }

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

    @staticmethod
    def _is_long_term_memory(rel: str) -> bool:
        """Logs are historical evidence, not long-term memory by default."""
        parts = Path(rel).parts
        return "04_Logs" not in parts and not rel.startswith("04_Logs/")

    def _readable_items(self, include_logs: bool = False) -> list[tuple[str, str]]:
        items: list[tuple[str, str]] = []
        for path in self.vault.rglob("*.md"):
            if ".cyrax" in path.parts:
                continue
            rel = self._relative(path)
            if not include_logs and not self._is_long_term_memory(rel):
                continue
            try:
                items.append((rel, path.read_text(encoding="utf-8")))
            except (OSError, UnicodeDecodeError):
                continue
        return items

    def _ensure_index(self) -> None:
        changed = False
        known = self._index["items"]
        current_paths = set()
        # Index durable memory only. Interaction logs remain historical evidence
        # and are deliberately excluded from semantic recall by default.
        for rel, content in self._readable_items(include_logs=False):
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

    def semantic_search(self, query: str, limit: int = 5, include_logs: bool = False) -> tuple[list[dict[str, Any]], str]:
        self._ensure_index()
        try:
            qv = self._embed(query)
            scored: list[dict[str, Any]] = []
            for rel, item in self._index["items"].items():
                if not include_logs and not self._is_long_term_memory(rel):
                    continue
                path = self.vault / rel
                if not path.exists():
                    continue
                content = path.read_text(encoding="utf-8")
                score = self._cosine(qv, item.get("embedding", []))
                scored.append(self._result(rel, round(score, 4), content))
            scored.sort(key=lambda x: x["score"], reverse=True)
            return scored[:limit], "semantic"
        except Exception:
            return self.search(query, limit=limit, include_logs=include_logs), "keyword-fallback"

    def search(self, query: str, limit: int = 5, include_logs: bool = False) -> list[dict[str, Any]]:
        terms = [t.lower() for t in re.findall(r"[\w\u0E00-\u0E7F]+", query) if len(t) > 1]
        scored: list[dict[str, Any]] = []
        for rel, content in self._readable_items(include_logs=include_logs):
            lower = content.lower()
            score = sum(lower.count(term) for term in terms)
            if score:
                scored.append(self._result(rel, score, content))
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
        evidence = MemoryEvidence(
            created=created,
            updated=now,
            last_verified=now,
            memory_type=memory_type,
            confidence=confidence,
            status="active",
        )
        path.write_text(evidence.to_frontmatter() + f"# {title}\n\n{content.strip()}\n", encoding="utf-8")
        self._ensure_index()
        return path

    def mark_status(self, path: str, status: str, superseded_by: str = "") -> Path:
        """Mark durable memory stale/contradicted without changing its body."""
        if status not in {"active", "stale", "contradicted"}:
            raise ValueError(f"invalid memory status: {status}")
        target = Path(path)
        if not target.is_absolute():
            target = self.vault / target
        target = target.resolve()
        target.relative_to(self.vault)
        content = target.read_text(encoding="utf-8")
        if not content.startswith("---"):
            raise ValueError("memory file has no frontmatter")
        lines = content.splitlines()
        end = next((i for i, line in enumerate(lines[1:], start=1) if line.strip() == "---"), None)
        if end is None:
            raise ValueError("memory frontmatter is not closed")
        now = self._now()
        replacements = {
            "updated": now,
            "status": status,
            "superseded_by": superseded_by,
        }
        seen: set[str] = set()
        for index in range(1, end):
            key = lines[index].split(":", 1)[0].strip().lower()
            if key in replacements:
                lines[index] = f"{key}: {replacements[key]}"
                seen.add(key)
        for key, value in replacements.items():
            if key not in seen:
                lines.insert(end, f"{key}: {value}")
                end += 1
        target.write_text("\n".join(lines) + "\n", encoding="utf-8")
        self._ensure_index()
        return target

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
