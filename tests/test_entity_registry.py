"""Tests for entity_registry.py — persistent entity registry."""

import json
import urllib.error
import urllib.request
from email.message import Message
from unittest.mock import MagicMock

from mempalace.entity_registry import (
    EntityRegistry,
    _wikipedia_lookup,
)


def _mock_urlopen(response_data, status=200):
    """Create a mock for urllib.request.urlopen."""
    if status == 404:
        raise urllib.error.HTTPError(
            url="https://en.wikipedia.org/api/rest_v1/page/summary/test",
            code=404,
            msg="Not Found",
            hdrs=Message(),
            fp=None,
        )
    mock_response = MagicMock()
    mock_response.read.return_value = json.dumps(response_data).encode()
    mock_response.__enter__ = lambda s: s
    mock_response.__exit__ = MagicMock(return_value=False)
    return mock_response


class TestEntityRegistryLoadSave:
    def test_load_empty(self, tmp_path):
        reg = EntityRegistry.load(tmp_path)
        assert reg.mode == "personal"
        assert reg.people == {}
        assert reg.projects == []

    def test_save_and_reload(self, tmp_path):
        reg = EntityRegistry.load(tmp_path)
        reg.seed(
            mode="work",
            people=[{"name": "Alice", "relationship": "colleague", "context": "work"}],
            projects=["MemPalace"],
        )
        reg2 = EntityRegistry.load(tmp_path)
        assert reg2.mode == "work"
        assert "Alice" in reg2.people
        assert "MemPalace" in reg2.projects

    def test_load_corrupt_json(self, tmp_path):
        (tmp_path / "entity_registry.json").write_text("not json{{{")
        reg = EntityRegistry.load(tmp_path)
        assert reg.people == {}


class TestSeed:
    def test_seed_people(self, tmp_path):
        reg = EntityRegistry.load(tmp_path)
        reg.seed(
            mode="personal",
            people=[
                {"name": "Riley", "relationship": "daughter", "context": "personal"},
                {"name": "Max", "relationship": "son", "context": "personal"},
            ],
            projects=[],
        )
        assert "Riley" in reg.people
        assert reg.people["Riley"]["source"] == "onboarding"
        assert reg.people["Riley"]["confidence"] >= 1.0

    def test_seed_with_aliases(self, tmp_path):
        reg = EntityRegistry.load(tmp_path)
        reg.seed(
            mode="personal",
            people=[{"name": "Maxwell", "relationship": "son", "context": "personal"}],
            projects=[],
            aliases={"Max": "Maxwell"},
        )
        assert "Max" in reg.people
        assert reg.people["Max"].get("canonical") == "Maxwell"

    def test_ambiguous_flags(self, tmp_path):
        reg = EntityRegistry.load(tmp_path)
        reg.seed(
            mode="personal",
            people=[{"name": "Grace", "relationship": "friend", "context": "personal"}],
            projects=[],
        )
        assert "grace" in reg.ambiguous_flags


class TestLookup:
    def _seeded_registry(self, tmp_path):
        reg = EntityRegistry.load(tmp_path)
        reg.seed(
            mode="personal",
            people=[
                {"name": "Riley", "relationship": "daughter", "context": "personal"},
                {"name": "Max", "relationship": "son", "context": "personal"},
            ],
            projects=["MemPalace"],
        )
        return reg

    def test_lookup_known_person(self, tmp_path):
        reg = self._seeded_registry(tmp_path)
        result = reg.lookup("Riley")
        assert result["type"] == "person"
        assert result["confidence"] >= 1.0

    def test_lookup_project(self, tmp_path):
        reg = self._seeded_registry(tmp_path)
        result = reg.lookup("MemPalace")
        assert result["type"] == "project"

    def test_lookup_unknown(self, tmp_path):
        reg = self._seeded_registry(tmp_path)
        result = reg.lookup("Gandalf")
        assert result["type"] == "unknown"

    def test_lookup_wiki_cached_confirmed(self, tmp_path):
        reg = EntityRegistry.load(tmp_path)
        reg._data["wiki_cache"] = {
            "Devon": {"inferred_type": "person", "confidence": 0.9, "confirmed": True},
        }
        result = reg.lookup("Devon")
        assert result["type"] == "person"
        assert result["source"] == "wiki"

    def test_disambiguation_person_context(self, tmp_path):
        reg = EntityRegistry.load(tmp_path)
        reg.seed(
            mode="personal",
            people=[{"name": "Max", "relationship": "son", "context": "personal"}],
            projects=[],
        )
        result = reg.lookup("Max", context="I picked up Max from school")
        assert result["type"] == "person"

    def test_disambiguation_concept_context(self, tmp_path):
        reg = EntityRegistry.load(tmp_path)
        reg.seed(
            mode="personal",
            people=[{"name": "Ever", "relationship": "", "context": "personal"}],
            projects=[],
        )
        result = reg.lookup("Ever", context="have you ever tried this")
        assert result["type"] == "concept"


