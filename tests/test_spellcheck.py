"""Tests for spellcheck.py — spell-correction with preservation rules."""

from pathlib import Path

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


class TestShouldSkip:
    def test_short_tokens(self):
        assert _should_skip("hi", set()) is True
        assert _should_skip("ok", set()) is True

    def test_tokens_with_digits(self):
        assert _should_skip("v2.0", set()) is True
        assert _should_skip("3am", set()) is True

    def test_camel_case(self):
        assert _should_skip("ChromaDB", set()) is True
        assert _should_skip("MemPalace", set()) is True

    def test_all_caps(self):
        assert _should_skip("NDCG", set()) is True
        assert _should_skip("API", set()) is True

    def test_technical_tokens(self):
        assert _should_skip("bge-large", set()) is True
        assert _should_skip("train_test", set()) is True

    def test_url_like(self):
        assert _should_skip("https://example.com", set()) is True

    def test_known_names(self):
        assert _should_skip("riley", {"riley", "sam"}) is True

    def test_normal_word_not_skipped(self):
        assert _should_skip("hello", set()) is False
        assert _should_skip("world", set()) is False


class TestEditDistance:
    def test_identical(self):
        assert _edit_distance("hello", "hello") == 0

    def test_one_edit(self):
        assert _edit_distance("hello", "helo") == 1

    def test_two_edits(self):
        assert _edit_distance("hello", "hllo") == 1

    def test_empty_strings(self):
        assert _edit_distance("", "") == 0
        assert _edit_distance("abc", "") == 3
        assert _edit_distance("", "abc") == 3

    def test_completely_different(self):
        assert _edit_distance("abc", "xyz") == 3


class TestGetSpeller:
    def test_returns_none_when_autocorrect_unavailable(self):
        """autocorrect is not installed, so _get_speller should return None."""
        import mempalace.spellcheck as sc

        old_speller = sc._speller
        old_available = sc._autocorrect_available
        try:
            sc._speller = None
            sc._autocorrect_available = None
            result = _get_speller()
            assert result is None
            assert sc._autocorrect_available is False
        finally:
            sc._speller = old_speller
            sc._autocorrect_available = old_available


class TestGetSystemWords:
    def test_returns_set(self):
        """_get_system_words should return a set (possibly empty)."""
        import mempalace.spellcheck as sc

        old = sc._system_words
        try:
            sc._system_words = None
            words = _get_system_words()
            assert isinstance(words, set)
        finally:
            sc._system_words = old

    def test_caches_result(self):
        """Second call returns same object (cached)."""
        import mempalace.spellcheck as sc

        old = sc._system_words
        try:
            sc._system_words = None
            first = _get_system_words()
            second = _get_system_words()
            assert first is second
        finally:
            sc._system_words = old

    def test_returns_empty_set_when_dict_missing(self):
        """When system dict does not exist, returns empty set."""
        import mempalace.spellcheck as sc

        old_words = sc._system_words
        old_dict = sc._SYSTEM_DICT
        try:
            sc._system_words = None
            sc._SYSTEM_DICT = Path("/nonexistent/path/to/dict/words")
            words = _get_system_words()
            assert words == set()
        finally:
            sc._system_words = old_words
            sc._SYSTEM_DICT = old_dict

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
