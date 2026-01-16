# OPTERP-8: Circuit Breaker Implementation

**Task:** Implement Circuit Breaker pattern for OFD API calls to prevent cascading failures

**Story Points:** 3
**Sprint:** Phase 1 - POC (Week 1-2)
**Status:** In Progress
**Created:** 2025-10-08
**Assignee:** AI Agent

---

## 📋 Task Description

Implement Circuit Breaker pattern to protect the system from cascading failures when OFD (Operator of Fiscal Data) service is unavailable. The circuit breaker will:
- Prevent repeated calls to failing OFD service
- Automatically failover to offline buffer
- Implement three states: CLOSED, OPEN, HALF_OPEN
- Track failure/success metrics

**References:**
- CLAUDE.md §4.2 (Двухфазная фискализация - Phase 2)
- CLAUDE.md §1.3 (Архитектурные паттерны - Circuit Breaker)
- docs/5. Руководство по офлайн-режиму.md §5.2 (Circuit Breaker)

---

## 🎯 Acceptance Criteria

- [ ] **AC1:** Circuit Breaker implemented with 3 states (CLOSED, OPEN, HALF_OPEN)
- [ ] **AC2:** Failure threshold configurable (default: 5 failures)
- [ ] **AC3:** Recovery timeout configurable (default: 60s)
- [ ] **AC4:** Half-open success threshold configurable (default: 2)
- [ ] **AC5:** Automatic state transitions working correctly
- [ ] **AC6:** Metrics tracking (failures, successes, state changes)
- [ ] **AC7:** Integration with health check endpoint
- [ ] **AC8:** Unit tests for all states and transitions (≥12 tests)
- [ ] **AC9:** All tests pass
- [ ] **AC10:** Test coverage ≥85%

---

## 📐 Implementation Plan

### Step 1: Research Circuit Breaker libraries (15 min)

**Options:**
1. **pybreaker** - Mature, well-documented
2. **circuitbreaker** - Simple, decorator-based
3. **Custom implementation** - Full control

**Decision:** Use **pybreaker** for maturity and feature-richness.

**Installation:**
```bash
pip install pybreaker
```

### Step 2: Create Circuit Breaker wrapper (30 min)

**File:** `kkt_adapter/app/circuit_breaker.py`

**Structure:**
```python
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

        # Register listeners
        self._breaker.add_listener(self._on_state_change)

    def _on_state_change(self, breaker, old_state, new_state):
        """Callback for state changes"""
        logger.warning(
            f"Circuit Breaker state changed: {old_state.name} -> {new_state.name}"
        )
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
        self._breaker.state = pybreaker.STATE_CLOSED
        self._failure_count = 0
        self._last_failure_time = None
        logger.info("Circuit Breaker reset to CLOSED")


# Global instance
_ofd_circuit_breaker: Optional[OFDCircuitBreaker] = None


def get_circuit_breaker() -> OFDCircuitBreaker:
    """Get global circuit breaker instance"""
    global _ofd_circuit_breaker
    if _ofd_circuit_breaker is None:
        _ofd_circuit_breaker = OFDCircuitBreaker()
    return _ofd_circuit_breaker


def reset_circuit_breaker():
    """Reset global circuit breaker (for testing)"""
    global _ofd_circuit_breaker
    _ofd_circuit_breaker = None
```

### Step 3: Integrate with main.py health check (15 min)

**Update:** `kkt_adapter/app/main.py`

```python
# In health_check() function
from circuit_breaker import get_circuit_breaker

cb = get_circuit_breaker()
cb_stats = cb.get_stats()

return HealthCheckResponse(
    status=overall_status,
    components={
        'buffer': {
            'status': 'healthy' if buffer_healthy else 'unhealthy',
            'percent_full': status.percent_full,
            'dlq_size': status.dlq_size,
            'pending': status.pending
        },
        'circuit_breaker': {
            'state': cb_stats.state,
            'failure_count': cb_stats.failure_count,
            'success_count': cb_stats.success_count,
            'last_failure': cb_stats.last_failure_time.isoformat() if cb_stats.last_failure_time else None
        },
        'database': {
            'status': 'healthy',
            'type': 'SQLite',
            'mode': 'WAL'
        }
    },
    version="0.1.0"
)
```

### Step 4: Create mock OFD client for testing (20 min)

**File:** `kkt_adapter/app/ofd_client.py`

```python
"""
Mock OFD Client for Testing

Author: AI Agent
Created: 2025-10-08
Purpose: Mock OFD API client for Circuit Breaker testing

Note: Real OFD client implementation will come in Phase 2 (OPTERP-12)
"""

import logging
import time
from typing import Dict, Any

logger = logging.getLogger(__name__)


class OFDClientError(Exception):
    """OFD client error"""
    pass


class OFDClient:
    """
    Mock OFD Client for testing Circuit Breaker

    Real implementation will be added in Phase 2.
    """

    def __init__(self, base_url: str = "https://ofd.example.com"):
        self.base_url = base_url
        self._fail_next = False  # For testing

    def send_receipt(self, receipt_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Send receipt to OFD

        Args:
            receipt_data: Receipt data to send

        Returns:
            OFD response with fiscal document

        Raises:
            OFDClientError: OFD unavailable or error
        """
        # Simulate network delay
        time.sleep(0.1)

        # For testing: simulate failure if flag set
        if self._fail_next:
            logger.error("OFD Client: Simulated failure")
            raise OFDClientError("OFD service unavailable")

        # Mock successful response
        logger.info(f"OFD Client: Receipt sent successfully for POS {receipt_data.get('pos_id')}")

        return {
            "fiscal_doc_number": "12345",
            "fiscal_doc_datetime": "2025-10-08T12:00:00Z",
            "fiscal_sign": "1234567890",
            "status": "accepted"
        }

    def set_fail_next(self, fail: bool = True):
        """Set flag to fail next request (for testing)"""
        self._fail_next = fail


# Global instance
_ofd_client: OFDClient | None = None


def get_ofd_client() -> OFDClient:
    """Get global OFD client instance"""
    global _ofd_client
    if _ofd_client is None:
        _ofd_client = OFDClient()
    return _ofd_client
```

