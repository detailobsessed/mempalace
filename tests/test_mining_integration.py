"""Integration tests for the mining pipeline.

Tests miner, convo_miner, split_mega_files, and entity_detector
end-to-end with real ChromaDB collections and temp directories.
"""

import os
from pathlib import Path

import pytest

from mempalace.convo_miner import (
    file_already_mined as convo_file_already_mined,
)
from mempalace.convo_miner import (
    get_collection as convo_get_collection,
)
from mempalace.convo_miner import (
    mine_convos,
    scan_convos,
)
from mempalace.entity_detector import (
    confirm_entities,
    detect_entities,
    scan_for_detection,
)
from mempalace.miner import (
    add_drawer,
    file_already_mined,
    get_collection,
    load_config,
    mine,
    process_file,
    status,
)
from mempalace.split_mega_files import (
    _load_known_people,
    extract_people,
    split_file,
)

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def project_dir(tmp_path):
    """Create a fake project directory for mining."""
    proj = tmp_path / "myproject"
    proj.mkdir()
    # Create mempalace.yaml
    (proj / "mempalace.yaml").write_text(
        "wing: myproject\nrooms:\n  - name: backend\n    description: Backend code\n  - name: general\n    description: Everything else\n",
        encoding="utf-8",
    )
    # Create some source files
    backend = proj / "backend"
    backend.mkdir()
    (backend / "app.py").write_text("# Backend application\nimport flask\n" + "def handle_request():\n    pass\n" * 20, encoding="utf-8")
    (proj / "notes.md").write_text("# Project Notes\n" + "This is a note about the project.\n" * 20, encoding="utf-8")
    return proj


@pytest.fixture
def convo_dir(tmp_path):
    """Create a directory with fake conversation files."""
    cdir = tmp_path / "convos"
    cdir.mkdir()
    # File with > markers (exchange format)
    exchange_content = (
        "> How do I fix this Python bug in the API?\n"
        "You need to check the error handling in the function.\n\n"
        "> What about the database connection?\n"
        "Make sure you close connections properly.\n\n"
        "> Can you show me a code example?\n"
        "Here is a simple example of proper connection handling.\n\n"
        "> Thanks for the help with debugging\n"
        "You're welcome! Let me know if you need more help.\n"
    )
    (cdir / "chat1.md").write_text(exchange_content, encoding="utf-8")
    # Plain text file (paragraph chunking fallback)
    plain_content = (
        "We decided to switch to PostgreSQL instead of MySQL.\n"
        "The team chose this approach after evaluating alternatives.\n\n"
        "The migration plan involves several steps that we picked carefully.\n"
        "We replaced the ORM layer with a lighter alternative option.\n\n"
        "Overall this was a good trade-off for the project going forward.\n"
        "We migrated all data successfully without any downtime issues.\n"
    )
    (cdir / "notes.txt").write_text(plain_content, encoding="utf-8")
    return cdir


# ============================================================================
# 1. miner.py integration tests
# ============================================================================


class TestLoadConfig:
    def test_loads_mempalace_yaml(self, project_dir):
        config = load_config(str(project_dir))
        assert config["wing"] == "myproject"
        assert len(config["rooms"]) == 2

    def test_missing_config_exits(self, tmp_path):
        empty = tmp_path / "empty"
        empty.mkdir()
        with pytest.raises(SystemExit):
            load_config(str(empty))

    def test_legacy_fallback(self, tmp_path):
        proj = tmp_path / "legacy"
        proj.mkdir()
        (proj / "mempal.yaml").write_text("wing: legacy_wing\nrooms:\n  - name: stuff\n    description: things\n", encoding="utf-8")
        config = load_config(str(proj))
        assert config["wing"] == "legacy_wing"


