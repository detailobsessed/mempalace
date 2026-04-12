"""Tests for repair.py — scan, prune, rebuild."""

import chromadb

from mempalace.repair import COLLECTION_NAME, _paginate_ids, rebuild_index, scan_palace


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
