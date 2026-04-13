"""Tests for miner.py — file chunking and room detection."""

from pathlib import Path

from mempalace.miner import (
    GitignoreMatcher,
    add_drawer,
    chunk_text,
    detect_room,
    file_already_mined,
    process_file,
    scan_project,
)


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
        (tmp_path / "app.py").write_text("print('hello')", encoding="utf-8")
        (tmp_path / "notes.md").write_text("# Notes", encoding="utf-8")
        (tmp_path / "image.png").write_bytes(b"\x89PNG")
        files = scan_project(str(tmp_path))
        extensions = {f.suffix for f in files}
        assert ".py" in extensions
        assert ".md" in extensions
        assert ".png" not in extensions

    def test_skips_git_dir(self, tmp_path):
        git_dir = tmp_path / ".git"
        git_dir.mkdir()
        (git_dir / "config.py").write_text("x = 1", encoding="utf-8")
        (tmp_path / "app.py").write_text("print('hello')", encoding="utf-8")
        files = scan_project(str(tmp_path))
        assert all(".git" not in str(f) for f in files)

    def test_skips_config_files(self, tmp_path):
        (tmp_path / "mempalace.yaml").write_text("wing: test", encoding="utf-8")
        (tmp_path / ".gitignore").write_text("*.pyc", encoding="utf-8")
        (tmp_path / "app.py").write_text("print('hello')", encoding="utf-8")
        files = scan_project(str(tmp_path))
        names = {f.name for f in files}
        assert "mempalace.yaml" not in names
        assert ".gitignore" not in names
        assert "app.py" in names


