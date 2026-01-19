"""Log viewer functionality for Vintage Story Server Manager."""

import subprocess
import sys
import time
from pathlib import Path

from rich.console import Console
from rich.prompt import Prompt

from .config import get_logs_path, load_config

console = Console()


def _get_active_log_files(logs_path: Path) -> list[Path]:
    """Get list of active (non-archived) log files."""
    if not logs_path.exists():
        return []

    return sorted(
        [f for f in logs_path.iterdir() if f.is_file() and f.suffix == ".txt"],
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )


def _get_archive_folders(logs_path: Path) -> list[Path]:
    """Get list of archived log folders sorted by date (newest first)."""
    archive_path = logs_path / "Archive"
    if not archive_path.exists():
        return []

    return sorted(
        [d for d in archive_path.iterdir() if d.is_dir()],
        key=lambda p: p.name,
        reverse=True,
    )


def _get_log_files_in_folder(folder: Path) -> list[Path]:
    """Get log files in a specific folder."""
    return sorted(
        [f for f in folder.iterdir() if f.is_file()],
        key=lambda p: p.name,
    )


def tail_live(config: dict | None = None) -> None:
    """
    Follow active log files with streaming output.

    Press Ctrl+C to stop.
    """
    if config is None:
        config = load_config()

    logs_path = get_logs_path(config)
    log_files = _get_active_log_files(logs_path)

    if not log_files:
        console.print(f"[yellow]No active log files found in {logs_path}[/yellow]")
        return

    console.print(f"[bold]Tailing {len(log_files)} log file(s)[/bold]")
    console.print("Press Ctrl+C to stop\n")

    # Track file positions and state for each file
    file_positions: dict[Path, int] = {}
    in_block_states: dict[Path, bool] = {}

    for log_file in log_files:
        file_positions[log_file] = log_file.stat().st_size
        in_block_states[log_file] = False
        console.print(f"[dim]Watching: {log_file.name}[/dim]")

    console.print()

    try:
        while True:
            for log_file in log_files:
                if not log_file.exists():
                    continue

                current_size = log_file.stat().st_size
                last_pos = file_positions.get(log_file, 0)

                if current_size > last_pos:
                    with open(log_file, "r", encoding="utf-8", errors="replace") as f:
                        f.seek(last_pos)
                        new_content = f.read()
                        if new_content:
                            prefix = f"[cyan][{log_file.stem}][/cyan] "
                            is_server_main = log_file.stem == "server-main"

                            for line in new_content.splitlines():
                                if not is_server_main:
                                    console.print(f"{prefix}{line}")
                                    continue

                                # State machine for server-main.log
                                line_lower = line.lower()
                                in_block = in_block_states[log_file]

                                if in_block:
                                    if "memory usage managed/total:" in line_lower:
                                        in_block_states[log_file] = False
                                    # Discard line
                                elif "is up and running" in line_lower:
                                    in_block_states[log_file] = True
                                    # Discard line
                                elif "is not running" in line_lower:
                                    # Discard single-line status
                                    pass
                                else:
                                    console.print(f"{prefix}{line}")

                    file_positions[log_file] = current_size
            time.sleep(0.5)
    except KeyboardInterrupt:
        console.print("\n[yellow]Stopped tailing logs[/yellow]")


def browse_archives(config: dict | None = None) -> None:
    """
    Browse archived log folders interactively.

    Select a timestamped folder, then select a log file to view.
    """
    if config is None:
        config = load_config()

    logs_path = get_logs_path(config)
    archive_folders = _get_archive_folders(logs_path)

    if not archive_folders:
        console.print(
            f"[yellow]No archived logs found in {logs_path / 'Archive'}[/yellow]"
        )
        return

    # Display archive folders
    console.print("[bold]Archived Log Sessions[/bold]\n")
    for i, folder in enumerate(archive_folders, 1):
        file_count = len(list(folder.iterdir()))
        console.print(f"  {i}. {folder.name} ({file_count} files)")

    console.print(f"  0. Cancel\n")

    # Get folder selection
    choice = Prompt.ask("Select session", default="0")

    try:
        choice_num = int(choice)
        if choice_num == 0:
            return
        if choice_num < 1 or choice_num > len(archive_folders):
            console.print("[red]Invalid selection[/red]")
            return

        selected_folder = archive_folders[choice_num - 1]

    except ValueError:
        console.print("[red]Invalid input[/red]")
        return

    # Display files in selected folder
    log_files = _get_log_files_in_folder(selected_folder)

    if not log_files:
        console.print(f"[yellow]No log files in {selected_folder.name}[/yellow]")
        return

    console.print(f"\n[bold]Log Files in {selected_folder.name}[/bold]\n")
    for i, log_file in enumerate(log_files, 1):
        size_kb = log_file.stat().st_size / 1024
        console.print(f"  {i}. {log_file.name} ({size_kb:.1f} KB)")

    console.print(f"  0. Back\n")

    # Get file selection
    file_choice = Prompt.ask("Select file", default="0")

    try:
        file_choice_num = int(file_choice)
        if file_choice_num == 0:
            return browse_archives(config)  # Go back to folder selection
        if file_choice_num < 1 or file_choice_num > len(log_files):
            console.print("[red]Invalid selection[/red]")
            return

        selected_file = log_files[file_choice_num - 1]

    except ValueError:
        console.print("[red]Invalid input[/red]")
        return

    # View the selected file using system pager
    view_file(selected_file)


def view_file(file_path: Path) -> None:
    """View a file using the system pager or less, filtering status blocks."""
    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        if file_path.stem == "server-main":
            lines = f.readlines()
            filtered_lines = []
            in_block = False
            for line in lines:
                line_lower = line.lower()
                if "is up and running" in line_lower:
                    in_block = True
                    continue  # Start of block, discard
                if "is not running" in line_lower:
                    continue  # Single line block, discard

                if in_block:
                    if "memory usage managed/total:" in line_lower:
                        in_block = False
                    continue  # Line is inside block, discard

                filtered_lines.append(line)
            content = "".join(filtered_lines)
        else:
            content = f.read()

    pager_cmd = []
    if sys.platform == "win32":
        pager_cmd = ["more"]
    else:
        pager_cmd = ["less", "-R"]

    try:
        process = subprocess.Popen(pager_cmd, stdin=subprocess.PIPE, text=True)
        process.communicate(input=content)
    except (FileNotFoundError, Exception):
        console.print(content)
