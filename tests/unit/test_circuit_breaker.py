"""
Unit Tests for Circuit Breaker

Author: AI Agent
Created: 2025-10-08
Updated: 2025-10-09
Purpose: Comprehensive tests for OFD Circuit Breaker implementation

Test Coverage:
- Circuit Breaker states (CLOSED, OPEN, HALF_OPEN)
- State transitions
- Failure/success counting
- Metrics tracking
- Integration with OFD client

Reference: OPTERP-12, OPTERP-14
"""

import pytest
import sys
import time
from pathlib import Path
from datetime import datetime, timedelta
import pybreaker

# Add kkt_adapter/app to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'kkt_adapter' / 'app'))

from circuit_breaker import (
    OFDCircuitBreaker,
    get_circuit_breaker,
    reset_circuit_breaker
)
from ofd_client import OFDClient, OFDClientError, reset_ofd_client


# ====================
# Fixtures
# ====================

@pytest.fixture
def cb():
    """Create circuit breaker with short timeouts for testing"""
    reset_circuit_breaker()
    return OFDCircuitBreaker(
        failure_threshold=3,  # Reduced for faster tests
        recovery_timeout=2,   # 2 seconds for testing
        half_open_max_calls=2
    )


@pytest.fixture
def ofd_client():
    """Create OFD client for testing"""
    reset_ofd_client()
    return OFDClient()


@pytest.fixture
def receipt_data():
    """Sample receipt data for testing"""
    return {
        "pos_id": "POS-TEST",
        "type": "sale",
        "items": [{"name": "Test", "price": 100}]
    }


# ====================
# Tests: Circuit Breaker States
# ====================

class TestCircuitBreakerStates:
    """Tests for circuit breaker state management"""

    def test_initial_state_is_closed(self, cb):
        """Test that circuit breaker starts in CLOSED state"""
        assert cb.state == "CLOSED"
        assert cb.is_closed is True
        assert cb.is_open is False
        assert cb.is_half_open is False

    def test_state_opens_after_failures(self, cb, ofd_client, receipt_data):
        """Test that circuit opens after failure threshold"""
        ofd_client.set_fail_next(True)

        # Make failures equal to threshold
        # Note: Last failure raises CircuitBreakerError (threshold reached)
        for i in range(3):
            with pytest.raises((OFDClientError, pybreaker.CircuitBreakerError)):
                cb.call(ofd_client.send_receipt, receipt_data)

        # Circuit should be OPEN now
        assert cb.state == "OPEN"
        assert cb.is_open is True

    def test_state_half_open_after_timeout(self, cb, ofd_client, receipt_data):
        """Test that circuit transitions to HALF_OPEN after recovery timeout"""
        ofd_client.set_fail_next(True)

        # Open the circuit
        for i in range(3):
            with pytest.raises((OFDClientError, pybreaker.CircuitBreakerError)):
                cb.call(ofd_client.send_receipt, receipt_data)

        assert cb.state == "OPEN"

        # Wait for recovery timeout
        time.sleep(2.5)

        # Next call should attempt in HALF_OPEN state
        ofd_client.set_fail_next(False)  # Allow success
        result = cb.call(ofd_client.send_receipt, receipt_data)

        assert result is not None
        # After successful call in HALF_OPEN, should be CLOSED
        assert cb.state == "CLOSED"

    def test_state_stays_closed_on_success(self, cb, ofd_client, receipt_data):
        """Test that circuit stays CLOSED on successful calls"""
        # Make several successful calls
        for i in range(10):
            cb.call(ofd_client.send_receipt, receipt_data)

        assert cb.state == "CLOSED"


# ====================
# Tests: State Transitions
# ====================

class TestCircuitBreakerTransitions:
    """Tests for circuit breaker state transitions"""

    def test_closed_to_open_transition(self, cb, ofd_client, receipt_data):
        """Test CLOSED -> OPEN transition"""
        assert cb.state == "CLOSED"

        ofd_client.set_fail_next(True)

        # Trigger failures
        for i in range(3):
            with pytest.raises((OFDClientError, pybreaker.CircuitBreakerError)):
                cb.call(ofd_client.send_receipt, receipt_data)

        assert cb.state == "OPEN"

    def test_open_to_half_open_transition(self, cb, ofd_client, receipt_data):
        """Test OPEN -> HALF_OPEN transition"""
        # Open the circuit
        ofd_client.set_fail_next(True)
        for i in range(3):
            with pytest.raises((OFDClientError, pybreaker.CircuitBreakerError)):
                cb.call(ofd_client.send_receipt, receipt_data)

        assert cb.state == "OPEN"

        # Wait for recovery timeout
        time.sleep(2.5)

        # Circuit should allow next call (HALF_OPEN)
        # We detect HALF_OPEN by attempting a call and checking it doesn't immediately fail
        ofd_client.set_fail_next(False)
        result = cb.call(ofd_client.send_receipt, receipt_data)
        assert result is not None

    def test_half_open_to_closed_on_success(self, cb, ofd_client, receipt_data):
        """Test HALF_OPEN -> CLOSED transition on success"""
        # Open circuit
        ofd_client.set_fail_next(True)
        for i in range(3):
            with pytest.raises((OFDClientError, pybreaker.CircuitBreakerError)):
                cb.call(ofd_client.send_receipt, receipt_data)

        # Wait for recovery
        time.sleep(2.5)

        # Successful call in HALF_OPEN should close circuit
        ofd_client.set_fail_next(False)
        cb.call(ofd_client.send_receipt, receipt_data)

        assert cb.state == "CLOSED"

    def test_half_open_to_open_on_failure(self, cb, ofd_client, receipt_data):
        """Test HALF_OPEN -> OPEN transition on failure"""
        # Open circuit
        ofd_client.set_fail_next(True)
        for i in range(3):
            with pytest.raises((OFDClientError, pybreaker.CircuitBreakerError)):
                cb.call(ofd_client.send_receipt, receipt_data)

        # Wait for recovery
        time.sleep(2.5)

        # Failed call in HALF_OPEN should reopen circuit
        ofd_client.set_fail_next(True)
        with pytest.raises((OFDClientError, pybreaker.CircuitBreakerError)):
            cb.call(ofd_client.send_receipt, receipt_data)

        assert cb.state == "OPEN"


