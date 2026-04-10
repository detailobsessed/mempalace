#!/bin/bash
# MemPalace SessionStart Hook — thin wrapper calling Python CLI
# All logic lives in mempalace.hooks_cli for cross-harness extensibility
INPUT=$(cat)
echo "$INPUT" | mempalace hook run --hook session-start --harness claude-code
