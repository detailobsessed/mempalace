"""Integration tests for mcp_server.py — MCP protocol + tool functions."""

import json

import pytest

from mempalace import mcp_server
from mempalace.config import MempalaceConfig
from mempalace.knowledge_graph import KnowledgeGraph


@pytest.fixture
def mcp_palace(tmp_path, monkeypatch):
    """Set up MCP server with a fresh temp palace + knowledge graph."""
    palace_path = str(tmp_path / "palace")

    config = MempalaceConfig(config_dir=str(tmp_path / "config"))
    config.init()
    monkeypatch.setattr(mcp_server, "_config", config)
    monkeypatch.setattr(config, "_file_config", {"palace_path": palace_path})

    kg = KnowledgeGraph(db_path=str(tmp_path / "kg.sqlite3"))
    monkeypatch.setattr(mcp_server, "_kg", kg)

    # Reset client/collection caches so each test gets a fresh connection
    monkeypatch.setattr(mcp_server, "_client_cache", None)
    monkeypatch.setattr(mcp_server, "_collection_cache", None)

    return palace_path


# ---------------------------------------------------------------------------
# Helper to add a drawer directly via ChromaDB so read-tools have data
# ---------------------------------------------------------------------------


def _seed_drawers(palace_path, items):
    """Add drawers directly to ChromaDB for test setup."""
    import chromadb

    client = chromadb.PersistentClient(path=palace_path)
    col = client.get_or_create_collection("mempalace_drawers")
    for item in items:
        col.add(
            ids=[item["id"]],
            documents=[item["doc"]],
            metadatas=[item["meta"]],
        )
    return col


# ============================= NO-PALACE ERROR =============================


@pytest.mark.parametrize(
    ("tool_fn", "args"),
    [
        (mcp_server.tool_status, ()),
        (mcp_server.tool_list_wings, ()),
        (mcp_server.tool_list_rooms, ()),
        (mcp_server.tool_get_taxonomy, ()),
        (mcp_server.tool_search, ("hello",)),
        (mcp_server.tool_check_duplicate, ("anything",)),
        (mcp_server.tool_traverse_graph, ("some-room",)),
        (mcp_server.tool_find_tunnels, ()),
        (mcp_server.tool_graph_stats, ()),
        (mcp_server.tool_delete_drawer, ("nonexistent",)),
    ],
    ids=[
        "status",
        "list_wings",
        "list_rooms",
        "get_taxonomy",
        "search",
        "check_duplicate",
        "traverse_graph",
        "find_tunnels",
        "graph_stats",
        "delete_drawer",
    ],
)
def test_no_palace_returns_error(mcp_palace, tool_fn, args):
    """All read/graph/delete tools return an error dict when no palace exists."""
    result = tool_fn(*args)
    assert "error" in result


def test_no_palace_status_error_message(mcp_palace):
    """tool_status returns a specific 'No palace found' error message."""
    result = mcp_server.tool_status()
    assert "No palace found" in result["error"]


# ============================= READ TOOLS ==================================


class TestToolStatus:
    def test_with_data(self, mcp_palace):
        _seed_drawers(
            mcp_palace,
            [
                {
                    "id": "d1",
                    "doc": "hello world",
                    "meta": {"wing": "wing_code", "room": "setup"},
                },
                {
                    "id": "d2",
                    "doc": "goodbye world",
                    "meta": {"wing": "wing_code", "room": "teardown"},
                },
                {
                    "id": "d3",
                    "doc": "family note",
                    "meta": {"wing": "wing_user", "room": "family"},
                },
            ],
        )
        result = mcp_server.tool_status()
        assert result["total_drawers"] == 3
        assert result["wings"]["wing_code"] == 2
        assert result["wings"]["wing_user"] == 1
        assert result["rooms"]["setup"] == 1
        assert result["rooms"]["teardown"] == 1
        assert result["rooms"]["family"] == 1
        assert "palace_path" in result
        assert "protocol" in result
        assert "aaak_dialect" in result


