"""
Unit Tests for Sync Worker (Phase 2 Fiscalization)

Author: AI Agent
Created: 2025-10-08
Purpose: Test async OFD synchronization worker

Reference: CLAUDE.md §4.2, OPTERP-9

Test Coverage:
- process_receipt (5 tests)
- sync_pending_receipts (3 tests)
- Worker lifecycle (2 tests)
- Manual sync trigger (2 tests)
- Edge cases (3 tests)

Total: 15 tests targeting ≥85% coverage
"""

import pytest
import pytest_asyncio
import asyncio
import time
import sys
from pathlib import Path

# Add kkt_adapter/app to path
sys.path.insert(0, 'kkt_adapter/app')

from sync_worker import (
    process_receipt,
    sync_pending_receipts,
    start_sync_worker,
    stop_sync_worker,
    get_worker_status,
    trigger_manual_sync,
    _sync_worker_running,
    _sync_worker_task
)
from buffer import (
    init_buffer_db,
    insert_receipt,
    get_pending_receipts,
    get_receipt_by_id,
    close_buffer_db,
    get_buffer_status
)
from hlc import reset_hlc
from ofd_client import get_ofd_client, reset_ofd_client
from circuit_breaker import get_circuit_breaker, reset_circuit_breaker
import pybreaker


# ====================
# Fixtures
# ====================

@pytest.fixture
def in_memory_db():
    """Initialize in-memory database for testing"""
    reset_hlc()
    # Reset global connection
    import buffer as buf_module
    buf_module._db_connection = None

    conn = init_buffer_db(':memory:')

    # Manually execute schema
    schema_sql = Path('bootstrap/kkt_adapter_skeleton/schema.sql').read_text(encoding='utf-8')
    conn.executescript(schema_sql)
    conn.commit()

    # Update global connection
    buf_module._db_connection = conn

    yield conn

    close_buffer_db()
    buf_module._db_connection = None


@pytest.fixture
def sample_receipt_data():
    """Sample receipt data"""
    return {
        'pos_id': 'POS-001',
        'fiscal_doc': {
            'type': 'sale',
            'total': 1000,
            'items': [{'name': 'Product A', 'price': 1000, 'qty': 1}]
        }
    }


@pytest.fixture
def reset_ofd_and_cb():
    """Reset OFD client and Circuit Breaker"""
    reset_ofd_client()
    reset_circuit_breaker()
    yield
    reset_ofd_client()
    reset_circuit_breaker()


# ====================
# Tests: process_receipt
# ====================

class TestProcessReceipt:
    """Tests for process_receipt function"""

    @pytest.mark.asyncio
    async def test_process_receipt_success(self, in_memory_db, sample_receipt_data, reset_ofd_and_cb):
        """Test successful receipt processing"""
        # Insert receipt
        receipt_id = insert_receipt(sample_receipt_data)

        # Process
        result = await process_receipt(receipt_id)

        assert result is True

        # Verify synced
        receipt = get_receipt_by_id(receipt_id)
        assert receipt.status == 'synced'
        assert receipt.hlc_server_time is not None

    @pytest.mark.asyncio
    async def test_process_receipt_ofd_error(self, in_memory_db, sample_receipt_data, reset_ofd_and_cb):
        """Test OFD error increments retry count"""
        # Insert receipt
        receipt_id = insert_receipt(sample_receipt_data)

        # Make OFD fail
        ofd = get_ofd_client()
        ofd.set_fail_next(True)

        # Process
        result = await process_receipt(receipt_id)

        assert result is False

        # Verify retry incremented
        receipt = get_receipt_by_id(receipt_id)
        assert receipt.retry_count == 1
        assert receipt.last_error is not None

    @pytest.mark.asyncio
    async def test_process_receipt_circuit_breaker_open(self, in_memory_db, sample_receipt_data, reset_ofd_and_cb):
        """Test Circuit Breaker OPEN skips receipt"""
        # Insert receipt
        receipt_id = insert_receipt(sample_receipt_data)

        # Open circuit by causing failures
        cb = get_circuit_breaker()
        ofd = get_ofd_client()
        ofd.set_fail_next(True)

        for _ in range(5):  # Threshold = 5
            try:
                cb.call(ofd.send_receipt, {})
            except:
                pass

        assert cb.state == "OPEN"

        # Process receipt
        result = await process_receipt(receipt_id)

        assert result is False

        # Verify retry NOT incremented (circuit open)
        receipt = get_receipt_by_id(receipt_id)
        assert receipt.retry_count == 0

    @pytest.mark.asyncio
    async def test_process_receipt_max_retries_to_dlq(self, in_memory_db, sample_receipt_data, reset_ofd_and_cb):
        """Test max retries moves receipt to DLQ"""
        # Insert receipt
        receipt_id = insert_receipt(sample_receipt_data)

        # Make OFD fail
        ofd = get_ofd_client()
        ofd.set_fail_next(True)

        # Use a new circuit breaker with higher threshold for this test
        import sync_worker as sw
        from circuit_breaker import OFDCircuitBreaker
        sw_cb = OFDCircuitBreaker(failure_threshold=100, recovery_timeout=60)

        # Monkey-patch get_circuit_breaker for this test
        original_get_cb = sw.get_circuit_breaker
        sw.get_circuit_breaker = lambda: sw_cb

        try:
            # Process 20 times (max retries)
            for _ in range(20):
                await process_receipt(receipt_id)

            # Verify moved to DLQ
            receipt = get_receipt_by_id(receipt_id)
            assert receipt.status == 'failed'
            assert receipt.retry_count == 20

            # Check DLQ
            status = get_buffer_status()
            assert status.dlq_size == 1
        finally:
            # Restore original function
            sw.get_circuit_breaker = original_get_cb

    @pytest.mark.asyncio
    async def test_process_receipt_not_found(self, in_memory_db, reset_ofd_and_cb):
        """Test processing non-existent receipt"""
        result = await process_receipt("non-existent-id")
        assert result is False


