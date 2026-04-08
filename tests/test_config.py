"""Tests for config.py — MemPalace configuration system."""

import json

from mempalace.config import DEFAULT_COLLECTION_NAME, DEFAULT_PALACE_PATH, MempalaceConfig


class TestConfigDefaults:
    def test_default_palace_path(self, tmp_path):
        cfg = MempalaceConfig(config_dir=str(tmp_path))
        assert cfg.palace_path == DEFAULT_PALACE_PATH

    def test_default_collection_name(self, tmp_path):
        cfg = MempalaceConfig(config_dir=str(tmp_path))
        assert cfg.collection_name == DEFAULT_COLLECTION_NAME

    def test_default_topic_wings(self, tmp_path):
        cfg = MempalaceConfig(config_dir=str(tmp_path))
        assert "emotions" in cfg.topic_wings
        assert "technical" in cfg.topic_wings

    def test_default_hall_keywords(self, tmp_path):
        cfg = MempalaceConfig(config_dir=str(tmp_path))
        assert "emotions" in cfg.hall_keywords
        assert "scared" in cfg.hall_keywords["emotions"]


class TestConfigFromFile:
    def test_reads_config_file(self, tmp_path):
        config = {"palace_path": "/custom/path", "collection_name": "custom_collection"}
        (tmp_path / "config.json").write_text(json.dumps(config))
        cfg = MempalaceConfig(config_dir=str(tmp_path))
        assert cfg.palace_path == "/custom/path"
        assert cfg.collection_name == "custom_collection"

    def test_invalid_json_uses_defaults(self, tmp_path):
        (tmp_path / "config.json").write_text("not json{{{")
        cfg = MempalaceConfig(config_dir=str(tmp_path))
        assert cfg.palace_path == DEFAULT_PALACE_PATH


class TestConfigInit:
    def test_creates_config_dir(self, tmp_path):
        config_dir = tmp_path / "new_config"
        cfg = MempalaceConfig(config_dir=str(config_dir))
        result = cfg.init()
        assert config_dir.exists()
        assert result.exists()

    def test_creates_default_config(self, tmp_path):
        config_dir = tmp_path / "new_config"
        cfg = MempalaceConfig(config_dir=str(config_dir))
        cfg.init()
        data = json.loads((config_dir / "config.json").read_text())
        assert "palace_path" in data
        assert "topic_wings" in data

    def test_does_not_overwrite_existing(self, tmp_path):
        custom = {"palace_path": "/my/custom/path"}
        (tmp_path / "config.json").write_text(json.dumps(custom))
        cfg = MempalaceConfig(config_dir=str(tmp_path))
        cfg.init()
        data = json.loads((tmp_path / "config.json").read_text())
        assert data["palace_path"] == "/my/custom/path"


class TestPeopleMap:
    def test_reads_people_map(self, tmp_path):
        people = {"bob": "Robert", "ali": "Alice"}
        (tmp_path / "people_map.json").write_text(json.dumps(people))
        cfg = MempalaceConfig(config_dir=str(tmp_path))
        assert cfg.people_map["bob"] == "Robert"

    def test_save_people_map(self, tmp_path):
        cfg = MempalaceConfig(config_dir=str(tmp_path))
        cfg.save_people_map({"max": "Maxwell"})
        assert (tmp_path / "people_map.json").exists()
        data = json.loads((tmp_path / "people_map.json").read_text())
        assert data["max"] == "Maxwell"

    def test_missing_people_map_returns_empty(self, tmp_path):
        cfg = MempalaceConfig(config_dir=str(tmp_path))
        assert cfg.people_map == {}


class TestEnvVarOverride:
    def test_env_overrides_config(self, tmp_path, monkeypatch):
        config = {"palace_path": "/from/config"}
        (tmp_path / "config.json").write_text(json.dumps(config))
        monkeypatch.setenv("MEMPALACE_PALACE_PATH", "/from/env")
        cfg = MempalaceConfig(config_dir=str(tmp_path))
        assert cfg.palace_path == "/from/env"

    def test_legacy_env_var(self, tmp_path, monkeypatch):
        monkeypatch.setenv("MEMPAL_PALACE_PATH", "/legacy/path")
        cfg = MempalaceConfig(config_dir=str(tmp_path))
        assert cfg.palace_path == "/legacy/path"
