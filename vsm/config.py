"""Configuration management for Vintage Story Server Manager."""

import json
from pathlib import Path

DEFAULT_CONFIG = {
    "data_path": "/var/vintagestory/data",
    "server_path": "~/server",
    "world_backup_interval": 1,
    "server_backup_interval": 6,
    "max_server_backups": 7,
}


def get_config_path() -> Path:
    """Get the path to the config file (same directory as the package)."""
    return Path(__file__).parent.parent / "config.json"


def load_config() -> dict:
    """Load configuration from config.json, creating with defaults if missing."""
    config_path = get_config_path()

    if not config_path.exists():
        save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG.copy()

    with open(config_path, "r") as f:
        config = json.load(f)

    # Merge with defaults for any missing keys
    merged = DEFAULT_CONFIG.copy()
    merged.update(config)
    return merged


def save_config(config: dict) -> None:
    """Save configuration to config.json."""
    config_path = get_config_path()
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)


def get_data_path(config: dict) -> Path:
    """Get the data path, expanding ~ if present."""
    return Path(config["data_path"]).expanduser()


def get_server_path(config: dict) -> Path:
    """Get the server path, expanding ~ if present."""
    return Path(config["server_path"]).expanduser()


def get_logs_path(config: dict) -> Path:
    """Get the logs directory path."""
    return get_data_path(config) / "Logs"


def get_world_backups_path(config: dict) -> Path:
    """Get the world backups directory path."""
    return get_data_path(config) / "Backups"


def get_server_executable(config: dict) -> Path:
    """Get the server executable path."""
    return get_server_path(config) / "server.sh"


def get_server_backups_path(config: dict) -> Path:
    """Get the server backups directory path."""
    return get_server_path(config) / "backups"
