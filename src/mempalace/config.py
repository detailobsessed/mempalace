"""
MemPalace configuration system.

Priority: env vars > config file (~/.mempalace/config.json) > defaults
"""

import json
import os
from pathlib import Path

DEFAULT_PALACE_PATH = str(Path("~/.mempalace/palace").expanduser())
DEFAULT_COLLECTION_NAME = "mempalace_drawers"

DEFAULT_TOPIC_WINGS = [
    "emotions",
    "consciousness",
    "memory",
    "technical",
    "identity",
    "family",
    "creative",
]

DEFAULT_HALL_KEYWORDS = {
    "emotions": [
        "scared",
        "afraid",
        "worried",
        "happy",
        "sad",
        "love",
        "hate",
        "feel",
        "cry",
        "tears",
    ],
    "consciousness": [
        "consciousness",
        "conscious",
        "aware",
        "real",
        "genuine",
        "soul",
        "exist",
        "alive",
    ],
    "memory": ["memory", "remember", "forget", "recall", "archive", "palace", "store"],
    "technical": [
        "code",
        "python",
        "script",
        "bug",
        "error",
        "function",
        "api",
        "database",
        "server",
    ],
    "identity": ["identity", "name", "who am i", "persona", "self"],
    "family": ["family", "kids", "children", "daughter", "son", "parent", "mother", "father"],
    "creative": ["game", "gameplay", "player", "app", "design", "art", "music", "story"],
}


class MempalaceConfig:
    """Configuration manager for MemPalace.

    Load order: env vars > config file > defaults.
    """

    def __init__(self, config_dir=None):
        """Initialize config.

        Args:
            config_dir: Override config directory (useful for testing).
                        Defaults to ~/.mempalace.
        """
        self._config_dir = Path(config_dir) if config_dir else Path(Path("~/.mempalace").expanduser())
        self._config_file = self._config_dir / "config.json"
        self._people_map_file = self._config_dir / "people_map.json"
        self._file_config = {}

        if self._config_file.exists():
            try:
                with Path(self._config_file).open("r", encoding="utf-8") as f:
                    loaded = json.load(f)
                    self._file_config = loaded if isinstance(loaded, dict) else {}
            except json.JSONDecodeError, OSError:
                self._file_config = {}

    @property
    def palace_path(self):
        """Path to the memory palace data directory."""
        env_val = os.environ.get("MEMPALACE_PALACE_PATH") or os.environ.get("MEMPAL_PALACE_PATH")
        if env_val:
            return env_val
        return self._file_config.get("palace_path", DEFAULT_PALACE_PATH)

    @property
    def collection_name(self):
        """ChromaDB collection name."""
        return self._file_config.get("collection_name", DEFAULT_COLLECTION_NAME)

    @property
    def people_map(self):
        """Mapping of name variants to canonical names."""
        if self._people_map_file.exists():
            try:
                with Path(self._people_map_file).open("r", encoding="utf-8") as f:
                    return json.load(f)
            except json.JSONDecodeError, OSError:
                pass
        return self._file_config.get("people_map", {})

    @property
    def topic_wings(self):
        """List of topic wing names."""
        return self._file_config.get("topic_wings", DEFAULT_TOPIC_WINGS)

    @property
    def hall_keywords(self):
        """Mapping of hall names to keyword lists."""
        return self._file_config.get("hall_keywords", DEFAULT_HALL_KEYWORDS)

    def init(self):
        """Create config directory and write default config.json if it doesn't exist."""
        self._config_dir.mkdir(parents=True, exist_ok=True)
        if not self._config_file.exists():
            default_config = {
                "palace_path": DEFAULT_PALACE_PATH,
                "collection_name": DEFAULT_COLLECTION_NAME,
                "topic_wings": DEFAULT_TOPIC_WINGS,
                "hall_keywords": DEFAULT_HALL_KEYWORDS,
            }
            with Path(self._config_file).open("w", encoding="utf-8") as f:
                json.dump(default_config, f, indent=2)
        return self._config_file

    def save_people_map(self, people_map):
        """Write people_map.json to config directory.

        Args:
            people_map: Dict mapping name variants to canonical names.
        """
        self._config_dir.mkdir(parents=True, exist_ok=True)
        with Path(self._people_map_file).open("w", encoding="utf-8") as f:
            json.dump(people_map, f, indent=2)
        return self._people_map_file


MAX_NAME_LENGTH = 256


def sanitize_name(value: str, field_name: str = "name") -> str:
    """Validate and sanitize a wing/room/entity name.

    Rejects path-traversal characters (``..``, ``/``, ``\\``).
    Raises ValueError if the name is invalid.
    """
    if not isinstance(value, str) or not value.strip():
        msg = f"{field_name} must be a non-empty string"
        raise ValueError(msg)
    value = value.strip()
    if len(value) > MAX_NAME_LENGTH:
        msg = f"{field_name} exceeds maximum length of {MAX_NAME_LENGTH} characters"
        raise ValueError(msg)
    if ".." in value or "/" in value or "\\" in value:
        msg = f"{field_name} contains invalid path characters"
        raise ValueError(msg)
    if "\x00" in value:
        msg = f"{field_name} contains null bytes"
        raise ValueError(msg)
    return value


def sanitize_kg_value(value: str, field_name: str = "value") -> str:
    """Validate a knowledge-graph subject/predicate/object.

    Like sanitize_name but without path-traversal restrictions — KG values
    are stored in SQLite, not used as filesystem paths.
    Raises ValueError if the value is invalid.
    """
    if not isinstance(value, str) or not value.strip():
        msg = f"{field_name} must be a non-empty string"
        raise ValueError(msg)
    value = value.strip()
    if len(value) > MAX_NAME_LENGTH:
        msg = f"{field_name} exceeds maximum length of {MAX_NAME_LENGTH} characters"
        raise ValueError(msg)
    if "\x00" in value:
        msg = f"{field_name} contains null bytes"
        raise ValueError(msg)
    return value


def sanitize_content(value: str, max_length: int = 100_000) -> str:
    """Validate drawer/diary content length."""
    if not isinstance(value, str) or not value.strip():
        msg = "content must be a non-empty string"
        raise ValueError(msg)
    if len(value) > max_length:
        msg = f"content exceeds maximum length of {max_length} characters"
        raise ValueError(msg)
    if "\x00" in value:
        msg = "content contains null bytes"
        raise ValueError(msg)
    return value


def build_where(wing: str | None, room: str | None) -> dict | None:
    """Build a ChromaDB where filter from optional wing/room."""
    if wing and room:
        return {"$and": [{"wing": wing}, {"room": room}]}
    if wing:
        return {"wing": wing}
    if room:
        return {"room": room}
    return None
