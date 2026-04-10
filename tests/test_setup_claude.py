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

    # Create fake plugin dir
    plugin_dir = tmp_path / ".claude-plugin"
    plugin_dir.mkdir()
    monkeypatch.setattr(setup_claude, "PLUGIN_DIR", plugin_dir)

    return tmp_path


# ---------------------------------------------------------------------------
# register_plugin
# ---------------------------------------------------------------------------


class TestRegisterPlugin:
    def test_skips_when_no_claude_cli(self, fake_home, capsys):
        with patch.object(shutil, "which", return_value=None):
            setup_claude.register_plugin()

        out = capsys.readouterr().out
        assert "claude CLI not found" in out

    def test_registers_plugin(self, fake_home):
        with (
            patch.object(shutil, "which", return_value="/usr/bin/claude"),
            patch("setup_claude.subprocess") as mock_sub,
        ):
            mock_sub.run.return_value.returncode = 0
            mock_sub.run.return_value.stderr = ""
            setup_claude.register_plugin()

        call_args = mock_sub.run.call_args[0][0]
        assert "plugin" in call_args
        assert "add" in call_args

    def test_handles_already_registered(self, fake_home, capsys):
        with (
            patch.object(shutil, "which", return_value="/usr/bin/claude"),
            patch("setup_claude.subprocess") as mock_sub,
        ):
            mock_sub.run.return_value.returncode = 1
            mock_sub.run.return_value.stderr = "already registered"
            setup_claude.register_plugin()

        out = capsys.readouterr().out
        assert "already registered" in out.lower()

    def test_skips_when_no_plugin_dir(self, fake_home, capsys, monkeypatch):
        monkeypatch.setattr(setup_claude, "PLUGIN_DIR", fake_home / "nonexistent")
        with patch.object(shutil, "which", return_value="/usr/bin/claude"):
            setup_claude.register_plugin()

        out = capsys.readouterr().out
        assert ".claude-plugin/ not found" in out


# ---------------------------------------------------------------------------
# unregister_plugin
# ---------------------------------------------------------------------------


class TestUnregisterPlugin:
    def test_skips_when_no_claude_cli(self, fake_home, capsys):
        with patch.object(shutil, "which", return_value=None):
            setup_claude.unregister_plugin()

        out = capsys.readouterr().out
        assert "claude CLI not found" in out

    def test_removes_plugin(self, fake_home):
        with (
            patch.object(shutil, "which", return_value="/usr/bin/claude"),
            patch("setup_claude.subprocess") as mock_sub,
        ):
            mock_sub.run.return_value.returncode = 0
            mock_sub.run.return_value.stderr = ""
            setup_claude.unregister_plugin()

        call_args = mock_sub.run.call_args[0][0]
        assert "plugin" in call_args
        assert "remove" in call_args

    def test_handles_not_found(self, fake_home, capsys):
        with (
            patch.object(shutil, "which", return_value="/usr/bin/claude"),
            patch("setup_claude.subprocess") as mock_sub,
        ):
            mock_sub.run.return_value.returncode = 1
            mock_sub.run.return_value.stderr = "not found"
            setup_claude.unregister_plugin()

        out = capsys.readouterr().out
        assert "not registered" in out.lower()


# ---------------------------------------------------------------------------
# _hook_matches_mempalace (legacy)
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
        assert not setup_claude._hook_matches_mempalace(
            "/some/path/save_hook.sh",
            "mempal_save_hook.sh",
        )

    def test_no_match_suffix_embedded(self):
        assert not setup_claude._hook_matches_mempalace(
            "/some/path/notmempal_save_hook.sh",
            "mempal_save_hook.sh",
        )


# ---------------------------------------------------------------------------
# _remove_old_hooks (legacy)
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
# remove_hooks (legacy cleanup)
# ---------------------------------------------------------------------------


