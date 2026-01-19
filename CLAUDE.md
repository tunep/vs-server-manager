# CLAUDE.md

This file provides guidance to Claude Code when working with code in this repository.

## Project Overview

Vintage Story Server Manager (VSM) is a Python TUI application for managing Vintage Story dedicated game servers. It provides server control, backup management, scheduling, and live log viewing through a Textual-based terminal interface.

**Current platform:** Linux only (Windows support planned)
**Version:** 0.2.0

## Commands

```bash
# Development
pip install -e .          # Install in development mode
pip install -e ".[dev]"   # Install with dev dependencies (pytest, black, ruff)

# Running
vsm                       # Launch the TUI application

# Code Quality
ruff check .              # Lint
black .                   # Format
pytest                    # Run tests
```

## Architecture

### Entry Point
`vsm` CLI command → `vsm.tui:main()` → launches `VSMApp` (Textual app)

### Core Modules (`vsm/`)
- `config.py` - JSON config loading/saving, path helpers (`get_data_path`, `get_server_executable`, etc.)
- `server.py` - Server control via `server.sh` subprocess calls (start, stop, status, command)
- `backup.py` - World backups (via server's `genbackup`) and server backups (tar.gz archives)
- `scheduler.py` - APScheduler-based background jobs for automated backups with player announcements
- `downtime.py` - Tracks server downtime for backup duration estimates
- `logs.py` - Log file reading with filtering for status block noise

### TUI Layer (`vsm/tui/`)
- `app.py` - Main `VSMApp` class with tab navigation and keybindings
- `workers.py` - `run_blocking()` helper for running sync code in thread pool
- `screens/` - Modal screens:
  - `config_screen.py` - Editable VSM config viewer (press Enter to edit values)
  - `server_config_screen.py` - Editable server config (serverconfig.json) viewer
  - `edit_value_screen.py` - Modal dialog for editing individual config values
  - `confirm_screen.py` - Confirmation dialog for destructive actions
- `tabs/` - Individual tab components (StatusTab, LogsTab, BackupsTab, SchedulerTab, ConsoleTab)

### Key Patterns

- **Blocking Operations**: All server commands are blocking subprocess calls. The TUI uses `run_blocking()` from `workers.py` to run them in a `ThreadPoolExecutor` without freezing the UI.
- **Tab Architecture**: Each tab inherits from `Container` and implements `compose()` for layout. Tabs refresh via workers and update widgets directly.
- **Scheduler Singleton**: `VSMScheduler.get_instance()` returns the global scheduler. The scheduler runs APScheduler in background mode and manages backup jobs + announcement scheduling.
- **Config Flow**: `load_config()` auto-creates `config.json` with defaults. All path functions (`get_data_path`, etc.) expand `~` and return `Path` objects.
- **Server State Management**: StatusTab tracks transitional states (`_starting`, `_stopping`, `_restarting`) to provide accurate UI feedback. BackupsTab checks these states before allowing manual backups.
- **Modal Dialogs**: Use `push_screen_wait()` for confirmation dialogs that need to block until user responds.

## Server Interaction

The app controls Vintage Story via a `server.sh` wrapper script:
- `server.sh start/stop/status/restart` - lifecycle commands
- `server.sh command <cmd>` - send commands (like `genbackup`, `announce`)

Status parsing uses regex to extract version, uptime, players, and memory from the script's output.

## Dependencies

- `textual>=0.50.0` - TUI framework
- `apscheduler>=3.10` - Background job scheduling
- `rich>=13.0` - Terminal formatting (used by Textual)
