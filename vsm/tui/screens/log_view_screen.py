"""A simple screen to display the contents of a log file."""

from pathlib import Path

from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.widgets import RichLog, Static


class LogViewScreen(ModalScreen):
    """A modal screen that displays the contents of a file."""

    BINDINGS = [("escape", "app.pop_screen", "Close")]

    def __init__(self, file_path: Path, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.file_path = file_path

    def compose(self) -> ComposeResult:
        """Create the log view screen layout."""
        yield Static(f"Log: {self.file_path.name}", classes="panel-title")
        log_viewer = RichLog(id="log-viewer", highlight=True, markup=True)
        log_viewer.border_title = self.file_path.name
        yield log_viewer

    def on_mount(self) -> None:
        """Load the log file content."""
        log_viewer = self.query_one("#log-viewer", RichLog)
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                log_viewer.write(f.read())
        except FileNotFoundError:
            log_viewer.write(f"[red]Log file not found: {self.file_path}[/red]")
        except Exception as e:
            log_viewer.write(f"[red]Error reading log file: {e}[/red]")
