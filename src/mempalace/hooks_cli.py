"""
Hook logic for MemPalace — Python implementation of stop and precompact hooks.

Reads JSON from stdin, outputs JSON to stdout.
Supported hooks: session-start, stop, precompact
Supported harnesses: claude-code, codex (extensible to cursor, gemini, etc.)
"""

from __future__ import annotations

import contextlib
import json
import os
import re
import subprocess  # noqa: S404
import sys
from datetime import UTC, datetime
from pathlib import Path

SAVE_INTERVAL = 15
_CONFIG_DIR = Path.home() / ".mempalace"
STATE_DIR = _CONFIG_DIR / "hook_state"
_bg_procs: list[subprocess.Popen[bytes]] = []  # prevent GC ResourceWarning on fire-and-forget

STOP_BLOCK_REASON = (
    "AUTO-SAVE checkpoint (MemPalace). Save this session's key content:\n"
    "1. mempalace_diary_write — AAAK-compressed session summary\n"
    "2. mempalace_add_drawer — verbatim quotes, decisions, code snippets\n"
    "3. mempalace_kg_add — entity relationships (optional)\n"
    "Do NOT write to Claude Code's native auto-memory (.md files). "
    "Continue conversation after saving."
)

PRECOMPACT_BLOCK_REASON = (
    "COMPACTION IMMINENT (MemPalace). Save ALL session content before context is lost:\n"
    "1. mempalace_diary_write — thorough AAAK-compressed session summary\n"
    "2. mempalace_add_drawer — ALL verbatim quotes, decisions, code, context\n"
    "3. mempalace_kg_add — entity relationships (optional)\n"
    "Be thorough \u2014 after compaction, detailed context will be lost. "
    "Do NOT write to Claude Code's native auto-memory (.md files). "
    "Save everything to MemPalace, then allow compaction to proceed."
)


def _sanitize_session_id(session_id: str) -> str:
    """Only allow alnum, dash, underscore to prevent path traversal."""
    sanitized = re.sub(r"[^a-zA-Z0-9_-]", "", session_id)
    return sanitized or "unknown"


def _is_command_message(content: str | list) -> bool:
    """Check if message content is a command-message (should be skipped)."""
    if isinstance(content, str):
        return "<command-message>" in content
    if isinstance(content, list):
        text = " ".join(b.get("text", "") for b in content if isinstance(b, dict))
        return "<command-message>" in text
    return False


def _is_user_turn(entry: dict) -> bool:
    """Check if a transcript entry is a countable user turn (Claude Code or Codex)."""
    # Claude Code format: {"message": {"role": "user", "content": "..."}}
    msg = entry.get("message", {})
    if isinstance(msg, dict) and msg.get("role") == "user":
        return not _is_command_message(msg.get("content", ""))
    # Codex CLI format: {"type": "event_msg", "payload": {"type": "user_message", ...}}
    if entry.get("type") == "event_msg":
        payload = entry.get("payload", {})
        if isinstance(payload, dict) and payload.get("type") == "user_message":
            return not _is_command_message(payload.get("message", ""))
    return False


def _count_human_messages(transcript_path: str) -> int:
    """Count human messages in a JSONL transcript, skipping command-messages."""
    path = Path(transcript_path).expanduser()
    if not path.is_file():
        return 0
    count = 0
    try:
        with path.open(encoding="utf-8", errors="replace") as f:
            for line in f:
                try:
                    entry = json.loads(line)
                    if _is_user_turn(entry):
                        count += 1
                except json.JSONDecodeError, AttributeError:
                    pass
    except OSError:
        return 0
    return count


def _log(message: str) -> None:
    """Append to hook state log file."""
    try:
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        log_path = STATE_DIR / "hook.log"
        timestamp = datetime.now(tz=UTC).strftime("%H:%M:%S")
        with log_path.open("a", encoding="utf-8") as f:
            f.write(f"[{timestamp}] {message}\n")
    except OSError:
        pass


def _output(data: dict) -> None:
    """Print compact JSON to stdout (single line — required by Claude Code hooks)."""
    print(json.dumps(data, ensure_ascii=False))


