"""Server configuration screen for VSM TUI."""

import json
from pathlib import Path

from textual.app import ComposeResult
from textual.containers import Vertical, Horizontal
from textual.screen import ModalScreen
from textual.widgets import Button, DataTable, Static, Input

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
        ("enter", "edit_selected", "Edit"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.config = load_server_config()
        self.original_config = self.config.copy()
        self.editing_key: str | None = None
        # Track which keys are editable (not dicts/lists)
        self.editable_keys: list[str] = []

    def compose(self) -> ComposeResult:
        """Create the server config dialog layout."""
        with Vertical(id="server-config-dialog"):
            yield Static("Server Configuration", classes="title")
            yield Static(f"[dim]{get_server_config_path()}[/dim]")
            yield Static("[dim]Press Enter to edit, Escape to cancel[/dim]", id="server-config-help")
            yield DataTable(id="server-config-table")
            with Horizontal(id="server-edit-container", classes="hidden"):
                yield Static("Value:", classes="edit-label")
                yield Input(id="server-edit-input", placeholder="Enter new value")
            with Horizontal(id="server-config-buttons"):
                yield Button("Save", id="save-btn", variant="success")
                yield Button("Cancel", id="cancel-btn", variant="default")

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
        self.editable_keys = []

        if not self.config:
            table.add_row("[dim]No config found[/dim]", "[dim]--[/dim]")
            return

        # Show key settings, skip complex nested objects for display
        for key, value in self.config.items():
            # Skip complex nested structures for cleaner display
            if isinstance(value, (dict, list)):
                if isinstance(value, list):
                    display_value = f"[dim][{len(value)} items][/dim]"
                else:
                    display_value = "[dim]{...}[/dim]"
                # Not editable
            elif value is None:
                display_value = "[dim]null[/dim]"
                self.editable_keys.append(key)
            elif isinstance(value, bool):
                display_value = "[green]true[/green]" if value else "[red]false[/red]"
                self.editable_keys.append(key)
            else:
                display_value = str(value)
                # Truncate long values for display
                if len(display_value) > 50:
                    display_value = display_value[:47] + "..."
                self.editable_keys.append(key)
            table.add_row(key, display_value, key=key)

    def _get_raw_value(self, key: str) -> str:
        """Get the raw value for editing (not formatted for display)."""
        value = self.config[key]
        if value is None:
            return "null"
        elif isinstance(value, bool):
            return "true" if value else "false"
        else:
            return str(value)

    def _parse_value(self, raw: str, original_value):
        """Parse a raw string value back to the appropriate type."""
        raw = raw.strip()

        # Handle null
        if raw.lower() == "null":
            return None

        # Handle booleans
        if raw.lower() in ("true", "false"):
            return raw.lower() == "true"

        # Try to preserve the original type
        if isinstance(original_value, int):
            try:
                return int(raw)
            except ValueError:
                pass
        elif isinstance(original_value, float):
            try:
                return float(raw)
            except ValueError:
                pass

        # Default to string
        return raw

    def _start_editing(self, key: str) -> None:
        """Start editing a config value."""
        if key not in self.editable_keys:
            self.app.notify("Cannot edit complex values (lists/objects)", severity="warning")
            return

        self.editing_key = key
        edit_container = self.query_one("#server-edit-container")
        edit_container.remove_class("hidden")
        edit_input = self.query_one("#server-edit-input", Input)
        edit_input.value = self._get_raw_value(key)
        edit_input.focus()

    def _stop_editing(self, save: bool = True) -> None:
        """Stop editing and optionally save the value."""
        if self.editing_key and save:
            edit_input = self.query_one("#server-edit-input", Input)
            original_value = self.config[self.editing_key]
            new_value = self._parse_value(edit_input.value, original_value)
            self.config[self.editing_key] = new_value
            self._populate_table()

        self.editing_key = None
        edit_container = self.query_one("#server-edit-container")
        edit_container.add_class("hidden")
        self.query_one("#server-config-table", DataTable).focus()

    def action_edit_selected(self) -> None:
        """Edit the currently selected row."""
        if self.editing_key:
            self._stop_editing(save=True)
            return

        if not self.config:
            return

        table = self.query_one("#server-config-table", DataTable)
        if table.cursor_row is not None:
            key = list(self.config.keys())[table.cursor_row]
            self._start_editing(key)

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle row double-click to edit."""
        if event.row_key and event.row_key.value:
            self._start_editing(str(event.row_key.value))

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle input submission."""
        if event.input.id == "server-edit-input":
            self._stop_editing(save=True)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "save-btn":
            if self.config:
                save_server_config(self.config)
                self.app.notify("Server configuration saved")
            self.dismiss()
        elif event.button.id == "cancel-btn":
            self.dismiss()

    def action_cancel(self) -> None:
        """Cancel and close the screen."""
        if self.editing_key:
            self._stop_editing(save=False)
        else:
            self.dismiss()
