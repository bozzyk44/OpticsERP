# Task Plan: Two-Phase Fiscalization - Phase 2

**Task ID:** OPTERP-9
**Created:** 2025-10-08
**Assignee:** AI Agent
**Sprint:** POC Week 3
**Reference:** CLAUDE.md §4.2, §5.1 (Week 3)

---

## 📋 Task Description

Implement Phase 2 of two-phase fiscalization: **asynchronous OFD sending with Circuit Breaker protection**.

Currently, `/v1/kkt/receipt` endpoint only implements Phase 1 (save to buffer). This task adds Phase 2 (send to OFD).

### Two-Phase Fiscalization Architecture

```
┌──────────────┐
│   POS Client │
└───────┬──────┘
        │ POST /v1/kkt/receipt
        ▼
┌───────────────────────────────────────────────┐
│  Phase 1: Local (ALWAYS succeeds)            │
│  ✓ Save to SQLite buffer                     │
│  ✓ Print receipt on KKT (mock for now)       │
│  ✓ Return receipt_id immediately             │
└───────────────────────────────────────────────┘
        │
        ▼
┌───────────────────────────────────────────────┐
│  Phase 2: Remote (ASYNC, best-effort)        │
│  ✓ Background task picks pending receipts    │
│  ✓ Circuit Breaker protects OFD calls        │
│  ✓ Retry logic (max 20 attempts)             │
│  ✓ Move to DLQ if max retries exceeded       │
└───────────────────────────────────────────────┘
```

---

## ✅ Acceptance Criteria

1. **Background Sync Worker:**
   - Runs every 5-10 seconds
   - Fetches pending receipts from buffer (limit: 50)
   - Sends to OFD via Circuit Breaker
   - Updates receipt status (syncing → synced/failed)
   - Logs all events to buffer_events table

2. **Circuit Breaker Integration:**
   - Use `OFDCircuitBreaker` from OPTERP-8
   - Fail-fast when circuit is OPEN
   - Track success/failure metrics

3. **Retry Logic:**
   - Increment retry_count on failure
   - Move to DLQ after 20 attempts
   - Exponential backoff (optional for POC)

4. **Endpoint Update:**
   - `POST /v1/kkt/receipt`: Trigger Phase 2 after Phase 1
   - `POST /v1/kkt/buffer/sync`: Manual sync trigger (admin)

5. **Testing:**
   - Unit tests for sync worker (≥15 tests)
   - Integration test: buffer → OFD flow
   - Coverage: ≥85%

---

## 📝 Implementation Steps

### Step 1: Create Sync Worker (30 min)
**File:** `kkt_adapter/app/sync_worker.py`

**Functions:**
- `sync_pending_receipts()` - Main sync logic
- `process_receipt(receipt_id)` - Process single receipt
- `start_sync_worker()` - Start background worker
- `stop_sync_worker()` - Stop background worker (graceful shutdown)