class TestGetCollectionAndDrawers:
    def test_get_collection_creates_fresh(self, palace_path):
        col = get_collection(palace_path)
        assert col is not None
        assert col.count() == 0

    def test_get_collection_idempotent(self, palace_path):
        col1 = get_collection(palace_path)
        col2 = get_collection(palace_path)
        assert col1.name == col2.name

    def test_add_drawer_and_query(self, palace_path):
        col = get_collection(palace_path)
        added = add_drawer(
            collection=col,
            wing="test_wing",
            room="test_room",
            content="This is drawer content for testing purposes.",
            source_file="/fake/path.py",
            chunk_index=0,
            agent="test",
            source_mtime=0.0,
        )
        assert added is True
        assert col.count() == 1

    def test_add_drawer_duplicate_silently_skipped(self, palace_path):
        col = get_collection(palace_path)
        add_drawer(col, "w", "r", "content here", "/f.py", 0, "test", source_mtime=0.0)
        add_drawer(col, "w", "r", "content here", "/f.py", 0, "test", source_mtime=0.0)
        # Duplicate ID -- returns False or raises and catches
        assert col.count() == 1

    def test_file_already_mined_false_initially(self, palace_path):
        col = get_collection(palace_path)
        assert file_already_mined(col, "/nonexistent.py", 0.0) is False

    def test_file_already_mined_true_after_add(self, palace_path):
        col = get_collection(palace_path)
        add_drawer(col, "w", "r", "some content", "/mined.py", 0, "test", source_mtime=100.0)
        assert file_already_mined(col, "/mined.py", 100.0) is True


class TestProcessFile:
    def test_process_file_adds_drawers(self, project_dir, palace_path):
        col = get_collection(palace_path)
        filepath = project_dir / "backend" / "app.py"
        rooms = [
            {"name": "backend", "description": "Backend code"},
            {"name": "general", "description": "Everything else"},
        ]
        count, room = process_file(
            filepath=filepath,
            project_path=project_dir,
            collection=col,
            wing="myproject",
            rooms=rooms,
            agent="test",
            dry_run=False,
        )
        assert count > 0
        assert room == "backend"
        assert col.count() == count

    def test_process_file_skips_already_mined(self, project_dir, palace_path):
        col = get_collection(palace_path)
        filepath = project_dir / "backend" / "app.py"
        rooms = [{"name": "backend", "description": "Backend code"}]
        kwargs = {
            "filepath": filepath,
            "project_path": project_dir,
            "collection": col,
            "wing": "w",
            "rooms": rooms,
            "agent": "test",
            "dry_run": False,
        }
        first, _ = process_file(**kwargs)
        assert first > 0
        second, _ = process_file(**kwargs)
        assert second == 0

    def test_process_file_dry_run(self, project_dir, palace_path):
        col = get_collection(palace_path)
        filepath = project_dir / "backend" / "app.py"
        rooms = [{"name": "backend", "description": "Backend code"}]
        count, room = process_file(
            filepath=filepath,
            project_path=project_dir,
            collection=col,
            wing="w",
            rooms=rooms,
            agent="test",
            dry_run=True,
        )
        assert count > 0
        assert room == "backend"
        # Dry run should not add anything to the collection
        assert col.count() == 0

    def test_process_file_tiny_file_skipped(self, project_dir, palace_path):
        tiny = project_dir / "tiny.py"
        tiny.write_text("x=1", encoding="utf-8")
        col = get_collection(palace_path)
        rooms = [{"name": "general", "description": "All"}]
        count, _ = process_file(
            filepath=tiny,
            project_path=project_dir,
            collection=col,
            wing="w",
            rooms=rooms,
            agent="test",
            dry_run=False,
        )
        assert count == 0


