# OPTERP-7: FastAPI Unit Tests

**Task:** Write comprehensive unit tests for FastAPI KKT Adapter endpoints

**Story Points:** 3
**Sprint:** Phase 1 - POC (Week 1)
**Status:** In Progress
**Created:** 2025-10-08
**Assignee:** AI Agent

---

## 📋 Task Description

Create comprehensive unit tests for all FastAPI endpoints implemented in OPTERP-6. Tests should cover positive cases, negative cases, edge cases, validation, and error handling.

**References:**
- CLAUDE.md §5.1 (POC Week 1 testing)
- OPTERP-6: FastAPI Main Application (completed)
- docs/task_plans/20251008_OPTERP-6_fastapi_main_application.md

---

## 🎯 Acceptance Criteria

- [ ] **AC1:** Unit tests for POST /v1/kkt/receipt endpoint (≥8 tests)
- [ ] **AC2:** Unit tests for GET /v1/kkt/buffer/status endpoint (≥3 tests)
- [ ] **AC3:** Unit tests for GET /v1/health endpoint (≥3 tests)
- [ ] **AC4:** Unit tests for root endpoint GET / (≥1 test)
- [ ] **AC5:** Tests for Pydantic validation (≥5 tests)
- [ ] **AC6:** Tests for error handling (≥4 tests)
- [ ] **AC7:** Tests for idempotency (≥2 tests)
- [ ] **AC8:** Test coverage ≥90%
- [ ] **AC9:** All tests pass
- [ ] **AC10:** Test logs saved to tests/logs/unit/

---

## 📐 Implementation Plan

### Step 1: Create test file structure (10 min)

**File:** `tests/unit/test_fastapi_endpoints.py`

**Structure:**
```python
"""
Unit Tests for FastAPI KKT Adapter Endpoints

Author: AI Agent
Created: 2025-10-08
Purpose: Comprehensive unit tests for all FastAPI endpoints

Test Coverage:
- POST /v1/kkt/receipt - Receipt creation with two-phase fiscalization
- GET /v1/kkt/buffer/status - Buffer status and metrics
- GET /v1/health - Health check and component status
- GET / - Root endpoint
- Pydantic validation
- Error handling
- Idempotency
"""

import pytest
import sys
from pathlib import Path
from httpx import AsyncClient

# Add kkt_adapter/app to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'kkt_adapter' / 'app'))

from main import app
from buffer import init_buffer_db, close_buffer_db
```

### Step 2: Create fixtures (15 min)

**Fixtures needed:**
```python
@pytest.fixture(scope="function")
async def client():
    """HTTP client for FastAPI testing"""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac

@pytest.fixture(scope="function")
def clean_database():
    """Initialize clean in-memory database for each test"""
    # Initialize in-memory database
    init_buffer_db(':memory:')
    yield
    close_buffer_db()

@pytest.fixture
def valid_receipt_data():
    """Valid receipt data for testing"""
    return {
        "pos_id": "POS-001",
        "type": "sale",
        "items": [
            {
                "name": "Product A",
                "price": 100.00,
                "quantity": 2,
                "total": 200.00,
                "vat_rate": 20
            }
        ],
        "payments": [
            {
                "type": "cash",
                "amount": 200.00
            }
        ]
    }
```

### Step 3: Tests for POST /v1/kkt/receipt (30 min)

