"""Logs tab for VSM TUI."""

from pathlib import Path

from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.widgets import Button, RichLog, Select
from textual.widget import Widget

from ...config import get_logs_path, load_config
from ..workers import run_blocking


def _get_active_log_files(logs_path: Path) -> list[Path]:
    """Get list of active (non-archived) log files."""
    if not logs_path.exists():
        return []
    return sorted(
        [f for f in logs_path.iterdir() if f.is_file() and f.suffix == ".txt"],
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )


class LogsTab(Widget):
    """Live logs viewer tab."""

    DEFAULT_CSS = """
    LogsTab {
        layout: vertical;
        height: 100%;
    }
    """

    def __init__(self) -> None:
        super().__init__()
        self._file_positions: dict[Path, int] = {}
        self._log_files: list[Path] = []
        self._following = True

    def compose(self) -> ComposeResult:
        """Create the logs tab layout."""
        with Horizontal(id="log-controls"):
            yield Select(
                [(("All Logs", "all"))],
                value="all",
                id="log-select",
                allow_blank=False,
            )
            yield Button("Clear", id="btn-clear")
            yield Button("Pause", id="btn-pause")
        yield RichLog(id="log-viewer", highlight=True, markup=True)

    def on_mount(self) -> None:
        """Initialize log viewer."""
        self._init_logs()
        self.set_interval(0.5, self._poll_logs)

    def _init_logs(self) -> None:
        """Initialize log file tracking."""
        config = load_config()
        logs_path = get_logs_path(config)
        self._log_files = _get_active_log_files(logs_path)

        # Update select options
        select = self.query_one("#log-select", Select)
        options = [("All Logs", "all")]
        for log_file in self._log_files:
            options.append((log_file.stem, str(log_file)))
        select.set_options(options)

        # Initialize file positions to current end
        for log_file in self._log_files:
            if log_file.exists():
                self._file_positions[log_file] = log_file.stat().st_size

        log_viewer = self.query_one("#log-viewer", RichLog)
        log_viewer.write("[dim]Watching log files...[/dim]")

    def _poll_logs(self) -> None:
        """Poll for new log content."""
        if not self._following:
            return

        self.run_worker(self._read_new_content(), exclusive=True)

    async def _read_new_content(self) -> None:
        """Read new content from log files."""
        select = self.query_one("#log-select", Select)
        selected = select.value
        log_viewer = self.query_one("#log-viewer", RichLog)

        for log_file in self._log_files:
            # Skip if filtering to specific file
            if selected != "all" and str(log_file) != selected:
                continue

            if not log_file.exists():
                continue

            try:
                current_size = log_file.stat().st_size
                last_pos = self._file_positions.get(log_file, 0)

                if current_size > last_pos:
                    content = await run_blocking(
                        self._read_file_chunk, log_file, last_pos
                    )
                    if content:
                        prefix = f"[cyan][{log_file.stem}][/cyan] "
                        for line in content.splitlines():
                            if line.strip():
                                log_viewer.write(f"{prefix}{line}")
                    self._file_positions[log_file] = current_size
                elif current_size < last_pos:
                    # File was truncated, reset position
                    self._file_positions[log_file] = 0
            except Exception:
                pass

    @staticmethod
    def _read_file_chunk(file_path: Path, start_pos: int) -> str:
        """Read a chunk of a file from a given position."""
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            f.seek(start_pos)
            return f.read()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "btn-clear":
            log_viewer = self.query_one("#log-viewer", RichLog)
            log_viewer.clear()
        elif event.button.id == "btn-pause":
            self._following = not self._following
            btn = self.query_one("#btn-pause", Button)
            btn.label = "Resume" if not self._following else "Pause"
