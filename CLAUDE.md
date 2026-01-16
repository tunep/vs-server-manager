# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Vintage Story Server Manager (VSM) is a Python TUI application for managing Vintage Story dedicated game servers. It provides server control, backup management, scheduling, and live log viewing through a Textual-based terminal interface.

**Current platform:** Linux only (Windows support planned)

## Commands

### Development
```bash
pip install -e .          # Install in development mode
pip install -e ".[dev]"   # Install with dev dependencies (pytest, black, ruff)
```

### Running
```bash
vsm                       # Launch the TUI application
```

### Code Quality
```bash
ruff check .              # Lint
black .                   # Format
pytest                    # Run tests (no tests currently exist)
```

## Architecture

### Entry Point
- `vsm` CLI command → `vsm.tui:main()` → launches `VSMApp` (Textual app)

### Core Modules (`vsm/`)
| Module | Purpose |
|--------|---------|
| `config.py` | JSON config loading/saving, path helpers (`get_data_path`, `get_server_executable`, etc.) |
| `server.py` | Server control via `server.sh` subprocess calls (start, stop, status, command) |
| `backup.py` | World backups (via server's `genbackup`) and server backups (tar.gz archives) |
| `scheduler.py` | APScheduler-based background jobs for automated backups with player announcements |
| `downtime.py` | Tracks server downtime for backup duration estimates |
| `logs.py` | Log file reading utilities |

### TUI Layer (`vsm/tui/`)
| Component | Purpose |
|-----------|---------|
| `app.py` | Main `VSMApp` class with tab navigation and keybindings |
| `workers.py` | `run_blocking()` helper for running sync code in thread pool |
| `screens/config_screen.py` | Modal config viewer |
| `tabs/` | Individual tab components (StatusTab, LogsTab, BackupsTab, SchedulerTab, ConsoleTab) |

### Key Patterns

**Blocking Operations**: All server commands are blocking subprocess calls. The TUI uses `run_blocking()` from `workers.py` to run them in a `ThreadPoolExecutor` without freezing the UI.

**Tab Architecture**: Each tab inherits from `Container` and implements `compose()` for layout. Tabs refresh via workers (`run_worker()`) and update widgets directly.

**Scheduler Singleton**: `VSMScheduler.get_instance()` returns the global scheduler. The scheduler runs APScheduler in background mode and manages backup jobs + announcement scheduling.

**Config Flow**: `load_config()` auto-creates `config.json` with defaults. All path functions (`get_data_path`, etc.) expand `~` and return `Path` objects.

## Server Interaction

The app controls Vintage Story via a `server.sh` wrapper script:
- `server.sh start/stop/status/restart` for lifecycle
- `server.sh command <cmd>` to send commands (like `genbackup`, `announce`)

Status parsing uses regex to extract version, uptime, players, and memory from the script's output.
