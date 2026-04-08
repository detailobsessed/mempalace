"""Tests for normalize.py — chat export format normalization."""

import json

from mempalace.normalize import (
    _extract_content,
    _messages_to_transcript,
    _try_chatgpt_json,
    _try_claude_ai_json,
    _try_claude_code_jsonl,
    _try_codex_jsonl,
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
        f.write_text("> question 1\nanswer 1\n> question 2\nanswer 2\n> question 3\nanswer 3\n", encoding="utf-8")
        result = normalize(str(f))
        assert result.count(">") >= 3

    def test_plain_text_passthrough(self, tmp_path):
        f = tmp_path / "notes.txt"
        content = "Just some plain notes about the project."
        f.write_text(content, encoding="utf-8")
        result = normalize(str(f))
        assert result == content

    def test_json_chat(self, tmp_path):
        f = tmp_path / "chat.json"
        data = [
            {"role": "user", "content": "hello"},
            {"role": "assistant", "content": "hi there"},
        ]
        f.write_text(json.dumps(data), encoding="utf-8")
        result = normalize(str(f))
        assert "> hello" in result

    def test_empty_file(self, tmp_path):
        f = tmp_path / "empty.txt"
        f.write_text("", encoding="utf-8")
        result = normalize(str(f))
        assert not result

    def test_oserror_nonexistent_file(self):
        import pytest

        with pytest.raises(OSError, match="Could not read"):
            normalize("/nonexistent/path/to/file.txt")


class TestCodexJsonl:
    def test_valid_codex_session(self):
        lines = [
            json.dumps({"type": "session_meta", "session_id": "abc123"}),
            json.dumps({
                "type": "event_msg",
                "payload": {"type": "user_message", "message": "Fix the bug"},
            }),
            json.dumps({
                "type": "event_msg",
                "payload": {"type": "agent_message", "message": "Done, I fixed it."},
            }),
        ]
        content = "\n".join(lines)
        result = _try_codex_jsonl(content)
        assert result is not None
        assert "> Fix the bug" in result
        assert "Done, I fixed it." in result

    def test_codex_without_session_meta(self):
        """Without session_meta, codex parser should return None."""
        lines = [
            json.dumps({
                "type": "event_msg",
                "payload": {"type": "user_message", "message": "hello"},
            }),
            json.dumps({
                "type": "event_msg",
                "payload": {"type": "agent_message", "message": "hi"},
            }),
        ]
        content = "\n".join(lines)
        result = _try_codex_jsonl(content)
        assert result is None

    def test_codex_too_few_messages(self):
        lines = [
            json.dumps({"type": "session_meta", "session_id": "abc"}),
            json.dumps({
                "type": "event_msg",
                "payload": {"type": "user_message", "message": "hello"},
            }),
        ]
        content = "\n".join(lines)
        result = _try_codex_jsonl(content)
        assert result is None

    def test_codex_skips_non_event_msg(self):
        lines = [
            json.dumps({"type": "session_meta", "session_id": "abc"}),
            json.dumps({"type": "response_item", "payload": {"text": "noise"}}),
            json.dumps({
                "type": "event_msg",
                "payload": {"type": "user_message", "message": "query"},
            }),
            json.dumps({
                "type": "event_msg",
                "payload": {"type": "agent_message", "message": "answer"},
            }),
        ]
        content = "\n".join(lines)
        result = _try_codex_jsonl(content)
        assert result is not None
        assert "noise" not in result

    def test_codex_skips_non_string_message(self):
        lines = [
            json.dumps({"type": "session_meta", "session_id": "abc"}),
            json.dumps({
                "type": "event_msg",
                "payload": {"type": "user_message", "message": ["not", "a", "string"]},
            }),
            json.dumps({
                "type": "event_msg",
                "payload": {"type": "user_message", "message": "real question"},
            }),
            json.dumps({
                "type": "event_msg",
                "payload": {"type": "agent_message", "message": "real answer"},
            }),
        ]
        content = "\n".join(lines)
        result = _try_codex_jsonl(content)
        assert result is not None
        assert "> real question" in result

    def test_codex_skips_non_dict_payload(self):
        lines = [
            json.dumps({"type": "session_meta", "session_id": "abc"}),
            json.dumps({"type": "event_msg", "payload": "not a dict"}),
            json.dumps({
                "type": "event_msg",
                "payload": {"type": "user_message", "message": "q"},
            }),
            json.dumps({
                "type": "event_msg",
                "payload": {"type": "agent_message", "message": "a"},
            }),
        ]
        content = "\n".join(lines)
        result = _try_codex_jsonl(content)
        assert result is not None

    def test_codex_plain_text_returns_none(self):
        result = _try_codex_jsonl("just some plain text\nnothing special")
        assert result is None


class TestClaudeAiPrivacyExport:
    def test_privacy_export_with_chat_messages(self):
        """Array of conversation objects with chat_messages inside each."""
        data = [
            {
                "uuid": "conv-1",
                "name": "First conversation",
                "chat_messages": [
                    {"role": "human", "content": "What is Python?"},
                    {"role": "assistant", "content": "A programming language."},
                ],
            },
            {
                "uuid": "conv-2",
                "name": "Second conversation",
                "chat_messages": [
                    {"role": "user", "content": "Tell me about Rust."},
                    {"role": "ai", "content": "A systems programming language."},
                ],
            },
        ]
        result = _try_claude_ai_json(data)
        assert result is not None
        assert "> What is Python?" in result
        assert "A programming language." in result
        assert "> Tell me about Rust." in result
        assert "A systems programming language." in result

    def test_privacy_export_too_few_messages(self):
        data = [
            {
                "uuid": "conv-1",
                "chat_messages": [
                    {"role": "user", "content": "hello"},
                ],
            },
        ]
        result = _try_claude_ai_json(data)
        assert result is None

    def test_privacy_export_skips_non_dict_entries(self):
        data = [
            "not a dict",
            {
                "chat_messages": [
                    {"role": "user", "content": "question"},
                    {"role": "assistant", "content": "answer"},
                ],
            },
        ]
        # First element has no "chat_messages" key, so won't enter privacy path
        # This exercises the flat-message fallback
        result = _try_claude_ai_json(data)
        # The first item is a string, not a dict with chat_messages, so it
        # falls through to the flat message path which also can't parse strings
        assert result is None


class TestChatGptFallbackRoot:
    def test_root_with_message_no_synthetic_root(self):
        """When root node has a message (no synthetic null-message root)."""
        data = {
            "mapping": {
                "root": {
                    "parent": None,
                    "message": {
                        "author": {"role": "system"},
                        "content": {"parts": ["You are a helpful assistant."]},
                    },
                    "children": ["msg1"],
                },
                "msg1": {
                    "parent": "root",
                    "message": {
                        "author": {"role": "user"},
                        "content": {"parts": ["What is 1+1?"]},
                    },
                    "children": ["msg2"],
                },
                "msg2": {
                    "parent": "msg1",
                    "message": {
                        "author": {"role": "assistant"},
                        "content": {"parts": ["2"]},
                    },
                    "children": [],
                },
            }
        }
        result = _try_chatgpt_json(data)
        assert result is not None
        assert "> What is 1+1?" in result
        assert "2" in result


class TestSlackThreePlusSpeakers:
    def test_three_speakers_role_alternation(self):
        """With 3+ speakers, roles alternate based on last_role."""
        data = [
            {"type": "message", "user": "U1", "text": "Hey team"},
            {"type": "message", "user": "U2", "text": "Hi U1"},
            {"type": "message", "user": "U3", "text": "Hello everyone"},
            {"type": "message", "user": "U1", "text": "Let's discuss the plan"},
        ]
        result = _try_slack_json(data)
        assert result is not None
        # U1 is first seen -> user, U2 last_role=user -> assistant,
        # U3 last_role=assistant -> user
        assert "> Hey team" in result
        assert "> Hello everyone" in result


class TestMessagesToTranscriptOrphanedAssistant:
    def test_consecutive_assistant_messages(self):
        """Assistant messages without a preceding user message are output as plain text."""
        messages = [
            ("assistant", "I started without being asked."),
            ("user", "Now I ask something."),
            ("assistant", "Here is the answer."),
        ]
        result = _messages_to_transcript(messages, spellcheck=False)
        # The orphaned assistant message should appear as plain text (no > marker)
        assert "I started without being asked." in result
        assert "> Now I ask something." in result
        assert "Here is the answer." in result
        # Only one user turn marker
        lines_with_marker = [ln for ln in result.split("\n") if ln.strip().startswith(">")]
        assert len(lines_with_marker) == 1

    def test_multiple_consecutive_assistant_messages(self):
        """Multiple assistant messages in a row without user turns."""
        messages = [
            ("assistant", "First orphan."),
            ("assistant", "Second orphan."),
            ("user", "Finally a question."),
            ("assistant", "And an answer."),
        ]
        result = _messages_to_transcript(messages, spellcheck=False)
        assert "First orphan." in result
        assert "Second orphan." in result
        assert "> Finally a question." in result
        assert "And an answer." in result
        lines_with_marker = [ln for ln in result.split("\n") if ln.strip().startswith(">")]
        assert len(lines_with_marker) == 1