class TestToolListWings:
    def test_with_data(self, mcp_palace):
        _seed_drawers(
            mcp_palace,
            [
                {"id": "d1", "doc": "a", "meta": {"wing": "wing_code", "room": "r1"}},
                {"id": "d2", "doc": "b", "meta": {"wing": "wing_code", "room": "r2"}},
                {"id": "d3", "doc": "c", "meta": {"wing": "wing_user", "room": "r1"}},
            ],
        )
        result = mcp_server.tool_list_wings()
        assert result["wings"]["wing_code"] == 2
        assert result["wings"]["wing_user"] == 1


class TestToolListRooms:
    def test_all_rooms(self, mcp_palace):
        _seed_drawers(
            mcp_palace,
            [
                {"id": "d1", "doc": "a", "meta": {"wing": "wing_code", "room": "setup"}},
                {"id": "d2", "doc": "b", "meta": {"wing": "wing_user", "room": "diary"}},
            ],
        )
        result = mcp_server.tool_list_rooms()
        assert result["wing"] == "all"
        assert "setup" in result["rooms"]
        assert "diary" in result["rooms"]

    def test_filtered_by_wing(self, mcp_palace):
        _seed_drawers(
            mcp_palace,
            [
                {"id": "d1", "doc": "a", "meta": {"wing": "wing_code", "room": "setup"}},
                {"id": "d2", "doc": "b", "meta": {"wing": "wing_user", "room": "diary"}},
            ],
        )
        result = mcp_server.tool_list_rooms(wing="wing_code")
        assert result["wing"] == "wing_code"
        assert "setup" in result["rooms"]
        assert "diary" not in result["rooms"]


class TestToolGetTaxonomy:
    def test_with_data(self, mcp_palace):
        _seed_drawers(
            mcp_palace,
            [
                {"id": "d1", "doc": "a", "meta": {"wing": "wing_code", "room": "setup"}},
                {"id": "d2", "doc": "b", "meta": {"wing": "wing_code", "room": "setup"}},
                {"id": "d3", "doc": "c", "meta": {"wing": "wing_user", "room": "diary"}},
            ],
        )
        result = mcp_server.tool_get_taxonomy()
        assert result["taxonomy"]["wing_code"]["setup"] == 2
        assert result["taxonomy"]["wing_user"]["diary"] == 1


class TestToolSearch:
    def test_search_returns_results(self, mcp_palace):
        _seed_drawers(
            mcp_palace,
            [
                {
                    "id": "d1",
                    "doc": "Python is a great programming language",
                    "meta": {"wing": "wing_code", "room": "python"},
                },
            ],
        )
        result = mcp_server.tool_search("python programming")
        assert "results" in result
        assert len(result["results"]) >= 1


class TestToolCheckDuplicate:
    def test_no_duplicate(self, mcp_palace):
        _seed_drawers(
            mcp_palace,
            [
                {
                    "id": "d1",
                    "doc": "The sky is blue on a clear day",
                    "meta": {"wing": "wing_code", "room": "r1"},
                },
            ],
        )
        result = mcp_server.tool_check_duplicate("Completely unrelated content about quantum physics")
        # With a high threshold, dissimilar content should not match
        assert "is_duplicate" in result

    def test_exact_duplicate(self, mcp_palace):
        content = "This is exact duplicate content for testing purposes"
        _seed_drawers(
            mcp_palace,
            [
                {
                    "id": "d1",
                    "doc": content,
                    "meta": {"wing": "wing_code", "room": "r1"},
                },
            ],
        )
        result = mcp_server.tool_check_duplicate(content, threshold=0.5)
        assert result["is_duplicate"] is True
        assert len(result["matches"]) >= 1
        assert result["matches"][0]["id"] == "d1"


class TestToolGetAaakSpec:
    def test_returns_spec(self, mcp_palace):
        result = mcp_server.tool_get_aaak_spec()
        assert "aaak_spec" in result
        assert "AAAK" in result["aaak_spec"]
        assert "FORMAT" in result["aaak_spec"]


# ============================= GRAPH TOOLS =================================


