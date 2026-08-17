"""Local hardening checks for CYRAX evidence integrity and approval gates."""

from __future__ import annotations

import tempfile
from pathlib import Path

from agent.cyrax import CYRAX
from agent.tool_bridge import ToolBridge


def check(condition: bool, label: str) -> None:
    if not condition:
        raise AssertionError(label)
    print(f"PASS: {label}")


def main() -> None:
    check(CYRAX._is_authoritative_read_tool("read_file"), "read_file is authoritative")
    check(CYRAX._is_authoritative_read_tool("list_directory"), "list_directory is authoritative")
    check(CYRAX._is_authoritative_read_tool("ollama_models"), "ollama_models is authoritative")
    check(not CYRAX._is_authoritative_read_tool("write_file"), "write_file is an action, not read evidence")

    with tempfile.TemporaryDirectory(prefix="cyrax-hardening-") as temp:
        root = Path(temp)
        (root / "E2E_TEST.txt").write_text("exact-name", encoding="utf-8")
        (root / "README.md").write_text("readme", encoding="utf-8")
        (root / "subdir").mkdir()

        bridge = ToolBridge(None)
        listing = bridge.list_directory(str(root))
        check("E2E_TEST.txt" in listing, "directory evidence preserves exact filename")
        check("README.md" in listing, "directory evidence preserves all files")
        check("[DIR] subdir" in listing, "directory evidence preserves directory entries")

        content = bridge.read_file(str(root / "E2E_TEST.txt"))
        check(content == "exact-name", "read_file preserves exact file content")

        ToolBridge._approval = staticmethod(lambda _description: False)
        denied_path = root / "denied.txt"
        denied = bridge.write_file(str(denied_path), "must-not-write")
        check(denied == "File write denied by user.", "write_file respects approval denial")
        check(not denied_path.exists(), "denied write creates no file")
        denied_ps = bridge.execute_powershell("Write-Output blocked")
        check(denied_ps == "Execution denied by user.", "PowerShell respects approval denial")

        ToolBridge._approval = staticmethod(lambda _description: True)
        allowed_path = root / "allowed.txt"
        allowed = bridge.write_file(str(allowed_path), "approved")
        check(allowed_path.exists(), "approved write creates the file")
        check(allowed == f"File written successfully: {allowed_path.resolve()}", "approved write reports exact path")

    print("HARDENING_CHECKS: PASS")


if __name__ == "__main__":
    main()