**Test cases:**
```python
class TestCreateReceipt:
    """Tests for POST /v1/kkt/receipt endpoint"""

    async def test_create_receipt_success(self, client, clean_database, valid_receipt_data):
        """Test successful receipt creation"""
        response = await client.post(
            "/v1/kkt/receipt",
            json=valid_receipt_data,
            headers={"Idempotency-Key": "test-key-001"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "buffered"
        assert "receipt_id" in data
        assert data["fiscal_doc"] is None

    async def test_create_receipt_missing_idempotency_key(self, client, valid_receipt_data):
        """Test receipt creation without Idempotency-Key header"""
        response = await client.post("/v1/kkt/receipt", json=valid_receipt_data)
        assert response.status_code == 422  # Validation error

    async def test_create_receipt_invalid_type(self, client, valid_receipt_data):
        """Test receipt creation with invalid type"""
        valid_receipt_data["type"] = "invalid_type"
        response = await client.post(
            "/v1/kkt/receipt",
            json=valid_receipt_data,
            headers={"Idempotency-Key": "test-key-002"}
        )
        assert response.status_code == 422

    async def test_create_receipt_empty_items(self, client, valid_receipt_data):
        """Test receipt creation with empty items list"""
        valid_receipt_data["items"] = []
        response = await client.post(
            "/v1/kkt/receipt",
            json=valid_receipt_data,
            headers={"Idempotency-Key": "test-key-003"}
        )
        assert response.status_code == 422

    async def test_create_receipt_invalid_total(self, client, valid_receipt_data):
        """Test receipt creation with mismatched item total"""
        valid_receipt_data["items"][0]["total"] = 999.99  # Should be 200.00
        response = await client.post(
            "/v1/kkt/receipt",
            json=valid_receipt_data,
            headers={"Idempotency-Key": "test-key-004"}
        )
        assert response.status_code == 422

    async def test_create_receipt_payment_mismatch(self, client, valid_receipt_data):
        """Test receipt creation with payments not matching items total"""
        valid_receipt_data["payments"][0]["amount"] = 100.00  # Should be 200.00
        response = await client.post(
            "/v1/kkt/receipt",
            json=valid_receipt_data,
            headers={"Idempotency-Key": "test-key-005"}
        )
        assert response.status_code == 422

    async def test_create_receipt_negative_price(self, client, valid_receipt_data):
        """Test receipt creation with negative price"""
        valid_receipt_data["items"][0]["price"] = -100.00
        response = await client.post(
            "/v1/kkt/receipt",
            json=valid_receipt_data,
            headers={"Idempotency-Key": "test-key-006"}
        )
        assert response.status_code == 422

    async def test_create_receipt_multiple_payments(self, client, valid_receipt_data):
        """Test receipt creation with multiple payment methods"""
        valid_receipt_data["payments"] = [
            {"type": "cash", "amount": 100.00},
            {"type": "card", "amount": 100.00}
        ]
        response = await client.post(
            "/v1/kkt/receipt",
            json=valid_receipt_data,
            headers={"Idempotency-Key": "test-key-007"}
        )
        assert response.status_code == 200
```

### Step 4: Tests for GET /v1/kkt/buffer/status (15 min)

**Test cases:**
```python
class TestBufferStatus:
    """Tests for GET /v1/kkt/buffer/status endpoint"""

    async def test_buffer_status_empty(self, client, clean_database):
        """Test buffer status with empty buffer"""
        response = await client.get("/v1/kkt/buffer/status")
        assert response.status_code == 200
        data = response.json()
        assert data["total_capacity"] == 200
        assert data["current_queued"] == 0
        assert data["percent_full"] == 0.0
        assert data["pending"] == 0
        assert data["synced"] == 0
        assert data["failed"] == 0

    async def test_buffer_status_with_receipts(self, client, clean_database, valid_receipt_data):
        """Test buffer status after adding receipts"""
        # Add receipt
        await client.post(
            "/v1/kkt/receipt",
            json=valid_receipt_data,
            headers={"Idempotency-Key": "test-key-100"}
        )

        # Check status
        response = await client.get("/v1/kkt/buffer/status")
        assert response.status_code == 200
        data = response.json()
        assert data["current_queued"] == 1
        assert data["pending"] == 1
        assert data["percent_full"] > 0

    async def test_buffer_status_network_detection(self, client, clean_database):
        """Test network status detection in buffer status"""
        response = await client.get("/v1/kkt/buffer/status")
        assert response.status_code == 200
        data = response.json()
        assert "network_status" in data
        assert data["network_status"] in ["online", "offline", "degraded"]
```

### Step 5: Tests for GET /v1/health (15 min)