class TestMineEndToEnd:
    def test_mine_files_into_palace(self, project_dir, palace_path):
        mine(
            project_dir=str(project_dir),
            palace_path=palace_path,
            agent="test",
        )
        col = get_collection(palace_path)
        assert col.count() > 0

    def test_mine_dry_run_no_writes(self, project_dir, palace_path):
        mine(
            project_dir=str(project_dir),
            palace_path=palace_path,
            dry_run=True,
        )
        col = get_collection(palace_path)
        assert col.count() == 0

    def test_mine_with_limit(self, project_dir, palace_path):
        mine(
            project_dir=str(project_dir),
            palace_path=palace_path,
            limit=1,
            agent="test",
        )
        col = get_collection(palace_path)
        # Only 1 file processed, so drawers should be limited
        assert col.count() > 0

    def test_mine_with_wing_override(self, project_dir, palace_path):
        mine(
            project_dir=str(project_dir),
            palace_path=palace_path,
            wing_override="custom_wing",
            agent="test",
        )
        col = get_collection(palace_path)
        results = col.get(limit=1, include=["metadatas"])
        assert results["metadatas"][0]["wing"] == "custom_wing"

    def test_mine_idempotent(self, project_dir, palace_path):
        mine(project_dir=str(project_dir), palace_path=palace_path, agent="test")
        col = get_collection(palace_path)
        count_first = col.count()
        mine(project_dir=str(project_dir), palace_path=palace_path, agent="test")
        col2 = get_collection(palace_path)
        assert col2.count() == count_first

    def test_modified_file_gets_remined(self, project_dir, palace_path):
        """A file modified after mining should be re-mined on the next run."""
        mine(project_dir=str(project_dir), palace_path=palace_path, agent="test")
        col = get_collection(palace_path)

        # Pick the first file and grab its original content
        target = next(project_dir.rglob("*.py"))
        original_meta = col.get(
            where={"source_file": str(target)},
            include=["documents", "metadatas"],
        )
        assert original_meta["ids"], "file should have been mined"

        # Modify the file and force mtime advance (HFS+ has 1s resolution)
        target.write_text("# rewritten\n" + "updated = True\n" * 30, encoding="utf-8")
        new_mtime = target.stat().st_mtime + 1.0
        os.utime(target, (new_mtime, new_mtime))

        # Re-mine — modified file should be picked up
        mine(project_dir=str(project_dir), palace_path=palace_path, agent="test")
        col2 = get_collection(palace_path)
        updated = col2.get(
            where={"source_file": str(target)},
            include=["documents"],
        )
        assert updated["ids"], "file should still have drawers after re-mine"
        assert "updated = True" in updated["documents"][0]


class TestStatus:
    def test_status_with_data(self, project_dir, palace_path, capsys):
        mine(project_dir=str(project_dir), palace_path=palace_path, agent="test")
        status(palace_path)
        captured = capsys.readouterr()
        assert "drawers" in captured.out.lower()

    def test_status_empty_palace(self, tmp_path, capsys):
        empty_palace = str(tmp_path / "empty_palace")
        status(empty_palace)
        captured = capsys.readouterr()
        assert "no palace" in captured.out.lower() or "not found" in captured.out.lower()


# ============================================================================
# 2. convo_miner.py integration tests
# ============================================================================


class TestConvoGetCollection:
    def test_creates_collection(self, palace_path):
        col = convo_get_collection(palace_path)
        assert col is not None
        assert col.count() == 0

    def test_file_already_mined_false(self, palace_path):
        col = convo_get_collection(palace_path)
        assert convo_file_already_mined(col, "/fake.md") is False


class TestScanConvos:
    def test_finds_conversation_files(self, convo_dir):
        files = scan_convos(str(convo_dir))
        extensions = {f.suffix for f in files}
        assert ".md" in extensions or ".txt" in extensions
        assert len(files) == 2

    def test_empty_dir(self, tmp_path):
        empty = tmp_path / "empty_convos"
        empty.mkdir()
        files = scan_convos(str(empty))
        assert files == []

    def test_skips_excluded_dirs(self, convo_dir):
        venv = convo_dir / ".venv"
        venv.mkdir()
        (venv / "stray.txt").write_text("should be skipped", encoding="utf-8")
        files = scan_convos(str(convo_dir))
        assert all(".venv" not in str(f) for f in files)


