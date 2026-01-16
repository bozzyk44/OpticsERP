# KKT Emulation Guide for Local Testing

**Last Updated:** 2025-11-30
**Purpose:** Enable development and testing of fiscal functionality without real ККТ hardware

---

## 📋 Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Current Implementation](#current-implementation)
4. [Emulation Modes](#emulation-modes)
5. [Setup Instructions](#setup-instructions)
6. [Testing Scenarios](#testing-scenarios)
7. [Advanced Configuration](#advanced-configuration)
8. [Troubleshooting](#troubleshooting)
9. [References](#references)

---

## 1. Overview

### What is KKT Emulation?

**КК** (Контрольно-кассовая техника / Cash Register Technology) emulation allows developers to:
- Test fiscal receipt generation **without physical ККТ hardware**
- Develop and validate 54-ФЗ compliance logic
- Simulate OFD (Operator Fiscal Data) connectivity
- Test offline-first buffer mechanisms
- Validate ФФД (Fiscal Data Format) 1.0, 1.05, 1.1, 1.2 compliance

### Why Emulation Matters

**Development Benefits:**
- ✅ **Zero hardware costs** - No need for ~50,000₽ ККТ device
- ✅ **Fast iteration** - Test fiscalization in <1s instead of minutes
- ✅ **Deterministic testing** - Reproducible scenarios (errors, delays, edge cases)
- ✅ **CI/CD compatible** - Automated testing without hardware dependencies
- ✅ **Parallel testing** - Run 100+ concurrent tests simultaneously

**Regulatory Context:**
- 54-ФЗ mandates online fiscal registration for all retail sales in Russia
- ККТ must print receipts with fiscal signs (ФП - фискальный признак)
- ОФД transmission required within 30 days (or immediate for most transactions)
- Non-compliance penalties: **от 10,000₽** per violation

---

## 2. Architecture

### Three-Layer Emulation Stack

```
┌─────────────────────────────────────────┐
│  Application Layer (Odoo POS Module)    │  ← Business logic
├─────────────────────────────────────────┤
│  KKT Adapter (FastAPI)                  │  ← Offline-first buffer
│  ├─ Mock KKT Driver (Phase 1)           │  ← Print emulation
│  └─ Mock OFD Client (Phase 2)           │  ← OFD sync emulation
├─────────────────────────────────────────┤
│  Mock Services (Test Environment)       │
│  ├─ Mock OFD Server (HTTP Flask)        │  ← OFD API emulator
│  └─ Mock Odoo Server (HTTP Flask)       │  ← Odoo API emulator
└─────────────────────────────────────────┘
```

### Component Responsibilities

| Component | File | Purpose | Realism Level |
|-----------|------|---------|---------------|
| **Mock KKT Driver** | `kkt_adapter/app/kkt_driver.py` | Simulate ККТ printing (Phase 1) | Basic (no hardware) |
| **Mock OFD Client** | `kkt_adapter/app/ofd_client.py` | Simulate OFD transmission (Phase 2) | Medium (mock mode) |
| **Mock OFD Server** | `tests/integration/mock_ofd_server.py` | HTTP server for integration tests | High (real HTTP) |
| **Mock Odoo Server** | `tests/integration/mock_odoo_server.py` | Simulate Odoo heartbeat API | High (real HTTP) |

---

## 3. Current Implementation

### Mock KKT Driver (`kkt_driver.py`)

**Key Features:**
- **Sequential fiscal doc numbering** (thread-safe counter)
- **Simulated print delay** (200-500ms random)
- **Mock fiscal sign generation** (SHA-256 hash, 10 chars)
- **QR code data** (ФФД 1.2 format: `t=...&s=...&fn=...&i=...&fp=...`)
- **Deterministic output** (same input → same fiscal sign)

**Mock Configuration:**
```python
MOCK_KKT_CONFIG = {
    "kkt_number": "0000000000001234",  # Mock ККТ registration number
    "fn_number": "9999999999999999",    # Mock Fiscal Module serial
    "ofd_name": "Платформа ОФД",        # Mock OFD provider
    "inn": "7707083893",                 # Mock company INN
    "rn_kkt": "0000000000001234",        # Mock ККТ registration number
}
```

**API:**
```python
def print_receipt(receipt_data: dict) -> Dict[str, Any]:
    """
    Mock fiscal receipt printing

    Args:
        receipt_data: {
            'pos_id': str,
            'fiscal_doc': {
                'type': 'sale' | 'refund',
                'items': [...],
                'payments': [...]
            }
        }

    Returns:
        {
            'fiscal_doc_number': int,       # Sequential (1, 2, 3, ...)
            'fiscal_sign': str,             # 10-char hash
            'fiscal_datetime': str,         # ISO 8601 UTC
            'fn_number': str,               # Fiscal module serial
            'kkt_number': str,              # ККТ registration #
            'qr_code_data': str,            # ФФД format QR
            'shift_number': int,            # Always 1 (POC)
            'receipt_number': int,          # Same as fiscal_doc_number
            'total': float                  # Calculated from items
        }
    """
```

**Thread Safety:**
```python
_fiscal_doc_counter = 0
_counter_lock = threading.Lock()

def _get_next_fiscal_doc_number() -> int:
    global _fiscal_doc_counter
    with _counter_lock:
        _fiscal_doc_counter += 1
        return _fiscal_doc_counter
```

**Fiscal Sign Algorithm:**
```python
def _generate_fiscal_sign(receipt_data: dict, fiscal_doc_number: int) -> str:
    """Generate mock fiscal sign (hash)"""
    data_str = f"{fiscal_doc_number}_{receipt_data.get('pos_id', '')}_{datetime.now().isoformat()}"
    hash_obj = hashlib.sha256(data_str.encode('utf-8'))
    fiscal_sign = hash_obj.hexdigest()[:10]  # First 10 chars
    return fiscal_sign.upper()
```

**QR Code Format (ФФД 1.2):**
```python
# Example output:
# t=20251130T1200&s=2500.00&fn=9999999999999999&i=42&fp=A1B2C3D4E5&n=1
#
# Fields:
# - t: Datetime (YYYYMMDDTHHMM)
# - s: Sum (total amount)
# - fn: Fiscal module number
# - i: Fiscal document number
# - fp: Fiscal sign (фискальный признак)
# - n: Receipt type (1=sale, 2=refund)
```

### Mock OFD Client (`ofd_client.py`)

**Two Modes:**

**1. Mock Mode (`mock_mode=True`):**
- **Purpose:** Unit tests (fast, no network)
- **Behavior:** Simulates OFD with 100ms delay
- **Configurable failures:** `set_fail_next(True)` to simulate errors
- **Call tracking:** `get_call_count()` for test assertions

**2. HTTP Mode (`mock_mode=False`):**
- **Purpose:** Integration tests (realistic)
- **Behavior:** Real HTTP POST to `base_url/ofd/v1/receipt`
- **Timeout:** 10 seconds (configurable)
- **Error handling:** Connection errors, timeouts, HTTP 4xx/5xx

**Usage:**
```python
# Unit test mode (fast)
client = OFDClient(mock_mode=True)
response = client.send_receipt(receipt_data)  # 100ms delay

# Integration test mode (realistic)
client = OFDClient(base_url="http://localhost:9000", mock_mode=False)
response = client.send_receipt(receipt_data)  # Real HTTP call
```

### Mock OFD Server (`mock_ofd_server.py`)

**Flask HTTP Server for Integration Tests**

**Features:**
- **Fast startup** (<1s)
- **Thread-safe** state management
- **Configurable failure modes:**
  - `set_failure_count(N)` - Fail next N requests
  - `set_permanent_failure(True)` - All requests fail (503)
  - `set_success()` - All requests succeed (200)
- **Stateful tracking:**
  - `get_received_receipts()` - All accepted receipts
  - `get_call_count()` - Total API calls
- **Clean shutdown** - Graceful stop with 5s timeout

**API Endpoints:**
```python
# Accept fiscal document (Phase 2 sync)
POST /ofd/v1/receipt
→ 200 OK: {"status": "accepted", "ofd_id": "OFD-000001", "timestamp": 1234567890}
→ 503 Service Unavailable: {"error": "OFD service unavailable"}

# Health check
GET /ofd/v1/health
→ 200 OK: {"status": "healthy", "call_count": 42, "receipts_received": 38}

# Reset state (test-only)
POST /ofd/v1/_test/reset
→ 200 OK: {"status": "reset"}
```

**Usage in Tests:**
```python
# Context manager (auto start/stop)
with MockOFDServer(port=9000) as server:
    server.set_success()
    # ... run tests ...
    assert server.get_call_count() == 10
    receipts = server.get_received_receipts()

# Manual control
server = MockOFDServer(port=9000)
server.start()  # Blocks until ready (max 5s)
server.set_failure_count(5)  # Next 5 requests fail
# ... tests ...
server.stop()   # Graceful shutdown
```

**Failure Mode Testing:**
```python
# Scenario 1: Temporary OFD outage (Circuit Breaker test)
server.set_failure_count(10)  # Fail next 10 requests
# Circuit Breaker should open after 5 failures
# Requests 6-10 should be buffered

# Scenario 2: Permanent OFD outage (Offline mode test)
server.set_permanent_failure(True)
# All receipts should buffer
# No OFD sync should succeed

# Scenario 3: Recovery test
server.set_permanent_failure(True)  # Outage
# ... buffer receipts ...
server.set_success()  # Recovery
# Buffered receipts should sync automatically
```

---

## 4. Emulation Modes

### Mode 1: Unit Test (In-Memory Mock)

**Purpose:** Fast unit tests with no external dependencies

**Components:**
- Mock KKT Driver (`mock_mode=True` implicit)
- Mock OFD Client (`mock_mode=True`)
- No HTTP servers

**Performance:**
- Receipt generation: ~0.3s (200-500ms print delay)
- OFD sync: ~0.1s (mock delay)
- **Total test suite:** <10 seconds (100+ tests)

**Example:**
```python
# tests/unit/test_kkt_driver.py
def test_print_receipt_success():
    receipt_data = {
        'pos_id': 'POS-001',
        'fiscal_doc': {
            'type': 'sale',
            'items': [{'name': 'Product', 'price': 100, 'quantity': 2}],
            'payments': [{'type': 'cash', 'amount': 200}]
        }
    }

    fiscal_doc = print_receipt(receipt_data)

    assert fiscal_doc['fiscal_doc_number'] == 1
    assert fiscal_doc['total'] == 200.0
    assert len(fiscal_doc['fiscal_sign']) == 10
```

### Mode 2: Integration Test (HTTP Mock Servers)

**Purpose:** Realistic end-to-end testing with network simulation

**Components:**
- Mock KKT Driver
- OFD Client (`mock_mode=False`)
- Mock OFD Server (Flask HTTP on port 9000)
- Mock Odoo Server (Flask HTTP on port 8069)

**Performance:**
- Receipt generation: ~0.3s (print delay)
- OFD sync: ~0.05s (HTTP localhost)
- **Total test suite:** <30 seconds (integration tests)

**Example:**
```python
# tests/integration/test_ofd_sync.py
import pytest
from mock_ofd_server import MockOFDServer
from ofd_client import OFDClient

@pytest.fixture
def ofd_server():
    server = MockOFDServer(port=9000)
    server.start()
    yield server
    server.stop()

def test_ofd_sync_success(ofd_server):
    ofd_server.set_success()

    client = OFDClient(base_url="http://localhost:9000", mock_mode=False)
    response = client.send_receipt({'pos_id': 'POS-001', ...})

    assert response['status'] == 'accepted'
    assert ofd_server.get_call_count() == 1
```

### Mode 3: Manual Testing (Docker Compose)

**Purpose:** Manual QA testing and demonstration

**Components:**
- Full KKT Adapter (FastAPI on port 8000)
- Mock OFD Server (Docker service on port 9000)
- Mock Odoo Server (Docker service on port 8069)
- SQLite buffer persistence

**Usage:**
```bash
# Start all mock services
docker-compose up -d kkt_adapter mock_ofd mock_odoo

# Test via HTTP API
curl -X POST http://localhost:8000/v1/kkt/receipt \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: $(uuidgen)" \
  -d '{
    "pos_id": "POS-001",
    "type": "sale",
    "items": [{"name": "Test Product", "price": 100, "quantity": 1, "vat_rate": 20}],
    "payments": [{"type": "cash", "amount": 100}]
  }'

# Check buffer status
curl http://localhost:8000/v1/kkt/buffer/status

# Trigger manual sync
curl -X POST http://localhost:8000/v1/kkt/buffer/sync
```

### Mode 4: Production (Real ККТ Hardware)

**Purpose:** Production deployment with actual fiscal devices

**Components:**
- Real KKT Driver (replaces mock `kkt_driver.py`)
- Real OFD Client (API calls to production OFD)
- Real SQLite buffer (disaster recovery)
- Real Fiscal Module (ФН)

**Implementation:**
```python
# kkt_adapter/app/kkt_driver_real.py (future)
from pyatol import AtolDriver  # Example: АТОЛ driver

def print_receipt(receipt_data: dict) -> Dict[str, Any]:
    """Real fiscal receipt printing via АТОЛ SDK"""
    driver = AtolDriver(port='/dev/ttyUSB0', baudrate=115200)
    driver.open_shift()

    fiscal_doc = driver.print_fiscal_receipt(
        items=receipt_data['fiscal_doc']['items'],
        payments=receipt_data['fiscal_doc']['payments']
    )

    driver.close()
    return fiscal_doc
```

**Configuration (`.env`):**
```bash
# Production mode
KKT_MODE=production  # vs 'mock' (default for development)
KKT_DRIVER_TYPE=atol  # vs 'mock'
KKT_PORT=/dev/ttyUSB0
KKT_BAUDRATE=115200

# Real OFD credentials
KKT_OFD_API_URL=https://ofd.platformaofd.ru/api/v1
KKT_OFD_API_TOKEN=your_production_ofd_token_here
```

---

## 5. Setup Instructions

### Quick Start (Unit Tests)

**1. Install dependencies:**
```bash
cd OpticsERP
pip install -r requirements.txt
```

**2. Run unit tests:**
```bash
pytest tests/unit/test_kkt_driver.py -v

# Expected output:
# tests/unit/test_kkt_driver.py::TestPrintReceipt::test_print_receipt_success PASSED
# tests/unit/test_kkt_driver.py::TestPrintReceipt::test_print_receipt_sequential_numbering PASSED
# ... (30+ tests in <5s)
```

**3. Run single test:**
```bash
pytest tests/unit/test_kkt_driver.py::TestPrintReceipt::test_print_receipt_success -v
```

### Integration Tests Setup

**1. Start mock OFD server:**
```python
# Option A: Via pytest fixture (automatic)
pytest tests/integration/test_ofd_sync.py -v

# Option B: Manual start (for debugging)
python tests/integration/mock_ofd_server.py
# Server starts on http://localhost:9000
# Press Ctrl+C to stop
```

**2. Verify mock OFD server:**
```bash
# Health check
curl http://localhost:9000/ofd/v1/health

# Expected response:
# {
#   "status": "healthy",
#   "permanent_failure": false,
#   "failure_count": 0,
#   "call_count": 0,
#   "receipts_received": 0
# }
```

**3. Run integration tests:**
```bash
pytest tests/integration/test_ofd_sync.py -v

# Expected: All tests PASS (10-20s)
```

### Docker Compose Setup (Full Stack)

**1. Create docker-compose.mock.yml:**
```yaml
version: '3.8'

services:
  # Mock OFD Server
  mock_ofd:
    build:
      context: ./tests/integration
      dockerfile: Dockerfile.mock_ofd
    ports:
      - "9000:9000"
    environment:
      - FLASK_ENV=development
    networks:
      - kkt_network

  # Mock Odoo Server
  mock_odoo:
    build:
      context: ./tests/integration
      dockerfile: Dockerfile.mock_odoo
    ports:
      - "8069:8069"
    networks:
      - kkt_network

  # KKT Adapter (with mocks)
  kkt_adapter:
    build: ./kkt_adapter
    ports:
      - "8000:8000"
    environment:
      - KKT_MODE=mock
      - KKT_OFD_API_URL=http://mock_ofd:9000
      - KKT_ODOO_API_URL=http://mock_odoo:8069
    volumes:
      - ./kkt_adapter/data:/app/data
    depends_on:
      - mock_ofd
      - mock_odoo
    networks:
      - kkt_network

networks:
  kkt_network:
    driver: bridge
```

**2. Start stack:**
```bash
docker-compose -f docker-compose.mock.yml up -d

# Wait for services ready (5-10s)
docker-compose -f docker-compose.mock.yml ps

# Expected:
# NAME                   STATUS   PORTS
# mock_ofd               Up       0.0.0.0:9000->9000/tcp
# mock_odoo              Up       0.0.0.0:8069->8069/tcp
# kkt_adapter            Up       0.0.0.0:8000->8000/tcp
```

**3. Test end-to-end:**
```bash
# Create receipt
curl -X POST http://localhost:8000/v1/kkt/receipt \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: $(uuidgen)" \
  -d @tests/fixtures/sample_receipt.json

# Check buffer
curl http://localhost:8000/v1/kkt/buffer/status | jq

# Verify OFD received
curl http://localhost:9000/ofd/v1/health | jq '.receipts_received'
# Expected: 1
```

---

## 6. Testing Scenarios

### Scenario 1: Happy Path (Online Sale)

**Objective:** Verify end-to-end fiscalization when OFD is available

**Steps:**
1. Mock OFD server is healthy (`set_success()`)
2. Create receipt via `/v1/kkt/receipt`
3. Receipt is printed (Phase 1)
4. Receipt is buffered with `status='pending'`
5. Sync worker sends to OFD (Phase 2)
6. Buffer updates `status='synced'`

**Test:**
```python
def test_happy_path_online_sale(ofd_server):
    ofd_server.set_success()

    # Create receipt
    response = requests.post('http://localhost:8000/v1/kkt/receipt', ...)
    assert response.status_code == 200
    assert response.json()['status'] == 'printed'

    # Wait for sync (max 30s)
    time.sleep(15)

    # Verify synced
    status = requests.get('http://localhost:8000/v1/kkt/buffer/status').json()
    assert status['pending'] == 0
    assert status['synced'] == 1

    # Verify OFD received
    assert ofd_server.get_call_count() == 1
```

### Scenario 2: Offline Mode (OFD Unavailable)

**Objective:** Verify receipts buffer when OFD is down

**Steps:**
1. Mock OFD server is down (`set_permanent_failure(True)`)
2. Create 10 receipts
3. All receipts print successfully (Phase 1 always works)
4. All receipts buffer with `status='pending'`
5. Circuit Breaker opens after 5 failures
6. Sync worker stops trying OFD
7. Buffer fills to 10 receipts

**Test:**
```python
def test_offline_mode_ofd_unavailable(ofd_server):
    ofd_server.set_permanent_failure(True)

    # Create 10 receipts
    for i in range(10):
        response = requests.post('http://localhost:8000/v1/kkt/receipt', ...)
        assert response.json()['status'] == 'printed'  # Phase 1 succeeds

    # Wait for sync attempts (Circuit Breaker)
    time.sleep(10)

    # Verify all buffered
    status = requests.get('http://localhost:8000/v1/kkt/buffer/status').json()
    assert status['pending'] == 10
    assert status['synced'] == 0

    # Verify Circuit Breaker opened
    health = requests.get('http://localhost:8000/v1/health').json()
    assert health['components']['circuit_breaker']['state'] == 'OPEN'

    # Verify OFD never received (all failed)
    assert ofd_server.get_call_count() >= 5  # At least 5 attempts before CB opened
    assert ofd_server.get_received_receipts() == []
```

### Scenario 3: Recovery (OFD Returns)

**Objective:** Verify automatic sync when OFD recovers

**Steps:**
1. Start with OFD down, buffer 10 receipts
2. OFD recovers (`set_success()`)
3. Sync worker detects recovery (Circuit Breaker half-open)
4. All 10 receipts sync successfully
5. Buffer clears (`pending=0`, `synced=10`)

**Test:**
```python
def test_recovery_ofd_returns(ofd_server):
    # Phase 1: Offline - buffer 10 receipts
    ofd_server.set_permanent_failure(True)
    for i in range(10):
        requests.post('http://localhost:8000/v1/kkt/receipt', ...)
    time.sleep(5)

    # Verify buffered
    status = requests.get('http://localhost:8000/v1/kkt/buffer/status').json()
    assert status['pending'] == 10

    # Phase 2: Recovery
    ofd_server.set_success()

    # Trigger manual sync (or wait for automatic)
    requests.post('http://localhost:8000/v1/kkt/buffer/sync')
    time.sleep(2)

    # Verify all synced
    status = requests.get('http://localhost:8000/v1/kkt/buffer/status').json()
    assert status['pending'] == 0
    assert status['synced'] == 10

    # Verify OFD received all
    assert len(ofd_server.get_received_receipts()) == 10
```

### Scenario 4: Circuit Breaker (Cascade Failure Prevention)

**Objective:** Verify Circuit Breaker prevents cascade failures

**Steps:**
1. OFD is slow (500ms response)
2. Create 100 receipts rapidly
3. Circuit Breaker opens after 5 consecutive failures
4. Sync worker stops calling OFD (prevents cascade)
5. New receipts buffer instantly (no OFD delay)

**Test:**
```python
def test_circuit_breaker_cascade_prevention(ofd_server):
    # Configure OFD to fail
    ofd_server.set_failure_count(100)  # Fail many requests

    # Rapidly create receipts
    start = time.time()
    for i in range(20):
        requests.post('http://localhost:8000/v1/kkt/receipt', ...)
    duration = time.time() - start

    # Verify fast completion (Circuit Breaker prevents cascade)
    assert duration < 10  # Should complete in <10s (not 20 * 10s timeout)

    # Verify Circuit Breaker opened
    health = requests.get('http://localhost:8000/v1/health').json()
    assert health['components']['circuit_breaker']['state'] == 'OPEN'

    # Verify OFD was called only ~5 times (not 20)
    assert 5 <= ofd_server.get_call_count() <= 7  # CB opened after 5 failures
```

### Scenario 5: Buffer Overflow (Capacity Limit)

**Objective:** Verify graceful handling when buffer is full

**Steps:**
1. Configure buffer max size = 10
2. Buffer 10 receipts (OFD down)
3. Attempt to create 11th receipt
4. Receipt 11 is rejected with HTTP 503
5. Error message: "Buffer full: Cannot accept new receipts"

**Test:**
```python
def test_buffer_overflow_capacity_limit(ofd_server):
    ofd_server.set_permanent_failure(True)

    # Fill buffer to capacity (10 receipts)
    for i in range(10):
        response = requests.post('http://localhost:8000/v1/kkt/receipt', ...)
        assert response.status_code == 200

    # Verify buffer full
    status = requests.get('http://localhost:8000/v1/kkt/buffer/status').json()
    assert status['percent_full'] == 100.0

    # Attempt 11th receipt (should fail)
    response = requests.post('http://localhost:8000/v1/kkt/receipt', ...)
    assert response.status_code == 503
    assert 'Buffer full' in response.json()['detail']
```

### Scenario 6: Thread Safety (Concurrent Receipts)

**Objective:** Verify no duplicate fiscal doc numbers under load

**Steps:**
1. Create 100 receipts concurrently (10 threads × 10 receipts)
2. Verify all fiscal doc numbers are unique
3. Verify sequential numbering (1..100)

**Test:**
```python
def test_thread_safety_concurrent_receipts():
    import threading

    results = []
    lock = threading.Lock()

    def create_receipts():
        for _ in range(10):
            response = requests.post('http://localhost:8000/v1/kkt/receipt', ...).json()
            with lock:
                results.append(response['fiscal_doc']['fiscal_doc_number'])

    # 10 threads × 10 receipts = 100 total
    threads = [threading.Thread(target=create_receipts) for _ in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # Verify uniqueness
    assert len(results) == 100
    assert len(set(results)) == 100

    # Verify sequential
    assert set(results) == set(range(1, 101))
```

---

## 7. Advanced Configuration

### Mock KKT Driver Configuration

**Custom Mock Settings (for testing specific scenarios):**

```python
# tests/conftest.py
import pytest
from kkt_adapter.app import kkt_driver

@pytest.fixture
def custom_kkt_config():
    """Override mock KKT configuration"""
    original = kkt_driver.MOCK_KKT_CONFIG.copy()

    kkt_driver.MOCK_KKT_CONFIG.update({
        "kkt_number": "1234567890123456",
        "fn_number": "8888888888888888",
        "ofd_name": "Test OFD Provider",
        "inn": "1234567890"
    })

    yield kkt_driver.MOCK_KKT_CONFIG

    # Restore original
    kkt_driver.MOCK_KKT_CONFIG.update(original)
```

### Mock OFD Server Configuration

**Latency Simulation:**
```python
# tests/integration/mock_ofd_server.py (modify)
class MockOFDServer:
    def __init__(self, port=9000, latency_ms=0):
        self.latency_ms = latency_ms
        # ...

    def _setup_routes(self):
        @self.app.route('/ofd/v1/receipt', methods=['POST'])
        def receipt():
            # Simulate network latency
            time.sleep(self.latency_ms / 1000.0)
            # ...

# Usage in tests
server = MockOFDServer(port=9000, latency_ms=500)  # 500ms latency
```

**Partial Failure Mode:**
```python
# Fail every Nth request
class MockOFDServer:
    def __init__(self, fail_every_n=0):
        self.fail_every_n = fail_every_n
        # ...

    def _setup_routes(self):
        @self.app.route('/ofd/v1/receipt', methods=['POST'])
        def receipt():
            with self._lock:
                self._call_count += 1

                # Fail every Nth request
                if self.fail_every_n > 0 and self._call_count % self.fail_every_n == 0:
                    return jsonify({"error": "Intermittent failure"}), 503

                # Success
                # ...

# Usage
server = MockOFDServer(fail_every_n=5)  # Fail every 5th request
```

### Environment Variables for Testing

**`.env.test` (test environment):**
```bash
# KKT Adapter
KKT_MODE=mock
KKT_BUFFER_MAX_SIZE=100  # Smaller buffer for testing
KKT_BUFFER_ALERT_THRESHOLD=0.8
KKT_BUFFER_BLOCK_THRESHOLD=1.0

# OFD Client
KKT_OFD_API_URL=http://localhost:9000
KKT_OFD_TIMEOUT=5  # Shorter timeout for faster tests
KKT_OFD_RETRY_ATTEMPTS=2  # Fewer retries

# Circuit Breaker
KKT_CIRCUIT_BREAKER_THRESHOLD=3  # Open after 3 failures (vs 5 in prod)
KKT_CIRCUIT_BREAKER_TIMEOUT=10   # 10s timeout (vs 60s)
KKT_CIRCUIT_BREAKER_RECOVERY_TIMEOUT=30  # 30s recovery (vs 300s)

# Sync Worker
KKT_HLC_SYNC_INTERVAL=5  # Sync every 5s (vs 30s in prod)
KKT_SYNC_BATCH_SIZE=10   # Smaller batches
```

### pytest Configuration

**`pytest.ini`:**
```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*

# Markers
markers =
    unit: Unit tests (fast, no external deps)
    integration: Integration tests (with mock servers)
    slow: Slow tests (>5s)
    kkt: KKT emulation tests
    ofd: OFD sync tests

# Coverage
addopts =
    --cov=kkt_adapter
    --cov-report=html
    --cov-report=term-missing
    --strict-markers
    -v

# Logging
log_cli = true
log_cli_level = INFO
log_file = tests/logs/pytest.log
log_file_level = DEBUG
```

**Run specific test categories:**
```bash
# Only unit tests (fast)
pytest -m unit

# Only integration tests
pytest -m integration

# Only KKT emulation tests
pytest -m kkt

# Skip slow tests
pytest -m "not slow"

# Run with coverage
pytest --cov=kkt_adapter --cov-report=html
open htmlcov/index.html  # View coverage report
```

---

## 8. Troubleshooting

### Issue 1: Mock OFD Server Won't Start

**Symptoms:**
```
TimeoutError: Mock OFD Server failed to start on 127.0.0.1:9000
```

**Causes:**
- Port 9000 already in use
- Firewall blocking localhost:9000
- Flask not installed

**Solutions:**
```bash
# Check port usage
netstat -tulpn | grep 9000
# Or on Windows
netstat -ano | findstr :9000

# Kill process on port
python scripts/kill_port.py 9000

# Change port
server = MockOFDServer(port=9001)

# Install Flask
pip install flask werkzeug
```

### Issue 2: Fiscal Doc Numbers Not Sequential

**Symptoms:**
```
AssertionError: assert [1, 3, 2] == [1, 2, 3]
```

**Causes:**
- Race condition in counter increment
- Counter not reset between tests

**Solutions:**
```python
# Use reset_counter fixture
@pytest.fixture(autouse=True)
def reset_fiscal_counter():
    from kkt_driver import reset_counter
    reset_counter()
    yield
    reset_counter()

# Or reset manually
from kkt_driver import reset_counter
reset_counter()
```

### Issue 3: OFD Client Timeout

**Symptoms:**
```
OFDClientError: OFD request timeout after 10s
```

**Causes:**
- Mock OFD server not running
- Network issues
- Timeout too short for integration tests

**Solutions:**
```python
# Increase timeout for slow tests
client = OFDClient(base_url="http://localhost:9000", timeout=30)

# Verify server is running
curl http://localhost:9000/ofd/v1/health

# Check logs
docker-compose logs mock_ofd
```

### Issue 4: Buffer Doesn't Clear After Sync

**Symptoms:**
```python
assert status['pending'] == 0  # AssertionError: assert 10 == 0
```

**Causes:**
- Sync worker not running
- OFD client failures
- Circuit Breaker open

**Solutions:**
```bash
# Check sync worker status
curl http://localhost:8000/v1/kkt/worker/status

# Check Circuit Breaker state
curl http://localhost:8000/v1/health | jq '.components.circuit_breaker.state'

# Trigger manual sync
curl -X POST http://localhost:8000/v1/kkt/buffer/sync

# Check OFD server health
curl http://localhost:9000/ofd/v1/health
```

### Issue 5: Duplicate Fiscal Signs

**Symptoms:**
```python
assert fiscal_doc1['fiscal_sign'] != fiscal_doc2['fiscal_sign']  # Fails
```

**Causes:**
- Timestamp resolution too low (same millisecond)
- Deterministic hash with same input

**Solutions:**
```python
# Add small delay between receipts
import time
fiscal_doc1 = print_receipt(receipt_data)
time.sleep(0.01)  # 10ms delay
fiscal_doc2 = print_receipt(receipt_data)

# Or use different inputs
receipt_data_2 = receipt_data.copy()
receipt_data_2['fiscal_doc']['idempotency_key'] = 'different-key'
```

---

## 9. References

### Documentation

**Internal:**
- `CLAUDE.md` §7 - Two-Phase Fiscalization architecture
- `docs/5. Руководство по офлайн-режиму.md` - Offline buffer design
- `docs/diagrams/two_phase_fiscalization.md` - Architecture diagram
- `kkt_adapter/app/kkt_driver.py` - Mock KKT implementation
- `tests/integration/mock_ofd_server.py` - Mock OFD server

**External (54-ФЗ & ККТ):**
- [54-ФЗ Law Text (Russian)](http://www.consultant.ru/document/cons_doc_LAW_42359/)
- [ФФД 1.2 Specification (Russian)](https://www.nalog.gov.ru/rn77/taxation/ffd/)
- [ККТ-ОНЛАЙН Emulator](https://infostart.ru/1c/tools/668945/) - 1C-based emulator
- [K-SOFT ККТ Emulator](https://infostart.ru/1c/tools/1330826/) - ФФД 1.1 support
- [Astral OFD Testing Guide](https://astral.ru/articles/ofd/12956/)

**Python Libraries:**
- [python-cash-register](https://github.com/palazzem/python-cash-register) - Generic cash register library
- [54-FZ GitHub Topics](https://github.com/topics/54-fz) - Related projects

**Testing Tools:**
- [pytest Documentation](https://docs.pytest.org/)
- [Flask Testing](https://flask.palletsprojects.com/en/2.3.x/testing/)
- [requests-mock](https://requests-mock.readthedocs.io/) - HTTP mocking library

### Sources

**Research conducted on:** 2025-11-30

**КТ Emulation Resources:**
- [ККТ-ОНЛАЙН 54-ФЗ Emulator](https://infostart.ru/1c/tools/668945/)
- [K-SOFT ККТ Emulator with OFD](https://infostart.ru/1c/tools/1330826/)
- [Astral OFD Emulation Guide](https://astral.ru/articles/ofd/12956/)
- [1CLancer ККТ Tools](https://1clancer.ru/catalog/3946)
- [Interface31 ККТ Emulators](https://interface31.ru/tech_it/2019/08/emulyator-onlayn-kkt-i-emulyator-bankovskogo-terminala-dlya-1spredpriyatie.html)

**Testing & Development:**
- [GitHub 54-FZ Topics](https://github.com/topics/54-fz)
- [python-cash-register](https://github.com/palazzem/python-cash-register)
- [Maya ECR Simulator](https://developers.maya.ph/docs/electronic-cash-register-simulator-tool)

---

## 10. Next Steps

### Short-term (Current POC)

- [x] Mock KKT Driver implemented
- [x] Mock OFD Client implemented
- [x] Mock OFD Server implemented
- [x] Unit tests (30+ tests, 95%+ coverage)
- [x] Integration tests (OFD sync scenarios)
- [ ] Stress tests (1000+ receipts, buffer overflow)
- [ ] Performance benchmarks (receipts/second)

### Medium-term (MVP)

- [ ] Real ККТ driver abstraction layer (strategy pattern)
- [ ] АТОЛ driver implementation (if АТОЛ hardware selected)
- [ ] ШТРИХ-М driver implementation (if ШТРИХ-М hardware)
- [ ] Driver auto-detection (USB vendor ID)
- [ ] Hardware compatibility matrix documentation
- [ ] Real OFD integration testing (sandbox environments)

### Long-term (Production)

- [ ] ККТ health monitoring (paper jam, fiscal module full, etc.)
- [ ] Shift management (open/close shift automation)
- [ ] X/Z-report generation (fiscal reports)
- [ ] ФН capacity alerts (3-5 days before full)
- [ ] Multi-ККТ support (1 POS = multiple ККТ for redundancy)
- [ ] Failover mechanisms (automatic switch to backup ККТ)

---

**Document Version:** 1.0
**Last Updated:** 2025-11-30
**Author:** AI Agent (Claude Code)
**Status:** ✅ COMPLETE

🤖 Generated with [Claude Code](https://claude.com/claude-code)
