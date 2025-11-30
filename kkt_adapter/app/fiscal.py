"""
Fiscal Module - Two-Phase Fiscalization Orchestrator

Author: AI Agent
Created: 2025-10-09
Task: OPTERP-16

Purpose:
Central orchestrator for two-phase fiscalization providing clean API
and encapsulating complexity of Phase 1 (local) and Phase 2 (async).

Architecture:
┌──────────────────────────────────────────────┐
│  Fiscal Module (Orchestrator)               │
│  ┌────────────────────────────────────────┐ │
│  │ Phase 1: Local (Always Succeeds)      │ │
│  │  1. Insert to buffer                  │ │
│  │  2. Print on KKT                      │ │
│  │  3. Update buffer with fiscal doc     │ │
│  └────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────┐ │
│  │ Phase 2: Async (Best-Effort)          │ │
│  │  - Handled by sync_worker             │ │
│  │  - Circuit Breaker protection         │ │
│  │  - Buffered when OFD offline          │ │
│  └────────────────────────────────────────┘ │
└──────────────────────────────────────────────┘

Reference: CLAUDE.md §7 (Two-Phase Fiscalization)
"""

import logging
from dataclasses import dataclass
from typing import Dict, Any, Optional
from datetime import datetime

# Import Phase 1 components
try:
    from buffer import (
        insert_receipt,
        update_receipt_fiscal_doc,
        get_receipt_by_id,
        BufferFullError
    )
    from kkt_driver import print_receipt
    from circuit_breaker import get_circuit_breaker
    from sync_worker import get_worker_status
except ImportError:
    # Handle direct execution
    from buffer import (
        insert_receipt,
        update_receipt_fiscal_doc,
        get_receipt_by_id,
        BufferFullError
    )
    from kkt_driver import print_receipt
    from circuit_breaker import get_circuit_breaker
    from sync_worker import get_worker_status

logger = logging.getLogger(__name__)


# ====================
# Data Classes
# ====================

@dataclass
class FiscalResult:
    """
    Result of fiscal receipt processing

    Attributes:
        receipt_id: Unique receipt identifier (UUID)
        status: Processing status ('printed', 'buffered', 'failed')
        fiscal_doc: Fiscal document data (if printed successfully)
        error: Error message (if failed)
    """
    receipt_id: str
    status: str  # 'printed', 'buffered', 'failed'
    fiscal_doc: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


@dataclass
class FiscalStatus:
    """
    Current fiscal status of a receipt

    Attributes:
        receipt_id: Receipt UUID
        phase1_status: Phase 1 status ('completed', 'failed')
        phase2_status: Phase 2 status ('pending', 'syncing', 'synced', 'failed')
        fiscal_doc: Fiscal document data
        retry_count: Number of Phase 2 retry attempts
        created_at: Receipt creation timestamp
        synced_at: Phase 2 sync completion timestamp (if synced)
    """
    receipt_id: str
    phase1_status: str  # 'completed', 'failed'
    phase2_status: str  # 'pending', 'syncing', 'synced', 'failed'
    fiscal_doc: Optional[Dict[str, Any]] = None
    retry_count: int = 0
    created_at: Optional[datetime] = None
    synced_at: Optional[datetime] = None


@dataclass
class Phase2Health:
    """
    Health status of Phase 2 (async OFD sync)

    Attributes:
        worker_running: Is sync worker running
        circuit_breaker_state: CB state ('CLOSED', 'OPEN', 'HALF_OPEN')
        pending_count: Number of pending receipts
        last_sync_time: Last successful sync timestamp
        success_count: Total successful syncs
        failure_count: Total failed syncs
    """
    worker_running: bool
    circuit_breaker_state: str
    pending_count: int
    last_sync_time: Optional[datetime] = None
    success_count: int = 0
    failure_count: int = 0


# ====================
# Core Functions
# ====================