class TestToolTraverseGraph:
    def test_with_data(self, mcp_palace):
        _seed_drawers(
            mcp_palace,
            [
                {"id": "d1", "doc": "a", "meta": {"wing": "wing_code", "room": "setup"}},
                {"id": "d2", "doc": "b", "meta": {"wing": "wing_user", "room": "setup"}},
            ],
        )
        result = mcp_server.tool_traverse_graph("setup")
        # Returns a list of traversal nodes
        assert isinstance(result, list)
        assert len(result) >= 1
        assert result[0]["room"] == "setup"


class TestToolFindTunnels:
    def test_with_data(self, mcp_palace):
        _seed_drawers(
            mcp_palace,
            [
                {"id": "d1", "doc": "a", "meta": {"wing": "wing_code", "room": "shared-room"}},
                {"id": "d2", "doc": "b", "meta": {"wing": "wing_user", "room": "shared-room"}},
            ],
        )
        result = mcp_server.tool_find_tunnels(wing_a="wing_code", wing_b="wing_user")
        assert isinstance(result, list)
        assert len(result) >= 1
        assert result[0]["room"] == "shared-room"


class TestToolGraphStats:
    def test_with_data(self, mcp_palace):
        _seed_drawers(
            mcp_palace,
            [
                {"id": "d1", "doc": "a", "meta": {"wing": "wing_code", "room": "r1"}},
            ],
        )
        result = mcp_server.tool_graph_stats()
        assert isinstance(result, dict)


# ============================= WRITE TOOLS =================================


class TestToolAddDrawer:
    def test_add_success(self, mcp_palace):
        result = mcp_server.tool_add_drawer("wing_code", "setup", "New drawer content")
        assert result["success"] is True
        assert "drawer_id" in result
        assert result["wing"] == "wing_code"
        assert result["room"] == "setup"

    def test_add_duplicate_blocked(self, mcp_palace):
        content = "Exact same content for duplicate test"
        r1 = mcp_server.tool_add_drawer("wing_code", "r1", content)
        assert r1["success"] is True

        r2 = mcp_server.tool_add_drawer("wing_code", "r1", content)
        assert r2["success"] is False
        assert r2["reason"] == "duplicate"

    def test_add_with_source_file(self, mcp_palace):
        result = mcp_server.tool_add_drawer("wing_code", "setup", "Content from a file", source_file="test.py")
        assert result["success"] is True

    def test_add_with_added_by(self, mcp_palace):
        result = mcp_server.tool_add_drawer("wing_code", "setup", "Agent-added content", added_by="test_agent")
        assert result["success"] is True


class TestToolDeleteDrawer:
    def test_delete_nonexistent(self, mcp_palace):
        _seed_drawers(
            mcp_palace,
            [{"id": "d1", "doc": "x", "meta": {"wing": "w", "room": "r"}}],
        )
        result = mcp_server.tool_delete_drawer("nonexistent_id")
        assert result["success"] is False
        assert "not found" in result["error"].lower()

    def test_delete_success(self, mcp_palace):
        _seed_drawers(
            mcp_palace,
            [{"id": "d1", "doc": "to delete", "meta": {"wing": "w", "room": "r"}}],
        )
        result = mcp_server.tool_delete_drawer("d1")
        assert result["success"] is True
        assert result["drawer_id"] == "d1"


# ============================= KNOWLEDGE GRAPH =============================


class TestToolKgAdd:
    def test_add_triple(self, mcp_palace):
        result = mcp_server.tool_kg_add("Max", "loves", "chess")
        assert result["success"] is True
        assert "triple_id" in result
        assert result["fact"] == "Max \u2192 loves \u2192 chess"

    def test_add_with_valid_from(self, mcp_palace):
        result = mcp_server.tool_kg_add("Max", "started", "swimming", valid_from="2025-01-01")
        assert result["success"] is True


