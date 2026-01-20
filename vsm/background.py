"""
This script runs in the background to manage the VSM scheduler and RPC server.
It is launched by the `vsm-scheduler` command.
"""

import logging
import os
import signal
import sys
import time
from logging.handlers import RotatingFileHandler
from pathlib import Path

from .config import get_config_path, load_config
from .rpc import SchedulerRPCServer
from .scheduler import get_scheduler

PID_NAME = "vsm-scheduler.pid"
READY_NAME = "vsm-scheduler.ready"

PID_DIR = get_config_path().parent

LOG_FILE = PID_DIR / "vsm-scheduler.log"

# Path to this module's directory - used to detect if source files are removed
_MODULE_DIR = Path(__file__).parent


def setup_logging():
    """Set up logging for the background process."""
    # Ensure the log directory exists
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("VSMBackground")
    logger.setLevel(logging.INFO)

    handler = RotatingFileHandler(
        LOG_FILE,
        maxBytes=1024 * 1024,  # 1 MB
        backupCount=5,
    )
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    # Also configure the scheduler's logger
    scheduler_logger = logging.getLogger("VSMScheduler")
    scheduler_logger.setLevel(logging.INFO)
    scheduler_logger.addHandler(handler)

    return logger


def write_pid_file():
    """Write the current process ID to a file."""
    PID_DIR.mkdir(parents=True, exist_ok=True)
    with open(PID_DIR / PID_NAME, "w") as f:
        f.write(str(os.getpid()))


def check_source_files_exist():
    """Check if the vsm module source files still exist.

    Returns True if files exist, False if they've been removed (e.g., repo was deleted).
    """
    # Check for key files that should always exist
    critical_files = [
        _MODULE_DIR / "__init__.py",
        _MODULE_DIR / "background.py",
        _MODULE_DIR / "scheduler.py",
    ]
    return all(f.exists() for f in critical_files)


def main():
    """Main function for the background process."""
    logger = setup_logging()
    logger.info("Starting VSM Background Process...")

    try:
        # Write PID file
        write_pid_file()

        config = load_config()

        # Get and configure scheduler
        scheduler = get_scheduler()
        scheduler.set_log_callback(lambda msg: logging.getLogger("VSMScheduler").info(msg))
        scheduler.start(config)

        # Start RPC server to listen for commands
        rpc_server = SchedulerRPCServer(scheduler, config, PID_DIR)
        rpc_server.start()  # This is a Thread, so it's non-blocking

        logger.info("VSM Background Process started successfully.")

    except Exception:
        logger.critical("An unhandled exception occurred", exc_info=True)
        sys.exit(1)

    def handle_shutdown_signal(signum, frame):
        logger.info(f"Received signal {signum}. Shutting down...")
        rpc_server.stop()
        scheduler.stop()
        # Clean up PID file
        try:
            (PID_DIR / PID_NAME).unlink(missing_ok=True)
        except OSError:
            pass
        logger.info("Shutdown complete.")
        sys.exit(0)

    signal.signal(signal.SIGTERM, handle_shutdown_signal)
    signal.signal(signal.SIGINT, handle_shutdown_signal)

    def graceful_shutdown(reason):
        """Perform graceful shutdown with the given reason."""
        logger.warning(f"{reason} Shutting down daemon...")
        rpc_server.stop()
        scheduler.stop()
        # Clean up PID and ready files
        try:
            (PID_DIR / PID_NAME).unlink(missing_ok=True)
            (PID_DIR / READY_NAME).unlink(missing_ok=True)
        except OSError:
            pass
        logger.info("Daemon terminated.")
        sys.exit(0)

    # Keep the main thread alive, listening for signals
    # Also check periodically if source files or PID file still exist
    try:
        while True:
            time.sleep(10)
            # Check if PID file has been removed (intentional stop signal)
            if not (PID_DIR / PID_NAME).exists():
                graceful_shutdown("PID file was removed.")
            # Check if source files have been removed (e.g., repo was recloned)
            if not check_source_files_exist():
                graceful_shutdown("Source files no longer exist (repo may have been removed).")
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
