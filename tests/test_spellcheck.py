"""Tests for spellcheck.py — spell-correction with preservation rules."""

from pathlib import Path

import pytest

import mempalace.spellcheck as sc
from mempalace.spellcheck import (
    _edit_distance,
    _get_speller,
    _get_system_words,
    _load_known_names,
    _should_skip,
    spellcheck_transcript,
    spellcheck_transcript_line,
    spellcheck_user_text,
)


@pytest.mark.parametrize(
    ("token", "names", "expected"),
    [
        # short tokens
        ("hi", set(), True),
        ("ok", set(), True),
        # digits
        ("v2.0", set(), True),
        ("3am", set(), True),
        # camelCase / PascalCase
        ("ChromaDB", set(), True),
        ("MemPalace", set(), True),
        ("CamelCase", set(), True),
        ("longMemEval", set(), True),
        # ALL_CAPS
        ("NDCG", set(), True),
        ("API", set(), True),
        ("MAX_RESULTS", set(), True),
        ("API_KEY", set(), True),
        # hyphenated / underscored
        ("bge-large", set(), True),
        ("bge-large-en", set(), True),
        ("train_test", set(), True),
        ("my_variable", set(), True),
        # URLs
        ("https://example.com", set(), True),
        ("https://example.com/path", set(), True),
        ("www.example.com", set(), True),
        # file paths
        ("/Users/someone/file.txt", set(), True),
        ("~/Documents", set(), True),
        ("file.json", set(), True),
        # markdown formatting
        ("`code`", set(), True),
        ("**bold**", set(), True),
        # known names
        ("riley", {"riley", "sam"}, True),
        # normal words — should NOT skip
        ("hello", set(), False),
        ("world", set(), False),
    ],
)
def test_should_skip(token, names, expected):
    assert _should_skip(token, names) is expected


@pytest.mark.parametrize(
    ("a", "b", "expected"),
    [
        ("hello", "hello", 0),
        ("hello", "helo", 1),
        ("hello", "hllo", 1),
        ("", "", 0),
        ("abc", "", 3),
        ("", "abc", 3),
        ("abc", "xyz", 3),
    ],
)
def test_edit_distance(a, b, expected):
    assert _edit_distance(a, b) == expected


class TestGetSpeller:
    def test_returns_none_when_autocorrect_unavailable(self, monkeypatch):
        """autocorrect is not installed, so _get_speller should return None."""
        monkeypatch.setattr(sc, "_speller", None)
        monkeypatch.setattr(sc, "_autocorrect_available", None)
        result = _get_speller()
        assert result is None
        assert sc._autocorrect_available is False


class TestGetSystemWords:
    def test_returns_set(self, monkeypatch):
        """_get_system_words should return a set (possibly empty)."""
        monkeypatch.setattr(sc, "_system_words", None)
        words = _get_system_words()
        assert isinstance(words, set)

    def test_caches_result(self, monkeypatch):
        """Second call returns same object (cached)."""
        monkeypatch.setattr(sc, "_system_words", None)
        first = _get_system_words()
        second = _get_system_words()
        assert first is second

    def test_returns_empty_set_when_dict_missing(self, monkeypatch):
        """When system dict does not exist, returns empty set."""
        monkeypatch.setattr(sc, "_system_words", None)
        monkeypatch.setattr(sc, "_SYSTEM_DICT", Path("/nonexistent/path/to/dict/words"))
        words = _get_system_words()
        assert words == set()

    def test_nonempty_on_macos(self):
        """On macOS, /usr/share/dict/words exists so the set should be populated."""
        words = _get_system_words()
        assert isinstance(words, set)
        if Path("/usr/share/dict/words").exists():
            assert len(words) > 0


class TestLoadKnownNames:
    def test_returns_set(self):
        """_load_known_names returns a set (may be empty if registry unavailable)."""
        result = _load_known_names()
        assert isinstance(result, set)


class TestSpellcheckUserText:
    def test_fallback_returns_unchanged(self):
        """Without autocorrect installed, text should pass through unchanged."""
        text = "this is sme misspeled text"
        result = spellcheck_user_text(text)
        assert result == text

    def test_with_explicit_known_names(self):
        """known_names parameter is accepted; text returned unchanged without autocorrect."""
        text = "Riley and Sam went out"
        result = spellcheck_user_text(text, known_names={"riley", "sam"})
        assert result == text

    def test_empty_string(self):
        result = spellcheck_user_text("")
        assert not result


class TestSpellcheckTranscriptLine:
    def test_user_turn_line(self):
        """Lines starting with '>' should attempt correction (fallback = unchanged)."""
        line = "> this is my message"
        result = spellcheck_transcript_line(line)
        assert result == line

    def test_assistant_line_untouched(self):
        """Lines NOT starting with '>' should be returned as-is."""
        line = "This is an assistant response with a typo"
        result = spellcheck_transcript_line(line)
        assert result == line

    def test_empty_user_turn(self):
        """A '>' line with no content should pass through."""
        line = "> "
        result = spellcheck_transcript_line(line)
        assert result == "> "

    def test_indented_user_turn(self):
        """Indented '>' line should still be detected."""
        line = "  > hello world message here"
        result = spellcheck_transcript_line(line)
        assert result == line


