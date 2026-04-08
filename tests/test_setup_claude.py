"""Tests for scripts/setup_claude.py — the Claude Code installer."""

import json
import shutil
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# The setup script lives in scripts/, not in the package.
# Import it by inserting its directory into sys.path.
SCRIPTS_DIR = str(Path(__file__).resolve().parent.parent / "scripts")
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

import setup_claude  # noqa: E402

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def fake_home(tmp_path, monkeypatch):
    """Redirect all paths the setup script uses to a temp directory."""
    claude_dir = tmp_path / ".claude"
    claude_dir.mkdir()

    monkeypatch.setattr(setup_claude, "CLAUDE_SETTINGS", claude_dir / "settings.json")
    monkeypatch.setattr(setup_claude, "CLAUDE_MD", claude_dir / "CLAUDE.md")
    monkeypatch.setattr(setup_claude, "HOOKS_DIR", tmp_path / "hooks")

    # Create fake hook scripts so paths resolve
    hooks_dir = tmp_path / "hooks"
    hooks_dir.mkdir()
    (hooks_dir / "mempal_save_hook.sh").touch()
    (hooks_dir / "mempal_precompact_hook.sh").touch()

    return tmp_path


# ---------------------------------------------------------------------------
# _hook_matches_mempalace
# ---------------------------------------------------------------------------


class TestHookMatchesMempalace:
    def test_exact_match(self):
        assert setup_claude._hook_matches_mempalace("mempal_save_hook.sh", "mempal_save_hook.sh")

    def test_absolute_path(self):
        assert setup_claude._hook_matches_mempalace(
            "/home/user/repos/mempalace/hooks/mempal_save_hook.sh",
            "mempal_save_hook.sh",
        )

    def test_different_base_dirs(self):
        assert setup_claude._hook_matches_mempalace(
            "/home/user/.mempalace/hooks/mempal_save_hook.sh",
            "mempal_save_hook.sh",
        )

    def test_no_match_different_script(self):
        assert not setup_claude._hook_matches_mempalace(
            "/some/path/other_hook.sh",
            "mempal_save_hook.sh",
        )

    def test_no_match_partial_name(self):
        # "save_hook.sh" should not match "mempal_save_hook.sh"
        assert not setup_claude._hook_matches_mempalace(
            "/some/path/save_hook.sh",
            "mempal_save_hook.sh",
        )

    def test_no_match_suffix_embedded(self):
        # Must match after a slash, not just endswith
        assert not setup_claude._hook_matches_mempalace(
            "/some/path/notmempal_save_hook.sh",
            "mempal_save_hook.sh",
        )


# ---------------------------------------------------------------------------
# _remove_old_hooks
# ---------------------------------------------------------------------------


class TestRemoveOldHooks:
    def test_removes_matching_entries(self):
        entries = [
            {"hooks": [{"command": "/old/path/mempal_save_hook.sh"}]},
            {"hooks": [{"command": "/other/tool/hook.sh"}]},
        ]
        removed = setup_claude._remove_old_hooks(entries, "mempal_save_hook.sh")
        assert removed == 1
        assert len(entries) == 1
        assert entries[0]["hooks"][0]["command"] == "/other/tool/hook.sh"

    def test_removes_multiple_duplicates(self):
        entries = [
            {"hooks": [{"command": "/path/a/mempal_save_hook.sh"}]},
            {"hooks": [{"command": "/path/b/mempal_save_hook.sh"}]},
        ]
        removed = setup_claude._remove_old_hooks(entries, "mempal_save_hook.sh")
        assert removed == 2
        assert len(entries) == 0

    def test_no_match_leaves_entries_intact(self):
        entries = [
            {"hooks": [{"command": "/some/other_hook.sh"}]},
        ]
        removed = setup_claude._remove_old_hooks(entries, "mempal_save_hook.sh")
        assert removed == 0
        assert len(entries) == 1

    def test_empty_list(self):
        entries = []
        removed = setup_claude._remove_old_hooks(entries, "mempal_save_hook.sh")
        assert removed == 0


