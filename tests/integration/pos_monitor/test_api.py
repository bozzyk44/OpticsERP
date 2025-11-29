# tests/integration/pos_monitor/test_api.py
"""Integration tests for POS Monitor API endpoints"""
import pytest
from fastapi.testclient import TestClient
import sys
from pathlib import Path

# Add pos_monitor to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / 'pos_monitor'))

from app.main import app


@pytest.fixture
def client(mock_buffer_db):
    """Create TestClient with mocked database"""
    return TestClient(app)


@pytest.mark.integration
@pytest.mark.pos_monitor
def test_health_endpoint(client):
    """Test /health endpoint"""
    response = client.get("/health")

    assert response.status_code == 200

    data = response.json()
    assert 'status' in data
    assert 'timestamp' in data
    assert 'buffer_accessible' in data

    assert data['status'] == 'ok'
    assert data['buffer_accessible'] is True


@pytest.mark.integration
@pytest.mark.pos_monitor
def test_get_status_endpoint(client, monkeypatch):
    """Test /api/v1/status endpoint"""
    # Mock KKT Adapter as healthy
    import requests

    class MockResponse:
        status_code = 200

        def json(self):
            return {"circuit_breaker_state": "CLOSED"}

    def mock_get(*args, **kwargs):
        return MockResponse()

    monkeypatch.setattr(requests, 'get', mock_get)

    response = client.get("/api/v1/status")

    assert response.status_code == 200

    data = response.json()
    assert 'cash_balance' in data
    assert 'card_balance' in data
    assert 'buffer' in data
    assert 'kkt_status' in data
    assert 'timestamp' in data

    # From mock_buffer_db
    assert data['cash_balance'] == 5000.0
    assert data['card_balance'] == 12000.0

    # Buffer should have pending receipts
    assert data['buffer']['pending'] == 3
    assert data['buffer']['dlq'] == 1
    assert data['buffer']['percent_full'] == 1.5

    # KKT status
    assert data['kkt_status']['is_online'] is True
    assert data['kkt_status']['circuit_breaker_state'] == 'CLOSED'


@pytest.mark.integration
@pytest.mark.pos_monitor
def test_get_alerts_endpoint(client, monkeypatch):
    """Test /api/v1/alerts endpoint"""
    # Mock KKT Adapter as healthy
    import requests

    class MockResponse:
        status_code = 200

        def json(self):
            return {"circuit_breaker_state": "CLOSED"}

    def mock_get(*args, **kwargs):
        return MockResponse()

    monkeypatch.setattr(requests, 'get', mock_get)

    response = client.get("/api/v1/alerts")

    assert response.status_code == 200

    data = response.json()
    assert isinstance(data, list)

    # Should have at least 1 alert (DLQ > 0 from mock_buffer_db)
    assert len(data) >= 1

    # Check alert structure
    alert = data[0]
    assert 'level' in alert
    assert 'message' in alert
    assert 'action' in alert
    assert 'timestamp' in alert

    # DLQ alert should be P1
    dlq_alert = next((a for a in data if "DLQ" in a['message'] or "Ошибки" in a['message']), None)
    assert dlq_alert is not None
    assert dlq_alert['level'] == 'P1'


@pytest.mark.integration
@pytest.mark.pos_monitor
def test_get_sales_today_endpoint(client):
    """Test /api/v1/sales/today endpoint"""
    response = client.get("/api/v1/sales/today")

    assert response.status_code == 200

    data = response.json()
    assert 'total_revenue' in data
    assert 'total_count' in data
    assert 'hourly_data' in data
    assert 'date' in data

    # From mock_buffer_db: 5 receipts (1000 + 1500 + 2000 + 2500 + 1200 = 8200)
    assert data['total_revenue'] == 8200.0
    assert data['total_count'] == 5

    # Hourly data should have 5 entries
    assert len(data['hourly_data']) == 5


@pytest.mark.integration
@pytest.mark.pos_monitor
def test_api_docs_accessible(client):
    """Test API documentation endpoints are accessible"""
    # OpenAPI JSON
    response = client.get("/openapi.json")
    assert response.status_code == 200

    # Swagger UI
    response = client.get("/api/docs")
    assert response.status_code == 200

    # ReDoc
    response = client.get("/api/redoc")
    assert response.status_code == 200


@pytest.mark.integration
@pytest.mark.pos_monitor
def test_status_endpoint_with_missing_db(client, monkeypatch):
    """Test /api/v1/status with missing database"""
    # Set non-existent DB path
    monkeypatch.setattr('pos_monitor.app.database.BUFFER_DB_PATH', '/nonexistent/buffer.db')

    response = client.get("/api/v1/status")

    # Should return 503 Service Unavailable
    assert response.status_code == 503

    data = response.json()
    assert 'detail' in data
    assert 'Database not accessible' in data['detail']


@pytest.mark.integration
@pytest.mark.pos_monitor
def test_health_endpoint_with_missing_db(client, monkeypatch):
    """Test /health with missing database (degraded state)"""
    # Set non-existent DB path
    monkeypatch.setattr('pos_monitor.app.database.BUFFER_DB_PATH', '/nonexistent/buffer.db')
    monkeypatch.setattr('pos_monitor.app.config.BUFFER_DB_PATH', '/nonexistent/buffer.db')

    response = client.get("/health")

    assert response.status_code == 200

    data = response.json()
    assert data['status'] == 'degraded'
    assert data['buffer_accessible'] is False


@pytest.mark.integration
@pytest.mark.pos_monitor
@pytest.mark.skip(reason="WebSocket testing requires async client - future enhancement")
def test_websocket_connection():
    """Test WebSocket /ws/realtime endpoint"""
    # TODO: Implement WebSocket testing with httpx AsyncClient
    # from httpx import AsyncClient, ASGITransport
    # This requires async test setup
    pass


@pytest.mark.integration
@pytest.mark.pos_monitor
def test_cors_headers(client):
    """Test CORS headers are present"""
    response = client.get("/api/v1/status", headers={"Origin": "http://localhost:3000"})

    assert "access-control-allow-origin" in response.headers
    assert response.headers["access-control-allow-origin"] == "*"


@pytest.mark.integration
@pytest.mark.pos_monitor
def test_request_logging_middleware(client, caplog):
    """Test that request logging middleware logs requests"""
    import logging

    # Set log level to capture INFO logs
    caplog.set_level(logging.INFO)

    response = client.get("/health")

    assert response.status_code == 200

    # Check logs contain request info
    log_records = [r.message for r in caplog.records]
    health_logs = [log for log in log_records if '/health' in log]

    assert len(health_logs) > 0
