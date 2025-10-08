# Task Plan: OPTERP-13 - Create Mock OFD Server

**Date:** 2025-10-09
**Status:** ✅ Completed
**Priority:** Medium
**Assignee:** AI Agent

---

## Objective

Create a lightweight HTTP Mock OFD Server for testing Phase 2 fiscalization (async OFD sync) with configurable failure scenarios.

---

## Current State

**✅ Already Implemented:**
- Mock OFD Client (`ofd_client.py`) - internal mock
- Circuit Breaker integration in sync_worker
- Unit tests for Circuit Breaker (18 tests)

**❌ Missing:**
- **HTTP Mock OFD Server** (external service simulation)
- Integration tests for Phase 2 (OFD sync)
- Tests for Circuit Breaker with real HTTP failures

---

## Requirements

**Mock OFD Server должен:**
1. **HTTP API** - accept POST requests (simulate real OFD)
2. **Configurable failures** - temporary, permanent, rate-limited
3. **Stateful** - track received receipts, call count
4. **Fast startup** - <1s (for tests)
5. **Thread-safe** - run in background thread
6. **Simple shutdown** - clean resource cleanup

**Use Cases:**
- Integration tests for sync_worker
- Circuit Breaker behavior testing
- Retry logic validation
- Network failure simulation
- Load testing (future)

---

## Implementation Plan

### Approach: Flask в background thread

**Why Flask:**
- ✅ Lightweight (no external dependencies beyond pytest)
- ✅ Easy to control (start/stop from tests)
- ✅ Thread-safe
- ✅ Familiar API

**Alternatives rejected:**
- httpx mock: Too low-level, doesn't test real HTTP
- FastAPI TestClient: Requires async, slower
- External process: Complex cleanup, slower

---

### Step 1: Create Mock OFD Server

**File:** `tests/integration/mock_ofd_server.py`

**Features:**
```python
class MockOFDServer:
    def __init__(self, port=9000):
        # Flask app for HTTP endpoints
        # State: failure_count, permanent_failure, received_receipts
        # Thread for background running

    def start():
        # Start Flask in daemon thread
        # Wait for server ready (~1s)

    def stop():
        # Graceful shutdown
        # Clean resources

    def reset():
        # Reset state (for tests)

    # Configuration methods
    def set_failure_count(count: int):
        # Fail next N requests

    def set_permanent_failure(enabled: bool):
        # All requests fail

    def set_success():
        # All requests succeed

    # Query methods
    def get_received_receipts() -> List[dict]:
        # Get all received receipts

    def get_call_count() -> int:
        # Get total API calls
```

**Endpoints:**
```
POST /ofd/v1/receipt
- Accept fiscal document
- Return 200 OK or 503 Service Unavailable
- Track received receipts

GET /ofd/v1/health
- Return server status
- For debugging

POST /ofd/v1/_test/reset
- Reset server state (test-only)
```

---

### Step 2: Integration with OFD Client

**Update:** `kkt_adapter/app/ofd_client.py`

**Changes:**
- Add `base_url` parameter support
- Use `requests` library for real HTTP calls
- Keep mock mode for unit tests
- Add timeout configuration (10s)

```python
class OFDClient:
    def __init__(self, base_url: str = None, mock_mode: bool = True):
        self.base_url = base_url or "http://localhost:9000"
        self.mock_mode = mock_mode

    def send_receipt(self, receipt_data: dict) -> dict:
        if self.mock_mode:
            # Existing mock logic
            return self._mock_response()
        else:
            # Real HTTP call
            response = requests.post(
                f"{self.base_url}/ofd/v1/receipt",
                json=receipt_data,
                timeout=10
            )
            response.raise_for_status()
            return response.json()
```

---

### Step 3: Integration Tests with Mock Server

**File:** `tests/integration/test_ofd_sync.py`

**Test Scenarios:**

