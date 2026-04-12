"""Integration tests for layers.py, searcher.py, and palace_graph.py."""

import chromadb
import pytest

from mempalace.layers import Layer0, Layer1, Layer2, Layer3, MemoryStack
from mempalace.palace_graph import build_graph, find_tunnels, graph_stats, traverse
from mempalace.searcher import search, search_memories

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

META_BASE = {"chunk_index": 0, "added_by": "test"}


def _meta(wing, room, source_file, filed_at, **extra):
    return {**META_BASE, "wing": wing, "room": room, "source_file": source_file, "filed_at": filed_at, **extra}


@pytest.fixture
def palace(tmp_path):
    """Create a populated palace for testing."""
    palace_path = str(tmp_path / "palace")
    client = chromadb.PersistentClient(path=palace_path)
    col = client.get_or_create_collection("mempalace_drawers")
    col.add(
        ids=["d1", "d2", "d3", "d4"],
        documents=[
            "GraphQL migration discussion and architecture decisions",
            "Riley's school schedule and activities",
            "Sprint planning meeting notes for Q2",
            "Database optimization and indexing strategy",
        ],
        metadatas=[
            _meta("myproject", "backend", "notes.txt", "2026-01-01"),
            _meta("personal", "family", "journal.txt", "2026-01-02"),
            _meta("myproject", "planning", "sprint.txt", "2026-01-03"),
            _meta("myproject", "backend", "db.txt", "2026-01-04"),
        ],
    )
    client.close()
    return palace_path


@pytest.fixture
def palace_with_tunnels(tmp_path):
    """Palace where the same room name appears in multiple wings (creates graph edges)."""
    palace_path = str(tmp_path / "palace_tunnels")
    client = chromadb.PersistentClient(path=palace_path)
    col = client.get_or_create_collection("mempalace_drawers")
    col.add(
        ids=["t1", "t2", "t3", "t4", "t5"],
        documents=[
            "Backend work on the API layer",
            "Backend infrastructure for personal site",
            "Frontend React components",
            "Frontend design tokens",
            "DevOps CI/CD pipeline config",
        ],
        metadatas=[
            _meta("myproject", "backend", "a.txt", "2026-01-01", hall="engineering"),
            _meta("personal", "backend", "b.txt", "2026-01-02", hall="engineering"),
            _meta("myproject", "frontend", "c.txt", "2026-01-03", hall="engineering"),
            _meta("personal", "frontend", "d.txt", "2026-01-04", hall="design"),
            _meta("myproject", "devops", "e.txt", "2026-01-05", hall="infra"),
        ],
    )
    client.close()
    return palace_path


# ---------------------------------------------------------------------------
# Layer 0 tests
# ---------------------------------------------------------------------------


class TestLayer0:
    def test_render_with_file(self, tmp_path):
        identity_file = tmp_path / "identity.txt"
        identity_file.write_text("I am Atlas, a personal AI assistant.", encoding="utf-8")
        layer = Layer0(identity_path=str(identity_file))
        assert layer.render() == "I am Atlas, a personal AI assistant."

    def test_render_missing_file(self, tmp_path):
        layer = Layer0(identity_path=str(tmp_path / "nonexistent.txt"))
        result = layer.render()
        assert "No identity configured" in result

    def test_render_caches(self, tmp_path):
        identity_file = tmp_path / "identity.txt"
        identity_file.write_text("cached identity", encoding="utf-8")
        layer = Layer0(identity_path=str(identity_file))
        first = layer.render()
        # Modify file after first read
        identity_file.write_text("changed identity", encoding="utf-8")
        second = layer.render()
        assert first == second  # cached

    def test_token_estimate(self, tmp_path):
        identity_file = tmp_path / "identity.txt"
        identity_file.write_text("a" * 400, encoding="utf-8")
        layer = Layer0(identity_path=str(identity_file))
        assert layer.token_estimate() == 100


# ---------------------------------------------------------------------------
# Layer 1 tests
# ---------------------------------------------------------------------------


