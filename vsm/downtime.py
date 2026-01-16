"""Downtime tracking for Vintage Story Server Manager."""

import json
from datetime import datetime
from pathlib import Path

from .config import get_server_backups_path, load_config

DOWNTIME_FILENAME = ".downtime"


def _get_downtime_file(config: dict) -> Path:
    """Get the path to the downtime tracking file."""
    backups_path = get_server_backups_path(config)
    backups_path.mkdir(parents=True, exist_ok=True)
    return backups_path / DOWNTIME_FILENAME


def _load_downtime_data(config: dict) -> dict:
    """Load downtime data from file."""
    downtime_file = _get_downtime_file(config)

    if not downtime_file.exists():
        return {}

    with open(downtime_file, "r") as f:
        return json.load(f)


def _save_downtime_data(config: dict, data: dict) -> None:
    """Save downtime data to file."""
    downtime_file = _get_downtime_file(config)

    with open(downtime_file, "w") as f:
        json.dump(data, f, indent=2)


def record_stop_time(config: dict | None = None) -> None:
    """Record the timestamp when server stop begins."""
    if config is None:
        config = load_config()

    data = _load_downtime_data(config)
    data["stop_time"] = datetime.now().isoformat()
    _save_downtime_data(config, data)


def record_start_time(config: dict | None = None) -> None:
    """
    Record the timestamp when server is back online and calculate downtime.

    This should be called after the server has fully started.
    """
    if config is None:
        config = load_config()

    data = _load_downtime_data(config)
    start_time = datetime.now()
    data["start_time"] = start_time.isoformat()

    # Calculate downtime if we have both timestamps
    if "stop_time" in data:
        stop_time = datetime.fromisoformat(data["stop_time"])
        downtime_seconds = (start_time - stop_time).total_seconds()
        data["last_downtime_seconds"] = downtime_seconds

    _save_downtime_data(config, data)


def get_estimated_downtime(config: dict | None = None) -> int | None:
    """
    Get the estimated downtime in seconds based on the last backup cycle.

    Returns None if no previous downtime has been recorded.
    """
    if config is None:
        config = load_config()

    data = _load_downtime_data(config)
    return data.get("last_downtime_seconds")


def get_estimated_downtime_minutes(config: dict | None = None) -> int | None:
    """
    Get the estimated downtime in minutes (rounded up).

    Returns None if no previous downtime has been recorded.
    """
    seconds = get_estimated_downtime(config)
    if seconds is None:
        return None

    # Round up to nearest minute
    return int((seconds + 59) // 60)


def format_downtime_estimate(config: dict | None = None) -> str:
    """
    Get a formatted string for the downtime estimate.

    Returns empty string if no estimate is available.
    """
    minutes = get_estimated_downtime_minutes(config)
    if minutes is None:
        return ""

    if minutes == 1:
        return "(estimated downtime: 1 minute)"
    return f"(estimated downtime: {minutes} minutes)"
