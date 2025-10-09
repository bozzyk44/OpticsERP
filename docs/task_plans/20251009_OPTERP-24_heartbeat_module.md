# Task Plan: OPTERP-24 - Implement Heartbeat Module

**Date:** 2025-10-09
**Status:** In Progress
**Priority:** High
**Assignee:** AI Agent

---

## Objective

Create `kkt_adapter/app/heartbeat.py` with heartbeat functionality to monitor KKT Adapter connectivity to Odoo.

---

## Requirements (from JIRA)

From `docs/jira/jira_import.csv`:
> - Heartbeat sends every 30s
> - Payload contains buffer_status + cb_state
> - Hysteresis: 3 failures → offline, 2 successes → online
> - Timeout 5s (non-blocking)

---

## Architecture

### Purpose

Heartbeat monitors KKT Adapter → Odoo connectivity:
- KKT Adapter sends periodic "ping" to Odoo
- Odoo tracks which adapters are online/offline
- Hysteresis logic prevents flapping (rapid online/offline transitions)

### Flow Diagram

```
┌────────────────────────────────────────────────┐
│  KKT Adapter (Edge Device)                    │
│  ┌──────────────────────────────────────────┐ │
│  │ Heartbeat Module (every 30s)             │ │
│  │ ┌────────────────────────────────────┐   │ │
│  │ │ 1. Get buffer_status               │   │ │
│  │ │ 2. Get circuit_breaker_state       │   │ │
│  │ │ 3. Build payload                   │   │ │
│  │ │ 4. POST /api/v1/kkt/heartbeat      │   │ │
│  │ │ 5. Update hysteresis state         │   │ │
│  │ └────────────────────────────────────┘   │ │
│  └──────────────────────────────────────────┘ │
└────────────────────────────────────────────────┘
                    │
                    │ HTTP POST (timeout: 5s)
                    ▼
┌────────────────────────────────────────────────┐
│  Odoo (Central Server)                        │
│  ┌──────────────────────────────────────────┐ │
│  │ POST /api/v1/kkt/heartbeat               │ │
│  │ ┌────────────────────────────────────┐   │ │
│  │ │ 1. Receive payload                 │   │ │
│  │ │ 2. Update adapter status           │   │ │
│  │ │ 3. Store metrics                   │   │ │
│  │ │ 4. Return 200 OK                   │   │ │
│  │ └────────────────────────────────────┘   │ │
│  └──────────────────────────────────────────┘ │
└────────────────────────────────────────────────┘
```

### Hysteresis Logic

Prevents rapid online/offline flapping:

```
Initial State: UNKNOWN
├─ 2 consecutive successes → ONLINE
├─ 3 consecutive failures → OFFLINE
└─ Mixed results → Stay in current state

Example:
Success → Success → ONLINE (2 successes)
Success → Fail → Success → ONLINE (still online, not 3 failures)
Fail → Fail → Fail → OFFLINE (3 failures)
Fail → Success → OFFLINE (still offline, not 2 successes)
Success → Success → ONLINE (2 successes, back online)
```

---

## Implementation Plan

### File: kkt_adapter/app/heartbeat.py