**Test cases:**
```python
class TestHealthCheck:
    """Tests for GET /v1/health endpoint"""

    async def test_health_check_healthy(self, client, clean_database):
        """Test health check when system is healthy"""
        response = await client.get("/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "components" in data
        assert "buffer" in data["components"]
        assert "circuit_breaker" in data["components"]
        assert "database" in data["components"]

    async def test_health_check_components(self, client, clean_database):
        """Test health check component details"""
        response = await client.get("/v1/health")
        data = response.json()

        buffer = data["components"]["buffer"]
        assert buffer["status"] == "healthy"
        assert "percent_full" in buffer
        assert "dlq_size" in buffer

    async def test_health_check_version(self, client):
        """Test health check includes version"""
        response = await client.get("/v1/health")
        data = response.json()
        assert data["version"] == "0.1.0"
```

### Step 6: Tests for root endpoint (5 min)

**Test case:**
```python
class TestRootEndpoint:
    """Tests for GET / root endpoint"""

    async def test_root_endpoint(self, client):
        """Test root endpoint returns API information"""
        response = await client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "KKT Adapter API"
        assert data["version"] == "0.1.0"
        assert data["docs"] == "/docs"
        assert data["health"] == "/v1/health"
```

### Step 7: Tests for idempotency (15 min)

**Test cases:**
```python
class TestIdempotency:
    """Tests for idempotency handling"""

    async def test_idempotency_duplicate_key(self, client, clean_database, valid_receipt_data):
        """Test that duplicate idempotency keys are handled"""
        # Create receipt
        response1 = await client.post(
            "/v1/kkt/receipt",
            json=valid_receipt_data,
            headers={"Idempotency-Key": "test-key-idempotent"}
        )
        assert response1.status_code == 200
        receipt_id_1 = response1.json()["receipt_id"]

        # Try to create again with same idempotency key
        # Note: Current implementation doesn't enforce idempotency at API level,
        # only at buffer level. This test documents expected future behavior.
        response2 = await client.post(
            "/v1/kkt/receipt",
            json=valid_receipt_data,
            headers={"Idempotency-Key": "test-key-idempotent"}
        )
        assert response2.status_code == 200
        receipt_id_2 = response2.json()["receipt_id"]

        # Currently creates new receipt (future: should return same receipt_id)
        # This test documents current behavior
        assert receipt_id_1 != receipt_id_2  # Will change when idempotency is enforced

    async def test_idempotency_different_keys(self, client, clean_database, valid_receipt_data):
        """Test that different idempotency keys create different receipts"""
        response1 = await client.post(
            "/v1/kkt/receipt",
            json=valid_receipt_data,
            headers={"Idempotency-Key": "key-1"}
        )
        response2 = await client.post(
            "/v1/kkt/receipt",
            json=valid_receipt_data,
            headers={"Idempotency-Key": "key-2"}
        )
        assert response1.status_code == 200
        assert response2.status_code == 200
        assert response1.json()["receipt_id"] != response2.json()["receipt_id"]
```

### Step 8: Run tests and check coverage (15 min)

```bash
# Install test dependencies
pip install pytest pytest-asyncio httpx pytest-cov

# Run tests with coverage
pytest tests/unit/test_fastapi_endpoints.py -v --cov=kkt_adapter/app --cov-report=term --cov-report=html

# Save test log
pytest tests/unit/test_fastapi_endpoints.py -v --tb=short 2>&1 | tee tests/logs/unit/20251008_OPTERP-7_fastapi_unit_tests.log
```

### Step 9: Fix any failing tests (variable time)

- Analyze failures
- Fix issues in implementation or tests
- Re-run tests until all pass

### Step 10: Commit and push (10 min)

```bash
git add tests/unit/test_fastapi_endpoints.py
git add tests/logs/unit/20251008_OPTERP-7_fastapi_unit_tests.log
git commit -m "test(fastapi): add comprehensive unit tests for all endpoints [OPTERP-7]"
git push origin feature/phase1-poc
```

---

## 🧪 Testing Strategy

**Test Pyramid:**
- Unit tests (this task): 26 tests covering all endpoints
- Integration tests (future): End-to-end scenarios
- Smoke tests (completed): Manual verification

**Coverage Goals:**
- Endpoints: 100%
- Business logic: ≥90%
- Error handling: 100%
- Validation: 100%

