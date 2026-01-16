# tests/unit/pos_monitor/conftest.py
"""Pytest fixtures for POS Monitor unit tests"""
import pytest
import sqlite3
import tempfile
import sys
from pathlib import Path
from datetime import date

# Add pos_monitor to Python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / 'pos_monitor'))


@pytest.fixture
def mock_buffer_db(monkeypatch):
    """
    Create a temporary buffer.db for testing

    Creates tables and inserts test data
    """
    # Create temporary database
    temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
    temp_db_path = Path(temp_db.name)
    temp_db.close()

    # Initialize database with schema
    conn = sqlite3.connect(str(temp_db_path))
    cursor = conn.cursor()

    # Create pos_sessions table
    cursor.execute("""
        CREATE TABLE pos_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pos_id TEXT NOT NULL,
            status TEXT NOT NULL,
            cash_balance REAL DEFAULT 0,
            card_balance REAL DEFAULT 0,
            opened_at INTEGER NOT NULL,
            closed_at INTEGER
        )
    """)

    # Create receipts table
    cursor.execute("""
        CREATE TABLE receipts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fiscal_doc_id TEXT UNIQUE NOT NULL,
            pos_id TEXT NOT NULL,
            type TEXT NOT NULL,
            total REAL NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            created_at TEXT NOT NULL,
            synced_at INTEGER
        )
    """)

    # Create dlq table
    cursor.execute("""
        CREATE TABLE dlq (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fiscal_doc_id TEXT NOT NULL,
            error TEXT,
            moved_at INTEGER NOT NULL
        )
    """)

    # Insert test data - open POS session
    cursor.execute("""
        INSERT INTO pos_sessions (pos_id, status, cash_balance, card_balance, opened_at)
        VALUES ('POS-001', 'open', 5000.0, 12000.0, strftime('%s', 'now'))
    """)

    # Insert test receipts
    today = date.today().isoformat()
    cursor.execute(f"""
        INSERT INTO receipts (fiscal_doc_id, pos_id, type, total, status, created_at, synced_at)
        VALUES
            ('REC-001', 'POS-001', 'sale', 1000.0, 'synced', '{today} 10:00:00', strftime('%s', 'now')),
            ('REC-002', 'POS-001', 'sale', 1500.0, 'synced', '{today} 11:00:00', strftime('%s', 'now')),
            ('REC-003', 'POS-001', 'sale', 2000.0, 'pending', '{today} 12:00:00', NULL),
            ('REC-004', 'POS-001', 'sale', 2500.0, 'pending', '{today} 13:00:00', NULL),
            ('REC-005', 'POS-001', 'sale', 1200.0, 'pending', '{today} 14:00:00', NULL)
    """)

    # Insert DLQ record
    cursor.execute("""
        INSERT INTO dlq (fiscal_doc_id, error, moved_at)
        VALUES ('REC-FAILED', 'OFD timeout after 20 retries', strftime('%s', 'now'))
    """)

    conn.commit()
    conn.close()

    # Monkeypatch BUFFER_DB_PATH
    monkeypatch.setattr('app.config.BUFFER_DB_PATH', str(temp_db_path))
    monkeypatch.setattr('app.database.BUFFER_DB_PATH', str(temp_db_path))

    yield temp_db_path

    # Cleanup
    try:
        temp_db_path.unlink()
    except:
        pass


@pytest.fixture
def mock_kkt_adapter_offline(monkeypatch):
    """Mock KKT Adapter as offline (for alert testing)"""
    import requests

    def mock_get(*args, **kwargs):
        raise requests.exceptions.ConnectionError("KKT Adapter offline")

    monkeypatch.setattr(requests, 'get', mock_get)


@pytest.fixture
def mock_kkt_adapter_online_cb_open(monkeypatch):
    """Mock KKT Adapter online but Circuit Breaker OPEN"""
    import requests

    class MockResponse:
        status_code = 200

        def json(self):
            return {"circuit_breaker_state": "OPEN"}

    def mock_get(url, *args, **kwargs):
        if '/health' in url:
            return MockResponse()
        elif '/v1/health' in url:
            return MockResponse()
        raise requests.exceptions.ConnectionError("Unexpected URL")

    monkeypatch.setattr(requests, 'get', mock_get)


@pytest.fixture
def empty_buffer_db(monkeypatch):
    """Create empty buffer.db (no sessions, no receipts)"""
    temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
    temp_db_path = Path(temp_db.name)
    temp_db.close()

    conn = sqlite3.connect(str(temp_db_path))
    cursor = conn.cursor()

    # Create empty tables
    cursor.execute("""
        CREATE TABLE pos_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pos_id TEXT NOT NULL,
            status TEXT NOT NULL,
            cash_balance REAL DEFAULT 0,
            card_balance REAL DEFAULT 0,
            opened_at INTEGER NOT NULL,
            closed_at INTEGER
        )
    """)

    cursor.execute("""
        CREATE TABLE receipts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fiscal_doc_id TEXT UNIQUE NOT NULL,
            pos_id TEXT NOT NULL,
            type TEXT NOT NULL,
            total REAL NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            created_at TEXT NOT NULL,
            synced_at INTEGER
        )
    """)

    cursor.execute("""
        CREATE TABLE dlq (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fiscal_doc_id TEXT NOT NULL,
            error TEXT,
            moved_at INTEGER NOT NULL
        )
    """)

    conn.commit()
    conn.close()

    monkeypatch.setattr('app.config.BUFFER_DB_PATH', str(temp_db_path))
    monkeypatch.setattr('app.database.BUFFER_DB_PATH', str(temp_db_path))

    yield temp_db_path

    try:
        temp_db_path.unlink()
    except:
        pass
