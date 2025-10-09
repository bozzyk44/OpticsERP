"""
Unit Tests for Mock Odoo Server

Author: AI Agent
Created: 2025-10-09
Task: OPTERP-26

Test Coverage:
- Server lifecycle (start/stop)
- Heartbeat endpoint (success/failure modes)
- State tracking (received heartbeats, call counts)
- Thread safety
- Context manager
"""

import pytest
import requests
import time
import threading
from pathlib import Path
import sys

# Add integration test directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'integration'))

from mock_odoo_server import MockOdooServer


# ====================
# Fixtures
# ====================

@pytest.fixture
def server():
    """Create Mock Odoo Server instance"""
    server = MockOdooServer(port=8069)
    yield server
    # Cleanup
    try:
        server.stop()
    except:
        pass


@pytest.fixture
def running_server():
    """Create and start Mock Odoo Server"""
    server = MockOdooServer(port=8069)
    server.start()
    time.sleep(0.5)  # Wait for server to be ready
    yield server
    server.stop()


# ====================
# Tests: Server Lifecycle
# ====================

class TestMockOdooServerBasic:
    """Tests for basic server operations"""

    def test_server_creation(self, server):
        """Test server can be created"""
        assert server.port == 8069
        assert server.host == "127.0.0.1"

    def test_server_startup(self, server):
        """Test server starts successfully"""
        server.start()
        time.sleep(0.5)

        # Verify server is running (health check)
        response = requests.get("http://localhost:8069/health", timeout=2)
        assert response.status_code == 200
        assert response.json()["status"] == "ok"

        server.stop()

    def test_server_shutdown(self, running_server):
        """Test server stops gracefully"""
        running_server.stop()
        time.sleep(0.5)

        # Verify server is stopped
        with pytest.raises(requests.ConnectionError):
            requests.get("http://localhost:8069/health", timeout=1)

    def test_server_context_manager(self):
        """Test server works with context manager"""
        with MockOdooServer(port=8069) as server:
            time.sleep(0.5)
            response = requests.get("http://localhost:8069/health", timeout=2)
            assert response.status_code == 200

        # Verify server stopped after context exit
        time.sleep(0.5)
        with pytest.raises(requests.ConnectionError):
            requests.get("http://localhost:8069/health", timeout=1)

    def test_server_double_start_raises(self, running_server):
        """Test starting already running server raises error"""
        with pytest.raises(RuntimeError, match="already running"):
            running_server.start()


# ====================
# Tests: Heartbeat Endpoint
# ====================

class TestHeartbeatEndpoint:
    """Tests for heartbeat endpoint"""

    def test_heartbeat_success_mode(self, running_server):
        """Test heartbeat returns 200 OK in success mode"""
        running_server.set_success()

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
            json=heartbeat_data,
            timeout=2
        )

        assert response.status_code == 200
        assert response.json()["status"] == "ok"
        assert response.json()["message"] == "Heartbeat received"

    def test_heartbeat_permanent_failure(self, running_server):
        """Test heartbeat returns 503 in permanent failure mode"""
        running_server.set_permanent_failure(True)

        heartbeat_data = {
            "timestamp": "2025-10-09T12:00:00Z",
            "adapter_id": "KKT-001"
        }

        response = requests.post(
            "http://localhost:8069/api/v1/kkt/heartbeat",
            json=heartbeat_data,
            timeout=2
        )

        assert response.status_code == 503
        assert "error" in response.json()

    def test_heartbeat_temporary_failure(self, running_server):
        """Test heartbeat fails N times then succeeds"""
        running_server.set_failure_count(2)

        heartbeat_data = {
            "timestamp": "2025-10-09T12:00:00Z",
            "adapter_id": "KKT-001"
        }

        # First heartbeat - failure
        response1 = requests.post(
            "http://localhost:8069/api/v1/kkt/heartbeat",
            json=heartbeat_data,
            timeout=2
        )
        assert response1.status_code == 503

        # Second heartbeat - failure
        response2 = requests.post(
            "http://localhost:8069/api/v1/kkt/heartbeat",
            json=heartbeat_data,
            timeout=2
        )
        assert response2.status_code == 503

        # Third heartbeat - success (count exhausted)
        response3 = requests.post(
            "http://localhost:8069/api/v1/kkt/heartbeat",
            json=heartbeat_data,
            timeout=2
        )
        assert response3.status_code == 200

    def test_heartbeat_stores_payload(self, running_server):
        """Test heartbeat stores received payload"""
        running_server.set_success()

        heartbeat_data = {
            "timestamp": "2025-10-09T12:00:00Z",
            "adapter_id": "KKT-001",
            "buffer_status": {
                "total_capacity": 200,
                "current_queued": 10
            }
        }

        response = requests.post(
            "http://localhost:8069/api/v1/kkt/heartbeat",
            json=heartbeat_data,
            timeout=2
        )
        assert response.status_code == 200

        # Verify payload was stored
        received = running_server.get_received_heartbeats()
        assert len(received) == 1
        assert received[0]["adapter_id"] == "KKT-001"
        assert received[0]["buffer_status"]["current_queued"] == 10


# ====================
# Tests: State Tracking
# ====================

