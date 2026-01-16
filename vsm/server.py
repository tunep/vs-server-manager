"""Server control operations for Vintage Story Server Manager."""

import re
import subprocess
from dataclasses import dataclass

from .config import get_server_executable, load_config


@dataclass
class ServerStatus:
    """Server status information."""

    running: bool
    version: str | None = None
    uptime: str | None = None
    players_online: int = 0
    max_players: int = 0
    memory_managed: str | None = None
    memory_total: str | None = None


def _run_server_command(args: list[str], config: dict | None = None) -> str:
    """Run a server.sh command and return the output."""
    if config is None:
        config = load_config()

    server_sh = get_server_executable(config)

    if not server_sh.exists():
        raise FileNotFoundError(f"Server executable not found: {server_sh}")

    result = subprocess.run(
        [str(server_sh)] + args,
        capture_output=True,
        text=True,
    )

    return result.stdout + result.stderr


def start(config: dict | None = None) -> str:
    """Start the server."""
    return _run_server_command(["start"], config)


def stop(config: dict | None = None) -> str:
    """Stop the server."""
    return _run_server_command(["stop"], config)


def restart(config: dict | None = None) -> str:
    """Restart the server (stop then start)."""
    return _run_server_command(["restart"], config)


def status(config: dict | None = None) -> ServerStatus:
    """Get the server status by running server.sh status and parsing output."""
    output = _run_server_command(["status"], config)

    # Check if server is running
    running = "is up and running" in output

    if not running:
        return ServerStatus(running=False)

    # Parse version
    version_match = re.search(r"Version:\s*(\S+)", output)
    version = version_match.group(1) if version_match else None

    # Parse uptime
    uptime_match = re.search(r"Uptime:\s*(.+?)(?:\n|$)", output)
    uptime = uptime_match.group(1).strip() if uptime_match else None

    # Parse players
    players_match = re.search(r"Players online:\s*(\d+)\s*/\s*(\d+)", output)
    if players_match:
        players_online = int(players_match.group(1))
        max_players = int(players_match.group(2))
    else:
        players_online = 0
        max_players = 0

    # Parse memory
    memory_match = re.search(
        r"Memory usage Managed/Total:\s*(\S+)\s*/\s*(\S+)", output
    )
    if memory_match:
        memory_managed = memory_match.group(1)
        memory_total = memory_match.group(2)
    else:
        memory_managed = None
        memory_total = None

    return ServerStatus(
        running=True,
        version=version,
        uptime=uptime,
        players_online=players_online,
        max_players=max_players,
        memory_managed=memory_managed,
        memory_total=memory_total,
    )


def command(cmd: str, config: dict | None = None) -> str:
    """Send a command to the running server."""
    return _run_server_command(["command", cmd], config)


def get_players(config: dict | None = None) -> int:
    """Get the number of players currently online by running 'list clients'."""
    output = command("list clients", config)

    # Count player lines (format: [id] PlayerName IP:Port)
    player_lines = re.findall(r"^\[\d+\]\s+\S+\s+\S+:\d+$", output, re.MULTILINE)
    return len(player_lines)


def announce(message: str, config: dict | None = None) -> str:
    """Send an announcement to all players."""
    return command(f"announce {message}", config)
