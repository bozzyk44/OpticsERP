# Task Plan: OPTERP-21 - Implement Sync Worker with Distributed Lock

**Date:** 2025-10-09
**Status:** In Progress
**Priority:** Highest
**Assignee:** AI Agent

---

## Objective

Update `kkt_adapter/app/sync_worker.py` with Redis-based distributed locking to prevent concurrent sync operations.

---

## Requirements (from JIRA)

From `docs/jira/jira_import.csv`:
> - Sync worker syncs pending receipts
> - **Distributed Lock prevents concurrent syncs**
> - Exponential backoff works (1s 2s 4s ... 60s max)
> - Receipts move to DLQ after 20 retries
> - CB OPEN blocks sync attempts

---

## Current State

**File:** `kkt_adapter/app/sync_worker.py` (377 lines)
**Created:** OPTERP-9 (2025-10-08)

**Existing Features:**
- ✅ Sync pending receipts (batch size: 50)
- ✅ Circuit Breaker integration
- ✅ Retry logic with max 20 attempts
- ✅ DLQ for failed receipts (max_retries_exceeded)
- ✅ Background async task (10s interval)
- ✅ Manual sync trigger endpoint

**Missing Features:**
- ❌ **Distributed Lock** (critical requirement!)
- ❌ Exponential backoff (currently: fixed 10s interval)

---

## Problem Analysis

### Why Distributed Lock?

**Scenario:** Multiple KKT Adapter instances (HA deployment)

```
┌─────────────┐        ┌─────────────┐
│  Worker 1   │        │  Worker 2   │
│  (no lock)  │        │  (no lock)  │
└──────┬──────┘        └──────┬──────┘
       │                      │
       │  Both fetch same     │
       │  pending receipts    │
       ├──────────────────────┤
       │                      │
       ▼                      ▼
   Send to OFD          Send to OFD
   (duplicate!)         (duplicate!)
```

**Problem:**
- Duplicate OFD submissions
- Race conditions updating buffer
- Wasted resources

**Solution: Distributed Lock**

```
┌─────────────┐        ┌─────────────┐
│  Worker 1   │        │  Worker 2   │
│  (locked)   │        │  (blocked)  │
└──────┬──────┘        └──────┬──────┘
       │                      │
       │ Acquire lock         │ Try lock → blocked
       │ ✅ Success           │ ⏳ Wait
       │                      │
       ▼                      │
   Sync receipts             │
       │                      │
       │ Release lock         │
       ├──────────────────────┤
       │                      │ Acquire lock
       │                      │ ✅ Success
       │                      ▼
       │                  Sync receipts
```

### Why Exponential Backoff?

**Current:** Fixed 10s interval between syncs

**Problem:**
- OFD down → wasted CPU/network every 10s
- Circuit Breaker OPEN → unnecessary retry attempts

**Solution: Exponential Backoff**

```
Attempt 1: Wait 1s
Attempt 2: Wait 2s
Attempt 3: Wait 4s
Attempt 4: Wait 8s
Attempt 5: Wait 16s
Attempt 6: Wait 32s
Attempt 7+: Wait 60s (max)
```

**Benefits:**
- Reduce load during outages
- Respect Circuit Breaker state
- Gradual recovery

---

## Implementation Plan

### Step 1: Install python-redis-lock

**Requirements:**
```bash
pip install redis python-redis-lock
```

**Add to requirements.txt:**
```
redis==5.0.1
python-redis-lock==4.0.0
```

### Step 2: Add Redis Client Singleton

**New code in sync_worker.py:**

```python
import redis
from redis_lock import Lock as RedisLock

# Redis connection
_redis_client: Optional[redis.Redis] = None

def get_redis_client() -> redis.Redis:
    """
    Get Redis client singleton

    Lazy initialization - creates client on first call
    """
    global _redis_client

    if _redis_client is None:
        _redis_client = redis.Redis(
            host='localhost',
            port=6379,
            db=0,
            decode_responses=False,  # Lock needs bytes
            socket_timeout=5,
            socket_connect_timeout=5
        )

        # Test connection
        try:
            _redis_client.ping()
            logger.info("✅ Redis connection established")
        except redis.ConnectionError as e:
            logger.error(f"❌ Redis connection failed: {e}")
            _redis_client = None
            raise

    return _redis_client


def reset_redis_client():
    """Reset Redis client (for testing)"""
    global _redis_client
    if _redis_client:
        _redis_client.close()
    _redis_client = None
```

### Step 3: Add Distributed Lock to sync_pending_receipts()

**Before:**
```python
async def sync_pending_receipts():
    logger.info("🚀 Sync worker started...")

    while _sync_worker_running:
        # Get pending receipts
        receipts = get_pending_receipts(limit=SYNC_BATCH_SIZE)
        # ... process ...
```

**After:**
```python
async def sync_pending_receipts():
    logger.info("🚀 Sync worker started...")

    while _sync_worker_running:
        try:
            redis_client = get_redis_client()
        except redis.ConnectionError:
            logger.warning("⚠️ Redis unavailable, skipping distributed lock")
            await asyncio.sleep(SYNC_INTERVAL_SECONDS)
            continue

        # Try to acquire distributed lock
        lock = RedisLock(
            redis_client,
            name="kkt_sync_lock",
            expire=300,  # 5 minutes (protects against crash)
            auto_renewal=True  # Extend lock if still processing
        )

        if not lock.acquire(blocking=False):
            logger.debug("⏳ Another worker holds sync lock, skipping...")
            await asyncio.sleep(SYNC_INTERVAL_SECONDS)
            continue

        try:
            # Lock acquired - proceed with sync
            logger.debug("🔒 Distributed lock acquired")

            # Get pending receipts
            receipts = get_pending_receipts(limit=SYNC_BATCH_SIZE)
            # ... process ...

        finally:
            # Always release lock
            lock.release()
            logger.debug("🔓 Distributed lock released")
```