class TestStateTracking:
    """Tests for state tracking"""

    def test_call_count_increments(self, running_server):
        """Test call count increments for each heartbeat"""
        running_server.set_success()

        heartbeat_data = {"timestamp": "2025-10-09T12:00:00Z"}

        # Send 3 heartbeats
        for i in range(3):
            requests.post(
                "http://localhost:8069/api/v1/kkt/heartbeat",
                json=heartbeat_data,
                timeout=2
            )

        assert running_server.get_call_count() == 3

    def test_call_count_increments_on_failure(self, running_server):
        """Test call count increments even on failure"""
        running_server.set_permanent_failure(True)

        heartbeat_data = {"timestamp": "2025-10-09T12:00:00Z"}

        # Send 2 heartbeats (both fail)
        for i in range(2):
            requests.post(
                "http://localhost:8069/api/v1/kkt/heartbeat",
                json=heartbeat_data,
                timeout=2
            )

        assert running_server.get_call_count() == 2

    def test_received_heartbeats_only_on_success(self, running_server):
        """Test received_heartbeats only stores successful heartbeats"""
        running_server.set_failure_count(1)

        heartbeat_data = {"timestamp": "2025-10-09T12:00:00Z", "adapter_id": "KKT-001"}

        # First heartbeat - fails
        requests.post(
            "http://localhost:8069/api/v1/kkt/heartbeat",
            json=heartbeat_data,
            timeout=2
        )

        # Second heartbeat - succeeds
        requests.post(
            "http://localhost:8069/api/v1/kkt/heartbeat",
            json=heartbeat_data,
            timeout=2
        )

        # Only 1 heartbeat stored (the successful one)
        received = running_server.get_received_heartbeats()
        assert len(received) == 1
        assert running_server.get_call_count() == 2

    def test_reset_clears_state(self, running_server):
        """Test reset clears all state"""
        running_server.set_success()

        heartbeat_data = {"timestamp": "2025-10-09T12:00:00Z"}

        # Send 2 heartbeats
        for i in range(2):
            requests.post(
                "http://localhost:8069/api/v1/kkt/heartbeat",
                json=heartbeat_data,
                timeout=2
            )

        assert running_server.get_call_count() == 2
        assert len(running_server.get_received_heartbeats()) == 2

        # Reset
        running_server.reset()

        assert running_server.get_call_count() == 0
        assert len(running_server.get_received_heartbeats()) == 0


# ====================
# Tests: Failure Modes
# ====================

class TestFailureModes:
    """Tests for failure mode configuration"""

    def test_set_success_clears_failures(self, running_server):
        """Test set_success clears all failure modes"""
        running_server.set_permanent_failure(True)
        running_server.set_failure_count(5)

        # Clear with set_success
        running_server.set_success()

        heartbeat_data = {"timestamp": "2025-10-09T12:00:00Z"}
        response = requests.post(
            "http://localhost:8069/api/v1/kkt/heartbeat",
            json=heartbeat_data,
            timeout=2
        )

        assert response.status_code == 200

    def test_permanent_failure_overrides_count(self, running_server):
        """Test permanent failure takes precedence over count"""
        running_server.set_failure_count(1)  # Would fail once
        running_server.set_permanent_failure(True)  # Override

        heartbeat_data = {"timestamp": "2025-10-09T12:00:00Z"}

        # All heartbeats fail
        for i in range(3):
            response = requests.post(
                "http://localhost:8069/api/v1/kkt/heartbeat",
                json=heartbeat_data,
                timeout=2
            )
            assert response.status_code == 503

    def test_disable_permanent_failure(self, running_server):
        """Test disabling permanent failure"""
        running_server.set_permanent_failure(True)
        running_server.set_permanent_failure(False)  # Disable

        heartbeat_data = {"timestamp": "2025-10-09T12:00:00Z"}
        response = requests.post(
            "http://localhost:8069/api/v1/kkt/heartbeat",
            json=heartbeat_data,
            timeout=2
        )

        assert response.status_code == 200


# ====================
# Tests: Thread Safety
# ====================

class TestThreadSafety:
    """Tests for thread safety"""

    def test_concurrent_heartbeats(self, running_server):
        """Test concurrent heartbeats are handled safely"""
        running_server.set_success()

        def send_heartbeat(adapter_id):
            heartbeat_data = {
                "timestamp": "2025-10-09T12:00:00Z",
                "adapter_id": adapter_id
            }
            requests.post(
                "http://localhost:8069/api/v1/kkt/heartbeat",
                json=heartbeat_data,
                timeout=2
            )

        # Send 10 heartbeats concurrently
        threads = []
        for i in range(10):
            thread = threading.Thread(target=send_heartbeat, args=(f"KKT-{i:03d}",))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # Verify all heartbeats received
        assert running_server.get_call_count() == 10
        assert len(running_server.get_received_heartbeats()) == 10


# ====================
# Tests: Edge Cases
# ====================

class TestEdgeCases:
    """Tests for edge cases"""

    def test_empty_heartbeat_payload(self, running_server):
        """Test heartbeat with empty payload"""
        running_server.set_success()

        response = requests.post(
            "http://localhost:8069/api/v1/kkt/heartbeat",
            json={},
            timeout=2
        )

        assert response.status_code == 200
        received = running_server.get_received_heartbeats()
        assert len(received) == 1
        assert received[0] == {}

    def test_large_heartbeat_payload(self, running_server):
        """Test heartbeat with large payload"""
        running_server.set_success()

        # Create large payload
        heartbeat_data = {
            "timestamp": "2025-10-09T12:00:00Z",
            "adapter_id": "KKT-001",
            "buffer_status": {
                "large_field": "x" * 10000  # 10KB string
            }
        }

        response = requests.post(
            "http://localhost:8069/api/v1/kkt/heartbeat",
            json=heartbeat_data,
            timeout=2
        )

        assert response.status_code == 200
        received = running_server.get_received_heartbeats()
        assert len(received[0]["buffer_status"]["large_field"]) == 10000
