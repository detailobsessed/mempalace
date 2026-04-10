"""Tests for mempalace.hooks_cli — hook logic for Claude Code integration."""

import contextlib
import io
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from mempalace.hooks_cli import (
    PRECOMPACT_BLOCK_REASON,
    SAVE_INTERVAL,
    _count_human_messages,
    _log,
    _maybe_auto_ingest,
    _mine_transcript,
    _parse_harness_input,
    _sanitize_session_id,
    hook_precompact,
    hook_session_start,
    hook_stop,
    run_hook,
)

# --- _sanitize_session_id ---


def test_sanitize_normal_id():
    assert _sanitize_session_id("abc-123_XYZ") == "abc-123_XYZ"


def test_sanitize_strips_dangerous_chars():
    assert _sanitize_session_id("../../etc/passwd") == "etcpasswd"


def test_sanitize_empty_returns_unknown():
    assert _sanitize_session_id("") == "unknown"
    assert _sanitize_session_id("!!!") == "unknown"


# --- _count_human_messages ---


def _write_transcript(path: Path, entries: list[dict]):
    with path.open("w", encoding="utf-8") as f:
        for entry in entries:
            f.write(json.dumps(entry) + "\n")


def test_count_human_messages_basic(tmp_path):
    transcript = tmp_path / "t.jsonl"
    _write_transcript(
        transcript,
        [
            {"message": {"role": "user", "content": "hello"}},
            {"message": {"role": "assistant", "content": "hi"}},
            {"message": {"role": "user", "content": "bye"}},
        ],
    )
    assert _count_human_messages(str(transcript)) == 2


def test_count_skips_command_messages(tmp_path):
    transcript = tmp_path / "t.jsonl"
    _write_transcript(
        transcript,
        [
            {"message": {"role": "user", "content": "<command-message>status</command-message>"}},
            {"message": {"role": "user", "content": "real question"}},
        ],
    )
    assert _count_human_messages(str(transcript)) == 1


def test_count_handles_list_content(tmp_path):
    transcript = tmp_path / "t.jsonl"
    _write_transcript(
        transcript,
        [
            {"message": {"role": "user", "content": [{"type": "text", "text": "hello"}]}},
            {
                "message": {
                    "role": "user",
                    "content": [{"type": "text", "text": "<command-message>x</command-message>"}],
                }
            },
        ],
    )
    assert _count_human_messages(str(transcript)) == 1


def test_count_missing_file():
    assert _count_human_messages("/nonexistent/path.jsonl") == 0


def test_count_empty_file(tmp_path):
    transcript = tmp_path / "t.jsonl"
    transcript.write_text("", encoding="utf-8")
    assert _count_human_messages(str(transcript)) == 0


def test_count_malformed_json_lines(tmp_path):
    transcript = tmp_path / "t.jsonl"
    transcript.write_text('not json\n{"message": {"role": "user", "content": "ok"}}\n', encoding="utf-8")
    assert _count_human_messages(str(transcript)) == 1


# --- hook_stop ---


def _capture_hook_output(hook_fn, data, harness="claude-code", state_dir=None):
    """Run a hook and capture its JSON stdout output."""
    buf = io.StringIO()
    patches = [patch("mempalace.hooks_cli._output", side_effect=lambda d: buf.write(json.dumps(d)))]
    if state_dir:
        patches.extend([
            patch("mempalace.hooks_cli.STATE_DIR", state_dir),
            patch("mempalace.hooks_cli._CONFIG_DIR", state_dir),
        ])
    with contextlib.ExitStack() as stack:
        for p in patches:
            stack.enter_context(p)
        hook_fn(data, harness)
    return json.loads(buf.getvalue())


def test_stop_hook_passthrough_when_active(tmp_path):
    with patch("mempalace.hooks_cli.STATE_DIR", tmp_path):
        result = _capture_hook_output(
            hook_stop,
            {"session_id": "test", "stop_hook_active": True, "transcript_path": ""},
            state_dir=tmp_path,
        )
    assert result == {}


def test_stop_hook_passthrough_when_active_string(tmp_path):
    with patch("mempalace.hooks_cli.STATE_DIR", tmp_path):
        result = _capture_hook_output(
            hook_stop,
            {"session_id": "test", "stop_hook_active": "true", "transcript_path": ""},
            state_dir=tmp_path,
        )
    assert result == {}


def test_stop_hook_passthrough_below_interval(tmp_path):
    transcript = tmp_path / "t.jsonl"
    _write_transcript(
        transcript,
        [{"message": {"role": "user", "content": f"msg {i}"}} for i in range(SAVE_INTERVAL - 1)],
    )
    result = _capture_hook_output(
        hook_stop,
        {"session_id": "test", "stop_hook_active": False, "transcript_path": str(transcript)},
        state_dir=tmp_path,
    )
    assert result == {}


