"""
Mock Odoo Server for Testing Heartbeat

Author: AI Agent
Created: 2025-10-09
Task: OPTERP-26

Features:
- Flask HTTP server running in background thread
- Heartbeat endpoint: POST /api/v1/kkt/heartbeat
- Configurable response modes (success, failure)
- Stateful heartbeat tracking
- Thread-safe operations
- Fast startup (<1s)
- Clean shutdown

Usage:
    server = MockOdooServer(port=8069)
    server.start()
    server.set_success()  # All heartbeats succeed
    # ... test code ...
    server.stop()
"""

import threading
import time
import json
from typing import List, Dict, Any, Optional
from flask import Flask, request, jsonify
from werkzeug.serving import make_server
import logging


class MockOdooServer:
    """
    Lightweight HTTP Mock Odoo Server for testing heartbeat

    Simulates real Odoo heartbeat endpoint with configurable scenarios
    """

    def __init__(self, port: int = 8069, host: str = "127.0.0.1"):
        """
        Initialize Mock Odoo Server

        Args:
            port: Port to listen on (default: 8069, standard Odoo port)
            host: Host to bind to (default: 127.0.0.1)
        """
        self.port = port
        self.host = host
        self.app = Flask(__name__)
        self.server: Optional[Any] = None
        self.thread: Optional[threading.Thread] = None

        # Thread-safe state
        self._lock = threading.Lock()
        self._failure_mode = False
        self._permanent_failure = False
        self._failure_count = 0
        self._received_heartbeats: List[Dict[str, Any]] = []
        self._call_count = 0

        # Disable Flask logging (reduce noise in tests)
        log = logging.getLogger('werkzeug')
        log.setLevel(logging.ERROR)

        # Setup routes
        self._setup_routes()

    def _setup_routes(self):
        """Setup Flask routes"""

        @self.app.route('/api/v1/kkt/heartbeat', methods=['POST'])
        def heartbeat():
            """
            Heartbeat endpoint

            Accepts heartbeat from KKT Adapter and returns 200 OK or error
            based on current failure mode.
            """
            with self._lock:
                self._call_count += 1

                # Check permanent failure mode
                if self._permanent_failure:
                    return jsonify({"error": "Odoo service unavailable"}), 503

                # Check temporary failure mode
                if self._failure_count > 0:
                    self._failure_count -= 1
                    return jsonify({"error": "Temporary Odoo failure"}), 503

                # Success mode - store heartbeat
                heartbeat_data = request.get_json()
                self._received_heartbeats.append(heartbeat_data)

                return jsonify({
                    "status": "ok",
                    "message": "Heartbeat received"
                }), 200

        @self.app.route('/health', methods=['GET'])
        def health():
            """Health check endpoint"""
            return jsonify({"status": "ok"}), 200

    def start(self):
        """
        Start Mock Odoo Server in background thread

        Returns immediately after server starts listening
        """
        if self.thread and self.thread.is_alive():
            raise RuntimeError("Mock Odoo Server already running")

        # Create server
        self.server = make_server(
            self.host,
            self.port,
            self.app,
            threaded=True
        )

        # Start in background thread
        self.thread = threading.Thread(
            target=self.server.serve_forever,
            daemon=True
        )
        self.thread.start()

        # Wait for server to be ready (max 2s)
        start_time = time.time()
        while time.time() - start_time < 2:
            try:
                import requests
                response = requests.get(f"http://{self.host}:{self.port}/health", timeout=1)
                if response.status_code == 200:
                    break
            except:
                time.sleep(0.1)

    def stop(self):
        """
        Stop Mock Odoo Server (graceful shutdown)

        Waits for server thread to terminate
        """
        if self.server:
            self.server.shutdown()
            self.server = None

        if self.thread:
            self.thread.join(timeout=2)
            self.thread = None

    def set_success(self):
        """
        Set success mode - all heartbeats return 200 OK

        Clears all failure modes
        """
        with self._lock:
            self._failure_mode = False
            self._permanent_failure = False
            self._failure_count = 0

    def set_failure_count(self, count: int):
        """
        Set temporary failure mode

        Next `count` heartbeats will fail with 503,
        then revert to success mode.

        Args:
            count: Number of heartbeats to fail
        """
        with self._lock:
            self._failure_count = count
            self._permanent_failure = False

    def set_permanent_failure(self, enabled: bool = True):
        """
        Set permanent failure mode

        All heartbeats will fail with 503 until disabled.

        Args:
            enabled: True to enable permanent failure, False to disable
        """
        with self._lock:
            self._permanent_failure = enabled
            if enabled:
                self._failure_count = 0

    def get_received_heartbeats(self) -> List[Dict[str, Any]]:
        """
        Get list of received heartbeats

        Returns:
            List of heartbeat payloads (JSON dicts)
        """
        with self._lock:
            return list(self._received_heartbeats)

    def get_call_count(self) -> int:
        """
        Get total number of heartbeat calls

        Returns:
            Number of POST /api/v1/kkt/heartbeat calls
        """
        with self._lock:
            return self._call_count

    def reset(self):
        """
        Reset server state

        Clears:
        - Received heartbeats
        - Call count
        - Failure modes
        """
        with self._lock:
            self._received_heartbeats.clear()
            self._call_count = 0
            self._failure_mode = False
            self._permanent_failure = False
            self._failure_count = 0

    def __enter__(self):
        """Context manager entry - start server"""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - stop server"""
        self.stop()


# ====================
# Example Usage
# ====================

if __name__ == "__main__":
    # Demo: Start server, send test heartbeat, stop
    import requests

    print("Starting Mock Odoo Server on port 8069...")
    server = MockOdooServer(port=8069)
    server.start()

    try:
        print("Server started successfully")

        # Test heartbeat
        heartbeat_data = {
            "timestamp": "2025-10-09T12:00:00Z",
            "adapter_id": "KKT-001",
            "buffer_status": {
                "total_capacity": 200,
                "current_queued": 5,
                "percent_full": 2.5
            },
            "circuit_breaker": {
                "state": "CLOSED",
                "failure_count": 0
            }
        }

        response = requests.post(
            "http://localhost:8069/api/v1/kkt/heartbeat",
            json=heartbeat_data
        )

        print(f"Heartbeat response: {response.status_code} - {response.json()}")
        print(f"Received heartbeats: {len(server.get_received_heartbeats())}")

    finally:
        print("Stopping server...")
        server.stop()
        print("Server stopped")
