#!/usr/bin/env python3
"""
Install MemPalace integration for Claude Code.

Sets up:
  - Global MCP server  (claude mcp add mempalace -s user)
  - Auto-save hooks    (~/.claude/settings.json: Stop + PreCompact)

Usage:
    python scripts/setup_claude.py

Idempotent — safe to run multiple times.
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


# ---------------------------------------------------------------------------
# Python discovery
# ---------------------------------------------------------------------------


def _uv_tools_dir() -> Path:
    """Return the uv tools directory, respecting UV_TOOL_DIR if set."""
    env = os.environ.get("UV_TOOL_DIR")
    if env:
        return Path(env)
    return Path.home() / ".local" / "share" / "uv" / "tools"


def find_python() -> str:
    """
    Return the best Python path for running mempalace.mcp_server.

    Preference order:
      1. Python inside the mempalace uv tool venv (mempalace already installed)
      2. Any Python on PATH that can import mempalace
      3. System python3 / python (with a warning)
    """
    uv_python = _uv_tools_dir() / "mempalace" / "bin" / "python"
    if uv_python.exists():
        return str(uv_python)

    for candidate in ("python3", "python"):
        exe = shutil.which(candidate)
        if not exe:
            continue
        result = subprocess.run(
            [exe, "-c", "import mempalace"],
            capture_output=True,
            check=False,
        )
        if result.returncode == 0:
            return exe

    # Last resort — system python3 may not have mempalace, but warn and proceed
    fallback = shutil.which("python3") or shutil.which("python")
    if fallback:
        print(
            f"  ! Could not find a Python with mempalace installed.\n"
            f"    Falling back to {fallback}.\n"
            f"    Run `uv tool install mempalace` first for best results."
        )
        return fallback

    print("Error: no Python interpreter found on PATH.", file=sys.stderr)
    sys.exit(1)


# ---------------------------------------------------------------------------
# MCP registration
# ---------------------------------------------------------------------------


def register_mcp(python_path: str) -> None:
    """Register mempalace as a global MCP server via the claude CLI."""
    print("Registering MCP server...")

    claude = shutil.which("claude")
    if not claude:
        print("  ! claude CLI not found — skipping MCP registration.")
        print("    Install it from https://claude.ai/download and re-run.")
        return

    result = subprocess.run(
        [claude, "mcp", "list"],
        capture_output=True,
        text=True,
        check=False,
    )
    if "mempalace" in result.stdout:
        print("  ✓ Already registered — skipping.")
        return

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
    print(f"  ✓ Registered  ({python_path} -m mempalace.mcp_server)")


# ---------------------------------------------------------------------------
# Hook installation
# ---------------------------------------------------------------------------


def _hook_already_present(entries: list[dict], command: str) -> bool:
    return any(any(h.get("command") == command for h in entry.get("hooks", [])) for entry in entries)


def add_hooks() -> None:
    """Merge Stop and PreCompact hooks into ~/.claude/settings.json."""
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
    if _hook_already_present(stop_entries, save_hook):
        print("  ✓ Stop hook already present — skipping.")
    else:
        stop_entries.append({
            "matcher": "",
            "hooks": [{"type": "command", "command": save_hook, "timeout": 30}],
        })
        print("  ✓ Stop hook added")
        print(f"      {save_hook}")

    # -- PreCompact hook -----------------------------------------------------
    precompact_entries = hooks.setdefault("PreCompact", [])
    if _hook_already_present(precompact_entries, precompact_hook):
        print("  ✓ PreCompact hook already present — skipping.")
    else:
        precompact_entries.append({
            "hooks": [{"type": "command", "command": precompact_hook, "timeout": 30}],
        })
        print("  ✓ PreCompact hook added")
        print(f"      {precompact_hook}")

    CLAUDE_SETTINGS.parent.mkdir(parents=True, exist_ok=True)
    with CLAUDE_SETTINGS.open("w", encoding="utf-8") as f:
        json.dump(settings, f, indent=2)
        f.write("\n")


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

    python_path = find_python()
    print(f"Using Python: {python_path}\n")

    register_mcp(python_path)
    print()
    add_hooks()

    print("\nDone! Restart Claude Code for changes to take effect.")


if __name__ == "__main__":
    main()
