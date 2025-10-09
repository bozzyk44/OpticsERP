# Task Plan: OPTERP-26 - Create Mock Odoo Server for Heartbeat Testing

**Date:** 2025-10-09
**Status:** ✅ Complete
**Priority:** High
**Assignee:** AI Agent

---

## Objective

Create Mock Odoo Server for testing heartbeat integration without real Odoo instance.

---

## Requirements (from JIRA)

From `docs/jira/jira_import.csv`:
> - POST /api/v1/kkt/heartbeat returns 200 OK
> - Mock server runs independently

---

## Implementation

### Files Created

1. **tests/integration/mock_odoo_server.py** (285 lines)
   - Flask-based HTTP server in background thread
   - POST /api/v1/kkt/heartbeat endpoint
   - Configurable failure modes (success, temporary, permanent)
   - State tracking (received heartbeats, call counts)
   - Thread-safe operations

2. **tests/unit/test_mock_odoo_server.py** (400+ lines)
   - 19 unit tests (100% pass)
   - Coverage: lifecycle, heartbeat, state tracking, failure modes, thread safety

---

## Architecture

```
┌─────────────────────────────────────────┐
│  MockOdooServer (Flask + Thread)        │
│  ┌───────────────────────────────────┐  │
│  │ POST /api/v1/kkt/heartbeat        │  │
│  │  - Accept heartbeat payload       │  │
│  │  - Return 200 OK / 503 Error      │  │
│  │  - Track received payloads        │  │
│  └───────────────────────────────────┘  │
│  ┌───────────────────────────────────┐  │
│  │ GET /health                       │  │
│  │  - Return 200 OK (health check)   │  │
│  └───────────────────────────────────┘  │
│                                         │
│  Configuration:                         │
│  - set_success()                        │
│  - set_failure_count(N)                 │
│  - set_permanent_failure(bool)          │
│                                         │
│  State:                                 │
│  - get_received_heartbeats()            │
│  - get_call_count()                     │
│  - reset()                              │
└─────────────────────────────────────────┘
```

---

## Key Features

### 1. Configurable Failure Modes

**Success Mode:**
```python
server.set_success()
# All heartbeats return 200 OK
```

**Temporary Failure:**
```python
server.set_failure_count(3)
# Next 3 heartbeats fail with 503
# Then revert to success mode
```

**Permanent Failure:**
```python
server.set_permanent_failure(True)
# All heartbeats fail with 503 until disabled
```

### 2. State Tracking

**Received Heartbeats:**
```python
heartbeats = server.get_received_heartbeats()
# Returns list of all successful heartbeat payloads
# Only successful heartbeats are stored
```

**Call Count:**
```python
count = server.get_call_count()
# Returns total number of heartbeat calls (success + failure)
```

**Reset:**
```python
server.reset()
# Clear all state:
# - Received heartbeats
# - Call count
# - Failure modes
```

### 3. Thread-Safe Operations

- All state access protected with `threading.Lock`
- Safe for concurrent heartbeat calls
- Background thread execution

### 4. Context Manager Support

```python
with MockOdooServer(port=8069) as server:
    # Server started
    response = requests.post("http://localhost:8069/api/v1/kkt/heartbeat", json=data)
# Server stopped automatically
```

---

## API Endpoints

### POST /api/v1/kkt/heartbeat

**Request:**
```json
{
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
```

**Response (Success):**
```json
{
  "status": "ok",
  "message": "Heartbeat received"
}
```
**Status:** 200 OK

**Response (Failure):**
```json
{
  "error": "Odoo service unavailable"
}
```
**Status:** 503 Service Unavailable

### GET /health

**Response:**
```json
{
  "status": "ok"
}
```
**Status:** 200 OK

---

## Testing

### Unit Tests (19 tests, 100% pass)

**Test Coverage:**
1. **Server Lifecycle (5 tests)**
   - Creation
   - Startup
   - Shutdown
   - Context manager
   - Double start protection

2. **Heartbeat Endpoint (4 tests)**
   - Success mode (200 OK)
   - Permanent failure (503)
   - Temporary failure (N failures → success)
   - Payload storage

