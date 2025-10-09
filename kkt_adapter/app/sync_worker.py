"""
Sync Worker for OFD Fiscalization (Phase 2)

Author: AI Agent
Created: 2025-10-08
Purpose: Background worker for asynchronous OFD synchronization

Reference: CLAUDE.md §4.2, OPTERP-9

This module implements Phase 2 of two-phase fiscalization:
- Background task picks up pending receipts from buffer
- Sends to OFD via Circuit Breaker
- Updates receipt status (syncing → synced/failed)
- Implements retry logic with exponential backoff
- Moves failed receipts to Dead Letter Queue (DLQ)

Architecture:
┌──────────────────────────────────────────────┐
│  Sync Worker (Background Task)              │
│  ┌──────────────────────────────────────┐   │
│  │ 1. Get pending receipts (limit: 50) │   │
│  │ 2. For each receipt:                 │   │
│  │    - Send to OFD via Circuit Breaker│   │
│  │    - Mark synced on success          │   │
│  │    - Increment retry on failure      │   │
│  │    - Move to DLQ if max retries      │   │
│  │ 3. Sleep 10s, repeat                 │   │
│  └──────────────────────────────────────┘   │
└──────────────────────────────────────────────┘
"""

import asyncio
import logging
import time
import json
import redis
from typing import List, Optional
from datetime import datetime
from redis_lock import Lock as RedisLock

# Import buffer operations
try:
    from .buffer import (
        get_pending_receipts,
        mark_synced,
        increment_retry_count,
        move_to_dlq,
        get_receipt_by_id,
        update_receipt_status
    )
    from .circuit_breaker import get_circuit_breaker
    from .ofd_client import get_ofd_client, OFDClientError
except ImportError:
    from buffer import (
        get_pending_receipts,
        mark_synced,
        increment_retry_count,
        move_to_dlq,
        get_receipt_by_id,
        update_receipt_status
    )
    from circuit_breaker import get_circuit_breaker
    from ofd_client import get_ofd_client, OFDClientError

import pybreaker

logger = logging.getLogger(__name__)

# ====================
# Sync Worker State
# ====================

_sync_worker_running = False
_sync_worker_task: Optional[asyncio.Task] = None
_redis_client: Optional[redis.Redis] = None

# Configuration
SYNC_INTERVAL_SECONDS = 10  # Run every 10 seconds
SYNC_BATCH_SIZE = 50  # Process up to 50 receipts per iteration
MAX_RETRY_ATTEMPTS = 20  # Move to DLQ after 20 failed attempts

# Distributed Lock Configuration
LOCK_NAME = "kkt_sync_lock"
LOCK_EXPIRE_SECONDS = 300  # 5 minutes (protects against crash)
LOCK_AUTO_RENEWAL = True  # Extend lock if still processing

# Exponential Backoff Configuration
BACKOFF_BASE_DELAY = 1  # 1 second
BACKOFF_MAX_DELAY = 60  # 60 seconds


# ====================
# Redis Client
# ====================

def get_redis_client() -> Optional[redis.Redis]:
    """
    Get Redis client singleton

    Lazy initialization - creates client on first call.
    Returns None if Redis is unavailable (fallback to no distributed lock).

    Returns:
        Redis client or None if connection fails
    """
    global _redis_client

    if _redis_client is None:
        try:
            _redis_client = redis.Redis(
                host='localhost',
                port=6379,
                db=0,
                decode_responses=False,  # Lock needs bytes
                socket_timeout=5,
                socket_connect_timeout=5
            )

            # Test connection
            _redis_client.ping()
            logger.info("✅ Redis connection established for distributed locking")

        except (redis.ConnectionError, redis.TimeoutError) as e:
            logger.warning(f"⚠️ Redis connection failed: {e}. Distributed locking disabled.")
            _redis_client = None

    return _redis_client


def reset_redis_client():
    """
    Reset Redis client (for testing)

    Closes existing connection and clears singleton.
    """
    global _redis_client
    if _redis_client:
        try:
            _redis_client.close()
        except:
            pass
    _redis_client = None


# ====================
# Exponential Backoff
# ====================

def calculate_backoff_delay(consecutive_failures: int) -> float:
    """
    Calculate exponential backoff delay

    Uses formula: min(BASE * 2^failures, MAX)

    Args:
        consecutive_failures: Number of consecutive sync failures (0-based)

    Returns:
        Delay in seconds

    Examples:
        failures=0 → 1s
        failures=1 → 2s
        failures=2 → 4s
        failures=3 → 8s
        failures=4 → 16s
        failures=5 → 32s
        failures=6+ → 60s (max)
    """
    if consecutive_failures < 0:
        consecutive_failures = 0

    delay = min(BACKOFF_BASE_DELAY * (2 ** consecutive_failures), BACKOFF_MAX_DELAY)
    return delay


# ====================
# Core Sync Logic
# ====================

