"""CYRAX: local Qwen3 agent with Open Interpreter + Obsidian second brain."""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

import ollama
from interpreter import interpreter

from memory import MemoryManager
from memory.memory_policy import MemoryPolicy
from tool_bridge import ToolBridge


class CYRAX:
    def __init__(self, model: str = "qwen3:8b", vault_path: str | None = None):
        self.model = model
        self.vault_path = Path(vault_path or os.getenv("CYRAX_OBSIDIAN_VAULT", "F:/AI/CYRAX-Vault")).expanduser().resolve()
        self.memory = MemoryManager(str(self.vault_path))
        self.tools = ToolBridge(self.memory)
        self.memory_policy = MemoryPolicy()
        self.last_source = "runtime"

        interpreter.llm.model = f"ollama_chat/{model}"
        interpreter.llm.api_base = os.getenv("CYRAX_OLLAMA_API_BASE", "http://127.0.0.1:11434")
        interpreter.llm.supports_functions = True
        interpreter.llm.supports_vision = False
        interpreter.computer.offline = True
        interpreter.auto_run = False
        interpreter.safe_mode = "ask"
        self.history: list[dict[str, Any]] = []

    def memory_context(self, query: str, limit: int = 5) -> str:
        results, mode = self.memory.semantic_search(query, limit=limit)
        if not results:
            return f"No relevant long-term memory was found. Retrieval mode: {mode}."
        return f"Retrieval mode: {mode}\n\n" + "\n\n".join(
            f"--- {item['path']} (score={item['score']}) ---\n{item['content']}" for item in results
        )

    @staticmethod
    def _looks_live(user_message: str) -> bool:
        text = user_message.lower()
        live_terms = (
            "ตอนนี้", "ปัจจุบัน", "ล่าสุด", "มีอะไรติดตั้ง", "สถานะ", "ollama",
            "gpu", "ram", "cpu", "ไฟล์นี้มี", "ไฟล์อะไร", "โฟลเดอร์",
            "process", "running", "ติดตั้งอยู่", "version", "เวอร์ชัน",
        )
        return any(term in text for term in live_terms)

    @staticmethod
    def _is_runtime_model_question(user_message: str) -> bool:
        """Return True for questions about CYRAX's configured main model."""
        text = user_message.strip().lower()
        if "ollama" in text and any(term in text for term in ("ติดตั้ง", "มีโมเดล", "models", "installed")):
            return False
        patterns = (
            "cyrax ใช้โมเดลอะไร", "cyrax ใช้โมเดลไหน", "cyrax ใช้ llm อะไร", "cyrax ใช้ llm ไหน",
            "โมเดลหลักของ cyrax", "โมเดลหลักคืออะไร", "ใช้โมเดลหลักอะไร", "ระบบสมองของโปรเจกต์นี้",
            "ระบบสมองของโปรเจคนี้", "main model", "main llm", "active model",
        )
        return any(pattern in text for pattern in patterns)

    def _deterministic_runtime_answer(self, user_message: str) -> str | None:
        if self._is_runtime_model_question(user_message):
            self.last_source = "runtime"
            return f"CYRAX ใช้โมเดลหลัก **{self.model}** ผ่าน Ollama\n\n[Source: Runtime]"
        return None

    def system_prompt(self, user_message: str) -> str:
        context = self.memory_context(user_message)
        live_hint = (
            "THIS IS A LIVE-STATE REQUEST. Do not answer from memory alone. Use the appropriate native tool first, then answer from its result."
            if self._looks_live(user_message)
            else "This is not obviously a live-state request. Use relevant long-term memory when helpful."
        )
        return (
            "You are CYRAX, a local-first AI agent running on Windows.\n"
            f"Your active local model is {self.model} through Ollama.\n"
            "Open Interpreter is installed as the computer/code execution layer.\n"
            "CYRAX uses an Obsidian vault as persistent long-term memory with semantic retrieval.\n\n"
            "TOOL PRIORITY:\n"
            "1. Deterministic runtime facts such as CYRAX's configured model are answered by CYRAX runtime, not by tools.\n"
            "2. Live machine state uses the appropriate native tool.\n"
            "3. Actions use the narrowest native tool available.\n"
            "4. PowerShell is a fallback only when no narrower native tool can perform the task.\n\n"
            "REALITY PRIORITY:\n"
            "1. Live tool results are the highest authority for current machine state.\n"
            "2. Current project files and explicit user statements come next.\n"
            "3. Obsidian long-term memory is context, not unquestionable truth.\n"
            "4. Old logs are historical evidence only.\n"
            "5. If live evidence conflicts with memory, trust live evidence and say that memory was stale.\n\n"
            "TOOL RESULT INTEGRITY:\n"
            "1. A successful native tool result is authoritative evidence.\n"
            "2. Never claim a file is empty, missing, or unread when read_file returned actual content.\n"
            "3. Never contradict exact content returned by read_file.\n"
            "4. Never replace a successful tool result with a guess from memory.\n"
            "5. For read-only file requests, report the returned file content faithfully.\n\n"
            "UNIT ACCURACY:\n"
            "1. Tool output that says bytes means BYTES. Never call bytes bits.\n"
            "2. If a tool returns N bytes, report N bytes and, when useful, convert to GiB as N / 1073741824.\n"
            "3. For the Ollama model list, the authoritative fields are the tool's bytes and GiB values. Do not reinterpret them.\n"
            "4. Never invent parameter counts, quantization, context length, embedding size, or other metadata unless a tool actually returned it.\n"
            "5. Before answering a tool-backed size question, copy the unit exactly from the tool result.\n\n"
            "MEMORY DISCIPLINE:\n"
            "1. A user statement containing a durable fact, preference, decision, task, or explicit remember instruction may be saved.\n"
            "2. Do NOT save ordinary informational questions, status questions, or requests for explanations as memories.\n"
            "3. Do not create memory merely because a question contains words such as project, model, Ollama, or CYRAX.\n\n"
            "RULES:\n"
            "1. When the user asks about live machine state, use the appropriate tool.\n"
            "2. When the user asks to create, modify, or execute something, actually call a tool; never merely print a proposed command.\n"
            "3. After a tool returns, inspect its result and answer based on that result.\n"
            "4. Never invent tool output, installed models, file contents, GPU state, or memories.\n"
            "5. For explicit memory requests, use memory_save or the memory policy. Do not claim to remember unless saving succeeds.\n"
            "6. Use semantic memory when a prior user fact or project detail is relevant.\n"
            "7. Keep answers concise unless the user asks for detail.\n\n"
            f"REQUEST CLASSIFICATION:\n{live_hint}\n\n"
            f"RELEVANT LONG-TERM MEMORY:\n{context}\n\nUSER REQUEST:\n{user_message}"
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
            return {"role": getattr(message, "role", "assistant"), "content": getattr(message, "content", ""), "tool_calls": getattr(message, "tool_calls", None)}
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

    @staticmethod
    def _normalize_tool_units(answer: str, messages: list[dict[str, Any]]) -> str:
        """Prevent LLM unit hallucinations when a live tool supplied an exact unit."""
        if not answer:
            return answer
        tool_text = "\n".join(str(message.get("content", "")) for message in messages if message.get("role") == "tool")
        if not tool_text or "bytes" not in tool_text.lower():
            return answer
        byte_numbers = set(re.findall(r"(?<!\d)(\d{1,3}(?:,\d{3})+|\d+)(?=\s+bytes\b)", tool_text, flags=re.IGNORECASE))
        for number in byte_numbers:
            answer = re.sub(rf"(?<!\d){re.escape(number)}\s+bytes\s+(?:บิต|bits?)\b", f"{number} bytes", answer, flags=re.IGNORECASE)
            answer = re.sub(rf"(?<!\d){re.escape(number)}(?=\s*(?:บิต|bits?)\b)", f"{number} bytes", answer, flags=re.IGNORECASE)
        return answer

    def _auto_memory(self, user_message: str) -> str | None:
        decision = self.memory_policy.classify(user_message)
        if not decision.should_save:
            return None
        folder = "02_Projects" if decision.category == "project" else "01_Memory"
        content = f"Original user statement:\n\n{user_message}\n\nClassification: {decision.category}\nReason: {decision.reason}"
        path = self.memory.remember(title=decision.title, content=content, folder=folder, memory_type=decision.category)
        return f"Auto-memory saved: {path}"

    def run(self, user_message: str) -> str:
        deterministic = self._deterministic_runtime_answer(user_message)
        if deterministic is not None:
            self.history.extend([{"role": "user", "content": user_message}, {"role": "assistant", "content": deterministic}])
            self.memory.log(f"User: {user_message}\nCYRAX: {deterministic}")
            return deterministic

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
                answer = self._normalize_tool_units(answer, messages)
                try:
                    memory_result = self._auto_memory(user_message)
                    if memory_result:
                        print(f"\nCYRAX memory: {memory_result}")
                except Exception as exc:
                    print(f"\nCYRAX memory warning: {exc}")
                self.history.extend([{"role": "user", "content": user_message}, {"role": "assistant", "content": answer}])
                self.memory.log(f"User: {user_message}\nCYRAX: {answer}")
                return answer
            messages.append({"role": "assistant", "content": message.get("content", ""), "tool_calls": tool_calls})
            for call in tool_calls:
                name, arguments = self._call_parts(call)
                print(f"\nCYRAX tool: {name}")
                result = self.tools.call(name, arguments)
                print(result)
                self.last_source = "live_tool" if name in {"ollama_models", "read_file", "list_directory"} else "action"
                messages.append({"role": "tool", "content": result})
                # Native read_file is already the authoritative answer. Do not
                # ask the LLM to reinterpret it and accidentally claim the file
                # is empty or missing. This also keeps read-only requests out of
                # the model's hallucination path.
                if name == "read_file" and not result.startswith("Error:"):
                    answer = result
                    self.history.extend([{"role": "user", "content": user_message}, {"role": "assistant", "content": answer}])
                    self.memory.log(f"User: {user_message}\nCYRAX: {answer}")
                    return answer
        return "I stopped after too many tool calls. Please try the request again."

    def remember(self, title: str, content: str, folder: str = "01_Memory") -> Path:
        return self.memory.remember(title, content, folder=folder)


if __name__ == "__main__":
    cyrax = CYRAX()
    print("CYRAX online.")
    print(f"Model: {cyrax.model}")
    print(f"Obsidian memory: {cyrax.vault_path}")
    print(f"Semantic memory model: {cyrax.memory.embedding_model}")
    print("Open Interpreter: installed / computer layer available")
    print("Native Ollama tools: enabled (approval required for writes/PowerShell)")
    print("Second Brain: semantic recall + live-reality priority + conservative auto-memory")
    print("Tool routing: deterministic runtime facts + native live tools + PowerShell fallback")
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