class TestGitignoreMatcher:
    """Tests for GitignoreMatcher covering parsing, matching, and edge cases."""

    # --- from_dir: file read errors and missing files ---

    def test_from_dir_no_gitignore(self, tmp_path):
        """Returns None when no .gitignore exists."""
        assert GitignoreMatcher.from_dir(tmp_path) is None

    def test_from_dir_read_error(self, tmp_path):
        """Returns None when .gitignore cannot be read (lines 103-104)."""
        gitignore = tmp_path / ".gitignore"
        gitignore.mkdir()  # directory instead of file — is_file() returns False
        assert GitignoreMatcher.from_dir(tmp_path) is None

    def test_from_dir_empty_gitignore(self, tmp_path):
        """Returns None when .gitignore has no valid rules."""
        (tmp_path / ".gitignore").write_text("\n\n# just comments\n\n", encoding="utf-8")
        assert GitignoreMatcher.from_dir(tmp_path) is None

    def test_from_dir_only_blank_patterns(self, tmp_path):
        """Returns None when patterns reduce to empty strings (line 129-130)."""
        (tmp_path / ".gitignore").write_text("/\n", encoding="utf-8")
        assert GitignoreMatcher.from_dir(tmp_path) is None

    # --- Parsing: negated, anchored, dir-only, escaped patterns ---

    def test_parse_negated_pattern(self, tmp_path):
        """Negated pattern (!) is parsed correctly (lines 117-119)."""
        (tmp_path / ".gitignore").write_text("*.log\n!important.log\n", encoding="utf-8")
        matcher = GitignoreMatcher.from_dir(tmp_path)
        assert matcher is not None
        assert len(matcher.rules) == 2
        assert matcher.rules[0]["negated"] is False
        assert matcher.rules[1]["negated"] is True
        assert matcher.rules[1]["pattern"] == "important.log"

    def test_parse_anchored_pattern(self, tmp_path):
        """Anchored pattern (/pattern) is parsed correctly (lines 121-123)."""
        (tmp_path / ".gitignore").write_text("/build\n", encoding="utf-8")
        matcher = GitignoreMatcher.from_dir(tmp_path)
        assert matcher is not None
        assert matcher.rules[0]["anchored"] is True
        assert matcher.rules[0]["pattern"] == "build"

    def test_parse_dir_only_pattern(self, tmp_path):
        """Directory-only pattern (pattern/) is parsed correctly (lines 125-127)."""
        (tmp_path / ".gitignore").write_text("logs/\n", encoding="utf-8")
        matcher = GitignoreMatcher.from_dir(tmp_path)
        assert matcher is not None
        assert matcher.rules[0]["dir_only"] is True
        assert matcher.rules[0]["pattern"] == "logs"

    def test_parse_escaped_hash(self, tmp_path):
        r"""Escaped hash (\#) is treated as literal (lines 112-113)."""
        (tmp_path / ".gitignore").write_text("\\#backup\n", encoding="utf-8")
        matcher = GitignoreMatcher.from_dir(tmp_path)
        assert matcher is not None
        assert matcher.rules[0]["pattern"] == "#backup"

    def test_parse_escaped_bang(self, tmp_path):
        r"""Escaped bang (\!) strips backslash then negation check runs (lines 112-113, 117-119)."""
        (tmp_path / ".gitignore").write_text("\\!important\n", encoding="utf-8")
        matcher = GitignoreMatcher.from_dir(tmp_path)
        assert matcher is not None
        # After stripping \, line becomes "!important"; then negation check
        # strips the "!" and sets negated=True, leaving pattern "important"
        assert matcher.rules[0]["pattern"] == "important"
        assert matcher.rules[0]["negated"] is True

    def test_parse_comment_skipped(self, tmp_path):
        """Lines starting with # are skipped (line 114-115)."""
        (tmp_path / ".gitignore").write_text("# a comment\n*.pyc\n", encoding="utf-8")
        matcher = GitignoreMatcher.from_dir(tmp_path)
        assert matcher is not None
        assert len(matcher.rules) == 1
        assert matcher.rules[0]["pattern"] == "*.pyc"

    # --- matches(): basic operation ---

    def test_matches_simple_glob(self, tmp_path):
        """Simple glob pattern matches a file."""
        (tmp_path / ".gitignore").write_text("*.pyc\n", encoding="utf-8")
        matcher = GitignoreMatcher.from_dir(tmp_path)
        f = tmp_path / "module.pyc"
        assert matcher.matches(f, is_dir=False) is True

    def test_matches_no_match(self, tmp_path):
        """File not matching any rule returns None."""
        (tmp_path / ".gitignore").write_text("*.pyc\n", encoding="utf-8")
        matcher = GitignoreMatcher.from_dir(tmp_path)
        f = tmp_path / "module.py"
        assert matcher.matches(f, is_dir=False) is None

    def test_matches_path_outside_base(self, tmp_path):
        """Path outside base_dir returns None (line 147-148)."""
        (tmp_path / ".gitignore").write_text("*.log\n", encoding="utf-8")
        matcher = GitignoreMatcher.from_dir(tmp_path)

        assert matcher.matches(Path("/some/other/place/file.log"), is_dir=False) is None

    def test_matches_base_dir_itself(self, tmp_path):
        """Matching base_dir itself returns None (empty relative, line 150-151)."""
        (tmp_path / ".gitignore").write_text("*.log\n", encoding="utf-8")
        matcher = GitignoreMatcher.from_dir(tmp_path)
        assert matcher.matches(tmp_path, is_dir=True) is None

    def test_matches_negation_overrides(self, tmp_path):
        """Negated pattern un-ignores a previously ignored file (line 159)."""
        (tmp_path / ".gitignore").write_text("*.log\n!important.log\n", encoding="utf-8")
        matcher = GitignoreMatcher.from_dir(tmp_path)
        assert matcher.matches(tmp_path / "debug.log", is_dir=False) is True
        assert matcher.matches(tmp_path / "important.log", is_dir=False) is False

    def test_matches_is_dir_auto_detect(self, tmp_path):
        """is_dir=None triggers auto-detection (line 153-154)."""
        (tmp_path / ".gitignore").write_text("logs/\n", encoding="utf-8")
        matcher = GitignoreMatcher.from_dir(tmp_path)
        logs_dir = tmp_path / "logs"
        logs_dir.mkdir()
        assert matcher.matches(logs_dir) is True  # is_dir auto-detected

    # --- _rule_matches: anchored patterns ---

    def test_anchored_pattern_matches_root_only(self, tmp_path):
        """Anchored pattern only matches at the root of base_dir (lines 175-176)."""
        (tmp_path / ".gitignore").write_text("/build\n", encoding="utf-8")
        matcher = GitignoreMatcher.from_dir(tmp_path)
        assert matcher.matches(tmp_path / "build", is_dir=False) is True
        assert matcher.matches(tmp_path / "src" / "build", is_dir=False) is None

    def test_unanchored_pattern_matches_any_depth(self, tmp_path):
        """Unanchored pattern matches at any depth (line 178)."""
        (tmp_path / ".gitignore").write_text("build\n", encoding="utf-8")
        matcher = GitignoreMatcher.from_dir(tmp_path)
        assert matcher.matches(tmp_path / "build", is_dir=False) is True
        assert matcher.matches(tmp_path / "src" / "build", is_dir=False) is True

    # --- _rule_matches: dir_only patterns ---

    def test_dir_only_pattern_skips_files(self, tmp_path):
        """dir_only pattern does not match a regular file (lines 167-170)."""
        (tmp_path / ".gitignore").write_text("logs/\n", encoding="utf-8")
        matcher = GitignoreMatcher.from_dir(tmp_path)
        # File named "logs" should not be matched by dir_only rule
        assert matcher.matches(tmp_path / "logs", is_dir=False) is None

    def test_dir_only_pattern_matches_directory(self, tmp_path):
        """dir_only pattern matches a directory."""
        (tmp_path / ".gitignore").write_text("logs/\n", encoding="utf-8")
        matcher = GitignoreMatcher.from_dir(tmp_path)
        assert matcher.matches(tmp_path / "logs", is_dir=True) is True

    def test_dir_only_matches_file_inside_dir(self, tmp_path):
        """dir_only pattern matches files inside a matching directory (line 168)."""
        (tmp_path / ".gitignore").write_text("logs/\n", encoding="utf-8")
        matcher = GitignoreMatcher.from_dir(tmp_path)
        # A file inside "logs/" — parts[:-1] = ["logs"], should match
        assert matcher.matches(tmp_path / "logs" / "app.log", is_dir=False) is True

    def test_dir_only_anchored_multi_part(self, tmp_path):
        """dir_only + anchored with multi-part pattern (lines 171-172)."""
        (tmp_path / ".gitignore").write_text("/build/output/\n", encoding="utf-8")
        matcher = GitignoreMatcher.from_dir(tmp_path)
        assert matcher.matches(tmp_path / "build" / "output", is_dir=True) is True
        assert matcher.matches(tmp_path / "other" / "build" / "output", is_dir=True) is None

    # --- _match_from_root: ** glob patterns ---

    def test_double_star_glob_matches_nested(self, tmp_path):
        """** pattern matches arbitrary depth (line 190-191)."""
        (tmp_path / ".gitignore").write_text("logs/**/*.log\n", encoding="utf-8")
        matcher = GitignoreMatcher.from_dir(tmp_path)
        assert matcher.matches(tmp_path / "logs" / "app.log", is_dir=False) is True
        assert matcher.matches(tmp_path / "logs" / "sub" / "debug.log", is_dir=False) is True
        assert matcher.matches(tmp_path / "logs" / "a" / "b" / "c.log", is_dir=False) is True

    def test_double_star_no_match(self, tmp_path):
        """** pattern doesn't match when prefix is wrong."""
        (tmp_path / ".gitignore").write_text("logs/**/*.log\n", encoding="utf-8")
        matcher = GitignoreMatcher.from_dir(tmp_path)
        assert matcher.matches(tmp_path / "src" / "app.log", is_dir=False) is None

    def test_double_star_at_end(self, tmp_path):
        """Trailing ** matches everything below (line 183-184, 186-187)."""
        (tmp_path / ".gitignore").write_text("dist/**\n", encoding="utf-8")
        matcher = GitignoreMatcher.from_dir(tmp_path)
        assert matcher.matches(tmp_path / "dist" / "bundle.js", is_dir=False) is True
        assert matcher.matches(tmp_path / "dist" / "a" / "b.js", is_dir=False) is True

    def test_double_star_remaining_all_stars(self, tmp_path):
        """When path is exhausted, remaining ** parts all pass (line 187)."""
        (tmp_path / ".gitignore").write_text("dist/**/**\n", encoding="utf-8")
        matcher = GitignoreMatcher.from_dir(tmp_path)
        assert matcher.matches(tmp_path / "dist", is_dir=False) is True

    def test_multi_part_pattern_no_double_star(self, tmp_path):
        """Multi-part pattern without ** uses exact matching (line 193-196)."""
        (tmp_path / ".gitignore").write_text("src/generated\n", encoding="utf-8")
        matcher = GitignoreMatcher.from_dir(tmp_path)
        assert matcher.matches(tmp_path / "src" / "generated", is_dir=False) is True
        assert matcher.matches(tmp_path / "lib" / "generated", is_dir=False) is None

    def test_match_from_root_pattern_longer_than_path(self, tmp_path):
        """Pattern with more parts than path doesn't match (line 186)."""
        (tmp_path / ".gitignore").write_text("a/b/c/d\n", encoding="utf-8")
        matcher = GitignoreMatcher.from_dir(tmp_path)
        assert matcher.matches(tmp_path / "a" / "b", is_dir=False) is None

    def test_fnmatch_mismatch_returns_false(self, tmp_path):
        """fnmatch mismatch at a part returns False (line 193-194)."""
        (tmp_path / ".gitignore").write_text("src/*.py\n", encoding="utf-8")
        matcher = GitignoreMatcher.from_dir(tmp_path)
        assert matcher.matches(tmp_path / "src" / "module.js", is_dir=False) is None
        assert matcher.matches(tmp_path / "src" / "module.py", is_dir=False) is True