**Implementation:**
```python
import asyncio
import logging
from typing import List
from datetime import datetime

from buffer import get_pending_receipts, mark_synced, increment_retry_count, move_to_dlq
from circuit_breaker import get_circuit_breaker
from ofd_client import get_ofd_client, OFDClientError
import pybreaker

logger = logging.getLogger(__name__)

# Sync worker state
_sync_worker_running = False
_sync_worker_task = None

async def process_receipt(receipt_id: str) -> bool:
    """
    Process single receipt: send to OFD with Circuit Breaker

    Returns:
        True if synced successfully, False otherwise
    """
    cb = get_circuit_breaker()
    ofd = get_ofd_client()

    receipt = get_receipt_by_id(receipt_id)
    if not receipt:
        return False

    try:
        # Send to OFD via Circuit Breaker
        fiscal_doc = json.loads(receipt.fiscal_doc)
        result = cb.call(ofd.send_receipt, fiscal_doc)

        # Mark as synced
        server_time = int(time.time())
        mark_synced(receipt_id, server_time)

        logger.info(f"✅ Receipt {receipt_id} synced successfully")
        return True

    except pybreaker.CircuitBreakerError:
        # Circuit is OPEN - skip for now
        logger.warning(f"⚠️ Circuit Breaker OPEN, skipping {receipt_id}")
        return False

    except OFDClientError as e:
        # OFD error - increment retry
        new_count = increment_retry_count(receipt_id, str(e))
        logger.error(f"❌ OFD error for {receipt_id}: {e}, retry={new_count}")

        # Move to DLQ if max retries exceeded
        if new_count >= 20:
            move_to_dlq(receipt_id, reason="max_retries_exceeded")
            logger.error(f"🚨 Receipt {receipt_id} moved to DLQ (max retries)")

        return False

async def sync_pending_receipts():
    """
    Main sync loop: fetch pending receipts and send to OFD
    """
    while _sync_worker_running:
        try:
            # Get pending receipts
            receipts = get_pending_receipts(limit=50)

            if not receipts:
                # No pending receipts
                await asyncio.sleep(10)
                continue

            logger.info(f"Syncing {len(receipts)} pending receipts...")

            # Process each receipt
            synced_count = 0
            for receipt in receipts:
                if await process_receipt(receipt.id):
                    synced_count += 1

            logger.info(f"Sync completed: {synced_count}/{len(receipts)} synced")

            # Wait before next iteration
            await asyncio.sleep(10)

        except Exception as e:
            logger.exception(f"❌ Sync worker error: {e}")
            await asyncio.sleep(10)

def start_sync_worker():
    """Start background sync worker"""
    global _sync_worker_running, _sync_worker_task

    if _sync_worker_running:
        logger.warning("Sync worker already running")
        return

    _sync_worker_running = True
    _sync_worker_task = asyncio.create_task(sync_pending_receipts())
    logger.info("✅ Sync worker started")

def stop_sync_worker():
    """Stop background sync worker"""
    global _sync_worker_running, _sync_worker_task

    _sync_worker_running = False

    if _sync_worker_task:
        _sync_worker_task.cancel()
        _sync_worker_task = None

    logger.info("✅ Sync worker stopped")
```

### Step 2: Integrate with main.py (15 min)
**File:** `kkt_adapter/app/main.py`

**Changes:**
1. Import sync_worker
2. Start worker on startup event
3. Stop worker on shutdown event
4. Add manual sync endpoint

```python
from sync_worker import start_sync_worker, stop_sync_worker

@app.on_event("startup")
async def startup_event():
    # ...existing code...
    start_sync_worker()

@app.on_event("shutdown")
async def shutdown_event():
    # ...existing code...
    stop_sync_worker()

@app.post("/v1/kkt/buffer/sync")
async def trigger_manual_sync():
    """Trigger manual sync (admin only)"""
    from sync_worker import sync_pending_receipts
    asyncio.create_task(sync_pending_receipts())
    return {"status": "sync_triggered"}
```

### Step 3: Update create_receipt endpoint (10 min)
**File:** `kkt_adapter/app/main.py`

**Change line 232:**
```python
# TODO: Phase 2: Send to OFD asynchronously (OPTERP-8)
```

**To:**
```python
# Phase 2: Sync worker will pick up pending receipt automatically
# No action needed here - decoupled for reliability
```

### Step 4: Write Unit Tests (45 min)
**File:** `tests/unit/test_sync_worker.py`

**Test coverage:**
- Test sync_pending_receipts (empty, single, multiple)
- Test process_receipt (success, OFD error, circuit breaker open)
- Test retry logic (increment, max retries, DLQ)
- Test worker lifecycle (start, stop, restart)
- Test concurrent sync (no race conditions)

**Expected: ≥15 tests, ≥85% coverage**

### Step 5: Run Tests (10 min)
```bash
pytest tests/unit/test_sync_worker.py -v --cov=kkt_adapter.app.sync_worker --cov-report=term-missing
```

### Step 6: Integration Test (20 min)
**Manual test:**
1. Start FastAPI server
2. Create 10 receipts via API
3. Watch logs: sync worker picks up and syncs
4. Verify buffer status: pending=0, synced=10

