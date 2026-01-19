"""Configuration screen for VSM TUI."""

from textual.app import ComposeResult
from textual.containers import Vertical, Horizontal
from textual.screen import ModalScreen
from textual.widgets import Button, DataTable, Static

from ...config import load_config, save_config, get_config_path
from .edit_value_screen import EditValueScreen


class ConfigScreen(ModalScreen):
    """Modal screen for viewing and editing configuration."""

    BINDINGS = [
        ("escape", "cancel", "Cancel"),
        ("enter", "edit_selected", "Edit"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.config = load_config()
        self.original_config = self.config.copy()

    def compose(self) -> ComposeResult:
        """Create the config dialog layout."""
        with Vertical(id="config-dialog"):
            yield Static("Configuration", classes="title")
            yield Static(f"[dim]{get_config_path()}[/dim]")
            yield Static("[dim]Press Enter to edit, Escape to cancel[/dim]", id="config-help")
            yield DataTable(id="config-table")
            with Horizontal(id="config-buttons"):
                yield Button("Save", id="save-btn", variant="success")
                yield Button("Cancel", id="cancel-btn", variant="default")

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

    def _open_edit_modal(self, key: str) -> None:
        """Open the edit modal for a config value."""
        current_value = str(self.config[key])

        def handle_edit_result(new_value: str | None) -> None:
            if new_value is not None:
                old_value = self.config[key]
                # Try to preserve the original type
                if isinstance(old_value, int):
                    try:
                        new_value = int(new_value)
                    except ValueError:
                        pass
                elif isinstance(old_value, float):
                    try:
                        new_value = float(new_value)
                    except ValueError:
                        pass
                self.config[key] = new_value
                self._populate_table()

        self.app.push_screen(EditValueScreen(key, current_value), handle_edit_result)

    def action_edit_selected(self) -> None:
        """Edit the currently selected row."""
        table = self.query_one("#config-table", DataTable)
        if table.cursor_row is not None:
            key = list(self.config.keys())[table.cursor_row]
            self._open_edit_modal(key)

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle row double-click to edit."""
        if event.row_key and event.row_key.value:
            self._open_edit_modal(str(event.row_key.value))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "save-btn":
            save_config(self.config)
            self.app.notify("Configuration saved")
            self.dismiss()
        elif event.button.id == "cancel-btn":
            self.dismiss()

    def action_cancel(self) -> None:
        """Cancel and close the screen."""
        self.dismiss()