class TestRemoveHooks:
    def test_no_settings_file(self, fake_home, capsys):
        setup_claude.CLAUDE_SETTINGS.unlink(missing_ok=True)
        setup_claude.remove_hooks()

        out = capsys.readouterr().out
        assert "No settings.json" in out

    def test_removes_mempalace_hooks(self, fake_home):
        old_settings = {
            "hooks": {
                "Stop": [{"hooks": [{"type": "command", "command": "/old/mempal_save_hook.sh"}]}],
                "PreCompact": [{"hooks": [{"type": "command", "command": "/old/mempal_precompact_hook.sh"}]}],
            }
        }
        setup_claude.CLAUDE_SETTINGS.write_text(json.dumps(old_settings), encoding="utf-8")

        setup_claude.remove_hooks()

        settings = json.loads(setup_claude.CLAUDE_SETTINGS.read_text(encoding="utf-8"))
        assert "hooks" not in settings

    def test_preserves_non_mempalace_hooks(self, fake_home):
        other_settings = {
            "hooks": {
                "Stop": [
                    {"hooks": [{"type": "command", "command": "/other/tool.sh"}]},
                    {"hooks": [{"type": "command", "command": "/path/mempal_save_hook.sh"}]},
                ],
            }
        }
        setup_claude.CLAUDE_SETTINGS.write_text(json.dumps(other_settings), encoding="utf-8")

        setup_claude.remove_hooks()

        settings = json.loads(setup_claude.CLAUDE_SETTINGS.read_text(encoding="utf-8"))
        assert len(settings["hooks"]["Stop"]) == 1
        assert settings["hooks"]["Stop"][0]["hooks"][0]["command"] == "/other/tool.sh"


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

    def test_idempotent(self, fake_home):
        setup_claude.setup_claude_md()
        setup_claude.setup_claude_md()

        content = setup_claude.CLAUDE_MD.read_text(encoding="utf-8")
        assert content.count("## MemPalace") == 1


# ---------------------------------------------------------------------------
# remove_claude_md
# ---------------------------------------------------------------------------


class TestRemoveClaudeMd:
    def test_no_file(self, fake_home, capsys):
        setup_claude.CLAUDE_MD.unlink(missing_ok=True)
        setup_claude.remove_claude_md()

        out = capsys.readouterr().out
        assert "No CLAUDE.md" in out

    def test_removes_mempalace_section(self, fake_home):
        content = "# My Config\n\nSome stuff.\n\n## MemPalace\n\nYou have MemPalace installed.\n"
        setup_claude.CLAUDE_MD.write_text(content, encoding="utf-8")

        setup_claude.remove_claude_md()

        result = setup_claude.CLAUDE_MD.read_text(encoding="utf-8")
        assert "MemPalace" not in result
        assert "# My Config" in result

    def test_roundtrip_install_then_uninstall(self, fake_home):
        setup_claude.CLAUDE_MD.write_text("# My Config\n\nExisting content.\n", encoding="utf-8")

        setup_claude.setup_claude_md()
        assert "MemPalace" in setup_claude.CLAUDE_MD.read_text(encoding="utf-8")

        setup_claude.remove_claude_md()
        result = setup_claude.CLAUDE_MD.read_text(encoding="utf-8")
        assert "MemPalace" not in result
        assert "# My Config" in result


# ---------------------------------------------------------------------------
# Legacy MCP registration
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

        assert mock_sub.run.call_count == 3


# ---------------------------------------------------------------------------
# uninstall_uv_tool
# ---------------------------------------------------------------------------


class TestUninstallUvTool:
    def test_skips_when_no_uv(self, capsys):
        with patch.object(shutil, "which", return_value=None):
            setup_claude.uninstall_uv_tool()

        out = capsys.readouterr().out
        assert "uv not found" in out

    def test_skips_when_not_installed(self, fake_home, capsys):
        with (
            patch.object(shutil, "which", return_value="/usr/bin/uv"),
            patch.object(setup_claude, "_uv_tools_dir", return_value=fake_home / "uv_tools"),
        ):
            setup_claude.uninstall_uv_tool()

        out = capsys.readouterr().out
        assert "Not installed" in out

    def test_uninstalls_when_present(self, fake_home):
        uv_dir = fake_home / "uv_tools" / "mempalace" / "bin"
        uv_dir.mkdir(parents=True)
        (uv_dir / "python").touch()

        with (
            patch.object(shutil, "which", return_value="/usr/bin/uv"),
            patch.object(setup_claude, "_uv_tools_dir", return_value=fake_home / "uv_tools"),
            patch("setup_claude.subprocess") as mock_sub,
        ):
            mock_sub.run.return_value.returncode = 0
            mock_sub.run.return_value.stderr = ""
            setup_claude.uninstall_uv_tool()

        call_args = mock_sub.run.call_args[0][0]
        assert "uninstall" in call_args
        assert "mempalace" in call_args
