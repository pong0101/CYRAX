"""CYRAX: local Qwen3 agent with Open Interpreter + Obsidian second brain."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import ollama
from interpreter import interpreter

from memory import MemoryManager
from tool_bridge import ToolBridge


class CYRAX:
    def __init__(self, model: str = "qwen3:8b", vault_path: str | None = None):
        self.model = model
        self.vault_path = Path(
            vault_path or os.getenv("CYRAX_OBSIDIAN_VAULT", "F:/AI/CYRAX-Vault")
        ).expanduser().resolve()
        self.memory = MemoryManager(str(self.vault_path))
        self.tools = ToolBridge(self.memory)

        # Open Interpreter remains installed/configured as CYRAX's computer
        # execution layer. OI 0.4.3 can mis-handle Ollama tool calls with some
        # LiteLLM versions, so native Ollama tool calling is the reliable router.
        interpreter.llm.model = f"ollama_chat/{model}"
        interpreter.llm.api_base = os.getenv(
            "CYRAX_OLLAMA_API_BASE", "http://127.0.0.1:11434"
        )
        interpreter.llm.supports_functions = True
        interpreter.llm.supports_vision = False
        interpreter.computer.offline = True
        interpreter.auto_run = False
        interpreter.safe_mode = "ask"

        self.history: list[dict[str, Any]] = []

    def memory_context(self, query: str, limit: int = 5) -> str:
        results = self.memory.search(query, limit=limit)
        if not results:
            return "No relevant long-term memory was found."
        return "\n\n".join(
            f"--- {item['path']} (score={item['score']}) ---\n{item['content']}"
            for item in results
        )

    def system_prompt(self, user_message: str) -> str:
        context = self.memory_context(user_message)
        return (
            "You are CYRAX, a local-first AI agent running on Windows.\n"
            f"Your active local model is {self.model} through Ollama.\n"
            "Open Interpreter is installed as the computer/code execution layer.\n"
            "CYRAX also exposes native Ollama tools for reliable local execution.\n\n"
            "RULES:\n"
            "1. When the user asks about live machine state, use the appropriate tool.\n"
            "2. When the user asks to create, modify, or execute something, actually call a tool; never merely print a proposed command.\n"
            "3. After a tool returns, inspect its result and answer based on that result.\n"
            "4. Never invent tool output, installed models, file contents, GPU state, or memories.\n"
            "5. For explicit memory requests, use memory_save. Do not claim to remember unless the tool succeeds.\n"
            "6. Use memory_search when a prior user fact or project detail is relevant.\n"
            "7. Keep answers concise unless the user asks for detail.\n\n"
            f"RELEVANT LONG-TERM MEMORY:\n{context}\n\n"
            f"USER REQUEST:\n{user_message}"
        )

    def _chat_once(self, messages: list[dict[str, Any]]) -> Any:
        return ollama.chat(
            model=self.model,
            messages=messages,
            tools=self.tools.definitions(),
            options={"num_ctx": int(os.getenv("CYRAX_NUM_CTX", "8192"))},
        )

    @staticmethod
    def _message_dict(response: Any) -> dict[str, Any]:
        if isinstance(response, dict):
            return response.get("message", response)
        message = getattr(response, "message", None)
        if isinstance(message, dict):
            return message
        if message is not None:
            return {
                "role": getattr(message, "role", "assistant"),
                "content": getattr(message, "content", ""),
                "tool_calls": getattr(message, "tool_calls", None),
            }
        return {"role": "assistant", "content": str(response)}

    @staticmethod
    def _tool_calls(message: dict[str, Any]) -> list[Any]:
        return message.get("tool_calls") or []

    @staticmethod
    def _call_parts(call: Any) -> tuple[str, dict[str, Any]]:
        if isinstance(call, dict):
            fn = call.get("function", call)
            return fn.get("name", ""), fn.get("arguments", {}) or {}
        fn = getattr(call, "function", None)
        if fn is None:
            return "", {}
        name = getattr(fn, "name", "")
        arguments = getattr(fn, "arguments", {}) or {}
        return name, arguments if isinstance(arguments, dict) else {}

    def run(self, user_message: str) -> str:
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": self.system_prompt(user_message)},
            *self.history,
            {"role": "user", "content": user_message},
        ]

        for _ in range(8):
            response = self._chat_once(messages)
            message = self._message_dict(response)
            tool_calls = self._tool_calls(message)

            if not tool_calls:
                answer = str(message.get("content", "")).strip()
                self.history.extend(
                    [
                        {"role": "user", "content": user_message},
                        {"role": "assistant", "content": answer},
                    ]
                )
                self.memory.log(f"User: {user_message}\nCYRAX: {answer}")
                return answer

            messages.append(
                {
                    "role": "assistant",
                    "content": message.get("content", ""),
                    "tool_calls": tool_calls,
                }
            )

            for call in tool_calls:
                name, arguments = self._call_parts(call)
                print(f"\nCYRAX tool: {name}")
                result = self.tools.call(name, arguments)
                print(result)
                messages.append({"role": "tool", "content": result})

        return "I stopped after too many tool calls. Please try the request again."

    def remember(self, title: str, content: str, folder: str = "01_Memory") -> Path:
        return self.memory.remember(title, content, folder=folder)


if __name__ == "__main__":
    cyrax = CYRAX()
    print("CYRAX online.")
    print(f"Model: {cyrax.model}")
    print(f"Obsidian memory: {cyrax.vault_path}")
    print("Open Interpreter: installed / computer layer available")
    print("Native Ollama tools: enabled (approval required for writes/PowerShell)")
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

        try:
            response = cyrax.run(message)
            if response:
                print(f"\nCYRAX > {response}")
        except Exception as exc:
            print(f"\nCYRAX ERROR > {exc}")
