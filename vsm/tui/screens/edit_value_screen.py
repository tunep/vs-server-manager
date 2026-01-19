"""Edit value modal screen for config editors."""

from textual.app import ComposeResult
from textual.containers import Vertical, Horizontal
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Static


class EditValueScreen(ModalScreen[str | None]):
    """Modal screen for editing a single config value."""

    BINDINGS = [
        ("escape", "cancel", "Cancel"),
    ]

    def __init__(self, key: str, value: str) -> None:
        super().__init__()
        self.key = key
        self.initial_value = value

    def compose(self) -> ComposeResult:
        """Create the edit dialog layout."""
        with Vertical(id="edit-value-dialog"):
            yield Static(f"Edit: [bold]{self.key}[/bold]", classes="title")
            yield Input(id="edit-value-input", value=self.initial_value)
            with Horizontal(id="edit-value-buttons"):
                yield Button("Save", id="save-btn", variant="success")
                yield Button("Cancel", id="cancel-btn", variant="default")

    def on_mount(self) -> None:
        """Focus the input on mount."""
        input_widget = self.query_one("#edit-value-input", Input)
        input_widget.focus()
        input_widget.cursor_position = len(self.initial_value)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle input submission with Enter."""
        if event.input.id == "edit-value-input":
            self.dismiss(event.input.value)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "save-btn":
            input_widget = self.query_one("#edit-value-input", Input)
            self.dismiss(input_widget.value)
        elif event.button.id == "cancel-btn":
            self.dismiss(None)

    def action_cancel(self) -> None:
        """Cancel and close the screen."""
        self.dismiss(None)
