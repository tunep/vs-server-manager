# Vintage Story Server Manager

A Python TUI for managing a Vintage Story dedicated server.

> **Platform Support:** Currently Linux only. Designed for easy Windows support in the future.

## Features

- **Dashboard TUI** - Tab-based interface for all server management
- **Server Control** - Start, stop, restart, and check status
- **Live Logs** - Real-time log viewer with filtering
- **Backup Management** - Automated world and full server backups
- **Scheduler** - Background backup scheduling with player announcements
- **Server Console** - Send commands directly to the server

---

## Installation

Requires Python 3.10+

```bash
# Clone the repository
git clone https://github.com/tunep/vs-server-manager.git
cd vs-server-manager

# Install in development mode
pip install -e .

# Launch the TUI
vsm
```

---

## TUI Overview

Launch with `vsm` to open the terminal user interface.

```
+------------------------------------------------------------------+
|  Vintage Story Server Manager                              [v0.2] |
+------------------------------------------------------------------+
|  Status | Logs | Backups | Scheduler | Console                   |
+------------------------------------------------------------------+
|                                                                  |
|  Tab content displayed here                                      |
|                                                                  |
+------------------------------------------------------------------+
|  q:Quit  c:Config  r:Refresh                                     |
+------------------------------------------------------------------+
```

### Tabs

| Tab | Description |
|-----|-------------|
| **Status** | Server status (running/stopped, version, uptime, players, memory) and Start/Stop/Restart buttons |
| **Logs** | Live log viewer with file filter and pause/resume |
| **Backups** | List of server backups with World Backup and Server Backup buttons |
| **Scheduler** | Scheduler status, scheduled jobs, and Start/Stop controls |
| **Console** | Send commands to the server and view output |

### Key Bindings

| Key | Action |
|-----|--------|
| `q` | Quit |
| `c` | Open config viewer |
| `r` | Refresh current tab |
| `1-5` | Switch to tab (Status, Logs, Backups, Scheduler, Console) |

---

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

### Scheduler

Start the scheduler from the **Scheduler** tab. It runs in the background and:

- Schedules world backups at the configured interval
- Schedules server backups at the configured interval
- Announces upcoming server backups to online players
- Tracks downtime for accurate estimates

### Backup Announcements

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

---

## Configuration

Settings are stored in `config.json` (created automatically on first run).

| Setting | Default | Description |
|---------|---------|-------------|
| `data_path` | `/var/vintagestory/data` | Vintage Story data directory |
| `server_path` | `~/server` | Server installation directory |
| `world_backup_interval` | `1` | Hours between world backups |
| `server_backup_interval` | `6` | Hours between server backups |
| `max_server_backups` | `7` | Server backups to retain |

**Derived paths:**
- Logs: `{data_path}/Logs`
- World backups: `{data_path}/Backups`
- Server executable: `{server_path}/server.sh`
- Server backups: `{server_path}/backups`

Press `c` in the TUI to view current configuration.

---

## Server Commands

Use the **Console** tab to send commands to the server:

| Command | Description |
|---------|-------------|
| `announce <text>` | Broadcast message to all players |
| `genbackup [filename]` | Create world backup |
| `list clients` | Show online players |

---

## Platform Notes

### Linux (Current)
- Server executable: `{server_path}/server.sh`
- Default data path: `/var/vintagestory/data`

### Windows (Future)
- Server executable: `{server_path}/VintagestoryServer.exe`
- Default data path: `%AppData%/VintagestoryData`
