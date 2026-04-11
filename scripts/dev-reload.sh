#!/usr/bin/env bash
# Reinstall the mempalace CLI from the local working tree and remind
# the user to reload plugins inside Claude Code.
set -euo pipefail

echo "Reinstalling mempalace CLI from local source..."
uv tool install --force --editable .

echo ""
echo "Installed:"
uv tool list | grep -A2 "^mempalace "

echo ""
echo "If you're in a Claude Code session, run:  /reload-plugins"
