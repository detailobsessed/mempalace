"""Tests for room_detector_local.py — local room detection from folder structure."""

from mempalace.room_detector_local import (
    detect_rooms_from_files,
    detect_rooms_from_folders,
    save_config,
)


class TestDetectRoomsFromFolders:
    def test_detects_known_folders(self, tmp_path):
        (tmp_path / "frontend").mkdir()
        (tmp_path / "backend").mkdir()
        (tmp_path / "docs").mkdir()
        rooms = detect_rooms_from_folders(str(tmp_path))
        room_names = {r["name"] for r in rooms}
        assert "frontend" in room_names
        assert "backend" in room_names
        assert "documentation" in room_names

    def test_always_includes_general(self, tmp_path):
        rooms = detect_rooms_from_folders(str(tmp_path))
        room_names = {r["name"] for r in rooms}
        assert "general" in room_names

    def test_skips_dotdirs(self, tmp_path):
        (tmp_path / ".git").mkdir()
        (tmp_path / "node_modules").mkdir()
        (tmp_path / "src").mkdir()
        rooms = detect_rooms_from_folders(str(tmp_path))
        room_names = {r["name"] for r in rooms}
        assert ".git" not in room_names
        assert "node_modules" not in room_names

    def test_nested_folder_detection(self, tmp_path):
        nested = tmp_path / "app" / "backend"
        nested.mkdir(parents=True)
        rooms = detect_rooms_from_folders(str(tmp_path))
        room_names = {r["name"] for r in rooms}
        assert "backend" in room_names

    def test_custom_folder_becomes_room(self, tmp_path):
        (tmp_path / "analytics").mkdir()
        rooms = detect_rooms_from_folders(str(tmp_path))
        room_names = {r["name"] for r in rooms}
        assert "analytics" in room_names


class TestDetectRoomsFromFiles:
    def test_detects_from_filenames(self, tmp_path):
        (tmp_path / "test_app.py").write_text("pass")
        (tmp_path / "test_utils.py").write_text("pass")
        (tmp_path / "test_models.py").write_text("pass")
        rooms = detect_rooms_from_files(str(tmp_path))
        room_names = {r["name"] for r in rooms}
        assert "testing" in room_names

    def test_fallback_to_general(self, tmp_path):
        (tmp_path / "random.xyz").write_text("data")
        rooms = detect_rooms_from_files(str(tmp_path))
        room_names = {r["name"] for r in rooms}
        assert "general" in room_names


class TestSaveConfig:
    def test_saves_yaml(self, tmp_path):
        rooms = [
            {"name": "backend", "description": "Backend code"},
            {"name": "general", "description": "Everything else"},
        ]
        save_config(str(tmp_path), "myproject", rooms)
        config_path = tmp_path / "mempalace.yaml"
        assert config_path.exists()
        content = config_path.read_text()
        assert "myproject" in content
        assert "backend" in content
