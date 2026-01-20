# Vintage Story Server Manager (VSM)

A Python TUI for managing a Vintage Story dedicated server.

> **Platform Support:** Currently Linux only. Windows support planned.

## Features

- **Dashboard TUI** - Tab-based Textual interface for all server management
- **Server Control** - Start, stop, restart with transitional state display (Starting/Stopping)
- **Live Logs** - Real-time log viewer with file selection and automatic noise filtering
- **Backup Management** - World and server backups with state validation and confirmation dialogs
- **Scheduler Daemon** - Background scheduler with RPC interface for automated backups and announcements
- **Server Console** - Send commands directly to the server
- **Configuration Editing** - Edit VSM and server configs via modal dialogs

## Installation

Requires Python 3.10+

```bash
# Clone the repository
git clone https://github.com/tunep/vintage-story-backup.git
cd vintage-story-backup

# Install
pip install -e .

# Launch the TUI
vsm
```

## TUI Overview

Launch with `vsm` to open the terminal user interface.

```
┌──────────────────────────────────────────────────────────────────┐
│  Vintage Story Server Manager                             [v0.2] │
├──────────────────────────────────────────────────────────────────┤
│  Status │ Logs │ Backups │ Scheduler │ Console                   │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Tab content displayed here                                      │
│                                                                  │
├──────────────────────────────────────────────────────────────────┤
│  q:Quit  c:Config  r:Refresh                                     │
└──────────────────────────────────────────────────────────────────┘
```

### Tabs

| Tab | Description |
|-----|-------------|
| **Status** | Server status (Running/Stopped/Starting/Stopping), version, uptime, players, memory. Dynamic control buttons and Config button for server settings. |
| **Logs** | Log viewer with file selection dropdown. Automatically filters status block noise. |
| **Backups** | List of server backups. World Backup (requires running server) and Server Backup (with confirmation if server running) buttons. |
| **Scheduler** | Daemon status, scheduled jobs with next run times, Start/Stop/Advance controls, and log viewer |
| **Console** | Send commands to the server and view output |

### Key Bindings

| Key | Action |
|-----|--------|
| `q` | Quit |
| `c` | Open VSM config editor |
| `r` | Refresh current tab |
| `1-5` | Switch to tab (Status, Logs, Backups, Scheduler, Console) |
| `↑/↓` | Navigate control buttons (in Status tab) |

## Backup System

### Types of Backups

| Type | Method | Location | Default Interval |
|------|--------|----------|------------------|
| **World** | Server's `genbackup` command | `{data_path}/Backups` | Hourly |
| **Server** | Archives entire data folder | `{server_path}/backups` | Every 6 hours |

### Backup Behavior

1. **Server backups** archive `{data_path}` (includes world backups and logs)
2. After a server backup completes, clears world backups and logs to avoid duplicate data
3. **Skips world backup** when a server backup is scheduled for the same hour
4. Old server backups are pruned (default: keep 7)

### Scheduler Daemon

The scheduler runs as a background daemon process, separate from the TUI. Start it from the **Scheduler** tab or via CLI:

```bash
vsm-scheduler start   # Start the daemon
vsm-scheduler stop    # Stop the daemon
vsm-scheduler status  # Check daemon status
```

The daemon provides:

- Automated world backups at the configured interval
- Automated server backups at the configured interval
- Player announcements before server backups
- Downtime tracking for accurate estimates
- RPC interface for TUI communication (default: 127.0.0.1:8585)

**Scheduler Tab Controls:**
| Button | Action |
|--------|--------|
| Start Daemon | Launch the background scheduler |
| Stop Daemon | Terminate the scheduler daemon |
| Advance 1m | Advance all jobs by 1 minute (for testing) |
| Refresh | Manually refresh status |
| View Log | Open scheduler log file |

### Announcements

Announcements are broadcast to players before server backups:

| Minutes Before | Message |
|----------------|---------|
| 30, 15, 10, 5, 2, 1 | Server going offline for backup in X minutes (estimated downtime: Y minutes) |

Announcements only trigger when players are online.

### Downtime Tracking

Estimated downtime is calculated from previous backup cycles:

1. Records timestamp when `stop` command starts
2. Records timestamp when `start` command finishes
3. Uses the duration for future estimates

## Configuration

Settings are stored in `config.json` (created automatically on first run).

| Setting | Default | Description |
|---------|---------|-------------|
| `data_path` | `/var/vintagestory/data` | Vintage Story data directory |
| `server_path` | `~/server` | Server installation directory |
| `world_backup_interval` | `1` | Hours between world backups |
| `server_backup_interval` | `6` | Hours between server backups |
| `max_server_backups` | `7` | Server backups to retain |
| `rpc_host` | `127.0.0.1` | RPC server host |
| `rpc_port` | `8585` | RPC server port |

**Derived paths:**
- Logs: `{data_path}/Logs`
- World backups: `{data_path}/Backups`
- Server executable: `{server_path}/server.sh`
- Server backups: `{server_path}/backups`

**Daemon files** (in `~/.config/vintage-story-backup/`):
- `vsm-scheduler.pid` - Process ID file
- `vsm-scheduler.log` - Rotating log file
- `vsm-scheduler.ready` - Ready signal file

Press `c` in the TUI to view current configuration.

## Server Commands

Use the **Console** tab to send commands to the server:

| Command | Description |
|---------|-------------|
| `announce <text>` | Broadcast message to all players |
| `genbackup [filename]` | Create world backup |
| `list clients` | Show online players |

## Platform Notes

### Linux (Current)
- Server executable: `{server_path}/server.sh`
- Default data path: `/var/vintagestory/data`

### Windows (Future)
- Server executable: `{server_path}/VintagestoryServer.exe`
- Default data path: `%AppData%/VintagestoryData`