class TestToolKgQuery:
    def test_query_empty(self, mcp_palace):
        result = mcp_server.tool_kg_query("Nobody")
        assert result["entity"] == "Nobody"
        assert result["count"] == 0
        assert result["facts"] == []

    def test_query_after_add(self, mcp_palace):
        mcp_server.tool_kg_add("Alice", "parent_of", "Max")
        result = mcp_server.tool_kg_query("Alice")
        assert result["count"] >= 1
        facts = result["facts"]
        predicates = [f["predicate"] for f in facts]
        assert "parent_of" in predicates

    def test_query_with_direction(self, mcp_palace):
        mcp_server.tool_kg_add("Alice", "parent_of", "Max")
        result = mcp_server.tool_kg_query("Max", direction="incoming")
        assert result["count"] >= 1

    def test_query_with_as_of(self, mcp_palace):
        mcp_server.tool_kg_add("Max", "does", "swimming", valid_from="2025-01-01")
        result = mcp_server.tool_kg_query("Max", as_of="2025-06-01")
        assert result["count"] >= 1


class TestToolKgInvalidate:
    def test_invalidate(self, mcp_palace):
        mcp_server.tool_kg_add("Max", "has_issue", "ankle_injury")
        result = mcp_server.tool_kg_invalidate("Max", "has_issue", "ankle_injury", ended="2026-02-15")
        assert result["success"] is True
        assert result["ended"] == "2026-02-15"

    def test_invalidate_default_ended(self, mcp_palace):
        mcp_server.tool_kg_add("Max", "attends", "school_x")
        result = mcp_server.tool_kg_invalidate("Max", "attends", "school_x")
        assert result["success"] is True
        assert result["ended"] == "today"


class TestToolKgTimeline:
    def test_empty_timeline(self, mcp_palace):
        result = mcp_server.tool_kg_timeline()
        assert result["entity"] == "all"
        assert result["count"] == 0

    def test_entity_timeline(self, mcp_palace):
        mcp_server.tool_kg_add("Max", "loves", "chess", valid_from="2025-01-01")
        mcp_server.tool_kg_add("Max", "does", "swimming", valid_from="2025-06-01")
        result = mcp_server.tool_kg_timeline(entity="Max")
        assert result["entity"] == "Max"
        assert result["count"] == 2

    def test_full_timeline(self, mcp_palace):
        mcp_server.tool_kg_add("Alice", "parent_of", "Max")
        mcp_server.tool_kg_add("Max", "loves", "chess")
        result = mcp_server.tool_kg_timeline()
        assert result["entity"] == "all"
        assert result["count"] >= 2


class TestToolKgStats:
    def test_empty_stats(self, mcp_palace):
        result = mcp_server.tool_kg_stats()
        assert result["entities"] == 0
        assert result["triples"] == 0

    def test_stats_after_adds(self, mcp_palace):
        mcp_server.tool_kg_add("Alice", "parent_of", "Max")
        mcp_server.tool_kg_add("Max", "loves", "chess")
        result = mcp_server.tool_kg_stats()
        assert result["entities"] >= 3  # Alice, Max, chess
        assert result["triples"] == 2
        assert result["current_facts"] == 2
        assert result["expired_facts"] == 0


# ============================= DIARY TOOLS =================================


class TestToolDiaryWrite:
    def test_write_entry(self, mcp_palace):
        result = mcp_server.tool_diary_write("Claude", "SESSION:2026-04-04|test.entry")
        assert result["success"] is True
        assert "entry_id" in result
        assert result["agent"] == "Claude"
        assert result["topic"] == "general"

    def test_write_with_topic(self, mcp_palace):
        result = mcp_server.tool_diary_write("Claude", "worked on tests", topic="testing")
        assert result["success"] is True
        assert result["topic"] == "testing"

    def test_wing_name_normalization(self, mcp_palace):
        result = mcp_server.tool_diary_write("My Agent", "entry text")
        assert result["success"] is True
        assert "entry_id" in result
        # Wing should be wing_my_agent (lowered, spaces to underscores)
        assert "wing_my_agent" in result["entry_id"]


