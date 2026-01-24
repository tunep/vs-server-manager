"""Backup scheduling with announcements for Vintage Story Server Manager."""

from datetime import datetime, timedelta
from enum import Enum
from typing import Any

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

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

# Announcement intervals in minutes before backup
ANNOUNCEMENT_INTERVALS = [30, 15, 10, 5, 2, 1]


class SchedulerState(Enum):
    """Scheduler state enum."""
    STOPPED = "stopped"
    RUNNING = "running"
    PAUSED = "paused"


class VSMScheduler:
    """Background scheduler for VSM backups."""

    _instance: "VSMScheduler | None" = None

    def __init__(self) -> None:
        self._scheduler: BackgroundScheduler | None = None
        self._config: dict | None = None
        self._log_callback: Any = None

    @classmethod
    def get_instance(cls) -> "VSMScheduler":
        """Get the singleton scheduler instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def set_log_callback(self, callback: Any) -> None:
        """Set a callback for log messages."""
        self._log_callback = callback

    def _log(self, message: str) -> None:
        """Log a message."""
        if self._log_callback:
            self._log_callback(message)

    def get_state(self) -> SchedulerState:
        """Get the current scheduler state."""
        if self._scheduler is None:
            return SchedulerState.STOPPED
        if self._scheduler.running:
            return SchedulerState.RUNNING
        return SchedulerState.STOPPED

    def get_jobs(self) -> list[dict]:
        """Get list of scheduled jobs."""
        if self._scheduler is None:
            return []

        jobs = []
        for job in self._scheduler.get_jobs():
            job_info = {
                "id": job.id,
                "name": job.name,
                "next_run_time": job.next_run_time,
            }
            # Get trigger info
            if hasattr(job.trigger, "__str__"):
                job_info["trigger"] = str(job.trigger)
            else:
                job_info["trigger"] = "unknown"
            jobs.append(job_info)
        return jobs

    def advance_jobs(self, minutes: int = 1) -> int:
        """Advance all jobs by the specified number of minutes. Returns count of modified jobs."""
        if self._scheduler is None:
            return 0

        count = 0
        for job in self._scheduler.get_jobs():
            if job.next_run_time:
                new_time = job.next_run_time - timedelta(minutes=minutes)
                job.modify(next_run_time=new_time)
                self._log(f"Advanced job '{job.name}' to {new_time}")
                count += 1
        return count

    def start(self, config: dict | None = None) -> None:
        """Start the scheduler with backup jobs."""
        if self._scheduler is not None and self._scheduler.running:
            return

        if config is None:
            config = load_config()
        self._config = config

        self._scheduler = BackgroundScheduler()

        world_interval = config.get("world_backup_interval", 1)
        server_interval = config.get("server_backup_interval", 6)
        offset_hours = config.get("backup_offset_hours", 0)

        # Calculate backup hours based on interval and offset
        # e.g., server_interval=12, offset=5 -> backups at 5:00 and 17:00
        server_backup_hours = (
            {(offset_hours + i * server_interval) % 24 for i in range(24 // server_interval)}
            if server_interval > 0
            else set()
        )
        world_backup_hours = (
            {(offset_hours + i * world_interval) % 24 for i in range(24 // world_interval)}
            if world_interval > 0
            else set()
        )
        # World backups only run at hours when server backups don't
        world_only_hours = world_backup_hours - server_backup_hours

        # Schedule world backups (only at hours without server backups), 0 disables
        if world_interval > 0 and world_only_hours:
            world_hours_str = ",".join(str(h) for h in sorted(world_only_hours))
            self._scheduler.add_job(
                self._run_world_backup,
                CronTrigger(hour=world_hours_str, minute=0),
                id="world_backup",
                name="World Backup",
            )

        # Schedule server backups at calculated hours, 0 disables
        if server_interval > 0:
            server_hours_str = ",".join(str(h) for h in sorted(server_backup_hours))
            self._scheduler.add_job(
                self._run_server_backup,
                CronTrigger(hour=server_hours_str, minute=0),
                id="server_backup",
                name="Server Backup",
            )

            # Schedule announcements
            self._schedule_next_announcements()

            # Re-schedule announcements after each server backup
            self._scheduler.add_job(
                self._schedule_next_announcements,
                CronTrigger(hour=server_hours_str, minute=1),
                id="reschedule_announcements",
                name="Reschedule Announcements",
            )

        self._scheduler.start()
        self._log("Scheduler started")

    def stop(self) -> None:
        """Stop the scheduler."""
        if self._scheduler is not None:
            self._scheduler.shutdown(wait=False)
            self._scheduler = None
            self._log("Scheduler stopped")

    def _should_announce(self) -> bool:
        """Check if we should announce (only when players are online)."""
        try:
            players = get_players(self._config)
            return players > 0
        except Exception:
            return False

    def _send_announcement(self, minutes: int) -> None:
        """Send a backup announcement to players."""
        if not self._should_announce():
            return

        downtime_estimate = format_downtime_estimate(self._config)
        if minutes == 1:
            message = f"Server going offline for backup in 1 minute {downtime_estimate}".strip()
        else:
            message = f"Server going offline for backup in {minutes} minutes {downtime_estimate}".strip()

        try:
            announce(message, self._config)
            self._log(f"Announced: {message}")
        except Exception as e:
            self._log(f"Failed to announce: {e}")

    def _run_world_backup(self) -> None:
        """Run a world backup."""
        self._log(f"{datetime.now()} Running world backup...")

        try:
            result = world_backup(self._config)
            self._log("World backup complete")
        except Exception as e:
            self._log(f"World backup failed: {e}")

    def _run_server_backup(self) -> None:
        """Run a full server backup cycle with stop/start."""
        self._log(f"{datetime.now()} Starting server backup cycle...")

        try:
            # Record stop time and stop server
            record_stop_time(self._config)
            self._log("Stopping server...")
            stop(self._config)

            # Create backup
            self._log("Creating server backup...")
            result = server_backup(self._config)
            self._log(result)

            # Cleanup
            self._log("Cleaning up old data...")
            cleanup_result = cleanup_after_server_backup(self._config)
            if cleanup_result:
                self._log(cleanup_result)

            # Prune old backups
            prune_result = prune_old_backups(self._config)
            self._log(prune_result)

            # Restart server
            self._log("Starting server...")
            start(self._config)
            record_start_time(self._config)

            self._log("Server backup cycle complete")

        except Exception as e:
            self._log(f"Server backup failed: {e}")
            # Try to ensure server is running
            try:
                self._log("Attempting to restart server...")
                start(self._config)
            except Exception:
                pass

    def _schedule_next_announcements(self) -> None:
        """Schedule announcements before the next server backup."""
        if self._scheduler is None or self._config is None:
            return

        server_interval = self._config.get("server_backup_interval", 6)
        offset_hours = self._config.get("backup_offset_hours", 0)
        if server_interval <= 0:
            return
        now = datetime.now()

        # Calculate backup hours with offset
        backup_hours = sorted(
            (offset_hours + i * server_interval) % 24
            for i in range(24 // server_interval)
        )

        # Find the next backup hour
        current_hour = now.hour
        next_backup_hour = None
        for hour in backup_hours:
            if hour > current_hour:
                next_backup_hour = hour
                break

        # If no backup hour found today, use first backup hour tomorrow
        if next_backup_hour is None:
            next_backup_hour = backup_hours[0]
            next_backup = now.replace(
                hour=next_backup_hour, minute=0, second=0, microsecond=0
            ) + timedelta(days=1)
        else:
            next_backup = now.replace(
                hour=next_backup_hour, minute=0, second=0, microsecond=0
            )

        # Remove old announcement jobs
        for job in self._scheduler.get_jobs():
            if job.id.startswith("announce_"):
                job.remove()

        # Schedule new announcements
        for minutes in ANNOUNCEMENT_INTERVALS:
            announce_time = next_backup - timedelta(minutes=minutes)
            if announce_time > now:
                self._scheduler.add_job(
                    self._send_announcement,
                    "date",
                    run_date=announce_time,
                    args=[minutes],
                    id=f"announce_{minutes}",
                    name=f"Announce {minutes}m",
                )


def get_scheduler() -> VSMScheduler:
    """Get the global scheduler instance."""
    return VSMScheduler.get_instance()


# Legacy function for CLI compatibility
def run_scheduler() -> None:
    """Run the backup scheduler (blocking mode for CLI)."""
    import signal
    import sys
    from rich.console import Console

    console = Console()
    config = load_config()

    scheduler = get_scheduler()
    scheduler.set_log_callback(lambda msg: console.print(msg))

    console.print("[bold]Vintage Story Backup Scheduler[/bold]")
    console.print(f"World backup interval: every {config.get('world_backup_interval', 1)} hour(s)")
    console.print(f"Server backup interval: every {config.get('server_backup_interval', 6)} hour(s)")
    console.print("Press Ctrl+C to stop\n")

    scheduler.start(config)

    def shutdown(signum, frame):
        console.print("\n[yellow]Shutting down scheduler...[/yellow]")
        scheduler.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    try:
        # Keep main thread alive
        import time
        while True:
            time.sleep(1)
    except (KeyboardInterrupt, SystemExit):
        scheduler.stop()