3. **State Tracking (4 tests)**
   - Call count increments
   - Call count on failures
   - Received heartbeats only on success
   - Reset clears state

4. **Failure Modes (3 tests)**
   - set_success clears failures
   - Permanent failure overrides count
   - Disable permanent failure

5. **Thread Safety (1 test)**
   - Concurrent heartbeats (10 threads)

6. **Edge Cases (2 tests)**
   - Empty payload
   - Large payload (10KB)

**Test Results:**
```
============================= test session starts =============================
tests/unit/test_mock_odoo_server.py::TestMockOdooServerBasic::test_server_creation PASSED
tests/unit/test_mock_odoo_server.py::TestMockOdooServerBasic::test_server_startup PASSED
tests/unit/test_mock_odoo_server.py::TestMockOdooServerBasic::test_server_shutdown PASSED
tests/unit/test_mock_odoo_server.py::TestMockOdooServerBasic::test_server_context_manager PASSED
tests/unit/test_mock_odoo_server.py::TestMockOdooServerBasic::test_server_double_start_raises PASSED
tests/unit/test_mock_odoo_server.py::TestHeartbeatEndpoint::test_heartbeat_success_mode PASSED
tests/unit/test_mock_odoo_server.py::TestHeartbeatEndpoint::test_heartbeat_permanent_failure PASSED
tests/unit/test_mock_odoo_server.py::TestHeartbeatEndpoint::test_heartbeat_temporary_failure PASSED
tests/unit/test_mock_odoo_server.py::TestHeartbeatEndpoint::test_heartbeat_stores_payload PASSED
tests/unit/test_mock_odoo_server.py::TestStateTracking::test_call_count_increments PASSED
tests/unit/test_mock_odoo_server.py::TestStateTracking::test_call_count_increments_on_failure PASSED
tests/unit/test_mock_odoo_server.py::TestStateTracking::test_received_heartbeats_only_on_success PASSED
tests/unit/test_mock_odoo_server.py::TestStateTracking::test_reset_clears_state PASSED
tests/unit/test_mock_odoo_server.py::TestFailureModes::test_set_success_clears_failures PASSED
tests/unit/test_mock_odoo_server.py::TestFailureModes::test_permanent_failure_overrides_count PASSED
tests/unit/test_mock_odoo_server.py::TestFailureModes::test_disable_permanent_failure PASSED
tests/unit/test_mock_odoo_server.py::TestThreadSafety::test_concurrent_heartbeats PASSED
tests/unit/test_mock_odoo_server.py::TestEdgeCases::test_empty_heartbeat_payload PASSED
tests/unit/test_mock_odoo_server.py::TestEdgeCases::test_large_heartbeat_payload PASSED

============================= 19 passed in 22.03s =============================
```

---

## Usage Example

```python
import requests
from tests.integration.mock_odoo_server import MockOdooServer

# Start server
server = MockOdooServer(port=8069)
server.start()

try:
    # Set success mode
    server.set_success()

    # Send heartbeat
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

    print(f"Response: {response.status_code} - {response.json()}")
    print(f"Received heartbeats: {len(server.get_received_heartbeats())}")
    print(f"Call count: {server.get_call_count()}")

finally:
    server.stop()
```

**Output:**
```
Response: 200 - {'status': 'ok', 'message': 'Heartbeat received'}
Received heartbeats: 1
Call count: 1
```

---

## Integration with Heartbeat Module

Mock Odoo Server is designed for testing heartbeat.py:

**Test Scenario 1: Heartbeat Success**
```python
# Setup
server = MockOdooServer(port=8069)
server.start()
server.set_success()

# Test heartbeat
from kkt_adapter.app.heartbeat import send_heartbeat

success = await send_heartbeat()  # Returns True
assert success

# Verify
assert server.get_call_count() == 1
heartbeats = server.get_received_heartbeats()
assert heartbeats[0]["adapter_id"] == "KKT-001"
```

