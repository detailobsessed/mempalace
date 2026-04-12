"""Tests for migrate.py — ChromaDB version recovery."""

import sqlite3
from unittest.mock import patch

import chromadb

from mempalace.migrate import (
    detect_chromadb_version,
    extract_drawers_from_sqlite,
    migrate,
)


class TestDetectChromadbVersion:
    def test_unknown_schema(self, tmp_path):
        db_path = str(tmp_path / "test.sqlite3")
        conn = sqlite3.connect(db_path)
        conn.execute("CREATE TABLE foo (id INTEGER)")
        conn.close()
        assert detect_chromadb_version(db_path) == "unknown"

    def test_detects_06x_schema(self, tmp_path):
        db_path = str(tmp_path / "test.sqlite3")
        conn = sqlite3.connect(db_path)
        conn.execute("CREATE TABLE collections (id TEXT, name TEXT)")
        conn.execute("CREATE TABLE embeddings_queue (id INTEGER)")
        conn.close()
        assert detect_chromadb_version(db_path) == "0.6.x"

    def test_detects_1x_schema(self, tmp_path):
        db_path = str(tmp_path / "test.sqlite3")
        conn = sqlite3.connect(db_path)
        conn.execute("CREATE TABLE collections (id TEXT, name TEXT, schema_str TEXT)")
        conn.close()
        assert detect_chromadb_version(db_path) == "1.x"


class TestExtractDrawersFromSqlite:
    def test_empty_db(self, tmp_path):
        db_path = str(tmp_path / "test.sqlite3")
        conn = sqlite3.connect(db_path)
        conn.execute("CREATE TABLE embeddings (id INTEGER PRIMARY KEY, embedding_id TEXT)")
        conn.execute(
            "CREATE TABLE embedding_metadata (id INTEGER, key TEXT, "
            "string_value TEXT, int_value INTEGER, float_value REAL, bool_value INTEGER)"
        )
        conn.close()
        assert extract_drawers_from_sqlite(db_path) == []

    def test_extracts_drawers_with_metadata(self, tmp_path):
        db_path = str(tmp_path / "test.sqlite3")
        conn = sqlite3.connect(db_path)
        conn.execute("CREATE TABLE embeddings (id INTEGER PRIMARY KEY, embedding_id TEXT)")
        conn.execute(
            "CREATE TABLE embedding_metadata (id INTEGER, key TEXT, "
            "string_value TEXT, int_value INTEGER, float_value REAL, bool_value INTEGER)"
        )
        conn.execute("INSERT INTO embeddings VALUES (1, 'drawer_1')")
        conn.execute("INSERT INTO embedding_metadata VALUES (1, 'chroma:document', 'hello world', NULL, NULL, NULL)")
        conn.execute("INSERT INTO embedding_metadata VALUES (1, 'wing', 'test_wing', NULL, NULL, NULL)")
        conn.execute("INSERT INTO embedding_metadata VALUES (1, 'room', 'test_room', NULL, NULL, NULL)")
        conn.execute("INSERT INTO embedding_metadata VALUES (1, 'count', NULL, 42, NULL, NULL)")
        conn.commit()
        conn.close()

        drawers = extract_drawers_from_sqlite(db_path)
        assert len(drawers) == 1
        assert drawers[0]["id"] == "drawer_1"
        assert drawers[0]["document"] == "hello world"
        assert drawers[0]["metadata"]["wing"] == "test_wing"
        assert drawers[0]["metadata"]["room"] == "test_room"
        assert drawers[0]["metadata"]["count"] == 42

    def test_skips_entries_without_document(self, tmp_path):
        db_path = str(tmp_path / "test.sqlite3")
        conn = sqlite3.connect(db_path)
        conn.execute("CREATE TABLE embeddings (id INTEGER PRIMARY KEY, embedding_id TEXT)")
        conn.execute(
            "CREATE TABLE embedding_metadata (id INTEGER, key TEXT, "
            "string_value TEXT, int_value INTEGER, float_value REAL, bool_value INTEGER)"
        )
        conn.execute("INSERT INTO embeddings VALUES (1, 'drawer_1')")
        conn.execute("INSERT INTO embedding_metadata VALUES (1, 'wing', 'test', NULL, NULL, NULL)")
        conn.commit()
        conn.close()

        assert extract_drawers_from_sqlite(db_path) == []


