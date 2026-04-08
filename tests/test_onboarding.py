"""Tests for onboarding.py — first-run setup and AAAK bootstrap."""

from mempalace.entity_registry import EntityRegistry
from mempalace.onboarding import (
    DEFAULT_WINGS,
    _auto_detect,
    _generate_aaak_bootstrap,
    _warn_ambiguous,
    quick_setup,
)


class TestQuickSetup:
    def test_creates_registry(self, tmp_path):
        reg = quick_setup(
            mode="personal",
            people=[
                {"name": "Riley", "relationship": "daughter", "context": "personal"},
            ],
            projects=["MemPalace"],
            config_dir=tmp_path,
        )
        assert isinstance(reg, EntityRegistry)
        assert "Riley" in reg.people
        assert "MemPalace" in reg.projects

    def test_work_mode(self, tmp_path):
        reg = quick_setup(
            mode="work",
            people=[
                {"name": "Alice", "relationship": "colleague", "context": "work"},
            ],
            projects=["Acme"],
            config_dir=tmp_path,
        )
        assert reg.mode == "work"

    def test_with_aliases(self, tmp_path):
        reg = quick_setup(
            mode="personal",
            people=[{"name": "Maxwell", "relationship": "son", "context": "personal"}],
            aliases={"Max": "Maxwell"},
            config_dir=tmp_path,
        )
        assert "Max" in reg.people


class TestGenerateAaakBootstrap:
    def test_creates_entity_file(self, tmp_path):
        _generate_aaak_bootstrap(
            people=[
                {"name": "Riley", "relationship": "daughter", "context": "personal"},
            ],
            projects=["MemPalace"],
            wings=["family", "projects"],
            mode="personal",
            config_dir=tmp_path,
        )
        entity_file = tmp_path / "aaak_entities.md"
        assert entity_file.exists()
        content = entity_file.read_text(encoding="utf-8")
        assert "RIL=Riley" in content
        assert "MEMP=MemPalace" in content

    def test_creates_facts_file(self, tmp_path):
        _generate_aaak_bootstrap(
            people=[
                {"name": "Alice", "relationship": "partner", "context": "personal"},
                {"name": "Bob", "relationship": "manager", "context": "work"},
            ],
            projects=["Acme"],
            wings=["family", "work"],
            mode="combo",
            config_dir=tmp_path,
        )
        facts_file = tmp_path / "critical_facts.md"
        assert facts_file.exists()
        content = facts_file.read_text(encoding="utf-8")
        assert "Alice" in content
        assert "Bob" in content
        assert "Acme" in content
        assert "combo" in content.lower()

    def test_handles_entity_code_collision(self, tmp_path):
        _generate_aaak_bootstrap(
            people=[
                {"name": "Alice", "relationship": "", "context": "personal"},
                {"name": "Alix", "relationship": "", "context": "personal"},
            ],
            projects=[],
            wings=["family"],
            mode="personal",
            config_dir=tmp_path,
        )
        content = (tmp_path / "aaak_entities.md").read_text(encoding="utf-8")
        # Both should be present with different codes
        assert "Alice" in content
        assert "Alix" in content


class TestWarnAmbiguous:
    def test_detects_ambiguous(self):
        people = [
            {"name": "Grace", "relationship": "friend"},
            {"name": "Riley", "relationship": "daughter"},
        ]
        ambiguous = _warn_ambiguous(people)
        assert "Grace" in ambiguous

    def test_no_ambiguous(self):
        people = [
            {"name": "Xyzzy", "relationship": "friend"},
        ]
        ambiguous = _warn_ambiguous(people)
        assert ambiguous == []


class TestAutoDetect:
    def test_returns_empty_for_no_files(self, tmp_path):
        result = _auto_detect(str(tmp_path), [])
        assert result == []

    def test_returns_empty_on_error(self):
        result = _auto_detect("/nonexistent/path", [])
        assert result == []


class TestDefaultWings:
    def test_all_modes_have_wings(self):
        for mode in ["work", "personal", "combo"]:
            assert len(DEFAULT_WINGS[mode]) > 0
