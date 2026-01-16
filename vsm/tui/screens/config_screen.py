"""Configuration screen for VSM TUI."""

from textual.app import ComposeResult
from textual.containers import Vertical, Horizontal
from textual.screen import ModalScreen
from textual.widgets import Button, DataTable, Static, Input, Label

from ...config import load_config, save_config, get_config_path


class ConfigScreen(ModalScreen):
    """Modal screen for viewing and editing configuration."""

    BINDINGS = [
        ("escape", "cancel", "Cancel"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.config = load_config()
        self.editing_key: str | None = None

    def compose(self) -> ComposeResult:
        """Create the config dialog layout."""
        with Vertical(id="config-dialog"):
            yield Static("Configuration", classes="title")
            yield Static(f"[dim]{get_config_path()}[/dim]")
            yield DataTable(id="config-table")
            with Horizontal(id="config-buttons"):
                yield Button("Close", id="close-btn", variant="primary")

    def on_mount(self) -> None:
        """Initialize the config table."""
        table = self.query_one("#config-table", DataTable)
        table.add_columns("Setting", "Value")
        table.cursor_type = "row"
        self._populate_table()

    def _populate_table(self) -> None:
        """Populate the config table with current values."""
        table = self.query_one("#config-table", DataTable)
        table.clear()
        for key, value in self.config.items():
            table.add_row(key, str(value), key=key)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "close-btn":
            self.dismiss()

    def action_cancel(self) -> None:
        """Cancel and close the screen."""
        self.dismiss()
