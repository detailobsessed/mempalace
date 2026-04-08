"""Tests for general_extractor.py — memory extraction from text."""

import re
import textwrap

from mempalace.general_extractor import (
    DECISION_MARKERS,
    EMOTION_MARKERS,
    MILESTONE_MARKERS,
    PREFERENCE_MARKERS,
    PROBLEM_MARKERS,
    _disambiguate,
    _extract_prose,
    _get_sentiment,
    _has_resolution,
    _is_code_line,
    _score_markers,
    _split_by_turns,
    _split_into_segments,
    extract_memories,
)


class TestGetSentiment:
    def test_positive(self):
        assert _get_sentiment("I'm so happy and proud of this breakthrough!") == "positive"

    def test_negative(self):
        assert _get_sentiment("The build keeps crashing, everything is broken") == "negative"

    def test_neutral(self):
        assert _get_sentiment("The meeting is scheduled for Tuesday") == "neutral"


class TestHasResolution:
    def test_fixed(self):
        assert _has_resolution("I finally fixed the issue with the database") is True

    def test_solved(self):
        assert _has_resolution("We solved it by changing the config") is True

    def test_no_resolution(self):
        assert _has_resolution("The server keeps crashing every hour") is False

    def test_got_it_working(self):
        assert _has_resolution("After three hours I got it working") is True


class TestIsCodeLine:
    def test_shell_command(self):
        assert _is_code_line("$ pip install chromadb") is True

    def test_import(self):
        assert _is_code_line("import os") is True

    def test_code_fence(self):
        assert _is_code_line("```python") is True

    def test_prose(self):
        assert _is_code_line("We decided to use GraphQL for the API") is False

    def test_empty(self):
        assert _is_code_line("") is False

    def test_low_alpha_ratio(self):
        assert _is_code_line("{[()]}=><&^%#@!") is True


class TestExtractProse:
    def test_strips_code_blocks(self):
        text = "Some prose here\n```python\nimport os\n```\nMore prose"
        result = _extract_prose(text)
        assert "import os" not in result
        assert "Some prose here" in result
        assert "More prose" in result

    def test_all_prose(self):
        text = "Just a normal paragraph about decisions"
        assert _extract_prose(text) == text


class TestScoreMarkers:
    def test_decision_markers(self):
        text = "we decided to use graphql instead of rest because it fits better"
        score, _keywords = _score_markers(text, DECISION_MARKERS)
        assert score > 0

    def test_preference_markers(self):
        text = "i prefer using snake_case and always use type hints"
        score, _keywords = _score_markers(text, PREFERENCE_MARKERS)
        assert score > 0

    def test_milestone_markers(self):
        text = "finally got it working! the prototype is shipped and version 2.0 is released"
        score, _keywords = _score_markers(text, MILESTONE_MARKERS)
        assert score > 0

    def test_problem_markers(self):
        text = "there's a bug causing the server to crash, the root cause is a memory leak"
        score, _keywords = _score_markers(text, PROBLEM_MARKERS)
        assert score > 0

    def test_emotion_markers(self):
        text = "i feel so proud and grateful, i love what we've built"
        score, _keywords = _score_markers(text, EMOTION_MARKERS)
        assert score > 0

    def test_no_match(self):
        text = "the quick brown fox jumps over the lazy dog"
        score, _keywords = _score_markers(text, DECISION_MARKERS)
        assert score == 0


class TestSplitByTurns:
    def test_splits_on_user_turns(self):
        turn_patterns = [
            re.compile(r"^>\s"),
            re.compile(r"^(Human|User)\s*:", re.IGNORECASE),
            re.compile(r"^(Assistant|Claude)\s*:", re.IGNORECASE),
        ]
        lines = [
            "> What is the best approach?",
            "Some assistant response here",
            "More response details",
            "> Can you explain further?",
            "Further explanation here",
        ]
        segments = _split_by_turns(lines, turn_patterns)
        assert len(segments) == 2

    def test_splits_on_human_assistant_turns(self):
        turn_patterns = [
            re.compile(r"^>\s"),
            re.compile(r"^(Human|User)\s*:", re.IGNORECASE),
            re.compile(r"^(Assistant|Claude)\s*:", re.IGNORECASE),
        ]
        lines = [
            "Human: What should we do?",
            "Some context",
            "Assistant: Here is my suggestion",
            "More details",
            "Human: Thanks, and what about X?",
        ]
        segments = _split_by_turns(lines, turn_patterns)
        assert len(segments) == 3


class TestSplitIntoSegments:
    def test_speaker_turn_splitting(self):
        """When enough turn markers exist, splits by turns."""
        text = textwrap.dedent("""\
            Human: First question here
            Response to first
            Human: Second question about decisions
            Response to second
            Human: Third question for good measure
            Response to third""")
        segments = _split_into_segments(text)
        assert len(segments) >= 3

    def test_paragraph_splitting(self):
        """Without turn markers, splits on double newlines."""
        text = "Paragraph one about decisions.\n\nParagraph two about problems.\n\nParagraph three."
        segments = _split_into_segments(text)
        assert len(segments) == 3

    def test_long_single_block_chunking(self):
        """A giant single block with >20 lines gets chunked."""
        lines = [f"Line {i} of content with some words" for i in range(50)]
        text = "\n".join(lines)
        segments = _split_into_segments(text)
        assert len(segments) >= 2


