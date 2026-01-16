"""CLI entry point for Vintage Story Server Manager."""

import json
import os
import subprocess
import sys

import click
from rich.console import Console
from rich.table import Table

from . import __version__
from .backup import list_backups, prune_old_backups, server_backup, world_backup
from .config import get_config_path, load_config
from .logs import browse_archives, tail_live
from .scheduler import run_scheduler
from .server import command as server_command
from .server import restart, start, status, stop

console = Console()


@click.group()
@click.version_option(version=__version__, prog_name="vsm")
def cli():
    """Vintage Story Server Manager - CLI tool for managing VS dedicated servers."""
    pass


# =============================================================================
# Server Control Commands
# =============================================================================


@cli.command()
def server_start():
    """Start the server."""
    console.print("[yellow]Starting server...[/yellow]")
    try:
        output = start()
        console.print(output)
        console.print("[green]Server start command executed[/green]")
    except FileNotFoundError as e:
        console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Failed to start server:[/red] {e}")
        sys.exit(1)


@cli.command()
def server_stop():
    """Stop the server."""
    console.print("[yellow]Stopping server...[/yellow]")
    try:
        output = stop()
        console.print(output)
        console.print("[green]Server stop command executed[/green]")
    except FileNotFoundError as e:
        console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Failed to stop server:[/red] {e}")
        sys.exit(1)


@cli.command()
def server_restart():
    """Restart the server."""
    console.print("[yellow]Restarting server...[/yellow]")
    try:
        output = restart()
        console.print(output)
        console.print("[green]Server restart command executed[/green]")
    except FileNotFoundError as e:
        console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Failed to restart server:[/red] {e}")
        sys.exit(1)


@cli.command()
def server_status():
    """Show server status."""
    try:
        server_status = status()

        table = Table(title="Server Status")
        table.add_column("Property", style="cyan")
        table.add_column("Value", style="green" if server_status.running else "red")

        table.add_row("Running", "Yes" if server_status.running else "No")

        if server_status.running:
            if server_status.version:
                table.add_row("Version", server_status.version)
            if server_status.uptime:
                table.add_row("Uptime", server_status.uptime)
            table.add_row(
                "Players",
                f"{server_status.players_online} / {server_status.max_players}",
            )
            if server_status.memory_managed and server_status.memory_total:
                table.add_row(
                    "Memory",
                    f"{server_status.memory_managed} / {server_status.memory_total}",
                )

        console.print(table)

    except FileNotFoundError as e:
        console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Failed to get status:[/red] {e}")
        sys.exit(1)


@cli.command()
@click.argument("cmd")
def command(cmd: str):
    """Send a command to the server."""
    try:
        output = server_command(cmd)
        console.print(output)
    except FileNotFoundError as e:
        console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Failed to send command:[/red] {e}")
        sys.exit(1)


# =============================================================================
# Backup Commands
# =============================================================================


@cli.group()
def backup():
    """Backup management commands."""
    pass


@backup.command(name="world")
def backup_world():
    """Create a world backup using server's genbackup command."""
    console.print("[yellow]Creating world backup...[/yellow]")
    try:
        output = world_backup()
        console.print(output)
        console.print("[green]World backup command executed[/green]")
    except Exception as e:
        console.print(f"[red]Failed to create world backup:[/red] {e}")
        sys.exit(1)


@backup.command(name="server")
def backup_server():
    """Create a full server backup (archives data directory)."""
    console.print("[yellow]Creating server backup...[/yellow]")
    try:
        output = server_backup()
        console.print(f"[green]{output}[/green]")

        prune_output = prune_old_backups()
        console.print(prune_output)
    except Exception as e:
        console.print(f"[red]Failed to create server backup:[/red] {e}")
        sys.exit(1)


@backup.command(name="list")
def backup_list():
    """List all server backups."""
    backups = list_backups()

    if not backups:
        console.print("[yellow]No server backups found[/yellow]")
        return

    table = Table(title="Server Backups")
    table.add_column("#", style="dim")
    table.add_column("Filename", style="cyan")
    table.add_column("Size", style="green")

    for i, backup_path in enumerate(backups, 1):
        size_mb = backup_path.stat().st_size / (1024 * 1024)
        table.add_row(str(i), backup_path.name, f"{size_mb:.1f} MB")

    console.print(table)


@backup.command(name="start")
def backup_start():
    """Start the backup scheduler daemon."""
    run_scheduler()


# =============================================================================
# Log Commands
# =============================================================================


@cli.group()
def logs():
    """Log viewing commands."""
    pass


@logs.command(name="live")
def logs_live():
    """Tail live log files."""
    tail_live()


@logs.command(name="archive")
def logs_archive():
    """Browse archived logs."""
    browse_archives()


# =============================================================================
# Config Commands
# =============================================================================


@cli.group()
def config():
    """Configuration commands."""
    pass


@config.command(name="show")
def config_show():
    """Show current configuration."""
    cfg = load_config()

    table = Table(title="Configuration")
    table.add_column("Setting", style="cyan")
    table.add_column("Value", style="green")

    for key, value in cfg.items():
        table.add_row(key, str(value))

    console.print(table)
    console.print(f"\n[dim]Config file: {get_config_path()}[/dim]")


@config.command(name="edit")
def config_edit():
    """Open config file in editor."""
    config_path = get_config_path()

    # Ensure config file exists
    if not config_path.exists():
        load_config()  # This creates the default config

    editor = os.environ.get("EDITOR", os.environ.get("VISUAL"))

    if not editor:
        # Try common editors
        for candidate in ["nano", "vim", "vi", "notepad"]:
            try:
                subprocess.run(["which", candidate], capture_output=True, check=True)
                editor = candidate
                break
            except Exception:
                continue

    if not editor:
        console.print(f"[yellow]No editor found. Config file is at:[/yellow]")
        console.print(f"  {config_path}")
        return

    try:
        subprocess.run([editor, str(config_path)])
    except Exception as e:
        console.print(f"[red]Failed to open editor:[/red] {e}")
        console.print(f"[yellow]Config file is at:[/yellow] {config_path}")


@config.command(name="path")
def config_path():
    """Show config file path."""
    console.print(get_config_path())


def main():
    """Main entry point."""
    cli()


if __name__ == "__main__":
    main()