```python
"""
Heartbeat Module for KKT Adapter → Odoo Monitoring

Author: AI Agent
Created: 2025-10-09
Task: OPTERP-24

Purpose:
- Send periodic heartbeat to Odoo (every 30s)
- Monitor adapter connectivity
- Report buffer status and circuit breaker state
- Hysteresis logic to prevent flapping

Hysteresis:
- 3 consecutive failures → OFFLINE
- 2 consecutive successes → ONLINE
"""

import asyncio
import logging
import time
import httpx
from typing import Optional, Dict, Any
from datetime import datetime
from enum import Enum

# Import dependencies
try:
    from .buffer import get_buffer_status
    from .circuit_breaker import get_circuit_breaker
except ImportError:
    from buffer import get_buffer_status
    from circuit_breaker import get_circuit_breaker

logger = logging.getLogger(__name__)


# ====================
# State Enums
# ====================

class HeartbeatState(Enum):
    """Heartbeat connection state"""
    UNKNOWN = "unknown"
    ONLINE = "online"
    OFFLINE = "offline"


# ====================
# Heartbeat State
# ====================

_heartbeat_running = False
_heartbeat_task: Optional[asyncio.Task] = None
_current_state = HeartbeatState.UNKNOWN
_consecutive_successes = 0
_consecutive_failures = 0

# Configuration
HEARTBEAT_INTERVAL_SECONDS = 30  # Send every 30s
HEARTBEAT_TIMEOUT_SECONDS = 5    # HTTP timeout
ODOO_HEARTBEAT_URL = "http://localhost:8069/api/v1/kkt/heartbeat"  # TODO: Configure
HYSTERESIS_SUCCESS_THRESHOLD = 2  # 2 successes → ONLINE
HYSTERESIS_FAILURE_THRESHOLD = 3  # 3 failures → OFFLINE


# ====================
# Core Logic
# ====================

def build_heartbeat_payload() -> Dict[str, Any]:
    """
    Build heartbeat payload with current adapter status

    Returns:
        Dictionary with:
        - timestamp: ISO 8601 timestamp
        - adapter_id: KKT Adapter ID (POS ID)
        - buffer_status: Buffer metrics
        - circuit_breaker_state: CB state
    """
    # Get buffer status
    buffer_status = get_buffer_status()

    # Get circuit breaker state
    cb = get_circuit_breaker()
    cb_stats = cb.get_stats()

    # Build payload
    payload = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "adapter_id": "KKT-001",  # TODO: Get from config
        "buffer_status": {
            "total_capacity": buffer_status.capacity,
            "current_queued": buffer_status.pending,
            "percent_full": buffer_status.percent_full,
            "pending": buffer_status.pending,
            "synced": buffer_status.synced,
            "failed": buffer_status.failed,
            "dlq_size": buffer_status.dlq_size
        },
        "circuit_breaker": {
            "state": cb_stats.state,
            "failure_count": cb_stats.failure_count,
            "success_count": cb_stats.success_count
        }
    }

    return payload


async def send_heartbeat() -> bool:
    """
    Send single heartbeat to Odoo

    Returns:
        True if heartbeat sent successfully, False otherwise
    """
    try:
        # Build payload
        payload = build_heartbeat_payload()

        # Send HTTP POST
        async with httpx.AsyncClient(timeout=HEARTBEAT_TIMEOUT_SECONDS) as client:
            response = await client.post(ODOO_HEARTBEAT_URL, json=payload)

            if response.status_code == 200:
                logger.debug("✅ Heartbeat sent successfully")
                return True
            else:
                logger.warning(f"⚠️ Heartbeat failed: HTTP {response.status_code}")
                return False

    except httpx.TimeoutException:
        logger.warning(f"⚠️ Heartbeat timeout after {HEARTBEAT_TIMEOUT_SECONDS}s")
        return False

    except httpx.ConnectError:
        logger.warning("⚠️ Heartbeat connection failed (Odoo unreachable)")
        return False

    except Exception as e:
        logger.exception(f"❌ Heartbeat error: {e}")
        return False


def update_heartbeat_state(success: bool) -> HeartbeatState:
    """
    Update heartbeat state with hysteresis logic

    Args:
        success: True if heartbeat succeeded, False otherwise

    Returns:
        New heartbeat state (ONLINE/OFFLINE/UNKNOWN)
    """
    global _current_state, _consecutive_successes, _consecutive_failures

    if success:
        # Success - increment success counter, reset failure counter
        _consecutive_successes += 1
        _consecutive_failures = 0

        # Check if we should transition to ONLINE
        if _consecutive_successes >= HYSTERESIS_SUCCESS_THRESHOLD:
            if _current_state != HeartbeatState.ONLINE:
                logger.info(f"🟢 Heartbeat state: OFFLINE → ONLINE ({_consecutive_successes} successes)")
            _current_state = HeartbeatState.ONLINE

    else:
        # Failure - increment failure counter, reset success counter
        _consecutive_failures += 1
        _consecutive_successes = 0

        # Check if we should transition to OFFLINE
        if _consecutive_failures >= HYSTERESIS_FAILURE_THRESHOLD:
            if _current_state != HeartbeatState.OFFLINE:
                logger.warning(f"🔴 Heartbeat state: ONLINE → OFFLINE ({_consecutive_failures} failures)")
            _current_state = HeartbeatState.OFFLINE

    return _current_state


async def heartbeat_loop():
    """
    Main heartbeat loop - runs continuously in background

    Sends heartbeat every HEARTBEAT_INTERVAL_SECONDS
    Updates hysteresis state based on success/failure
    """
    logger.info(f"🚀 Heartbeat started (interval: {HEARTBEAT_INTERVAL_SECONDS}s)")

    while _heartbeat_running:
        try:
            # Send heartbeat
            success = await send_heartbeat()

            # Update state with hysteresis
            new_state = update_heartbeat_state(success)

            logger.debug(
                f"Heartbeat: {new_state.value}, "
                f"successes={_consecutive_successes}, "
                f"failures={_consecutive_failures}"
            )

            # Wait before next heartbeat
            await asyncio.sleep(HEARTBEAT_INTERVAL_SECONDS)

        except asyncio.CancelledError:
            logger.info("Heartbeat cancelled, stopping...")
            break

        except Exception as e:
            logger.exception(f"❌ Heartbeat loop error: {e}")
            await asyncio.sleep(HEARTBEAT_INTERVAL_SECONDS)


# ====================
# Lifecycle
# ====================

def start_heartbeat():
    """Start background heartbeat task"""
    global _heartbeat_running, _heartbeat_task

    if _heartbeat_running:
        logger.warning("⚠️ Heartbeat already running")
        return

    _heartbeat_running = True

    try:
        loop = asyncio.get_running_loop()
        _heartbeat_task = loop.create_task(heartbeat_loop())
        logger.info("✅ Heartbeat started successfully")
    except RuntimeError:
        logger.warning("⚠️ No event loop running, heartbeat will start with FastAPI")
        _heartbeat_running = False


def stop_heartbeat():
    """Stop background heartbeat task (graceful shutdown)"""
    global _heartbeat_running, _heartbeat_task

    if not _heartbeat_running:
        logger.warning("⚠️ Heartbeat not running")
        return

    logger.info("Stopping heartbeat...")
    _heartbeat_running = False

    if _heartbeat_task:
        _heartbeat_task.cancel()
        _heartbeat_task = None

    logger.info("✅ Heartbeat stopped")


def get_heartbeat_status() -> Dict[str, Any]:
    """
    Get heartbeat status (for monitoring/health check)

    Returns:
        Dictionary with heartbeat status
    """
    return {
        "running": _heartbeat_running,
        "state": _current_state.value,
        "consecutive_successes": _consecutive_successes,
        "consecutive_failures": _consecutive_failures
    }
```