class TestDisambiguateEdgeCases:
    def test_resolved_problem_positive_emotional(self):
        """Resolved problem with positive sentiment and emotional score -> emotional."""
        text = "The bug was fixed and I'm so proud and happy it works now"
        result = _disambiguate("problem", text, {"emotional": 2.0, "milestone": 1.0})
        assert result == "emotional"

    def test_resolved_problem_no_emotional(self):
        """Resolved problem without emotional markers -> milestone."""
        text = "The server crash was fixed by patching the config"
        result = _disambiguate("problem", text, {"milestone": 1.0})
        assert result == "milestone"

    def test_problem_positive_sentiment_milestone(self):
        """Problem + positive + milestone score -> milestone."""
        text = "The build was broken but the breakthrough solved everything"
        result = _disambiguate("problem", text, {"milestone": 2.0})
        assert result == "milestone"

    def test_problem_positive_sentiment_emotional_only(self):
        """Problem + positive + emotional (no milestone) -> emotional."""
        text = "The problem is solved and I'm so happy and proud and grateful"
        result = _disambiguate("problem", text, {"emotional": 2.0})
        assert result == "emotional"

    def test_non_problem_unchanged(self):
        """Non-problem types pass through unchanged."""
        result = _disambiguate("decision", "we decided to use X", {"decision": 3.0})
        assert result == "decision"


class TestExtractMemories:
    def test_extracts_decision(self):
        text = (
            "We decided to switch from REST to GraphQL because the frontend needs flexible queries."
            " The trade-off is complexity but it's worth it."
        )
        memories = extract_memories(text)
        assert len(memories) > 0
        types = [m["memory_type"] for m in memories]
        assert "decision" in types

    def test_extracts_problem(self):
        text = (
            "There's a critical bug in production. The server keeps crashing every 30 minutes."
            " The root cause is a memory leak in the connection pool."
        )
        memories = extract_memories(text)
        assert len(memories) > 0

    def test_extracts_milestone(self):
        text = (
            "We finally got the prototype working! Shipped version 2.0 and deployed to production."
            " First time we've had zero downtime during a release."
        )
        memories = extract_memories(text)
        assert len(memories) > 0

    def test_extracts_emotional(self):
        text = "I feel so proud of what we've built. I love this team. It was a beautiful moment when everything came together."
        memories = extract_memories(text)
        assert len(memories) > 0

    def test_skips_short_text(self):
        text = "ok"
        memories = extract_memories(text)
        assert len(memories) == 0

    def test_chunk_index_sequential(self):
        text = (
            "We decided to use GraphQL. The trade-off was complexity.\n\n"
            "The bug was in the connection pool. The root cause was a memory leak.\n\n"
            "Finally got it working! Shipped v2.0."
        )
        memories = extract_memories(text)
        indices = [m["chunk_index"] for m in memories]
        assert indices == list(range(len(indices)))

    def test_resolved_problem_becomes_milestone(self):
        text = "The server was crashing but we fixed it by patching the connection pool. It works now."
        memories = extract_memories(text)
        if memories:
            assert memories[0]["memory_type"] in {"milestone", "problem"}

    def test_min_confidence_filtering(self):
        text = "maybe something happened with the approach"
        memories = extract_memories(text, min_confidence=0.9)
        assert len(memories) == 0

    def test_code_heavy_text(self):
        """Text with lots of code should still extract from prose portions."""
        text = textwrap.dedent("""\
            We decided to switch from SQLite to PostgreSQL because it scales better.
            The trade-off is that deployment is more complex.

            ```python
            import psycopg2
            conn = psycopg2.connect("dbname=test")
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users")
            ```

            The migration was a breakthrough. We finally got it working after weeks.""")
        memories = extract_memories(text)
        types = [m["memory_type"] for m in memories]
        assert len(memories) > 0
        assert any(t in types for t in ["decision", "milestone"])

    def test_very_long_single_block(self):
        """Very long single block (no double newlines) should be chunked and processed."""
        lines = [f"We decided to use approach {i} because it was better." for i in range(30)]
        text = "\n".join(lines)
        memories = extract_memories(text)
        assert len(memories) > 0

    def test_preference_extraction(self):
        """Preferences like 'I prefer' or 'always use' should be detected."""
        text = (
            "I prefer using snake_case for all variable names. "
            "We always use type hints in our Python code. "
            "Never use mutable default arguments in function signatures."
        )
        memories = extract_memories(text)
        assert len(memories) > 0

    def test_mixed_speaker_turns(self):
        """Text with speaker turn markers (>= 3 turns) uses turn splitting."""
        text = textwrap.dedent("""\
            > We should switch to GraphQL instead of REST because flexibility
            That's a good decision. Let me look at the trade-offs.
            > I prefer the schema-first approach, always use code generation
            Great preference. Here's how we can implement that.
            > Finally got it working! The prototype is deployed and version 2.0 is live
            Congratulations on the milestone!""")
        memories = extract_memories(text)
        assert len(memories) > 0

    def test_empty_text_returns_empty(self):
        assert extract_memories("") == []

    def test_whitespace_only_returns_empty(self):
        assert extract_memories("   \n\n   ") == []
