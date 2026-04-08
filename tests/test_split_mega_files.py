"""Tests for split_mega_files.py — session splitting logic."""

import json

from mempalace.split_mega_files import (
    _load_known_people,
    _load_username_map,
    extract_subject,
    extract_timestamp,
    find_session_boundaries,
    is_true_session_start,
)


class TestIsTrueSessionStart:
    def test_true_start(self):
        lines = [
            "Claude Code v1.0.0",
            "Some content here",
            "More content",
            "",
            "",
            "",
        ]
        assert is_true_session_start(lines, 0) is True

    def test_context_restore(self):
        lines = [
            "Claude Code v1.0.0",
            "Ctrl+E to show 5 previous messages",
            "More content",
            "",
            "",
            "",
        ]
        assert is_true_session_start(lines, 0) is False


class TestFindSessionBoundaries:
    def test_multiple_sessions(self):
        lines = [
            "Claude Code v1.0.0",
            "First session content",
            "",
            "Claude Code v1.0.0",
            "Second session content",
        ]
        boundaries = find_session_boundaries(lines)
        assert len(boundaries) == 2
        assert boundaries[0] == 0
        assert boundaries[1] == 3

    def test_no_sessions(self):
        lines = ["Just some text", "No sessions here"]
        boundaries = find_session_boundaries(lines)
        assert len(boundaries) == 0

    def test_skips_context_restores(self):
        # is_true_session_start looks at 6 lines from the header line.
        # The first header also sees "Ctrl+E" in its 6-line window,
        # so both are rejected. Need enough separation.
        lines = [
            "Claude Code v1.0.0",
            "First session content",
            "More content here",
            "Even more content",
            "Still going",
            "And more",
            "Plenty of separation now",
            "Claude Code v1.0.0",
            "Ctrl+E to show 5 previous messages",
            "This is a context restore, not a new session",
        ]
        boundaries = find_session_boundaries(lines)
        assert len(boundaries) == 1
        assert boundaries[0] == 0


class TestExtractSubject:
    def test_finds_first_prompt(self):
        lines = [
            "Claude Code v1.0.0",
            "> Can you help me fix the login bug?",
            "Sure, let me look at the code.",
        ]
        subject = extract_subject(lines)
        assert "login" in subject.lower() or "bug" in subject.lower()

    def test_skips_commands(self):
        lines = [
            "> cd /project",
            "> git status",
            "> Can you review this code?",
        ]
        subject = extract_subject(lines)
        assert "review" in subject.lower() or "code" in subject.lower()

    def test_no_prompts(self):
        lines = ["Just some content", "No user prompts"]
        subject = extract_subject(lines)
        assert subject == "session"

    def test_truncates_long_subjects(self):
        lines = ["> " + "word " * 30]
        subject = extract_subject(lines)
        assert len(subject) <= 60


class TestExtractTimestamp:
    def test_finds_timestamp(self):
        lines = [
            "Claude Code v1.0.0",
            "⏺ 3:45 PM Wednesday, March 26, 2026",
            "Some content",
        ]
        human, iso = extract_timestamp(lines)
        assert human is not None
        assert iso == "2026-03-26"

    def test_no_timestamp(self):
        lines = ["No timestamp here", "Just content"]
        human, iso = extract_timestamp(lines)
        assert human is None
        assert iso is None


class TestLoadKnownPeople:
    def test_returns_list(self):
        """_load_known_people returns a list (from file or fallback)."""
        result = _load_known_people()
        assert isinstance(result, list)
        assert len(result) > 0

    def test_loads_from_json_list(self, tmp_path):
        """When config is a plain JSON list, it returns that list."""
        names_file = tmp_path / "known_names.json"
        names_file.write_text(json.dumps(["TestPerson1", "TestPerson2"]))
        import mempalace.split_mega_files as smf

        old_path = smf._KNOWN_NAMES_PATH
        old_cache = smf._KNOWN_NAMES_CACHE
        try:
            smf._KNOWN_NAMES_PATH = names_file
            smf._KNOWN_NAMES_CACHE = None
            result = _load_known_people()
            assert result == ["TestPerson1", "TestPerson2"]
        finally:
            smf._KNOWN_NAMES_PATH = old_path
            smf._KNOWN_NAMES_CACHE = old_cache

    def test_loads_from_json_dict(self, tmp_path):
        """When config is a dict with 'names' key, extracts names."""
        names_file = tmp_path / "known_names.json"
        names_file.write_text(json.dumps({"names": ["Alpha", "Beta"]}))
        import mempalace.split_mega_files as smf

        old_path = smf._KNOWN_NAMES_PATH
        old_cache = smf._KNOWN_NAMES_CACHE
        try:
            smf._KNOWN_NAMES_PATH = names_file
            smf._KNOWN_NAMES_CACHE = None
            result = _load_known_people()
            assert result == ["Alpha", "Beta"]
        finally:
            smf._KNOWN_NAMES_PATH = old_path
            smf._KNOWN_NAMES_CACHE = old_cache


class TestLoadUsernameMap:
    def test_returns_dict(self):
        result = _load_username_map()
        assert isinstance(result, dict)

    def test_loads_username_map_from_config(self, tmp_path):
        names_file = tmp_path / "known_names.json"
        names_file.write_text(
            json.dumps({
                "names": ["Alice"],
                "username_map": {"jdoe": "John"},
            })
        )
        import mempalace.split_mega_files as smf

        old_path = smf._KNOWN_NAMES_PATH
        old_cache = smf._KNOWN_NAMES_CACHE
        try:
            smf._KNOWN_NAMES_PATH = names_file
            smf._KNOWN_NAMES_CACHE = None
            result = _load_username_map()
            assert result == {"jdoe": "John"}
        finally:
            smf._KNOWN_NAMES_PATH = old_path
            smf._KNOWN_NAMES_CACHE = old_cache
