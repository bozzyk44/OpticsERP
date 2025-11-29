# tests/unit/pos_monitor/test_alerts.py
"""Unit tests for POS Monitor alerts module"""
import pytest
import sqlite3
from pos_monitor.app.alerts import check_alerts, get_kkt_status


@pytest.mark.unit
@pytest.mark.pos_monitor
def test_check_alerts_no_issues(mock_buffer_db, monkeypatch):
    """Test alert checking with no issues"""
    # Mock KKT Adapter as healthy
    import requests

    class MockResponse:
        status_code = 200

        def json(self):
            return {"circuit_breaker_state": "CLOSED"}

    def mock_get(*args, **kwargs):
        return MockResponse()

    monkeypatch.setattr(requests, 'get', mock_get)

    alerts = check_alerts()

    # No alerts expected (buffer at 1.5%, DLQ has 1 entry which triggers P1)
    # Actually, DLQ > 0 should trigger P1 alert
    p1_alerts = [a for a in alerts if a.level == "P1"]
    assert len(p1_alerts) == 1
    assert "DLQ" in p1_alerts[0].message or "Ошибки отправки" in p1_alerts[0].message


@pytest.mark.unit
@pytest.mark.pos_monitor
def test_check_alerts_buffer_warning(mock_buffer_db, monkeypatch):
    """Test buffer warning alert (80% threshold)"""
    # Mock buffer with 160 pending receipts (80% of 200)
    def mock_get_buffer_status():
        return {
            "pending": 160,
            "dlq": 0,
            "percent_full": 80.0,
            "last_sync": None
        }

    monkeypatch.setattr('pos_monitor.app.alerts.get_buffer_status', mock_get_buffer_status)

    # Mock KKT Adapter as healthy
    import requests

    class MockResponse:
        status_code = 200

        def json(self):
            return {"circuit_breaker_state": "CLOSED"}

    def mock_get(*args, **kwargs):
        return MockResponse()

    monkeypatch.setattr(requests, 'get', mock_get)

    alerts = check_alerts()

    # Should have P2 alert for buffer warning
    p2_alerts = [a for a in alerts if a.level == "P2"]
    assert len(p2_alerts) >= 1

    buffer_alert = next((a for a in p2_alerts if "Буфер" in a.message), None)
    assert buffer_alert is not None
    assert "160" in buffer_alert.message
    assert "80" in buffer_alert.message


@pytest.mark.unit
@pytest.mark.pos_monitor
def test_check_alerts_buffer_critical(mock_buffer_db, monkeypatch):
    """Test buffer critical alert (100% threshold)"""
    # Mock buffer with 200 pending receipts (100% of 200)
    def mock_get_buffer_status():
        return {
            "pending": 200,
            "dlq": 0,
            "percent_full": 100.0,
            "last_sync": None
        }

    monkeypatch.setattr('pos_monitor.app.alerts.get_buffer_status', mock_get_buffer_status)

    # Mock KKT Adapter as healthy
    import requests

    class MockResponse:
        status_code = 200

        def json(self):
            return {"circuit_breaker_state": "CLOSED"}

    def mock_get(*args, **kwargs):
        return MockResponse()

    monkeypatch.setattr(requests, 'get', mock_get)

    alerts = check_alerts()

    # Should have P1 alert for buffer critical
    p1_alerts = [a for a in alerts if a.level == "P1"]
    assert len(p1_alerts) >= 1

    buffer_alert = next((a for a in p1_alerts if "переполнен" in a.message), None)
    assert buffer_alert is not None
    assert "200" in buffer_alert.message
    assert "100" in buffer_alert.message