async def process_receipt(receipt_id: str) -> bool:
    """
    Process single receipt: send to OFD with Circuit Breaker protection

    This function implements the core Phase 2 logic:
    1. Fetch receipt from buffer
    2. Send to OFD via Circuit Breaker
    3. Mark as synced on success
    4. Increment retry count on failure
    5. Move to DLQ if max retries exceeded

    Args:
        receipt_id: Receipt UUID

    Returns:
        True if synced successfully, False otherwise
    """
    cb = get_circuit_breaker()
    ofd = get_ofd_client()

    # Fetch receipt
    receipt = get_receipt_by_id(receipt_id)
    if not receipt:
        logger.error(f"❌ Receipt {receipt_id} not found in buffer")
        return False

    # Skip if already synced
    if receipt.status == 'synced':
        logger.debug(f"Receipt {receipt_id} already synced, skipping")
        return True

    try:
        # Parse fiscal document
        fiscal_doc = json.loads(receipt.fiscal_doc)

        # Send to OFD via Circuit Breaker
        logger.debug(f"Sending receipt {receipt_id} to OFD (attempt {receipt.retry_count + 1})")

        result = cb.call(ofd.send_receipt, fiscal_doc)

        # Mark as synced
        server_time = int(time.time())
        mark_synced(receipt_id, server_time)

        logger.info(f"✅ Receipt {receipt_id} synced successfully (POS: {receipt.pos_id})")
        return True

    except pybreaker.CircuitBreakerError:
        # Circuit is OPEN - skip for now (don't increment retry)
        logger.warning(f"⚠️ Circuit Breaker OPEN, skipping receipt {receipt_id}")
        return False

    except OFDClientError as e:
        # OFD error - increment retry count
        new_count = increment_retry_count(receipt_id, str(e))
        logger.error(f"❌ OFD error for receipt {receipt_id}: {e}, retry_count={new_count}")

        # Move to DLQ if max retries exceeded
        if new_count >= MAX_RETRY_ATTEMPTS:
            move_to_dlq(receipt_id, reason="max_retries_exceeded")
            logger.error(f"🚨 Receipt {receipt_id} moved to DLQ (max retries: {MAX_RETRY_ATTEMPTS})")

        return False

    except Exception as e:
        # Unexpected error - increment retry count
        logger.exception(f"❌ Unexpected error processing receipt {receipt_id}: {e}")
        increment_retry_count(receipt_id, f"Unexpected error: {str(e)}")
        return False


async def sync_pending_receipts():
    """
    Main sync loop: fetch pending receipts and send to OFD

    This function runs continuously in the background with:
    1. Distributed Lock - prevents concurrent sync from multiple workers
    2. Exponential Backoff - reduces load during outages
    3. Batch Processing - processes up to SYNC_BATCH_SIZE receipts
    4. Error Recovery - continues running despite errors

    The loop continues until _sync_worker_running is set to False.
    """
    logger.info(f"🚀 Sync worker started (interval: {SYNC_INTERVAL_SECONDS}s, batch: {SYNC_BATCH_SIZE})")

    # Track consecutive failures for exponential backoff
    consecutive_failures = 0

    while _sync_worker_running:
        lock = None

        try:
            # Try to get Redis client for distributed locking
            redis_client = get_redis_client()

            if redis_client:
                # Try to acquire distributed lock (non-blocking)
                lock = RedisLock(
                    redis_client,
                    name=LOCK_NAME,
                    expire=LOCK_EXPIRE_SECONDS,
                    auto_renewal=LOCK_AUTO_RENEWAL
                )

                acquired = lock.acquire(blocking=False)

                if not acquired:
                    # Another worker holds the lock - skip this iteration
                    logger.debug("⏳ Another worker holds sync lock, skipping iteration...")
                    await asyncio.sleep(SYNC_INTERVAL_SECONDS)
                    continue

                logger.debug("🔒 Distributed lock acquired")
            else:
                # Redis unavailable - proceed without lock (warn once per startup)
                logger.debug("⚠️ Distributed lock unavailable (Redis not connected)")

            # Get pending receipts
            receipts = get_pending_receipts(limit=SYNC_BATCH_SIZE)

            if not receipts:
                # No pending receipts - reset backoff and wait
                consecutive_failures = 0
                logger.debug("No pending receipts, waiting...")
                await asyncio.sleep(SYNC_INTERVAL_SECONDS)
                continue

            logger.info(f"📤 Syncing {len(receipts)} pending receipt(s)...")
            start_time = time.time()

            # Process each receipt
            synced_count = 0
            failed_count = 0
            skipped_count = 0

            for receipt in receipts:
                result = await process_receipt(receipt.id)

                if result:
                    synced_count += 1
                elif receipt.status == 'failed':
                    failed_count += 1
                else:
                    skipped_count += 1

            # Log summary
            duration = time.time() - start_time
            logger.info(
                f"✅ Sync batch completed in {duration:.2f}s: "
                f"synced={synced_count}, failed={failed_count}, skipped={skipped_count}"
            )

            # Update backoff based on results
            if synced_count == 0 and len(receipts) > 0:
                # All failed - increment backoff
                consecutive_failures += 1
            else:
                # At least one success - reset backoff
                consecutive_failures = 0

            # Calculate delay with exponential backoff
            if consecutive_failures > 0:
                delay = calculate_backoff_delay(consecutive_failures)
                logger.info(f"⏰ Backing off for {delay}s (consecutive_failures={consecutive_failures})")
            else:
                delay = SYNC_INTERVAL_SECONDS

            await asyncio.sleep(delay)

        except asyncio.CancelledError:
            logger.info("Sync worker cancelled, stopping...")
            break

        except Exception as e:
            logger.exception(f"❌ Sync worker error: {e}")
            # Continue running despite error
            consecutive_failures += 1
            delay = calculate_backoff_delay(consecutive_failures)
            await asyncio.sleep(delay)

        finally:
            # Always release lock if acquired
            if lock:
                try:
                    lock.release()
                    logger.debug("🔓 Distributed lock released")
                except:
                    pass  # Lock may have expired or Redis disconnected