class TestLayer1:
    def test_generate_with_drawers(self, palace):
        layer = Layer1(palace_path=palace)
        result = layer.generate()
        assert "ESSENTIAL STORY" in result
        assert "backend" in result or "family" in result

    def test_generate_wing_filter(self, palace):
        layer = Layer1(palace_path=palace, wing="personal")
        result = layer.generate()
        assert "ESSENTIAL STORY" in result
        assert "Riley" in result

    def test_generate_no_palace(self, tmp_path):
        layer = Layer1(palace_path=str(tmp_path / "nonexistent"))
        result = layer.generate()
        assert "No palace found" in result

    def test_generate_empty_collection(self, tmp_path):
        palace_path = str(tmp_path / "empty_palace")
        client = chromadb.PersistentClient(path=palace_path)
        client.get_or_create_collection("mempalace_drawers")
        client.close()
        layer = Layer1(palace_path=palace_path)
        result = layer.generate()
        assert "No memories yet" in result

    def test_generate_with_importance(self, tmp_path):
        palace_path = str(tmp_path / "importance_palace")
        client = chromadb.PersistentClient(path=palace_path)
        col = client.get_or_create_collection("mempalace_drawers")
        col.add(
            ids=["i1", "i2"],
            documents=["Low importance item", "High importance item"],
            metadatas=[
                _meta("w", "r", "lo.txt", "2026-01-01", importance=1),
                _meta("w", "r", "hi.txt", "2026-01-02", importance=9),
            ],
        )
        client.close()
        layer = Layer1(palace_path=palace_path)
        result = layer.generate()
        # High importance should appear first in the output
        hi_pos = result.find("High importance")
        lo_pos = result.find("Low importance")
        assert hi_pos < lo_pos


# ---------------------------------------------------------------------------
# Layer 2 tests
# ---------------------------------------------------------------------------


class TestLayer2:
    def test_retrieve_all(self, palace):
        layer = Layer2(palace_path=palace)
        result = layer.retrieve()
        assert "ON-DEMAND" in result
        assert "4 drawers" in result

    def test_retrieve_by_wing(self, palace):
        layer = Layer2(palace_path=palace)
        result = layer.retrieve(wing="myproject")
        assert "3 drawers" in result

    def test_retrieve_by_room(self, palace):
        layer = Layer2(palace_path=palace)
        result = layer.retrieve(room="backend")
        assert "2 drawers" in result

    def test_retrieve_by_wing_and_room(self, palace):
        layer = Layer2(palace_path=palace)
        result = layer.retrieve(wing="personal", room="family")
        assert "1 drawers" in result
        assert "Riley" in result

    def test_retrieve_no_results(self, palace):
        layer = Layer2(palace_path=palace)
        result = layer.retrieve(wing="nonexistent")
        assert "No drawers found" in result

    def test_retrieve_no_palace(self, tmp_path):
        layer = Layer2(palace_path=str(tmp_path / "nope"))
        result = layer.retrieve()
        assert "No palace found" in result


# ---------------------------------------------------------------------------
# Layer 3 tests
# ---------------------------------------------------------------------------


class TestLayer3:
    def test_search(self, palace):
        layer = Layer3(palace_path=palace)
        result = layer.search("database optimization")
        assert "SEARCH RESULTS" in result
        assert "database" in result.lower()

    def test_search_with_wing_filter(self, palace):
        layer = Layer3(palace_path=palace)
        result = layer.search("planning", wing="myproject")
        assert "SEARCH RESULTS" in result

    def test_search_with_room_filter(self, palace):
        layer = Layer3(palace_path=palace)
        result = layer.search("architecture", room="backend")
        assert "SEARCH RESULTS" in result

    def test_search_with_wing_and_room(self, palace):
        layer = Layer3(palace_path=palace)
        result = layer.search("index", wing="myproject", room="backend")
        assert "SEARCH RESULTS" in result

    def test_search_no_palace(self, tmp_path):
        layer = Layer3(palace_path=str(tmp_path / "nope"))
        result = layer.search("anything")
        assert "No palace found" in result

    def test_search_raw_returns_list(self, palace):
        layer = Layer3(palace_path=palace)
        hits = layer.search_raw("database")
        assert isinstance(hits, list)
        assert len(hits) > 0
        hit = hits[0]
        assert "text" in hit
        assert "wing" in hit
        assert "room" in hit
        assert "similarity" in hit
        assert "source_file" in hit
        assert "metadata" in hit

    def test_search_raw_with_wing_filter(self, palace):
        layer = Layer3(palace_path=palace)
        hits = layer.search_raw("school", wing="personal")
        assert all(h["wing"] == "personal" for h in hits)

    def test_search_raw_no_palace(self, tmp_path):
        layer = Layer3(palace_path=str(tmp_path / "nope"))
        hits = layer.search_raw("anything")
        assert hits == []


