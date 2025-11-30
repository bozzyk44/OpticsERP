# Docker Compose Testing Guide

**Last Updated:** 2025-11-30
**Purpose:** Run integration tests using Docker Compose with mock services

---

## 📋 Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Quick Start](#quick-start)
4. [Services](#services)
5. [Usage Examples](#usage-examples)
6. [Troubleshooting](#troubleshooting)
7. [Advanced Configuration](#advanced-configuration)

---

## 1. Overview

### What is Docker Compose Testing?

Docker Compose testing enables **realistic end-to-end testing** without production dependencies:
- ✅ **Isolated test environment** - No conflicts with development services
- ✅ **Reproducible tests** - Same environment every time
- ✅ **Fast setup** - Automated service orchestration
- ✅ **Real HTTP** - Actual network communication between services
- ✅ **CI/CD ready** - Automated testing in pipelines

### Test Stack Components

| Service | Port | Purpose | Image |
|---------|------|---------|-------|
| **mock_ofd** | 9000 | Mock OFD API | Python 3.11 + Flask |
| **mock_odoo** | 8070 | Mock Odoo API | Python 3.11 + Flask |
| **kkt_adapter** | 8001 | System Under Test | KKT Adapter (FastAPI) |
| **redis** | 6380 | Distributed Lock | Redis 7 Alpine |
| **test_runner** | - | Run pytest | Python 3.11 + pytest |

---

## 2. Architecture

### Service Topology

```
┌────────────────────────────────────────────────┐
│  Test Network (opticserp_test_network)        │
│                                                │
│  ┌─────────────┐         ┌─────────────┐      │
│  │ Mock OFD    │◄────────│ KKT Adapter │      │
│  │ :9000       │  Sync   │ :8001       │      │
│  └─────────────┘         └──────┬──────┘      │
│                                 │             │
│  ┌─────────────┐                │             │
│  │ Mock Odoo   │◄───────────────┘             │
│  │ :8070       │  Heartbeat                   │
│  └─────────────┘                               │
│                                                │
│  ┌─────────────┐         ┌─────────────┐      │
│  │ Redis       │◄────────│ Test Runner │      │
│  │ :6379       │         │ (pytest)    │      │
│  └─────────────┘         └─────────────┘      │
│                                                │
└────────────────────────────────────────────────┘
            ↑
    Host: localhost
    Ports: 9000, 8070, 8001, 6380
```

### Data Flow

**Receipt Creation Test:**
```
1. Test Runner → POST /v1/kkt/receipt → KKT Adapter
2. KKT Adapter → Print (mock) → Buffer (SQLite)
3. KKT Adapter (sync worker) → POST /ofd/v1/receipt → Mock OFD
4. Mock OFD → 200 OK → KKT Adapter
5. KKT Adapter → Update buffer (status='synced')
6. Test Runner → GET /v1/kkt/buffer/status → Verify synced
```

---

## 3. Quick Start

### Prerequisites

```bash
# Required software
- Docker 24.0+
- Docker Compose 2.20+
- curl (for health checks)
- jq (optional, for JSON formatting)

# Verify installation
docker --version
docker-compose --version
```

### Start Test Stack

**Method 1: Using automated script (recommended)**
```bash
# Make script executable
chmod +x scripts/run_docker_tests.sh

# Run all tests
./scripts/run_docker_tests.sh

# Run with options
./scripts/run_docker_tests.sh --build        # Force rebuild
./scripts/run_docker_tests.sh --keep-up      # Keep services running
./scripts/run_docker_tests.sh --filter test_ofd  # Run specific tests
```

**Method 2: Manual docker-compose**
```bash
# Start services
docker-compose -f docker-compose.test.yml up -d

# Wait for health checks (30-60s)
docker-compose -f docker-compose.test.yml ps

# Run tests
docker-compose -f docker-compose.test.yml exec test_runner \
  pytest tests/integration -v

# Stop services
docker-compose -f docker-compose.test.yml down -v
```

### Verify Services

```bash
# Check all services healthy
docker-compose -f docker-compose.test.yml ps

# Expected output:
# NAME                   STATUS              PORTS
# mock_ofd               Up (healthy)        0.0.0.0:9000->9000/tcp
# mock_odoo              Up (healthy)        0.0.0.0:8070->8070/tcp
# kkt_adapter            Up (healthy)        0.0.0.0:8001->8000/tcp
# test_redis             Up (healthy)        0.0.0.0:6380->6379/tcp
# test_runner            Up                  -

# Test individual services
curl http://localhost:9000/ofd/v1/health  # Mock OFD
curl http://localhost:8070/api/v1/health  # Mock Odoo
curl http://localhost:8001/v1/health      # KKT Adapter
```

---

## 4. Services

### Mock OFD Server

**Configuration:**
- **Port:** 9000
- **Dockerfile:** `tests/integration/Dockerfile.mock_ofd`
- **Code:** `tests/integration/mock_ofd_server.py`
- **Startup:** `mock_ofd_standalone.py`

**API Endpoints:**
```bash
# Accept fiscal receipt
POST /ofd/v1/receipt
Content-Type: application/json
Body: {"pos_id": "POS-001", ...}
→ 200 OK: {"status": "accepted", "ofd_id": "OFD-000001"}
→ 503 Service Unavailable: {"error": "OFD unavailable"}

# Health check
GET /ofd/v1/health
→ 200 OK: {
    "status": "healthy",
    "call_count": 42,
    "receipts_received": 38,
    "permanent_failure": false,
    "failure_count": 0
  }

# Reset state (testing only)
POST /ofd/v1/_test/reset
→ 200 OK: {"status": "reset"}
```

**Failure Mode Configuration:**
```bash
# Set failure modes via environment
docker-compose -f docker-compose.test.yml exec mock_ofd \
  curl -X POST http://localhost:9000/ofd/v1/_test/config \
  -d '{"permanent_failure": true}'

# Or via Python API (in tests)
import requests
requests.post('http://localhost:9000/ofd/v1/_test/config',
              json={'failure_count': 5})
```

### Mock Odoo Server

**Configuration:**
- **Port:** 8070
- **Dockerfile:** `tests/integration/Dockerfile.mock_odoo`
- **Code:** `tests/integration/mock_odoo_server.py`
- **Startup:** `mock_odoo_standalone.py`

**API Endpoints:**
```bash
# Heartbeat (KKT Adapter health check)
POST /api/v1/kkt/heartbeat
Content-Type: application/json
Body: {"kkt_id": "KKT-001", "status": "online", "buffer_fullness": 0.5}
→ 200 OK: {"status": "accepted", "timestamp": 1701345600}

# Health check
GET /api/v1/health
→ 200 OK: {
    "status": "healthy",
    "heartbeat_count": 120,
    "last_heartbeat": "2025-11-30T12:00:00Z"
  }
```

### KKT Adapter (System Under Test)

**Configuration:**
- **Port:** 8001 (external), 8000 (internal)
- **Dockerfile:** `kkt_adapter/Dockerfile`
- **Mode:** Test mode (faster sync, smaller buffer)

**Test-specific environment:**
```yaml
environment:
  # Buffer (test mode)
  - BUFFER_MAX_SIZE=100          # vs 1000 (production)
  - BUFFER_ALERT_THRESHOLD=0.8

  # OFD Client (HTTP mode)
  - OFD_MODE=http                # Real HTTP to mock_ofd
  - OFD_API_URL=http://mock_ofd:9000
  - OFD_TIMEOUT=5                # vs 10s (production)

  # Circuit Breaker (faster response)
  - CIRCUIT_BREAKER_THRESHOLD=3  # vs 5 (production)
  - CIRCUIT_BREAKER_TIMEOUT=10   # vs 60s

  # Sync Worker (faster sync)
  - SYNC_INTERVAL=5              # vs 30s (production)
  - SYNC_BATCH_SIZE=10           # vs 100
```

**API Endpoints:**
```bash
# Create receipt
POST http://localhost:8001/v1/kkt/receipt
Headers: Idempotency-Key: {uuid}
Body: {receipt_data}

# Buffer status
GET http://localhost:8001/v1/kkt/buffer/status

# Manual sync
POST http://localhost:8001/v1/kkt/buffer/sync

# Health check
GET http://localhost:8001/v1/health
```

### Test Runner

**Configuration:**
- **Image:** Python 3.11 + pytest
- **Dockerfile:** `Dockerfile.test`
- **Command:** `tail -f /dev/null` (keep alive for manual execution)

**Run tests manually:**
```bash
# Enter container
docker-compose -f docker-compose.test.yml exec test_runner bash

# Run all integration tests
pytest tests/integration -v

# Run specific test file
pytest tests/integration/test_ofd_sync.py -v

# Run specific test
pytest tests/integration/test_ofd_sync.py::test_happy_path_online_sale -v

# With coverage
pytest tests/integration --cov=kkt_adapter --cov-report=html
```

---

## 5. Usage Examples

### Example 1: Happy Path Test

**Start services and run single test:**
```bash
# Start services
docker-compose -f docker-compose.test.yml up -d

# Wait for healthy
sleep 10

# Run specific test
docker-compose -f docker-compose.test.yml exec test_runner \
  pytest tests/integration/test_ofd_sync.py::test_happy_path_online_sale -v

# Check results
curl http://localhost:9000/ofd/v1/health | jq '.receipts_received'
# Expected: 1

# Cleanup
docker-compose -f docker-compose.test.yml down -v
```

### Example 2: Offline Mode Test

**Test buffering when OFD is unavailable:**
```bash
# Start services
docker-compose -f docker-compose.test.yml up -d

# Set OFD to permanent failure
curl -X POST http://localhost:9000/ofd/v1/_test/config \
  -H "Content-Type: application/json" \
  -d '{"permanent_failure": true}'

# Create receipts (should buffer)
for i in {1..10}; do
  curl -X POST http://localhost:8001/v1/kkt/receipt \
    -H "Content-Type: application/json" \
    -H "Idempotency-Key: $(uuidgen)" \
    -d @tests/fixtures/sample_receipt.json
done

# Verify buffered
curl http://localhost:8001/v1/kkt/buffer/status | jq '.pending'
# Expected: 10

# Verify OFD never received
curl http://localhost:9000/ofd/v1/health | jq '.receipts_received'
# Expected: 0

# Cleanup
docker-compose -f docker-compose.test.yml down -v
```

### Example 3: Recovery Test

**Test automatic sync when OFD recovers:**
```bash
# Start services
docker-compose -f docker-compose.test.yml up -d

# Phase 1: OFD down, buffer receipts
curl -X POST http://localhost:9000/ofd/v1/_test/config \
  -d '{"permanent_failure": true}'

for i in {1..5}; do
  curl -X POST http://localhost:8001/v1/kkt/receipt \
    -H "Idempotency-Key: $(uuidgen)" \
    -d @tests/fixtures/sample_receipt.json
done

# Verify buffered
curl http://localhost:8001/v1/kkt/buffer/status | jq '.pending'
# Expected: 5

# Phase 2: OFD recovers
curl -X POST http://localhost:9000/ofd/v1/_test/config \
  -d '{"permanent_failure": false}'

# Trigger manual sync (or wait for automatic)
curl -X POST http://localhost:8001/v1/kkt/buffer/sync

# Wait for sync
sleep 5

# Verify all synced
curl http://localhost:8001/v1/kkt/buffer/status | jq '.synced'
# Expected: 5

curl http://localhost:9000/ofd/v1/health | jq '.receipts_received'
# Expected: 5

# Cleanup
docker-compose -f docker-compose.test.yml down -v
```

### Example 4: Debugging Failed Tests

**Keep services running for investigation:**
```bash
# Run tests but keep services up
./scripts/run_docker_tests.sh --keep-up

# If tests fail, inspect logs
docker-compose -f docker-compose.test.yml logs kkt_adapter --tail=100
docker-compose -f docker-compose.test.yml logs mock_ofd --tail=50

# Check buffer state
curl http://localhost:8001/v1/kkt/buffer/status | jq

# Check OFD state
curl http://localhost:9000/ofd/v1/health | jq

# Enter KKT Adapter container
docker-compose -f docker-compose.test.yml exec kkt_adapter bash

# Inspect SQLite buffer
sqlite3 /app/data/buffer.db "SELECT * FROM receipts;"

# When done debugging
docker-compose -f docker-compose.test.yml down -v
```

---

## 6. Troubleshooting

### Issue 1: Services Won't Start

**Symptoms:**
```
ERROR: Cannot start service mock_ofd: port is already allocated
```

**Solutions:**
```bash
# Check port conflicts
netstat -tulpn | grep -E "9000|8070|8001|6380"

# Stop conflicting services
docker ps | grep -E "9000|8070|8001|6380"
docker stop <container_id>

# Or use different ports in docker-compose.test.yml
ports:
  - "9001:9000"  # Change 9000 → 9001
```

### Issue 2: Health Checks Failing

**Symptoms:**
```
mock_ofd      Up (unhealthy)
kkt_adapter   Up (health: starting)
```

**Solutions:**
```bash
# Check service logs
docker-compose -f docker-compose.test.yml logs mock_ofd

# Common issues:
# - Flask server crashed (check logs)
# - Port not exposed (check Dockerfile EXPOSE)
# - curl not installed (check Dockerfile)

# Rebuild images
docker-compose -f docker-compose.test.yml build --no-cache
docker-compose -f docker-compose.test.yml up -d
```

### Issue 3: Tests Timeout

**Symptoms:**
```
TimeoutError: Service did not become healthy within 60s
```

**Solutions:**
```bash
# Increase health check intervals
# Edit docker-compose.test.yml:
healthcheck:
  interval: 30s    # vs 10s
  timeout: 10s     # vs 5s
  start_period: 30s  # vs 5s

# Or wait longer before running tests
sleep 30
docker-compose -f docker-compose.test.yml exec test_runner pytest ...
```

### Issue 4: Network Isolation

**Symptoms:**
```
ConnectionError: Cannot connect to http://mock_ofd:9000
```

**Solutions:**
```bash
# Verify all services on same network
docker-compose -f docker-compose.test.yml ps --format json | jq '.[].Networks'

# All should show: opticserp_test_network

# Restart with fresh network
docker-compose -f docker-compose.test.yml down -v
docker network prune -f
docker-compose -f docker-compose.test.yml up -d
```

### Issue 5: Volume Persistence

**Symptoms:**
```
# Tests fail on second run due to stale buffer data
```

**Solutions:**
```bash
# Always clean volumes between runs
docker-compose -f docker-compose.test.yml down -v

# Or use automated script (does this automatically)
./scripts/run_docker_tests.sh

# Manual volume cleanup
docker volume rm opticserp_test_kkt_data
docker volume rm opticserp_test_redis_data
```

---

## 7. Advanced Configuration

### Custom Test Configuration

**Create `.env.test` for custom settings:**
```bash
# .env.test (loaded by docker-compose.test.yml)
BUFFER_MAX_SIZE=50
SYNC_INTERVAL=2
CIRCUIT_BREAKER_THRESHOLD=2
OFD_TIMEOUT=3
```

**Use in docker-compose.test.yml:**
```yaml
kkt_adapter:
  env_file:
    - .env.test
  environment:
    - BUFFER_MAX_SIZE=${BUFFER_MAX_SIZE:-100}
```

### Performance Profiling

**Run tests with profiling:**
```bash
docker-compose -f docker-compose.test.yml exec test_runner \
  pytest tests/integration \
  --profile \
  --profile-svg \
  -v

# Results in /app/prof/*.svg
```

### Coverage Report

**Generate HTML coverage report:**
```bash
docker-compose -f docker-compose.test.yml exec test_runner \
  pytest tests/integration \
  --cov=kkt_adapter \
  --cov-report=html \
  --cov-report=term-missing

# View report
docker-compose -f docker-compose.test.yml exec test_runner \
  python -m http.server 8888 --directory /app/htmlcov

# Open http://localhost:8888 in browser
```

### CI/CD Integration

**GitHub Actions example:**
```yaml
# .github/workflows/test.yml
name: Integration Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Run Docker Compose tests
        run: |
          chmod +x scripts/run_docker_tests.sh
          ./scripts/run_docker_tests.sh --build

      - name: Upload test results
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: test-results
          path: test-results/
```

---

## 8. Best Practices

### Development Workflow

**1. Quick iteration:**
```bash
# Keep services running during development
docker-compose -f docker-compose.test.yml up -d

# Make code changes

# Re-run tests (no restart needed with --reload)
docker-compose -f docker-compose.test.yml exec test_runner \
  pytest tests/integration/test_my_feature.py -v

# When done
docker-compose -f docker-compose.test.yml down -v
```

**2. Test isolation:**
```bash
# Always use fresh environment for each test run
./scripts/run_docker_tests.sh --build

# Or manually
docker-compose -f docker-compose.test.yml down -v
docker-compose -f docker-compose.test.yml up -d --build
```

**3. Debugging:**
```bash
# Keep services up after test failure
./scripts/run_docker_tests.sh --keep-up

# Inspect service state
curl http://localhost:8001/v1/health | jq
docker-compose -f docker-compose.test.yml logs kkt_adapter

# Enter container for debugging
docker-compose -f docker-compose.test.yml exec kkt_adapter bash
```

---

## 9. Summary

**Created Files:**
- ✅ `docker-compose.test.yml` - Test stack orchestration
- ✅ `tests/integration/Dockerfile.mock_ofd` - Mock OFD image
- ✅ `tests/integration/Dockerfile.mock_odoo` - Mock Odoo image
- ✅ `tests/integration/mock_ofd_standalone.py` - OFD standalone runner
- ✅ `tests/integration/mock_odoo_standalone.py` - Odoo standalone runner
- ✅ `tests/integration/requirements-mock.txt` - Mock dependencies
- ✅ `Dockerfile.test` - Test runner image
- ✅ `scripts/run_docker_tests.sh` - Automated test script

**Quick Commands:**
```bash
# Start everything and run tests
./scripts/run_docker_tests.sh

# Run specific tests
./scripts/run_docker_tests.sh --filter test_ofd

# Keep services for debugging
./scripts/run_docker_tests.sh --keep-up

# Force rebuild
./scripts/run_docker_tests.sh --build
```

**Service URLs (when running):**
- Mock OFD: http://localhost:9000/ofd/v1/health
- Mock Odoo: http://localhost:8070/api/v1/health
- KKT Adapter: http://localhost:8001/v1/health
- Redis: localhost:6380

---

**Document Version:** 1.0
**Last Updated:** 2025-11-30
**Author:** AI Agent (Claude Code)
**Status:** ✅ COMPLETE

🤖 Generated with [Claude Code](https://claude.com/claude-code)
