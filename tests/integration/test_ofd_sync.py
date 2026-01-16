"""
Integration Tests for Phase 2 OFD Sync

Author: AI Agent
Created: 2025-10-09
Task: OPTERP-13

Test Coverage:
- Successful OFD sync with Mock OFD Server
- Temporary OFD failures with retry + recovery
- Circuit Breaker behavior (open/close)
- Circuit Breaker recovery after OFD restoration
"""

import pytest
import asyncio
import time
import sys
from pathlib import Path

# Add kkt_adapter to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "kkt_adapter" / "app"))

from buffer import get_receipt_by_id
from circuit_breaker import get_circuit_breaker, reset_circuit_breaker
from ofd_client import OFDClient, reset_ofd_client
from sync_worker import start_sync_worker, stop_sync_worker


# ====================
# Helper Functions
# ====================

async def wait_for_sync(receipt_id: str, timeout: int = 15) -> bool:
    """
    Wait for receipt to be synced to OFD

    Args:
        receipt_id: Receipt UUID
        timeout: Max wait time in seconds

    Returns:
        True if synced, False if timeout
    """
    start = time.time()
    while time.time() - start < timeout:
        receipt = get_receipt_by_id(receipt_id)
        if receipt and receipt.status == "synced":
            return True
        await asyncio.sleep(0.5)
    return False


# ====================
# Tests: OFD Sync Success
# ====================

class TestOFDSyncSuccess:
    """Tests for successful OFD sync scenarios"""

    @pytest.mark.asyncio
    @pytest.mark.ofd_server
    async def test_ofd_sync_basic(self, client, sample_receipt_data, mock_ofd_server, reset_cb):
        """
        Test basic OFD sync with Mock OFD Server

        Scenario:
        1. Create receipt (buffered + printed)
        2. Mock OFD Server accepts request
        3. Sync worker sends to OFD
        4. Receipt marked as 'synced'
        """
        # Setup OFD Client in HTTP mode
        reset_ofd_client()
        from ofd_client import get_ofd_client
        ofd_client = get_ofd_client()
        ofd_client.mock_mode = False
        ofd_client.base_url = "http://localhost:9000"

        # Mock OFD Server in success mode
        mock_ofd_server.set_success()

        # Create receipt
        response = await client.post(
            "/v1/kkt/receipt",
            json=sample_receipt_data,
            headers={"Idempotency-Key": "test-sync-001"}
        )

        assert response.status_code == 200
        receipt_id = response.json()["receipt_id"]

        # Start sync worker
        start_sync_worker()

        try:
            # Wait for sync (max 15s)
            synced = await wait_for_sync(receipt_id, timeout=15)
            assert synced, "Receipt should be synced within 15s"

            # Verify receipt status
            receipt = get_receipt_by_id(receipt_id)
            assert receipt.status == "synced"
            assert receipt.hlc_server_time is not None

            # Verify OFD received it
            received = mock_ofd_server.get_received_receipts()
            assert len(received) == 1
            assert received[0]["pos_id"] == "POS-001"

        finally:
            stop_sync_worker()

    @pytest.mark.asyncio
    @pytest.mark.ofd_server
    async def test_ofd_sync_multiple_receipts(self, client, sample_receipt_data, mock_ofd_server, reset_cb):
        """
        Test OFD sync with multiple receipts

        Scenario:
        1. Create 5 receipts
        2. All receipts synced to OFD
        3. Verify all marked as 'synced'
        """
        # Setup OFD Client in HTTP mode
        reset_ofd_client()
        from ofd_client import get_ofd_client
        ofd_client = get_ofd_client()
        ofd_client.mock_mode = False
        ofd_client.base_url = "http://localhost:9000"

        mock_ofd_server.set_success()

        # Create 5 receipts
        receipt_ids = []
        for i in range(5):
            response = await client.post(
                "/v1/kkt/receipt",
                json=sample_receipt_data,
                headers={"Idempotency-Key": f"test-sync-multi-{i}"}
            )
            assert response.status_code == 200
            receipt_ids.append(response.json()["receipt_id"])

        # Start sync worker
        start_sync_worker()

        try:
            # Wait for all receipts to sync (max 30s)
            for receipt_id in receipt_ids:
                synced = await wait_for_sync(receipt_id, timeout=30)
                assert synced, f"Receipt {receipt_id} should be synced"

            # Verify OFD received all 5
            received = mock_ofd_server.get_received_receipts()
            assert len(received) == 5

        finally:
            stop_sync_worker()


# ====================
# Tests: Temporary Failures
# ====================

