# tests/unit/pos_monitor/test_database.py
"""Unit tests for POS Monitor database module"""
import pytest
from pos_monitor.app.database import (
    get_cash_balance,
    get_buffer_status,
    get_sales_today,
    check_buffer_accessible
)
from datetime import date


@pytest.mark.unit
@pytest.mark.pos_monitor
def test_get_cash_balance_with_open_session(mock_buffer_db):
    """Test cash balance retrieval with open POS session"""
    cash, card = get_cash_balance()

    assert cash == 5000.0
    assert card == 12000.0


@pytest.mark.unit
@pytest.mark.pos_monitor
def test_get_cash_balance_no_open_session(empty_buffer_db):
    """Test cash balance retrieval when no session is open"""
    cash, card = get_cash_balance()

    assert cash == 0.0
    assert card == 0.0


@pytest.mark.unit
@pytest.mark.pos_monitor
def test_get_buffer_status(mock_buffer_db):
    """Test buffer status retrieval"""
    status = get_buffer_status()

    assert 'pending' in status
    assert 'dlq' in status
    assert 'percent_full' in status
    assert 'last_sync' in status

    # From mock data: 3 pending receipts (REC-003, REC-004, REC-005)
    assert status['pending'] == 3

    # From mock data: 1 DLQ entry (REC-FAILED)
    assert status['dlq'] == 1

    # Percent full = (3 / 200) * 100 = 1.5%
    assert status['percent_full'] == 1.5

    # Last sync should exist (REC-001, REC-002 are synced)
    assert status['last_sync'] is not None


@pytest.mark.unit
@pytest.mark.pos_monitor
def test_get_buffer_status_empty(empty_buffer_db):
    """Test buffer status with empty buffer"""
    status = get_buffer_status()

    assert status['pending'] == 0
    assert status['dlq'] == 0
    assert status['percent_full'] == 0.0
    assert status['last_sync'] is None


@pytest.mark.unit
@pytest.mark.pos_monitor
def test_get_sales_today(mock_buffer_db):
    """Test sales data for today"""
    sales = get_sales_today()

    assert 'total_revenue' in sales
    assert 'total_count' in sales
    assert 'hourly_data' in sales
    assert 'date' in sales

    # From mock data: 5 receipts today (1000 + 1500 + 2000 + 2500 + 1200 = 8200)
    assert sales['total_revenue'] == 8200.0
    assert sales['total_count'] == 5

    # Date should be today
    assert sales['date'] == date.today().isoformat()

    # Hourly data should have entries for hours 10, 11, 12, 13, 14
    assert len(sales['hourly_data']) == 5

    # Check hourly breakdown
    hourly_by_hour = {h['hour']: h for h in sales['hourly_data']}

    assert 10 in hourly_by_hour
    assert hourly_by_hour[10]['revenue'] == 1000.0
    assert hourly_by_hour[10]['count'] == 1

    assert 11 in hourly_by_hour
    assert hourly_by_hour[11]['revenue'] == 1500.0

    assert 14 in hourly_by_hour
    assert hourly_by_hour[14]['revenue'] == 1200.0


@pytest.mark.unit
@pytest.mark.pos_monitor
def test_get_sales_today_empty(empty_buffer_db):
    """Test sales data with no receipts"""
    sales = get_sales_today()

    assert sales['total_revenue'] == 0.0
    assert sales['total_count'] == 0
    assert sales['hourly_data'] == []
    assert sales['date'] == date.today().isoformat()


@pytest.mark.unit
@pytest.mark.pos_monitor
def test_check_buffer_accessible(mock_buffer_db):
    """Test buffer accessibility check"""
    assert check_buffer_accessible() is True


@pytest.mark.unit
@pytest.mark.pos_monitor
def test_check_buffer_accessible_missing_db(monkeypatch):
    """Test buffer accessibility with missing database"""
    # Set non-existent path
    monkeypatch.setattr('pos_monitor.app.database.BUFFER_DB_PATH', '/nonexistent/buffer.db')
    monkeypatch.setattr('pos_monitor.app.config.BUFFER_DB_PATH', '/nonexistent/buffer.db')

    assert check_buffer_accessible() is False


@pytest.mark.unit
@pytest.mark.pos_monitor
def test_get_buffer_percent_full_calculation(mock_buffer_db, monkeypatch):
    """Test percent full calculation with different capacities"""
    # Change capacity to 10 for easier testing
    monkeypatch.setattr('pos_monitor.app.database.BUFFER_CAPACITY', 10)

    status = get_buffer_status()

    # 3 pending receipts / 10 capacity = 30%
    assert status['percent_full'] == 30.0


@pytest.mark.unit
@pytest.mark.pos_monitor
def test_read_only_mode(mock_buffer_db):
    """Test that database is opened in read-only mode"""
    from pos_monitor.app.database import get_db
    import sqlite3

    # Attempt to write should fail in read-only mode
    with pytest.raises(sqlite3.OperationalError, match="readonly"):
        with get_db() as conn:
            conn.execute("INSERT INTO receipts (fiscal_doc_id, pos_id, type, total, created_at) VALUES (?, ?, ?, ?, ?)",
                        ('TEST-RO', 'POS-001', 'sale', 100.0, '2025-01-01 00:00:00'))
            conn.commit()
