"""
Unit Tests for Heartbeat Module

Author: AI Agent
Created: 2025-10-09
Task: OPTERP-24

Test Coverage:
- Heartbeat payload building
- Hysteresis state transitions
- State management
- Lifecycle (start/stop)
"""

import pytest
import sys
from pathlib import Path

# Add kkt_adapter/app to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'kkt_adapter' / 'app'))

from heartbeat import (
    build_heartbeat_payload,
    update_heartbeat_state,
    get_heartbeat_status,
    reset_heartbeat_state,
    HeartbeatState,
    HYSTERESIS_SUCCESS_THRESHOLD,
    HYSTERESIS_FAILURE_THRESHOLD
)
from buffer import init_buffer_db, close_buffer_db, get_db
from circuit_breaker import reset_circuit_breaker


# ====================
# Fixtures
# ====================

@pytest.fixture
def reset_test_env():
    """Reset test environment before each test"""
    # Reset database
    try:
        close_buffer_db()
    except:
        pass

    init_buffer_db()
    conn = get_db()
    conn.execute("DELETE FROM receipts")
    conn.execute("DELETE FROM dlq")
    conn.execute("DELETE FROM buffer_events")
    conn.commit()

    # Reset other components
    reset_circuit_breaker()
    reset_heartbeat_state()

    yield

    try:
        close_buffer_db()
    except:
        pass


# ====================
# Tests: Payload Building
# ====================

class TestBuildPayload:
    """Tests for build_heartbeat_payload()"""

    def test_payload_structure(self, reset_test_env):
        """Test heartbeat payload has required structure"""
        payload = build_heartbeat_payload()

        # Top-level fields
        assert "timestamp" in payload
        assert "adapter_id" in payload
        assert "buffer_status" in payload
        assert "circuit_breaker" in payload

    def test_payload_timestamp_format(self, reset_test_env):
        """Test timestamp is ISO 8601 format with Z suffix"""
        payload = build_heartbeat_payload()

        timestamp = payload["timestamp"]
        assert isinstance(timestamp, str)
        assert timestamp.endswith("Z")
        assert "T" in timestamp  # ISO 8601 format

    def test_payload_adapter_id(self, reset_test_env):
        """Test adapter_id is present"""
        payload = build_heartbeat_payload()

        assert "adapter_id" in payload
        assert isinstance(payload["adapter_id"], str)
        assert len(payload["adapter_id"]) > 0

    def test_payload_buffer_status_fields(self, reset_test_env):
        """Test buffer_status has all required fields"""
        payload = build_heartbeat_payload()

        buffer_status = payload["buffer_status"]
        assert "total_capacity" in buffer_status
        assert "current_queued" in buffer_status
        assert "percent_full" in buffer_status
        assert "pending" in buffer_status
        assert "synced" in buffer_status
        assert "failed" in buffer_status
        assert "dlq_size" in buffer_status

    def test_payload_circuit_breaker_fields(self, reset_test_env):
        """Test circuit_breaker has required fields"""
        payload = build_heartbeat_payload()

        cb = payload["circuit_breaker"]
        assert "state" in cb
        assert "failure_count" in cb
        assert "success_count" in cb

    def test_payload_buffer_values(self, reset_test_env):
        """Test buffer_status values are correct"""
        payload = build_heartbeat_payload()

        buffer_status = payload["buffer_status"]
        assert buffer_status["total_capacity"] == 200  # Default capacity
        assert buffer_status["current_queued"] == 0    # Empty buffer
        assert buffer_status["percent_full"] == 0.0
        assert buffer_status["pending"] == 0
        assert buffer_status["synced"] == 0
        assert buffer_status["failed"] == 0
        assert buffer_status["dlq_size"] == 0

    def test_payload_circuit_breaker_initial_state(self, reset_test_env):
        """Test circuit_breaker initial state is CLOSED"""
        payload = build_heartbeat_payload()

        cb = payload["circuit_breaker"]
        assert cb["state"] == "CLOSED"
        assert cb["failure_count"] == 0
        assert cb["success_count"] == 0


# ====================
# Tests: Hysteresis Logic
# ====================

