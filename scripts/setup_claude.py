#!/usr/bin/env python3
"""
Install MemPalace integration for Claude Code.

Sets up:
  - mempalace uv tool   (editable install from this repo)
  - Global MCP server  (claude mcp add mempalace -s user)
  - Auto-save hooks    (~/.claude/settings.json: Stop + PreCompact)
  - CLAUDE.md entry    (~/.claude/CLAUDE.md: mempalace awareness)

Usage:
    python scripts/setup_claude.py

Idempotent — safe to run multiple times.
Installs from the local clone so your fork's fixes are always in effect.
To update after pulling upstream: just `git rebase upstream/main` — no reinstall needed.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
HOOKS_DIR = REPO_ROOT / "hooks"
CLAUDE_SETTINGS = Path.home() / ".claude" / "settings.json"
CLAUDE_MD = Path.home() / ".claude" / "CLAUDE.md"

MEMPALACE_CLAUDE_MD = """\
## MemPalace

You have MemPalace installed as an MCP server. Run `mempalace_status` at the \
start of each session to learn the memory protocol, AAAK dialect, and available \
tools.
"""


# ---------------------------------------------------------------------------
# Python discovery
# ---------------------------------------------------------------------------


def _uv_tools_dir() -> Path:
    """Return the uv tools directory, respecting UV_TOOL_DIR if set."""
    env = os.environ.get("UV_TOOL_DIR")
    if env:
        return Path(env)
    return Path.home() / ".local" / "share" / "uv" / "tools"


def _install_from_repo() -> None:
    """Install mempalace as an editable uv tool from this repo."""
    uv = shutil.which("uv")
    if not uv:
        print("Error: uv not found. Install it from https://docs.astral.sh/uv/", file=sys.stderr)
        sys.exit(1)
    print(f"  Installing mempalace (editable) from {REPO_ROOT} ...")
    subprocess.run([uv, "tool", "install", "--editable", str(REPO_ROOT)], check=True)
    print("  ✓ Installed")


def find_python() -> str:
    """
    Return the Python path for running mempalace.mcp_server.

    Installs from the local repo (editable) if not already present so the
    fork's code is always in effect for both the CLI and the MCP server.
    """
    uv_python = _uv_tools_dir() / "mempalace" / "bin" / "python"
    if not uv_python.exists():
        _install_from_repo()
    if uv_python.exists():
        return str(uv_python)

    print("Error: uv tool install succeeded but Python not found at expected path.", file=sys.stderr)
    sys.exit(1)


# ---------------------------------------------------------------------------
# MCP registration
# ---------------------------------------------------------------------------


def register_mcp(python_path: str) -> None:
    """Register mempalace as a global MCP server via the claude CLI.

    If a mempalace MCP server is already registered but uses a different
    command (e.g. PyPI instead of local fork), it is removed and re-added.
    """
    print("Registering MCP server...")

    claude = shutil.which("claude")
    if not claude:
        print("  ! claude CLI not found — skipping MCP registration.")
        print("    Install it from https://claude.ai/download and re-run.")
        return

    expected_command = f"{python_path} -m mempalace.mcp_server"

    result = subprocess.run(
        [claude, "mcp", "list"],
        capture_output=True,
        text=True,
        check=False,
    )
    if "mempalace" in result.stdout:
        if expected_command in result.stdout:
            print("  ✓ Already registered with correct command — skipping.")
            return
        print("  ! Registered with wrong command — replacing...")
        rm = subprocess.run(
            [claude, "mcp", "remove", "mempalace", "-s", "user"],
            capture_output=True,
            check=False,
        )
        if rm.returncode != 0:
            print(f"  ⚠ Failed to remove old registration: {rm.stderr.strip()}")

    subprocess.run(
        [
            claude,
            "mcp",
            "add",
            "mempalace",
            "-s",
            "user",
            "--",
            python_path,
            "-m",
            "mempalace.mcp_server",
        ],
        check=True,
    )
    print(f"  ✓ Registered  ({expected_command})")


# ---------------------------------------------------------------------------
# Hook installation
# ---------------------------------------------------------------------------


def _hook_matches_mempalace(command: str, script_name: str) -> bool:
    """Check if a hook command refers to a mempalace hook by filename."""
    return command.endswith("/" + script_name) or command == script_name


def _remove_old_hooks(entries: list[dict], script_name: str) -> int:
    """Remove any existing mempalace hook entries matching the script name.

    Returns the number of entries removed.
    """
    before = len(entries)
    entries[:] = [
        entry for entry in entries if not any(_hook_matches_mempalace(h.get("command", ""), script_name) for h in entry.get("hooks", []))
    ]
    return before - len(entries)


def add_hooks() -> None:
    """Merge Stop and PreCompact hooks into ~/.claude/settings.json.

    Replaces any existing mempalace hooks (regardless of install path)
    with hooks pointing to this repo's hooks directory.
    """
    print("Installing hooks...")

    save_hook = str(HOOKS_DIR / "mempal_save_hook.sh")
    precompact_hook = str(HOOKS_DIR / "mempal_precompact_hook.sh")

    settings: dict = {}
    if CLAUDE_SETTINGS.exists():
        with CLAUDE_SETTINGS.open(encoding="utf-8") as f:
            settings = json.load(f)

    hooks = settings.setdefault("hooks", {})

    # -- Stop hook -----------------------------------------------------------
    stop_entries = hooks.setdefault("Stop", [])
    removed = _remove_old_hooks(stop_entries, "mempal_save_hook.sh")
    if removed:
        print(f"  ✓ Removed {removed} old Stop hook(s)")
    stop_entries.append({
        "matcher": "",
        "hooks": [{"type": "command", "command": save_hook, "timeout": 30}],
    })
    print("  ✓ Stop hook set")
    print(f"      {save_hook}")

    # -- PreCompact hook -----------------------------------------------------
    precompact_entries = hooks.setdefault("PreCompact", [])
    removed = _remove_old_hooks(precompact_entries, "mempal_precompact_hook.sh")
    if removed:
        print(f"  ✓ Removed {removed} old PreCompact hook(s)")
    precompact_entries.append({
        "hooks": [{"type": "command", "command": precompact_hook, "timeout": 30}],
    })
    print("  ✓ PreCompact hook set")
    print(f"      {precompact_hook}")

    CLAUDE_SETTINGS.parent.mkdir(parents=True, exist_ok=True)
    with CLAUDE_SETTINGS.open("w", encoding="utf-8") as f:
        json.dump(settings, f, indent=2)
        f.write("\n")


# ---------------------------------------------------------------------------
# CLAUDE.md setup
# ---------------------------------------------------------------------------


def setup_claude_md() -> None:
    """Append a MemPalace section to ~/.claude/CLAUDE.md if not already present."""
    print("Setting up CLAUDE.md...")

    if CLAUDE_MD.exists():
        content = CLAUDE_MD.read_text(encoding="utf-8")
        if "mempalace" in content.lower():
            print("  ✓ Already present — skipping.")
            return
    else:
        content = ""

    CLAUDE_MD.parent.mkdir(parents=True, exist_ok=True)
    with CLAUDE_MD.open("a", encoding="utf-8") as f:
        if content:
            f.write("\n")
        f.write(MEMPALACE_CLAUDE_MD)
    print("  ✓ MemPalace section added")
    print(f"      {CLAUDE_MD}")


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------


def main() -> None:
    if not HOOKS_DIR.exists():
        print(
            f"Error: hooks/ not found at {HOOKS_DIR}\nRun this script from inside the mempalace repo.",
            file=sys.stderr,
        )
        sys.exit(1)

    print("Installing mempalace...")
    python_path = find_python()
    print(f"  Using Python: {python_path}\n")

    register_mcp(python_path)
    print()
    add_hooks()
    print()
    setup_claude_md()

    print("\nDone! Restart Claude Code for changes to take effect.")


if __name__ == "__main__":
    main()
