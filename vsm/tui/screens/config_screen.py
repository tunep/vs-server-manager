"""Configuration screen for VSM TUI."""

from textual.app import ComposeResult
from textual.containers import Vertical, Horizontal
from textual.screen import ModalScreen
from textual.widgets import Button, DataTable, Static, Input

from ...config import load_config, save_config, get_config_path


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
        self.editing_key: str | None = None

    def compose(self) -> ComposeResult:
        """Create the config dialog layout."""
        with Vertical(id="config-dialog"):
            yield Static("Configuration", classes="title")
            yield Static(f"[dim]{get_config_path()}[/dim]")
            yield Static("[dim]Press Enter to edit, Escape to cancel[/dim]", id="config-help")
            yield DataTable(id="config-table")
            with Horizontal(id="edit-container", classes="hidden"):
                yield Static("Value:", classes="edit-label")
                yield Input(id="edit-input", placeholder="Enter new value")
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

    def _start_editing(self, key: str) -> None:
        """Start editing a config value."""
        self.editing_key = key
        edit_container = self.query_one("#edit-container")
        edit_container.remove_class("hidden")
        edit_input = self.query_one("#edit-input", Input)
        edit_input.value = str(self.config[key])
        edit_input.focus()

    def _stop_editing(self, save: bool = True) -> None:
        """Stop editing and optionally save the value."""
        if self.editing_key and save:
            edit_input = self.query_one("#edit-input", Input)
            new_value = edit_input.value
            old_value = self.config[self.editing_key]

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

            self.config[self.editing_key] = new_value
            self._populate_table()

        self.editing_key = None
        edit_container = self.query_one("#edit-container")
        edit_container.add_class("hidden")
        self.query_one("#config-table", DataTable).focus()

    def action_edit_selected(self) -> None:
        """Edit the currently selected row."""
        if self.editing_key:
            self._stop_editing(save=True)
            return

        table = self.query_one("#config-table", DataTable)
        if table.cursor_row is not None:
            row_key = table.get_row_at(table.cursor_row)
            if row_key:
                key = list(self.config.keys())[table.cursor_row]
                self._start_editing(key)

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle row double-click to edit."""
        if event.row_key and event.row_key.value:
            self._start_editing(str(event.row_key.value))

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle input submission."""
        if event.input.id == "edit-input":
            self._stop_editing(save=True)

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
        if self.editing_key:
            self._stop_editing(save=False)
        else:
            self.dismiss()
