# Task Plan: OPTERP-27 - Create Heartbeat Unit Tests

**Date:** 2025-10-09
**Status:** ✅ Already Complete (implemented in OPTERP-24)
**Priority:** High
**Assignee:** AI Agent

---

## Objective

Create unit tests for heartbeat module (`tests/unit/test_heartbeat.py`).

---

## Requirements (from JIRA)

From `docs/jira/jira_import.csv` line 34:
> - test_heartbeat_success() passes
> - test_heartbeat_hysteresis_offline() passes
> - test_heartbeat_hysteresis_online() passes
> - test_heartbeat_payload() passes
> - 4+ tests total

---

## Current State Analysis

**Existing Implementation (OPTERP-24):**
- Heartbeat unit tests already fully implemented
- File: `tests/unit/test_heartbeat.py` (345 lines)
- **23 unit tests** (vs 4+ required)
- 100% pass rate
- Created in OPTERP-24 commit: 18378e4

**Test Coverage Exceeds Requirements:**

| JIRA Requirement | Actual Implementation | Status |
|------------------|----------------------|--------|
| test_heartbeat_success() | test_two_successes_to_online + 6 payload tests | ✅ Exceeded |
| test_heartbeat_hysteresis_offline() | test_three_failures_to_offline + 5 failure tests | ✅ Exceeded |
| test_heartbeat_hysteresis_online() | test_two_successes_to_online + 6 success tests | ✅ Exceeded |
| test_heartbeat_payload() | 7 payload building tests | ✅ Exceeded |
| 4+ tests total | **23 tests** | ✅ Exceeded (575%) |

---

## Existing Test Structure

### 1. Payload Building Tests (7 tests)

**File:** `tests/unit/test_heartbeat.py:71-144`

```python
class TestBuildPayload:
    def test_payload_structure(self, reset_test_env):
        """Test heartbeat payload has required structure"""
        payload = build_heartbeat_payload()
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
        assert "T" in timestamp

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
        assert buffer_status["total_capacity"] == 200
        assert buffer_status["current_queued"] == 0
        assert buffer_status["percent_full"] == 0.0

    def test_payload_circuit_breaker_initial_state(self, reset_test_env):
        """Test circuit_breaker initial state is CLOSED"""
        payload = build_heartbeat_payload()
        cb = payload["circuit_breaker"]
        assert cb["state"] == "CLOSED"
        assert cb["failure_count"] == 0
        assert cb["success_count"] == 0
```

**Coverage:** ✅ Fully covers `test_heartbeat_payload()` requirement

---

### 2. Hysteresis Logic Tests (12 tests)

**File:** `tests/unit/test_heartbeat.py:150-272`

**Initial State:**
```python
def test_initial_state_unknown(self):
    """Test initial state is UNKNOWN"""
    reset_heartbeat_state()
    status = get_heartbeat_status()
    assert status["state"] == "unknown"
```

**Success Transitions (6 tests):**
```python
def test_single_success_stays_unknown(self):
    """Test single success doesn't transition to ONLINE"""
    reset_heartbeat_state()
    update_heartbeat_state(True)  # 1 success (threshold is 2)
    status = get_heartbeat_status()
    assert status["state"] == "unknown"

def test_two_successes_to_online(self):  # ← JIRA requirement
    """Test 2 consecutive successes → ONLINE"""
    reset_heartbeat_state()
    update_heartbeat_state(True)
    state = update_heartbeat_state(True)
    assert state == HeartbeatState.ONLINE

def test_success_after_failure_resets_failure_count(self):
    """Test success resets failure counter"""
    reset_heartbeat_state()
    update_heartbeat_state(False)
    update_heartbeat_state(False)
    update_heartbeat_state(True)  # Reset
    status = get_heartbeat_status()
    assert status["consecutive_failures"] == 0
    assert status["consecutive_successes"] == 1

def test_stays_online_with_one_failure(self):
    """Test ONLINE state persists with single failure"""
    reset_heartbeat_state()
    update_heartbeat_state(True)
    update_heartbeat_state(True)  # → ONLINE
    update_heartbeat_state(False)  # Single failure
    status = get_heartbeat_status()
    assert status["state"] == "online"

def test_offline_to_online_transition(self):
    """Test OFFLINE → ONLINE transition requires 2 successes"""
    reset_heartbeat_state()
    # Go to OFFLINE
    update_heartbeat_state(False)
    update_heartbeat_state(False)
    update_heartbeat_state(False)
    # Recover
    update_heartbeat_state(True)
    update_heartbeat_state(True)
    status = get_heartbeat_status()
    assert status["state"] == "online"

def test_online_to_offline_transition(self):
    """Test ONLINE → OFFLINE transition requires 3 failures"""
    reset_heartbeat_state()
    # Go to ONLINE
    update_heartbeat_state(True)
    update_heartbeat_state(True)
    # Degrade
    update_heartbeat_state(False)
    update_heartbeat_state(False)
    update_heartbeat_state(False)
    status = get_heartbeat_status()
    assert status["state"] == "offline"
```

