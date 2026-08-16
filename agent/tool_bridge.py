"""Native Ollama tool bridge for CYRAX.

Open Interpreter remains part of the CYRAX runtime, but Ollama tool calls are
handled here explicitly so local Qwen models cannot accidentally return a raw
JSON execute request without executing it.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Any

from memory import MemoryManager


class ToolBridge:
    def __init__(self, memory: MemoryManager):
        self.memory = memory
        self.workspace = Path(os.getenv("CYRAX_WORKSPACE", "F:/AI/CYRAX")).resolve()

    @staticmethod
    def _approval(description: str) -> bool:
        print(f"\nCYRAX approval required: {description}")
        answer = input("Approve? [y/N]: ").strip().lower()
        return answer in {"y", "yes"}

    def execute_powershell(self, code: str) -> str:
        """Execute PowerShell after explicit user approval."""
        if not code.strip():
            return "Error: PowerShell code is empty."
        if not self._approval(f"Execute PowerShell:\n{code}"):
            return "Execution denied by user."

        try:
            result = subprocess.run(
                ["powershell.exe", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-Command", code],
                capture_output=True,
                text=True,
                timeout=120,
                cwd=str(self.workspace),
            )
        except subprocess.TimeoutExpired:
            return "Error: PowerShell execution timed out after 120 seconds."
        except OSError as exc:
            return f"Error starting PowerShell: {exc}"

        output = (result.stdout or "").strip()
        errors = (result.stderr or "").strip()
        if result.returncode != 0:
            return f"PowerShell exit code {result.returncode}\nSTDERR:\n{errors}\nSTDOUT:\n{output}".strip()
        return output or "PowerShell completed successfully with no output."

    def read_file(self, path: str) -> str:
        """Read a text file. Absolute paths are allowed for local agent work."""
        target = Path(path).expanduser().resolve()
        try:
            return target.read_text(encoding="utf-8")
        except FileNotFoundError:
            return f"Error: file not found: {target}"
        except (OSError, UnicodeDecodeError) as exc:
            return f"Error reading {target}: {exc}"

    def write_file(self, path: str, content: str) -> str:
        """Write a text file after explicit user approval."""
        target = Path(path).expanduser().resolve()
        if not self._approval(f"Write file {target}" ):
            return "File write denied by user."
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
            return f"File written successfully: {target}"
        except OSError as exc:
            return f"Error writing {target}: {exc}"

    def list_directory(self, path: str = "") -> str:
        target = (Path(path).expanduser() if path else self.workspace).resolve()
        try:
            entries = sorted(target.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
            return "\n".join(("[DIR] " if p.is_dir() else "      ") + p.name for p in entries) or "Directory is empty."
        except OSError as exc:
            return f"Error listing {target}: {exc}"

    def ollama_models(self) -> str:
        """Return the installed Ollama model list from the live local server."""
        import ollama

        try:
            response = ollama.list()
            models: Any = response.get("models", []) if isinstance(response, dict) else getattr(response, "models", [])
            lines = []
            for model in models:
                if isinstance(model, dict):
                    name = model.get("name", "unknown")
                    size = model.get("size", 0)
                else:
                    name = getattr(model, "model", getattr(model, "name", "unknown"))
                    size = getattr(model, "size", 0)
                size_gb = float(size) / (1024 ** 3) if size else 0
                lines.append(f"{name} — {size:,} bytes ({size_gb:.2f} GiB)")
            return "\n".join(lines) if lines else "No Ollama models are installed."
        except Exception as exc:
            return f"Error querying Ollama: {exc}"

    def memory_save(self, title: str, content: str, folder: str = "01_Memory") -> str:
        path = self.memory.remember(title, content, folder=folder)
        return f"Memory saved to Obsidian: {path}"

    def memory_search(self, query: str, limit: int = 5) -> str:
        results = self.memory.search(query, limit=max(1, min(limit, 10)))
        if not results:
            return "No relevant memory found."
        return "\n\n".join(
            f"--- {item['path']} (score={item['score']}) ---\n{item['content']}"
            for item in results
        )

    def definitions(self) -> list[dict[str, Any]]:
        return [
            {"type": "function", "function": {"name": "execute_powershell", "description": "Execute a PowerShell command on the CYRAX Windows machine. Use when real machine state or an action is required.", "parameters": {"type": "object", "properties": {"code": {"type": "string"}}, "required": ["code"]}}},
            {"type": "function", "function": {"name": "read_file", "description": "Read a UTF-8 text file from the local machine.", "parameters": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}}},
            {"type": "function", "function": {"name": "write_file", "description": "Write a UTF-8 text file to the local machine. Requires user approval.", "parameters": {"type": "object", "properties": {"path": {"type": "string"}, "content": {"type": "string"}}, "required": ["path", "content"]}}},
            {"type": "function", "function": {"name": "list_directory", "description": "List a local directory.", "parameters": {"type": "object", "properties": {"path": {"type": "string"}}}}},
            {"type": "function", "function": {"name": "ollama_models", "description": "Query the live local Ollama server for installed models and their sizes.", "parameters": {"type": "object", "properties": {}}}},
            {"type": "function", "function": {"name": "memory_save", "description": "Persist a user-approved long-term memory as Markdown in the Obsidian vault.", "parameters": {"type": "object", "properties": {"title": {"type": "string"}, "content": {"type": "string"}, "folder": {"type": "string", "default": "01_Memory"}}, "required": ["title", "content"]}}},
            {"type": "function", "function": {"name": "memory_search", "description": "Search CYRAX's persistent Obsidian memory.", "parameters": {"type": "object", "properties": {"query": {"type": "string"}, "limit": {"type": "integer", "default": 5}}, "required": ["query"]}}},
        ]

    def call(self, name: str, arguments: dict[str, Any]) -> str:
        fn = getattr(self, name, None)
        if fn is None or name.startswith("_"):
            return f"Error: unknown tool {name}"
        try:
            return str(fn(**arguments))
        except Exception as exc:
            return f"Error in {name}: {exc}"