def test_stop_hook_allows_at_interval_and_mines(tmp_path):
    """At save interval, hook returns allow (not block) and mines transcript in background."""
    transcript = tmp_path / "t.jsonl"
    _write_transcript(
        transcript,
        [{"message": {"role": "user", "content": f"msg {i}"}} for i in range(SAVE_INTERVAL)],
    )
    with patch("mempalace.hooks_cli._mine_transcript") as mock_mine:
        result = _capture_hook_output(
            hook_stop,
            {"session_id": "test", "stop_hook_active": False, "transcript_path": str(transcript)},
            state_dir=tmp_path,
        )
    assert result == {}
    mock_mine.assert_called_once_with(str(transcript))


def test_stop_hook_tracks_save_point(tmp_path):
    transcript = tmp_path / "t.jsonl"
    _write_transcript(
        transcript,
        [{"message": {"role": "user", "content": f"msg {i}"}} for i in range(SAVE_INTERVAL)],
    )
    data = {"session_id": "test", "stop_hook_active": False, "transcript_path": str(transcript)}

    # First call mines and allows
    with patch("mempalace.hooks_cli._mine_transcript"):
        result = _capture_hook_output(hook_stop, data, state_dir=tmp_path)
    assert result == {}

    # Second call with same count passes through (already saved, no re-mine)
    with patch("mempalace.hooks_cli._mine_transcript") as mock_mine:
        result = _capture_hook_output(hook_stop, data, state_dir=tmp_path)
    assert result == {}
    mock_mine.assert_not_called()


# --- hook_session_start ---


def test_session_start_passes_through(tmp_path):
    result = _capture_hook_output(
        hook_session_start,
        {"session_id": "test"},
        state_dir=tmp_path,
    )
    assert result == {}


# --- hook_precompact ---


def test_precompact_always_blocks(tmp_path):
    result = _capture_hook_output(
        hook_precompact,
        {"session_id": "test", "transcript_path": "/nonexistent/t.jsonl"},
        state_dir=tmp_path,
    )
    assert result["decision"] == "block"
    assert result["reason"] == PRECOMPACT_BLOCK_REASON


def test_precompact_mines_transcript_synchronously(tmp_path):
    """Precompact mines the transcript synchronously (subprocess.run, not Popen)."""
    transcript = tmp_path / "t.jsonl"
    transcript.write_text('{"message": {"role": "user", "content": "hello"}}', encoding="utf-8")
    with patch("mempalace.hooks_cli.subprocess.run") as mock_run:
        result = _capture_hook_output(
            hook_precompact,
            {"session_id": "test", "transcript_path": str(transcript)},
            state_dir=tmp_path,
        )
    assert result["decision"] == "block"
    # Verify convo mining was called synchronously
    calls = mock_run.call_args_list
    convo_mine_calls = [c for c in calls if "--mode" in c[0][0] and "convos" in c[0][0]]
    assert len(convo_mine_calls) == 1


# --- _log ---


def test_log_writes_to_hook_log(tmp_path):
    with patch("mempalace.hooks_cli.STATE_DIR", tmp_path):
        _log("test message")
    log_path = tmp_path / "hook.log"
    assert log_path.is_file()
    content = log_path.read_text(encoding="utf-8")
    assert "test message" in content


def test_log_oserror_is_silenced():
    """_log should not raise if the directory cannot be created."""
    with patch("mempalace.hooks_cli.STATE_DIR", Path("/nonexistent/deeply/nested/dir")):
        _log("this will fail silently")


# --- _maybe_auto_ingest ---


def test_maybe_auto_ingest_no_env(tmp_path):
    """Without MEMPAL_DIR set, does nothing."""
    with patch.dict("os.environ", {}, clear=True), patch("mempalace.hooks_cli.STATE_DIR", tmp_path):
        _maybe_auto_ingest()


def test_maybe_auto_ingest_with_env(tmp_path):
    """With MEMPAL_DIR set to a valid directory, spawns subprocess."""
    mempal_dir = tmp_path / "project"
    mempal_dir.mkdir()
    with patch.dict("os.environ", {"MEMPAL_DIR": str(mempal_dir)}), patch("mempalace.hooks_cli.STATE_DIR", tmp_path):
        with patch("mempalace.hooks_cli.subprocess.Popen") as mock_popen:
            _maybe_auto_ingest()
            mock_popen.assert_called_once()


