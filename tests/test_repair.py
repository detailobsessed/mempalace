"""Tests for repair.py — scan, prune, rebuild."""

from pathlib import Path

import chromadb

from mempalace.repair import (
    COLLECTION_NAME,
    _backup_sqlite,
    _delete_ids,
    _extract_all_drawers,
    _paginate_ids,
    _probe_ids,
    _refile_drawers,
    prune_corrupt,
    rebuild_index,
    scan_palace,
)


class TestPaginateIds:
    def test_empty_collection(self, palace_path):
        client = chromadb.PersistentClient(path=palace_path)
        col = client.get_or_create_collection(COLLECTION_NAME)
        assert _paginate_ids(col) == []
        client.close()

    def test_returns_all_ids(self, palace_path):
        client = chromadb.PersistentClient(path=palace_path)
        col = client.get_or_create_collection(COLLECTION_NAME)
        col.add(
            ids=[f"id_{i}" for i in range(5)],
            documents=[f"doc {i}" for i in range(5)],
        )
        ids = _paginate_ids(col)
        assert len(ids) == 5
        client.close()


class TestProbeIds:
    def test_all_good_ids(self, palace_path):
        client = chromadb.PersistentClient(path=palace_path)
        col = client.get_or_create_collection(COLLECTION_NAME)
        col.add(ids=["a", "b"], documents=["doc a", "doc b"])
        good, bad = _probe_ids(col, ["a", "b"], 0.0)
        assert good == {"a", "b"}
        assert bad == set()
        client.close()


class TestDeleteIds:
    def test_deletes_existing_ids(self, palace_path):
        client = chromadb.PersistentClient(path=palace_path)
        col = client.get_or_create_collection(COLLECTION_NAME)
        col.add(ids=["a", "b", "c"], documents=["d1", "d2", "d3"])
        deleted, failed = _delete_ids(col, ["a", "b"])
        assert deleted == 2
        assert failed == 0
        assert col.count() == 1
        client.close()


class TestExtractAllDrawers:
    def test_extracts_all(self, palace_path):
        client = chromadb.PersistentClient(path=palace_path)
        col = client.get_or_create_collection(COLLECTION_NAME)
        col.add(
            ids=["d1", "d2"],
            documents=["content one", "content two"],
            metadatas=[{"wing": "a"}, {"wing": "b"}],
        )
        ids, docs, metas = _extract_all_drawers(col, col.count())
        assert len(ids) == 2
        assert "content one" in docs
        assert any(m.get("wing") == "a" for m in metas)
        client.close()


class TestBackupSqlite:
    def test_backup_creates_file(self, palace_path):
        palace = Path(palace_path)
        sqlite = palace / "chroma.sqlite3"
        sqlite.write_text("fake db", encoding="utf-8")
        _backup_sqlite(palace)
        backup = palace / "chroma.sqlite3.backup"
        assert backup.exists()
        assert backup.read_text(encoding="utf-8") == "fake db"

    def test_backup_no_sqlite(self, tmp_path):
        _backup_sqlite(tmp_path)  # should not raise


class TestRefilDrawers:
    def test_refile_creates_new_collection(self, palace_path):
        client = chromadb.PersistentClient(path=palace_path)
        client.get_or_create_collection(COLLECTION_NAME)
        _refile_drawers(client, ["d1"], ["doc one"], [{"wing": "w"}])
        col = client.get_collection(COLLECTION_NAME)
        assert col.count() == 1
        client.close()


class TestScanPalace:
    def test_scan_empty_palace(self, palace_path):
        client = chromadb.PersistentClient(path=palace_path)
        client.get_or_create_collection(COLLECTION_NAME)
        client.close()

        good, bad = scan_palace(palace_path=palace_path)
        assert len(good) == 0
        assert len(bad) == 0

    def test_scan_healthy_palace(self, palace_path):
        client = chromadb.PersistentClient(path=palace_path)
        col = client.get_or_create_collection(COLLECTION_NAME)
        col.add(
            ids=["d1", "d2", "d3"],
            documents=["doc one", "doc two", "doc three"],
            metadatas=[{"wing": "w"}, {"wing": "w"}, {"wing": "w"}],
        )
        client.close()

        good, bad = scan_palace(palace_path=palace_path)
        assert len(good) == 3
        assert len(bad) == 0

    def test_scan_with_wing_filter(self, palace_path):
        client = chromadb.PersistentClient(path=palace_path)
        col = client.get_or_create_collection(COLLECTION_NAME)
        col.add(
            ids=["d1", "d2"],
            documents=["doc one", "doc two"],
            metadatas=[{"wing": "alpha"}, {"wing": "beta"}],
        )
        client.close()

        good, bad = scan_palace(palace_path=palace_path, only_wing="alpha")
        assert len(good) == 1
        assert len(bad) == 0


class TestPruneCorrupt:
    def test_prune_no_file(self, palace_path):
        prune_corrupt(palace_path=palace_path, confirm=True)  # should not raise

    def test_prune_dry_run(self, palace_path):
        bad_file = Path(palace_path) / "corrupt_ids.txt"
        bad_file.write_text("bad_id_1\nbad_id_2\n", encoding="utf-8")
        prune_corrupt(palace_path=palace_path, confirm=False)  # dry run, no crash

    def test_prune_deletes_listed_ids(self, palace_path):
        client = chromadb.PersistentClient(path=palace_path)
        col = client.get_or_create_collection(COLLECTION_NAME)
        col.add(ids=["good", "bad1", "bad2"], documents=["g", "b1", "b2"])
        client.close()

        bad_file = Path(palace_path) / "corrupt_ids.txt"
        bad_file.write_text("bad1\nbad2\n", encoding="utf-8")
        prune_corrupt(palace_path=palace_path, confirm=True)

        client = chromadb.PersistentClient(path=palace_path)
        col = client.get_collection(COLLECTION_NAME)
        assert col.count() == 1
        assert col.get(ids=["good"])["ids"] == ["good"]
        client.close()


class TestRebuildIndex:
    def test_rebuild_preserves_drawers(self, palace_path):
        client = chromadb.PersistentClient(path=palace_path)
        col = client.get_or_create_collection(COLLECTION_NAME)
        col.add(
            ids=["d1", "d2"],
            documents=["content one", "content two"],
            metadatas=[{"wing": "a", "room": "r"}, {"wing": "b", "room": "r"}],
        )
        client.close()

        rebuild_index(palace_path=palace_path)

        client = chromadb.PersistentClient(path=palace_path)
        col = client.get_collection(COLLECTION_NAME)
        assert col.count() == 2
        data = col.get(ids=["d1", "d2"], include=["documents", "metadatas"])
        assert "content one" in data["documents"]
        assert "content two" in data["documents"]
        client.close()

    def test_rebuild_nonexistent_palace(self, tmp_path):
        rebuild_index(palace_path=str(tmp_path / "nonexistent"))

    def test_rebuild_empty_palace(self, palace_path):
        client = chromadb.PersistentClient(path=palace_path)
        client.get_or_create_collection(COLLECTION_NAME)
        client.close()

        rebuild_index(palace_path=palace_path)