def process_fiscal_receipt(receipt_data: dict) -> FiscalResult:
    """
    Process fiscal receipt with two-phase fiscalization

    Phase 1 (always succeeds, offline-first):
    1. Insert receipt to SQLite buffer
    2. Print fiscal document on KKT
    3. Update buffer with fiscal document data

    Phase 2 (async, best-effort):
    - Handled automatically by sync_worker (background task)
    - Circuit Breaker protects OFD API calls
    - Receipts buffered when OFD offline

    Args:
        receipt_data: Receipt data dict with structure:
            {
                'pos_id': str,
                'fiscal_doc': {
                    'type': 'sale' | 'refund',
                    'items': [...],
                    'payments': [...],
                    'idempotency_key': str
                }
            }

    Returns:
        FiscalResult with receipt_id, status, fiscal_doc

    Raises:
        BufferFullError: Buffer capacity reached
        ValueError: Invalid receipt data
    """
    logger.info(f"Processing fiscal receipt for POS {receipt_data.get('pos_id')}")

    try:
        # Phase 1 Step 1: Insert into buffer
        receipt_id = insert_receipt(receipt_data)
        logger.info(f"✅ Phase 1.1: Receipt buffered: {receipt_id}")

        # Phase 1 Step 2: Print on KKT
        try:
            fiscal_doc = print_receipt(receipt_data)
            logger.info(f"✅ Phase 1.2: Receipt printed: {receipt_id}, FD#{fiscal_doc['fiscal_doc_number']}")

            # Phase 1 Step 3: Update buffer with fiscal document
            update_receipt_fiscal_doc(receipt_id, fiscal_doc)
            logger.info(f"✅ Phase 1.3: Buffer updated with fiscal doc: {receipt_id}")

            # Phase 1 complete - return success
            # Phase 2 will be handled automatically by sync_worker
            return FiscalResult(
                receipt_id=receipt_id,
                status='printed',
                fiscal_doc=fiscal_doc,
                error=None
            )

        except Exception as print_error:
            # Phase 1 partial success: Buffered but print failed
            # Receipt still in buffer for offline-first guarantee
            logger.warning(f"⚠️ Phase 1.2 failed (print), receipt buffered: {receipt_id}, error={print_error}")

            return FiscalResult(
                receipt_id=receipt_id,
                status='buffered',
                fiscal_doc=None,
                error=f"Print failed: {str(print_error)}"
            )

    except BufferFullError as e:
        # Phase 1 failed: Buffer full (critical error)
        logger.error(f"❌ Phase 1.1 failed: Buffer full: {e}")
        raise

    except ValueError as e:
        # Phase 1 failed: Invalid data (validation error)
        logger.error(f"❌ Phase 1 failed: Validation error: {e}")
        raise

    except Exception as e:
        # Phase 1 failed: Unexpected error
        logger.exception(f"❌ Phase 1 failed: Unexpected error: {e}")
        return FiscalResult(
            receipt_id='',
            status='failed',
            fiscal_doc=None,
            error=f"Unexpected error: {str(e)}"
        )


def get_fiscal_status(receipt_id: str) -> Optional[FiscalStatus]:
    """
    Get current fiscal status for receipt

    Queries buffer to determine Phase 1 and Phase 2 status.

    Args:
        receipt_id: Receipt UUID

    Returns:
        FiscalStatus object or None if not found
    """
    import json

    receipt = get_receipt_by_id(receipt_id)

    if not receipt:
        logger.warning(f"Receipt not found: {receipt_id}")
        return None

    # Parse fiscal_doc (it's stored as JSON string in DB)
    fiscal_doc_dict = None
    if receipt.fiscal_doc:
        try:
            fiscal_doc_dict = json.loads(receipt.fiscal_doc)
        except:
            fiscal_doc_dict = None

    # Determine Phase 1 status
    # Phase 1 is "completed" if fiscal_doc exists (printed successfully)
    phase1_status = 'completed' if fiscal_doc_dict else 'failed'

    # Phase 2 status comes from buffer status field
    phase2_status = receipt.status  # 'pending', 'syncing', 'synced', 'failed'

    return FiscalStatus(
        receipt_id=receipt_id,
        phase1_status=phase1_status,
        phase2_status=phase2_status,
        fiscal_doc=fiscal_doc_dict,
        retry_count=receipt.retry_count,
        created_at=receipt.created_at,
        synced_at=receipt.synced_at if hasattr(receipt, 'synced_at') else None
    )


def get_phase2_health() -> Phase2Health:
    """
    Get Phase 2 (async OFD sync) health status

    Queries sync_worker and circuit_breaker for status.

    Returns:
        Phase2Health object with worker and CB status
    """
    # Get worker status
    worker_status = get_worker_status()
    worker_running = worker_status.get('running', False)
    last_sync = worker_status.get('last_sync_time')
    success_count = worker_status.get('success_count', 0)
    failure_count = worker_status.get('failure_count', 0)
    pending_count = worker_status.get('pending_receipts', 0)

    # Get Circuit Breaker status
    cb = get_circuit_breaker()
    cb_stats = cb.get_stats()
    cb_state = cb_stats.state

    # Parse last_sync_time
    last_sync_time = None
    if last_sync:
        try:
            last_sync_time = datetime.fromisoformat(last_sync.replace('Z', '+00:00'))
        except:
            pass

    return Phase2Health(
        worker_running=worker_running,
        circuit_breaker_state=cb_state,
        pending_count=pending_count,
        last_sync_time=last_sync_time,
        success_count=success_count,
        failure_count=failure_count
    )


# ====================
# Module Info
# ====================

__all__ = [
    'FiscalResult',
    'FiscalStatus',
    'Phase2Health',
    'process_fiscal_receipt',
    'get_fiscal_status',
    'get_phase2_health',
]
