# Vintage Story Server Manager

A Python CLI for managing a Vintage Story dedicated server.

> **Platform Support:** Currently Linux only. Designed for easy Windows support in the future.

## Features

- **Server Control** - Start, stop, restart, and check status
- **Backup Management** - Automated world and full server backups
- **Log Viewer** - Tail live logs or browse archived logs
- **Configuration** - Editable settings via `config.json`

---

## Installation

Requires Python 3.10+

```bash
# Clone the repository
git clone https://github.com/yourusername/vs-server-manager.git
cd vs-server-manager

# Install in development mode
pip install -e .

# Verify installation
vsm --help
```

---

## CLI Usage

```
vsm [command]
```

### Server Control

| Command | Description |
|---------|-------------|
| `vsm server-start` | Start the server |
| `vsm server-stop` | Stop the server |
| `vsm server-restart` | Restart the server |
| `vsm server-status` | Show server status |
| `vsm command "<cmd>"` | Send a command to the server console |

### Backup Management

| Command | Description |
|---------|-------------|
| `vsm backup world` | Create a world backup (uses server's `genbackup`) |
| `vsm backup server` | Create a full server backup (archives data directory) |
| `vsm backup list` | List all server backups |
| `vsm backup start` | Start the backup scheduler daemon |

### Log Viewer

| Command | Description |
|---------|-------------|
| `vsm logs live` | Tail live log files (Ctrl+C to stop) |
| `vsm logs archive` | Browse and view archived logs |

### Configuration

| Command | Description |
|---------|-------------|
| `vsm config show` | Display current configuration |
| `vsm config edit` | Open config file in `$EDITOR` |
| `vsm config path` | Show config file location |

---

## Backup System

### Types of Backups

| Type | Method | Location | Default Interval | Max Count |
|------|--------|----------|------------------|-----------|
| **World** | Server's `genbackup` command | `{data_path}/Backups` | Hourly | N/A |
| **Server** | Script archives entire data folder | `{server_path}/backups` | Every 6 hours | 7 |

### Backup Behavior

1. **Server backups** archive `{data_path}` (includes world backups and logs)
2. After a server backup completes, clear the world backups and logs folders to avoid duplicate data
3. **Skip the world backup** when a server backup is scheduled for the same hour

### Backup Scheduler

Run `vsm backup start` to start the backup scheduler daemon. This runs in the foreground and:

- Schedules world backups at the configured interval
- Schedules server backups at the configured interval
- Announces upcoming server backups to online players
- Tracks downtime for accurate estimates

Press Ctrl+C to stop the scheduler.

### Backup Announcements

Announcements are broadcast to all players before server backups, giving advance notice that the server will go offline.

| Minutes Before | Message |
|----------------|---------|
| 30 | Server going offline for backup in 30 minutes (estimated downtime: X minutes) |
| 15 | Server going offline for backup in 15 minutes (estimated downtime: X minutes) |
| 10 | Server going offline for backup in 10 minutes (estimated downtime: X minutes) |
| 5 | Server going offline for backup in 5 minutes (estimated downtime: X minutes) |
| 2 | Server going offline for backup in 2 minutes (estimated downtime: X minutes) |
| 1 | Server going offline for backup in 1 minute (estimated downtime: X minutes) |

Announcements only trigger when players are online.

### Downtime Tracking

The estimated downtime is calculated by tracking each backup cycle:

1. Record timestamp when the `stop` command starts
2. Record timestamp when the `start` command finishes (server fully online)
3. Store the duration for future estimates

The most recent downtime duration is used. If no previous backup has been tracked, the estimate is omitted.

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

---

## Log Viewer

**Log directory:** `{data_path}/Logs`

### Live Logs
- Follow active log files, streaming new entries as they're written
- Press Ctrl+C to stop

### Archived Logs
- Browse by session: select a timestamped folder, then select a log file
- View using a pager (scroll freely, search with `/`)
- Located in `{data_path}/Logs/Archive/<timestamp>/`

**Archive behavior:** When the server starts, previous logs are moved to a timestamped folder in `Archive/` by the server.

---

## Server Commands Reference

These commands can be sent via `vsm command "<cmd>"`:

| Command | Description |
|---------|-------------|
| `announce <text>` | Broadcast message to all players |
| `genbackup [filename]` | Create world backup (defaults to timestamp) |
| `list clients` | Show online players |

---

## Platform Notes

### Linux (Current)
- Server executable: `{server_path}/server.sh`
- Default data path: `/var/vintagestory/data`

### Windows (Future)
- Server executable: `{server_path}/VintagestoryServer.exe` (or wrapper script)
- Default data path: `%AppData%/VintagestoryData` (typical location)
