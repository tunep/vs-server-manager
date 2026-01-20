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

from .config import get_config_path, load_config
from .rpc import SchedulerRPCServer
from .scheduler import get_scheduler

PID_NAME = "vsm-scheduler.pid"
PID_DIR = get_config_path().parent
LOG_FILE = PID_DIR / "vsm-scheduler.log"


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
        rpc_server = SchedulerRPCServer(scheduler, config)
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

    # Keep the main thread alive, listening for signals
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