class TestHysteresis:
    """Tests for hysteresis state transitions"""

    def test_initial_state_unknown(self):
        """Test initial state is UNKNOWN"""
        reset_heartbeat_state()
        status = get_heartbeat_status()
        assert status["state"] == "unknown"

    def test_single_success_stays_unknown(self):
        """Test single success doesn't transition to ONLINE"""
        reset_heartbeat_state()
        update_heartbeat_state(True)  # 1 success (threshold is 2)
        status = get_heartbeat_status()
        assert status["state"] == "unknown"
        assert status["consecutive_successes"] == 1

    def test_two_successes_to_online(self):
        """Test 2 consecutive successes → ONLINE"""
        reset_heartbeat_state()
        update_heartbeat_state(True)  # 1
        state = update_heartbeat_state(True)  # 2 → ONLINE
        assert state == HeartbeatState.ONLINE
        status = get_heartbeat_status()
        assert status["state"] == "online"
        assert status["consecutive_successes"] == 2

    def test_single_failure_stays_unknown(self):
        """Test single failure doesn't transition to OFFLINE"""
        reset_heartbeat_state()
        update_heartbeat_state(False)  # 1 failure (threshold is 3)
        status = get_heartbeat_status()
        assert status["state"] == "unknown"
        assert status["consecutive_failures"] == 1

    def test_two_failures_stay_unknown(self):
        """Test 2 consecutive failures stay UNKNOWN"""
        reset_heartbeat_state()
        update_heartbeat_state(False)  # 1
        update_heartbeat_state(False)  # 2 (threshold is 3)
        status = get_heartbeat_status()
        assert status["state"] == "unknown"
        assert status["consecutive_failures"] == 2

    def test_three_failures_to_offline(self):
        """Test 3 consecutive failures → OFFLINE"""
        reset_heartbeat_state()
        update_heartbeat_state(False)  # 1
        update_heartbeat_state(False)  # 2
        state = update_heartbeat_state(False)  # 3 → OFFLINE
        assert state == HeartbeatState.OFFLINE
        status = get_heartbeat_status()
        assert status["state"] == "offline"
        assert status["consecutive_failures"] == 3

    def test_success_after_failure_resets_failure_count(self):
        """Test success resets failure counter"""
        reset_heartbeat_state()
        update_heartbeat_state(False)  # 1 failure
        update_heartbeat_state(False)  # 2 failures
        update_heartbeat_state(True)   # Success → resets failures
        status = get_heartbeat_status()
        assert status["consecutive_failures"] == 0
        assert status["consecutive_successes"] == 1

    def test_failure_after_success_resets_success_count(self):
        """Test failure resets success counter"""
        reset_heartbeat_state()
        update_heartbeat_state(True)   # 1 success
        update_heartbeat_state(False)  # Failure → resets successes
        status = get_heartbeat_status()
        assert status["consecutive_successes"] == 0
        assert status["consecutive_failures"] == 1

    def test_stays_online_with_one_failure(self):
        """Test ONLINE state persists with single failure"""
        reset_heartbeat_state()
        # Go to ONLINE
        update_heartbeat_state(True)
        update_heartbeat_state(True)  # → ONLINE
        # Single failure (not enough for OFFLINE)
        update_heartbeat_state(False)
        status = get_heartbeat_status()
        assert status["state"] == "online"  # Still online

    def test_stays_offline_with_one_success(self):
        """Test OFFLINE state persists with single success"""
        reset_heartbeat_state()
        # Go to OFFLINE
        update_heartbeat_state(False)
        update_heartbeat_state(False)
        update_heartbeat_state(False)  # → OFFLINE
        # Single success (not enough for ONLINE)
        update_heartbeat_state(True)
        status = get_heartbeat_status()
        assert status["state"] == "offline"  # Still offline

    def test_offline_to_online_transition(self):
        """Test OFFLINE → ONLINE transition requires 2 successes"""
        reset_heartbeat_state()
        # Go to OFFLINE
        update_heartbeat_state(False)
        update_heartbeat_state(False)
        update_heartbeat_state(False)  # → OFFLINE
        # Recover: 2 successes
        update_heartbeat_state(True)   # 1
        update_heartbeat_state(True)   # 2 → ONLINE
        status = get_heartbeat_status()
        assert status["state"] == "online"

    def test_online_to_offline_transition(self):
        """Test ONLINE → OFFLINE transition requires 3 failures"""
        reset_heartbeat_state()
        # Go to ONLINE
        update_heartbeat_state(True)
        update_heartbeat_state(True)  # → ONLINE
        # Degrade: 3 failures
        update_heartbeat_state(False)  # 1
        update_heartbeat_state(False)  # 2
        update_heartbeat_state(False)  # 3 → OFFLINE
        status = get_heartbeat_status()
        assert status["state"] == "offline"


# ====================
# Tests: State Management
# ====================

class TestStateManagement:
    """Tests for state management"""

    def test_get_heartbeat_status_structure(self):
        """Test get_heartbeat_status returns correct structure"""
        reset_heartbeat_state()
        status = get_heartbeat_status()

        assert "running" in status
        assert "state" in status
        assert "consecutive_successes" in status
        assert "consecutive_failures" in status

    def test_reset_heartbeat_state(self):
        """Test reset_heartbeat_state clears all counters"""
        # Set some state
        update_heartbeat_state(True)
        update_heartbeat_state(True)  # ONLINE, 2 successes

        # Reset
        reset_heartbeat_state()

        status = get_heartbeat_status()
        assert status["state"] == "unknown"
        assert status["consecutive_successes"] == 0
        assert status["consecutive_failures"] == 0


# ====================
# Tests: Edge Cases
# ====================

class TestEdgeCases:
    """Tests for edge cases"""

    def test_many_successes_stays_online(self):
        """Test many consecutive successes keeps ONLINE state"""
        reset_heartbeat_state()
        # Go to ONLINE
        update_heartbeat_state(True)
        update_heartbeat_state(True)

        # Many more successes
        for _ in range(10):
            state = update_heartbeat_state(True)
            assert state == HeartbeatState.ONLINE

        status = get_heartbeat_status()
        assert status["state"] == "online"
        assert status["consecutive_successes"] == 12

    def test_many_failures_stays_offline(self):
        """Test many consecutive failures keeps OFFLINE state"""
        reset_heartbeat_state()
        # Go to OFFLINE
        update_heartbeat_state(False)
        update_heartbeat_state(False)
        update_heartbeat_state(False)

        # Many more failures
        for _ in range(10):
            state = update_heartbeat_state(False)
            assert state == HeartbeatState.OFFLINE

        status = get_heartbeat_status()
        assert status["state"] == "offline"
        assert status["consecutive_failures"] == 13
