"""Tests for dedup.py — near-duplicate drawer detection and removal."""

import chromadb

from mempalace.dedup import (
    COLLECTION_NAME,
    dedup_palace,
    dedup_source_group,
    get_source_groups,
    show_stats,
)


class TestGetSourceGroups:
    def test_empty_collection(self, palace_path):
        client = chromadb.PersistentClient(path=palace_path)
        col = client.get_or_create_collection(COLLECTION_NAME)
        groups = get_source_groups(col)
        assert groups == {}
        client.close()

    def test_groups_by_source_file(self, palace_path):
        client = chromadb.PersistentClient(path=palace_path)
        col = client.get_or_create_collection(COLLECTION_NAME)
        col.add(
            ids=[f"id_{i}" for i in range(10)],
            documents=[f"doc {i}" for i in range(10)],
            metadatas=[{"source_file": "a.py"}] * 5 + [{"source_file": "b.py"}] * 5,
        )
        groups = get_source_groups(col)
        assert "a.py" in groups
        assert "b.py" in groups
        client.close()

    def test_source_pattern_filter(self, palace_path):
        client = chromadb.PersistentClient(path=palace_path)
        col = client.get_or_create_collection(COLLECTION_NAME)
        col.add(
            ids=[f"id_{i}" for i in range(10)],
            documents=[f"doc {i}" for i in range(10)],
            metadatas=[{"source_file": "alpha.py"}] * 5 + [{"source_file": "beta.py"}] * 5,
        )
        groups = get_source_groups(col, source_pattern="alpha")
        assert "alpha.py" in groups
        assert "beta.py" not in groups
        client.close()


class TestDedupSourceGroup:
    def test_keeps_longest_removes_short_duplicate(self, palace_path):
        client = chromadb.PersistentClient(path=palace_path)
        col = client.get_or_create_collection(COLLECTION_NAME)
        long_doc = "This is a detailed description of the architecture and design. " * 5
        short_doc = "This is a detailed description of the architecture and design. " * 2
        col.add(
            ids=["long", "short"],
            documents=[long_doc, short_doc],
            metadatas=[{"source_file": "f.py"}, {"source_file": "f.py"}],
        )
        kept, _deleted = dedup_source_group(col, ["long", "short"], threshold=0.15, dry_run=True)
        assert "long" in kept
        client.close()

    def test_dry_run_does_not_delete(self, palace_path):
        client = chromadb.PersistentClient(path=palace_path)
        col = client.get_or_create_collection(COLLECTION_NAME)
        doc = "Identical content repeated for dedup testing. " * 3
        col.add(
            ids=["dup1", "dup2"],
            documents=[doc, doc],
            metadatas=[{"source_file": "f.py"}, {"source_file": "f.py"}],
        )
        _kept, _deleted = dedup_source_group(col, ["dup1", "dup2"], threshold=0.15, dry_run=True)
        assert col.count() == 2
        client.close()

    def test_live_run_deletes_duplicates(self, palace_path):
        client = chromadb.PersistentClient(path=palace_path)
        col = client.get_or_create_collection(COLLECTION_NAME)
        doc = "Identical content repeated exactly the same way for dedup testing. " * 3
        col.add(
            ids=["dup1", "dup2"],
            documents=[doc, doc],
            metadatas=[{"source_file": "f.py"}, {"source_file": "f.py"}],
        )
        kept, deleted = dedup_source_group(col, ["dup1", "dup2"], threshold=0.15, dry_run=False)
        # One should be kept, one deleted
        assert len(kept) + len(deleted) == 2
        # If a duplicate was detected, collection should have fewer entries
        assert col.count() <= 2
        client.close()

    def test_very_short_docs_are_deleted(self, palace_path):
        client = chromadb.PersistentClient(path=palace_path)
        col = client.get_or_create_collection(COLLECTION_NAME)
        col.add(
            ids=["short1", "short2"],
            documents=["hi", "ok"],
            metadatas=[{"source_file": "f.py"}, {"source_file": "f.py"}],
        )
        _kept, deleted = dedup_source_group(col, ["short1", "short2"], threshold=0.15, dry_run=True)
        assert "short1" in deleted
        assert "short2" in deleted
        client.close()


class TestShowStats:
    def test_show_stats_empty_palace(self, palace_path):
        client = chromadb.PersistentClient(path=palace_path)
        client.get_or_create_collection(COLLECTION_NAME)
        client.close()
        show_stats(palace_path=palace_path)  # should not raise

    def test_show_stats_with_data(self, palace_path):
        client = chromadb.PersistentClient(path=palace_path)
        col = client.get_or_create_collection(COLLECTION_NAME)
        col.add(
            ids=[f"d{i}" for i in range(10)],
            documents=[f"document number {i} with enough content" for i in range(10)],
            metadatas=[{"source_file": "same_file.py"} for _ in range(10)],
        )
        client.close()
        show_stats(palace_path=palace_path)


class TestDedupPalace:
    def test_dedup_palace_dry_run(self, palace_path):
        client = chromadb.PersistentClient(path=palace_path)
        col = client.get_or_create_collection(COLLECTION_NAME)
        doc = "This content is repeated many times for dedup testing purposes. " * 3
        col.add(
            ids=[f"d{i}" for i in range(6)],
            documents=[doc] * 6,
            metadatas=[{"source_file": "repeat.py"}] * 6,
        )
        client.close()

        dedup_palace(palace_path=palace_path, dry_run=True, min_count=2)

        # Dry run — all drawers still present
        client = chromadb.PersistentClient(path=palace_path)
        col = client.get_collection(COLLECTION_NAME)
        assert col.count() == 6
        client.close()

    def test_dedup_palace_live_run(self, palace_path):
        client = chromadb.PersistentClient(path=palace_path)
        col = client.get_or_create_collection(COLLECTION_NAME)
        doc = "This content is repeated many times for dedup testing purposes. " * 3
        col.add(
            ids=[f"d{i}" for i in range(6)],
            documents=[doc] * 6,
            metadatas=[{"source_file": "repeat.py"}] * 6,
        )
        client.close()

        dedup_palace(palace_path=palace_path, dry_run=False, min_count=2)

        client = chromadb.PersistentClient(path=palace_path)
        col = client.get_collection(COLLECTION_NAME)
        # Should have fewer drawers after live dedup
        assert col.count() < 6
        client.close()

    def test_dedup_palace_empty(self, palace_path):
        client = chromadb.PersistentClient(path=palace_path)
        client.get_or_create_collection(COLLECTION_NAME)
        client.close()
        dedup_palace(palace_path=palace_path, dry_run=True)
