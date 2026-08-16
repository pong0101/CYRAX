"""CYRAX: local Qwen3 agent with an Obsidian second brain."""

from __future__ import annotations

import os
from pathlib import Path

from interpreter import interpreter

from memory import MemoryManager


class CYRAX:
    def __init__(self, model: str = "qwen3:8b", vault_path: str | None = None):
        self.model = model
        self.vault_path = Path(
            vault_path
            or os.getenv("CYRAX_OBSIDIAN_VAULT", "F:/AI/CYRAX-Vault")
        ).expanduser().resolve()
        self.memory = MemoryManager(str(self.vault_path))

        # Open Interpreter routes the model through LiteLLM. The explicit
        # Ollama provider prefix avoids accidentally selecting another backend.
        interpreter.llm.model = f"ollama/{model}"
        interpreter.llm.api_base = os.getenv(
            "CYRAX_OLLAMA_HOST", "http://127.0.0.1:11434"
        )
        interpreter.auto_run = False
        interpreter.safe_mode = "ask"

    def memory_context(self, query: str, limit: int = 5) -> str:
        results = self.memory.search(query, limit=limit)
        if not results:
            return "No relevant long-term memory was found."

        blocks = []
        for item in results:
            blocks.append(
                f"--- {item['path']} (score={item['score']}) ---\n{item['content']}"
            )
        return "\n\n".join(blocks)

    def prompt(self, user_message: str) -> str:
        context = self.memory_context(user_message)
        return (
            "You are CYRAX, a local-first AI agent.\n"
            "You have an Obsidian vault as persistent long-term memory.\n"
            "Use tools when needed. Treat retrieved Obsidian notes as memory, not truth.\n"
            "Do not invent memories. If memory conflicts with current evidence, say so.\n"
            "When the user explicitly asks you to remember something, create a Markdown note "
            "in the Obsidian vault using the available CYRAX memory layer.\n\n"
            f"LONG-TERM MEMORY:\n{context}\n\n"
            f"USER:\n{user_message}"
        )

    def remember(self, title: str, content: str, folder: str = "01_Memory") -> Path:
        return self.memory.remember(title, content, folder=folder)

    def run(self, user_message: str):
        response = interpreter.chat(self.prompt(user_message))
        self.memory.log(f"User: {user_message}\nCYRAX: {response}")
        return response


if __name__ == "__main__":
    cyrax = CYRAX()
    print("CYRAX online.")
    print(f"Model: {cyrax.model}")
    print(f"Obsidian memory: {cyrax.vault_path}")
    print("Type 'exit' to quit.")

    while True:
        try:
            message = input("\nYou > ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nCYRAX offline.")
            break

        if message.lower() in {"exit", "quit"}:
            print("CYRAX offline.")
            break
        if not message:
            continue

        response = cyrax.run(message)
        if response:
            print(f"\nCYRAX > {response}")