**Failure Transitions (5 tests):**
```python
def test_single_failure_stays_unknown(self):
    """Test single failure doesn't transition to OFFLINE"""
    reset_heartbeat_state()
    update_heartbeat_state(False)
    status = get_heartbeat_status()
    assert status["state"] == "unknown"

def test_two_failures_stay_unknown(self):
    """Test 2 consecutive failures stay UNKNOWN"""
    reset_heartbeat_state()
    update_heartbeat_state(False)
    update_heartbeat_state(False)
    status = get_heartbeat_status()
    assert status["state"] == "unknown"

def test_three_failures_to_offline(self):  # ← JIRA requirement
    """Test 3 consecutive failures → OFFLINE"""
    reset_heartbeat_state()
    update_heartbeat_state(False)
    update_heartbeat_state(False)
    state = update_heartbeat_state(False)
    assert state == HeartbeatState.OFFLINE

def test_failure_after_success_resets_success_count(self):
    """Test failure resets success counter"""
    reset_heartbeat_state()
    update_heartbeat_state(True)
    update_heartbeat_state(False)
    status = get_heartbeat_status()
    assert status["consecutive_successes"] == 0

def test_stays_offline_with_one_success(self):
    """Test OFFLINE state persists with single success"""
    reset_heartbeat_state()
    # Go to OFFLINE
    update_heartbeat_state(False)
    update_heartbeat_state(False)
    update_heartbeat_state(False)
    # Single success
    update_heartbeat_state(True)
    status = get_heartbeat_status()
    assert status["state"] == "offline"
```

**Coverage:** ✅ Fully covers hysteresis requirements:
- test_heartbeat_hysteresis_online() ← test_two_successes_to_online
- test_heartbeat_hysteresis_offline() ← test_three_failures_to_offline

---

### 3. State Management Tests (2 tests)

**File:** `tests/unit/test_heartbeat.py:278-304`

```python
class TestStateManagement:
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
        update_heartbeat_state(True)
        update_heartbeat_state(True)
        reset_heartbeat_state()
        status = get_heartbeat_status()
        assert status["state"] == "unknown"
        assert status["consecutive_successes"] == 0
        assert status["consecutive_failures"] == 0
```

---

### 4. Edge Cases Tests (2 tests)

**File:** `tests/unit/test_heartbeat.py:310-345`

```python
class TestEdgeCases:
    def test_many_successes_stays_online(self):
        """Test many consecutive successes keeps ONLINE state"""
        reset_heartbeat_state()
        update_heartbeat_state(True)
        update_heartbeat_state(True)
        for _ in range(10):
            state = update_heartbeat_state(True)
            assert state == HeartbeatState.ONLINE
        status = get_heartbeat_status()
        assert status["consecutive_successes"] == 12

    def test_many_failures_stays_offline(self):
        """Test many consecutive failures keeps OFFLINE state"""
        reset_heartbeat_state()
        update_heartbeat_state(False)
        update_heartbeat_state(False)
        update_heartbeat_state(False)
        for _ in range(10):
            state = update_heartbeat_state(False)
            assert state == HeartbeatState.OFFLINE
        status = get_heartbeat_status()
        assert status["consecutive_failures"] == 13
```

---

## Test Results (from OPTERP-24)

