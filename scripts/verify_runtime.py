"""CYRAX Runtime Verification Test.

Run on the Windows CYRAX machine with:
    .\.venv\Scripts\python.exe .\scripts\verify_runtime.py

This checks the runtime/tooling contracts without changing production state.
"""
from __future__ import annotations

import os
import tempfile
from pathlib import Path

# Allow imports from the repository's agent package when this script is run
# from the repository root.
import sys

ROOT = Path(__file__).resolve().parents[1]
AGENT = ROOT / "agent"
if str(AGENT) not in sys.path:
    sys.path.insert(0, str(AGENT))

from cyrax import CYRAX  # noqa: E402
from memory import MemoryManager  # noqa: E402
from memory.memory_policy import MemoryPolicy  # noqa: E402
from tool_bridge import ToolBridge  # noqa: E402


PASS = 0
FAIL = 0


def check(name: str, condition: bool, detail: str = "") -> None:
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"[PASS] {name}" + (f" — {detail}" if detail else ""))
    else:
        FAIL += 1
        print(f"[FAIL] {name}" + (f" — {detail}" if detail else ""))


def main() -> int:
    print("=== CYRAX Runtime Verification ===")
    print(f"Repo: {ROOT}")
    print()

    cyrax = CYRAX()
    check("1. Runtime model identity", cyrax.model == "qwen3:8b", f"model={cyrax.model}")

    # Runtime model questions must be deterministic and must not require a live
    # Ollama inventory lookup.
    answer = cyrax._deterministic_runtime_answer("ตอนนี้ CYRAX ใช้โมเดลอะไร?")
    check(
        "2. Runtime model routing",
        answer is not None and "qwen3:8b" in answer and "[Source: Runtime]" in answer,
        "deterministic runtime answer",
    )

    # Live Ollama state.
    bridge = ToolBridge(cyrax.memory)
    models_text = bridge.ollama_models()
    print("\nLive Ollama models:")
    print(models_text)
    check("3. Live Ollama query succeeds", not models_text.startswith("Error querying Ollama"))
    check("4. qwen3:8b is installed", "qwen3:8b" in models_text)
    check("5. qwen3-embedding:0.6b is installed", "qwen3-embedding:0.6b" in models_text)
    check(
        "6. qwen3:8b size is authoritative bytes/GiB",
        "5,225,388,164 bytes (4.87 GiB)" in models_text,
        "no bits wording in tool output",
    )
    check("7. Tool output never labels bytes as bits", "bits" not in models_text.lower() and "บิต" not in models_text)

    # LLM output normalization must correct the exact historical failure mode
    # without changing the underlying byte value.
    malformed = "qwen3:8b มีขนาด 5,225,388,164 bytes บิต (4.87 GiB)"
    normalized = cyrax._normalize_tool_units(
        malformed,
        [{"role": "tool", "content": "qwen3:8b — 5,225,388,164 bytes (4.87 GiB)"}],
    )
    check(
        "8. Unit normalization",
        "5,225,388,164 bytes" in normalized and "5,225,388,164 bytes บิต" not in normalized,
        normalized,
    )

    # Memory recall: use the configured vault and ensure project memory is
    # available without treating interaction logs as durable memory.
    memory = MemoryManager(str(cyrax.vault_path))
    recalled = memory.search("CYRAX qwen3:8b", limit=10)
    recalled_text = "\n".join(item["content"] for item in recalled)
    check("9. Long-term project memory recall", "CYRAX" in recalled_text and "qwen3:8b" in recalled_text)
    check(
        "10. Historical logs are excluded by default",
        all("04_Logs/" not in item["path"] and not item["path"].startswith("04_Logs/") for item in recalled),
    )

    # Ordinary questions must not become new memories.
    decision = MemoryPolicy().classify("ตอนนี้ qwen3:8b มีขนาดเท่าไหร่?")
    check("11. Informational size question is not auto-memory", not decision.should_save)

    # Verify the stated reality hierarchy even if a stale memory result is
    # deliberately injected. This is a routing/policy assertion, not a model
    # generation test.
    original_memory_context = cyrax.memory_context
    cyrax.memory_context = lambda query, limit=5: (
        "STALE MEMORY: qwen3:999b is installed and is the current model."
    )
    prompt = cyrax.system_prompt("ตอนนี้ qwen3:8b มีขนาดเท่าไหร่?")
    cyrax.memory_context = original_memory_context
    check(
        "12. Live-tool priority over memory is explicit",
        "Live tool results are the highest authority" in prompt
        and "If live evidence conflicts with memory, trust live evidence" in prompt,
    )

    # Actual tool execution path: write/read/delete a temporary file. Approval
    # is overridden only inside this test so CI-like verification is unattended;
    # production ToolBridge still requires explicit approval.
    temp_path = Path(tempfile.gettempdir()) / "CYRAX_RUNTIME_VERIFY.txt"
    original_approval = bridge._approval
    bridge._approval = staticmethod(lambda description: True)
    try:
        write_result = bridge.write_file(str(temp_path), "CYRAX RUNTIME VERIFY OK")
        read_result = bridge.read_file(str(temp_path))
        check("13. Native write tool executes", "File written successfully" in write_result)
        check("14. Native read tool returns exact content", read_result == "CYRAX RUNTIME VERIFY OK", read_result)
    finally:
        bridge._approval = original_approval
        try:
            temp_path.unlink(missing_ok=True)
        except OSError:
            pass
    check("15. Runtime test leaves no temporary file", not temp_path.exists())

    print()
    print(f"=== RESULT: {PASS} passed / {FAIL} failed ===")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
