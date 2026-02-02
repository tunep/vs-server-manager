"""A simple screen to display the contents of a log file with tailing."""

from pathlib import Path

from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.widgets import RichLog, Static

from ..workers import run_blocking


class LogViewScreen(ModalScreen):
    """A modal screen that displays the contents of a file with live tailing."""

    BINDINGS = [("escape", "app.pop_screen", "Close")]

    def __init__(self, file_path: Path, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.file_path = file_path
        self._file_position: int = 0
        self._poll_timer = None

    def compose(self) -> ComposeResult:
        """Create the log view screen layout."""
        yield Static(f"Log: {self.file_path.name}", classes="panel-title")
        log_viewer = RichLog(id="log-viewer", highlight=True, markup=True)
        log_viewer.border_title = self.file_path.name
        yield log_viewer

    def on_mount(self) -> None:
        """Load the log file content and start tailing."""
        self._load_initial_content()
        self._poll_timer = self.set_interval(0.5, self._poll_log)

    def _load_initial_content(self) -> None:
        """Load the initial log file content."""
        log_viewer = self.query_one("#log-viewer", RichLog)
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                content = f.read()
                if content:
                    log_viewer.write(content)
                self._file_position = f.tell()
        except FileNotFoundError:
            log_viewer.write(f"[red]Log file not found: {self.file_path}[/red]")
        except Exception as e:
            log_viewer.write(f"[red]Error reading log file: {e}[/red]")

    def _poll_log(self) -> None:
        """Poll for new log content."""
        self.run_worker(self._read_new_content(), exclusive=True)

    async def _read_new_content(self) -> None:
        """Read new content from the log file."""
        if not self.file_path.exists():
            return

        try:
            current_size = self.file_path.stat().st_size

            if current_size > self._file_position:
                content = await run_blocking(
                    self._read_file_chunk, self.file_path, self._file_position
                )
                if content:
                    log_viewer = self.query_one("#log-viewer", RichLog)
                    log_viewer.write(content)
                self._file_position = current_size
            elif current_size < self._file_position:
                # File was truncated, reset and reload
                self._file_position = 0
                log_viewer = self.query_one("#log-viewer", RichLog)
                log_viewer.clear()
                self._load_initial_content()
        except Exception:
            pass

    @staticmethod
    def _read_file_chunk(file_path: Path, start_pos: int) -> str:
        """Read a chunk of a file from a given position."""
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            f.seek(start_pos)
            return f.read()

    def on_unmount(self) -> None:
        """Clean up when screen is closed."""
        if self._poll_timer:
            self._poll_timer.stop()
