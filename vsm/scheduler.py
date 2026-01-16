"""Backup scheduling with announcements for Vintage Story Server Manager."""

import signal
import sys
from datetime import datetime, timedelta

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from rich.console import Console

from .backup import (
    cleanup_after_server_backup,
    prune_old_backups,
    server_backup,
    world_backup,
)
from .config import load_config
from .downtime import (
    format_downtime_estimate,
    record_start_time,
    record_stop_time,
)
from .server import announce, get_players, start, stop

console = Console()

# Announcement intervals in minutes before backup
ANNOUNCEMENT_INTERVALS = [30, 15, 10, 5, 2, 1]


def _should_announce(config: dict) -> bool:
    """Check if we should announce (only when players are online)."""
    try:
        players = get_players(config)
        return players > 0
    except Exception:
        return False


def _send_announcement(minutes: int, config: dict) -> None:
    """Send a backup announcement to players."""
    if not _should_announce(config):
        return

    downtime_estimate = format_downtime_estimate(config)
    if minutes == 1:
        message = f"Server going offline for backup in 1 minute {downtime_estimate}".strip()
    else:
        message = f"Server going offline for backup in {minutes} minutes {downtime_estimate}".strip()

    try:
        announce(message, config)
        console.print(f"[yellow]Announced:[/yellow] {message}")
    except Exception as e:
        console.print(f"[red]Failed to announce:[/red] {e}")


def _run_world_backup(config: dict) -> None:
    """Run a world backup."""
    console.print(f"[cyan]{datetime.now()}[/cyan] Running world backup...")

    try:
        result = world_backup(config)
        console.print(f"[green]World backup complete[/green]")
        if result:
            console.print(result)
    except Exception as e:
        console.print(f"[red]World backup failed:[/red] {e}")


def _run_server_backup(config: dict) -> None:
    """Run a full server backup cycle with stop/start."""
    console.print(f"[cyan]{datetime.now()}[/cyan] Starting server backup cycle...")

    try:
        # Record stop time and stop server
        record_stop_time(config)
        console.print("[yellow]Stopping server...[/yellow]")
        stop(config)

        # Create backup
        console.print("[yellow]Creating server backup...[/yellow]")
        result = server_backup(config)
        console.print(f"[green]{result}[/green]")

        # Cleanup
        console.print("[yellow]Cleaning up old data...[/yellow]")
        cleanup_result = cleanup_after_server_backup(config)
        if cleanup_result:
            console.print(cleanup_result)

        # Prune old backups
        prune_result = prune_old_backups(config)
        console.print(prune_result)

        # Restart server
        console.print("[yellow]Starting server...[/yellow]")
        start(config)
        record_start_time(config)

        console.print("[green]Server backup cycle complete[/green]")

    except Exception as e:
        console.print(f"[red]Server backup failed:[/red] {e}")
        # Try to ensure server is running
        try:
            console.print("[yellow]Attempting to restart server...[/yellow]")
            start(config)
        except Exception:
            pass


def _schedule_announcements(
    scheduler: BlockingScheduler,
    backup_time: datetime,
    config: dict,
) -> None:
    """Schedule announcements before a backup."""
    now = datetime.now()

    for minutes in ANNOUNCEMENT_INTERVALS:
        announce_time = backup_time - timedelta(minutes=minutes)

        # Only schedule future announcements
        if announce_time > now:
            scheduler.add_job(
                _send_announcement,
                "date",
                run_date=announce_time,
                args=[minutes, config],
            )


def _is_server_backup_hour(hour: int, config: dict) -> bool:
    """Check if a given hour is a server backup hour."""
    server_interval = config.get("server_backup_interval", 6)
    return hour % server_interval == 0


def _world_backup_job(config: dict) -> None:
    """World backup job that skips when server backup is in same hour."""
    current_hour = datetime.now().hour

    if _is_server_backup_hour(current_hour, config):
        console.print(
            f"[dim]{datetime.now()} Skipping world backup (server backup scheduled this hour)[/dim]"
        )
        return

    _run_world_backup(config)


def run_scheduler() -> None:
    """Run the backup scheduler daemon."""
    config = load_config()
    scheduler = BlockingScheduler()

    world_interval = config.get("world_backup_interval", 1)
    server_interval = config.get("server_backup_interval", 6)

    console.print("[bold]Vintage Story Backup Scheduler[/bold]")
    console.print(f"World backup interval: every {world_interval} hour(s)")
    console.print(f"Server backup interval: every {server_interval} hour(s)")
    console.print("Press Ctrl+C to stop\n")

    # Schedule world backups (every N hours at :00)
    scheduler.add_job(
        _world_backup_job,
        CronTrigger(hour=f"*/{world_interval}", minute=0),
        args=[config],
        id="world_backup",
        name="World Backup",
    )

    # Schedule server backups (every N hours at :00)
    scheduler.add_job(
        _run_server_backup,
        CronTrigger(hour=f"*/{server_interval}", minute=0),
        args=[config],
        id="server_backup",
        name="Server Backup",
    )

    # Calculate next server backup time and schedule announcements
    now = datetime.now()
    current_hour = now.hour
    next_server_backup_hour = (
        (current_hour // server_interval + 1) * server_interval
    ) % 24

    if next_server_backup_hour <= current_hour:
        # Next backup is tomorrow
        next_backup = now.replace(
            hour=next_server_backup_hour, minute=0, second=0, microsecond=0
        ) + timedelta(days=1)
    else:
        next_backup = now.replace(
            hour=next_server_backup_hour, minute=0, second=0, microsecond=0
        )

    _schedule_announcements(scheduler, next_backup, config)

    # Re-schedule announcements after each server backup
    def schedule_next_announcements():
        now = datetime.now()
        next_backup = now.replace(minute=0, second=0, microsecond=0) + timedelta(
            hours=server_interval
        )
        _schedule_announcements(scheduler, next_backup, config)

    scheduler.add_job(
        schedule_next_announcements,
        CronTrigger(hour=f"*/{server_interval}", minute=1),
        id="reschedule_announcements",
        name="Reschedule Announcements",
    )

    # Handle graceful shutdown
    def shutdown(signum, frame):
        console.print("\n[yellow]Shutting down scheduler...[/yellow]")
        scheduler.shutdown(wait=False)
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        pass