class TestToolDiaryRead:
    def test_no_palace_returns_error_or_empty(self, mcp_palace):
        """diary_read may return entries (empty) even with no palace."""
        result = mcp_server.tool_diary_read("Claude")
        assert "error" in result or "entries" in result

    def test_read_empty(self, mcp_palace):
        # Create a collection first so it doesn't return "no palace"
        _seed_drawers(
            mcp_palace,
            [{"id": "d1", "doc": "x", "meta": {"wing": "w", "room": "r"}}],
        )
        result = mcp_server.tool_diary_read("Claude")
        assert result["entries"] == []
        assert "No diary entries yet" in result["message"]

    def test_read_after_write(self, mcp_palace):
        mcp_server.tool_diary_write("Claude", "First entry")
        mcp_server.tool_diary_write("Claude", "Second entry")
        result = mcp_server.tool_diary_read("Claude")
        assert result["agent"] == "Claude"
        assert result["total"] == 2
        assert result["showing"] == 2
        assert len(result["entries"]) == 2

    def test_read_last_n(self, mcp_palace):
        for i in range(5):
            mcp_server.tool_diary_write("Claude", f"Entry {i}")
        result = mcp_server.tool_diary_read("Claude", last_n=3)
        assert result["showing"] == 3
        assert result["total"] == 5


# ============================= HANDLE_REQUEST ==============================


