"""Tests for AAAK Dialect compression."""

import json

from mempalace.dialect import Dialect


class TestDialectInit:
    def test_default_no_entities(self):
        d = Dialect()
        assert d.entity_codes == {}

    def test_with_entities(self):
        d = Dialect(entities={"Alice": "ALC", "Bob": "BOB"})
        assert d.entity_codes["Alice"] == "ALC"
        assert d.entity_codes["alice"] == "ALC"

    def test_skip_names(self):
        d = Dialect(skip_names=["Gandalf"])
        assert "gandalf" in d.skip_names

    def test_from_config(self, tmp_path):
        config = {"entities": {"Alice": "ALC"}, "skip_names": ["Sherlock"]}
        cfg_file = tmp_path / "entities.json"
        cfg_file.write_text(json.dumps(config))
        d = Dialect.from_config(str(cfg_file))
        assert d.entity_codes["Alice"] == "ALC"
        assert "sherlock" in d.skip_names

    def test_save_config(self, tmp_path):
        d = Dialect(entities={"Alice": "ALC"})
        out = tmp_path / "out.json"
        d.save_config(str(out))
        loaded = json.loads(out.read_text())
        assert "Alice" in loaded["entities"]


class TestEncodeEntity:
    def test_known_entity(self):
        d = Dialect(entities={"Alice": "ALC"})
        assert d.encode_entity("Alice") == "ALC"

    def test_case_insensitive_lookup(self):
        d = Dialect(entities={"Alice": "ALC"})
        assert d.encode_entity("alice") == "ALC"

    def test_partial_match(self):
        d = Dialect(entities={"Alice Smith": "ALSO"})
        assert d.encode_entity("Alice Smith") == "ALSO"

    def test_auto_code_unknown(self):
        d = Dialect()
        assert d.encode_entity("Jordan") == "JOR"

    def test_skip_name_returns_none(self):
        d = Dialect(skip_names=["Gandalf"])
        assert d.encode_entity("Gandalf") is None


class TestEncodeEmotions:
    def test_known_emotions(self):
        d = Dialect()
        result = d.encode_emotions(["vulnerability", "joy"])
        assert result == "vul+joy"

    def test_caps_at_three(self):
        d = Dialect()
        result = d.encode_emotions(["joy", "fear", "trust", "grief"])
        codes = result.split("+")
        assert len(codes) == 3

    def test_unknown_emotion_truncated(self):
        d = Dialect()
        result = d.encode_emotions(["somethingweird"])
        assert result == "some"

    def test_deduplicates(self):
        d = Dialect()
        result = d.encode_emotions(["joy", "joyful"])
        assert result == "joy"


class TestCompress:
    def test_basic_compression(self):
        d = Dialect()
        result = d.compress("We decided to use GraphQL instead of REST because it fits better")
        assert "|" in result
        assert len(result) < 200

    def test_with_metadata(self):
        d = Dialect()
        result = d.compress(
            "Some text about decisions",
            metadata={"wing": "myproject", "room": "backend", "source_file": "notes.txt"},
        )
        assert "myproject" in result
        assert "backend" in result

    def test_detects_emotions(self):
        d = Dialect()
        result = d.compress("I'm so excited and happy about this breakthrough!")
        assert "excite" in result or "joy" in result

    def test_detects_flags(self):
        d = Dialect()
        result = d.compress("We decided to switch the database architecture to PostgreSQL")
        assert "DECISION" in result or "TECHNICAL" in result

    def test_detects_entities(self):
        d = Dialect(entities={"Alice": "ALC"})
        result = d.compress("Alice said she prefers the new approach")
        assert "ALC" in result

    def test_empty_text(self):
        d = Dialect()
        result = d.compress("")
        assert isinstance(result, str)


class TestCompressionStats:
    def test_stats_structure(self):
        d = Dialect()
        original = "This is a long piece of text that should compress well when encoded."
        compressed = d.compress(original)
        stats = d.compression_stats(original, compressed)
        assert "original_tokens_est" in stats
        assert "summary_tokens_est" in stats
        assert "size_ratio" in stats
        assert stats["original_chars"] == len(original)
        assert stats["summary_chars"] == len(compressed)

    def test_ratio_positive(self):
        d = Dialect()
        original = "We decided to use GraphQL because " * 20
        compressed = d.compress(original)
        stats = d.compression_stats(original, compressed)
        assert stats["size_ratio"] > 1


class TestCountTokens:
    def test_token_count(self):
        # Word-based heuristic: ~1.3 tokens per word, min 1
        assert Dialect.count_tokens("hello world") >= 2
        assert Dialect.count_tokens("") >= 0  # max(1, ...) returns 1 for empty
        assert Dialect.count_tokens("one") >= 1