# ---------------------------------------------------------------------------
# add_hooks
# ---------------------------------------------------------------------------


class TestAddHooks:
    def test_fresh_install(self, fake_home):
        setup_claude.add_hooks()

        settings = json.loads(setup_claude.CLAUDE_SETTINGS.read_text(encoding="utf-8"))
        assert len(settings["hooks"]["Stop"]) == 1
        assert len(settings["hooks"]["PreCompact"]) == 1
        assert settings["hooks"]["Stop"][0]["hooks"][0]["timeout"] == 30
        assert settings["hooks"]["PreCompact"][0]["hooks"][0]["timeout"] == 30

    def test_replaces_old_hooks_different_path(self, fake_home):
        # Pre-populate with hooks from a different install location
        old_settings = {
            "hooks": {
                "Stop": [{"matcher": "*", "hooks": [{"type": "command", "command": "/old/mempal_save_hook.sh", "timeout": 30000}]}],
                "PreCompact": [{"hooks": [{"type": "command", "command": "/old/mempal_precompact_hook.sh", "timeout": 30000}]}],
            }
        }
        setup_claude.CLAUDE_SETTINGS.write_text(json.dumps(old_settings), encoding="utf-8")

        setup_claude.add_hooks()

        settings = json.loads(setup_claude.CLAUDE_SETTINGS.read_text(encoding="utf-8"))
        # Old hooks replaced, not duplicated
        assert len(settings["hooks"]["Stop"]) == 1
        assert len(settings["hooks"]["PreCompact"]) == 1
        # Points to new path
        stop_cmd = settings["hooks"]["Stop"][0]["hooks"][0]["command"]
        assert stop_cmd.endswith("hooks/mempal_save_hook.sh")
        assert "/old/" not in stop_cmd

    def test_preserves_non_mempalace_hooks(self, fake_home):
        other_settings = {
            "hooks": {
                "Stop": [{"hooks": [{"type": "command", "command": "/other/tool.sh"}]}],
            }
        }
        setup_claude.CLAUDE_SETTINGS.write_text(json.dumps(other_settings), encoding="utf-8")

        setup_claude.add_hooks()

        settings = json.loads(setup_claude.CLAUDE_SETTINGS.read_text(encoding="utf-8"))
        # Other hook preserved + mempalace hook added
        assert len(settings["hooks"]["Stop"]) == 2
        commands = [e["hooks"][0]["command"] for e in settings["hooks"]["Stop"]]
        assert "/other/tool.sh" in commands

    def test_idempotent(self, fake_home):
        setup_claude.add_hooks()
        setup_claude.add_hooks()

        settings = json.loads(setup_claude.CLAUDE_SETTINGS.read_text(encoding="utf-8"))
        assert len(settings["hooks"]["Stop"]) == 1
        assert len(settings["hooks"]["PreCompact"]) == 1

    def test_preserves_existing_settings(self, fake_home):
        existing = {"permissions": {"allow": ["Bash(ls:*)"]}, "outputStyle": "Explanatory"}
        setup_claude.CLAUDE_SETTINGS.write_text(json.dumps(existing), encoding="utf-8")

        setup_claude.add_hooks()

        settings = json.loads(setup_claude.CLAUDE_SETTINGS.read_text(encoding="utf-8"))
        assert settings["permissions"] == {"allow": ["Bash(ls:*)"]}
        assert settings["outputStyle"] == "Explanatory"
        assert "hooks" in settings


# ---------------------------------------------------------------------------
# setup_claude_md
# ---------------------------------------------------------------------------


