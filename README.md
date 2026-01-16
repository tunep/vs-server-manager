# Vintage Story Server Manager

A Python CLI for managing a Vintage Story dedicated server.

> **Platform Support:** Currently Linux only. Designed for easy Windows support in the future.

## Features

- **Server Control** - Start, stop, restart, and check status
- **Backup Management** - Automated world and full server backups
- **Log Viewer** - Tail live logs or browse archived logs
- **Configuration** - Editable settings via `config.json`
- **Player Management** - *(WIP)*
- **Server Config Editor** - *(WIP)*

---

## Server Control

**Executable:** `{server_path}/server.sh`

| Command | Description |
|---------|-------------|
| `start` | Start the server |
| `stop` | Stop the server |
| `restart` | Restart the server |
| `status` | Check if server is running (see example outputs) |
| `command "<cmd>"` | Send a command to the server console |

**Useful server commands:**
- `announce <text>` - Broadcast message to all players
- `genbackup [filename]` - Create world backup (defaults to timestamp)
- `list clients` - Show online players (see example output)

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

### Backup Announcements

Server announcements are broadcast to all players before backups begin, giving them advance notice that the server will be going offline.

**Announcement Schedule:**

| Minutes Before | Message |
|----------------|---------|
| 30 | Server going offline for backup in 30 minutes (estimated downtime: X minutes) |
| 15 | Server going offline for backup in 15 minutes (estimated downtime: X minutes) |
| 10 | Server going offline for backup in 10 minutes (estimated downtime: X minutes) |
| 5 | Server going offline for backup in 5 minutes (estimated downtime: X minutes) |
| 2 | Server going offline for backup in 2 minutes (estimated downtime: X minutes) |
| 1 | Server going offline for backup in 1 minute (estimated downtime: X minutes) |

Announcements use the server's `announce` command and only trigger when players are online.

### Downtime Tracking

The estimated downtime displayed in announcements is calculated by tracking each backup cycle:

1. Record timestamp when the `stop` command starts
2. Record timestamp when the `start` command finishes (server fully online)
3. Store the duration for future estimates

The most recent downtime duration is used for the estimate. If no previous backup has been tracked, the estimate is omitted from announcements.

---

## Log Viewer

**Log directory:** `{data_path}/Logs`

### Live Logs
- Follow active log files, streaming new entries as they're written
- Press `q` or `Ctrl+C` to stop

### Archived Logs
- Browse by session: select a timestamped folder, then select a log file
- View using a pager (scroll freely, search with `/`)
- Located in `{data_path}/Logs/Archive/<timestamp>/`

**Archive behavior:** When the server starts, previous logs are moved to a timestamped folder in `Archive/` by the server.

---

## Configuration (`config.json`)

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

## Platform Notes

### Linux (Current)
- Server executable: `{server_path}/server.sh`
- Default data path: `/var/vintagestory/data`

### Windows (Future)
- Server executable: `{server_path}/VintagestoryServer.exe` (or wrapper script)
- Default data path: `%AppData%/VintagestoryData` (typical location)
