"""
Circuit Breaker for OFD API calls

Author: AI Agent
Created: 2025-10-08
Purpose: Prevent cascading failures when OFD is unavailable

Reference: CLAUDE.md §4.2, §1.3

The Circuit Breaker implements three states:
- CLOSED: Normal operation, requests pass through
- OPEN: Failures detected, requests fail fast
- HALF_OPEN: Testing recovery, limited requests allowed

State Transitions:
CLOSED --[failures >= threshold]--> OPEN
OPEN --[timeout elapsed]--> HALF_OPEN
HALF_OPEN --[success]--> CLOSED
HALF_OPEN --[failure]--> OPEN
"""

import pybreaker
import logging
from typing import Optional, Callable
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class CircuitBreakerStats:
    """Circuit Breaker statistics"""
    state: str  # CLOSED, OPEN, HALF_OPEN
    failure_count: int
    success_count: int
    last_failure_time: Optional[datetime]
    last_state_change: datetime


class OFDCircuitBreaker:
    """
    Circuit Breaker for OFD API calls

    Configuration:
    - failure_threshold: Number of failures before opening circuit (default: 5)
    - recovery_timeout: Seconds to wait before trying HALF_OPEN (default: 60)
    - half_open_max_calls: Max calls in HALF_OPEN state (default: 2)

    Example:
        cb = OFDCircuitBreaker(failure_threshold=5, recovery_timeout=60)

        try:
            result = cb.call(ofd_client.send_receipt, receipt_data)
        except pybreaker.CircuitBreakerError:
            # Circuit is OPEN, fallback to buffer
            logger.warning("OFD unavailable, buffering receipt")
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        half_open_max_calls: int = 2
    ):
        self._failure_threshold = failure_threshold
        self._recovery_timeout = recovery_timeout
        self._half_open_max_calls = half_open_max_calls

        # Create pybreaker instance
        self._breaker = pybreaker.CircuitBreaker(
            fail_max=failure_threshold,
            reset_timeout=recovery_timeout,
            state_storage=pybreaker.CircuitMemoryStorage(state=pybreaker.STATE_CLOSED)
        )

        # Statistics
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: Optional[datetime] = None
        self._last_state_change = datetime.now()

    def call(self, func: Callable, *args, **kwargs):
        """
        Execute function with circuit breaker protection

        Args:
            func: Function to call
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Function result

        Raises:
            pybreaker.CircuitBreakerError: Circuit is OPEN
            Exception: Function raised exception
        """
        try:
            result = self._breaker.call(func, *args, **kwargs)
            self._success_count += 1
            logger.debug(f"Circuit Breaker call succeeded, total: {self._success_count}")
            return result

        except pybreaker.CircuitBreakerError as e:
            # Circuit is OPEN - fail fast
            logger.warning(f"Circuit Breaker OPEN: {e}")
            raise

        except Exception as e:
            # Function failed - record failure
            self._failure_count += 1
            self._last_failure_time = datetime.now()
            logger.error(f"Circuit Breaker call failed: {e}, total failures: {self._failure_count}")
            raise

    @property
    def state(self) -> str:
        """Get current circuit breaker state"""
        state_map = {
            pybreaker.STATE_CLOSED: "CLOSED",
            pybreaker.STATE_OPEN: "OPEN",
            pybreaker.STATE_HALF_OPEN: "HALF_OPEN"
        }
        return state_map.get(self._breaker.current_state, "UNKNOWN")

    @property
    def is_closed(self) -> bool:
        """Check if circuit is CLOSED"""
        return self._breaker.current_state == pybreaker.STATE_CLOSED

    @property
    def is_open(self) -> bool:
        """Check if circuit is OPEN"""
        return self._breaker.current_state == pybreaker.STATE_OPEN

    @property
    def is_half_open(self) -> bool:
        """Check if circuit is HALF_OPEN"""
        return self._breaker.current_state == pybreaker.STATE_HALF_OPEN

    def get_stats(self) -> CircuitBreakerStats:
        """Get circuit breaker statistics"""
        return CircuitBreakerStats(
            state=self.state,
            failure_count=self._failure_count,
            success_count=self._success_count,
            last_failure_time=self._last_failure_time,
            last_state_change=self._last_state_change
        )

    def reset(self):
        """Reset circuit breaker to CLOSED state"""
        # Reset pybreaker state using internal state storage
        self._breaker._state_storage.state = pybreaker.STATE_CLOSED

        # Reset our internal statistics
        self._failure_count = 0
        self._last_failure_time = None
        self._last_state_change = datetime.now()
        logger.info("Circuit Breaker reset to CLOSED")


# Global instance
_ofd_circuit_breaker: Optional[OFDCircuitBreaker] = None


def get_circuit_breaker() -> OFDCircuitBreaker:
    """
    Get global circuit breaker instance

    Returns singleton instance of OFDCircuitBreaker with default configuration.
    """
    global _ofd_circuit_breaker
    if _ofd_circuit_breaker is None:
        _ofd_circuit_breaker = OFDCircuitBreaker()
    return _ofd_circuit_breaker


def reset_circuit_breaker():
    """
    Reset global circuit breaker (for testing)

    Sets global instance to None, forcing new instance on next get_circuit_breaker() call.
    """
    global _ofd_circuit_breaker
    _ofd_circuit_breaker = None