# ---------------------------------------------------------------------------
# MemoryStack tests
# ---------------------------------------------------------------------------


class TestMemoryStack:
    def test_wake_up(self, palace, tmp_path):
        identity = tmp_path / "identity.txt"
        identity.write_text("I am Atlas.", encoding="utf-8")
        stack = MemoryStack(palace_path=palace, identity_path=str(identity))
        result = stack.wake_up()
        assert "Atlas" in result
        assert "ESSENTIAL STORY" in result

    def test_wake_up_with_wing(self, palace, tmp_path):
        identity = tmp_path / "identity.txt"
        identity.write_text("I am Atlas.", encoding="utf-8")
        stack = MemoryStack(palace_path=palace, identity_path=str(identity))
        result = stack.wake_up(wing="personal")
        assert "Atlas" in result
        assert "Riley" in result

    def test_recall(self, palace, tmp_path):
        identity = tmp_path / "identity.txt"
        identity.write_text("test", encoding="utf-8")
        stack = MemoryStack(palace_path=palace, identity_path=str(identity))
        result = stack.recall(wing="myproject")
        assert "ON-DEMAND" in result

    def test_search(self, palace, tmp_path):
        identity = tmp_path / "identity.txt"
        identity.write_text("test", encoding="utf-8")
        stack = MemoryStack(palace_path=palace, identity_path=str(identity))
        result = stack.search("database")
        assert "SEARCH RESULTS" in result

    def test_status(self, palace, tmp_path):
        identity = tmp_path / "identity.txt"
        identity.write_text("test", encoding="utf-8")
        stack = MemoryStack(palace_path=palace, identity_path=str(identity))
        status = stack.status()
        assert status["total_drawers"] == 4
        assert status["palace_path"] == palace
        assert status["L0_identity"]["exists"] is True

    def test_status_no_palace(self, tmp_path):
        identity = tmp_path / "identity.txt"
        identity.write_text("test", encoding="utf-8")
        stack = MemoryStack(
            palace_path=str(tmp_path / "nope"),
            identity_path=str(identity),
        )
        status = stack.status()
        assert status["total_drawers"] == 0


# ---------------------------------------------------------------------------
# searcher.py tests
# ---------------------------------------------------------------------------


class TestSearcher:
    def test_search_prints_results(self, palace, capsys):
        search("database optimization", palace_path=palace)
        captured = capsys.readouterr()
        assert "Results for" in captured.out
        assert "database" in captured.out.lower() or "Database" in captured.out

    def test_search_with_wing_filter(self, palace, capsys):
        search("planning", palace_path=palace, wing="myproject")
        captured = capsys.readouterr()
        assert "Wing: myproject" in captured.out

    def test_search_with_room_filter(self, palace, capsys):
        search("architecture", palace_path=palace, room="backend")
        captured = capsys.readouterr()
        assert "Room: backend" in captured.out

    def test_search_no_palace_raises(self, tmp_path):
        from mempalace.searcher import SearchError

        with pytest.raises(SearchError):
            search("anything", palace_path=str(tmp_path / "nope"))

    def test_search_memories_returns_dict(self, palace):
        result = search_memories("database", palace_path=palace)
        assert "query" in result
        assert result["query"] == "database"
        assert "results" in result
        assert len(result["results"]) > 0
        hit = result["results"][0]
        assert "text" in hit
        assert "wing" in hit
        assert "room" in hit
        assert "similarity" in hit
        assert "source_file" in hit

    def test_search_memories_with_filters(self, palace):
        result = search_memories(
            "school",
            palace_path=palace,
            wing="personal",
            room="family",
        )
        assert result["filters"]["wing"] == "personal"
        assert result["filters"]["room"] == "family"

    def test_search_memories_no_palace(self, tmp_path):
        result = search_memories("anything", palace_path=str(tmp_path / "nope"))
        assert "error" in result


# ---------------------------------------------------------------------------
# palace_graph.py tests
# ---------------------------------------------------------------------------