class TestDecode:
    def test_decode_header(self):
        d = Dialect()
        text = 'myproject|backend|2026-01-01|notes\n0:ALC|graphql_rest|"decided to switch"|determ|DECISION'
        result = d.decode(text)
        assert result["header"]["file"] == "myproject"
        assert result["header"]["date"] == "2026-01-01"
        assert len(result["zettels"]) == 1

    def test_decode_tunnel(self):
        d = Dialect()
        text = "T:001<->002|shared_topic"
        result = d.decode(text)
        assert len(result["tunnels"]) == 1
        assert "T:001" in result["tunnels"][0]

    def test_decode_arc(self):
        d = Dialect()
        text = "ARC:fear->hope->peace"
        result = d.decode(text)
        assert result["arc"] == "fear->hope->peace"


class TestEncodeZettel:
    def test_basic_zettel(self):
        d = Dialect(entities={"Alice": "ALC"})
        zettel = {
            "id": "z-001",
            "people": ["Alice"],
            "topics": ["graphql", "api"],
            "content": "Alice said 'we should use GraphQL'",
            "emotional_weight": 0.7,
            "emotional_tone": ["conviction"],
            "origin_label": "",
            "notes": "",
            "title": "",
        }
        result = d.encode_zettel(zettel)
        assert "ALC" in result
        assert "graphql" in result

    def test_zettel_flags(self):
        d = Dialect()
        zettel = {
            "origin_moment": True,
            "sensitivity": "MAXIMUM",
            "notes": "foundational pillar genesis",
            "origin_label": "",
        }
        flags = d.get_flags(zettel)
        assert "ORIGIN" in flags
        assert "SENSITIVE" in flags
        assert "CORE" in flags
        assert "GENESIS" in flags


class TestEncodeFile:
    def test_full_file_encoding(self):
        d = Dialect(entities={"Alice": "ALC"})
        data = {
            "source_file": "001-meeting-notes.txt",
            "emotional_arc": "trust->fear->hope",
            "zettels": [
                {
                    "id": "z-001",
                    "people": ["Alice"],
                    "topics": ["planning"],
                    "content": "Alice planned the sprint",
                    "emotional_weight": 0.5,
                    "emotional_tone": [],
                    "date_context": "2026-01-01",
                    "origin_moment": False,
                    "sensitivity": "",
                    "notes": "",
                    "origin_label": "",
                    "title": "",
                }
            ],
            "tunnels": [{"from": "z-001", "to": "z-002", "label": "related:planning"}],
        }
        result = d.encode_file(data)
        assert "001" in result
        assert "ARC:trust->fear->hope" in result
        assert "T:001<->002" in result


class TestGenerateLayer1:
    def test_generates_from_zettel_files(self, tmp_path):
        """generate_layer1 reads zettel JSON files and produces Layer 1 output."""
        zettel_data = {
            "source_file": "001-session.txt",
            "emotional_arc": "hope->joy",
            "zettels": [
                {
                    "id": "z-001",
                    "people": ["Alice"],
                    "topics": ["project", "launch"],
                    "content": "Alice launched the new project. It was a breakthrough moment.",
                    "emotional_weight": 0.95,
                    "emotional_tone": ["joy", "hope"],
                    "date_context": "March 20, 2026",
                    "origin_moment": True,
                    "sensitivity": "",
                    "notes": "foundational pillar",
                    "origin_label": "project genesis",
                    "title": "Project - The big launch",
                },
            ],
            "tunnels": [
                {"from": "z-001", "to": "z-002", "label": "related:planning phase"},
            ],
        }
        (tmp_path / "file_001.json").write_text(json.dumps(zettel_data))

        d = Dialect(entities={"Alice": "ALC"})
        result = d.generate_layer1(str(tmp_path))
        assert "LAYER 1" in result
        assert "MOMENTS" in result
        assert "ALC" in result

    def test_writes_output_file(self, tmp_path):
        """generate_layer1 writes to output_path when specified."""
        zettel_data = {
            "source_file": "001-notes.txt",
            "zettels": [
                {
                    "id": "z-001",
                    "people": [],
                    "topics": ["misc"],
                    "content": "Some content",
                    "emotional_weight": 0.9,
                    "emotional_tone": [],
                    "date_context": "Jan 1, 2026",
                    "origin_moment": False,
                    "sensitivity": "",
                    "notes": "core belief",
                    "origin_label": "",
                    "title": "",
                },
            ],
            "tunnels": [],
        }
        (tmp_path / "file_001.json").write_text(json.dumps(zettel_data))
        out = tmp_path / "LAYER1.aaak"

        d = Dialect()
        d.generate_layer1(str(tmp_path), output_path=str(out))
        assert out.exists()
        assert "LAYER 1" in out.read_text()

    def test_with_identity_sections(self, tmp_path):
        """generate_layer1 includes identity sections when provided."""
        zettel_data = {
            "source_file": "001-notes.txt",
            "zettels": [
                {
                    "id": "z-001",
                    "people": [],
                    "topics": [],
                    "content": "content",
                    "emotional_weight": 0.9,
                    "emotional_tone": [],
                    "date_context": "Jan 1",
                    "origin_moment": False,
                    "sensitivity": "",
                    "notes": "",
                    "origin_label": "",
                    "title": "",
                },
            ],
            "tunnels": [],
        }
        (tmp_path / "file_001.json").write_text(json.dumps(zettel_data))

        d = Dialect()
        result = d.generate_layer1(
            str(tmp_path),
            identity_sections={"IDENTITY": ["Name: Test User", "Role: Developer"]},
        )
        assert "=IDENTITY=" in result
        assert "Name: Test User" in result

    def test_empty_dir(self, tmp_path):
        """generate_layer1 on empty directory produces header only."""
        d = Dialect()
        result = d.generate_layer1(str(tmp_path))
        assert "LAYER 1" in result

    def test_skips_non_json(self, tmp_path):
        """generate_layer1 ignores non-JSON files."""
        (tmp_path / "notes.txt").write_text("not json")
        d = Dialect()
        result = d.generate_layer1(str(tmp_path))
        assert "LAYER 1" in result