# ====================
# Worker Lifecycle
# ====================

def start_sync_worker():
    """
    Start background sync worker

    Creates async task that runs sync_pending_receipts() in the background.
    Should be called once during application startup.

    Note: This function is NOT async - it schedules the task but doesn't await it.
    """
    global _sync_worker_running, _sync_worker_task

    if _sync_worker_running:
        logger.warning("⚠️ Sync worker already running")
        return

    _sync_worker_running = True

    # Create background task
    # Note: We need an event loop to create the task
    try:
        loop = asyncio.get_running_loop()
        _sync_worker_task = loop.create_task(sync_pending_receipts())
        logger.info("✅ Sync worker started successfully")
    except RuntimeError:
        # No running event loop - will be started when FastAPI starts
        logger.warning("⚠️ No event loop running yet, sync worker will start with FastAPI")
        _sync_worker_running = False


def stop_sync_worker():
    """
    Stop background sync worker (graceful shutdown)

    Signals the worker to stop and cancels the async task.
    Should be called during application shutdown.
    """
    global _sync_worker_running, _sync_worker_task

    if not _sync_worker_running:
        logger.warning("⚠️ Sync worker not running")
        return

    logger.info("Stopping sync worker...")
    _sync_worker_running = False

    if _sync_worker_task:
        _sync_worker_task.cancel()
        _sync_worker_task = None

    logger.info("✅ Sync worker stopped")


def get_worker_status() -> dict:
    """
    Get sync worker status (for monitoring/health check)

    Returns:
        Dictionary with worker status:
        - running: bool
        - task_status: str (running|stopped|cancelled)
    """
    status = {
        "running": _sync_worker_running,
        "task_status": "stopped"
    }

    if _sync_worker_task:
        if _sync_worker_task.done():
            status["task_status"] = "completed" if not _sync_worker_task.cancelled() else "cancelled"
        else:
            status["task_status"] = "running"

    return status


# ====================
# Manual Sync Trigger
# ====================

async def trigger_manual_sync() -> dict:
    """
    Trigger manual sync (for admin endpoint)

    Runs one sync iteration immediately, without waiting for the scheduled interval.
    This is useful for testing or forcing sync after system recovery.

    Returns:
        Dictionary with sync results:
        - synced: int
        - failed: int
        - skipped: int
        - duration_seconds: float
    """
    logger.info("🔧 Manual sync triggered")

    receipts = get_pending_receipts(limit=SYNC_BATCH_SIZE)

    if not receipts:
        return {
            "synced": 0,
            "failed": 0,
            "skipped": 0,
            "duration_seconds": 0.0,
            "message": "No pending receipts"
        }

    start_time = time.time()

    synced_count = 0
    failed_count = 0
    skipped_count = 0

    for receipt in receipts:
        result = await process_receipt(receipt.id)

        if result:
            synced_count += 1
        elif receipt.status == 'failed':
            failed_count += 1
        else:
            skipped_count += 1

    duration = time.time() - start_time

    return {
        "synced": synced_count,
        "failed": failed_count,
        "skipped": skipped_count,
        "duration_seconds": round(duration, 2)
    }


# ====================
# Example Usage
# ====================

if __name__ == "__main__":
    # Demo: manual sync without FastAPI
    import sys
    sys.path.insert(0, '.')

    logging.basicConfig(level=logging.INFO)

    # Create event loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    # Run one sync iteration
    result = loop.run_until_complete(trigger_manual_sync())

    print(f"\n=== Manual Sync Result ===")
    print(f"Synced: {result['synced']}")
    print(f"Failed: {result['failed']}")
    print(f"Skipped: {result['skipped']}")
    print(f"Duration: {result['duration_seconds']}s")
