"""JSON-RPC server and client for VSM Scheduler."""

import json
import socket
import threading
from jsonrpc.manager import JSONRPCResponseManager

from .scheduler import VSMScheduler

class SchedulerRPCServer(threading.Thread):
    """A simple JSON-RPC server for the VSM Scheduler."""

    def __init__(self, scheduler: VSMScheduler, config: dict):
        super().__init__(daemon=True)
        self.scheduler = scheduler
        self.config = config
        self.host = config.get("rpc_host", "127.0.0.1")
        self.port = config.get("rpc_port", 8585)
        self.server_socket = None

    def rpc_get_status(self) -> dict:
        """Get the scheduler status."""
        state = self.scheduler.get_state()
        return {"status": state.value}

    def rpc_get_jobs(self) -> list:
        """Get the list of scheduled jobs."""
        jobs = self.scheduler.get_jobs()
        # Convert datetime objects to strings
        for job in jobs:
            if job.get("next_run_time"):
                job["next_run_time"] = job["next_run_time"].isoformat()
        return jobs

    def run(self):
        """Start the RPC server."""
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(1)

        while True:
            try:
                conn, _ = self.server_socket.accept()
                with conn:
                    data = conn.recv(1024)
                    if not data:
                        continue
                    
                    response = JSONRPCResponseManager.handle(
                        data.decode(), self
                    )
                    if response:
                        conn.sendall(response.json.encode())
            except (socket.error, ConnectionResetError):
                break # Exit loop if socket is closed or connection reset
            except Exception:
                # In a real app, log this exception
                pass
    
    def stop(self):
        """Stop the RPC server."""
        if self.server_socket:
            self.server_socket.close()


class SchedulerRPCClient:
    """A client for the VSM Scheduler RPC server."""

    def __init__(self, config: dict):
        self.host = config.get("rpc_host", "127.0.0.1")
        self.port = config.get("rpc_port", 8585)

    def _send_request(self, method: str, params: list | None = None) -> dict:
        """Send a JSON-RPC request."""
        payload = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params or [],
            "id": 1,
        }
        try:
            with socket.create_connection((self.host, self.port), timeout=2) as sock:
                sock.sendall(json.dumps(payload).encode())
                response = sock.recv(4096)
                if not response:
                    return {"error": {"message": "Empty response from server"}}
                return json.loads(response.decode())
        except (socket.timeout, ConnectionRefusedError):
             return {"error": {"message": "Connection to scheduler daemon failed."}}
        except Exception as e:
            return {"error": {"message": f"An unexpected error occurred: {e}"}}


    def get_status(self) -> dict:
        """Get the scheduler status from the daemon."""
        response = self._send_request("get_status")
        return response.get("result", {})

    def get_jobs(self) -> list:
        """Get the list of jobs from the daemon."""
        response = self._send_request("get_jobs")
        # In the response, isoformat strings need to be converted back to datetime
        jobs = response.get("result", [])
        from datetime import datetime
        for job in jobs:
            if job.get("next_run_time"):
                try:
                    job["next_run_time"] = datetime.fromisoformat(job["next_run_time"])
                except (ValueError, TypeError):
                    job["next_run_time"] = None # Handle potential parsing errors
        return jobs