@pytest.mark.unit
@pytest.mark.pos_monitor
def test_check_alerts_dlq_warning(mock_buffer_db, monkeypatch):
    """Test DLQ alert (DLQ > 0)"""
    # Mock buffer with DLQ entries
    def mock_get_buffer_status():
        return {
            "pending": 10,
            "dlq": 5,
            "percent_full": 5.0,
            "last_sync": None
        }

    monkeypatch.setattr('pos_monitor.app.alerts.get_buffer_status', mock_get_buffer_status)

    # Mock KKT Adapter as healthy
    import requests

    class MockResponse:
        status_code = 200

        def json(self):
            return {"circuit_breaker_state": "CLOSED"}

    def mock_get(*args, **kwargs):
        return MockResponse()

    monkeypatch.setattr(requests, 'get', mock_get)

    alerts = check_alerts()

    # Should have P1 alert for DLQ
    p1_alerts = [a for a in alerts if a.level == "P1"]
    dlq_alert = next((a for a in p1_alerts if "DLQ" in a.message or "Ошибки отправки" in a.message), None)

    assert dlq_alert is not None
    assert "5" in dlq_alert.message


@pytest.mark.unit
@pytest.mark.pos_monitor
def test_check_alerts_kkt_adapter_offline(mock_kkt_adapter_offline, mock_buffer_db, monkeypatch):
    """Test KKT Adapter offline alert"""
    # Mock buffer as healthy
    def mock_get_buffer_status():
        return {
            "pending": 10,
            "dlq": 1,  # Keep DLQ from mock_buffer_db
            "percent_full": 5.0,
            "last_sync": None
        }

    monkeypatch.setattr('pos_monitor.app.alerts.get_buffer_status', mock_get_buffer_status)

    alerts = check_alerts()

    # Should have P1 alert for KKT Adapter offline
    p1_alerts = [a for a in alerts if a.level == "P1"]
    kkt_alert = next((a for a in p1_alerts if "ККТ Adapter" in a.message), None)

    assert kkt_alert is not None
    assert "не отвечает" in kkt_alert.message


@pytest.mark.unit
@pytest.mark.pos_monitor
def test_check_alerts_circuit_breaker_open(mock_kkt_adapter_online_cb_open, mock_buffer_db, monkeypatch):
    """Test Circuit Breaker OPEN alert"""
    # Mock buffer as healthy
    def mock_get_buffer_status():
        return {
            "pending": 10,
            "dlq": 1,  # Keep DLQ from mock_buffer_db
            "percent_full": 5.0,
            "last_sync": None
        }

    monkeypatch.setattr('pos_monitor.app.alerts.get_buffer_status', mock_get_buffer_status)

    alerts = check_alerts()

    # Should have P2 alert for Circuit Breaker OPEN
    p2_alerts = [a for a in alerts if a.level == "P2"]
    cb_alert = next((a for a in p2_alerts if "ОФД" in a.message and "OPEN" in a.message), None)

    assert cb_alert is not None
    assert "недоступен" in cb_alert.message


@pytest.mark.unit
@pytest.mark.pos_monitor
def test_get_kkt_status_online(monkeypatch):
    """Test KKT status retrieval when online"""
    import requests

    class MockResponse:
        status_code = 200

        def json(self):
            return {"circuit_breaker_state": "CLOSED"}

    def mock_get(*args, **kwargs):
        return MockResponse()

    monkeypatch.setattr(requests, 'get', mock_get)

    status = get_kkt_status()

    assert status['is_online'] is True
    assert status['circuit_breaker_state'] == 'CLOSED'
    assert status['ofd_status'] == 'online'
    assert 'last_heartbeat' in status


@pytest.mark.unit
@pytest.mark.pos_monitor
def test_get_kkt_status_offline(mock_kkt_adapter_offline):
    """Test KKT status retrieval when offline"""
    status = get_kkt_status()

    assert status['is_online'] is False
    assert status['circuit_breaker_state'] == 'UNKNOWN'
    assert status['ofd_status'] == 'unknown'
    assert 'last_heartbeat' in status


@pytest.mark.unit
@pytest.mark.pos_monitor
def test_get_kkt_status_cb_open(mock_kkt_adapter_online_cb_open):
    """Test KKT status with Circuit Breaker OPEN"""
    status = get_kkt_status()

    assert status['is_online'] is True
    assert status['circuit_breaker_state'] == 'OPEN'
    assert status['ofd_status'] == 'offline'