class TestOFDTemporaryFailure:
    """Tests for temporary OFD failure scenarios"""

    @pytest.mark.asyncio
    @pytest.mark.ofd_server
    async def test_ofd_temporary_failure_recovery(self, client, sample_receipt_data, mock_ofd_server, reset_cb):
        """
        Test OFD temporary failure with recovery

        Scenario:
        1. Mock OFD fails 3 times
        2. Create receipt
        3. Sync worker retries
        4. After 3 failures, OFD succeeds
        5. Receipt eventually synced
        """
        # Setup OFD Client in HTTP mode
        reset_ofd_client()
        from ofd_client import get_ofd_client
        ofd_client = get_ofd_client()
        ofd_client.mock_mode = False
        ofd_client.base_url = "http://localhost:9000"

        # Mock OFD fails 3 times, then succeeds
        mock_ofd_server.set_failure_count(3)

        # Create receipt
        response = await client.post(
            "/v1/kkt/receipt",
            json=sample_receipt_data,
            headers={"Idempotency-Key": "test-temp-fail-001"}
        )

        assert response.status_code == 200
        receipt_id = response.json()["receipt_id"]

        # Start sync worker
        start_sync_worker()

        try:
            # Wait for retries + success (max 30s)
            synced = await wait_for_sync(receipt_id, timeout=30)
            assert synced, "Receipt should eventually sync after retries"

            # Verify receipt synced
            receipt = get_receipt_by_id(receipt_id)
            assert receipt.status == "synced"
            assert receipt.retry_count >= 3  # Failed at least 3 times

            # Verify OFD received it (after failures)
            received = mock_ofd_server.get_received_receipts()
            assert len(received) == 1

        finally:
            stop_sync_worker()


# ====================
# Tests: Circuit Breaker
# ====================

class TestCircuitBreaker:
    """Tests for Circuit Breaker behavior with OFD failures"""

    @pytest.mark.asyncio
    @pytest.mark.ofd_server
    async def test_circuit_breaker_opens_on_failures(self, client, sample_receipt_data, mock_ofd_server, reset_cb):
        """
        Test Circuit Breaker opens after threshold failures

        Scenario:
        1. Mock OFD in permanent failure mode
        2. Create 5 receipts (trigger CB threshold)
        3. Circuit Breaker opens after 5 failures
        4. Verify CB state = OPEN
        """
        # Setup OFD Client in HTTP mode
        reset_ofd_client()
        from ofd_client import get_ofd_client
        ofd_client = get_ofd_client()
        ofd_client.mock_mode = False
        ofd_client.base_url = "http://localhost:9000"

        # Mock OFD in permanent failure mode
        mock_ofd_server.set_permanent_failure(True)

        # Create 5 receipts (trigger CB)
        receipt_ids = []
        for i in range(5):
            response = await client.post(
                "/v1/kkt/receipt",
                json=sample_receipt_data,
                headers={"Idempotency-Key": f"test-cb-open-{i}"}
            )
            assert response.status_code == 200
            receipt_ids.append(response.json()["receipt_id"])

        # Start sync worker
        start_sync_worker()

        try:
            # Wait for failures (5 receipts × 2s interval = 10s)
            await asyncio.sleep(12)

            # Verify Circuit Breaker opened
            cb = get_circuit_breaker()
            stats = cb.get_stats()
            assert stats.state == "OPEN", "Circuit Breaker should open after threshold failures"
            assert stats.failure_count >= 5

            # Verify receipts not synced
            for receipt_id in receipt_ids:
                receipt = get_receipt_by_id(receipt_id)
                assert receipt.status != "synced"

        finally:
            stop_sync_worker()

    @pytest.mark.asyncio
    @pytest.mark.ofd_server
    @pytest.mark.slow
    async def test_circuit_breaker_recovery(self, client, sample_receipt_data, mock_ofd_server, reset_cb):
        """
        Test Circuit Breaker recovery after OFD restoration

        Scenario:
        1. Open Circuit Breaker (5 failures)
        2. Wait for recovery timeout (60s)
        3. Fix OFD (set success mode)
        4. CB enters HALF_OPEN
        5. Create receipt → syncs successfully
        6. CB returns to CLOSED

        NOTE: This test takes ~70s due to CB recovery timeout
        """
        # Setup OFD Client in HTTP mode
        reset_ofd_client()
        from ofd_client import get_ofd_client
        ofd_client = get_ofd_client()
        ofd_client.mock_mode = False
        ofd_client.base_url = "http://localhost:9000"

        # Step 1: Open Circuit Breaker
        mock_ofd_server.set_permanent_failure(True)

        # Create 5 receipts (trigger CB)
        for i in range(5):
            await client.post(
                "/v1/kkt/receipt",
                json=sample_receipt_data,
                headers={"Idempotency-Key": f"test-cb-recovery-open-{i}"}
            )

        # Start sync worker
        start_sync_worker()

        try:
            # Wait for CB to open
            await asyncio.sleep(12)

            cb = get_circuit_breaker()
            assert cb.get_stats().state == "OPEN"

            # Step 2: Wait for recovery timeout (60s)
            await asyncio.sleep(62)

            # Step 3: Fix OFD
            mock_ofd_server.set_success()

            # Step 4: Create new receipt (CB should try HALF_OPEN)
            response = await client.post(
                "/v1/kkt/receipt",
                json=sample_receipt_data,
                headers={"Idempotency-Key": "test-cb-recovery-new"}
            )
            receipt_id = response.json()["receipt_id"]

            # Wait for sync (CB should succeed and close)
            synced = await wait_for_sync(receipt_id, timeout=15)
            assert synced, "Receipt should sync after CB recovery"

            # Step 5: Verify CB closed
            cb = get_circuit_breaker()
            stats = cb.get_stats()
            assert stats.state == "CLOSED", "Circuit Breaker should close after successful recovery"

        finally:
            stop_sync_worker()
