#!/usr/bin/env python3
"""
Install or uninstall MemPalace integration for Claude Code.

Sets up:
  - mempalace uv tool   (editable install from this repo)
  - Claude Code plugin  (claude plugin add .claude-plugin)

Usage:
    python scripts/setup_claude.py              # install
    python scripts/setup_claude.py --uninstall  # remove everything

Idempotent — safe to run multiple times.
Installs from the local clone so your fork's fixes are always in effect.
To update after pulling upstream: just `git rebase upstream/main` — no reinstall needed.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PLUGIN_DIR = REPO_ROOT / ".claude-plugin"
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
# Plugin registration
# ---------------------------------------------------------------------------


def register_plugin() -> None:
    """Register the .claude-plugin as a local Claude Code plugin."""
    print("Registering plugin...")

    claude = shutil.which("claude")
    if not claude:
        print("  ! claude CLI not found — skipping plugin registration.")
        print("    Install it from https://claude.ai/download and re-run.")
        return

    if not PLUGIN_DIR.exists():
        print(f"  ! .claude-plugin/ not found at {PLUGIN_DIR}")
        return

    result = subprocess.run(
        [claude, "plugin", "add", str(PLUGIN_DIR)],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode == 0:
        print(f"  ✓ Plugin registered from {PLUGIN_DIR}")
    else:
        # Plugin may already be registered
        stderr = result.stderr.strip()
        if "already" in stderr.lower():
            print("  ✓ Plugin already registered — skipping.")
        else:
            print(f"  ⚠ Plugin registration failed: {stderr}")


# ---------------------------------------------------------------------------
# Legacy MCP registration (kept for migration/cleanup)
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
            text=True,
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
            f.write("\n\n" if not content.endswith("\n") else "\n")
        f.write(MEMPALACE_CLAUDE_MD)
    print("  ✓ MemPalace section added")
    print(f"      {CLAUDE_MD}")


# ---------------------------------------------------------------------------
# Uninstall
# ---------------------------------------------------------------------------


def unregister_plugin() -> None:
    """Remove the mempalace plugin from Claude Code."""
    print("Removing plugin...")
    claude = shutil.which("claude")
    if not claude:
        print("  ! claude CLI not found — skipping.")
        return

    result = subprocess.run(
        [claude, "plugin", "remove", "mempalace"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode == 0:
        print("  ✓ Plugin removed")
    else:
        stderr = result.stderr.strip()
        if "not found" in stderr.lower() or "not registered" in stderr.lower():
            print("  ✓ Plugin not registered — nothing to remove.")
        else:
            print(f"  ⚠ Failed to remove plugin: {stderr}")


def unregister_mcp() -> None:
    """Remove the mempalace MCP server registration (legacy cleanup)."""
    print("Removing legacy MCP server...")
    claude = shutil.which("claude")
    if not claude:
        print("  ! claude CLI not found — skipping.")
        return

    result = subprocess.run(
        [claude, "mcp", "list"],
        capture_output=True,
        text=True,
        check=False,
    )
    if "mempalace" not in result.stdout:
        print("  ✓ Not registered — nothing to remove.")
        return

    rm = subprocess.run(
        [claude, "mcp", "remove", "mempalace", "-s", "user"],
        capture_output=True,
        text=True,
        check=False,
    )
    if rm.returncode == 0:
        print("  ✓ Removed legacy MCP server registration")
    else:
        print(f"  ⚠ Failed to remove: {rm.stderr.strip()}")


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


def remove_hooks() -> None:
    """Remove mempalace hooks from ~/.claude/settings.json (legacy cleanup)."""
    print("Removing legacy hooks...")
    if not CLAUDE_SETTINGS.exists():
        print("  ✓ No settings.json — nothing to remove.")
        return

    with CLAUDE_SETTINGS.open(encoding="utf-8") as f:
        settings = json.load(f)

    hooks = settings.get("hooks", {})
    total_removed = 0

    for hook_type in ("Stop", "PreCompact"):
        entries = hooks.get(hook_type, [])
        for script_name in ("mempal_save_hook.sh", "mempal_precompact_hook.sh"):
            total_removed += _remove_old_hooks(entries, script_name)
        # Clean up empty arrays
        if not entries:
            hooks.pop(hook_type, None)

    # Clean up empty hooks dict
    if not hooks:
        settings.pop("hooks", None)

    with CLAUDE_SETTINGS.open("w", encoding="utf-8") as f:
        json.dump(settings, f, indent=2)
        f.write("\n")

    if total_removed:
        print(f"  ✓ Removed {total_removed} legacy hook(s)")
    else:
        print("  ✓ No legacy mempalace hooks found.")


def remove_claude_md() -> None:
    """Remove the MemPalace section from ~/.claude/CLAUDE.md."""
    print("Removing CLAUDE.md section...")
    if not CLAUDE_MD.exists():
        print("  ✓ No CLAUDE.md — nothing to remove.")
        return

    content = CLAUDE_MD.read_text(encoding="utf-8")
    if "mempalace" not in content.lower():
        print("  ✓ No MemPalace section found.")
        return

    # Remove the ## MemPalace section (everything from the heading to the next ## or EOF)
    cleaned = re.sub(
        r"\n*## MemPalace\b.*?(?=\n## |\Z)",
        "",
        content,
        flags=re.DOTALL,
    )
    cleaned = cleaned.rstrip() + "\n" if cleaned.strip() else ""

    CLAUDE_MD.write_text(cleaned, encoding="utf-8")
    print("  ✓ MemPalace section removed")


def uninstall_uv_tool() -> None:
    """Uninstall the mempalace uv tool."""
    print("Uninstalling uv tool...")
    uv = shutil.which("uv")
    if not uv:
        print("  ! uv not found — skipping.")
        return

    uv_python = _uv_tools_dir() / "mempalace" / "bin" / "python"
    if not uv_python.exists():
        print("  ✓ Not installed — nothing to remove.")
        return

    result = subprocess.run(
        [uv, "tool", "uninstall", "mempalace"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode == 0:
        print("  ✓ Uninstalled mempalace uv tool")
    else:
        print(f"  ⚠ Failed: {result.stderr.strip()}")


def uninstall() -> None:
    """Remove all mempalace integrations from Claude Code."""
    print("Uninstalling mempalace...\n")

    unregister_plugin()
    print()
    unregister_mcp()
    print()
    remove_hooks()
    print()
    remove_claude_md()
    print()
    uninstall_uv_tool()

    print("\nDone! Restart Claude Code for changes to take effect.")


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------


def main() -> None:
    if "--uninstall" in sys.argv:
        uninstall()
        return

    if not PLUGIN_DIR.exists():
        print(
            f"Error: .claude-plugin/ not found at {PLUGIN_DIR}\nRun this script from inside the mempalace repo.",
            file=sys.stderr,
        )
        sys.exit(1)

    print("Installing mempalace...\n")

    # Step 1: Ensure uv tool is installed (puts mempalace + mempalace-mcp-server on PATH)
    find_python()
    print()

    # Step 2: Register as a Claude Code plugin (hooks, MCP, skills, commands)
    register_plugin()
    print()

    # Step 3: Clean up any legacy manual registrations
    unregister_mcp()
    print()
    remove_hooks()
    print()

    # Step 4: CLAUDE.md awareness
    setup_claude_md()

    print("\nDone! Restart Claude Code for changes to take effect.")


if __name__ == "__main__":
    main()
