"""Tests for interactive flows — onboarding and room detection with monkeypatched input."""

import pytest

from mempalace.onboarding import (
    _ask,
    _ask_mode,
    _ask_people,
    _ask_projects,
    _ask_wings,
    _hr,
    _yn,
    run_onboarding,
)
from mempalace.room_detector_local import (
    detect_rooms_local,
    get_user_approval,
    print_proposed_structure,
)


class TestOnboardingHelpers:
    def test_hr(self, capsys):
        _hr()
        captured = capsys.readouterr()
        assert "─" in captured.out

    def test_ask_with_default(self, monkeypatch):
        monkeypatch.setattr("builtins.input", lambda _: "")
        assert _ask("test", default="hello") == "hello"

    def test_ask_with_input(self, monkeypatch):
        monkeypatch.setattr("builtins.input", lambda _: "custom")
        assert _ask("test", default="hello") == "custom"

    def test_ask_no_default(self, monkeypatch):
        monkeypatch.setattr("builtins.input", lambda _: "value")
        assert _ask("test") == "value"

    def test_yn_default_yes(self, monkeypatch):
        monkeypatch.setattr("builtins.input", lambda _: "")
        assert _yn("continue?") is True

    def test_yn_explicit_no(self, monkeypatch):
        monkeypatch.setattr("builtins.input", lambda _: "n")
        assert _yn("continue?") is False

    def test_yn_default_no(self, monkeypatch):
        monkeypatch.setattr("builtins.input", lambda _: "")
        assert _yn("continue?", default="n") is False

    def test_yn_explicit_yes(self, monkeypatch):
        monkeypatch.setattr("builtins.input", lambda _: "yes")
        assert _yn("continue?", default="n") is True


class TestAskMode:
    @pytest.mark.parametrize(
        ("input_val", "expected"),
        [("1", "work"), ("2", "personal"), ("3", "combo")],
    )
    def test_valid_choice(self, monkeypatch, input_val, expected):
        monkeypatch.setattr("builtins.input", lambda _: input_val)
        assert _ask_mode() == expected

    def test_invalid_then_valid(self, monkeypatch):
        responses = iter(["x", "invalid", "2"])
        monkeypatch.setattr("builtins.input", lambda _: next(responses))
        assert _ask_mode() == "personal"


class TestAskPeople:
    def test_personal_mode(self, monkeypatch):
        # Each person triggers a nickname prompt, so: name, nickname, name, nickname, done
        responses = iter(["Riley, daughter", "", "Max, son", "", "done"])
        monkeypatch.setattr("builtins.input", lambda _: next(responses))
        people, _aliases = _ask_people("personal")
        assert len(people) == 2
        assert people[0]["name"] == "Riley"
        assert people[0]["relationship"] == "daughter"

    def test_work_mode(self, monkeypatch):
        responses = iter(["Alice, colleague", "done"])
        monkeypatch.setattr("builtins.input", lambda _: next(responses))
        people, _aliases = _ask_people("work")
        assert len(people) == 1
        assert people[0]["context"] == "work"

    def test_combo_mode(self, monkeypatch):
        # Personal people, then work people
        responses = iter([
            "Riley, daughter",
            "",  # nickname prompt → skip
            "done",  # end personal
            "Alice, colleague",
            "done",  # end work
        ])
        monkeypatch.setattr("builtins.input", lambda _: next(responses))
        people, _aliases = _ask_people("combo")
        assert len(people) == 2

    def test_with_nickname(self, monkeypatch):
        responses = iter(["Maxwell, son", "Max", "done"])
        monkeypatch.setattr("builtins.input", lambda _: next(responses))
        _people, aliases = _ask_people("personal")
        assert aliases.get("Max") == "Maxwell"


class TestAskProjects:
    def test_returns_empty_for_personal(self, monkeypatch):
        projects = _ask_projects("personal")
        assert projects == []

    def test_work_mode(self, monkeypatch):
        responses = iter(["MemPalace", "Acme", "done"])
        monkeypatch.setattr("builtins.input", lambda _: next(responses))
        projects = _ask_projects("work")
        assert "MemPalace" in projects
        assert "Acme" in projects


class TestAskWings:
    def test_default_wings(self, monkeypatch):
        monkeypatch.setattr("builtins.input", lambda _: "")
        wings = _ask_wings("personal")
        assert len(wings) > 0

    def test_custom_wings(self, monkeypatch):
        monkeypatch.setattr("builtins.input", lambda _: "code, life, health")
        wings = _ask_wings("work")
        assert wings == ["code", "life", "health"]


class TestRunOnboarding:
    def test_full_flow(self, tmp_path, monkeypatch):
        responses = iter([
            "2",  # mode: personal
            "Riley, daughter",  # person
            "",  # no nickname
            "done",  # end people
            "",  # default wings
            "n",  # don't scan files
        ])
        monkeypatch.setattr("builtins.input", lambda _: next(responses))
        reg = run_onboarding(directory=str(tmp_path), config_dir=tmp_path, auto_detect=False)
        assert "Riley" in reg.people
        assert reg.mode == "personal"


class TestRoomDetectorInteractive:
    def test_print_proposed_structure(self, capsys):
        rooms = [
            {"name": "backend", "description": "Backend code"},
            {"name": "general", "description": "Everything else"},
        ]
        print_proposed_structure("myproject", rooms, 10, "folder structure")
        captured = capsys.readouterr()
        assert "myproject" in captured.out
        assert "backend" in captured.out

    def test_get_user_approval_accept(self, monkeypatch):
        rooms = [{"name": "backend", "description": "test"}]
        monkeypatch.setattr("builtins.input", lambda _: "")
        result = get_user_approval(rooms)
        assert result == rooms

    def test_get_user_approval_edit(self, monkeypatch):
        rooms = [
            {"name": "backend", "description": "test"},
            {"name": "frontend", "description": "test"},
            {"name": "general", "description": "test"},
        ]
        responses = iter(["edit", "2", "n"])  # edit, remove #2, don't add
        monkeypatch.setattr("builtins.input", lambda _: next(responses))
        result = get_user_approval(rooms)
        names = {r["name"] for r in result}
        assert "frontend" not in names
        assert "backend" in names

    def test_detect_rooms_local(self, tmp_path, monkeypatch, capsys):
        # Create project structure
        proj = tmp_path / "myproject"
        proj.mkdir()
        (proj / "backend").mkdir()
        (proj / "app.py").write_text("print('hello')\n" * 5, encoding="utf-8")
        (proj / "backend" / "server.py").write_text("import flask\n" * 5, encoding="utf-8")

        # Accept defaults
        monkeypatch.setattr("builtins.input", lambda _: "")
        detect_rooms_local(str(proj))

        # Should have created mempalace.yaml
        config_path = proj / "mempalace.yaml"
        assert config_path.exists()
