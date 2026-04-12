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

# Hook script names from all eras — old underscore style and current hyphen style.
MEMPALACE_HOOK_SCRIPTS = (
    "mempal_save_hook.sh",
    "mempal_precompact_hook.sh",
    "mempal-stop-hook.sh",
    "mempal-precompact-hook.sh",
    "mempal-sessionstart-hook.sh",
)

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


def _is_mempalace_hook(command: str) -> bool:
    """Check if a hook command refers to a mempalace hook script."""
    return any(("/" + s) in command or command == s or command.endswith(" " + s) for s in MEMPALACE_HOOK_SCRIPTS)


def remove_hooks() -> None:
    """Remove any mempalace hooks from ~/.claude/settings.json."""
    print("Removing hooks from settings.json...")
    if not CLAUDE_SETTINGS.exists():
        print("  ✓ No settings.json — nothing to remove.")
        return

    with CLAUDE_SETTINGS.open(encoding="utf-8") as f:
        settings = json.load(f)

    hooks = settings.get("hooks", {})
    total_removed = 0

    for hook_type in list(hooks):
        entries = hooks[hook_type]
        for entry in entries:
            inner = entry.get("hooks", [])
            original_len = len(inner)
            inner[:] = [h for h in inner if not _is_mempalace_hook(h.get("command", ""))]
            total_removed += original_len - len(inner)
        entries[:] = [e for e in entries if e.get("hooks", [])]
        if not entries:
            del hooks[hook_type]

    if not hooks:
        settings.pop("hooks", None)

    if total_removed:
        with CLAUDE_SETTINGS.open("w", encoding="utf-8") as f:
            json.dump(settings, f, indent=2)
            f.write("\n")
        print(f"  ✓ Removed {total_removed} hook(s)")
    else:
        print("  ✓ No mempalace hooks found.")


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
    remove_hooks()
    print()
    remove_claude_md()
    print()
    uninstall_uv_tool()

    palace_dir = Path.home() / ".mempalace"
    if palace_dir.exists():
        print(f"\nNote: Palace data at {palace_dir} was left intact.")
        print("      To remove it manually: rm -rf ~/.mempalace")

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

    # Step 3: CLAUDE.md awareness
    setup_claude_md()

    print("\nDone! Restart Claude Code for changes to take effect.")


if __name__ == "__main__":
    main()
