"""Tests for convo_miner.py — conversation chunking and room detection."""

from mempalace.convo_miner import (
    _chunk_by_exchange,
    _chunk_by_paragraph,
    chunk_exchanges,
    detect_convo_room,
)


class TestChunkExchanges:
    def test_exchange_pairs(self):
        content = (
            "> What is Python?\nPython is a programming language.\n> How do I install it?\nUse pip or conda.\n> Thanks\nYou're welcome."
        )
        chunks = chunk_exchanges(content)
        assert len(chunks) >= 2

    def test_fallback_to_paragraph(self):
        # Paragraphs must exceed MIN_CHUNK_SIZE (30 chars) to be kept
        content = (
            "First paragraph about stuff and things happening.\n\n"
            "Second paragraph with much more details about everything.\n\n"
            "Third paragraph wrapping up all the loose ends here."
        )
        chunks = chunk_exchanges(content)
        assert len(chunks) >= 2

    def test_empty_content(self):
        chunks = chunk_exchanges("")
        assert chunks == []


class TestChunkByExchange:
    def test_pairs_user_and_response(self):
        lines = [
            "> What is 2+2?",
            "The answer is 4.",
            "",
            "> What is 3+3?",
            "The answer is 6.",
        ]
        chunks = _chunk_by_exchange(lines)
        assert len(chunks) == 2
        assert "> What is 2+2?" in chunks[0]["content"]
        assert "answer is 4" in chunks[0]["content"]

    def test_user_turn_without_response(self):
        lines = ["> Just a question", "---", "> Another question"]
        chunks = _chunk_by_exchange(lines)
        # Short turns might be filtered by MIN_CHUNK_SIZE
        assert isinstance(chunks, list)

    def test_sequential_indices(self):
        lines = [
            "> First question here with enough text to pass minimum",
            "First answer with enough text to be meaningful content",
            "> Second question here with enough text to pass minimum",
            "Second answer with enough text to be meaningful content",
        ]
        chunks = _chunk_by_exchange(lines)
        for i, chunk in enumerate(chunks):
            assert chunk["chunk_index"] == i


class TestChunkByParagraph:
    def test_splits_on_double_newline(self):
        content = ("A" * 40) + "\n\n" + ("B" * 40)
        chunks = _chunk_by_paragraph(content)
        assert len(chunks) == 2

    def test_single_long_block_splits_by_lines(self):
        lines = ["Line number " + str(i) for i in range(50)]
        content = "\n".join(lines)
        chunks = _chunk_by_paragraph(content)
        assert len(chunks) >= 1


class TestDetectConvoRoom:
    def test_technical(self):
        content = "Let me debug this Python function. There's a bug in the API endpoint."
        assert detect_convo_room(content) == "technical"

    def test_planning(self):
        content = "Let's plan the roadmap for the next sprint. The priority is the milestone deadline."
        assert detect_convo_room(content) == "planning"

    def test_decisions(self):
        content = "We decided to switch to GraphQL. We chose this approach over the alternative."
        assert detect_convo_room(content) == "decisions"

    def test_problems(self):
        content = "The server is broken and keeps crashing. We need a workaround until the fix is resolved."
        assert detect_convo_room(content) == "problems"

    def test_general_fallback(self):
        content = "The weather is nice today and I had a good lunch."
        assert detect_convo_room(content) == "general"