class TestPurgeBeforeRemine:
    """Re-mining a file purges stale drawers before inserting fresh ones."""

    def test_purge_removes_preexisting_drawers(self, tmp_path, collection, monkeypatch):
        """process_file should purge stale drawers for the same source_file."""
        import mempalace.miner as miner_mod

        source = tmp_path / "app.py"
        source_file = str(source)

        # Pre-seed stale drawers with matching source_file metadata
        collection.add(
            ids=["stale_1", "stale_2"],
            documents=["old content one", "old content two"],
            metadatas=[
                {"wing": "w", "room": "r", "source_file": source_file, "chunk_index": 0},
                {"wing": "w", "room": "r", "source_file": source_file, "chunk_index": 1},
            ],
        )
        assert collection.count() == 2

        # Bypass file_already_mined guard to simulate forced re-mine
        monkeypatch.setattr(miner_mod, "file_already_mined", lambda *_a, **_kw: False)

        # Mine the file — purge should delete the stale drawers first
        source.write_text("fresh content here\n" * 30, encoding="utf-8")
        rooms = [{"name": "general", "keywords": []}]
        count, _room = process_file(source, tmp_path, collection, "test_wing", rooms, "agent", dry_run=False)
        assert count > 0

        # Stale IDs should be gone
        remaining_ids = set(collection.get()["ids"])
        assert "stale_1" not in remaining_ids
        assert "stale_2" not in remaining_ids
        # Only fresh drawers remain
        assert len(remaining_ids) == count