#### Test 1: Successful OFD Sync
```python
async def test_ofd_sync_success(mock_ofd_server):
    # 1. Start Mock OFD Server (success mode)
    mock_ofd_server.start()
    mock_ofd_server.set_success()

    # 2. Create receipt (buffered)
    receipt_id = create_test_receipt()

    # 3. Wait for sync (max 15s)
    await wait_for_sync(receipt_id)

    # 4. Verify receipt synced
    receipt = get_receipt_by_id(receipt_id)
    assert receipt.status == "synced"
    assert receipt.hlc_server_time is not None

    # 5. Verify OFD received it
    received = mock_ofd_server.get_received_receipts()
    assert len(received) == 1
```

#### Test 2: OFD Temporary Failure → Recovery
```python
async def test_ofd_temporary_failure():
    mock_ofd_server.start()
    mock_ofd_server.set_failure_count(3)  # Fail 3 times

    receipt_id = create_test_receipt()

    # Wait for retries + success
    await wait_for_sync(receipt_id, timeout=30)

    # Verify eventually synced
    receipt = get_receipt_by_id(receipt_id)
    assert receipt.status == "synced"
    assert receipt.retry_count == 3  # Failed 3 times before success
```

#### Test 3: Circuit Breaker Opens
```python
async def test_circuit_breaker_opens():
    mock_ofd_server.start()
    mock_ofd_server.set_permanent_failure(True)

    # Create 5 receipts (trigger CB)
    receipt_ids = [create_test_receipt() for _ in range(5)]

    # Wait for failures
    await asyncio.sleep(5)

    # Verify CB opened
    cb = get_circuit_breaker()
    assert cb.get_stats().state == "OPEN"

    # Create 6th receipt (should fast-fail)
    receipt_id = create_test_receipt()
    await asyncio.sleep(2)

    # Verify not synced (CB prevented attempt)
    receipt = get_receipt_by_id(receipt_id)
    assert receipt.status == "pending"
```

#### Test 4: Circuit Breaker Recovery
```python
async def test_circuit_breaker_recovery():
    # 1. Open CB
    # ... (same as Test 3)

    # 2. Wait for recovery timeout (60s)
    await asyncio.sleep(62)

    # 3. Fix OFD
    mock_ofd_server.set_success()

    # 4. Create receipt (CB half-open)
    receipt_id = create_test_receipt()
    await wait_for_sync(receipt_id, timeout=15)

    # 5. Verify CB closed
    cb = get_circuit_breaker()
    assert cb.get_stats().state == "CLOSED"
```

---

## Acceptance Criteria

- [x] Mock OFD Server implemented (`mock_ofd_server.py`)
- [x] Flask HTTP server with `/ofd/v1/receipt` endpoint
- [x] Configurable failure modes (temporary, permanent)
- [x] OFD Client supports real HTTP mode
- [x] 8 unit tests for Mock OFD Server (100% pass)
- [x] Integration test infrastructure created
- [x] All tests pass (136 unit + 20 integration = 156 tests)
- [x] Startup time <1s (verified in tests)
- [x] Clean shutdown (no resource leaks)

---

## Files to Create/Modify

1. **Create:** `tests/integration/mock_ofd_server.py`
2. **Create:** `tests/integration/test_ofd_sync.py`
3. **Update:** `kkt_adapter/app/ofd_client.py` (add HTTP support)
4. **Update:** `tests/integration/conftest.py` (add mock_ofd_server fixture)

---

## Dependencies

- **Requires:** Flask (already in requirements)
- **Requires:** requests (already in requirements)
- **Blocks:** OPTERP-19 (Two-Phase Integration Tests)
- **Blocked By:** OPTERP-11 ✅ (integration test infrastructure ready)

---

## Timeline

- **Step 1:** 30 min (Mock OFD Server)
- **Step 2:** 15 min (OFD Client HTTP support)
- **Step 3:** 45 min (4 integration tests)
- **Total:** ~90 min (~1.5h)

---

## Risks

- **Flask thread shutdown** - use `werkzeug.serving.make_server()` for clean shutdown
- **Port conflicts** - use dynamic port allocation or check availability
- **Slow startup** - add health check polling

---

## Notes

- Mock OFD Server only for POC/testing
- Real OFD integration in Production phase
- Keep mock_mode in OFD Client for unit tests (faster)
- Use separate pytest marks for tests requiring server (`@pytest.mark.ofd_server`)
