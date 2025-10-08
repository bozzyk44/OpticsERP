"""
Mock OFD Server for Testing Phase 2 Fiscalization

Author: AI Agent
Created: 2025-10-09
Task: OPTERP-13

Features:
- Flask HTTP server running in background thread
- Configurable failure modes (temporary, permanent)
- Stateful receipt tracking
- Thread-safe operations
- Fast startup (<1s)
- Clean shutdown

Usage:
    server = MockOFDServer(port=9000)
    server.start()
    server.set_success()  # All requests succeed
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


class MockOFDServer:
    """
    Lightweight HTTP Mock OFD Server for testing Phase 2 fiscalization

    Simulates real OFD API with configurable failure scenarios
    """

    def __init__(self, port: int = 9000, host: str = "127.0.0.1"):
        """
        Initialize Mock OFD Server

        Args:
            port: Port to listen on (default: 9000)
            host: Host to bind to (default: 127.0.0.1)
        """
        self.port = port
        self.host = host
        self.app = Flask(__name__)
        self.server: Optional[Any] = None
        self.thread: Optional[threading.Thread] = None

        # State (thread-safe)
        self._lock = threading.Lock()
        self._failure_count = 0  # Fail next N requests
        self._permanent_failure = False  # All requests fail
        self._received_receipts: List[Dict[str, Any]] = []  # Received receipts
        self._call_count = 0  # Total API calls

        # Configure Flask logging
        log = logging.getLogger('werkzeug')
        log.setLevel(logging.ERROR)  # Suppress Flask logs in tests

        # Setup routes
        self._setup_routes()

    def _setup_routes(self):
        """Setup Flask routes"""

        @self.app.route('/ofd/v1/receipt', methods=['POST'])
        def receipt():
            """Accept fiscal document (Phase 2 sync)"""
            with self._lock:
                self._call_count += 1

                # Check failure modes
                if self._permanent_failure:
                    return jsonify({"error": "OFD service unavailable"}), 503

                if self._failure_count > 0:
                    self._failure_count -= 1
                    return jsonify({"error": "Temporary OFD failure"}), 503

                # Success: store receipt
                receipt_data = request.get_json()
                self._received_receipts.append(receipt_data)

                return jsonify({
                    "status": "accepted",
                    "ofd_id": f"OFD-{self._call_count:06d}",
                    "timestamp": int(time.time())
                }), 200

        @self.app.route('/ofd/v1/health', methods=['GET'])
        def health():
            """Health check endpoint"""
            with self._lock:
                return jsonify({
                    "status": "healthy",
                    "permanent_failure": self._permanent_failure,
                    "failure_count": self._failure_count,
                    "call_count": self._call_count,
                    "receipts_received": len(self._received_receipts)
                }), 200

        @self.app.route('/ofd/v1/_test/reset', methods=['POST'])
        def reset():
            """Reset server state (test-only)"""
            self.reset()
            return jsonify({"status": "reset"}), 200

    def start(self):
        """
        Start Flask server in background thread

        Blocks until server is ready (max 5s timeout)
        """
        if self.thread and self.thread.is_alive():
            raise RuntimeError("Server already running")

        # Create server
        self.server = make_server(self.host, self.port, self.app, threaded=True)

        # Start in daemon thread
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

        # Wait for server ready (health check)
        import requests
        start_time = time.time()
        while time.time() - start_time < 5:
            try:
                resp = requests.get(f"http://{self.host}:{self.port}/ofd/v1/health", timeout=1)
                if resp.status_code == 200:
                    return  # Server ready
            except:
                pass
            time.sleep(0.1)

        raise TimeoutError(f"Mock OFD Server failed to start on {self.host}:{self.port}")

    def stop(self):
        """
        Stop Flask server and clean up resources

        Graceful shutdown with 5s timeout
        """
        if self.server:
            self.server.shutdown()
            self.server = None

        if self.thread:
            self.thread.join(timeout=5)
            self.thread = None

    def reset(self):
        """Reset server state (for tests)"""
        with self._lock:
            self._failure_count = 0
            self._permanent_failure = False
            self._received_receipts.clear()
            self._call_count = 0

    # Configuration methods

    def set_failure_count(self, count: int):
        """
        Fail next N requests

        Args:
            count: Number of requests to fail
        """
        with self._lock:
            self._failure_count = count

    def set_permanent_failure(self, enabled: bool):
        """
        Enable/disable permanent failure mode

        Args:
            enabled: If True, all requests fail with 503
        """
        with self._lock:
            self._permanent_failure = enabled

    def set_success(self):
        """Set server to success mode (all requests succeed)"""
        with self._lock:
            self._failure_count = 0
            self._permanent_failure = False

    # Query methods

    def get_received_receipts(self) -> List[Dict[str, Any]]:
        """
        Get all received receipts

        Returns:
            List of receipt data dictionaries
        """
        with self._lock:
            return self._received_receipts.copy()

    def get_call_count(self) -> int:
        """
        Get total API call count

        Returns:
            Total number of API calls
        """
        with self._lock:
            return self._call_count

    def __enter__(self):
        """Context manager support"""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager cleanup"""
        self.stop()