# ====================
# Tests: Metrics and Counters
# ====================

class TestCircuitBreakerMetrics:
    """Tests for circuit breaker metrics tracking"""

    def test_failure_count_increments(self, cb, ofd_client, receipt_data):
        """Test that failure count increments correctly"""
        ofd_client.set_fail_next(True)

        for i in range(2):
            with pytest.raises(OFDClientError):
                cb.call(ofd_client.send_receipt, receipt_data)

        stats = cb.get_stats()
        assert stats.failure_count == 2

    def test_success_count_increments(self, cb, ofd_client, receipt_data):
        """Test that success count increments correctly"""
        for i in range(5):
            cb.call(ofd_client.send_receipt, receipt_data)

        stats = cb.get_stats()
        assert stats.success_count == 5

    def test_last_failure_time_recorded(self, cb, ofd_client, receipt_data):
        """Test that last failure time is recorded"""
        ofd_client.set_fail_next(True)

        before = datetime.now()
        with pytest.raises(OFDClientError):
            cb.call(ofd_client.send_receipt, receipt_data)
        after = datetime.now()

        stats = cb.get_stats()
        assert stats.last_failure_time is not None
        assert before <= stats.last_failure_time <= after


# ====================
# Tests: Circuit Breaker Behavior
# ====================

class TestCircuitBreakerBehavior:
    """Tests for circuit breaker fail-fast behavior"""

    def test_open_circuit_fails_fast(self, cb, ofd_client, receipt_data):
        """Test that OPEN circuit fails immediately without calling function"""
        # Open the circuit
        ofd_client.set_fail_next(True)
        for i in range(3):
            with pytest.raises((OFDClientError, pybreaker.CircuitBreakerError)):
                cb.call(ofd_client.send_receipt, receipt_data)

        call_count_before = ofd_client.get_call_count()

        # Next call should fail fast without calling OFD
        with pytest.raises(pybreaker.CircuitBreakerError):
            cb.call(ofd_client.send_receipt, receipt_data)

        call_count_after = ofd_client.get_call_count()

        # OFD client should NOT have been called
        assert call_count_after == call_count_before

    def test_reset_clears_state(self, cb, ofd_client, receipt_data):
        """Test that reset clears circuit breaker state"""
        # Open the circuit
        ofd_client.set_fail_next(True)
        for i in range(3):
            with pytest.raises((OFDClientError, pybreaker.CircuitBreakerError)):
                cb.call(ofd_client.send_receipt, receipt_data)

        assert cb.state == "OPEN"

        # Reset
        cb.reset()

        assert cb.state == "CLOSED"
        stats = cb.get_stats()
        assert stats.failure_count == 0
        assert stats.last_failure_time is None


# ====================
# Tests: Global Instance
# ====================

class TestGlobalInstance:
    """Tests for global circuit breaker singleton"""

    def test_get_circuit_breaker_returns_singleton(self):
        """Test that get_circuit_breaker returns same instance"""
        reset_circuit_breaker()

        cb1 = get_circuit_breaker()
        cb2 = get_circuit_breaker()

        assert cb1 is cb2

    def test_reset_circuit_breaker_clears_global(self):
        """Test that reset_circuit_breaker clears global instance"""
        cb1 = get_circuit_breaker()

        reset_circuit_breaker()

        cb2 = get_circuit_breaker()

        assert cb1 is not cb2


# ====================
# Tests: Edge Cases
# ====================

class TestEdgeCases:
    """Tests for edge cases and error handling"""

    def test_circuit_breaker_with_non_exception_return(self, cb):
        """Test circuit breaker with function that returns value"""
        def success_func():
            return {"status": "ok"}

        result = cb.call(success_func)
        assert result == {"status": "ok"}

    def test_circuit_breaker_with_custom_exception(self, cb):
        """Test circuit breaker with custom exception"""
        class CustomError(Exception):
            pass

        def failing_func():
            raise CustomError("Custom error")

        for i in range(3):
            with pytest.raises((CustomError, pybreaker.CircuitBreakerError)):
                cb.call(failing_func)

        assert cb.state == "OPEN"

    def test_mixed_success_and_failure(self, cb, ofd_client, receipt_data):
        """Test circuit breaker with mixed successes and failures"""
        # Success
        cb.call(ofd_client.send_receipt, receipt_data)

        # Failure
        ofd_client.set_fail_next(True)
        with pytest.raises(OFDClientError):
            cb.call(ofd_client.send_receipt, receipt_data)

        # Success
        ofd_client.set_fail_next(False)
        cb.call(ofd_client.send_receipt, receipt_data)

        # Circuit should still be CLOSED
        assert cb.state == "CLOSED"

        stats = cb.get_stats()
        assert stats.success_count == 2
        assert stats.failure_count == 1
