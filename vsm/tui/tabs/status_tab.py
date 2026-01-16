"""Status tab for VSM TUI."""

from textual.app import ComposeResult
from textual.containers import Container, Vertical
from textual.events import Key
from textual.widgets import Button, Static

from ...config import load_config
from ...server import ServerStatus, status, start, stop, restart
from ..workers import run_blocking


class StatusTab(Container):
    """Server status and control tab."""

    def __init__(self) -> None:
        super().__init__()
        self._status: ServerStatus | None = None
        self._starting: bool = False
        self._restarting: bool = False
        self._stopping: bool = False

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
            yield Button("Start", id="btn-start", variant="success")
            yield Button("Stop", id="btn-stop", variant="error")
            yield Button("Restart", id="btn-restart", variant="warning")

    def on_mount(self) -> None:
        """Start status refresh on mount."""
        self.refresh_status()
        self.set_interval(5, self.refresh_status)

    def refresh_status(self) -> None:
        """Refresh server status."""
        # Don't refresh if we're in a temporary state
        if self._starting or self._restarting or self._stopping:
            return
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
        if self._status is None and not self._restarting and not self._stopping:
            return

        s = self._status
        btn_start = self.query_one("#btn-start", Button)
        btn_stop = self.query_one("#btn-stop", Button)
        btn_restart = self.query_one("#btn-restart", Button)

        # Check if server is fully running (has version, uptime, and memory)
        fully_running = (
            s and s.running and s.version and s.uptime and s.memory_managed
        )

        if self._restarting:
            self.query_one("#status-running", Static).update(
                "Status: [yellow]Restarting[/yellow]"
            )
            self.query_one("#status-version", Static).update("Version: [dim]--[/dim]")
            self.query_one("#status-uptime", Static).update("Uptime: [dim]--[/dim]")
            self.query_one("#status-players", Static).update("Players: [dim]--[/dim]")
            self.query_one("#status-memory", Static).update("Memory: [dim]--[/dim]")
            btn_start.display = False
            btn_stop.display = False
            btn_restart.display = False
        elif self._stopping:
            self.query_one("#status-running", Static).update(
                "Status: [yellow]Stopping[/yellow]"
            )
            self.query_one("#status-version", Static).update("Version: [dim]--[/dim]")
            self.query_one("#status-uptime", Static).update("Uptime: [dim]--[/dim]")
            self.query_one("#status-players", Static).update("Players: [dim]--[/dim]")
            self.query_one("#status-memory", Static).update("Memory: [dim]--[/dim]")
            btn_start.display = False
            btn_stop.display = False
            btn_restart.display = False
        elif fully_running:
            # Server is fully up and running
            self._starting = False
            self.query_one("#status-running", Static).update(
                "Status: [green]Running[/green]"
            )
            self.query_one("#status-version", Static).update(
                f"Version: {s.version}"
            )
            self.query_one("#status-uptime", Static).update(
                f"Uptime: {s.uptime}"
            )
            self.query_one("#status-players", Static).update(
                f"Players: {s.players_online} / {s.max_players}"
            )
            self.query_one("#status-memory", Static).update(
                f"Memory: {s.memory_managed} / {s.memory_total}"
            )
            # Server is running: show Stop and Restart, hide Start
            btn_start.display = False
            btn_stop.display = True
            btn_restart.display = True
        elif self._starting or (s and s.running and not fully_running):
            # Server is starting up
            self._starting = True
            self.query_one("#status-running", Static).update(
                "Status: [yellow]Starting[/yellow]"
            )
            self.query_one("#status-version", Static).update("Version: [dim]--[/dim]")
            self.query_one("#status-uptime", Static).update("Uptime: [dim]--[/dim]")
            self.query_one("#status-players", Static).update("Players: [dim]--[/dim]")
            self.query_one("#status-memory", Static).update("Memory: [dim]--[/dim]")
            # Server is starting: hide all buttons
            btn_start.display = False
            btn_stop.display = False
            btn_restart.display = False
        else:
            # Server is stopped
            self._starting = False
            self.query_one("#status-running", Static).update(
                "Status: [red]Stopped[/red]"
            )
            self.query_one("#status-version", Static).update("Version: --")
            self.query_one("#status-uptime", Static).update("Uptime: --")
            self.query_one("#status-players", Static).update("Players: --")
            self.query_one("#status-memory", Static).update("Memory: --")
            # Server is stopped: show Start, hide Stop and Restart
            btn_start.display = True
            btn_stop.display = False
            btn_restart.display = False

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle control button presses."""
        button_id = event.button.id
        config = load_config()

        if button_id == "btn-start":
            self._starting = True
            self._update_display()
            self.notify("Starting server...")
            try:
                await run_blocking(start, config)
                self.notify("Server start command sent", severity="information")
            except Exception as e:
                self.notify(f"Failed to start: {e}", severity="error")
            finally:
                self._starting = False
                self.refresh_status()

        elif button_id == "btn-stop":
            self._stopping = True
            self._update_display()
            self.notify("Stopping server...")
            try:
                await run_blocking(stop, config)
                self.notify("Server stop command sent", severity="information")
            except Exception as e:
                self.notify(f"Failed to stop: {e}", severity="error")
            finally:
                self._stopping = False
                self.refresh_status()

        elif button_id == "btn-restart":
            self._restarting = True
            self._update_display()
            self.notify("Restarting server...")
            try:
                await run_blocking(restart, config)
                self.notify("Server restart command sent", severity="information")
            except Exception as e:
                self.notify(f"Failed to restart: {e}", severity="error")
            finally:
                self._restarting = False
                self.refresh_status()



    def on_key(self, event: Key) -> None:
        """Handle key events for arrow navigation in controls."""
        focused = self.app.focused

        # We only care about events when a button inside the controls-panel is focused
        if (
            not isinstance(focused, Button)
            or not focused.parent
            or focused.parent.id != "controls-panel"
        ):
            return

        if event.key not in ("up", "down"):
            return

        event.prevent_default()

        # Get only the visible buttons
        visible_buttons = [
            btn for btn in self.query("#controls-panel Button") if btn.display
        ]

        if not visible_buttons:
            return

        try:
            current_index = visible_buttons.index(focused)
        except ValueError:
            return

        if event.key == "down":
            next_index = (current_index + 1) % len(visible_buttons)
            visible_buttons[next_index].focus()
        elif event.key == "up":
            next_index = (current_index - 1 + len(visible_buttons)) % len(
                visible_buttons
            )
            visible_buttons[next_index].focus()
