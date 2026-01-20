"""
Cross-platform daemon manager for VSM Scheduler.
"""

import argparse
import os
import subprocess
import sys
import time

import psutil

from .config import get_config_path, load_config
from .rpc import SchedulerRPCClient

PID_NAME = "vsm-scheduler.pid"
PID_DIR = get_config_path().parent
PID_FILE = PID_DIR / PID_NAME


def get_pid_from_file():
    """Get PID from the pidfile."""
    try:
        with open(PID_FILE, "r") as f:
            return int(f.read().strip())
    except (FileNotFoundError, ValueError):
        return None


def is_daemon_running():
    """Check if the daemon is running."""
    pid = get_pid_from_file()
    if pid is None:
        return False
    return psutil.pid_exists(pid)


def start_daemon():
    """Start the background daemon process."""
    if is_daemon_running():
        print("Daemon is already running.", file=sys.stderr)
        sys.exit(1)

    print("Starting VSM Scheduler Daemon in the background...")

    command = [sys.executable, "-m", "vsm.background"]

    kwargs = {}
    if sys.platform == "win32":
        kwargs["creationflags"] = subprocess.DETACHED_PROCESS
        kwargs["close_fds"] = True
    else:
        # On POSIX, the child process will be orphaned and reparented by init.
        # We don't need to do a double-fork here.
        pass

    try:
        subprocess.Popen(command, **kwargs)
        # Give it a moment to start and write its PID file
        time.sleep(2)
        if is_daemon_running():
            print("Daemon started successfully.")
        else:
            print("Daemon failed to start. Check the log file for details.", file=sys.stderr)
            sys.exit(1)
    except Exception as e:
        print(f"Failed to start daemon: {e}", file=sys.stderr)
        sys.exit(1)


def stop_daemon():
    """Stop the background daemon process."""
    pid = get_pid_from_file()
    if not pid or not psutil.pid_exists(pid):
        print("Daemon is not running.", file=sys.stderr)
        # Clean up stale PID file if it exists
        if PID_FILE.exists():
            PID_FILE.unlink()
        return

    print(f"Stopping VSM Scheduler Daemon (PID: {pid})...")
    try:
        proc = psutil.Process(pid)
        proc.terminate()  # Sends SIGTERM
        try:
            proc.wait(timeout=5)
            print("Daemon stopped.")
        except psutil.TimeoutExpired:
            print("Daemon did not terminate gracefully. Forcing...", file=sys.stderr)
            proc.kill()
            print("Daemon killed.")

    except psutil.NoSuchProcess:
        print("Daemon was not running.", file=sys.stderr)
    except Exception as e:
        print(f"Error stopping daemon: {e}", file=sys.stderr)

    # Clean up PID file
    if PID_FILE.exists():
        PID_FILE.unlink()


def main():
    """Main entry point for the vsm-scheduler command."""
    parser = argparse.ArgumentParser(description="VSM Scheduler Daemon Manager")
    parser.add_argument(
        "command",
        choices=["start", "stop", "status", "restart"],
        help="The command to execute.",
    )
    args = parser.parse_args()

    # Ensure config dir exists
    PID_DIR.mkdir(parents=True, exist_ok=True)

    if args.command == "start":
        start_daemon()

    elif args.command == "stop":
        stop_daemon()

    elif args.command == "restart":
        print("Restarting daemon...")
        stop_daemon()
        time.sleep(1)
        start_daemon()

    elif args.command == "status":
        if is_daemon_running():
            print("Daemon is running.")
            config = load_config()
            client = SchedulerRPCClient(config)
            status_response = client.get_status()
            if status_response and "status" in status_response:
                print(f"Scheduler Status: {status_response['status']}")
            else:
                error = status_response.get("error", {}).get("message", "Unknown error")
                print(f"Could not retrieve detailed status from daemon: {error}", file=sys.stderr)
        else:
            print("Daemon is not running.")

if __name__ == "__main__":
    main()