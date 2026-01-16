"""Backups tab for VSM TUI."""

from textual.app import ComposeResult
from textual.containers import Container, Horizontal
from textual.widgets import Button, DataTable, Static

from ...backup import list_backups, server_backup, world_backup
from ...config import load_config
from ..workers import run_blocking


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

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        config = load_config()

        if event.button.id == "btn-world-backup":
            self.notify("Creating world backup...")
            try:
                result = await run_blocking(world_backup, config)
                self.notify("World backup created", severity="information")
            except Exception as e:
                self.notify(f"World backup failed: {e}", severity="error")

        elif event.button.id == "btn-server-backup":
            self.notify("Creating server backup (this may take a while)...")
            try:
                result = await run_blocking(server_backup, config)
                self.notify("Server backup created", severity="information")
                self.refresh_backups()
            except Exception as e:
                self.notify(f"Server backup failed: {e}", severity="error")

        elif event.button.id == "btn-refresh":
            self.refresh_backups()
