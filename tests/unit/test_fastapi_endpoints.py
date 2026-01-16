"""
Unit Tests for FastAPI KKT Adapter Endpoints

Author: AI Agent
Created: 2025-10-08
Purpose: Comprehensive unit tests for all FastAPI endpoints

Test Coverage:
- POST /v1/kkt/receipt - Receipt creation with two-phase fiscalization
- GET /v1/kkt/buffer/status - Buffer status and metrics
- GET /v1/health - Health check and component status
- GET / - Root endpoint
- Pydantic validation
- Error handling
- Idempotency

Reference: OPTERP-7
"""

import pytest
import pytest_asyncio
import sys
import uuid
from pathlib import Path
from httpx import AsyncClient

# Add kkt_adapter/app to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'kkt_adapter' / 'app'))

from main import app
import buffer as buf_module


# ====================
# Fixtures
# ====================

@pytest.fixture(scope="function")
def clean_database():
    """
    Initialize clean in-memory database for each test

    This fixture ensures each test starts with a fresh database state.
    Uses :memory: database to avoid file system dependencies.
    """
    # Reset HLC state
    from hlc import reset_hlc
    reset_hlc()

    # Close any existing connection
    buf_module._db_connection = None

    # Initialize in-memory database
    conn = buf_module.init_buffer_db(':memory:')

    # Load schema manually for :memory: database
    schema_path = Path(__file__).parent.parent.parent / 'bootstrap' / 'kkt_adapter_skeleton' / 'schema.sql'
    if schema_path.exists():
        with open(schema_path, 'r', encoding='utf-8') as f:
            schema_sql = f.read()
            conn.executescript(schema_sql)
            conn.commit()

    # Set global connection
    buf_module._db_connection = conn

    yield conn

    # Cleanup
    buf_module.close_buffer_db()
    buf_module._db_connection = None


@pytest_asyncio.fixture(scope="function")
async def client(clean_database):
    """
    Async HTTP client for FastAPI testing

    Uses httpx.AsyncClient with TestClient-like interface.
    Base URL is set to http://test for testing.
    """
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def valid_receipt_data():
    """
    Valid receipt data for testing

    Returns a dictionary with valid receipt data that passes all
    Pydantic validation rules.
    """
    return {
        "pos_id": "POS-001",
        "type": "sale",
        "items": [
            {
                "name": "Product A",
                "price": 100.00,
                "quantity": 2,
                "total": 200.00,
                "vat_rate": 20
            }
        ],
        "payments": [
            {
                "type": "cash",
                "amount": 200.00
            }
        ]
    }


# ====================
# Tests: POST /v1/kkt/receipt
# ====================

