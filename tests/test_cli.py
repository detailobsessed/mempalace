"""Tests for cli.py — command handlers and argparse routing."""

import argparse
import sys
from pathlib import Path

import chromadb
import pytest

from mempalace.cli import (
    cmd_compress,
    cmd_hook_logs,
    cmd_mine,
    cmd_search,
    cmd_split,
    cmd_status,
    cmd_wakeup,
    main,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_palace(tmp_path, drawers=None):
    """Create a palace with optional drawers and return its path string."""
    palace_path = str(tmp_path / "palace")
    client = chromadb.PersistentClient(path=palace_path)
    col = client.get_or_create_collection("mempalace_drawers")
    if drawers:
        col.add(
            ids=[d["id"] for d in drawers],
            documents=[d["document"] for d in drawers],
            metadatas=[d["metadata"] for d in drawers],
        )
    return palace_path


_DRAWER_META = {
    "wing": "testapp",
    "room": "general",
    "source_file": "hello.py",
    "agent": "mempalace",
    "mined_at": "2025-01-01T00:00:00Z",
}


def _default_drawers(n=3):
    return [
        {
            "id": f"d{i}",
            "document": f"Drawer number {i} content about testing and code quality.",
            "metadata": {**_DRAWER_META, "room": "general" if i % 2 == 0 else "tests"},
        }
        for i in range(n)
    ]


def _fake_config(palace_path):
    """Return a callable that produces a fake MempalaceConfig with the given palace_path."""

    class _FakeConfig:
        def __init__(self):
            self.palace_path = palace_path

        def init(self):
            pass

    return _FakeConfig


# ---------------------------------------------------------------------------
# __main__.py entry point
# ---------------------------------------------------------------------------


class TestMainModule:
    def test_main_module_imports(self):
        from mempalace import main

        assert callable(main)


# ---------------------------------------------------------------------------
# cmd_status
# ---------------------------------------------------------------------------


class TestCmdStatus:
    def test_status_with_drawers(self, tmp_path, capsys):
        palace_path = _make_palace(tmp_path, _default_drawers(3))
        args = argparse.Namespace(palace=palace_path)
        cmd_status(args)
        out = capsys.readouterr().out
        assert "3 drawers" in out
        assert "testapp" in out

    def test_status_empty_palace(self, tmp_path, capsys):
        palace_path = _make_palace(tmp_path, [])
        args = argparse.Namespace(palace=palace_path)
        cmd_status(args)
        out = capsys.readouterr().out
        assert "0 drawers" in out

    def test_status_no_palace(self, tmp_path, capsys):
        palace_path = str(tmp_path / "nonexistent")
        args = argparse.Namespace(palace=palace_path)
        cmd_status(args)
        out = capsys.readouterr().out
        assert "No palace found" in out

    def test_status_uses_config_when_no_palace_arg(self, tmp_path, capsys, monkeypatch):
        palace_path = _make_palace(tmp_path, _default_drawers(1))
        monkeypatch.setattr("mempalace.cli.MempalaceConfig", _fake_config(palace_path))
        args = argparse.Namespace(palace=None)
        cmd_status(args)
        out = capsys.readouterr().out
        assert "1 drawers" in out


# ---------------------------------------------------------------------------
# cmd_search
# ---------------------------------------------------------------------------


class TestCmdSearch:
    def test_search_finds_results(self, tmp_path, capsys):
        palace_path = _make_palace(tmp_path, _default_drawers(3))
        args = argparse.Namespace(
            palace=palace_path,
            query="testing code quality",
            wing=None,
            room=None,
            results=5,
        )
        cmd_search(args)
        out = capsys.readouterr().out
        assert "Results for" in out
        assert "testing" in out.lower()

    def test_search_with_wing_filter(self, tmp_path, capsys):
        palace_path = _make_palace(tmp_path, _default_drawers(3))
        args = argparse.Namespace(
            palace=palace_path,
            query="drawer content",
            wing="testapp",
            room=None,
            results=2,
        )
        cmd_search(args)
        out = capsys.readouterr().out
        assert "Results for" in out
        assert "testapp" in out

    def test_search_with_room_filter(self, tmp_path, capsys):
        palace_path = _make_palace(tmp_path, _default_drawers(3))
        args = argparse.Namespace(
            palace=palace_path,
            query="drawer content",
            wing=None,
            room="general",
            results=5,
        )
        cmd_search(args)
        out = capsys.readouterr().out
        assert "Results for" in out

    def test_search_no_palace_exits(self, tmp_path):
        palace_path = str(tmp_path / "nonexistent")
        args = argparse.Namespace(
            palace=palace_path,
            query="anything",
            wing=None,
            room=None,
            results=5,
        )
        with pytest.raises(SystemExit):
            cmd_search(args)

    def test_search_uses_config_when_no_palace_arg(self, tmp_path, capsys, monkeypatch):
        palace_path = _make_palace(tmp_path, _default_drawers(2))
        monkeypatch.setattr("mempalace.cli.MempalaceConfig", _fake_config(palace_path))
        args = argparse.Namespace(
            palace=None,
            query="drawer content",
            wing=None,
            room=None,
            results=5,
        )
        cmd_search(args)
        out = capsys.readouterr().out
        assert "Results for" in out


# ---------------------------------------------------------------------------
# cmd_wakeup
# ---------------------------------------------------------------------------


class TestCmdWakeup:
    def test_wakeup_empty_palace(self, tmp_path, capsys):
        palace_path = _make_palace(tmp_path, [])
        args = argparse.Namespace(palace=palace_path, wing=None)
        cmd_wakeup(args)
        out = capsys.readouterr().out
        assert "Wake-up text" in out
        assert "tokens" in out

    def test_wakeup_with_drawers(self, tmp_path, capsys):
        palace_path = _make_palace(tmp_path, _default_drawers(3))
        args = argparse.Namespace(palace=palace_path, wing=None)
        cmd_wakeup(args)
        out = capsys.readouterr().out
        assert "Wake-up text" in out
        assert "=" * 50 in out

    def test_wakeup_with_wing(self, tmp_path, capsys):
        palace_path = _make_palace(tmp_path, _default_drawers(3))
        args = argparse.Namespace(palace=palace_path, wing="testapp")
        cmd_wakeup(args)
        out = capsys.readouterr().out
        assert "Wake-up text" in out

    def test_wakeup_uses_config_when_no_palace_arg(self, tmp_path, capsys, monkeypatch):
        palace_path = _make_palace(tmp_path, _default_drawers(1))
        monkeypatch.setattr("mempalace.cli.MempalaceConfig", _fake_config(palace_path))
        args = argparse.Namespace(palace=None, wing=None)
        cmd_wakeup(args)
        out = capsys.readouterr().out
        assert "Wake-up text" in out


# ---------------------------------------------------------------------------
# cmd_mine (project mode)
# ---------------------------------------------------------------------------


class TestCmdMine:
    def _make_project(self, tmp_path):
        """Create a minimal project directory with mempalace.yaml and a source file."""
        project = tmp_path / "myproject"
        project.mkdir()
        yaml_content = "wing: myproject\nrooms:\n  - name: general\n    description: All project files\n"
        (project / "mempalace.yaml").write_text(yaml_content, encoding="utf-8")
        (project / "hello.py").write_text("# A simple hello world\n" + "print('hello')\n" * 20, encoding="utf-8")
        return str(project)

    def test_mine_dry_run(self, tmp_path, capsys):
        project_dir = self._make_project(tmp_path)
        palace_path = str(tmp_path / "palace")
        args = argparse.Namespace(
            dir=project_dir,
            palace=palace_path,
            mode="projects",
            wing=None,
            agent="test",
            limit=0,
            dry_run=True,
            extract="exchange",
            include_ignored=[],
            no_gitignore=False,
        )
        cmd_mine(args)
        out = capsys.readouterr().out
        assert "MemPalace Mine" in out
        assert "DRY RUN" in out

    def test_mine_files_into_palace(self, tmp_path, capsys):
        project_dir = self._make_project(tmp_path)
        palace_path = str(tmp_path / "palace")
        args = argparse.Namespace(
            dir=project_dir,
            palace=palace_path,
            mode="projects",
            wing=None,
            agent="test",
            limit=0,
            dry_run=False,
            extract="exchange",
            include_ignored=[],
            no_gitignore=False,
        )
        cmd_mine(args)
        out = capsys.readouterr().out
        assert "Done" in out

        # Verify drawers were created
        client = chromadb.PersistentClient(path=palace_path)
        col = client.get_collection("mempalace_drawers")
        count = col.count()
        assert count > 0

    def test_mine_with_wing_override(self, tmp_path, capsys):
        project_dir = self._make_project(tmp_path)
        palace_path = str(tmp_path / "palace")
        args = argparse.Namespace(
            dir=project_dir,
            palace=palace_path,
            mode="projects",
            wing="custom_wing",
            agent="test",
            limit=1,
            dry_run=False,
            extract="exchange",
            include_ignored=[],
            no_gitignore=False,
        )
        cmd_mine(args)
        out = capsys.readouterr().out
        assert "custom_wing" in out

    def test_mine_uses_config_when_no_palace_arg(self, tmp_path, capsys, monkeypatch):
        project_dir = self._make_project(tmp_path)
        palace_path = str(tmp_path / "palace")
        monkeypatch.setattr("mempalace.cli.MempalaceConfig", _fake_config(palace_path))
        args = argparse.Namespace(
            dir=project_dir,
            palace=None,
            mode="projects",
            wing=None,
            agent="test",
            limit=0,
            dry_run=True,
            extract="exchange",
            include_ignored=[],
            no_gitignore=False,
        )
        cmd_mine(args)
        out = capsys.readouterr().out
        assert "MemPalace Mine" in out

    def test_mine_convos_mode(self, tmp_path, monkeypatch):
        """Test that convos mode dispatches to convo_miner.mine_convos."""
        called_with = {}

        def fake_mine_convos(**kwargs):
            called_with.update(kwargs)

        monkeypatch.setattr("mempalace.convo_miner.mine_convos", fake_mine_convos)

        convo_dir = str(tmp_path / "chats")
        Path(convo_dir).mkdir()
        palace_path = str(tmp_path / "palace")

        args = argparse.Namespace(
            dir=convo_dir,
            palace=palace_path,
            mode="convos",
            wing="convos_wing",
            agent="test",
            limit=5,
            dry_run=True,
            extract="exchange",
            include_ignored=[],
            no_gitignore=False,
        )
        cmd_mine(args)
        assert called_with["convo_dir"] == convo_dir
        assert called_with["wing"] == "convos_wing"
        assert called_with["dry_run"] is True
        assert called_with["extract_mode"] == "exchange"


# ---------------------------------------------------------------------------
# cmd_compress
# ---------------------------------------------------------------------------


class TestCmdCompress:
    def test_compress_dry_run(self, tmp_path, capsys):
        palace_path = _make_palace(tmp_path, _default_drawers(2))
        args = argparse.Namespace(
            palace=palace_path,
            wing=None,
            dry_run=True,
            config=None,
        )
        cmd_compress(args)
        out = capsys.readouterr().out
        assert "Compressing 2 drawers" in out
        assert "dry run" in out.lower()

    def test_compress_stores_results(self, tmp_path, capsys):
        palace_path = _make_palace(tmp_path, _default_drawers(2))
        args = argparse.Namespace(
            palace=palace_path,
            wing=None,
            dry_run=False,
            config=None,
        )
        cmd_compress(args)
        out = capsys.readouterr().out
        assert "Stored 2 compressed drawers" in out

        # Verify compressed collection exists
        client = chromadb.PersistentClient(path=palace_path)
        comp_col = client.get_collection("mempalace_compressed")
        assert comp_col.count() == 2

    def test_compress_with_wing_filter(self, tmp_path, capsys):
        drawers = _default_drawers(3)
        drawers[0]["metadata"]["wing"] = "other_wing"
        palace_path = _make_palace(tmp_path, drawers)

        args = argparse.Namespace(
            palace=palace_path,
            wing="testapp",
            dry_run=True,
            config=None,
        )
        cmd_compress(args)
        out = capsys.readouterr().out
        assert "Compressing 2 drawers" in out
        assert "wing 'testapp'" in out

    def test_compress_no_drawers(self, tmp_path, capsys):
        palace_path = _make_palace(tmp_path, [])
        args = argparse.Namespace(
            palace=palace_path,
            wing="nonexistent",
            dry_run=False,
            config=None,
        )
        cmd_compress(args)
        out = capsys.readouterr().out
        assert "No drawers found" in out

    def test_compress_no_palace_exits(self, tmp_path):
        palace_path = str(tmp_path / "nonexistent")
        args = argparse.Namespace(
            palace=palace_path,
            wing=None,
            dry_run=False,
            config=None,
        )
        with pytest.raises(SystemExit):
            cmd_compress(args)

    def test_compress_with_entity_config(self, tmp_path, capsys):
        palace_path = _make_palace(tmp_path, _default_drawers(1))
        config_file = tmp_path / "entities.json"
        config_file.write_text('{"people": ["Alice"], "projects": ["TestApp"]}', encoding="utf-8")

        args = argparse.Namespace(
            palace=palace_path,
            wing=None,
            dry_run=True,
            config=str(config_file),
        )
        cmd_compress(args)
        out = capsys.readouterr().out
        assert "Loaded entity config" in out
        assert "Compressing 1 drawers" in out

    def test_compress_uses_config_when_no_palace_arg(self, tmp_path, capsys, monkeypatch):
        palace_path = _make_palace(tmp_path, _default_drawers(1))
        monkeypatch.setattr("mempalace.cli.MempalaceConfig", _fake_config(palace_path))
        args = argparse.Namespace(
            palace=None,
            wing=None,
            dry_run=True,
            config=None,
        )
        cmd_compress(args)
        out = capsys.readouterr().out
        assert "Compressing 1 drawers" in out


# ---------------------------------------------------------------------------
# cmd_split
# ---------------------------------------------------------------------------


class TestCmdSplit:
    def test_split_builds_argv_and_calls_split_main(self, tmp_path, monkeypatch):
        """Verify cmd_split reconstructs sys.argv and delegates to split_mega_files.main."""
        captured_argv = {}

        def fake_split_main():
            captured_argv["argv"] = list(sys.argv)

        monkeypatch.setattr("mempalace.split_mega_files.main", fake_split_main)

        split_dir = str(tmp_path / "transcripts")
        args = argparse.Namespace(
            dir=split_dir,
            output_dir=None,
            dry_run=True,
            min_sessions=2,
        )
        cmd_split(args)
        assert captured_argv["argv"][0] == "mempalace split"
        assert split_dir in captured_argv["argv"]
        assert "--dry-run" in captured_argv["argv"]

    def test_split_with_output_dir(self, tmp_path, monkeypatch):
        captured_argv = {}

        def fake_split_main():
            captured_argv["argv"] = list(sys.argv)

        monkeypatch.setattr("mempalace.split_mega_files.main", fake_split_main)

        split_dir = str(tmp_path / "transcripts")
        output_dir = str(tmp_path / "output")
        args = argparse.Namespace(
            dir=split_dir,
            output_dir=output_dir,
            dry_run=False,
            min_sessions=5,
        )
        cmd_split(args)
        assert "--output-dir" in captured_argv["argv"]
        assert output_dir in captured_argv["argv"]
        assert "--min-sessions" in captured_argv["argv"]
        assert "5" in captured_argv["argv"]
        assert "--dry-run" not in captured_argv["argv"]

    def test_split_restores_sys_argv(self, tmp_path, monkeypatch):
        """Verify sys.argv is restored after cmd_split, even if split_main raises."""
        original_argv = list(sys.argv)

        err_msg = "boom"

        def failing_split_main():
            raise RuntimeError(err_msg)

        monkeypatch.setattr("mempalace.split_mega_files.main", failing_split_main)

        args = argparse.Namespace(
            dir=str(tmp_path / "x"),
            output_dir=None,
            dry_run=False,
            min_sessions=2,
        )
        with pytest.raises(RuntimeError, match=err_msg):
            cmd_split(args)
        assert sys.argv == original_argv


# ---------------------------------------------------------------------------
# cmd_init
# ---------------------------------------------------------------------------


class TestCmdInit:
    def test_init_creates_config(self, tmp_path, capsys, monkeypatch):
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        (project_dir / "main.py").write_text("print('hello')\n", encoding="utf-8")

        monkeypatch.setattr("mempalace.cli.MempalaceConfig", _fake_config(str(tmp_path / "palace")))

        args = argparse.Namespace(dir=str(project_dir), yes=True)

        # cmd_init imports entity_detector and room_detector_local
        # Mock those to avoid heavy processing
        monkeypatch.setattr(
            "mempalace.entity_detector.scan_for_detection",
            lambda _d: [],
        )
        monkeypatch.setattr(
            "mempalace.room_detector_local.detect_rooms_local",
            lambda **_kw: None,
        )

        from mempalace.cli import cmd_init

        cmd_init(args)
        out = capsys.readouterr().out
        assert "Scanning" in out


# ---------------------------------------------------------------------------
# main() argparse routing
# ---------------------------------------------------------------------------


class TestMain:
    def test_no_command_shows_help(self, capsys, monkeypatch):
        monkeypatch.setattr(sys, "argv", ["mempalace"])
        main()
        out = capsys.readouterr().out
        assert "MemPalace" in out

    def test_status_command_dispatches(self, tmp_path, monkeypatch):
        palace_path = _make_palace(tmp_path, _default_drawers(1))
        monkeypatch.setattr(sys, "argv", ["mempalace", "--palace", palace_path, "status"])
        dispatched = {}

        def fake_status(args):
            dispatched["called"] = True
            dispatched["palace"] = args.palace

        monkeypatch.setattr("mempalace.cli.cmd_status", fake_status)
        main()
        assert dispatched["called"] is True
        assert dispatched["palace"] == palace_path

    def test_search_command_dispatches(self, monkeypatch):
        monkeypatch.setattr(sys, "argv", ["mempalace", "search", "hello world", "--results", "3"])
        dispatched = {}

        def fake_search(args):
            dispatched["query"] = args.query
            dispatched["results"] = args.results

        monkeypatch.setattr("mempalace.cli.cmd_search", fake_search)
        main()
        assert dispatched["query"] == "hello world"
        assert dispatched["results"] == 3

    def test_mine_command_dispatches(self, tmp_path, monkeypatch):
        proj_dir = str(tmp_path / "proj")
        monkeypatch.setattr(
            sys,
            "argv",
            ["mempalace", "mine", proj_dir, "--mode", "convos", "--dry-run"],
        )
        dispatched = {}

        def fake_mine(args):
            dispatched["dir"] = args.dir
            dispatched["mode"] = args.mode
            dispatched["dry_run"] = args.dry_run

        monkeypatch.setattr("mempalace.cli.cmd_mine", fake_mine)
        main()
        assert dispatched["dir"] == proj_dir
        assert dispatched["mode"] == "convos"
        assert dispatched["dry_run"] is True

    def test_compress_command_dispatches(self, monkeypatch):
        monkeypatch.setattr(
            sys,
            "argv",
            ["mempalace", "compress", "--wing", "myapp", "--dry-run"],
        )
        dispatched = {}

        def fake_compress(args):
            dispatched["wing"] = args.wing
            dispatched["dry_run"] = args.dry_run

        monkeypatch.setattr("mempalace.cli.cmd_compress", fake_compress)
        main()
        assert dispatched["wing"] == "myapp"
        assert dispatched["dry_run"] is True

    def test_wakeup_command_dispatches(self, monkeypatch):
        monkeypatch.setattr(
            sys,
            "argv",
            ["mempalace", "wake-up", "--wing", "myapp"],
        )
        dispatched = {}

        def fake_wakeup(args):
            dispatched["wing"] = args.wing

        monkeypatch.setattr("mempalace.cli.cmd_wakeup", fake_wakeup)
        main()
        assert dispatched["wing"] == "myapp"

    def test_split_command_dispatches(self, tmp_path, monkeypatch):
        chats_dir = str(tmp_path / "chats")
        monkeypatch.setattr(
            sys,
            "argv",
            ["mempalace", "split", chats_dir, "--dry-run", "--min-sessions", "3"],
        )
        dispatched = {}

        def fake_split(args):
            dispatched["dir"] = args.dir
            dispatched["dry_run"] = args.dry_run
            dispatched["min_sessions"] = args.min_sessions

        monkeypatch.setattr("mempalace.cli.cmd_split", fake_split)
        main()
        assert dispatched["dir"] == chats_dir
        assert dispatched["dry_run"] is True
        assert dispatched["min_sessions"] == 3

    def test_init_command_dispatches(self, tmp_path, monkeypatch):
        proj_dir = str(tmp_path / "proj")
        monkeypatch.setattr(
            sys,
            "argv",
            ["mempalace", "init", proj_dir, "--yes"],
        )
        dispatched = {}

        def fake_init(args):
            dispatched["dir"] = args.dir
            dispatched["yes"] = args.yes

        monkeypatch.setattr("mempalace.cli.cmd_init", fake_init)
        main()
        assert dispatched["dir"] == proj_dir
        assert dispatched["yes"] is True

    def test_mine_default_values(self, tmp_path, monkeypatch):
        proj_dir = str(tmp_path / "proj")
        monkeypatch.setattr(sys, "argv", ["mempalace", "mine", proj_dir])
        dispatched = {}

        def fake_mine(args):
            dispatched["mode"] = args.mode
            dispatched["wing"] = args.wing
            dispatched["agent"] = args.agent
            dispatched["limit"] = args.limit
            dispatched["dry_run"] = args.dry_run

        monkeypatch.setattr("mempalace.cli.cmd_mine", fake_mine)
        main()
        assert dispatched["mode"] == "projects"
        assert dispatched["wing"] is None
        assert dispatched["agent"] == "mempalace"
        assert dispatched["limit"] == 0
        assert dispatched["dry_run"] is False


class TestCmdHookLogs:
    def test_no_log_file(self, tmp_path, capsys, monkeypatch):
        monkeypatch.setattr("mempalace.hooks_cli.STATE_DIR", tmp_path)
        args = argparse.Namespace(lines=50, follow=False)
        cmd_hook_logs(args)
        assert "No hook log found" in capsys.readouterr().out

    def test_shows_last_n_lines(self, tmp_path, capsys, monkeypatch):
        monkeypatch.setattr("mempalace.hooks_cli.STATE_DIR", tmp_path)
        log = tmp_path / "hook.log"
        log.write_text("\n".join(f"line {i}" for i in range(20)), encoding="utf-8")
        args = argparse.Namespace(lines=5, follow=False)
        cmd_hook_logs(args)
        out = capsys.readouterr().out
        assert "line 15" in out
        assert "line 19" in out
        assert "line 14" not in out

    def test_defaults_to_50_lines(self, tmp_path, capsys, monkeypatch):
        monkeypatch.setattr("mempalace.hooks_cli.STATE_DIR", tmp_path)
        log = tmp_path / "hook.log"
        log.write_text("\n".join(f"line {i}" for i in range(100)), encoding="utf-8")
        args = argparse.Namespace(lines=50, follow=False)
        cmd_hook_logs(args)
        out = capsys.readouterr().out
        assert "line 50" in out
        assert "line 49" not in out