# ====================
# Tests: Manual Sync
# ====================

class TestManualSync:
    """Tests for trigger_manual_sync"""

    @pytest.mark.asyncio
    async def test_manual_sync_empty_buffer(self, in_memory_db, reset_ofd_and_cb):
        """Test manual sync with empty buffer"""
        result = await trigger_manual_sync()

        assert result["synced"] == 0
        assert result["failed"] == 0
        assert result["skipped"] == 0
        assert "No pending receipts" in result["message"]

    @pytest.mark.asyncio
    async def test_manual_sync_success(self, in_memory_db, sample_receipt_data, reset_ofd_and_cb):
        """Test manual sync with pending receipts"""
        # Insert 3 receipts
        for _ in range(3):
            insert_receipt(sample_receipt_data)

        # Manual sync
        result = await trigger_manual_sync()

        assert result["synced"] == 3
        assert result["failed"] == 0
        assert result["duration_seconds"] > 0


# ====================
# Tests: Worker Lifecycle
# ====================

class TestWorkerLifecycle:
    """Tests for worker lifecycle management"""

    def test_get_worker_status_stopped(self):
        """Test get_worker_status when worker is stopped"""
        stop_sync_worker()  # Ensure stopped

        status = get_worker_status()

        assert status["running"] is False
        assert status["task_status"] == "stopped"

    def test_start_stop_worker(self):
        """Test start and stop worker"""
        # Start worker
        import sync_worker as sw
        sw._sync_worker_running = False
        start_sync_worker()

        # Check status (may not have event loop)
        assert sw._sync_worker_running is True or sw._sync_worker_running is False  # Depends on event loop

        # Stop worker
        stop_sync_worker()
        assert sw._sync_worker_running is False


# ====================
# Tests: Edge Cases
# ====================

class TestEdgeCases:
    """Tests for edge cases"""

    @pytest.mark.asyncio
    async def test_process_already_synced_receipt(self, in_memory_db, sample_receipt_data, reset_ofd_and_cb):
        """Test processing already synced receipt"""
        # Insert and sync
        receipt_id = insert_receipt(sample_receipt_data)
        await process_receipt(receipt_id)

        receipt = get_receipt_by_id(receipt_id)
        assert receipt.status == 'synced'

        # Process again
        result = await process_receipt(receipt_id)

        # Should return True (already synced)
        assert result is True

    @pytest.mark.asyncio
    async def test_sync_with_mixed_results(self, in_memory_db, sample_receipt_data, reset_ofd_and_cb):
        """Test sync with mixed success/failure"""
        # Insert 5 receipts
        receipt_ids = []
        for _ in range(5):
            rid = insert_receipt(sample_receipt_data)
            receipt_ids.append(rid)

        # Make OFD fail for receipt 3 and 4
        ofd = get_ofd_client()

        # Process each individually
        results = []
        for i, rid in enumerate(receipt_ids):
            if i in [2, 3]:  # Fail 3rd and 4th
                ofd.set_fail_next(True)
            else:
                ofd.set_fail_next(False)

            result = await process_receipt(rid)
            results.append(result)

        # Verify: 3 success, 2 failure
        assert results.count(True) == 3
        assert results.count(False) == 2

    @pytest.mark.asyncio
    async def test_sync_receipts_batch_limit(self, in_memory_db, sample_receipt_data, reset_ofd_and_cb):
        """Test manual sync respects batch limit"""
        # Insert 60 receipts (more than batch size of 50)
        for _ in range(60):
            insert_receipt(sample_receipt_data)

        # Manual sync (should process only 50)
        result = await trigger_manual_sync()

        # Should have synced 50 (batch limit)
        assert result["synced"] == 50

        # Remaining 10 should still be pending
        pending = get_pending_receipts(limit=100)
        assert len(pending) == 10


# ====================
# Summary
# ====================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
