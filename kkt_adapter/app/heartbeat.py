"""
Heartbeat Module for KKT Adapter → Odoo Monitoring

Author: AI Agent
Created: 2025-10-09
Task: OPTERP-24

Purpose:
- Send periodic heartbeat to Odoo (every 30s)
- Monitor adapter connectivity status
- Report buffer status and circuit breaker state
- Hysteresis logic to prevent state flapping

Architecture:
┌─────────────────────────────────────────┐
│  Heartbeat Loop (30s interval)         │
│  ┌───────────────────────────────────┐ │
│  │ 1. Get buffer_status              │ │
│  │ 2. Get circuit_breaker_state      │ │
│  │ 3. Build payload                  │ │
│  │ 4. POST /api/v1/kkt/heartbeat     │ │
│  │ 5. Update hysteresis state        │ │
│  └───────────────────────────────────┘ │
└─────────────────────────────────────────┘

Hysteresis Logic:
- Initial state: UNKNOWN
- 2 consecutive successes → ONLINE
- 3 consecutive failures → OFFLINE
- Mixed results → Stay in current state
"""

import asyncio
import logging
import httpx
from typing import Optional, Dict, Any
from datetime import datetime
from enum import Enum

# Import dependencies
try:
    from buffer import get_buffer_status
    from circuit_breaker import get_circuit_breaker
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
ODOO_HEARTBEAT_URL = "http://localhost:8069/api/v1/kkt/heartbeat"
HYSTERESIS_SUCCESS_THRESHOLD = 2  # 2 successes → ONLINE
HYSTERESIS_FAILURE_THRESHOLD = 3  # 3 failures → OFFLINE


# ====================
# Core Logic
# ====================

def build_heartbeat_payload() -> Dict[str, Any]:
    """
    Build heartbeat payload with current adapter status

    Includes:
    - Timestamp (ISO 8601 UTC)
    - Adapter ID
    - Buffer status (capacity, queued, percent_full, etc.)
    - Circuit breaker state (CLOSED/OPEN/HALF_OPEN)

    Returns:
        Dictionary with heartbeat payload
    """
    # Get buffer status
    buffer_status = get_buffer_status()

    # Get circuit breaker state
    cb = get_circuit_breaker()
    cb_stats = cb.get_stats()

    # Build payload
    payload = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "adapter_id": "KKT-001",  # TODO: Get from config/environment
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

    Sends HTTP POST to Odoo heartbeat endpoint with current adapter status.
    Non-blocking with 5s timeout to prevent blocking sync worker.

    Returns:
        True if heartbeat sent successfully (HTTP 200), False otherwise
    """
    try:
        # Build payload
        payload = build_heartbeat_payload()

        # Send HTTP POST (non-blocking, 5s timeout)
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

    Hysteresis prevents rapid state flapping:
    - Requires 2 consecutive successes to transition to ONLINE
    - Requires 3 consecutive failures to transition to OFFLINE
    - Mixed results keep current state

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
                logger.info(
                    f"🟢 Heartbeat state: {_current_state.value} → ONLINE "
                    f"({_consecutive_successes} consecutive successes)"
                )
            _current_state = HeartbeatState.ONLINE

    else:
        # Failure - increment failure counter, reset success counter
        _consecutive_failures += 1
        _consecutive_successes = 0

        # Check if we should transition to OFFLINE
        if _consecutive_failures >= HYSTERESIS_FAILURE_THRESHOLD:
            if _current_state != HeartbeatState.OFFLINE:
                logger.warning(
                    f"🔴 Heartbeat state: {_current_state.value} → OFFLINE "
                    f"({_consecutive_failures} consecutive failures)"
                )
            _current_state = HeartbeatState.OFFLINE

    return _current_state


async def heartbeat_loop():
    """
    Main heartbeat loop - runs continuously in background

    Sends heartbeat every HEARTBEAT_INTERVAL_SECONDS (30s).
    Updates hysteresis state based on success/failure.
    Continues running until _heartbeat_running is set to False.
    """
    logger.info(f"🚀 Heartbeat started (interval: {HEARTBEAT_INTERVAL_SECONDS}s)")

    while _heartbeat_running:
        try:
            # Send heartbeat
            success = await send_heartbeat()

            # Update state with hysteresis
            new_state = update_heartbeat_state(success)

            logger.debug(
                f"Heartbeat: state={new_state.value}, "
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
            # Continue running despite error
            await asyncio.sleep(HEARTBEAT_INTERVAL_SECONDS)


# ====================
# Lifecycle
# ====================

def start_heartbeat():
    """
    Start background heartbeat task

    Creates async task that runs heartbeat_loop() in the background.
    Should be called once during application startup.

    Note: This function is NOT async - it schedules the task but doesn't await it.
    """
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
    """
    Stop background heartbeat task (graceful shutdown)

    Signals the heartbeat loop to stop and cancels the async task.
    Should be called during application shutdown.
    """
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
        Dictionary with:
        - running: bool (is heartbeat running)
        - state: str (ONLINE/OFFLINE/UNKNOWN)
        - consecutive_successes: int
        - consecutive_failures: int
    """
    return {
        "running": _heartbeat_running,
        "state": _current_state.value,
        "consecutive_successes": _consecutive_successes,
        "consecutive_failures": _consecutive_failures
    }


def reset_heartbeat_state():
    """
    Reset heartbeat state (for testing)

    Resets state to UNKNOWN and clears counters.
    """
    global _current_state, _consecutive_successes, _consecutive_failures

    _current_state = HeartbeatState.UNKNOWN
    _consecutive_successes = 0
    _consecutive_failures = 0
