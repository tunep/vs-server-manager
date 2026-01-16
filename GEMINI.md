# GEMINI.md

## Project Overview

This project is a Terminal User Interface (TUI) application for managing a Vintage Story dedicated server. It is written in Python and uses the `textual` library for the TUI, `apscheduler` for scheduling backups, and `rich` for enhanced terminal output.

The application provides a tab-based interface for:
*   **Server Status:** Viewing server status (online/offline), version, uptime, and player count.
*   **Server Control:** Starting, stopping, and restarting the server.
*   **Log Viewing:** Real-time log monitoring with filtering.
*   **Backup Management:** Creating world and server backups.
*   **Task Scheduling:** Automating backups and server announcements.
*   **Server Console:** Sending commands directly to the game server.

The project is currently designed for Linux-based systems, with plans for future Windows support.

## Building and Running

### Prerequisites
*   Python 3.10+

### Installation and Execution

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/tunep/vs-server-manager.git
    cd vs-server-manager
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

## Development Conventions

*   **Formatting:** The project uses `black` for code formatting and `ruff` for linting. Configuration for these tools can be found in `pyproject.toml`.
*   **Dependencies:** Project dependencies are managed in `pyproject.toml` using `setuptools`.
*   **Architecture:** The application is structured into several modules:
    *   `vsm/tui`: Contains the Textual-based TUI application, including screens and tabs.
    *   `vsm/backup.py`: Handles the logic for creating and managing backups.
    *   `vsm/scheduler.py`: Manages scheduled tasks using `apscheduler`.
    *   `vsm/server.py`: Provides functions for interacting with the Vintage Story server process.
    *   `vsm/config.py`: Manages application configuration from a `config.json` file.
*   **Configuration:** The application is configured via a `config.json` file, which is created on the first run.

## Key Files

*   `pyproject.toml`: Defines project metadata, dependencies, and build configurations.
*   `README.md`: Provides a general overview of the project, its features, and setup instructions.
*   `vsm/tui/app.py`: The main TUI application file that sets up the layout and tabs.
*   `vsm/backup.py`: Contains the core logic for world and server backups.
*   `vsm/scheduler.py`: Implements the background scheduler for automated tasks.
*   `vsm/server.py`: Manages the server process and communication.
*   `config.json`: Stores user-configurable settings for the application.