**Test Organization:**
```
tests/unit/test_fastapi_endpoints.py
├── TestCreateReceipt (8 tests)
│   ├── test_create_receipt_success
│   ├── test_create_receipt_missing_idempotency_key
│   ├── test_create_receipt_invalid_type
│   ├── test_create_receipt_empty_items
│   ├── test_create_receipt_invalid_total
│   ├── test_create_receipt_payment_mismatch
│   ├── test_create_receipt_negative_price
│   └── test_create_receipt_multiple_payments
├── TestBufferStatus (3 tests)
│   ├── test_buffer_status_empty
│   ├── test_buffer_status_with_receipts
│   └── test_buffer_status_network_detection
├── TestHealthCheck (3 tests)
│   ├── test_health_check_healthy
│   ├── test_health_check_components
│   └── test_health_check_version
├── TestRootEndpoint (1 test)
│   └── test_root_endpoint
└── TestIdempotency (2 tests)
    ├── test_idempotency_duplicate_key
    └── test_idempotency_different_keys

Total: 17 tests (≥90% coverage target)
```

---

## 📦 Deliverables

- [ ] `tests/unit/test_fastapi_endpoints.py` (≈450 lines)
- [ ] Test log: `tests/logs/unit/20251008_OPTERP-7_fastapi_unit_tests.log`
- [ ] Coverage report (HTML)
- [ ] All 17+ tests passing
- [ ] Coverage ≥90%
- [ ] Code committed to `feature/phase1-poc` branch
- [ ] Changes pushed to remote

---

## ⏱️ Time Estimate

| Step | Task | Time |
|------|------|------|
| 1 | Create test file structure | 10 min |
| 2 | Create fixtures | 15 min |
| 3 | Tests for POST /v1/kkt/receipt | 30 min |
| 4 | Tests for GET /v1/kkt/buffer/status | 15 min |
| 5 | Tests for GET /v1/health | 15 min |
| 6 | Tests for root endpoint | 5 min |
| 7 | Tests for idempotency | 15 min |
| 8 | Run tests and check coverage | 15 min |
| 9 | Fix any failing tests | 30 min |
| 10 | Commit and push | 10 min |
| **TOTAL** | **2h 40min** |

---

## 🔗 Dependencies

**Requires:**
- ✅ OPTERP-6: FastAPI Main Application (completed)
- ✅ OPTERP-4: SQLite Buffer CRUD (completed)
- ✅ OPTERP-5: Buffer Unit Tests (completed)

**Blocks:**
- OPTERP-8: Circuit Breaker Implementation

---

## 📝 Notes

### Test Dependencies

New dependencies for testing:
```txt
pytest-asyncio==0.21.1  # Async test support
httpx==0.25.2           # Async HTTP client for FastAPI testing
```

Already installed:
- pytest (from OPTERP-5)
- pytest-cov (from OPTERP-5)

### Known Limitations

1. **Idempotency not enforced:** Current implementation doesn't prevent duplicate receipts with same Idempotency-Key. Tests document current behavior, will need update when feature is implemented.

2. **No mocking:** Tests use real SQLite in-memory database instead of mocking. This is intentional for integration testing.

3. **No async context manager tests:** Current tests don't verify database connection cleanup. This is covered by buffer unit tests (OPTERP-5).

### Future Enhancements

- Add tests for buffer capacity overflow (503 error)
- Add tests for concurrent requests
- Add tests for malformed JSON
- Add tests for SQL injection attempts
- Add performance tests (P95 < 7s)

---

## ✅ Definition of Done

- [ ] All 10 implementation steps completed
- [ ] 17+ tests written and passing
- [ ] Coverage ≥90% achieved
- [ ] Test log saved to tests/logs/unit/
- [ ] No failing tests
- [ ] No linter errors
- [ ] Code committed with message: `test(fastapi): add comprehensive unit tests for all endpoints [OPTERP-7]`
- [ ] Pushed to remote

---

## 🚀 Ready to Implement

This task plan is complete and ready for execution. Proceed with Step 1.
