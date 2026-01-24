"""Backup settings modal screen for scheduler tab."""

from textual.app import ComposeResult
from textual.containers import Vertical, Horizontal
from textual.screen import ModalScreen
from textual.widgets import Button, Select, Static

from ...config import load_config, save_config


# Server backup interval options (in hours)
SERVER_BACKUP_OPTIONS = [0, 4, 6, 8, 12, 24]


def get_divisors(n: int) -> list[int]:
    """Get all divisors of n that are less than n."""
    if n == 0:
        return []
    divisors = []
    for i in range(1, n):
        if n % i == 0:
            divisors.append(i)
    return divisors


def get_world_backup_options(server_interval: int) -> list[int]:
    """Get world backup interval options based on server backup interval.

    World backups should be divisors of server backup interval so they align.
    If server backups are disabled, world backups can run at any common interval.
    """
    if server_interval == 0:
        # If server backups disabled, allow common intervals
        return [0, 1, 2, 3, 4, 6, 8, 12, 24]
    return [0] + get_divisors(server_interval)


class BackupSettingsScreen(ModalScreen[bool]):
    """Modal screen for editing backup interval settings."""

    BINDINGS = [
        ("escape", "cancel", "Cancel"),
    ]

    def __init__(self) -> None:
        super().__init__()
        config = load_config()
        self.server_interval = config.get("server_backup_interval", 6)
        self.world_interval = config.get("world_backup_interval", 1)
        self.offset_hours = config.get("backup_offset_hours", 0)

    def compose(self) -> ComposeResult:
        """Create the settings dialog layout."""
        with Vertical(id="backup-settings-dialog"):
            yield Static("[bold]Backup Settings[/bold]", classes="title")

            yield Static("Server Backup Interval:", classes="setting-label")
            server_options = [
                (self._format_interval(h), h) for h in SERVER_BACKUP_OPTIONS
            ]
            yield Select(
                server_options,
                id="server-interval-select",
                value=self.server_interval,
                allow_blank=False,
            )

            yield Static("World Backup Interval:", classes="setting-label")
            world_options = [
                (self._format_interval(h), h)
                for h in get_world_backup_options(self.server_interval)
            ]
            yield Select(
                world_options,
                id="world-interval-select",
                value=self.world_interval,
                allow_blank=False,
            )

            yield Static("Schedule Offset:", classes="setting-label")
            with Horizontal(id="offset-controls"):
                yield Button("-", id="offset-minus", classes="offset-btn")
                yield Static(self._format_offset(), id="offset-value")
                yield Button("+", id="offset-plus", classes="offset-btn")

            with Horizontal(id="backup-settings-buttons"):
                yield Button("Save", id="save-btn", variant="success")
                yield Button("Cancel", id="cancel-btn", variant="default")

    def _format_interval(self, hours: int) -> str:
        """Format interval for display."""
        if hours == 0:
            return "Disabled"
        elif hours == 1:
            return "Every 1 hour"
        else:
            return f"Every {hours} hours"

    def _format_offset(self) -> str:
        """Format offset for display."""
        if self.offset_hours == 1:
            return "1 hour"
        return f"{self.offset_hours} hours"

    def _get_max_offset(self) -> int:
        """Get the maximum allowed offset based on server interval."""
        if self.server_interval <= 0:
            return 23  # Max offset when disabled
        return self.server_interval - 1

    def _update_offset_display(self) -> None:
        """Update the offset display."""
        offset_widget = self.query_one("#offset-value", Static)
        offset_widget.update(self._format_offset())

    def on_select_changed(self, event: Select.Changed) -> None:
        """Handle select changes."""
        if event.select.id == "server-interval-select":
            new_server_interval = event.value
            if new_server_interval == Select.BLANK:
                return

            self.server_interval = new_server_interval

            # Update world backup options based on new server interval
            world_select = self.query_one("#world-interval-select", Select)
            new_world_options = [
                (self._format_interval(h), h)
                for h in get_world_backup_options(new_server_interval)
            ]
            world_select.set_options(new_world_options)

            # Reset world interval if current value is no longer valid
            valid_values = [opt[1] for opt in new_world_options]
            if self.world_interval not in valid_values:
                # Default to first non-zero option if available, else 0
                self.world_interval = valid_values[1] if len(valid_values) > 1 else 0
            world_select.value = self.world_interval

            # Clamp offset to new max
            max_offset = self._get_max_offset()
            if self.offset_hours > max_offset:
                self.offset_hours = max_offset
                self._update_offset_display()

        elif event.select.id == "world-interval-select":
            if event.value != Select.BLANK:
                self.world_interval = event.value

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "save-btn":
            # Save to config
            config = load_config()
            config["server_backup_interval"] = self.server_interval
            config["world_backup_interval"] = self.world_interval
            config["backup_offset_hours"] = self.offset_hours
            save_config(config)
            self.dismiss(True)
        elif event.button.id == "cancel-btn":
            self.dismiss(False)
        elif event.button.id == "offset-minus":
            if self.offset_hours > 0:
                self.offset_hours -= 1
                self._update_offset_display()
        elif event.button.id == "offset-plus":
            max_offset = self._get_max_offset()
            if self.offset_hours < max_offset:
                self.offset_hours += 1
                self._update_offset_display()

    def action_cancel(self) -> None:
        """Cancel and close the screen."""
        self.dismiss(False)