def test_maybe_auto_ingest_oserror(tmp_path):
    """OSError during subprocess spawn is silenced."""
    mempal_dir = tmp_path / "project"
    mempal_dir.mkdir()
    with patch.dict("os.environ", {"MEMPAL_DIR": str(mempal_dir)}), patch("mempalace.hooks_cli.STATE_DIR", tmp_path):
        with patch("mempalace.hooks_cli.subprocess.Popen", side_effect=OSError("fail")):
            _maybe_auto_ingest()


# --- _mine_transcript ---


def test_mine_transcript_spawns_convo_mining(tmp_path):
    """Given a valid transcript, spawns background convo mining on its parent dir."""
    transcript = tmp_path / "t.jsonl"
    transcript.write_text('{"message": {"role": "user", "content": "hello"}}', encoding="utf-8")
    with patch("mempalace.hooks_cli.STATE_DIR", tmp_path):
        with patch("mempalace.hooks_cli.subprocess.Popen") as mock_popen:
            _mine_transcript(str(transcript))
            mock_popen.assert_called_once()
            call_args = mock_popen.call_args
            cmd = call_args[0][0] if call_args[0] else call_args[1].get("args", [])
            assert "--mode" in cmd
            assert "convos" in cmd
            assert str(tmp_path) in cmd


def test_mine_transcript_nonexistent_path_silent(tmp_path):
    """Nonexistent transcript path returns silently — no crash, no subprocess."""
    with patch("mempalace.hooks_cli.STATE_DIR", tmp_path):
        with patch("mempalace.hooks_cli.subprocess.Popen") as mock_popen:
            _mine_transcript("/nonexistent/transcript.jsonl")
            mock_popen.assert_not_called()


def test_mine_transcript_oserror_silenced(tmp_path):
    """OSError during subprocess spawn is silenced."""
    transcript = tmp_path / "t.jsonl"
    transcript.write_text('{"message": {"role": "user", "content": "hello"}}', encoding="utf-8")
    with patch("mempalace.hooks_cli.STATE_DIR", tmp_path):
        with patch("mempalace.hooks_cli.subprocess.Popen", side_effect=OSError("fail")):
            _mine_transcript(str(transcript))


# --- stop hook config opt-out ---


def test_stop_hook_skips_mining_when_auto_save_disabled(tmp_path):
    """When config has stop_hook.auto_save=false, hook returns {} without mining."""
    transcript = tmp_path / "t.jsonl"
    _write_transcript(
        transcript,
        [{"message": {"role": "user", "content": f"msg {i}"}} for i in range(SAVE_INTERVAL)],
    )
    # Write config.json into tmp_path which _capture_hook_output patches as _CONFIG_DIR
    (tmp_path / "config.json").write_text(json.dumps({"stop_hook": {"auto_save": False}}), encoding="utf-8")
    with patch("mempalace.hooks_cli._mine_transcript") as mock_mine:
        result = _capture_hook_output(
            hook_stop,
            {"session_id": "test", "stop_hook_active": False, "transcript_path": str(transcript)},
            state_dir=tmp_path,
        )
    assert result == {}
    mock_mine.assert_not_called()


def test_stop_hook_mines_when_auto_save_enabled(tmp_path):
    """When config has stop_hook.auto_save=true (default), mining happens."""
    transcript = tmp_path / "t.jsonl"
    _write_transcript(
        transcript,
        [{"message": {"role": "user", "content": f"msg {i}"}} for i in range(SAVE_INTERVAL)],
    )
    with patch("mempalace.hooks_cli._mine_transcript") as mock_mine:
        result = _capture_hook_output(
            hook_stop,
            {"session_id": "test", "stop_hook_active": False, "transcript_path": str(transcript)},
            state_dir=tmp_path,
        )
    assert result == {}
    mock_mine.assert_called_once()


# --- _parse_harness_input ---


def test_parse_harness_input_unknown():
    """Unknown harness should sys.exit(1)."""
    with pytest.raises(SystemExit) as exc_info:
        _parse_harness_input({"session_id": "test"}, "unknown-harness")
    assert exc_info.value.code == 1


def test_parse_harness_input_valid():
    result = _parse_harness_input(
        {"session_id": "abc-123", "stop_hook_active": True, "transcript_path": "/tmp/t.jsonl"},
        "claude-code",
    )
    assert result["session_id"] == "abc-123"
    assert result["stop_hook_active"] is True


# --- hook_stop with OSError on write ---


def test_stop_hook_oserror_on_last_save_read(tmp_path):
    """When last_save_file has invalid content, falls back to 0."""
    transcript = tmp_path / "t.jsonl"
    _write_transcript(
        transcript,
        [{"message": {"role": "user", "content": f"msg {i}"}} for i in range(SAVE_INTERVAL)],
    )
    (tmp_path / "test_last_save").write_text("not_a_number", encoding="utf-8")
    with patch("mempalace.hooks_cli._mine_transcript"):
        result = _capture_hook_output(
            hook_stop,
            {"session_id": "test", "stop_hook_active": False, "transcript_path": str(transcript)},
            state_dir=tmp_path,
        )
    assert result == {}


