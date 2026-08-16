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

        # Open Interpreter uses LiteLLM for the LLM transport and its
        # Computer object for actual code execution. Ollama exposes an
        # OpenAI-compatible endpoint at /v1, including tool/function calls.
        interpreter.llm.model = f"ollama_chat/{model}"
        interpreter.llm.api_base = os.getenv(
            "CYRAX_OLLAMA_API_BASE", "http://127.0.0.1:11434"
        )
        interpreter.llm.supports_functions = True
        interpreter.llm.supports_vision = False

        # Keep Open Interpreter's execution engine. CYRAX does not execute
        # PowerShell/Python itself; the generated code is handed to
        # interpreter.computer, which provides the approval/safe-mode barrier.
        interpreter.computer.offline = True
        interpreter.auto_run = False
        interpreter.safe_mode = "ask"
        interpreter.loop = True

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
            "You are CYRAX, a local-first AI agent running on Windows.\n"
            "Your model is Qwen3 running locally through Ollama.\n"
            "You have an Obsidian vault as persistent long-term memory.\n"
            "Open Interpreter is your computer/code execution layer.\n"
            "When a task requires inspecting the machine, files, processes, GPU, "
            "Ollama, or other system state, use the execute tool instead of merely "
            "printing a proposed command.\n"
            "Do not describe an execute call as the final answer. Execute it, inspect "
            "the result, then answer the user.\n"
            "Do not invent memories. Treat retrieved Obsidian notes as memory, not truth.\n"
            "When the user explicitly asks you to remember something, use the CYRAX "
            "memory layer to persist it as Markdown in the Obsidian vault.\n\n"
            f"LONG-TERM MEMORY:\n{context}\n\n"
            f"USER:\n{user_message}"
        )

    def remember(self, title: str, content: str, folder: str = "01_Memory") -> Path:
        return self.memory.remember(title, content, folder=folder)

    def run(self, user_message: str):
        response = interpreter.chat(self.prompt(user_message), display=False)

        # chat(display=False) may return either one message or a list of
        # messages depending on the Open Interpreter version.
        if isinstance(response, list):
            text_parts = [
                item.get("content", "")
                for item in response
                if isinstance(item, dict) and item.get("type") == "message"
            ]
            text = "\n".join(part for part in text_parts if part).strip()
            if text:
                response = text

        self.memory.log(f"User: {user_message}\nCYRAX: {response}")
        return response


if __name__ == "__main__":
    cyrax = CYRAX()
    print("CYRAX online.")
    print(f"Model: {cyrax.model}")
    print(f"Obsidian memory: {cyrax.vault_path}")
    print("Open Interpreter: Computer execution enabled (Safe Mode: ask)")
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