class TestExtractPeopleFromQuery:
    def test_finds_known_names(self, tmp_path):
        reg = EntityRegistry.load(tmp_path)
        reg.seed(
            mode="personal",
            people=[
                {"name": "Riley", "relationship": "daughter", "context": "personal"},
                {"name": "Max", "relationship": "son", "context": "personal"},
            ],
            projects=[],
        )
        found = reg.extract_people_from_query("What did Riley say about the game?")
        assert "Riley" in found

    def test_extract_unknown_candidates(self, tmp_path):
        reg = EntityRegistry.load(tmp_path)
        unknowns = reg.extract_unknown_candidates("Did Jordan and Kira finish the report?")
        assert "Jordan" in unknowns or "Kira" in unknowns


class TestWikipediaLookup:
    def test_name_detection(self, monkeypatch):
        monkeypatch.setattr(
            urllib.request,
            "urlopen",
            lambda *_a, **_kw: _mock_urlopen({"type": "standard", "title": "Riley", "extract": "Riley is a given name of Irish origin."}),
        )
        result = _wikipedia_lookup("Riley")
        assert result["inferred_type"] == "person"
        assert result["confidence"] >= 0.8

    def test_place_detection(self, monkeypatch):
        monkeypatch.setattr(
            urllib.request,
            "urlopen",
            lambda *_a, **_kw: _mock_urlopen({
                "type": "standard",
                "title": "Denver",
                "extract": "Denver is the capital of the state of Colorado.",
            }),
        )
        result = _wikipedia_lookup("Denver")
        assert result["inferred_type"] == "place"

    def test_disambiguation_with_name(self, monkeypatch):
        monkeypatch.setattr(
            urllib.request,
            "urlopen",
            lambda *_a, **_kw: _mock_urlopen({
                "type": "disambiguation",
                "title": "Sam",
                "description": "Sam is a given name",
                "extract": "Sam may refer to...",
            }),
        )
        result = _wikipedia_lookup("Sam")
        assert result["inferred_type"] == "person"

    def test_not_found_assumes_proper_noun(self, monkeypatch):
        def raise_404(*_a, **_kw):
            raise urllib.error.HTTPError(
                url="test",
                code=404,
                msg="Not Found",
                hdrs=Message(),
                fp=None,
            )

        monkeypatch.setattr(urllib.request, "urlopen", raise_404)
        result = _wikipedia_lookup("Xyzzyplugh")
        assert result["inferred_type"] == "person"

    def test_concept_detection(self, monkeypatch):
        monkeypatch.setattr(
            urllib.request,
            "urlopen",
            lambda *_a, **_kw: _mock_urlopen({
                "type": "standard",
                "title": "Python",
                "extract": "Python is a high-level programming language.",
            }),
        )
        result = _wikipedia_lookup("Python")
        assert result["inferred_type"] == "concept"


class TestResearchAndConfirm:
    def test_research_caches_result(self, tmp_path, monkeypatch):
        reg = EntityRegistry.load(tmp_path)
        monkeypatch.setattr(
            urllib.request,
            "urlopen",
            lambda *_a, **_kw: _mock_urlopen({"type": "standard", "title": "Devin", "extract": "Devin is a given name of Irish origin."}),
        )
        result = reg.research("Devin")
        assert result["inferred_type"] == "person"
        # Second call should use cache (no HTTP call)
        monkeypatch.setattr(
            urllib.request,
            "urlopen",
            lambda *_a, **_kw: _mock_urlopen({"type": "standard", "extract": "should not reach"}),
        )
        result2 = reg.research("Devin")
        assert result2["inferred_type"] == "person"

    def test_confirm_research_adds_to_people(self, tmp_path):
        reg = EntityRegistry.load(tmp_path)
        reg._data.setdefault("wiki_cache", {})["Devon"] = {
            "inferred_type": "person",
            "confidence": 0.8,
            "confirmed": False,
        }
        reg.confirm_research("Devon", "person", relationship="friend")
        assert "Devon" in reg.people
        assert reg.people["Devon"]["source"] == "wiki"


class TestLearnFromText:
    def test_learns_new_entities(self, tmp_path):
        reg = EntityRegistry.load(tmp_path)
        text = ("Alice said hello. Alice asked about the project. Alice laughed.\nAlice told me about it. Alice smiled warmly.\n") * 3
        candidates = reg.learn_from_text(text, min_confidence=0.5)
        assert isinstance(candidates, list)


class TestSummary:
    def test_summary_format(self, tmp_path):
        reg = EntityRegistry.load(tmp_path)
        reg.seed(
            mode="personal",
            people=[{"name": "Riley", "relationship": "daughter", "context": "personal"}],
            projects=["MemPalace"],
        )
        summary = reg.summary()
        assert "personal" in summary.lower()
        assert "Riley" in summary
        assert "MemPalace" in summary
