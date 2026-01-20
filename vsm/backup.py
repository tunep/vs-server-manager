"""Backup operations for Vintage Story Server Manager."""

import shutil
import tarfile
from datetime import datetime
from pathlib import Path

from .config import (
    get_data_path,
    get_logs_path,
    get_server_backups_path,
    get_world_backups_path,
    load_config,
)
from .server import command


def world_backup(config: dict | None = None) -> str:
    """Create a world backup using the server's genbackup command."""
    if config is None:
        config = load_config()

    return command("genbackup", config)


def server_backup(config: dict | None = None, manual: bool = False) -> str:
    """
    Create a full server backup by archiving the data directory.

    Archives {data_path} to {server_path}/backups/<type>-YYYY-MM-DD_HH-MM-SS.tar.gz
    where <type> is 'manual' or 'scheduled'.
    """
    if config is None:
        config = load_config()

    data_path = get_data_path(config)
    backups_path = get_server_backups_path(config)

    # Ensure backup directory exists
    backups_path.mkdir(parents=True, exist_ok=True)

    # Generate backup filename with readable timestamp
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    backup_type = "manual" if manual else "scheduled"
    backup_filename = f"{backup_type}-{timestamp}.tar.gz"
    backup_path = backups_path / backup_filename

    # Create tar.gz archive with fast compression (level 1)
    with tarfile.open(backup_path, "w:gz", compresslevel=1) as tar:
        tar.add(data_path, arcname=data_path.name)

    return f"Server backup created: {backup_path}"


def cleanup_after_server_backup(config: dict | None = None) -> str:
    """
    Clean up world backups and logs folders after a server backup.

    This prevents duplicate data since server backups include these folders.
    """
    if config is None:
        config = load_config()

    messages = []

    # Clear world backups folder
    world_backups = get_world_backups_path(config)
    if world_backups.exists():
        for item in world_backups.iterdir():
            if item.is_file():
                item.unlink()
            elif item.is_dir():
                shutil.rmtree(item)
        messages.append(f"Cleared world backups: {world_backups}")

    # Clear logs folder (but keep Archive structure)
    logs_path = get_logs_path(config)
    if logs_path.exists():
        for item in logs_path.iterdir():
            # Keep the Archive folder itself but clear non-archive log files
            if item.is_file():
                item.unlink()
                messages.append(f"Removed log file: {item.name}")

    return "\n".join(messages) if messages else "Nothing to clean up"


def prune_old_backups(config: dict | None = None) -> str:
    """
    Remove old server backups, keeping only max_server_backups most recent.
    """
    if config is None:
        config = load_config()

    max_backups = config.get("max_server_backups", 7)
    backups_path = get_server_backups_path(config)

    if not backups_path.exists():
        return "No backups directory found"

    # Get all backup files sorted by modification time (newest first)
    # Match both old (backup-*) and new (manual-*, scheduled-*) naming conventions
    all_backups = (
        list(backups_path.glob("backup-*.tar.gz"))
        + list(backups_path.glob("manual-*.tar.gz"))
        + list(backups_path.glob("scheduled-*.tar.gz"))
    )
    backups = sorted(
        all_backups,
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )

    if len(backups) <= max_backups:
        return f"No pruning needed ({len(backups)}/{max_backups} backups)"

    # Remove old backups
    removed = []
    for backup in backups[max_backups:]:
        backup.unlink()
        removed.append(backup.name)

    return f"Pruned {len(removed)} old backup(s): {', '.join(removed)}"


def list_backups(config: dict | None = None) -> list[Path]:
    """List all server backups sorted by date (newest first)."""
    if config is None:
        config = load_config()

    backups_path = get_server_backups_path(config)

    if not backups_path.exists():
        return []

    # Match both old (backup-*) and new (manual-*, scheduled-*) naming conventions
    all_backups = (
        list(backups_path.glob("backup-*.tar.gz"))
        + list(backups_path.glob("manual-*.tar.gz"))
        + list(backups_path.glob("scheduled-*.tar.gz"))
    )
    return sorted(
        all_backups,
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