---

## Integration with main.py

Add heartbeat to FastAPI startup/shutdown:

```python
# main.py
from .heartbeat import start_heartbeat, stop_heartbeat

@app.on_event("startup")
async def startup_event():
    init_buffer_db()
    start_sync_worker()
    start_heartbeat()  # Add this
    logger.info("✅ Heartbeat started")

@app.on_event("shutdown")
async def shutdown_event():
    stop_heartbeat()  # Add this
    stop_sync_worker()
    close_buffer_db()
```

---

## Testing Strategy

### Unit Tests

File: `tests/unit/test_heartbeat.py`

```python
def test_build_heartbeat_payload():
    """Test payload structure"""
    payload = build_heartbeat_payload()
    assert "timestamp" in payload
    assert "adapter_id" in payload
    assert "buffer_status" in payload
    assert "circuit_breaker" in payload

def test_hysteresis_success_to_online():
    """Test 2 successes → ONLINE"""
    reset_heartbeat_state()
    update_heartbeat_state(True)
    update_heartbeat_state(True)
    assert get_heartbeat_status()["state"] == "online"

def test_hysteresis_failure_to_offline():
    """Test 3 failures → OFFLINE"""
    reset_heartbeat_state()
    update_heartbeat_state(False)
    update_heartbeat_state(False)
    update_heartbeat_state(False)
    assert get_heartbeat_status()["state"] == "offline"

def test_hysteresis_prevents_flapping():
    """Test hysteresis prevents rapid state changes"""
    reset_heartbeat_state()
    update_heartbeat_state(True)   # 1 success
    update_heartbeat_state(False)  # 1 failure (resets successes)
    assert get_heartbeat_status()["state"] == "unknown"  # Not enough for transition
```

---

## Acceptance Criteria

- [ ] heartbeat.py module created
- [ ] Heartbeat sends every 30s
- [ ] Payload contains buffer_status
- [ ] Payload contains circuit_breaker_state
- [ ] Hysteresis: 3 failures → OFFLINE
- [ ] Hysteresis: 2 successes → ONLINE
- [ ] Timeout 5s (non-blocking)
- [ ] Start on FastAPI startup
- [ ] Stop on FastAPI shutdown
- [ ] Unit tests created (5+ tests)
- [ ] All tests pass

---

## Timeline

- Module implementation: 30 min
- Integration with main.py: 10 min
- Unit tests: 30 min
- Testing: 15 min
- **Total:** ~85 min

---

## Notes

**Why 30s interval?**
- Balance between responsiveness and server load
- 30s means max 30s to detect outage
- 2 min (4 heartbeats) to confirm stable recovery

**Why 5s timeout?**
- Non-blocking (doesn't delay sync worker)
- Fast enough for real-time monitoring
- Allows for network latency

**Hysteresis Benefits:**
- Prevents rapid state transitions (flapping)
- Filters transient network issues
- Requires sustained failure/recovery before state change

---

## Related Tasks

- **OPTERP-25:** Integrate APScheduler for Heartbeat (optional - can use asyncio.Task like sync worker)
- **OPTERP-26:** Create Mock Odoo Server - for heartbeat testing
- **OPTERP-27:** Create Heartbeat Unit Tests

---

## Dependencies

**Required:**
- httpx (async HTTP client) - already in requirements.txt
- Buffer module (get_buffer_status)
- Circuit Breaker module (get_circuit_breaker)

**Odoo Side:**
- POST /api/v1/kkt/heartbeat endpoint (future task)