### Step 5: Write unit tests (45 min)

**File:** `tests/unit/test_circuit_breaker.py`

**Test classes:**
- TestCircuitBreakerStates (4 tests)
- TestCircuitBreakerTransitions (4 tests)
- TestCircuitBreakerMetrics (2 tests)
- TestCircuitBreakerRecovery (2 tests)
- TestCircuitBreakerIntegration (2 tests)

### Step 6: Update requirements.txt (5 min)

```txt
# Add to kkt_adapter/requirements.txt
pybreaker==1.0.1  # Circuit Breaker pattern
```

### Step 7: Run tests and fix issues (30 min)

```bash
pytest tests/unit/test_circuit_breaker.py -v --cov=kkt_adapter/app/circuit_breaker --cov-report=term
```

### Step 8: Commit and push (10 min)

---

## 🧪 Testing Strategy

**Test Coverage:**

1. **State Tests:**
   - Initial state is CLOSED
   - State transitions to OPEN after failures
   - State transitions to HALF_OPEN after timeout
   - State transitions to CLOSED after success in HALF_OPEN

2. **Transition Tests:**
   - CLOSED -> OPEN (after failure_threshold failures)
   - OPEN -> HALF_OPEN (after recovery_timeout)
   - HALF_OPEN -> CLOSED (after success)
   - HALF_OPEN -> OPEN (after failure)

3. **Metrics Tests:**
   - Failure count increments
   - Success count increments
   - Last failure time recorded

4. **Recovery Tests:**
   - Recovery timeout works
   - Half-open allows limited calls

5. **Integration Tests:**
   - Circuit breaker integrates with OFD client
   - Health check reflects circuit breaker state

---

## 📦 Deliverables

- [ ] `kkt_adapter/app/circuit_breaker.py` (≈200 lines)
- [ ] `kkt_adapter/app/ofd_client.py` (≈80 lines, mock)
- [ ] `tests/unit/test_circuit_breaker.py` (≈350 lines)
- [ ] Updated `kkt_adapter/app/main.py` (health check integration)
- [ ] Updated `kkt_adapter/requirements.txt` (pybreaker)
- [ ] Test log: `tests/logs/unit/20251008_OPTERP-8_circuit_breaker_tests.log`
- [ ] All 14+ tests passing
- [ ] Coverage ≥85%
- [ ] Code committed to `feature/phase1-poc` branch
- [ ] Changes pushed to remote

---

## ⏱️ Time Estimate

| Step | Task | Time |
|------|------|------|
| 1 | Research Circuit Breaker libraries | 15 min |
| 2 | Create Circuit Breaker wrapper | 30 min |
| 3 | Integrate with health check | 15 min |
| 4 | Create mock OFD client | 20 min |
| 5 | Write unit tests | 45 min |
| 6 | Update requirements.txt | 5 min |
| 7 | Run tests and fix issues | 30 min |
| 8 | Commit and push | 10 min |
| **TOTAL** | **2h 50min** |

---

## 🔗 Dependencies

**Requires:**
- ✅ OPTERP-6: FastAPI Main Application (completed)
- ✅ OPTERP-7: FastAPI Unit Tests (completed)

**Blocks:**
- OPTERP-9: Sync Worker (needs Circuit Breaker for OFD calls)
- OPTERP-12: OFD Client Implementation (Phase 2)

---

## 📝 Notes

### Circuit Breaker States

**CLOSED (Normal):**
- All requests pass through
- Failures are counted
- Transitions to OPEN when failure_threshold reached

**OPEN (Failing):**
- Requests fail immediately (fail-fast)
- No calls to OFD service
- After recovery_timeout, transitions to HALF_OPEN

**HALF_OPEN (Testing):**
- Limited number of requests allowed
- If successful, transitions to CLOSED
- If failed, transitions back to OPEN

### Configuration

Default values (configurable):
- `failure_threshold`: 5 failures
- `recovery_timeout`: 60 seconds
- `half_open_max_calls`: 2 calls

### Future Enhancements (not in this task)

- Distributed circuit breaker (Redis-based state)
- Metrics export to Prometheus
- Circuit breaker per POS terminal
- Exponential backoff for recovery timeout
- Manual circuit breaker control endpoint

---

## ✅ Definition of Done

- [ ] All 8 implementation steps completed
- [ ] Circuit Breaker implemented with 3 states
- [ ] 14+ tests written and passing
- [ ] Coverage ≥85% achieved
- [ ] Integration with health check working
- [ ] Test log saved
- [ ] No failing tests
- [ ] Code committed with message: `feat(circuit-breaker): implement Circuit Breaker pattern for OFD API [OPTERP-8]`
- [ ] Pushed to remote

---

## 🚀 Ready to Implement

This task plan is complete and ready for execution. Proceed with Step 1.