class TestCompressFile:
    def test_compress_single_zettel_file(self, tmp_path):
        """compress_file reads a zettel JSON and returns AAAK Dialect string."""
        data = {
            "source_file": "002-design-review.txt",
            "emotional_arc": "",
            "zettels": [
                {
                    "id": "z-010",
                    "people": ["Bob"],
                    "topics": ["api", "design"],
                    "content": "Bob reviewed the API design",
                    "emotional_weight": 0.6,
                    "emotional_tone": ["trust"],
                    "date_context": "Feb 15, 2026",
                    "origin_moment": False,
                    "sensitivity": "",
                    "notes": "",
                    "origin_label": "",
                    "title": "API Review",
                },
            ],
            "tunnels": [],
        }
        f = tmp_path / "file_002.json"
        f.write_text(json.dumps(data))

        d = Dialect(entities={"Bob": "BOB"})
        result = d.compress_file(str(f))
        assert "BOB" in result
        assert "002" in result

    def test_compress_file_writes_output(self, tmp_path):
        """compress_file writes output when output_path given."""
        data = {
            "source_file": "003-notes.txt",
            "zettels": [
                {
                    "id": "z-020",
                    "people": [],
                    "topics": ["misc"],
                    "content": "Some notes",
                    "emotional_weight": 0.3,
                    "emotional_tone": [],
                    "date_context": "Jan 1",
                    "origin_moment": False,
                    "sensitivity": "",
                    "notes": "",
                    "origin_label": "",
                    "title": "",
                },
            ],
            "tunnels": [],
        }
        f = tmp_path / "file_003.json"
        f.write_text(json.dumps(data))
        out = tmp_path / "compressed.aaak"

        d = Dialect()
        d.compress_file(str(f), output_path=str(out))
        assert out.exists()


class TestCompressAll:
    def test_compress_multiple_files(self, tmp_path):
        """compress_all combines multiple zettel files separated by ---."""
        for i in range(3):
            data = {
                "source_file": f"00{i}-session.txt",
                "zettels": [
                    {
                        "id": f"z-{i:03d}",
                        "people": [],
                        "topics": ["topic"],
                        "content": f"Content for session {i}",
                        "emotional_weight": 0.5,
                        "emotional_tone": [],
                        "date_context": "Jan 1",
                        "origin_moment": False,
                        "sensitivity": "",
                        "notes": "",
                        "origin_label": "",
                        "title": "",
                    },
                ],
                "tunnels": [],
            }
            (tmp_path / f"file_{i:03d}.json").write_text(json.dumps(data))

        d = Dialect()
        result = d.compress_all(str(tmp_path))
        assert "---" in result
        assert result.count("---") >= 2

    def test_compress_all_writes_output(self, tmp_path):
        """compress_all writes to output_path when specified."""
        data = {
            "source_file": "001-test.txt",
            "zettels": [
                {
                    "id": "z-001",
                    "people": [],
                    "topics": [],
                    "content": "test",
                    "emotional_weight": 0.5,
                    "emotional_tone": [],
                    "date_context": "Jan 1",
                    "origin_moment": False,
                    "sensitivity": "",
                    "notes": "",
                    "origin_label": "",
                    "title": "",
                },
            ],
            "tunnels": [],
        }
        (tmp_path / "file_001.json").write_text(json.dumps(data))
        out = tmp_path / "ALL.aaak"

        d = Dialect()
        d.compress_all(str(tmp_path), output_path=str(out))
        assert out.exists()

    def test_skips_non_json_files(self, tmp_path):
        """compress_all ignores non-JSON files in the directory."""
        (tmp_path / "readme.txt").write_text("not json")
        data = {
            "source_file": "001-test.txt",
            "zettels": [
                {
                    "id": "z-001",
                    "people": [],
                    "topics": [],
                    "content": "test",
                    "emotional_weight": 0.5,
                    "emotional_tone": [],
                    "date_context": "Jan 1",
                    "origin_moment": False,
                    "sensitivity": "",
                    "notes": "",
                    "origin_label": "",
                    "title": "",
                },
            ],
            "tunnels": [],
        }
        (tmp_path / "file_001.json").write_text(json.dumps(data))

        d = Dialect()
        result = d.compress_all(str(tmp_path))
        assert isinstance(result, str)