def test_stop_hook_oserror_on_write(tmp_path):
    """When write to last_save_file fails, hook still outputs correctly."""
    transcript = tmp_path / "t.jsonl"
    _write_transcript(
        transcript,
        [{"message": {"role": "user", "content": f"msg {i}"}} for i in range(SAVE_INTERVAL)],
    )

    def bad_write_text(*_args, **_kwargs):
        msg = "disk full"
        raise OSError(msg)

    with (
        patch("mempalace.hooks_cli.STATE_DIR", tmp_path),
        patch.object(Path, "write_text", bad_write_text),
        patch("mempalace.hooks_cli._mine_transcript"),
    ):
        result = _capture_hook_output(
            hook_stop,
            {
                "session_id": "test",
                "stop_hook_active": False,
                "transcript_path": str(transcript),
            },
            state_dir=tmp_path,
        )
    assert result == {}


# --- hook_precompact with MEMPAL_DIR ---


def test_precompact_with_mempal_dir(tmp_path):
    """Precompact runs subprocess.run when MEMPAL_DIR is set."""
    mempal_dir = tmp_path / "project"
    mempal_dir.mkdir()
    with patch.dict("os.environ", {"MEMPAL_DIR": str(mempal_dir)}), patch("mempalace.hooks_cli.subprocess.run") as mock_run:
        result = _capture_hook_output(
            hook_precompact,
            {"session_id": "test"},
            state_dir=tmp_path,
        )
    assert result["decision"] == "block"
    mock_run.assert_called_once()


def test_precompact_with_mempal_dir_oserror(tmp_path):
    """Precompact handles OSError from subprocess gracefully."""
    mempal_dir = tmp_path / "project"
    mempal_dir.mkdir()
    with patch.dict("os.environ", {"MEMPAL_DIR": str(mempal_dir)}):
        with patch("mempalace.hooks_cli.subprocess.run", side_effect=OSError("fail")):
            result = _capture_hook_output(
                hook_precompact,
                {"session_id": "test"},
                state_dir=tmp_path,
            )
    assert result["decision"] == "block"


# --- run_hook ---


def test_run_hook_dispatches_session_start(tmp_path):
    """run_hook reads stdin JSON and dispatches to correct handler."""
    stdin_data = json.dumps({"session_id": "run-test"})
    with patch("sys.stdin", io.StringIO(stdin_data)), patch("mempalace.hooks_cli.STATE_DIR", tmp_path):
        with patch("mempalace.hooks_cli._output") as mock_output:
            run_hook("session-start", "claude-code")
    mock_output.assert_called_once_with({})


def test_run_hook_dispatches_stop(tmp_path):
    transcript = tmp_path / "t.jsonl"
    _write_transcript(transcript, [{"message": {"role": "user", "content": f"msg {i}"}} for i in range(3)])
    stdin_data = json.dumps({
        "session_id": "run-test",
        "stop_hook_active": False,
        "transcript_path": str(transcript),
    })
    with patch("sys.stdin", io.StringIO(stdin_data)), patch("mempalace.hooks_cli.STATE_DIR", tmp_path):
        with patch("mempalace.hooks_cli._output") as mock_output:
            run_hook("stop", "claude-code")
    mock_output.assert_called_once_with({})


def test_run_hook_dispatches_precompact(tmp_path):
    stdin_data = json.dumps({"session_id": "run-test"})
    with patch("sys.stdin", io.StringIO(stdin_data)), patch("mempalace.hooks_cli.STATE_DIR", tmp_path):
        with patch("mempalace.hooks_cli._output") as mock_output:
            run_hook("precompact", "claude-code")
    mock_output.assert_called_once()
    call_args = mock_output.call_args[0][0]
    assert call_args["decision"] == "block"


def test_run_hook_unknown_hook():
    stdin_data = json.dumps({"session_id": "test"})
    with patch("sys.stdin", io.StringIO(stdin_data)):
        with pytest.raises(SystemExit) as exc_info:
            run_hook("nonexistent", "claude-code")
        assert exc_info.value.code == 1


def test_run_hook_invalid_json(tmp_path):
    """Invalid stdin JSON should not crash — falls back to empty dict."""
    with patch("sys.stdin", io.StringIO("not valid json")), patch("mempalace.hooks_cli.STATE_DIR", tmp_path):
        with patch("mempalace.hooks_cli._output") as mock_output:
            run_hook("session-start", "claude-code")
    mock_output.assert_called_once_with({})
