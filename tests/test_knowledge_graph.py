"""Tests for knowledge_graph.py — temporal entity-relationship graph."""

import pytest

from mempalace.knowledge_graph import KnowledgeGraph


@pytest.fixture
def kg(tmp_path):
    db_path = str(tmp_path / "test_kg.sqlite3")
    return KnowledgeGraph(db_path=db_path)


class TestAddEntity:
    def test_add_and_stats(self, kg):
        kg.add_entity("Alice", "person")
        stats = kg.stats()
        assert stats["entities"] == 1

    def test_add_with_properties(self, kg):
        eid = kg.add_entity("Alice", "person", {"birthday": "1990-01-01"})
        assert eid == "alice"

    def test_upsert(self, kg):
        kg.add_entity("Alice", "person")
        kg.add_entity("Alice", "person", {"age": "35"})
        stats = kg.stats()
        assert stats["entities"] == 1


class TestAddTriple:
    def test_basic_triple(self, kg):
        tid = kg.add_triple("Max", "child_of", "Alice")
        assert tid is not None
        stats = kg.stats()
        assert stats["triples"] == 1

    def test_auto_creates_entities(self, kg):
        kg.add_triple("Max", "child_of", "Alice")
        stats = kg.stats()
        assert stats["entities"] == 2  # Max + Alice

    def test_with_temporal(self, kg):
        tid = kg.add_triple("Max", "does", "swimming", valid_from="2025-01-01")
        assert tid is not None

    def test_duplicate_returns_existing(self, kg):
        tid1 = kg.add_triple("Max", "loves", "chess")
        tid2 = kg.add_triple("Max", "loves", "chess")
        assert tid1 == tid2
        stats = kg.stats()
        assert stats["triples"] == 1


class TestInvalidate:
    def test_invalidate_sets_end_date(self, kg):
        kg.add_triple("Max", "has_issue", "injury", valid_from="2026-01-01")
        kg.invalidate("Max", "has_issue", "injury", ended="2026-02-15")
        stats = kg.stats()
        assert stats["expired_facts"] == 1
        assert stats["current_facts"] == 0


class TestQueryEntity:
    def test_outgoing(self, kg):
        kg.add_triple("Max", "loves", "chess")
        kg.add_triple("Max", "does", "swimming")
        results = kg.query_entity("Max", direction="outgoing")
        assert len(results) == 2
        predicates = {r["predicate"] for r in results}
        assert "loves" in predicates
        assert "does" in predicates

    def test_incoming(self, kg):
        kg.add_triple("Max", "child_of", "Alice")
        results = kg.query_entity("Alice", direction="incoming")
        assert len(results) == 1
        assert results[0]["subject"] == "Max"

    def test_both_directions(self, kg):
        kg.add_triple("Max", "child_of", "Alice")
        kg.add_triple("Alice", "married_to", "Jordan")
        results = kg.query_entity("Alice", direction="both")
        assert len(results) == 2

    def test_temporal_filter(self, kg):
        kg.add_triple("Max", "does", "swimming", valid_from="2025-01-01")
        kg.add_triple("Max", "does", "chess", valid_from="2026-01-01")
        results = kg.query_entity("Max", as_of="2025-06-01", direction="outgoing")
        assert len(results) == 1
        assert results[0]["object"] == "swimming"

    def test_expired_facts_filtered(self, kg):
        kg.add_triple("Max", "has_issue", "injury", valid_from="2026-01-01")
        kg.invalidate("Max", "has_issue", "injury", ended="2026-02-15")
        results = kg.query_entity("Max", as_of="2026-03-01", direction="outgoing")
        assert len(results) == 0


class TestQueryRelationship:
    def test_by_predicate(self, kg):
        kg.add_triple("Max", "loves", "chess")
        kg.add_triple("Alice", "loves", "gardening")
        results = kg.query_relationship("loves")
        assert len(results) == 2

    def test_normalizes_predicate(self, kg):
        kg.add_triple("Max", "child of", "Alice")
        results = kg.query_relationship("child of")
        assert len(results) == 1


class TestTimeline:
    def test_all_timeline(self, kg):
        kg.add_triple("Max", "born", "hospital", valid_from="2015-04-01")
        kg.add_triple("Max", "started", "school", valid_from="2021-09-01")
        timeline = kg.timeline()
        assert len(timeline) == 2
        # Should be chronological
        assert timeline[0]["valid_from"] <= timeline[1]["valid_from"]

    def test_entity_timeline(self, kg):
        kg.add_triple("Max", "born", "hospital", valid_from="2015-04-01")
        kg.add_triple("Alice", "started", "job", valid_from="2020-01-01")
        timeline = kg.timeline("Max")
        assert len(timeline) == 1
        assert timeline[0]["subject"] == "Max"


class TestStats:
    def test_empty_graph(self, kg):
        stats = kg.stats()
        assert stats["entities"] == 0
        assert stats["triples"] == 0
        assert stats["current_facts"] == 0
        assert stats["expired_facts"] == 0

    def test_populated_graph(self, kg):
        kg.add_triple("Max", "loves", "chess")
        kg.add_triple("Max", "does", "swimming")
        kg.add_triple("Max", "has_issue", "injury")
        kg.invalidate("Max", "has_issue", "injury")
        stats = kg.stats()
        assert stats["triples"] == 3
        assert stats["current_facts"] == 2
        assert stats["expired_facts"] == 1
        assert "loves" in stats["relationship_types"]


class TestSeedFromEntityFacts:
    def test_seed_from_entity_facts(self, tmp_path):
        kg = KnowledgeGraph(db_path=str(tmp_path / "kg.sqlite3"))
        facts = {
            "alice": {
                "full_name": "Alice",
                "type": "person",
                "gender": "female",
                "birthday": "1990-01-15",
                "partner": "jordan",
                "interests": ["reading", "hiking"],
            },
            "max": {
                "full_name": "Max",
                "type": "person",
                "gender": "male",
                "birthday": "2015-04-01",
                "parent": "alice",
                "relationship": "daughter",
                "interests": ["chess", "swimming"],
            },
            "buddy": {
                "full_name": "Buddy",
                "type": "animal",
                "relationship": "dog",
                "owner": "alice",
            },
        }
        kg.seed_from_entity_facts(facts)
        stats = kg.stats()
        assert stats["entities"] > 0
        assert stats["triples"] > 0

        results = kg.query_entity("Alice", direction="outgoing")
        predicates = {r["predicate"] for r in results}
        assert "married_to" in predicates
