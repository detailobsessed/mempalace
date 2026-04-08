"""Tests for normalize.py — chat export format normalization."""

import json

from mempalace.normalize import (
    _extract_content,
    _messages_to_transcript,
    _try_chatgpt_json,
    _try_claude_ai_json,
    _try_claude_code_jsonl,
    _try_slack_json,
    normalize,
)


class TestExtractContent:
    def test_string(self):
        assert _extract_content("hello world") == "hello world"

    def test_string_strips(self):
        assert _extract_content("  hello  ") == "hello"

    def test_list_of_strings(self):
        assert _extract_content(["hello", "world"]) == "hello world"

    def test_list_of_text_blocks(self):
        blocks = [{"type": "text", "text": "hello"}, {"type": "text", "text": "world"}]
        assert _extract_content(blocks) == "hello world"

    def test_dict_with_text(self):
        assert _extract_content({"text": "hello"}) == "hello"

    def test_empty_list(self):
        assert not _extract_content([])

    def test_none(self):
        assert not _extract_content(None)

    def test_mixed_list(self):
        blocks = ["hello", {"type": "text", "text": "world"}, {"type": "image", "url": "..."}]
        assert _extract_content(blocks) == "hello world"


class TestMessagesToTranscript:
    def test_basic_exchange(self):
        messages = [("user", "what is 2+2?"), ("assistant", "4")]
        result = _messages_to_transcript(messages, spellcheck=False)
        assert "> what is 2+2?" in result
        assert "4" in result

    def test_multiple_exchanges(self):
        messages = [
            ("user", "hello"),
            ("assistant", "hi there"),
            ("user", "bye"),
            ("assistant", "goodbye"),
        ]
        result = _messages_to_transcript(messages, spellcheck=False)
        assert result.count(">") == 2

    def test_consecutive_user_messages(self):
        messages = [("user", "first"), ("user", "second"), ("assistant", "response")]
        result = _messages_to_transcript(messages, spellcheck=False)
        assert "> first" in result
        assert "> second" in result


class TestClaudeAiJson:
    def test_simple_messages(self):
        data = [
            {"role": "user", "content": "hello"},
            {"role": "assistant", "content": "hi there"},
        ]
        result = _try_claude_ai_json(data)
        assert result is not None
        assert "> hello" in result

    def test_dict_wrapper(self):
        data = {
            "messages": [
                {"role": "user", "content": "hello"},
                {"role": "assistant", "content": "hi"},
            ]
        }
        result = _try_claude_ai_json(data)
        assert result is not None

    def test_human_role(self):
        data = [
            {"role": "human", "content": "hello"},
            {"role": "ai", "content": "hi"},
        ]
        result = _try_claude_ai_json(data)
        assert result is not None

    def test_too_few_messages(self):
        data = [{"role": "user", "content": "hello"}]
        result = _try_claude_ai_json(data)
        assert result is None

    def test_non_list(self):
        result = _try_claude_ai_json("not a list")
        assert result is None


class TestChatGptJson:
    def test_mapping_tree(self):
        data = {
            "mapping": {
                "root": {
                    "parent": None,
                    "message": None,
                    "children": ["msg1"],
                },
                "msg1": {
                    "parent": "root",
                    "message": {
                        "author": {"role": "user"},
                        "content": {"parts": ["what is AI?"]},
                    },
                    "children": ["msg2"],
                },
                "msg2": {
                    "parent": "msg1",
                    "message": {
                        "author": {"role": "assistant"},
                        "content": {"parts": ["AI is artificial intelligence."]},
                    },
                    "children": [],
                },
            }
        }
        result = _try_chatgpt_json(data)
        assert result is not None
        assert "> what is AI?" in result
        assert "artificial intelligence" in result

    def test_no_mapping(self):
        result = _try_chatgpt_json({"not": "mapping"})
        assert result is None


class TestSlackJson:
    def test_basic_dm(self):
        data = [
            {"type": "message", "user": "U1", "text": "hey there"},
            {"type": "message", "user": "U2", "text": "hi!"},
        ]
        result = _try_slack_json(data)
        assert result is not None
        assert "> hey there" in result

    def test_non_messages_skipped(self):
        data = [
            {"type": "channel_join", "user": "U1", "text": "joined"},
            {"type": "message", "user": "U1", "text": "hello"},
            {"type": "message", "user": "U2", "text": "hi"},
        ]
        result = _try_slack_json(data)
        assert result is not None

    def test_not_a_list(self):
        result = _try_slack_json({"not": "a list"})
        assert result is None


class TestClaudeCodeJsonl:
    def test_basic_session(self):
        lines = [
            json.dumps({"type": "human", "message": {"content": "hello"}}),
            json.dumps({"type": "assistant", "message": {"content": "hi there"}}),
        ]
        content = "\n".join(lines)
        result = _try_claude_code_jsonl(content)
        assert result is not None
        assert "> hello" in result

    def test_not_jsonl(self):
        result = _try_claude_code_jsonl("just plain text")
        assert result is None


class TestNormalize:
    def test_passthrough_with_markers(self, tmp_path):
        f = tmp_path / "chat.txt"
        f.write_text("> question 1\nanswer 1\n> question 2\nanswer 2\n> question 3\nanswer 3\n")
        result = normalize(str(f))
        assert result.count(">") >= 3

    def test_plain_text_passthrough(self, tmp_path):
        f = tmp_path / "notes.txt"
        content = "Just some plain notes about the project."
        f.write_text(content)
        result = normalize(str(f))
        assert result == content

    def test_json_chat(self, tmp_path):
        f = tmp_path / "chat.json"
        data = [
            {"role": "user", "content": "hello"},
            {"role": "assistant", "content": "hi there"},
        ]
        f.write_text(json.dumps(data))
        result = normalize(str(f))
        assert "> hello" in result

    def test_empty_file(self, tmp_path):
        f = tmp_path / "empty.txt"
        f.write_text("")
        result = normalize(str(f))
        assert not result