class TestMigrate:
    def test_no_database_file(self, tmp_path, capsys):
        result = migrate(str(tmp_path / "nonexistent"), dry_run=True)
        assert result is False
        assert "No palace database found" in capsys.readouterr().out

    def test_already_readable_palace(self, palace_path, capsys):
        client = chromadb.PersistentClient(path=palace_path)
        col = client.get_or_create_collection("mempalace_drawers")
        col.add(ids=["d1"], documents=["test doc"], metadatas=[{"wing": "w", "room": "r"}])
        client.close()

        result = migrate(palace_path, dry_run=False)
        assert result is True
        assert "No migration needed" in capsys.readouterr().out

    def test_dry_run_shows_summary(self, tmp_path, capsys):
        """Create a palace with raw SQLite that chromadb can't read, then dry-run migrate."""
        palace_dir = tmp_path / "palace"
        palace_dir.mkdir()
        db_path = palace_dir / "chroma.sqlite3"

        conn = sqlite3.connect(str(db_path))
        conn.execute("CREATE TABLE collections (id TEXT, name TEXT)")
        conn.execute("CREATE TABLE embeddings (id INTEGER PRIMARY KEY, embedding_id TEXT)")
        conn.execute(
            "CREATE TABLE embedding_metadata (id INTEGER, key TEXT, "
            "string_value TEXT, int_value INTEGER, float_value REAL, bool_value INTEGER)"
        )
        conn.execute("INSERT INTO embeddings VALUES (1, 'drawer_1')")
        conn.execute("INSERT INTO embedding_metadata VALUES (1, 'chroma:document', 'content here', NULL, NULL, NULL)")
        conn.execute("INSERT INTO embedding_metadata VALUES (1, 'wing', 'wing_test', NULL, NULL, NULL)")
        conn.execute("INSERT INTO embedding_metadata VALUES (1, 'room', 'room_test', NULL, NULL, NULL)")
        conn.commit()
        conn.close()

        result = migrate(str(palace_dir), dry_run=True)
        assert result is True
        output = capsys.readouterr().out
        assert "DRY RUN" in output
        assert "Would migrate 1 drawers" in output

    def test_full_migration_with_mocked_failure(self, tmp_path, capsys):
        """Full migration: create real palace, mock chromadb to fail on read, then migrate."""
        palace_dir = tmp_path / "palace"
        palace_dir.mkdir()

        # Create a real palace with chromadb
        client = chromadb.PersistentClient(path=str(palace_dir))
        col = client.get_or_create_collection("mempalace_drawers")
        for i in range(3):
            col.add(
                ids=[f"drawer_{i}"],
                documents=[f"content {i}"],
                metadatas=[{"wing": "wing_a", "room": "room_b"}],
            )
        client.close()

        # Patch PersistentClient to fail on the readability check but work for reimport
        original = chromadb.PersistentClient
        call_count = 0

        def failing_then_working(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise RuntimeError("Simulated version mismatch")
            return original(*args, **kwargs)

        with patch("chromadb.PersistentClient", side_effect=failing_then_working):
            result = migrate(str(palace_dir), dry_run=False)

        assert result is True
        output = capsys.readouterr().out
        assert "Migration complete" in output
        assert "Drawers migrated: 3" in output

        # Verify the migrated palace is readable
        client = chromadb.PersistentClient(path=str(palace_dir))
        col = client.get_collection("mempalace_drawers")
        assert col.count() == 3
        client.close()

    def test_migration_empty_drawers_with_mocked_failure(self, tmp_path, capsys):
        """Palace chromadb can't read, but no drawers in SQLite."""
        palace_dir = tmp_path / "palace"
        palace_dir.mkdir()

        # Create a real but empty palace
        client = chromadb.PersistentClient(path=str(palace_dir))
        client.get_or_create_collection("mempalace_drawers")
        client.close()

        with patch(
            "chromadb.PersistentClient",
            side_effect=RuntimeError("Simulated version mismatch"),
        ):
            result = migrate(str(palace_dir), dry_run=False)

        assert result is True
        assert "Nothing to migrate" in capsys.readouterr().out

    def test_extracts_float_and_bool_metadata(self, tmp_path):
        """Ensure float and bool metadata types are extracted correctly."""
        db_path = str(tmp_path / "test.sqlite3")
        conn = sqlite3.connect(db_path)
        conn.execute("CREATE TABLE embeddings (id INTEGER PRIMARY KEY, embedding_id TEXT)")
        conn.execute(
            "CREATE TABLE embedding_metadata (id INTEGER, key TEXT, "
            "string_value TEXT, int_value INTEGER, float_value REAL, bool_value INTEGER)"
        )
        conn.execute("INSERT INTO embeddings VALUES (1, 'drawer_1')")
        conn.execute("INSERT INTO embedding_metadata VALUES (1, 'chroma:document', 'doc', NULL, NULL, NULL)")
        conn.execute("INSERT INTO embedding_metadata VALUES (1, 'score', NULL, NULL, 0.95, NULL)")
        conn.execute("INSERT INTO embedding_metadata VALUES (1, 'active', NULL, NULL, NULL, 1)")
        conn.commit()
        conn.close()

        drawers = extract_drawers_from_sqlite(db_path)
        assert len(drawers) == 1
        assert abs(drawers[0]["metadata"]["score"] - 0.95) < 1e-9
        assert drawers[0]["metadata"]["active"] is True