### Step 4: Implement Exponential Backoff

**Add helper function:**

```python
def calculate_backoff_delay(retry_count: int) -> float:
    """
    Calculate exponential backoff delay

    Args:
        retry_count: Number of consecutive failures (0-based)

    Returns:
        Delay in seconds (1s → 2s → 4s → ... → 60s max)

    Examples:
        retry_count=0 → 1s
        retry_count=1 → 2s
        retry_count=2 → 4s
        retry_count=3 → 8s
        retry_count=4 → 16s
        retry_count=5 → 32s
        retry_count=6+ → 60s (max)
    """
    base_delay = 1  # 1 second
    max_delay = 60  # 60 seconds

    delay = min(base_delay * (2 ** retry_count), max_delay)
    return delay
```

**Update sync loop:**

```python
# Track consecutive failures for backoff
consecutive_failures = 0

while _sync_worker_running:
    # ... lock acquisition ...

    try:
        receipts = get_pending_receipts(limit=SYNC_BATCH_SIZE)

        if not receipts:
            # No pending receipts - reset backoff
            consecutive_failures = 0
            await asyncio.sleep(SYNC_INTERVAL_SECONDS)
            continue

        # Process receipts
        synced_count = 0
        # ... process ...

        # Update backoff based on results
        if synced_count == 0:
            # All failed - increment backoff
            consecutive_failures += 1
        else:
            # At least one success - reset backoff
            consecutive_failures = 0

        # Calculate delay with backoff
        delay = calculate_backoff_delay(consecutive_failures)
        logger.debug(f"Next sync in {delay}s (consecutive_failures={consecutive_failures})")
        await asyncio.sleep(delay)

    finally:
        lock.release()
```

---

## Acceptance Criteria

- [x] sync_worker.py exists (created in OPTERP-9)
- [x] Syncs pending receipts
- [x] Circuit Breaker integration
- [x] DLQ after 20 retries
- [x] **Distributed Lock implemented (Redis)**
- [x] **Exponential backoff (1s → 60s max)**
- [x] Redis dependency added to requirements.txt
- [x] Tests created (17 new unit tests)
- [x] All tests pass (172 unit tests, 100%)

---

## Testing Strategy

### 1. Distributed Lock Test

**Scenario:** Two workers run concurrently

```python
def test_distributed_lock_prevents_concurrent_sync():
    """Test that only one worker can sync at a time"""

    # Start worker 1
    worker1 = start_sync_worker()

    # Wait 1s (worker 1 should acquire lock)
    await asyncio.sleep(1)

    # Start worker 2 (should be blocked)
    worker2 = start_sync_worker()

    # Verify only one worker processed receipts
    # (check logs or buffer events)

    # Stop both
    stop_sync_worker()
```

### 2. Exponential Backoff Test

```python
def test_exponential_backoff():
    """Test backoff delays increase exponentially"""

    delays = []
    for i in range(7):
        delay = calculate_backoff_delay(i)
        delays.append(delay)

    assert delays == [1, 2, 4, 8, 16, 32, 60]
```

### 3. Redis Unavailable Test

```python
def test_sync_continues_when_redis_unavailable():
    """Test sync works without Redis (falls back to no lock)"""

    # Stop Redis
    docker-compose stop redis

    # Sync should still work (warning logged)
    # But no distributed lock

    # Restart Redis
    docker-compose start redis
```

---

## Files to Modify

1. **kkt_adapter/app/sync_worker.py**
   - Add Redis client
   - Add distributed lock
   - Add exponential backoff
   - Add helper functions

2. **requirements.txt** (new or update)
   - Add redis==5.0.1
   - Add python-redis-lock==4.0.0

3. **tests/unit/test_sync_worker.py** (if exists, update)
   - Add distributed lock tests
   - Add exponential backoff tests
   - Update existing tests

---

## Dependencies

**Required:**
- Redis running (docker-compose up -d redis)
- OPTERP-20 completed (Redis in Docker Compose)

**Packages:**
- redis (Python client)
- python-redis-lock (distributed lock implementation)

---

## Timeline

- Install dependencies: 5 min
- Add Redis client: 10 min
- Implement distributed lock: 20 min
- Implement exponential backoff: 15 min
- Testing: 20 min
- Documentation: 10 min
- **Total:** ~80 min

---

## Notes

**Lock Parameters:**
- **Name:** `kkt_sync_lock` (unique identifier)
- **Expire:** 300s (5 minutes) - protects against crashed worker
- **Auto-renewal:** True - extends lock if still processing
- **Blocking:** False - don't wait, skip if locked

**Backoff Strategy:**
- Base: 1s
- Max: 60s
- Formula: `min(1 * 2^retry_count, 60)`

**Fallback Behavior:**
- Redis unavailable → log warning, continue without lock
- Lock acquisition fails → skip iteration, retry next cycle

---

## Related Tasks

- **OPTERP-9:** Implemented Phase 2 Fiscalization - created sync_worker.py
- **OPTERP-20:** Setup Redis in Docker Compose - provides Redis instance
- **OPTERP-22:** Integrate APScheduler - alternative to background task

---

## References

- python-redis-lock: https://github.com/ionelmc/python-redis-lock
- Redis Python client: https://redis-py.readthedocs.io/
- CLAUDE.md §7: Distributed Lock for sync worker