class TestCreateReceipt:
    """Tests for POST /v1/kkt/receipt endpoint"""

    @pytest.mark.asyncio
    async def test_create_receipt_success(self, client, valid_receipt_data):
        """Test successful receipt creation with KKT printing"""
        response = await client.post(
            "/v1/kkt/receipt",
            json=valid_receipt_data,
            headers={"Idempotency-Key": str(uuid.uuid4())}
        )

        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "printed"  # Phase 1: now prints on KKT
        assert "receipt_id" in data
        assert data["fiscal_doc"] is not None  # Now populated after print
        assert "fiscal_doc_number" in data["fiscal_doc"]
        assert "fiscal_sign" in data["fiscal_doc"]
        assert data["message"] == "Receipt printed successfully"

        # Verify receipt_id is a valid UUID
        try:
            uuid.UUID(data["receipt_id"])
        except ValueError:
            pytest.fail("receipt_id is not a valid UUID")

    @pytest.mark.asyncio
    async def test_create_receipt_missing_idempotency_key(self, client, valid_receipt_data):
        """Test receipt creation without Idempotency-Key header"""
        response = await client.post("/v1/kkt/receipt", json=valid_receipt_data)

        assert response.status_code == 422  # Validation error
        data = response.json()
        assert "detail" in data

    @pytest.mark.asyncio
    async def test_create_receipt_invalid_type(self, client, valid_receipt_data):
        """Test receipt creation with invalid type"""
        valid_receipt_data["type"] = "invalid_type"

        response = await client.post(
            "/v1/kkt/receipt",
            json=valid_receipt_data,
            headers={"Idempotency-Key": str(uuid.uuid4())}
        )

        assert response.status_code == 422
        data = response.json()
        assert "detail" in data

    @pytest.mark.asyncio
    async def test_create_receipt_empty_items(self, client, valid_receipt_data):
        """Test receipt creation with empty items list"""
        valid_receipt_data["items"] = []

        response = await client.post(
            "/v1/kkt/receipt",
            json=valid_receipt_data,
            headers={"Idempotency-Key": str(uuid.uuid4())}
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_create_receipt_invalid_total(self, client, valid_receipt_data):
        """Test receipt creation with mismatched item total"""
        valid_receipt_data["items"][0]["total"] = 999.99  # Should be 200.00

        response = await client.post(
            "/v1/kkt/receipt",
            json=valid_receipt_data,
            headers={"Idempotency-Key": str(uuid.uuid4())}
        )

        assert response.status_code == 422
        data = response.json()
        assert "detail" in data

    @pytest.mark.asyncio
    async def test_create_receipt_payment_mismatch(self, client, valid_receipt_data):
        """Test receipt creation with payments not matching items total"""
        valid_receipt_data["payments"][0]["amount"] = 100.00  # Should be 200.00

        response = await client.post(
            "/v1/kkt/receipt",
            json=valid_receipt_data,
            headers={"Idempotency-Key": str(uuid.uuid4())}
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_create_receipt_negative_price(self, client, valid_receipt_data):
        """Test receipt creation with negative price"""
        valid_receipt_data["items"][0]["price"] = -100.00
        valid_receipt_data["items"][0]["total"] = -200.00

        response = await client.post(
            "/v1/kkt/receipt",
            json=valid_receipt_data,
            headers={"Idempotency-Key": str(uuid.uuid4())}
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_create_receipt_multiple_payments(self, client, valid_receipt_data):
        """Test receipt creation with multiple payment methods"""
        valid_receipt_data["payments"] = [
            {"type": "cash", "amount": 100.00},
            {"type": "card", "amount": 100.00}
        ]

        response = await client.post(
            "/v1/kkt/receipt",
            json=valid_receipt_data,
            headers={"Idempotency-Key": str(uuid.uuid4())}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "printed"

    @pytest.mark.asyncio
    async def test_create_receipt_multiple_items(self, client, valid_receipt_data):
        """Test receipt creation with multiple items"""
        valid_receipt_data["items"] = [
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
                "vat_rate": 10
            }
        ]
        valid_receipt_data["payments"] = [
            {"type": "cash", "amount": 250.00}
        ]

        response = await client.post(
            "/v1/kkt/receipt",
            json=valid_receipt_data,
            headers={"Idempotency-Key": str(uuid.uuid4())}
        )

        assert response.status_code == 200


# ====================
# Tests: GET /v1/kkt/buffer/status
# ====================

class TestBufferStatus:
    """Tests for GET /v1/kkt/buffer/status endpoint"""

    @pytest.mark.asyncio
    async def test_buffer_status_empty(self, client):
        """Test buffer status with empty buffer"""
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
    async def test_buffer_status_with_receipts(self, client, valid_receipt_data):
        """Test buffer status after adding receipts"""
        # Add receipt
        await client.post(
            "/v1/kkt/receipt",
            json=valid_receipt_data,
            headers={"Idempotency-Key": str(uuid.uuid4())}
        )

        # Check status
        response = await client.get("/v1/kkt/buffer/status")

        assert response.status_code == 200

        data = response.json()
        assert data["current_queued"] == 1
        assert data["pending"] == 1
        assert data["total_receipts"] == 1
        assert data["percent_full"] > 0
        assert data["percent_full"] == 0.5  # 1 / 200 * 100

    @pytest.mark.asyncio
    async def test_buffer_status_network_detection(self, client):
        """Test network status detection in buffer status"""
        response = await client.get("/v1/kkt/buffer/status")

        assert response.status_code == 200

        data = response.json()
        assert "network_status" in data
        assert data["network_status"] in ["online", "offline", "degraded"]

        # With empty buffer and no synced receipts, should be offline
        assert data["network_status"] == "offline"


# ====================
# Tests: GET /v1/health
# ====================

class TestHealthCheck:
    """Tests for GET /v1/health endpoint"""

    @pytest.mark.asyncio
    async def test_health_check_healthy(self, client):
        """Test health check when system is healthy"""
        response = await client.get("/v1/health")

        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "healthy"
        assert "components" in data
        assert "buffer" in data["components"]
        assert "circuit_breaker" in data["components"]
        assert "database" in data["components"]

    @pytest.mark.asyncio
    async def test_health_check_components(self, client):
        """Test health check component details"""
        response = await client.get("/v1/health")

        data = response.json()

        buffer = data["components"]["buffer"]
        assert buffer["status"] == "healthy"
        assert "percent_full" in buffer
        assert "dlq_size" in buffer
        assert "pending" in buffer
        assert buffer["percent_full"] == 0.0
        assert buffer["dlq_size"] == 0

        db = data["components"]["database"]
        assert db["status"] == "healthy"
        assert db["type"] == "SQLite"
        assert db["mode"] == "WAL"

    @pytest.mark.asyncio
    async def test_health_check_version(self, client):
        """Test health check includes version"""
        response = await client.get("/v1/health")

        data = response.json()
        assert data["version"] == "0.1.0"


# ====================
# Tests: GET /
# ====================

class TestRootEndpoint:
    """Tests for GET / root endpoint"""

    @pytest.mark.asyncio
    async def test_root_endpoint(self, client):
        """Test root endpoint returns API information"""
        response = await client.get("/")

        assert response.status_code == 200

        data = response.json()
        assert data["message"] == "KKT Adapter API"
        assert data["version"] == "0.1.0"
        assert data["docs"] == "/docs"
        assert data["health"] == "/v1/health"
        assert data["status"] == "operational"


# ====================
# Tests: Idempotency
# ====================

class TestIdempotency:
    """Tests for idempotency handling"""

    @pytest.mark.asyncio
    async def test_idempotency_different_keys(self, client, valid_receipt_data):
        """Test that different idempotency keys create different receipts"""
        key1 = str(uuid.uuid4())
        key2 = str(uuid.uuid4())

        response1 = await client.post(
            "/v1/kkt/receipt",
            json=valid_receipt_data,
            headers={"Idempotency-Key": key1}
        )
        response2 = await client.post(
            "/v1/kkt/receipt",
            json=valid_receipt_data,
            headers={"Idempotency-Key": key2}
        )

        assert response1.status_code == 200
        assert response2.status_code == 200

        receipt_id_1 = response1.json()["receipt_id"]
        receipt_id_2 = response2.json()["receipt_id"]

        assert receipt_id_1 != receipt_id_2

    @pytest.mark.asyncio
    async def test_idempotency_same_key_creates_duplicate(self, client, valid_receipt_data):
        """
        Test that same idempotency key creates duplicate receipts

        Note: Current implementation doesn't enforce idempotency at API level.
        This test documents current behavior. In future, same idempotency key
        should return the same receipt_id (idempotent).

        TODO (OPTERP-8): Implement proper idempotency enforcement
        """
        idem_key = str(uuid.uuid4())

        response1 = await client.post(
            "/v1/kkt/receipt",
            json=valid_receipt_data,
            headers={"Idempotency-Key": idem_key}
        )
        response2 = await client.post(
            "/v1/kkt/receipt",
            json=valid_receipt_data,
            headers={"Idempotency-Key": idem_key}
        )

        assert response1.status_code == 200
        assert response2.status_code == 200

        receipt_id_1 = response1.json()["receipt_id"]
        receipt_id_2 = response2.json()["receipt_id"]

        # Currently creates duplicate (will change when idempotency is enforced)
        assert receipt_id_1 != receipt_id_2


# ====================
# Tests: Error Handling
# ====================

class TestErrorHandling:
    """Tests for error handling"""

    @pytest.mark.asyncio
    async def test_malformed_json(self, client):
        """Test handling of malformed JSON"""
        response = await client.post(
            "/v1/kkt/receipt",
            content="{invalid json}",
            headers={
                "Content-Type": "application/json",
                "Idempotency-Key": str(uuid.uuid4())
            }
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_missing_required_fields(self, client):
        """Test handling of missing required fields"""
        incomplete_data = {
            "pos_id": "POS-001"
            # Missing: type, items, payments
        }

        response = await client.post(
            "/v1/kkt/receipt",
            json=incomplete_data,
            headers={"Idempotency-Key": str(uuid.uuid4())}
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_invalid_vat_rate(self, client, valid_receipt_data):
        """Test handling of invalid VAT rate"""
        valid_receipt_data["items"][0]["vat_rate"] = 999  # Should be 0-20

        response = await client.post(
            "/v1/kkt/receipt",
            json=valid_receipt_data,
            headers={"Idempotency-Key": str(uuid.uuid4())}
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_nonexistent_endpoint(self, client):
        """Test handling of requests to nonexistent endpoints"""
        response = await client.get("/v1/nonexistent")

        assert response.status_code == 404