class TestSetupClaudeMd:
    def test_creates_new_file(self, fake_home):
        setup_claude.setup_claude_md()

        content = setup_claude.CLAUDE_MD.read_text(encoding="utf-8")
        assert "MemPalace" in content
        assert "mempalace_status" in content

    def test_appends_to_existing(self, fake_home):
        setup_claude.CLAUDE_MD.write_text("# My Config\n\nSome existing content.\n", encoding="utf-8")

        setup_claude.setup_claude_md()

        content = setup_claude.CLAUDE_MD.read_text(encoding="utf-8")
        assert content.startswith("# My Config")
        assert "MemPalace" in content

    def test_skips_if_already_present(self, fake_home):
        setup_claude.CLAUDE_MD.write_text("## MemPalace\n\nAlready configured.\n", encoding="utf-8")

        setup_claude.setup_claude_md()

        content = setup_claude.CLAUDE_MD.read_text(encoding="utf-8")
        assert content.count("MemPalace") == 1

    def test_case_insensitive_detection(self, fake_home):
        setup_claude.CLAUDE_MD.write_text("Uses MEMPALACE for memory.\n", encoding="utf-8")

        setup_claude.setup_claude_md()

        content = setup_claude.CLAUDE_MD.read_text(encoding="utf-8")
        # Should not add another section
        assert "mempalace_status" not in content

    def test_idempotent(self, fake_home):
        setup_claude.setup_claude_md()
        setup_claude.setup_claude_md()

        content = setup_claude.CLAUDE_MD.read_text(encoding="utf-8")
        assert content.count("## MemPalace") == 1


# ---------------------------------------------------------------------------
# register_mcp
# ---------------------------------------------------------------------------


class TestRegisterMcp:
    def test_skips_when_no_claude_cli(self, capsys):
        with patch.object(shutil, "which", return_value=None):
            setup_claude.register_mcp("/fake/python")

        out = capsys.readouterr().out
        assert "claude CLI not found" in out

    def test_skips_when_correct_command_registered(self):
        python_path = "/tools/mempalace/bin/python"
        mcp_output = f"mempalace: {python_path} -m mempalace.mcp_server - Connected"

        with (
            patch.object(shutil, "which", return_value="/usr/bin/claude"),
            patch("setup_claude.subprocess") as mock_sub,
        ):
            mock_sub.run.return_value.stdout = mcp_output
            mock_sub.run.return_value.returncode = 0
            setup_claude.register_mcp(python_path)

        # Only called once (mcp list), not add
        assert mock_sub.run.call_count == 1

    def test_replaces_wrong_command(self):
        python_path = "/tools/mempalace/bin/python"
        mcp_output = "mempalace: uv run --with mempalace python -m mempalace.mcp_server"

        list_result = MagicMock(stdout=mcp_output, returncode=0)
        remove_result = MagicMock(stdout="", stderr="", returncode=0)
        add_result = MagicMock(stdout="", returncode=0)

        with (
            patch.object(shutil, "which", return_value="/usr/bin/claude"),
            patch("setup_claude.subprocess") as mock_sub,
        ):
            mock_sub.run.side_effect = [list_result, remove_result, add_result]
            setup_claude.register_mcp(python_path)

        # Called 3 times: list, remove, add
        assert mock_sub.run.call_count == 3
        remove_call = mock_sub.run.call_args_list[1]
        assert "remove" in remove_call[0][0]
        add_call = mock_sub.run.call_args_list[2]
        assert python_path in add_call[0][0]

    def test_adds_when_not_registered(self):
        python_path = "/tools/mempalace/bin/python"

        with (
            patch.object(shutil, "which", return_value="/usr/bin/claude"),
            patch("setup_claude.subprocess") as mock_sub,
        ):
            mock_sub.run.return_value.stdout = "other-server: something"
            mock_sub.run.return_value.returncode = 0
            setup_claude.register_mcp(python_path)

        # Called 2 times: list, add (no remove needed)
        assert mock_sub.run.call_count == 2
        add_call = mock_sub.run.call_args_list[1]
        assert "add" in add_call[0][0]
