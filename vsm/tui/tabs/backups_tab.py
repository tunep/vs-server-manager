"""Backups tab for VSM TUI."""

from enum import Enum

from textual.app import ComposeResult
from textual.containers import Container, Horizontal
from textual.widgets import Button, DataTable, Static

from ...backup import list_backups, server_backup, world_backup
from ...config import load_config
from ...server import ServerStatus, start, status, stop
from ..screens.confirm_screen import ConfirmScreen
from ..workers import run_blocking
from .status_tab import StatusTab


class ServerState(Enum):
    """Possible server states."""

    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    UNKNOWN = "unknown"


def _get_server_state(server_status: ServerStatus | None) -> ServerState:
    """Determine the server state from a ServerStatus object."""
    if server_status is None:
        return ServerState.UNKNOWN

    if not server_status.running:
        return ServerState.STOPPED

    # Server is running - check if fully started (has version, uptime, memory)
    fully_running = (
        server_status.version
        and server_status.uptime
        and server_status.memory_managed
    )

    if fully_running:
        return ServerState.RUNNING
    else:
        return ServerState.STARTING


class BackupsTab(Container):
    """Backup management tab."""

    def compose(self) -> ComposeResult:
        """Create the backups tab layout."""
        yield Static("SERVER BACKUPS", classes="panel-title")
        yield DataTable(id="backup-table")
        with Horizontal(id="backup-controls"):
            yield Button("World Backup", id="btn-world-backup", variant="primary")
            yield Button("Server Backup", id="btn-server-backup", variant="warning")
            yield Button("Refresh", id="btn-refresh")

    def on_mount(self) -> None:
        """Initialize the backup table."""
        table = self.query_one("#backup-table", DataTable)
        table.add_columns("Filename", "Size", "Date")
        table.cursor_type = "row"
        self.refresh_backups()

    def refresh_backups(self) -> None:
        """Refresh the backup list."""
        self.run_worker(self._load_backups(), exclusive=True)

    async def _load_backups(self) -> None:
        """Load backups in background."""
        try:
            config = load_config()
            backups = await run_blocking(list_backups, config)
            self._update_table(backups)
        except Exception as e:
            self.notify(f"Failed to load backups: {e}", severity="error")

    def _update_table(self, backups: list) -> None:
        """Update the backup table."""
        table = self.query_one("#backup-table", DataTable)
        table.clear()

        if not backups:
            table.add_row("No backups found", "--", "--")
            return

        for backup_path in backups:
            size_mb = backup_path.stat().st_size / (1024 * 1024)
            mtime = backup_path.stat().st_mtime
            from datetime import datetime
            date_str = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M")
            table.add_row(
                backup_path.name,
                f"{size_mb:.1f} MB",
                date_str,
            )

    async def _get_current_server_state(self, config: dict) -> ServerState:
        """Get the current server state."""
        try:
            server_status = await run_blocking(status, config)
            return _get_server_state(server_status)
        except Exception:
            return ServerState.UNKNOWN

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        config = load_config()

        if event.button.id == "btn-world-backup":
            # World backup requires server to be fully running
            server_state = await self._get_current_server_state(config)

            if server_state != ServerState.RUNNING:
                self.notify(
                    "World backup requires the server to be fully online",
                    severity="warning",
                )
                return

            self.notify("Creating world backup...")
            try:
                await run_blocking(world_backup, config)
                self.notify("World backup created", severity="information")
            except Exception as e:
                self.notify(f"World backup failed: {e}", severity="error")

        elif event.button.id == "btn-server-backup":
            # Run in a worker so we can use push_screen_wait
            self.run_worker(self._handle_server_backup(config))

        elif event.button.id == "btn-refresh":
            self.refresh_backups()

    async def _handle_server_backup(self, config: dict) -> None:
        """Handle server backup with state validation and confirmation."""
        # Server backup requires server to be fully stopped or fully running
        server_state = await self._get_current_server_state(config)

        if server_state == ServerState.STARTING:
            self.notify(
                "Cannot create server backup while the server is starting",
                severity="warning",
            )
            return

        if server_state == ServerState.UNKNOWN:
            self.notify(
                "Cannot determine server status",
                severity="error",
            )
            return

        if server_state == ServerState.RUNNING:
            # Server is running, show confirmation dialog
            confirmed = await self.app.push_screen_wait(
                ConfirmScreen(
                    "Server Backup",
                    "The server is currently running.\n\n"
                    "Creating a server backup requires stopping the server.\n"
                    "The server will be restarted after the backup completes.\n\n"
                    "Do you want to continue?",
                )
            )
            if confirmed:
                await self._perform_server_backup_with_restart(config)
        else:
            # Server is stopped, proceed directly
            await self._perform_server_backup(config)

    async def _perform_server_backup(self, config: dict) -> None:
        """Perform a server backup without stop/start."""
        self.notify("Creating server backup (this may take a while)...")
        try:
            await run_blocking(server_backup, config)
            self.notify("Server backup created", severity="information")
            self.refresh_backups()
        except Exception as e:
            self.notify(f"Server backup failed: {e}", severity="error")

    def _get_status_tab(self) -> StatusTab | None:
        """Get the StatusTab instance from the app."""
        try:
            return self.app.query_one(StatusTab)
        except Exception:
            return None

    async def _perform_server_backup_with_restart(self, config: dict) -> None:
        """Stop server, perform backup, and restart."""
        status_tab = self._get_status_tab()

        try:
            # Set stopping state on StatusTab
            if status_tab:
                status_tab._stopping = True
                status_tab._update_display()

            self.notify("Stopping server...")
            await run_blocking(stop, config)

            # Clear stopping state
            if status_tab:
                status_tab._stopping = False
                status_tab._update_display()

            self.notify("Creating server backup (this may take a while)...")
            await run_blocking(server_backup, config)

            # Set starting state on StatusTab
            if status_tab:
                status_tab._starting = True
                status_tab._update_display()

            self.notify("Restarting server...")
            await run_blocking(start, config)

            self.notify("Server backup created and server restarted", severity="information")
            self.refresh_backups()
        except Exception as e:
            self.notify(f"Server backup failed: {e}", severity="error")
            # Try to restart the server even if backup failed
            try:
                if status_tab:
                    status_tab._starting = True
                    status_tab._update_display()

                self.notify("Attempting to restart server...")
                await run_blocking(start, config)
            except Exception:
                self.notify("Failed to restart server", severity="error")
        finally:
            # Reset states and refresh status
            if status_tab:
                status_tab._stopping = False
                status_tab._starting = False
                status_tab.refresh_status()