### Step 7: Commit and Push (5 min)
```bash
git add .
git commit -m "feat(kkt_adapter): implement Phase 2 fiscalization with async sync worker [OPTERP-9]"
git push origin feature/phase1-poc
```

---

## 🧪 Testing Plan

### Unit Tests
1. **test_sync_pending_receipts_empty** - No pending receipts
2. **test_sync_pending_receipts_single** - One receipt synced successfully
3. **test_sync_pending_receipts_multiple** - Multiple receipts (50+)
4. **test_process_receipt_success** - OFD sync success
5. **test_process_receipt_ofd_error** - OFD unavailable, retry incremented
6. **test_process_receipt_circuit_open** - Circuit breaker OPEN, skip
7. **test_process_receipt_max_retries** - 20 retries → DLQ
8. **test_start_stop_worker** - Lifecycle management
9. **test_worker_restart** - Stop and restart worker
10. **test_concurrent_sync** - No race conditions with multiple workers

### Integration Test
```bash
# Terminal 1: Start server
cd kkt_adapter/app && python main.py

# Terminal 2: Create receipts
for i in {1..10}; do
  curl -X POST http://localhost:8000/v1/kkt/receipt \
    -H "Idempotency-Key: $(uuidgen)" \
    -H "Content-Type: application/json" \
    -d '{"pos_id":"POS-001","type":"sale","items":[{"name":"Test","price":100,"qty":1}],"payments":[{"type":"cash","amount":100}]}'
done

# Check buffer status
curl http://localhost:8000/v1/kkt/buffer/status

# Expected: synced=10, pending=0
```

---

## 📊 Metrics

### Coverage Target
- **sync_worker.py:** ≥85%
- **Tests:** 15+ tests

### Performance Target
- Sync 50 receipts in <5 seconds (with mocked OFD)
- Background worker overhead: <10 MB RAM

---

## 🚧 Risks and Mitigation

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| **Async task not started** | Medium | High | Add health check for worker status |
| **Race condition on buffer** | Low | Medium | Thread-safe locks already in buffer.py |
| **Circuit breaker always OPEN** | Low | Medium | Manual sync endpoint for bypass |
| **DLQ grows unbounded** | Low | Medium | Monitoring alert at DLQ size >50 |

---

## 📦 Deliverables

1. ✅ `sync_worker.py` (200+ lines)
2. ✅ Updated `main.py` (startup/shutdown hooks)
3. ✅ `test_sync_worker.py` (15+ tests, ≥85% coverage)
4. ✅ Integration test results (logs)
5. ✅ Git commit + push

---

## 🔗 Dependencies

- **OPTERP-4/5:** SQLite Buffer (✅ complete)
- **OPTERP-8:** Circuit Breaker (✅ complete)
- **OPTERP-6:** FastAPI Basic API (✅ complete)

---

## ⏱️ Time Estimate

| Step | Estimated Time |
|------|---------------|
| 1. Create sync_worker.py | 30 min |
| 2. Integrate with main.py | 15 min |
| 3. Update create_receipt | 10 min |
| 4. Write unit tests | 45 min |
| 5. Run tests | 10 min |
| 6. Integration test | 20 min |
| 7. Commit and push | 5 min |
| **Total** | **~2 hours** |

---

## ✅ Definition of Done

- [ ] `sync_worker.py` created with all functions
- [ ] Worker starts/stops with FastAPI lifecycle
- [ ] Manual sync endpoint works
- [ ] 15+ unit tests pass (≥85% coverage)
- [ ] Integration test: 10 receipts synced successfully
- [ ] Buffer status shows synced receipts (pending=0)
- [ ] No errors in logs during sync
- [ ] Circuit breaker metrics updated correctly
- [ ] Code committed and pushed to `feature/phase1-poc`

---

**Status:** Ready to implement
**Next Task:** OPTERP-10 (Receipt Endpoint Phase 1)