class TestBuildGraph:
    def test_build_graph_nodes(self, palace_with_tunnels):
        client = chromadb.PersistentClient(path=palace_with_tunnels)
        col = client.get_collection("mempalace_drawers")
        nodes, _edges = build_graph(col=col)
        client.close()
        assert "backend" in nodes
        assert "frontend" in nodes
        assert "devops" in nodes
        # backend spans two wings
        assert len(nodes["backend"]["wings"]) == 2
        assert nodes["backend"]["count"] == 2

    def test_build_graph_edges(self, palace_with_tunnels):
        client = chromadb.PersistentClient(path=palace_with_tunnels)
        col = client.get_collection("mempalace_drawers")
        _nodes, edges = build_graph(col=col)
        client.close()
        # backend and frontend each span 2 wings, so edges exist
        assert len(edges) > 0
        rooms_with_edges = {e["room"] for e in edges}
        assert "backend" in rooms_with_edges

    def test_build_graph_no_collection(self):
        nodes, edges = build_graph(col=None, config=None)
        # Falls back to default config which won't have a palace
        # Either returns empty or the real palace; we just check it doesn't crash
        assert isinstance(nodes, dict)
        assert isinstance(edges, list)

    def test_build_graph_single_wing_no_edges(self, palace):
        """Rooms in a single wing should produce no tunnel edges."""
        client = chromadb.PersistentClient(path=palace)
        col = client.get_collection("mempalace_drawers")
        nodes, edges = build_graph(col=col)
        client.close()
        # Only rooms with 2+ wings produce edges
        for edge in edges:
            room = edge["room"]
            assert len(nodes[room]["wings"]) >= 2


class TestTraverse:
    def test_traverse_from_existing_room(self, palace_with_tunnels):
        client = chromadb.PersistentClient(path=palace_with_tunnels)
        col = client.get_collection("mempalace_drawers")
        results = traverse("backend", col=col)
        client.close()
        assert isinstance(results, list)
        assert results[0]["room"] == "backend"
        assert results[0]["hop"] == 0
        # Should find connected rooms
        rooms_found = {r["room"] for r in results}
        assert len(rooms_found) >= 2

    def test_traverse_nonexistent_room(self, palace_with_tunnels):
        client = chromadb.PersistentClient(path=palace_with_tunnels)
        col = client.get_collection("mempalace_drawers")
        result = traverse("nonexistent-room", col=col)
        client.close()
        assert isinstance(result, dict)
        assert "error" in result

    def test_traverse_max_hops(self, palace_with_tunnels):
        client = chromadb.PersistentClient(path=palace_with_tunnels)
        col = client.get_collection("mempalace_drawers")
        results = traverse("devops", col=col, max_hops=1)
        client.close()
        assert isinstance(results, list)
        # All results should be within 1 hop
        for r in results:
            assert r["hop"] <= 1


class TestFindTunnels:
    def test_find_all_tunnels(self, palace_with_tunnels):
        client = chromadb.PersistentClient(path=palace_with_tunnels)
        col = client.get_collection("mempalace_drawers")
        tunnels = find_tunnels(col=col)
        client.close()
        assert len(tunnels) >= 2  # backend and frontend span 2 wings
        for t in tunnels:
            assert len(t["wings"]) >= 2

    def test_find_tunnels_between_wings(self, palace_with_tunnels):
        client = chromadb.PersistentClient(path=palace_with_tunnels)
        col = client.get_collection("mempalace_drawers")
        tunnels = find_tunnels(wing_a="myproject", wing_b="personal", col=col)
        client.close()
        assert len(tunnels) >= 1
        for t in tunnels:
            assert "myproject" in t["wings"]
            assert "personal" in t["wings"]

    def test_find_tunnels_no_match(self, palace_with_tunnels):
        client = chromadb.PersistentClient(path=palace_with_tunnels)
        col = client.get_collection("mempalace_drawers")
        tunnels = find_tunnels(wing_a="nonexistent", col=col)
        client.close()
        assert tunnels == []


class TestGraphStats:
    def test_graph_stats(self, palace_with_tunnels):
        client = chromadb.PersistentClient(path=palace_with_tunnels)
        col = client.get_collection("mempalace_drawers")
        stats = graph_stats(col=col)
        client.close()
        assert stats["total_rooms"] == 3  # backend, frontend, devops
        assert stats["tunnel_rooms"] >= 2  # backend and frontend
        assert stats["total_edges"] >= 1
        assert "rooms_per_wing" in stats
        assert "myproject" in stats["rooms_per_wing"]
        assert "top_tunnels" in stats
