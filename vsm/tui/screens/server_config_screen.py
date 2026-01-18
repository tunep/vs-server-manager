"""Server configuration screen for VSM TUI."""

import json
from pathlib import Path

from textual.app import ComposeResult
from textual.containers import Vertical, Horizontal
from textual.screen import ModalScreen
from textual.widgets import Button, DataTable, Static

from ...config import load_config, get_data_path


def get_server_config_path() -> Path:
    """Get the path to the server config file."""
    config = load_config()
    return get_data_path(config) / "serverconfig.json"


def load_server_config() -> dict:
    """Load server configuration from serverconfig.json."""
    config_path = get_server_config_path()

    if not config_path.exists():
        return {}

    with open(config_path, "r") as f:
        return json.load(f)


def save_server_config(config: dict) -> None:
    """Save server configuration to serverconfig.json."""
    config_path = get_server_config_path()
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)


class ServerConfigScreen(ModalScreen):
    """Modal screen for viewing and editing server configuration."""

    BINDINGS = [
        ("escape", "cancel", "Cancel"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.config = load_server_config()
        self.editing_key: str | None = None

    def compose(self) -> ComposeResult:
        """Create the server config dialog layout."""
        with Vertical(id="server-config-dialog"):
            yield Static("Server Configuration", classes="title")
            yield Static(f"[dim]{get_server_config_path()}[/dim]")
            yield DataTable(id="server-config-table")
            with Horizontal(id="server-config-buttons"):
                yield Button("Close", id="close-btn", variant="primary")

    def on_mount(self) -> None:
        """Initialize the config table."""
        table = self.query_one("#server-config-table", DataTable)
        table.add_columns("Setting", "Value")
        table.cursor_type = "row"
        self._populate_table()

    def _populate_table(self) -> None:
        """Populate the config table with current values."""
        table = self.query_one("#server-config-table", DataTable)
        table.clear()

        if not self.config:
            table.add_row("[dim]No config found[/dim]", "[dim]--[/dim]")
            return

        # Show key settings, skip complex nested objects for display
        for key, value in self.config.items():
            # Skip complex nested structures for cleaner display
            if isinstance(value, (dict, list)):
                if isinstance(value, list):
                    display_value = f"[{len(value)} items]"
                else:
                    display_value = f"{{...}}"
            elif value is None:
                display_value = "[dim]null[/dim]"
            elif isinstance(value, bool):
                display_value = "[green]true[/green]" if value else "[red]false[/red]"
            else:
                display_value = str(value)
                # Truncate long values
                if len(display_value) > 40:
                    display_value = display_value[:37] + "..."
            table.add_row(key, display_value, key=key)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "close-btn":
            self.dismiss()

    def action_cancel(self) -> None:
        """Cancel and close the screen."""
        self.dismiss()
