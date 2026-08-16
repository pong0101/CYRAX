"""Patch an existing CYRAX checkout to use agent.request_router.

This is intentionally a small, idempotent source transformation so an
existing local checkout can adopt the router without manually editing the
large cyrax.py file.

Run from F:\\AI\\CYRAX:
    .\\.venv\\Scripts\\python.exe .\\scripts\\upgrade_request_routing.py
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "agent" / "cyrax.py"

text = TARGET.read_text(encoding="utf-8")
original = text

if "from request_router import RequestRouter" not in text:
    text = text.replace(
        "from tool_bridge import ToolBridge\n",
        "from tool_bridge import ToolBridge\nfrom request_router import RequestRouter\n",
        1,
    )

if "self.router = RequestRouter()" not in text:
    text = text.replace(
        "self.memory_policy = MemoryPolicy()\n        self.last_source = \"runtime\"",
        "self.memory_policy = MemoryPolicy()\n        self.router = RequestRouter()\n        self.last_source = \"runtime\"",
        1,
    )

old = '''        context = self.memory_context(user_message)\n        live_hint = (\n            "THIS IS A LIVE-STATE REQUEST. Do not answer from memory alone. Use the appropriate native tool first, then answer from its result."\n            if self._looks_live(user_message)\n            else "This is not obviously a live-state request. Use relevant long-term memory when helpful."\n        )'''
new = '''        context = self.memory_context(user_message)\n        route = self.router.classify(user_message)\n        if route.kind == "live":\n            live_hint = (\n                "THIS IS A LIVE-STATE REQUEST. Use the appropriate native live tool first. "\n                "Do not answer current-state facts from memory alone."\n            )\n        elif route.kind == "memory":\n            live_hint = (\n                "THIS IS A HISTORICAL/MEMORY REQUEST. Use semantic memory as the primary source; "\n                "do not replace historical facts with a live-state guess."\n            )\n        elif route.kind == "action":\n            live_hint = (\n                "THIS IS AN ACTION REQUEST. Actually execute the narrowest native tool available. "\n                "Do not merely print a proposed command."\n            )\n        elif route.kind == "memory_save":\n            live_hint = (\n                "THIS IS AN EXPLICIT MEMORY REQUEST. Save it using the memory tool/policy and only "\n                "claim success after the save succeeds."\n            )\n        else:\n            live_hint = "GENERAL REQUEST. Use memory only when relevant and do not invent current machine state."'''
if old in text:
    text = text.replace(old, new, 1)

old_prompt = '''            "TOOL PRIORITY:\\n"\n            "1. Deterministic runtime facts such as CYRAX's configured model are answered by CYRAX runtime, not by tools.\\n"\n            "2. Live machine state uses the appropriate native tool.\\n"\n            "3. Actions use the narrowest native tool available.\\n"\n            "4. PowerShell is a fallback only when no narrower native tool can perform the task.\\n\\n"'''
new_prompt = '''            "TOOL PRIORITY:\\n"\n            "1. Deterministic runtime facts such as CYRAX's configured model are answered by CYRAX runtime, not by tools.\\n"\n            "2. Live/current machine state uses the appropriate native live tool before memory.\\n"\n            "3. Historical questions use semantic memory.\\n"\n            "4. Actions use the narrowest native tool available.\\n"\n            "5. PowerShell is a fallback only when no narrower native tool can perform the task.\\n"\n            "6. When live and memory disagree, live wins for current-state facts.\\n\\n"'''
if old_prompt in text:
    text = text.replace(old_prompt, new_prompt, 1)

if text == original:
    print("No changes needed; request routing is already installed.")
else:
    TARGET.write_text(text, encoding="utf-8")
    print(f"Updated: {TARGET}")
    print("Next: run scripts/verify_runtime.py")