class TestDrawerIdHashing:
    """Drawer IDs must use SHA-256 (not MD5) for collision resistance."""

    def test_drawer_id_uses_sha256_length(self, collection):
        """SHA-256 hex[:24] produces a 24-char suffix, not MD5's 16-char."""

        add_drawer(collection, "test_wing", "test_room", "hello world", "/tmp/test.txt", 0, "test", source_mtime=0.0)
        ids = collection.get()["ids"]
        assert len(ids) == 1
        # Format: drawer_{wing}_{room}_{hash} — extract hash suffix
        parts = ids[0].split("_")
        hash_suffix = parts[-1]
        assert len(hash_suffix) == 24, f"Expected 24-char sha256 hash suffix, got {len(hash_suffix)}: {hash_suffix}"

    def test_no_md5_in_miner(self):
        """Ensure miner module doesn't use md5 anywhere."""
        import inspect

        from mempalace import miner

        source = inspect.getsource(miner)
        assert "hashlib.md5" not in source, "miner.py still uses hashlib.md5"


class TestMtimeRemine:
    """Mtime tracking ensures modified files get re-mined."""

    def test_file_already_mined_false_when_no_drawers(self, collection):
        assert file_already_mined(collection, "/nonexistent.py", 100.0) is False

    def test_file_already_mined_true_when_mtime_unchanged(self, collection):
        add_drawer(collection, "w", "r", "x" * 60, "/f.py", 0, "a", source_mtime=100.0)
        assert file_already_mined(collection, "/f.py", 100.0) is True

    def test_file_already_mined_false_when_mtime_newer(self, collection):
        add_drawer(collection, "w", "r", "x" * 60, "/f.py", 0, "a", source_mtime=100.0)
        assert file_already_mined(collection, "/f.py", 200.0) is False

    def test_file_already_mined_false_when_mtime_missing(self, collection):
        """Legacy drawers without source_mtime should trigger re-mine."""
        collection.add(
            ids=["legacy_1"],
            documents=["old content"],
            metadatas=[{"wing": "w", "room": "r", "source_file": "/f.py", "chunk_index": 0}],
        )
        assert file_already_mined(collection, "/f.py", 100.0) is False

    def test_process_file_stores_source_mtime(self, tmp_path, collection):
        source = tmp_path / "hello.py"
        source.write_text("content here\n" * 30, encoding="utf-8")
        rooms = [{"name": "general", "keywords": []}]
        count, _room = process_file(source, tmp_path, collection, "w", rooms, "a", dry_run=False)
        assert count > 0
        meta = collection.get(include=["metadatas"])["metadatas"][0]
        assert "source_mtime" in meta
        assert isinstance(meta["source_mtime"], float)
