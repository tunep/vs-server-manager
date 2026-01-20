# GEMINI.md

## Project Overview

This project is a Terminal User Interface (TUI) application for managing a Vintage Story dedicated server. It is written in Python and uses the `textual` library for the TUI, `apscheduler` for scheduling backups, and `rich` for enhanced terminal output.

The application provides a tab-based interface for:
*   **Server Status:** Viewing server status (online/offline/starting/stopping), version, uptime, and player count with dynamic button visibility.
*   **Server Control:** Starting, stopping, and restarting the server, with accurate transitional state tracking.
*   **Log Viewing:** Real-time log monitoring with file selection and automatic filtering of status block noise.
*   **Backup Management:** Creating world and server backups with server state validation and confirmation dialogs.
*   **Task Scheduling:** Automating backups and server announcements.
*   **Server Console:** Sending commands directly to the game server.
*   **Configuration Editing:** Edit both VSM config and server config (serverconfig.json) via modal dialogs.

The project is currently designed for Linux-based systems, with plans for future Windows support.

## Building and Running

### Prerequisites
*   Python 3.10+

### Installation and Execution

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/tunep/vintage-story-backup.git
    cd vintage-story-backup
    ```

2.  **Install dependencies in editable mode:**
    ```bash
    pip install -e .
    ```

3.  **Run the TUI application:**
    ```bash
    vsm
    ```

The main entry point for the application is `vsm.tui:main`, as defined in `pyproject.toml`.

### Testing

The project uses `pytest` for testing. To run the tests, first install the development dependencies:

```bash
pip install -e .[dev]
```

Then run pytest:

```bash
pytest
```

**NOTE: Do not run tests in the current environment.**

## Development Conventions

*   **Formatting:** The project uses `black` for code formatting and `ruff` for linting. Configuration for these tools can be found in `pyproject.toml`.
*   **Dependencies:** Project dependencies are managed in `pyproject.toml` using `setuptools`.
*   **Architecture:** The application is structured into several modules:
    *   `vsm/tui`: Contains the Textual-based TUI application, including screens and tabs.
    *   `vsm/tui/screens`: Modal screens for config editing, confirmations, and value editing.
    *   `vsm/tui/tabs`: Individual tab components for each functional area.
    *   `vsm/backup.py`: Handles the logic for creating and managing backups.
    *   `vsm/scheduler.py`: Manages scheduled tasks using `apscheduler`.
    *   `vsm/server.py`: Provides functions for interacting with the Vintage Story server process.
    *   `vsm/config.py`: Manages application configuration from a `config.json` file.
    *   `vsm/logs.py`: Log file reading with filtering to remove status block noise.
    *   `vsm/downtime.py`: Tracks server downtime for backup duration estimates.
*   **Configuration:** The application is configured via a `config.json` file, which is created on the first run. Server-specific settings are in `serverconfig.json` within the data directory.

## Key Files

*   `pyproject.toml`: Defines project metadata, dependencies, and build configurations.
*   `README.md`: Provides a general overview of the project, its features, and setup instructions.
*   `vsm/tui/app.py`: The main TUI application file that sets up the layout and tabs.
*   `vsm/tui/screens/config_screen.py`: Editable VSM configuration screen.
*   `vsm/tui/screens/server_config_screen.py`: Editable server configuration screen.
*   `vsm/tui/screens/confirm_screen.py`: Confirmation dialog for destructive actions.
*   `vsm/tui/tabs/status_tab.py`: Server status display with transitional state tracking.
*   `vsm/tui/tabs/backups_tab.py`: Backup management with server state validation.
*   `vsm/backup.py`: Contains the core logic for world and server backups.
*   `vsm/scheduler.py`: Implements the background scheduler for automated tasks.
*   `vsm/server.py`: Manages the server process and communication.
*   `config.json`: Stores user-configurable settings for the application.
