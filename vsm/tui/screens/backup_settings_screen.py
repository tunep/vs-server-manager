"""Backup settings modal screen for scheduler tab."""

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
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


def generate_timeline(
    server_interval: int, world_interval: int, offset_hours: int
) -> tuple[str, str, str]:
    """Generate a 48-character timeline showing backup schedule.

    Returns a tuple of (time_axis, timeline_bar, legend).
    """
    # Calculate backup hours
    server_hours: set[int] = set()
    world_hours: set[int] = set()

    if server_interval > 0:
        for i in range(24 // server_interval):
            server_hours.add((offset_hours + i * server_interval) % 24)

    if world_interval > 0:
        for i in range(24 // world_interval):
            world_hours.add((offset_hours + i * world_interval) % 24)

    # World-only hours (world backups that don't overlap with server)
    world_only_hours = world_hours - server_hours

    # Build 48-char timeline (2 chars per hour)
    timeline_chars = []
    for hour in range(24):
        if hour in server_hours:
            timeline_chars.append("[cyan]██[/]")
        elif hour in world_only_hours:
            timeline_chars.append("[green]▓▓[/]")
        else:
            timeline_chars.append("[dim]··[/]")

    timeline_bar = "".join(timeline_chars)

    # Time axis with markers at 0, 6, 12, 18, 24
    time_axis = "0     6     12    18    24"

    # Build legend based on what's shown
    legend_parts = []
    if server_hours:
        legend_parts.append("[cyan]██[/] Server+World")
    if world_only_hours:
        legend_parts.append("[green]▓▓[/] World only")
    if not server_hours and not world_only_hours:
        legend_parts.append("[dim]No backups scheduled[/]")

    legend = "  ".join(legend_parts)

    return time_axis, timeline_bar, legend


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

            # Timeline preview
            yield Static("Schedule Preview (24h):", classes="setting-label")
            time_axis, timeline_bar, legend = generate_timeline(
                self.server_interval, self.world_interval, self.offset_hours
            )
            with Vertical(id="timeline-container"):
                yield Static(time_axis, id="timeline-axis")
                yield Static(timeline_bar, id="timeline-bar")
                yield Static(legend, id="timeline-legend")

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

    def _update_timeline(self) -> None:
        """Update the timeline preview based on current settings."""
        time_axis, timeline_bar, legend = generate_timeline(
            self.server_interval, self.world_interval, self.offset_hours
        )
        self.query_one("#timeline-axis", Static).update(time_axis)
        self.query_one("#timeline-bar", Static).update(timeline_bar)
        self.query_one("#timeline-legend", Static).update(legend)

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

            self._update_timeline()

        elif event.select.id == "world-interval-select":
            if event.value != Select.BLANK:
                self.world_interval = event.value
                self._update_timeline()

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
                self._update_timeline()
        elif event.button.id == "offset-plus":
            max_offset = self._get_max_offset()
            if self.offset_hours < max_offset:
                self.offset_hours += 1
                self._update_offset_display()
                self._update_timeline()

    def action_cancel(self) -> None:
        """Cancel and close the screen."""
        self.dismiss(False)