class TestMineConvosEndToEnd:
    def test_mine_convos_exchange_mode(self, convo_dir, palace_path):
        mine_convos(
            convo_dir=str(convo_dir),
            palace_path=palace_path,
            wing="test_convos",
            agent="test",
        )
        col = convo_get_collection(palace_path)
        assert col.count() > 0
        # Verify metadata
        results = col.get(limit=1, include=["metadatas"])
        meta = results["metadatas"][0]
        assert meta["wing"] == "test_convos"
        assert meta["ingest_mode"] == "convos"

    def test_mine_convos_dry_run(self, convo_dir, palace_path):
        mine_convos(
            convo_dir=str(convo_dir),
            palace_path=palace_path,
            wing="test",
            dry_run=True,
        )
        col = convo_get_collection(palace_path)
        assert col.count() == 0

    def test_mine_convos_idempotent(self, convo_dir, palace_path):
        mine_convos(convo_dir=str(convo_dir), palace_path=palace_path, wing="w", agent="test")
        col = convo_get_collection(palace_path)
        count_first = col.count()
        mine_convos(convo_dir=str(convo_dir), palace_path=palace_path, wing="w", agent="test")
        col2 = convo_get_collection(palace_path)
        assert col2.count() == count_first

    def test_mine_convos_with_limit(self, convo_dir, palace_path):
        mine_convos(
            convo_dir=str(convo_dir),
            palace_path=palace_path,
            wing="w",
            limit=1,
            agent="test",
        )
        col = convo_get_collection(palace_path)
        assert col.count() > 0

    def test_mine_convos_default_wing_from_dirname(self, convo_dir, palace_path):
        mine_convos(
            convo_dir=str(convo_dir),
            palace_path=palace_path,
            agent="test",
        )
        col = convo_get_collection(palace_path)
        results = col.get(limit=1, include=["metadatas"])
        # Wing should be derived from directory name
        assert results["metadatas"][0]["wing"] == "convos"


# ============================================================================
# 3. split_mega_files.py integration tests
# ============================================================================


def _make_mega_file(directory, filename="mega.txt", num_sessions=3):
    """Create a fake mega-file with multiple Claude Code sessions."""
    lines = []
    for i in range(num_sessions):
        lines.extend([
            f"Claude Code v1.0.{i}",
            f"⏺ {i + 1}:00 PM Wednesday, March 2{i}, 2026",
            "",
            f"> Can you help me with task number {i}?",
            f"Sure, I'll help with task {i}.",
            "",
        ])
        # Add enough lines to pass the 10-line minimum
        lines.extend(f"Session {i} line {j}: doing some work on the project." for j in range(15))
        lines.append("")
    path = directory / filename
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


class TestSplitFile:
    def test_splits_mega_file(self, tmp_path):
        mega = _make_mega_file(tmp_path, num_sessions=3)
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        written = split_file(str(mega), str(output_dir))
        assert len(written) == 3
        for p in written:
            assert Path(p).exists()

    def test_dry_run_no_files_written(self, tmp_path):
        mega = _make_mega_file(tmp_path, num_sessions=2)
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        written = split_file(str(mega), str(output_dir), dry_run=True)
        assert len(written) == 2
        # Files should NOT actually exist in dry run
        for p in written:
            assert not Path(p).exists()

    def test_single_session_not_split(self, tmp_path):
        """A file with only one session is not a mega-file."""
        content = "Claude Code v1.0.0\nSome content\n" * 20
        path = tmp_path / "single.txt"
        path.write_text(content, encoding="utf-8")
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        written = split_file(str(path), str(output_dir))
        assert written == []

    def test_output_to_same_dir_when_none(self, tmp_path):
        mega = _make_mega_file(tmp_path, num_sessions=2)
        written = split_file(str(mega), None)
        assert len(written) == 2
        for p in written:
            assert Path(p).parent == tmp_path


class TestExtractPeople:
    def test_detects_known_names(self):
        lines = [
            "Working on the project with Alice and Ben.",
            "Alice said we should refactor the module.",
            "Ben agreed with the plan.",
        ] + ["filler\n"] * 97
        people = extract_people(lines)
        assert "Alice" in people
        assert "Ben" in people

    def test_no_people_found(self):
        lines = ["Just some random text about code."] * 100
        people = extract_people(lines)
        assert people == []

    def test_returns_sorted(self):
        lines = [
            "Sam and Ben were discussing the project.",
            "Alice joined later.",
        ] + ["filler\n"] * 98
        people = extract_people(lines)
        assert people == sorted(people)


