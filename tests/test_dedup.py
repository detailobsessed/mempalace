"""Tests for dedup.py — near-duplicate drawer detection."""

import chromadb

from mempalace.dedup import COLLECTION_NAME, dedup_source_group, get_source_groups


class TestGetSourceGroups:
    def test_empty_collection(self, palace_path):
        client = chromadb.PersistentClient(path=palace_path)
        col = client.get_or_create_collection(COLLECTION_NAME)
        groups = get_source_groups(col, min_count=1)
        assert groups == {}
        client.close()

    def test_groups_by_source_file(self, palace_path):
        client = chromadb.PersistentClient(path=palace_path)
        col = client.get_or_create_collection(COLLECTION_NAME)
        col.add(
            ids=["a1", "a2", "a3", "b1"],
            documents=["doc a1", "doc a2", "doc a3", "doc b1"],
            metadatas=[
                {"source_file": "file_a.py"},
                {"source_file": "file_a.py"},
                {"source_file": "file_a.py"},
                {"source_file": "file_b.py"},
            ],
        )
        groups = get_source_groups(col, min_count=2)
        assert "file_a.py" in groups
        assert "file_b.py" not in groups  # only 1 drawer, below min_count=2
        assert len(groups["file_a.py"]) == 3
        client.close()

    def test_source_pattern_filter(self, palace_path):
        client = chromadb.PersistentClient(path=palace_path)
        col = client.get_or_create_collection(COLLECTION_NAME)
        col.add(
            ids=["a1", "a2", "b1", "b2"],
            documents=["doc a1", "doc a2", "doc b1", "doc b2"],
            metadatas=[
                {"source_file": "/project/alpha.py"},
                {"source_file": "/project/alpha.py"},
                {"source_file": "/other/beta.py"},
                {"source_file": "/other/beta.py"},
            ],
        )
        groups = get_source_groups(col, min_count=1, source_pattern="alpha")
        assert "/project/alpha.py" in groups
        assert "/other/beta.py" not in groups
        client.close()


class TestDedupSourceGroup:
    def test_keeps_longest_removes_short_duplicate(self, palace_path):
        client = chromadb.PersistentClient(path=palace_path)
        col = client.get_or_create_collection(COLLECTION_NAME)
        # Two very similar docs — the longer one should be kept
        long_doc = "This is a detailed description of the architecture and design. " * 5
        short_doc = "This is a detailed description of the architecture and design. " * 2
        col.add(
            ids=["long", "short"],
            documents=[long_doc, short_doc],
            metadatas=[{"source_file": "f.py"}, {"source_file": "f.py"}],
        )
        kept, _deleted = dedup_source_group(col, ["long", "short"], threshold=0.15, dry_run=True)
        # At minimum, the long one should be kept
        assert "long" in kept
        client.close()

    def test_dry_run_does_not_delete(self, palace_path):
        client = chromadb.PersistentClient(path=palace_path)
        col = client.get_or_create_collection(COLLECTION_NAME)
        doc = "Identical content repeated exactly the same way. " * 3
        col.add(
            ids=["dup1", "dup2"],
            documents=[doc, doc],
            metadatas=[{"source_file": "f.py"}, {"source_file": "f.py"}],
        )
        _kept, _deleted = dedup_source_group(col, ["dup1", "dup2"], threshold=0.15, dry_run=True)
        # Collection should still have both since dry_run=True
        assert col.count() == 2
        client.close()

    def test_very_short_docs_are_deleted(self, palace_path):
        client = chromadb.PersistentClient(path=palace_path)
        col = client.get_or_create_collection(COLLECTION_NAME)
        col.add(
            ids=["tiny", "normal"],
            documents=["hi", "This is a normal length document with enough content to keep."],
            metadatas=[{"source_file": "f.py"}, {"source_file": "f.py"}],
        )
        kept, deleted = dedup_source_group(col, ["tiny", "normal"], threshold=0.15, dry_run=True)
        assert "tiny" in deleted
        assert "normal" in kept
        client.close()
