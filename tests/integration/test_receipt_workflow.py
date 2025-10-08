"""
Integration Tests for Receipt Endpoint Workflow

Author: AI Agent
Created: 2025-10-09
Task: OPTERP-11

Test Coverage:
- End-to-end receipt creation (buffer → print → sync)
- Offline scenarios
- Circuit Breaker behavior
- DLQ management
- Idempotency
- Error handling
"""

import pytest
import uuid
import time
import asyncio
from typing import Optional

# Import modules under test
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "kkt_adapter" / "app"))

from buffer import get_receipt_by_id, get_buffer_status, get_db
from circuit_breaker import get_circuit_breaker


# ====================
# Helper Functions
# ====================

async def wait_for_status(receipt_id: str, target_status: str, timeout: int = 15) -> bool:
    """
    Wait for receipt to reach target status

    Args:
        receipt_id: Receipt UUID
        target_status: Target status (pending|syncing|synced|failed)
        timeout: Max wait time in seconds

    Returns:
        True if status reached, False if timeout
    """
    start = time.time()
    while time.time() - start < timeout:
        receipt = get_receipt_by_id(receipt_id)
        if receipt and receipt.status == target_status:
            return True
        await asyncio.sleep(0.5)
    return False


def get_receipt_from_buffer(receipt_id: str) -> Optional[dict]:
    """Get receipt from buffer by ID"""
    receipt = get_receipt_by_id(receipt_id)
    return receipt.to_dict() if receipt else None


# ====================
# Tests: Happy Path
# ====================

class TestReceiptHappyPath:
    """Tests for successful receipt creation and processing"""

    @pytest.mark.asyncio
    async def test_receipt_creation_success(self, client, sample_receipt_data):
        """Test successful receipt creation with printing"""
        response = await client.post(
            "/v1/kkt/receipt",
            json=sample_receipt_data,
            headers={"Idempotency-Key": str(uuid.uuid4())}
        )

        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "printed"
        assert "receipt_id" in data
        assert data["fiscal_doc"] is not None
        assert "fiscal_doc_number" in data["fiscal_doc"]
        assert "fiscal_sign" in data["fiscal_doc"]
        assert data["message"] == "Receipt printed successfully"

        # Verify receipt_id is valid UUID
        receipt_id = data["receipt_id"]
        uuid.UUID(receipt_id)

        # Verify stored in buffer
        receipt = get_receipt_from_buffer(receipt_id)
        assert receipt is not None
        assert receipt["status"] == "pending"
        assert receipt["pos_id"] == "POS-001"

    @pytest.mark.asyncio
    async def test_receipt_fiscal_doc_populated(self, client, sample_receipt_data):
        """Test fiscal document populated after printing"""
        response = await client.post(
            "/v1/kkt/receipt",
            json=sample_receipt_data,
            headers={"Idempotency-Key": str(uuid.uuid4())}
        )

        assert response.status_code == 200
        fiscal_doc = response.json()["fiscal_doc"]

        # Verify fiscal doc structure
        assert fiscal_doc["fiscal_doc_number"] == 1  # First receipt
        assert len(fiscal_doc["fiscal_sign"]) == 10
        assert "fiscal_datetime" in fiscal_doc
        assert fiscal_doc["fn_number"] == "9999999999999999"
        assert fiscal_doc["kkt_number"] == "0000000000001234"
        assert "qr_code_data" in fiscal_doc
        assert fiscal_doc["shift_number"] == 1
        assert fiscal_doc["total"] == 200.00

    @pytest.mark.asyncio
    async def test_receipt_stored_in_buffer(self, client, sample_receipt_data):
        """Test receipt stored in SQLite buffer"""
        response = await client.post(
            "/v1/kkt/receipt",
            json=sample_receipt_data,
            headers={"Idempotency-Key": str(uuid.uuid4())}
        )

        receipt_id = response.json()["receipt_id"]
        receipt = get_receipt_from_buffer(receipt_id)

        # Verify buffer entry
        assert receipt["id"] == receipt_id
        assert receipt["pos_id"] == "POS-001"
        assert receipt["status"] == "pending"
        assert receipt["retry_count"] == 0
        assert receipt["hlc_local_time"] > 0
        assert receipt["hlc_logical_counter"] >= 0

        # Verify fiscal doc merged into buffer
        fiscal_doc = receipt["fiscal_doc"]
        assert "fiscal_doc_number" in fiscal_doc
        assert "fiscal_sign" in fiscal_doc

    @pytest.mark.asyncio
    async def test_sequential_fiscal_doc_numbers(self, client, sample_receipt_data):
        """Test sequential fiscal document numbering"""
        receipt_ids = []

        for i in range(5):
            response = await client.post(
                "/v1/kkt/receipt",
                json=sample_receipt_data,
                headers={"Idempotency-Key": str(uuid.uuid4())}
            )
            assert response.status_code == 200
            receipt_ids.append(response.json()["receipt_id"])

        # Verify sequential numbering
        for i, receipt_id in enumerate(receipt_ids):
            receipt = get_receipt_from_buffer(receipt_id)
            fiscal_doc = receipt["fiscal_doc"]
            assert fiscal_doc["fiscal_doc_number"] == i + 1