def _maybe_auto_ingest(*, blocking: bool = False) -> None:
    """If MEMPAL_DIR is set and exists, run mempalace mine.

    Args:
        blocking: If True, wait for mining to finish (used by precompact
                  so memories land before compaction).
    """
    mempal_dir = os.environ.get("MEMPAL_DIR", "")
    if mempal_dir and Path(mempal_dir).is_dir():
        try:
            STATE_DIR.mkdir(parents=True, exist_ok=True)
            log_path = STATE_DIR / "hook.log"
            with log_path.open("a", encoding="utf-8") as log_f:
                cmd = [sys.executable, "-m", "mempalace", "mine", mempal_dir]
                if blocking:
                    subprocess.run(  # noqa: S603
                        cmd,
                        stdout=log_f,
                        stderr=log_f,
                        timeout=60,
                        check=False,
                    )
                else:
                    _bg_procs.append(
                        subprocess.Popen(cmd, stdout=log_f, stderr=log_f),  # noqa: S603
                    )
        except OSError, subprocess.SubprocessError:
            pass


SUPPORTED_HARNESSES = {"claude-code", "codex"}


def _parse_harness_input(data: dict, harness: str) -> dict:
    """Parse stdin JSON according to the harness type."""
    if harness not in SUPPORTED_HARNESSES:
        print(f"Unknown harness: {harness}", file=sys.stderr)
        sys.exit(1)
    return {
        "session_id": _sanitize_session_id(str(data.get("session_id", "unknown"))),
        "stop_hook_active": data.get("stop_hook_active", False),
        "transcript_path": str(data.get("transcript_path", "")),
    }


def hook_stop(data: dict, harness: str) -> None:
    """Stop hook: block every N messages for auto-save."""
    parsed = _parse_harness_input(data, harness)
    session_id = parsed["session_id"]
    stop_hook_active = parsed["stop_hook_active"]
    transcript_path = parsed["transcript_path"]

    # If already in a save cycle, let through (infinite-loop prevention)
    if str(stop_hook_active).lower() in {"true", "1", "yes"}:
        _output({})
        return

    # Count human messages
    exchange_count = _count_human_messages(transcript_path)

    # Track last save point
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    last_save_file = STATE_DIR / f"{session_id}_last_save"
    last_save = 0
    if last_save_file.is_file():
        try:
            last_save = int(last_save_file.read_text(encoding="utf-8").strip())
        except ValueError, OSError:
            last_save = 0

    since_last = exchange_count - last_save

    _log(f"Session {session_id}: {exchange_count} exchanges, {since_last} since last save")

    if since_last >= SAVE_INTERVAL and exchange_count > 0:
        # Update last save point
        with contextlib.suppress(OSError):
            last_save_file.write_text(str(exchange_count), encoding="utf-8")

        _log(f"TRIGGERING SAVE at exchange {exchange_count}")

        _maybe_auto_ingest()

        _output({"decision": "block", "reason": STOP_BLOCK_REASON})
    else:
        _output({})


def hook_session_start(data: dict, harness: str) -> None:
    """Session start hook: initialize session tracking state."""
    parsed = _parse_harness_input(data, harness)
    session_id = parsed["session_id"]

    _log(f"SESSION START for session {session_id}")

    STATE_DIR.mkdir(parents=True, exist_ok=True)

    # Pass through — no blocking on session start
    _output({})


def hook_precompact(data: dict, harness: str) -> None:
    """Precompact hook: always block with comprehensive save instruction."""
    parsed = _parse_harness_input(data, harness)
    session_id = parsed["session_id"]

    _log(f"PRE-COMPACT triggered for session {session_id}")

    # Auto-ingest synchronously before compaction (so memories land first)
    _maybe_auto_ingest(blocking=True)

    # Always block — compaction = save everything
    _output({"decision": "block", "reason": PRECOMPACT_BLOCK_REASON})


def run_hook(hook_name: str, harness: str) -> None:
    """Main entry point: read stdin JSON, dispatch to hook handler."""
    try:
        data = json.load(sys.stdin)
    except json.JSONDecodeError:
        _log("WARNING: Failed to parse stdin JSON, proceeding with empty data")
        data = {}

    hooks = {
        "session-start": hook_session_start,
        "stop": hook_stop,
        "precompact": hook_precompact,
    }

    handler = hooks.get(hook_name)
    if handler is None:
        print(f"Unknown hook: {hook_name}", file=sys.stderr)
        sys.exit(1)

    handler(data, harness)
