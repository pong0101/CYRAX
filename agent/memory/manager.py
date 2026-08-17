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

from .evidence import MemoryEvidence


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