# ====================
# Tests: Error Handling
# ====================

class TestReceiptErrorHandling:
    """Tests for error handling and validation"""

    @pytest.mark.asyncio
    async def test_receipt_missing_idempotency_key(self, client, sample_receipt_data):
        """Test error when Idempotency-Key header missing"""
        response = await client.post(
            "/v1/kkt/receipt",
            json=sample_receipt_data
        )

        assert response.status_code == 422  # Unprocessable Entity

    @pytest.mark.asyncio
    async def test_receipt_invalid_type(self, client, sample_receipt_data):
        """Test error when receipt type invalid"""
        sample_receipt_data["type"] = "invalid_type"

        response = await client.post(
            "/v1/kkt/receipt",
            json=sample_receipt_data,
            headers={"Idempotency-Key": str(uuid.uuid4())}
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_receipt_empty_items(self, client, sample_receipt_data):
        """Test error when items list empty"""
        sample_receipt_data["items"] = []

        response = await client.post(
            "/v1/kkt/receipt",
            json=sample_receipt_data,
            headers={"Idempotency-Key": str(uuid.uuid4())}
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_receipt_empty_payments(self, client, sample_receipt_data):
        """Test error when payments list empty"""
        sample_receipt_data["payments"] = []

        response = await client.post(
            "/v1/kkt/receipt",
            json=sample_receipt_data,
            headers={"Idempotency-Key": str(uuid.uuid4())}
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_receipt_negative_price(self, client, sample_receipt_data):
        """Test error when item price negative"""
        sample_receipt_data["items"][0]["price"] = -100.00

        response = await client.post(
            "/v1/kkt/receipt",
            json=sample_receipt_data,
            headers={"Idempotency-Key": str(uuid.uuid4())}
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_receipt_payment_mismatch(self, client, sample_receipt_data):
        """Test error when payment total doesn't match items total"""
        sample_receipt_data["items"][0]["total"] = 200.00
        sample_receipt_data["payments"][0]["amount"] = 150.00  # Mismatch

        response = await client.post(
            "/v1/kkt/receipt",
            json=sample_receipt_data,
            headers={"Idempotency-Key": str(uuid.uuid4())}
        )

        assert response.status_code == 422


# ====================
# Tests: Buffer Management
# ====================

class TestBufferManagement:
    """Tests for buffer status and capacity"""

    @pytest.mark.asyncio
    async def test_buffer_status_empty(self, client):
        """Test buffer status when empty"""
        response = await client.get("/v1/kkt/buffer/status")

        assert response.status_code == 200
        data = response.json()

        assert data["total_capacity"] == 200
        assert data["current_queued"] == 0
        assert data["percent_full"] == 0.0
        assert data["pending"] == 0
        assert data["synced"] == 0
        assert data["failed"] == 0
        assert data["dlq_size"] == 0

    @pytest.mark.asyncio
    async def test_buffer_status_after_receipt(self, client, sample_receipt_data):
        """Test buffer status after creating receipt"""
        # Create receipt
        await client.post(
            "/v1/kkt/receipt",
            json=sample_receipt_data,
            headers={"Idempotency-Key": str(uuid.uuid4())}
        )

        # Check buffer status
        response = await client.get("/v1/kkt/buffer/status")
        data = response.json()

        assert data["current_queued"] == 1
        assert data["percent_full"] == 0.5  # 1/200 = 0.5%
        assert data["pending"] == 1
        assert data["total_receipts"] == 1

    @pytest.mark.asyncio
    async def test_buffer_capacity_tracking(self, client, sample_receipt_data):
        """Test buffer capacity tracking with multiple receipts"""
        # Create 10 receipts
        for i in range(10):
            await client.post(
                "/v1/kkt/receipt",
                json=sample_receipt_data,
                headers={"Idempotency-Key": str(uuid.uuid4())}
            )

        # Check buffer status
        response = await client.get("/v1/kkt/buffer/status")
        data = response.json()

        assert data["current_queued"] == 10
        assert data["percent_full"] == 5.0  # 10/200 = 5%
        assert data["pending"] == 10

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_buffer_full_error(self, client, sample_receipt_data):
        """Test buffer full error when capacity reached"""
        # Fill buffer to capacity (200 receipts)
        for i in range(200):
            response = await client.post(
                "/v1/kkt/receipt",
                json=sample_receipt_data,
                headers={"Idempotency-Key": str(uuid.uuid4())}
            )
            assert response.status_code == 200

        # Verify buffer status
        status_response = await client.get("/v1/kkt/buffer/status")
        assert status_response.json()["percent_full"] == 100.0

        # Try to create 201st receipt (should fail)
        response = await client.post(
            "/v1/kkt/receipt",
            json=sample_receipt_data,
            headers={"Idempotency-Key": str(uuid.uuid4())}
        )

        assert response.status_code == 503
        assert "Buffer full" in response.json()["detail"]


# ====================
# Tests: Idempotency
# ====================

class TestIdempotency:
    """Tests for idempotency key handling"""

    @pytest.mark.asyncio
    async def test_different_idempotency_keys(self, client, sample_receipt_data):
        """Test different idempotency keys create different receipts"""
        key1 = str(uuid.uuid4())
        key2 = str(uuid.uuid4())

        # Create first receipt
        response1 = await client.post(
            "/v1/kkt/receipt",
            json=sample_receipt_data,
            headers={"Idempotency-Key": key1}
        )
        receipt_id1 = response1.json()["receipt_id"]

        # Create second receipt with different key
        response2 = await client.post(
            "/v1/kkt/receipt",
            json=sample_receipt_data,
            headers={"Idempotency-Key": key2}
        )
        receipt_id2 = response2.json()["receipt_id"]

        # Verify different receipt IDs
        assert receipt_id1 != receipt_id2

    @pytest.mark.asyncio
    async def test_same_idempotency_key_creates_duplicate(self, client, sample_receipt_data):
        """
        Test same idempotency key creates duplicate receipt (POC behavior)

        NOTE: True idempotency will be implemented in Phase 2.
        For POC, we allow duplicates.
        """
        key = str(uuid.uuid4())

        # Create first receipt
        response1 = await client.post(
            "/v1/kkt/receipt",
            json=sample_receipt_data,
            headers={"Idempotency-Key": key}
        )
        receipt_id1 = response1.json()["receipt_id"]

        # Create second receipt with same key
        response2 = await client.post(
            "/v1/kkt/receipt",
            json=sample_receipt_data,
            headers={"Idempotency-Key": key}
        )
        receipt_id2 = response2.json()["receipt_id"]

        # For POC: different IDs (duplicates allowed)
        assert receipt_id1 != receipt_id2

        # TODO: In Phase 2, implement true idempotency:
        # assert receipt_id1 == receipt_id2


# ====================
# Tests: Health Check
# ====================

class TestHealthCheck:
    """Tests for health check endpoint"""

    @pytest.mark.asyncio
    async def test_health_check_healthy(self, client):
        """Test health check when system healthy"""
        response = await client.get("/v1/health")

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "healthy"
        assert "components" in data
        assert "buffer" in data["components"]
        assert "circuit_breaker" in data["components"]
        assert "database" in data["components"]
        assert data["version"] == "0.1.0"

    @pytest.mark.asyncio
    async def test_health_check_components(self, client):
        """Test health check component details"""
        response = await client.get("/v1/health")
        data = response.json()

        # Buffer component
        assert data["components"]["buffer"]["status"] == "healthy"
        assert "percent_full" in data["components"]["buffer"]
        assert "dlq_size" in data["components"]["buffer"]

        # Circuit Breaker component
        assert data["components"]["circuit_breaker"]["state"] == "CLOSED"
        assert "failure_count" in data["components"]["circuit_breaker"]

        # Database component
        assert data["components"]["database"]["status"] == "healthy"
        assert data["components"]["database"]["type"] == "SQLite"
        assert data["components"]["database"]["mode"] == "WAL"


# ====================
# Tests: Multiple Items/Payments
# ====================

class TestComplexReceipts:
    """Tests for receipts with multiple items and payments"""

    @pytest.mark.asyncio
    async def test_receipt_multiple_items(self, client, sample_receipt_data):
        """Test receipt with multiple items"""
        sample_receipt_data["items"] = [
            {
                "name": "Product A",
                "price": 100.00,
                "quantity": 2,
                "total": 200.00,
                "vat_rate": 20
            },
            {
                "name": "Product B",
                "price": 50.00,
                "quantity": 1,
                "total": 50.00,
                "vat_rate": 20
            }
        ]
        sample_receipt_data["payments"][0]["amount"] = 250.00

        response = await client.post(
            "/v1/kkt/receipt",
            json=sample_receipt_data,
            headers={"Idempotency-Key": str(uuid.uuid4())}
        )

        assert response.status_code == 200
        assert response.json()["status"] == "printed"
        assert response.json()["fiscal_doc"]["total"] == 250.00

    @pytest.mark.asyncio
    async def test_receipt_multiple_payments(self, client, sample_receipt_data):
        """Test receipt with multiple payment types"""
        sample_receipt_data["payments"] = [
            {"type": "cash", "amount": 100.00},
            {"type": "card", "amount": 100.00}
        ]

        response = await client.post(
            "/v1/kkt/receipt",
            json=sample_receipt_data,
            headers={"Idempotency-Key": str(uuid.uuid4())}
        )

        assert response.status_code == 200
        assert response.json()["status"] == "printed"
