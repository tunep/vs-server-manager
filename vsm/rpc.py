"""OpenRPC server and client for VSM Scheduler."""

import functools
import json
import logging
import socket
import threading
from datetime import datetime
from pathlib import Path
from typing import Any

from openrpc import RPCServer

from .scheduler import VSMScheduler, SchedulerState


READY_NAME = "vsm-scheduler.ready"

logger = logging.getLogger("VSMScheduler")


class SchedulerRPCServer(threading.Thread):
    """A simple OpenRPC server for the VSM Scheduler."""

    def __init__(self, scheduler: VSMScheduler, config: dict, pid_dir: str):
        super().__init__(daemon=True)
        self.scheduler = scheduler
        self.config = config
        self.pid_dir = pid_dir
        self.host = config.get("rpc_host", "127.0.0.1")
        self.port = config.get("rpc_port", 8585)
        self.server_socket: socket.socket | None = None

        self.rpc_server = RPCServer()
        self._register_methods()

    def _register_methods(self):
        """Register scheduler methods with the RPC server."""

        # Use the decorator syntax to register methods
        @self.rpc_server.method(name="get_status")
        def get_status() -> dict:
            """Get the scheduler status."""
            state = self.scheduler.get_state()
            return {"status": state.value}

        @self.rpc_server.method(name="get_jobs")
        def get_jobs() -> list[dict]:
            """Get the list of scheduled jobs."""
            jobs = self.scheduler.get_jobs()
            # Convert datetime objects to strings for serialization
            for job in jobs:
                if job.get("next_run_time"):
                    job["next_run_time"] = job["next_run_time"].isoformat()
            return jobs

        @self.rpc_server.method(name="advance_jobs")
        def advance_jobs(minutes: int = 1) -> dict:
            """Advance all jobs by the specified number of minutes."""
            count = self.scheduler.advance_jobs(minutes)
            return {"advanced": count}
        
    def run(self):
        """Start the RPC server."""
        logger.info(f"RPC server starting on {self.host}:{self.port}")
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            self.server_socket.bind((self.host, self.port))
        except Exception as e:
            logger.error(f"RPC server failed to bind: {e}")
            return
        self.server_socket.listen(1)
        logger.info(f"RPC server listening on {self.host}:{self.port}")

        # Signal that the server is ready
        (self.pid_dir / READY_NAME).touch()

        while True:
            try:
                logger.debug("RPC server waiting for connection...")
                conn, addr = self.server_socket.accept()
                logger.info(f"RPC server accepted connection from {addr}")
                with conn:
                    data = conn.recv(4096)
                    if not data:
                        logger.warning("RPC server received empty data")
                        continue

                    logger.info(f"RPC server received: {data.decode()}")
                    # Process the request using the openrpc server
                    response_json = self.rpc_server.process_request(data.decode())
                    logger.info(f"RPC server response: {response_json}")
                    if response_json:
                        conn.sendall(response_json.encode())
                    else:
                        logger.warning("RPC server handle() returned None/empty")
            except (socket.error, ConnectionResetError) as e:
                logger.info(f"RPC server socket closed: {e}")
                break # Exit loop if socket is closed or connection reset
            except Exception as e:
                logger.error(f"RPC server error: {e}", exc_info=True)
    
    def stop(self):
        """Stop the RPC server."""
        if self.server_socket:
            self.server_socket.close()


class SchedulerRPCClient:
    """A client for the VSM Scheduler OpenRPC server (custom JSON-RPC 2.0 client)."""

    def __init__(self, config: dict):
        self.host = config.get("rpc_host", "127.0.0.1")
        self.port = config.get("rpc_port", 8585)

    def _send_request(self, method: str, params: list | None = None) -> dict:
        """Send a JSON-RPC request over a raw socket."""
        payload = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params or [],
            "id": 1,
        }
        try:
            with socket.create_connection((self.host, self.port), timeout=2) as sock:
                sock.sendall(json.dumps(payload).encode())
                response_data = sock.recv(4096)
                if not response_data:
                    return {"error": {"message": "Empty response from server"}}
                return json.loads(response_data.decode())
        except (socket.timeout, ConnectionRefusedError):
             return {"error": {"message": "Connection to scheduler daemon failed."}}
        except Exception as e:
            return {"error": {"message": f"An unexpected error occurred: {e}"}}


    def get_status(self) -> dict:
        """Get the scheduler status from the daemon."""
        response = self._send_request("get_status")
        if "error" in response:
            return response
        return response.get("result", {})

    def get_jobs(self) -> list[dict]:
        """Get the list of jobs from the daemon."""
        response = self._send_request("get_jobs")
        jobs = response.get("result", [])
        # Convert isoformat strings back to datetime objects
        for job in jobs:
            if job.get("next_run_time"):
                try:
                    job["next_run_time"] = datetime.fromisoformat(job["next_run_time"])
                except (ValueError, TypeError):
                    job["next_run_time"] = None
        return jobs

    def advance_jobs(self, minutes: int = 1) -> dict:
        """Advance all jobs by the specified number of minutes."""
        response = self._send_request("advance_jobs", {"minutes": minutes})
        if "error" in response:
            return response
        return response.get("result", {})