class TestLoadKnownPeople:
    def test_returns_list(self):
        result = _load_known_people()
        assert isinstance(result, list)
        assert len(result) > 0

    def test_fallback_contains_expected_names(self):
        # When no config file exists, should return the hardcoded fallback
        result = _load_known_people()
        # The fallback list includes these names
        assert "Alice" in result or "Ben" in result


# ============================================================================
# 4. entity_detector.py integration tests
# ============================================================================


@pytest.fixture
def entity_files(tmp_path):
    """Create files with recognizable entity patterns."""
    prose_dir = tmp_path / "prose"
    prose_dir.mkdir()

    # File with person-like entity
    person_content = (
        "Alice said hello to the team. Alice asked about the deadline.\n"
        "Alice laughed at the joke. Alice thinks we should ship soon.\n"
        "Alice: I'll handle the backend refactor.\n"
        "Alice decided to push the code. Hey Alice, can you review this?\n"
        "Thanks Alice for the help. Alice wrote the tests.\n"
    )
    (prose_dir / "chat.txt").write_text(person_content, encoding="utf-8")

    # File with project-like entity
    project_content = (
        "We're building MemPalace for memory management.\n"
        "Deploy MemPalace to production. The MemPalace architecture is solid.\n"
        "Check MemPalace.py for details. MemPalace v2 is coming.\n"
        "import MemPalace in your script. The MemPalace pipeline works.\n"
        "pip install MemPalace to get started. MemPalace-core is stable.\n"
    )
    (prose_dir / "project.md").write_text(project_content, encoding="utf-8")

    return prose_dir


class TestDetectEntities:
    def test_detects_people_and_projects(self, entity_files):
        files = list(entity_files.glob("*"))
        result = detect_entities(files)
        assert "people" in result
        assert "projects" in result
        assert "uncertain" in result

    def test_empty_files_no_crash(self, tmp_path):
        empty = tmp_path / "empty.txt"
        empty.write_text("", encoding="utf-8")
        result = detect_entities([empty])
        assert result == {"people": [], "projects": [], "uncertain": []}

    def test_no_files(self):
        result = detect_entities([])
        assert result == {"people": [], "projects": [], "uncertain": []}

    def test_max_files_respected(self, entity_files):
        files = list(entity_files.glob("*"))
        result = detect_entities(files, max_files=1)
        # Should still work with just 1 file
        assert isinstance(result, dict)

    def test_entity_structure(self, entity_files):
        files = list(entity_files.glob("*"))
        result = detect_entities(files)
        all_entities = result["people"] + result["projects"] + result["uncertain"]
        for entity in all_entities:
            assert "name" in entity
            assert "type" in entity
            assert "confidence" in entity
            assert "frequency" in entity
            assert "signals" in entity


class TestConfirmEntities:
    def test_auto_accept_with_yes(self):
        detected = {
            "people": [
                {"name": "Alice", "type": "person", "confidence": 0.9, "frequency": 10, "signals": ["dialogue marker (3x)"]},
            ],
            "projects": [
                {"name": "MemPalace", "type": "project", "confidence": 0.8, "frequency": 8, "signals": ["project verb (2x)"]},
            ],
            "uncertain": [
                {"name": "Ambiguous", "type": "uncertain", "confidence": 0.5, "frequency": 5, "signals": ["mixed"]},
            ],
        }
        confirmed = confirm_entities(detected, yes=True)
        assert "Alice" in confirmed["people"]
        assert "MemPalace" in confirmed["projects"]
        # Uncertain should be skipped with yes=True
        assert "Ambiguous" not in confirmed["people"]
        assert "Ambiguous" not in confirmed["projects"]

    def test_auto_accept_empty(self):
        detected = {"people": [], "projects": [], "uncertain": []}
        confirmed = confirm_entities(detected, yes=True)
        assert confirmed["people"] == []
        assert confirmed["projects"] == []