class TestHandleRequest:
    def test_initialize(self, mcp_palace):
        resp = mcp_server.handle_request({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
        assert resp["jsonrpc"] == "2.0"
        assert resp["id"] == 1
        result = resp["result"]
        assert result["protocolVersion"] == "2024-11-05"
        assert result["serverInfo"]["name"] == "mempalace"
        assert "tools" in result["capabilities"]

    def test_notifications_initialized(self, mcp_palace):
        resp = mcp_server.handle_request({"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}})
        assert resp is None

    def test_tools_list(self, mcp_palace):
        resp = mcp_server.handle_request({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
        assert resp["id"] == 2
        tools = resp["result"]["tools"]
        assert isinstance(tools, list)
        tool_names = [t["name"] for t in tools]
        assert "mempalace_status" in tool_names
        assert "mempalace_search" in tool_names
        assert "mempalace_add_drawer" in tool_names
        assert "mempalace_kg_add" in tool_names
        assert "mempalace_diary_write" in tool_names
        # Each tool should have name, description, inputSchema
        for t in tools:
            assert "name" in t
            assert "description" in t
            assert "inputSchema" in t

    def test_tools_call_status(self, mcp_palace):
        _seed_drawers(
            mcp_palace,
            [{"id": "d1", "doc": "x", "meta": {"wing": "w", "room": "r"}}],
        )
        resp = mcp_server.handle_request({
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {"name": "mempalace_status", "arguments": {}},
        })
        assert resp["id"] == 3
        content = resp["result"]["content"]
        assert len(content) == 1
        assert content[0]["type"] == "text"
        data = json.loads(content[0]["text"])
        assert data["total_drawers"] == 1

    def test_tools_call_kg_add(self, mcp_palace):
        resp = mcp_server.handle_request({
            "jsonrpc": "2.0",
            "id": 4,
            "method": "tools/call",
            "params": {
                "name": "mempalace_kg_add",
                "arguments": {
                    "subject": "Alice",
                    "predicate": "parent_of",
                    "object": "Max",
                },
            },
        })
        assert resp["id"] == 4
        data = json.loads(resp["result"]["content"][0]["text"])
        assert data["success"] is True

    def test_tools_call_unknown_tool(self, mcp_palace):
        resp = mcp_server.handle_request({
            "jsonrpc": "2.0",
            "id": 5,
            "method": "tools/call",
            "params": {"name": "nonexistent_tool", "arguments": {}},
        })
        assert resp["id"] == 5
        assert "error" in resp
        assert resp["error"]["code"] == -32601
        assert "Unknown tool" in resp["error"]["message"]

    def test_tools_call_with_error(self, mcp_palace):
        # Calling search without required 'query' arg should trigger error
        resp = mcp_server.handle_request({
            "jsonrpc": "2.0",
            "id": 6,
            "method": "tools/call",
            "params": {"name": "mempalace_search", "arguments": {}},
        })
        assert resp["id"] == 6
        assert "error" in resp
        assert resp["error"]["code"] == -32000

    def test_unknown_method(self, mcp_palace):
        resp = mcp_server.handle_request({"jsonrpc": "2.0", "id": 7, "method": "bogus/method", "params": {}})
        assert resp["id"] == 7
        assert "error" in resp
        assert resp["error"]["code"] == -32601
        assert "Unknown method" in resp["error"]["message"]

    def test_tools_call_add_drawer(self, mcp_palace):
        resp = mcp_server.handle_request({
            "jsonrpc": "2.0",
            "id": 8,
            "method": "tools/call",
            "params": {
                "name": "mempalace_add_drawer",
                "arguments": {
                    "wing": "wing_test",
                    "room": "integration",
                    "content": "Added via handle_request",
                },
            },
        })
        data = json.loads(resp["result"]["content"][0]["text"])
        assert data["success"] is True
        assert data["wing"] == "wing_test"

    def test_tools_call_get_aaak_spec(self, mcp_palace):
        resp = mcp_server.handle_request({
            "jsonrpc": "2.0",
            "id": 9,
            "method": "tools/call",
            "params": {"name": "mempalace_get_aaak_spec", "arguments": {}},
        })
        data = json.loads(resp["result"]["content"][0]["text"])
        assert "aaak_spec" in data

    def test_missing_id(self, mcp_palace):
        resp = mcp_server.handle_request({"jsonrpc": "2.0", "method": "initialize", "params": {}})
        assert resp["id"] is None
        assert "result" in resp

    def test_missing_params(self, mcp_palace):
        resp = mcp_server.handle_request({"jsonrpc": "2.0", "id": 10, "method": "initialize"})
        assert resp["id"] == 10
        assert "result" in resp

    def test_type_coercion_integer_as_string(self, mcp_palace):
        """Lines 763-764: MCP sends limit as string '3' instead of int 3."""
        _seed_drawers(
            mcp_palace,
            [{"id": "d1", "doc": "Python testing", "meta": {"wing": "wing_code", "room": "tests"}}],
        )
        resp = mcp_server.handle_request({
            "jsonrpc": "2.0",
            "id": 20,
            "method": "tools/call",
            "params": {
                "name": "mempalace_search",
                "arguments": {"query": "python", "limit": "3"},
            },
        })
        assert resp["id"] == 20
        assert "result" in resp
        data = json.loads(resp["result"]["content"][0]["text"])
        # Should succeed — limit was coerced from "3" to 3
        assert "results" in data or "error" in data

    def test_type_coercion_number_as_string(self, mcp_palace):
        """Lines 765-766: MCP sends threshold as string '0.5' instead of float 0.5."""
        _seed_drawers(
            mcp_palace,
            [{"id": "d1", "doc": "duplicate check", "meta": {"wing": "wing_code", "room": "r1"}}],
        )
        resp = mcp_server.handle_request({
            "jsonrpc": "2.0",
            "id": 21,
            "method": "tools/call",
            "params": {
                "name": "mempalace_check_duplicate",
                "arguments": {"content": "duplicate check", "threshold": "0.5"},
            },
        })
        assert resp["id"] == 21
        assert "result" in resp
        data = json.loads(resp["result"]["content"][0]["text"])
        assert "is_duplicate" in data

    def test_tool_handler_exception(self, mcp_palace):
        """Lines 774-780: tool handler raises an unexpected exception."""
        original_handler = mcp_server.TOOLS["mempalace_status"]["handler"]
        try:
            mcp_server.TOOLS["mempalace_status"]["handler"] = lambda: (_ for _ in ()).throw(RuntimeError("boom"))
            resp = mcp_server.handle_request({
                "jsonrpc": "2.0",
                "id": 22,
                "method": "tools/call",
                "params": {"name": "mempalace_status", "arguments": {}},
            })
            assert resp["id"] == 22
            assert "error" in resp
            assert resp["error"]["code"] == -32000
            assert "Internal tool error" in resp["error"]["message"]
        finally:
            mcp_server.TOOLS["mempalace_status"]["handler"] = original_handler


# ==================== METADATA SCAN ERROR PATHS ============================


class TestMetadataScanErrors:
    """Cover the except:pass blocks in tool_status, tool_list_wings,
    tool_list_rooms, and tool_get_taxonomy (lines 80-81, 135-136, 157-158, 175-176)."""

    @staticmethod
    def _patch_collection_get(mcp_palace, monkeypatch):
        """Patch _get_collection to return a collection whose .get() raises."""
        # Seed data so the collection exists
        _seed_drawers(
            mcp_palace,
            [{"id": "d1", "doc": "x", "meta": {"wing": "w", "room": "r"}}],
        )
        original_get_collection = mcp_server._get_collection

        def patched(create=False):
            col = original_get_collection(create=create)
            if col is None:
                return None

            def broken_get(*_args, **_kwargs):
                msg = "ChromaDB metadata scan failed"
                raise RuntimeError(msg)

            col.get = broken_get
            return col

        monkeypatch.setattr(mcp_server, "_get_collection", patched)

    def test_status_metadata_error(self, mcp_palace, monkeypatch):
        self._patch_collection_get(mcp_palace, monkeypatch)
        result = mcp_server.tool_status()
        # count() still works; metadata scan fails silently → empty wings/rooms
        assert result["total_drawers"] == 1
        assert result["wings"] == {}
        assert result["rooms"] == {}

    def test_list_wings_metadata_error(self, mcp_palace, monkeypatch):
        self._patch_collection_get(mcp_palace, monkeypatch)
        result = mcp_server.tool_list_wings()
        assert result["wings"] == {}

    def test_list_rooms_metadata_error(self, mcp_palace, monkeypatch):
        self._patch_collection_get(mcp_palace, monkeypatch)
        result = mcp_server.tool_list_rooms()
        assert result["wing"] == "all"
        assert result["rooms"] == {}

    def test_get_taxonomy_metadata_error(self, mcp_palace, monkeypatch):
        self._patch_collection_get(mcp_palace, monkeypatch)
        result = mcp_server.tool_get_taxonomy()
        assert result["taxonomy"] == {}


# ==================== WRITE TOOL ERROR PATHS ===============================


class TestWriteToolErrors:
    """Cover error branches in tool_add_drawer and tool_delete_drawer
    (lines 263, 295-296, 312-313)."""

    def test_add_drawer_chromadb_error(self, mcp_palace, monkeypatch):
        """Lines 295-296: col.add() raises an exception."""
        # Create a palace so _get_collection works
        _seed_drawers(
            mcp_palace,
            [{"id": "d1", "doc": "seed", "meta": {"wing": "wing_code", "room": "r1"}}],
        )
        original_get_collection = mcp_server._get_collection

        def patched_get_collection(create=False):
            col = original_get_collection(create=create)
            if col is None:
                return None

            def broken_upsert(*_args, **_kwargs):
                msg = "ChromaDB upsert failed"
                raise RuntimeError(msg)

            col.upsert = broken_upsert
            return col

        monkeypatch.setattr(mcp_server, "_get_collection", patched_get_collection)
        result = mcp_server.tool_add_drawer("wing_code", "newroom", "unique content that won't duplicate")
        assert result["success"] is False
        assert "ChromaDB upsert failed" in result["error"]

    def test_delete_drawer_chromadb_error(self, mcp_palace, monkeypatch):
        """Lines 312-313: col.delete() raises an exception."""
        _seed_drawers(
            mcp_palace,
            [{"id": "d1", "doc": "to delete", "meta": {"wing": "w", "room": "r"}}],
        )
        original_get_collection = mcp_server._get_collection

        def patched_get_collection(create=False):
            col = original_get_collection(create=create)
            if col is None:
                return None

            def broken_delete(*_args, **_kwargs):
                msg = "ChromaDB delete failed"
                raise RuntimeError(msg)

            col.delete = broken_delete
            return col

        monkeypatch.setattr(mcp_server, "_get_collection", patched_get_collection)
        result = mcp_server.tool_delete_drawer("d1")
        assert result["success"] is False
        assert "ChromaDB delete failed" in result["error"]

    def test_add_drawer_no_collection(self, mcp_palace, monkeypatch):
        """Line 263: _get_collection(create=True) returns None."""
        monkeypatch.setattr(mcp_server, "_get_collection", lambda create=False: None)  # noqa: ARG005
        result = mcp_server.tool_add_drawer("wing_code", "r1", "content")
        assert "error" in result
        assert "No palace found" in result["error"]


# ==================== DIARY READ ERROR PATH ================================


class TestDiaryReadError:
    """Cover the except branch in tool_diary_read (lines 443-444)."""

    def test_diary_read_chromadb_error(self, mcp_palace, monkeypatch):
        _seed_drawers(
            mcp_palace,
            [{"id": "d1", "doc": "seed", "meta": {"wing": "wing_claude", "room": "diary"}}],
        )
        original_get_collection = mcp_server._get_collection

        def patched_get_collection(create=False):
            col = original_get_collection(create=create)
            if col is None:
                return None

            def broken_get(*_args, **_kwargs):
                msg = "ChromaDB diary read failed"
                raise RuntimeError(msg)

            col.get = broken_get
            return col

        monkeypatch.setattr(mcp_server, "_get_collection", patched_get_collection)
        result = mcp_server.tool_diary_read("Claude")
        assert "error" in result
        assert "ChromaDB diary read failed" in result["error"]


# ========================== HEALTH CHECK ==================================


class TestHealthCheck:
    """Tests for _health_check() warnings surfaced via tool_status()."""

    def test_no_palace_warning(self, mcp_palace):
        """No palace → critical no_palace warning."""
        warnings = mcp_server._health_check()
        checks = {w["check"] for w in warnings}
        assert "no_palace" in checks
        critical = [w for w in warnings if w["check"] == "no_palace"]
        assert critical[0]["level"] == "critical"

    def test_no_identity_warning(self, mcp_palace, tmp_path):
        """Palace exists but no identity.txt → warning."""
        _seed_drawers(mcp_palace, [{"id": "d1", "doc": "hello", "meta": {"wing": "w", "room": "r"}}])
        # Reset collection cache so it picks up the seeded data
        mcp_server._collection_cache = None
        warnings = mcp_server._health_check()
        checks = {w["check"] for w in warnings}
        assert "no_identity" in checks
        assert "no_palace" not in checks

    def test_no_project_config_warning(self, mcp_palace, tmp_path, monkeypatch):
        """No mempalace.yaml in CWD → info warning."""
        _seed_drawers(mcp_palace, [{"id": "d1", "doc": "hello", "meta": {"wing": "w", "room": "r"}}])
        mcp_server._collection_cache = None
        # CWD is tmp_path which has no mempalace.yaml
        monkeypatch.chdir(tmp_path)
        warnings = mcp_server._health_check()
        checks = {w["check"] for w in warnings}
        assert "no_project_config" in checks

    def test_empty_palace_warning(self, mcp_palace, monkeypatch):
        """Palace exists but empty → warning."""
        import chromadb

        # Create empty collection
        client = chromadb.PersistentClient(path=mcp_palace)
        client.get_or_create_collection("mempalace_drawers")
        mcp_server._collection_cache = None
        mcp_server._client_cache = None
        warnings = mcp_server._health_check()
        checks = {w["check"] for w in warnings}
        assert "empty_palace" in checks
        assert "no_palace" not in checks

    def test_all_good_no_warnings(self, mcp_palace, tmp_path, monkeypatch):
        """Everything configured → no warnings."""
        _seed_drawers(mcp_palace, [{"id": "d1", "doc": "hello", "meta": {"wing": "w", "room": "r"}}])
        mcp_server._collection_cache = None
        # Create identity.txt
        identity = mcp_server._config._config_dir / "identity.txt"
        identity.write_text("I am a test user", encoding="utf-8")
        # Create mempalace.yaml in CWD
        monkeypatch.chdir(tmp_path)
        (tmp_path / "mempalace.yaml").write_text("wing: test\nrooms: []", encoding="utf-8")
        warnings = mcp_server._health_check()
        assert warnings == []

    def test_status_includes_warnings_key(self, mcp_palace):
        """tool_status() always includes a warnings key."""
        result = mcp_server.tool_status()
        assert "warnings" in result

    def test_status_with_data_includes_warnings(self, mcp_palace):
        """tool_status() with data still includes warnings key."""
        _seed_drawers(mcp_palace, [{"id": "d1", "doc": "hello", "meta": {"wing": "w", "room": "r"}}])
        mcp_server._collection_cache = None
        result = mcp_server.tool_status()
        assert "warnings" in result
        assert "total_drawers" in result
