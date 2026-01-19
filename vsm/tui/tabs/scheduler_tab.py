"""Scheduler tab for VSM TUI."""

from datetime import datetime, timedelta

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Button, DataTable, Static

from ...config import load_config
from ...scheduler import get_scheduler, SchedulerState


class SchedulerTab(Container):
    """Scheduler status and control tab."""

    def compose(self) -> ComposeResult:
        """Create the scheduler tab layout."""
        with Vertical(id="scheduler-status"):
            yield Static("SCHEDULER STATUS", classes="panel-title")
            yield Static("Status: [dim]Loading...[/dim]", id="sched-status")
            yield Static("Next backup: [dim]--[/dim]", id="sched-next")
        yield Static("SCHEDULED JOBS", classes="panel-title")
        yield DataTable(id="scheduler-jobs")
        with Horizontal(id="scheduler-controls"):
            yield Button("Start Scheduler", id="btn-start-sched", variant="success")
            yield Button("Stop Scheduler", id="btn-stop-sched", variant="error")
            yield Button("Refresh", id="btn-refresh-sched")

    def on_mount(self) -> None:
        """Initialize scheduler display."""
        table = self.query_one("#scheduler-jobs", DataTable)
        table.add_columns("Job", "Trigger", "Next Run")
        self.refresh_status()
        self.set_interval(10, self.refresh_status)

    def refresh_status(self) -> None:
        """Refresh scheduler status."""
        scheduler = get_scheduler()
        state = scheduler.get_state()

        # Update status
        status_widget = self.query_one("#sched-status", Static)
        if state == SchedulerState.RUNNING:
            status_widget.update("Status: [green]Running[/green]")
        elif state == SchedulerState.PAUSED:
            status_widget.update("Status: [yellow]Paused[/yellow]")
        else:
            status_widget.update("Status: [red]Stopped[/red]")

        # Update jobs table
        table = self.query_one("#scheduler-jobs", DataTable)
        table.clear()

        jobs = scheduler.get_jobs()
        if not jobs:
            table.add_row("No jobs scheduled", "--", "--")
            self.query_one("#sched-next", Static).update("Next backup: --")
        else:
            next_run = None
            for job in jobs:
                job_name = job.get("name", job.get("id", "Unknown"))
                trigger = job.get("trigger", "--")
                next_run_time = job.get("next_run_time")

                if next_run_time:
                    next_str = self._time_until(next_run_time)
                    if next_run is None or next_run_time < next_run:
                        next_run = next_run_time
                else:
                    next_str = "--"

                table.add_row(job_name, trigger, next_str)

            # Update next backup display
            if next_run:
                self.query_one("#sched-next", Static).update(
                    f"Next backup: {next_run.strftime('%H:%M')} ({self._time_until(next_run)})"
                )
            else:
                self.query_one("#sched-next", Static).update("Next backup: --")

    def _time_until(self, dt: datetime) -> str:
        """Get human-readable time until datetime."""
        # Use timezone-aware now if dt has timezone info
        if dt.tzinfo is not None:
            now = datetime.now(dt.tzinfo)
        else:
            now = datetime.now()
        diff = dt - now

        if diff.total_seconds() < 0:
            return "now"

        hours, remainder = divmod(int(diff.total_seconds()), 3600)
        minutes, _ = divmod(remainder, 60)

        if hours > 0:
            return f"in {hours}h {minutes}m"
        return f"in {minutes}m"

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        scheduler = get_scheduler()

        if event.button.id == "btn-start-sched":
            try:
                config = load_config()
                scheduler.start(config)
                self.notify("Scheduler started", severity="information")
                self.refresh_status()
            except Exception as e:
                self.notify(f"Failed to start scheduler: {e}", severity="error")

        elif event.button.id == "btn-stop-sched":
            try:
                scheduler.stop()
                self.notify("Scheduler stopped", severity="information")
                self.refresh_status()
            except Exception as e:
                self.notify(f"Failed to stop scheduler: {e}", severity="error")

        elif event.button.id == "btn-refresh-sched":
            self.refresh_status()