class TestScanForDetection:
    def test_finds_prose_files(self, entity_files):
        files = scan_for_detection(str(entity_files))
        extensions = {f.suffix for f in files}
        assert ".txt" in extensions or ".md" in extensions

    def test_empty_dir(self, tmp_path):
        empty = tmp_path / "nothing"
        empty.mkdir()
        files = scan_for_detection(str(empty))
        assert files == []

    def test_max_files_cap(self, tmp_path):
        d = tmp_path / "many"
        d.mkdir()
        for i in range(20):
            (d / f"file{i}.txt").write_text(f"Content {i}\n" * 10, encoding="utf-8")
        files = scan_for_detection(str(d), max_files=5)
        assert len(files) <= 5

    def test_falls_back_to_all_readable(self, tmp_path):
        """When fewer than 3 prose files, includes all readable files."""
        d = tmp_path / "mixed"
        d.mkdir()
        (d / "only.txt").write_text("one prose file\n" * 10, encoding="utf-8")
        (d / "code.py").write_text("print('hello')\n" * 10, encoding="utf-8")
        files = scan_for_detection(str(d))
        extensions = {f.suffix for f in files}
        # Should include .py since fewer than 3 prose files
        assert ".py" in extensions

    def test_skips_excluded_dirs(self, tmp_path):
        d = tmp_path / "proj"
        d.mkdir()
        (d / "readme.md").write_text("Hello\n" * 10, encoding="utf-8")
        venv = d / ".venv"
        venv.mkdir()
        (venv / "stray.txt").write_text("should skip", encoding="utf-8")
        files = scan_for_detection(str(d))
        assert all(".venv" not in str(f) for f in files)


# ============================================================================
# Sentinel drawer for 0-chunk conversation files
# ============================================================================


class TestSentinelDrawerForEmptyFiles:
    """Files that produce 0 chunks should get a sentinel so they aren't re-processed."""

    def test_register_empty_file_creates_sentinel(self, tmp_path):
        """Sentinel makes file_already_mined return True."""
        from mempalace.convo_miner import _register_empty_file

        palace_path = str(tmp_path / "palace")
        col = convo_get_collection(palace_path)
        _register_empty_file(col, "/empty.md", "test_wing", "test_agent")
        assert convo_file_already_mined(col, "/empty.md") is True

    def test_sentinel_metadata(self, tmp_path):
        """Sentinel drawer has correct metadata fields."""
        from mempalace.convo_miner import _register_empty_file

        palace_path = str(tmp_path / "palace")
        col = convo_get_collection(palace_path)
        _register_empty_file(col, "/empty2.md", "w", "a")
        results = col.get(where={"source_file": "/empty2.md"}, include=["metadatas"])
        meta = results["metadatas"][0]
        assert meta["room"] == "_sentinel"
        assert meta["chunk_index"] == -1
        assert meta["is_sentinel"] == "true"
        assert meta["extract_mode"] == "sentinel"

    def test_zero_chunk_file_not_reprocessed(self, tmp_path):
        """A file that yields 0 chunks is skipped on the second run."""
        cdir = tmp_path / "convos"
        cdir.mkdir()
        # Content passes MIN_CHUNK_SIZE (30) but each exchange pair is too short
        # to produce a chunk, so chunk_exchanges returns []
        content = "> q?\nyes\n\n" * 6  # 60 chars total, but each pair is ~10 chars
        (cdir / "nochnk.md").write_text(content, encoding="utf-8")
        palace_path = str(tmp_path / "palace")
        mine_convos(convo_dir=str(cdir), palace_path=palace_path, wing="t", agent="t")
        col = convo_get_collection(palace_path)
        assert convo_file_already_mined(col, str(cdir / "nochnk.md")) is True

    def test_dry_run_does_not_write_sentinel(self, tmp_path):
        """Dry run must not write any sentinels."""
        cdir = tmp_path / "convos"
        cdir.mkdir()
        # Content passes MIN_CHUNK_SIZE (30) but each exchange pair is too short
        # to produce a chunk, so chunk_exchanges returns [] — sentinel path is reached
        (cdir / "tiny.md").write_text("> q?\nyes\n\n" * 6, encoding="utf-8")
        palace_path = str(tmp_path / "palace")
        mine_convos(
            convo_dir=str(cdir),
            palace_path=palace_path,
            wing="t",
            agent="t",
            dry_run=True,
        )
        col = convo_get_collection(palace_path)
        assert col.count() == 0