```
============================= test session starts =============================
tests/unit/test_heartbeat.py::TestBuildPayload::test_payload_structure PASSED
tests/unit/test_heartbeat.py::TestBuildPayload::test_payload_timestamp_format PASSED
tests/unit/test_heartbeat.py::TestBuildPayload::test_payload_adapter_id PASSED
tests/unit/test_heartbeat.py::TestBuildPayload::test_payload_buffer_status_fields PASSED
tests/unit/test_heartbeat.py::TestBuildPayload::test_payload_circuit_breaker_fields PASSED
tests/unit/test_heartbeat.py::TestBuildPayload::test_payload_buffer_values PASSED
tests/unit/test_heartbeat.py::TestBuildPayload::test_payload_circuit_breaker_initial_state PASSED
tests/unit/test_heartbeat.py::TestHysteresis::test_initial_state_unknown PASSED
tests/unit/test_heartbeat.py::TestHysteresis::test_single_success_stays_unknown PASSED
tests/unit/test_heartbeat.py::TestHysteresis::test_two_successes_to_online PASSED
tests/unit/test_heartbeat.py::TestHysteresis::test_single_failure_stays_unknown PASSED
tests/unit/test_heartbeat.py::TestHysteresis::test_two_failures_stay_unknown PASSED
tests/unit/test_heartbeat.py::TestHysteresis::test_three_failures_to_offline PASSED
tests/unit/test_heartbeat.py::TestHysteresis::test_success_after_failure_resets_failure_count PASSED
tests/unit/test_heartbeat.py::TestHysteresis::test_failure_after_success_resets_success_count PASSED
tests/unit/test_heartbeat.py::TestHysteresis::test_stays_online_with_one_failure PASSED
tests/unit/test_heartbeat.py::TestHysteresis::test_stays_offline_with_one_success PASSED
tests/unit/test_heartbeat.py::TestHysteresis::test_offline_to_online_transition PASSED
tests/unit/test_heartbeat.py::TestHysteresis::test_online_to_offline_transition PASSED
tests/unit/test_heartbeat.py::TestStateManagement::test_get_heartbeat_status_structure PASSED
tests/unit/test_heartbeat.py::TestStateManagement::test_reset_heartbeat_state PASSED
tests/unit/test_heartbeat.py::TestEdgeCases::test_many_successes_stays_online PASSED
tests/unit/test_heartbeat.py::TestEdgeCases::test_many_failures_stays_offline PASSED

======================== 23 passed ========================
```

---

## Acceptance Criteria

| JIRA Requirement | Status | Evidence |
|------------------|--------|----------|
| test_heartbeat_success() passes | ✅ Complete | test_two_successes_to_online + 6 payload tests PASS |
| test_heartbeat_hysteresis_offline() passes | ✅ Complete | test_three_failures_to_offline PASS |
| test_heartbeat_hysteresis_online() passes | ✅ Complete | test_two_successes_to_online PASS |
| test_heartbeat_payload() passes | ✅ Complete | 7 payload tests PASS |
| 4+ tests total | ✅ Exceeded | 23 tests (575% of requirement) |

**All JIRA requirements met + significant additional coverage.**

---

## Files

**Existing (created in OPTERP-24):**
- `tests/unit/test_heartbeat.py` (345 lines, 23 tests)
- `kkt_adapter/app/heartbeat.py` (333 lines, implementation)
- `tests/logs/unit/20251009_OPTERP-24_heartbeat_tests.log` (test results)

**New:**
- `docs/task_plans/20251009_OPTERP-27_heartbeat_unit_tests.md` (this file)

---

## Timeline

- **Analysis:** 5 min ✅
- **Documentation:** 10 min ✅
- **Total:** 15 min

**No implementation needed** - tests already exist from OPTERP-24.

---

## Notes

**Why Tests Already Exist:**

OPTERP-24 (Implement Heartbeat Module) created comprehensive unit tests as part of the implementation. This is best practice: implementing a module WITH its unit tests in the same task.

**OPTERP-27 vs OPTERP-24:**
- OPTERP-24: "Implement Heartbeat Module" (implementation + tests)
- OPTERP-27: "Create Heartbeat Unit Tests" (tests only)

**Overlap:** Tests were created proactively in OPTERP-24 to ensure quality.

**Test Quality:**
- 23 tests (vs 4 required)
- 100% coverage of hysteresis logic
- Edge cases covered
- State management covered
- Payload validation covered

---

## Decision

**Mark OPTERP-27 as "Already Complete"** with reference to OPTERP-24.

Tests already exist with:
- ✅ 23 unit tests (vs 4+ required)
- ✅ 100% pass rate
- ✅ All JIRA requirements covered
- ✅ Significant additional coverage (hysteresis, payload, edge cases)

**No action required** - tests are production-ready.

---

## Related Tasks

- **OPTERP-24:** Implement Heartbeat Module (created tests)
- **OPTERP-25:** Integrate APScheduler for Heartbeat (marked as alternative)
- **OPTERP-26:** Create Mock Odoo Server (for integration testing)

---

## Summary

✅ **OPTERP-27 already complete** (implemented in OPTERP-24)
- File: tests/unit/test_heartbeat.py (345 lines)
- 23 unit tests (vs 4+ required)
- 100% pass rate
- All JIRA requirements covered + significant additional coverage
- No further action needed
