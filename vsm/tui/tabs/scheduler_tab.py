"""Scheduler tab for VSM TUI."""

import subprocess
import sys
from datetime import datetime
from pathlib import Path

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Button, DataTable, Static

from ...config import get_config_path, load_config
from ...rpc import SchedulerRPCClient
from ...scheduler import SchedulerState
from ..screens.log_view_screen import LogViewScreen


class SchedulerTab(Container):
    """Scheduler status and control tab."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.rpc_client = SchedulerRPCClient(load_config())
        self.log_file = get_config_path().parent / "vsm-scheduler.log"

    def compose(self) -> ComposeResult:
        """Create the scheduler tab layout."""
        with Vertical(id="scheduler-status"):
            yield Static("SCHEDULER DAEMON", classes="panel-title")
            yield Static("Status: [dim]Loading...[/dim]", id="sched-status")
            yield Static("Next backup: [dim]--[/dim]", id="sched-next")
        yield Static("SCHEDULED JOBS", classes="panel-title")
        yield DataTable(id="scheduler-jobs")
        with Horizontal(id="scheduler-controls"):
            yield Button("Start Daemon", id="btn-start-sched", variant="success")
            yield Button("Stop Daemon", id="btn-stop-sched", variant="error")
            yield Button("Postpone 5m", id="btn-advance-jobs", variant="warning")
            yield Button("View Log", id="btn-view-log")

    def on_mount(self) -> None:
        """Initialize scheduler display."""
        table = self.query_one("#scheduler-jobs", DataTable)
        table.add_columns("Job", "Trigger", "Next Run")
        self.refresh_status()
        self.set_interval(1, self.refresh_status)

    def refresh_status(self) -> None:
        """Refresh scheduler status via RPC."""
        status_widget = self.query_one("#sched-status", Static)
        table = self.query_one("#scheduler-jobs", DataTable)
        next_backup_widget = self.query_one("#sched-next", Static)

        status_response = self.rpc_client.get_status()

        if status_response.get("error"):
            status_widget.update("Status: [red]Daemon Unreachable[/red]")
            table.clear()
            table.add_row("Could not connect to scheduler daemon.", "", "")
            next_backup_widget.update("Next backup: --")
            return

        state = status_response.get("status")

        if state == SchedulerState.RUNNING.value:
            status_widget.update("Status: [green]Running[/green]")
        else:
            status_widget.update(f"Status: [yellow]{state.capitalize() if state else 'Unknown'}[/yellow]")

        # Update jobs table
        table.clear()
        jobs = self.rpc_client.get_jobs()

        if not jobs:
            table.add_row("No jobs scheduled", "--", "--")
            next_backup_widget.update("Next backup: --")
        else:
            next_run = None
            for job in jobs:
                job_name = job.get("name", job.get("id", "Unknown"))
                trigger = job.get("trigger", "--")
                next_run_time = job.get("next_run_time")

                if next_run_time:
                    # next_run_time is already a datetime object from the client
                    next_str = self._time_until(next_run_time)
                    if next_run is None or next_run_time < next_run:
                        next_run = next_run_time
                else:
                    next_str = "--"

                table.add_row(job_name, trigger, next_str)

            # Update next backup display
            if next_run:
                next_backup_widget.update(
                    f"Next backup: {next_run.strftime('%H:%M')} ({self._time_until(next_run)})"
                )
            else:
                next_backup_widget.update("Next backup: --")

    def _time_until(self, dt: datetime) -> str:
        """Get human-readable time until datetime."""
        if dt.tzinfo:
            now = datetime.now(dt.tzinfo)
        else:
            now = datetime.now()

        if dt.tzinfo is None and now.tzinfo is not None:
            now = now.astimezone(None)

        diff = dt - now

        if diff.total_seconds() < 0:
            return "recently"

        seconds = int(diff.total_seconds())
        hours, remainder = divmod(seconds, 3600)
        minutes, _ = divmod(remainder, 60)

        if hours > 0:
            return f"in {hours}h {minutes}m"
        if minutes > 0:
            return f"in {minutes}m"
        return "in <1m"

    def _run_command(self, command: list[str]):
        """Run a shell command and notify the user."""
        try:
            # Use the same Python executable that's running the TUI
            process = subprocess.Popen(
                [sys.executable, "-m", "vsm.daemon"] + command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8'
            )
            stdout, stderr = process.communicate(timeout=20)

            if process.returncode == 0:
                self.notify(f"Command '{' '.join(command)}' successful.", severity="information")
                if stdout:
                    self.notify(stdout.strip(), title="Output")
            else:
                self.notify(f"Command '{' '.join(command)}' failed.", severity="error", timeout=10)
                error_message = stderr.strip() if stderr else "No error output."
                self.notify(error_message, title="Error Output", timeout=10)

        except FileNotFoundError:
            self.notify("Error: 'vsm-scheduler' command not found in PATH.", severity="error")
        except subprocess.TimeoutExpired:
            self.notify("Command timed out.", severity="error")
        except Exception as e:
            self.notify(f"An unexpected error occurred: {e}", severity="error")

        self.refresh_status()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "btn-start-sched":
            self.notify("Attempting to start daemon in background...")
            self._run_command(["start"])
        elif event.button.id == "btn-stop-sched":
            self.notify("Attempting to stop daemon...")
            self._run_command(["stop"])
        elif event.button.id == "btn-advance-jobs":
            result = self.rpc_client.advance_jobs(5)
            if result.get("error"):
                self.notify(f"Failed to postpone jobs: {result['error'].get('message', 'Unknown error')}", severity="error")
            else:
                count = result.get("advanced", 0)
                self.notify(f"Postponed {count} job(s) by 5 minutes.")
            self.refresh_status()
        elif event.button.id == "btn-view-log":
            self.app.push_screen(LogViewScreen(self.log_file))