**Test Scenario 2: Heartbeat Failure → Recovery**
```python
# Setup
server.set_failure_count(2)  # Fail twice

# Test failures
success1 = await send_heartbeat()  # Returns False
success2 = await send_heartbeat()  # Returns False

# Recovery
success3 = await send_heartbeat()  # Returns True

# Verify hysteresis state transitions
assert server.get_call_count() == 3
assert len(server.get_received_heartbeats()) == 1  # Only 1 success
```

**Test Scenario 3: Permanent Failure (OFD Down)**
```python
# Setup
server.set_permanent_failure(True)

# Test heartbeats
for i in range(5):
    success = await send_heartbeat()
    assert not success  # All fail

# Verify
assert server.get_call_count() == 5
assert len(server.get_received_heartbeats()) == 0  # No successes
```

---

## Comparison with Mock OFD Server

| Feature | Mock OFD Server | Mock Odoo Server |
|---------|----------------|------------------|
| **Purpose** | Test OFD sync | Test heartbeat |
| **Endpoint** | POST /api/v2/receipt | POST /api/v1/kkt/heartbeat |
| **Port** | 8080 | 8069 |
| **Success Response** | `{"receipt_id": "..."}` | `{"status": "ok"}` |
| **Failure Modes** | ✅ Temporary, Permanent | ✅ Temporary, Permanent |
| **State Tracking** | ✅ Received receipts, call count | ✅ Received heartbeats, call count |
| **Thread Safety** | ✅ Lock-based | ✅ Lock-based |
| **Context Manager** | ✅ Yes | ✅ Yes |
| **Tests** | 16 tests | 19 tests |

**Pattern Consistency:** Both mock servers follow same design pattern for testability.

---

## Files

**Created:**
- `tests/integration/mock_odoo_server.py` (285 lines)
- `tests/unit/test_mock_odoo_server.py` (400+ lines, 19 tests)
- `docs/task_plans/20251009_OPTERP-26_mock_odoo_server.md` (this file)

**No changes needed:**
- Heartbeat module already sends to correct endpoint
- Tests can now use Mock Odoo Server instead of real Odoo

---

## Acceptance Criteria

| Requirement | Status | Evidence |
|-------------|--------|----------|
| POST /api/v1/kkt/heartbeat returns 200 OK | ✅ Complete | test_heartbeat_success_mode PASS |
| Mock server runs independently | ✅ Complete | Background thread, test_server_startup PASS |
| Configurable failure modes | ✅ Bonus | Temporary + permanent failure modes |
| State tracking | ✅ Bonus | Received heartbeats, call count |
| Thread safety | ✅ Bonus | test_concurrent_heartbeats PASS |
| Unit tests | ✅ Complete | 19 tests (100% pass) |

**All JIRA requirements met + bonus features.**

---

## Timeline

- **Analysis:** 5 min ✅
- **Implementation:** 20 min ✅
- **Testing:** 15 min ✅
- **Documentation:** 10 min ✅
- **Total:** 50 min

---

## Notes

**Why Flask?**
- Lightweight HTTP server (same as Mock OFD Server)
- Fast startup (<1s)
- No external dependencies (Flask already in requirements.txt)
- Perfect for testing

**Why Thread?**
- Non-blocking (server runs in background)
- Tests can make HTTP requests from main thread
- Clean shutdown with context manager

**Why Lock?**
- Thread-safe state access
- Prevents race conditions in concurrent tests
- Same pattern as Mock OFD Server

---

## Next Steps

Mock Odoo Server is ready for use in:
1. **Integration tests** (heartbeat.py with mock Odoo)
2. **POC-5 testing** (heartbeat monitoring)
3. **Local development** (no real Odoo needed)

**No action required** - Mock Odoo Server is complete and tested.

---

## Related Tasks

- **OPTERP-13:** Create Mock OFD Server (similar pattern)
- **OPTERP-24:** Implement Heartbeat Module (consumer of Mock Odoo Server)
- **OPTERP-25:** APScheduler for Heartbeat (marked as alternative implementation)

---

## Summary

✅ **Mock Odoo Server complete**
- Flask-based HTTP server
- POST /api/v1/kkt/heartbeat endpoint
- Configurable failure modes
- State tracking
- 19 unit tests (100% pass)
- Ready for heartbeat integration testing
