"""Tests for miner.py — file chunking and room detection."""

from mempalace.miner import chunk_text, detect_room, scan_project


class TestChunkText:
    def test_short_text_single_chunk(self):
        chunks = chunk_text("Hello world, this is a test of chunking.", "test.txt")
        assert len(chunks) == 0  # Below MIN_CHUNK_SIZE (50)

    def test_above_min_size(self):
        text = "A" * 60
        chunks = chunk_text(text, "test.txt")
        assert len(chunks) == 1
        assert chunks[0]["chunk_index"] == 0

    def test_long_text_multiple_chunks(self):
        text = "word " * 500  # ~2500 chars, should split into multiple chunks
        chunks = chunk_text(text, "test.txt")
        assert len(chunks) > 1
        # Indices should be sequential
        for i, chunk in enumerate(chunks):
            assert chunk["chunk_index"] == i

    def test_empty_text(self):
        chunks = chunk_text("", "test.txt")
        assert chunks == []

    def test_whitespace_only(self):
        chunks = chunk_text("   \n\n   ", "test.txt")
        assert chunks == []

    def test_paragraph_boundary_splitting(self):
        para1 = "First paragraph. " * 30
        para2 = "Second paragraph. " * 30
        text = para1 + "\n\n" + para2
        chunks = chunk_text(text, "test.txt")
        assert len(chunks) >= 2


class TestDetectRoom:
    def _make_rooms(self):
        return [
            {"name": "backend", "keywords": ["api", "server", "database"]},
            {"name": "frontend", "keywords": ["react", "component", "ui"]},
            {"name": "general", "keywords": []},
        ]

    def test_folder_path_match(self, tmp_path):
        backend_dir = tmp_path / "backend"
        backend_dir.mkdir()
        filepath = backend_dir / "app.py"
        filepath.touch()
        rooms = self._make_rooms()
        room = detect_room(filepath, "some content", rooms, tmp_path)
        assert room == "backend"

    def test_filename_match(self, tmp_path):
        filepath = tmp_path / "backend_utils.py"
        filepath.touch()
        rooms = self._make_rooms()
        room = detect_room(filepath, "some content", rooms, tmp_path)
        assert room == "backend"

    def test_keyword_scoring(self, tmp_path):
        filepath = tmp_path / "misc.py"
        filepath.touch()
        rooms = self._make_rooms()
        content = "This file sets up the api server and database connection pool"
        room = detect_room(filepath, content, rooms, tmp_path)
        assert room == "backend"

    def test_fallback_to_general(self, tmp_path):
        filepath = tmp_path / "random.txt"
        filepath.touch()
        rooms = self._make_rooms()
        room = detect_room(filepath, "nothing relevant here", rooms, tmp_path)
        assert room == "general"


class TestScanProject:
    def test_finds_readable_files(self, tmp_path):
        (tmp_path / "app.py").write_text("print('hello')")
        (tmp_path / "notes.md").write_text("# Notes")
        (tmp_path / "image.png").write_bytes(b"\x89PNG")
        files = scan_project(str(tmp_path))
        extensions = {f.suffix for f in files}
        assert ".py" in extensions
        assert ".md" in extensions
        assert ".png" not in extensions

    def test_skips_git_dir(self, tmp_path):
        git_dir = tmp_path / ".git"
        git_dir.mkdir()
        (git_dir / "config.py").write_text("x = 1")
        (tmp_path / "app.py").write_text("print('hello')")
        files = scan_project(str(tmp_path))
        assert all(".git" not in str(f) for f in files)

    def test_skips_config_files(self, tmp_path):
        (tmp_path / "mempalace.yaml").write_text("wing: test")
        (tmp_path / ".gitignore").write_text("*.pyc")
        (tmp_path / "app.py").write_text("print('hello')")
        files = scan_project(str(tmp_path))
        names = {f.name for f in files}
        assert "mempalace.yaml" not in names
        assert ".gitignore" not in names
        assert "app.py" in names
