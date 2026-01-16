"""Status tab for VSM TUI."""

from textual.app import ComposeResult
from textual.containers import Vertical, Horizontal
from textual.widgets import Button, Static
from textual.widget import Widget

from ...config import load_config
from ...server import ServerStatus, status, start, stop, restart
from ..workers import run_blocking


class StatusTab(Widget):
    """Server status and control tab."""

    DEFAULT_CSS = """
    StatusTab {
        layout: horizontal;
        height: 100%;
    }
    """

    def __init__(self) -> None:
        super().__init__()
        self._status: ServerStatus | None = None

    def compose(self) -> ComposeResult:
        """Create the status tab layout."""
        with Vertical(id="status-panel"):
            yield Static("SERVER STATUS", classes="panel-title")
            yield Static("Status: [dim]Loading...[/dim]", id="status-running")
            yield Static("Version: [dim]--[/dim]", id="status-version")
            yield Static("Uptime: [dim]--[/dim]", id="status-uptime")
            yield Static("Players: [dim]--[/dim]", id="status-players")
            yield Static("Memory: [dim]--[/dim]", id="status-memory")
        with Vertical(id="controls-panel"):
            yield Static("CONTROLS", classes="panel-title")
            with Horizontal():
                yield Button("Start", id="btn-start", variant="success")
                yield Button("Stop", id="btn-stop", variant="error")
                yield Button("Restart", id="btn-restart", variant="warning")

    def on_mount(self) -> None:
        """Start status refresh on mount."""
        self.refresh_status()
        self.set_interval(5, self.refresh_status)

    def refresh_status(self) -> None:
        """Refresh server status."""
        self.run_worker(self._fetch_status(), exclusive=True)

    async def _fetch_status(self) -> None:
        """Fetch status in background."""
        try:
            config = load_config()
            self._status = await run_blocking(status, config)
            self._update_display()
        except Exception as e:
            self._status = None
            self.query_one("#status-running", Static).update(
                f"Status: [red]Error: {e}[/red]"
            )

    def _update_display(self) -> None:
        """Update the status display."""
        if self._status is None:
            return

        s = self._status
        if s.running:
            self.query_one("#status-running", Static).update(
                "Status: [green]Running[/green]"
            )
            self.query_one("#status-version", Static).update(
                f"Version: {s.version or '--'}"
            )
            self.query_one("#status-uptime", Static).update(
                f"Uptime: {s.uptime or '--'}"
            )
            self.query_one("#status-players", Static).update(
                f"Players: {s.players_online} / {s.max_players}"
            )
            if s.memory_managed and s.memory_total:
                self.query_one("#status-memory", Static).update(
                    f"Memory: {s.memory_managed} / {s.memory_total}"
                )
            else:
                self.query_one("#status-memory", Static).update("Memory: --")
        else:
            self.query_one("#status-running", Static).update(
                "Status: [red]Stopped[/red]"
            )
            self.query_one("#status-version", Static).update("Version: --")
            self.query_one("#status-uptime", Static).update("Uptime: --")
            self.query_one("#status-players", Static).update("Players: --")
            self.query_one("#status-memory", Static).update("Memory: --")

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle control button presses."""
        button_id = event.button.id
        config = load_config()

        if button_id == "btn-start":
            self.notify("Starting server...")
            try:
                await run_blocking(start, config)
                self.notify("Server start command sent", severity="information")
            except Exception as e:
                self.notify(f"Failed to start: {e}", severity="error")

        elif button_id == "btn-stop":
            self.notify("Stopping server...")
            try:
                await run_blocking(stop, config)
                self.notify("Server stop command sent", severity="information")
            except Exception as e:
                self.notify(f"Failed to stop: {e}", severity="error")

        elif button_id == "btn-restart":
            self.notify("Restarting server...")
            try:
                await run_blocking(restart, config)
                self.notify("Server restart command sent", severity="information")
            except Exception as e:
                self.notify(f"Failed to restart: {e}", severity="error")

        # Refresh status after action
        self.set_timer(2, self.refresh_status)