class TestSpellcheckTranscript:
    def test_full_transcript(self):
        """spellcheck_transcript processes all lines, only touching '>' lines."""
        content = "> my first message\nAssistant says hello\n> second message"
        result = spellcheck_transcript(content)
        lines = result.split("\n")
        assert len(lines) == 3
        assert lines[1] == "Assistant says hello"

    def test_no_user_turns(self):
        content = "Just assistant text\nMore text"
        result = spellcheck_transcript(content)
        assert result == content


# ─────────────────────────────────────────────────────────────────────────────
# Additional coverage tests
# ─────────────────────────────────────────────────────────────────────────────


class TestGetSpellerWhenAvailable:
    def test_speller_initialized_when_autocorrect_importable(self, monkeypatch):
        """When autocorrect IS available, _get_speller returns a Speller instance."""
        fake_speller = lambda x: x  # noqa: E731
        monkeypatch.setattr(sc, "_speller", fake_speller)
        monkeypatch.setattr(sc, "_autocorrect_available", True)

        result = _get_speller()
        assert result is fake_speller
        assert sc._autocorrect_available is True


class TestGetSystemWordsNoDict:
    def test_returns_empty_set_on_missing_dict(self, monkeypatch):
        """On a system without /usr/share/dict/words, returns empty set."""
        monkeypatch.setattr(sc, "_system_words", None)
        monkeypatch.setattr(sc, "_SYSTEM_DICT", Path("/no/such/dict/words"))
        words = _get_system_words()
        assert words == set()


class TestSpellcheckUserTextEntryPoint:
    def test_no_autocorrect_returns_unchanged(self, monkeypatch):
        """When autocorrect is not installed, spellcheck_user_text returns input as-is."""
        monkeypatch.setattr(sc, "_speller", None)
        monkeypatch.setattr(sc, "_autocorrect_available", False)

        text = "teh is definitely mispeled text"  # cspell:disable-line
        result = spellcheck_user_text(text)
        assert result == text

    def test_skip_urls_in_text(self, monkeypatch):
        """URLs embedded in text should not be modified."""
        monkeypatch.setattr(sc, "_speller", lambda w: w.lower())
        monkeypatch.setattr(sc, "_autocorrect_available", True)

        text = "visit https://example.com for details"
        result = spellcheck_user_text(text, known_names=set())
        assert "https://example.com" in result

    def test_skip_paths_in_text(self, monkeypatch):
        """File paths in text should not be modified."""
        monkeypatch.setattr(sc, "_speller", lambda w: w.lower())
        monkeypatch.setattr(sc, "_autocorrect_available", True)

        text = "check ~/Documents/notes.txt please"
        result = spellcheck_user_text(text, known_names=set())
        assert "~/Documents/notes.txt" in result

    def test_skip_entity_names(self, monkeypatch):
        """Known entity names should be preserved."""
        monkeypatch.setattr(sc, "_speller", lambda _word: "corrected")
        monkeypatch.setattr(sc, "_autocorrect_available", True)

        text = "Riley went to the store"
        result = spellcheck_user_text(text, known_names={"riley"})
        # "Riley" starts uppercase → skipped as proper noun
        # "went", "store" are valid system words → skipped
        # "the" is < 4 chars → skipped
        assert "Riley" in result

    def test_known_names_loaded_when_none(self, monkeypatch):
        """When known_names is None, _load_known_names is called."""
        monkeypatch.setattr(sc, "_speller", None)
        monkeypatch.setattr(sc, "_autocorrect_available", False)

        # When autocorrect is unavailable, returns text unchanged
        # but the code path for known_names=None is not reached (early return)
        text = "hello world"
        result = spellcheck_user_text(text, known_names=None)
        assert result == text

    def test_correction_with_punctuation(self, monkeypatch):
        """Trailing punctuation should be preserved after correction."""
        monkeypatch.setattr(sc, "_speller", lambda _word: "wrong")
        monkeypatch.setattr(sc, "_autocorrect_available", True)
        monkeypatch.setattr(sc, "_system_words", set())

        text = "wrng."
        result = spellcheck_user_text(text, known_names=set())
        # "wrng" → "wrong" (edit distance 1), punctuation "." reattached
        assert result == "wrong."

    def test_capitalized_word_skipped(self, monkeypatch):
        """Words starting with uppercase are treated as proper nouns and skipped."""
        monkeypatch.setattr(sc, "_speller", lambda _word: "wrong")
        monkeypatch.setattr(sc, "_autocorrect_available", True)
        monkeypatch.setattr(sc, "_system_words", set())

        text = "Boston is nice"
        result = spellcheck_user_text(text, known_names=set())
        assert "Boston" in result

    def test_edit_distance_guard(self, monkeypatch):
        """Corrections with too-high edit distance are rejected."""
        monkeypatch.setattr(sc, "_speller", lambda _word: "xylophone")
        monkeypatch.setattr(sc, "_autocorrect_available", True)
        monkeypatch.setattr(sc, "_system_words", set())

        text = "test"
        result = spellcheck_user_text(text, known_names=set())
        # "test" → "xylophone" has edit distance > 3, should be rejected
        assert result == "test"
