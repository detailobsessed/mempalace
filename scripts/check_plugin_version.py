#!/usr/bin/env python3
"""Pre-commit hook: fail if .claude-plugin/ content changed without a version bump."""

import json
import subprocess
import sys

PLUGIN_JSON = ".claude-plugin/plugin.json"
VERSION_FILES = {PLUGIN_JSON}


def staged_files() -> set[str]:
    result = subprocess.run(
        ["git", "diff", "--cached", "--name-only"],
        capture_output=True,
        text=True,
        check=True,
    )
    return set(result.stdout.strip().splitlines())


def version_changed(path: str) -> bool:
    """Check if the version field changed in a staged JSON file."""
    try:
        old = subprocess.run(
            ["git", "show", f"HEAD:{path}"],
            capture_output=True,
            text=True,
            check=True,
        )
        old_version = json.loads(old.stdout).get("version")
    except subprocess.CalledProcessError, json.JSONDecodeError:
        return True  # new file or unparsable — don't block

    try:
        new = subprocess.run(
            ["git", "show", f":{path}"],
            capture_output=True,
            text=True,
            check=True,
        )
        new_version = json.loads(new.stdout).get("version")
    except subprocess.CalledProcessError, json.JSONDecodeError:
        return True  # staged deletion or unparsable — don't block

    return old_version != new_version


def main() -> int:
    files = staged_files()
    plugin_content = {f for f in files if f.startswith(".claude-plugin/") and f not in VERSION_FILES}

    if not plugin_content:
        return 0

    if PLUGIN_JSON not in files or not version_changed(PLUGIN_JSON):
        red = "\033[31m"
        yellow = "\033[33m"
        bold = "\033[1m"
        reset = "\033[0m"
        print(f"\n{red}{bold}✗ Plugin content changed without a version bump{reset}\n")
        print(f"  {yellow}Changed files:{reset}")
        for f in sorted(plugin_content):
            print(f"    • {f}")
        print(f"\n  {yellow}Action:{reset} bump version in {bold}{PLUGIN_JSON}{reset}\n")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
