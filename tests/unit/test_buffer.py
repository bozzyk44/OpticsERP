"""
Unit tests for SQLite Buffer CRUD Operations

Author: AI Agent
Created: 2025-10-08
Purpose: Test buffer.py CRUD operations, thread safety, HLC ordering

Reference: CLAUDE.md §4.1, OPTERP-4

Test Coverage:
- Database initialization (3 tests)
- Insert receipt operations (4 tests)
- Get pending receipts (4 tests)
- Mark synced operations (3 tests)
- Move to DLQ operations (4 tests)
- Buffer status queries (3 tests)
- Helper functions (4 tests)
- Thread safety (2 tests)
- Edge cases (3 tests)

Total: 30 tests targeting ≥95% coverage
"""

import pytest
import sqlite3
import time
import uuid
import json
import threading
from pathlib import Path

# Import buffer module
import sys
sys.path.insert(0, 'kkt_adapter/app')

from buffer import (
    init_buffer_db,
    get_db,
    close_buffer_db,
    insert_receipt,
    get_pending_receipts,
    mark_synced,
    move_to_dlq,
    get_buffer_status,
    update_receipt_status,
    increment_retry_count,
    get_receipt_by_id,
    Receipt,
    BufferStatus,
    BufferFullError,
    ReceiptNotFoundError
)
from hlc import reset_hlc


# ====================
# Pytest Fixtures
# ====================

@pytest.fixture
def in_memory_db():
    """Initialize in-memory database for testing"""
    reset_hlc()
    # Reset global connection
    import buffer as buf_module
    buf_module._db_connection = None

    conn = init_buffer_db(':memory:')

    # Manually execute schema for :memory: database
    schema_sql = Path('bootstrap/kkt_adapter_skeleton/schema.sql').read_text(encoding='utf-8')
    conn.executescript(schema_sql)
    conn.commit()

    # Update global connection
    buf_module._db_connection = conn

    yield conn
    close_buffer_db()
    # Reset again
    buf_module._db_connection = None


@pytest.fixture
def sample_receipt_data():
    """Sample receipt data for testing"""
    return {
        'pos_id': 'POS-001',
        'fiscal_doc': {
            'type': 'sale',
            'total': 1000,
            'items': [{'name': 'Product A', 'price': 1000, 'qty': 1}]
        }
    }


# ====================
# Database Initialization Tests
# ====================

class TestDatabaseInitialization:
    """Test database initialization and schema creation"""

    def test_init_buffer_db_creates_tables(self, in_memory_db):
        """Database initialization creates all required tables"""
        conn = in_memory_db

        cursor = conn.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table'
            ORDER BY name
        """)
        tables = [row[0] for row in cursor.fetchall()]

        assert 'receipts' in tables
        assert 'dlq' in tables
        assert 'buffer_events' in tables
        assert 'config' in tables

    def test_init_buffer_db_pragma_settings(self, in_memory_db):
        """PRAGMA settings are correctly set"""
        conn = in_memory_db

        # Check journal_mode (should be memory for :memory: db)
        cursor = conn.execute("PRAGMA journal_mode")
        journal_mode = cursor.fetchone()[0]
        assert journal_mode in ['wal', 'memory']  # memory mode for :memory: db

        # Check foreign_keys
        cursor = conn.execute("PRAGMA foreign_keys")
        fk_enabled = cursor.fetchone()[0]
        assert fk_enabled == 1

    def test_init_buffer_db_default_config(self, in_memory_db):
        """Config table populated with default values"""
        conn = in_memory_db

        cursor = conn.execute("""
            SELECT key, value FROM config
            ORDER BY key
        """)
        config = {row[0]: row[1] for row in cursor.fetchall()}

        assert config['buffer_capacity'] == '200'
        assert config['circuit_breaker_threshold'] == '5'
        assert config['max_retry_attempts'] == '20'


# ====================
# Insert Receipt Tests
# ====================

class TestInsertReceipt:
    """Test receipt insertion operations"""

    def test_insert_receipt_success(self, in_memory_db, sample_receipt_data):
        """Insert receipt successfully"""
        receipt_id = insert_receipt(sample_receipt_data)

        assert receipt_id is not None
        assert len(receipt_id) == 36  # UUID length with hyphens

        # Verify in database
        receipt = get_receipt_by_id(receipt_id)
        assert receipt is not None
        assert receipt.pos_id == sample_receipt_data['pos_id']
        assert receipt.status == 'pending'
        assert receipt.retry_count == 0

    def test_insert_receipt_generates_uuid(self, in_memory_db, sample_receipt_data):
        """Insert receipt generates valid UUID"""
        receipt_id = insert_receipt(sample_receipt_data)

        # Validate UUID format
        try:
            uuid_obj = uuid.UUID(receipt_id)
            assert str(uuid_obj) == receipt_id
        except ValueError:
            pytest.fail("Invalid UUID format")

    def test_insert_receipt_assigns_hlc(self, in_memory_db, sample_receipt_data):
        """Insert receipt assigns HLC timestamp"""
        receipt_id = insert_receipt(sample_receipt_data)
        receipt = get_receipt_by_id(receipt_id)

        # HLC fields should be populated
        assert receipt.hlc_local_time > 0
        assert receipt.hlc_logical_counter >= 0
        assert receipt.hlc_server_time is None  # Not synced yet

    def test_insert_receipt_capacity_check(self, in_memory_db):
        """BufferFullError raised when capacity reached"""
        # Insert 200 receipts (default capacity)
        for i in range(200):
            insert_receipt({
                'pos_id': f'POS-{i:03d}',
                'fiscal_doc': {'total': 1000}
            })

        # 201st insert should fail
        with pytest.raises(BufferFullError):
            insert_receipt({
                'pos_id': 'POS-201',
                'fiscal_doc': {'total': 1000}
            })


# ====================
# Get Pending Receipts Tests
# ====================

class TestGetPendingReceipts:
    """Test querying pending receipts"""

    def test_get_pending_receipts_empty(self, in_memory_db):
        """Empty buffer returns empty list"""
        pending = get_pending_receipts()
        assert pending == []

    def test_get_pending_receipts_limit(self, in_memory_db):
        """get_pending_receipts respects limit parameter"""
        # Insert 10 receipts
        for i in range(10):
            insert_receipt({
                'pos_id': f'POS-{i}',
                'fiscal_doc': {'total': 1000}
            })

        # Request only 5
        pending = get_pending_receipts(limit=5)
        assert len(pending) == 5

    def test_get_pending_receipts_hlc_ordering(self, in_memory_db):
        """Receipts ordered by HLC (oldest first)"""
        reset_hlc()

        # Insert 5 receipts with small delays to ensure different HLC
        receipt_ids = []
        for i in range(5):
            receipt_id = insert_receipt({
                'pos_id': f'POS-{i}',
                'fiscal_doc': {'total': 1000 * (i+1)}
            })
            receipt_ids.append(receipt_id)
            time.sleep(0.01)  # Small delay to advance time

        # Get pending receipts
        pending = get_pending_receipts(limit=10)

        # Should be in insertion order (HLC is monotonic)
        assert len(pending) == 5
        for i, receipt in enumerate(pending):
            assert receipt.id == receipt_ids[i]

    def test_get_pending_receipts_excludes_synced(self, in_memory_db, sample_receipt_data):
        """get_pending_receipts excludes synced receipts"""
        # Insert 3 receipts
        receipt_ids = []
        for i in range(3):
            receipt_id = insert_receipt({
                'pos_id': f'POS-{i}',
                'fiscal_doc': {'total': 1000}
            })
            receipt_ids.append(receipt_id)

        # Mark first receipt as synced
        mark_synced(receipt_ids[0], server_time=int(time.time()))

        # Get pending
        pending = get_pending_receipts()

        # Should only return 2 pending receipts
        assert len(pending) == 2
        pending_ids = [r.id for r in pending]
        assert receipt_ids[0] not in pending_ids
        assert receipt_ids[1] in pending_ids
        assert receipt_ids[2] in pending_ids


# ====================
# Mark Synced Tests
# ====================

class TestMarkSynced:
    """Test marking receipts as synced"""

    def test_mark_synced_success(self, in_memory_db, sample_receipt_data):
        """Mark receipt as synced successfully"""
        receipt_id = insert_receipt(sample_receipt_data)
        server_time = int(time.time())

        result = mark_synced(receipt_id, server_time)
        assert result == True

        # Verify status changed
        receipt = get_receipt_by_id(receipt_id)
        assert receipt.status == 'synced'
        assert receipt.synced_at is not None

    def test_mark_synced_assigns_server_time(self, in_memory_db, sample_receipt_data):
        """mark_synced assigns hlc_server_time"""
        receipt_id = insert_receipt(sample_receipt_data)
        server_time = 1234567890

        mark_synced(receipt_id, server_time)

        receipt = get_receipt_by_id(receipt_id)
        assert receipt.hlc_server_time == server_time

    def test_mark_synced_receipt_not_found(self, in_memory_db):
        """mark_synced returns False for invalid ID"""
        fake_id = str(uuid.uuid4())
        result = mark_synced(fake_id, server_time=int(time.time()))
        assert result == False


# ====================
# Move to DLQ Tests
# ====================

class TestMoveToDLQ:
    """Test Dead Letter Queue operations"""

    def test_move_to_dlq_success(self, in_memory_db, sample_receipt_data):
        """Move receipt to DLQ successfully"""
        # Insert receipt
        receipt_id = insert_receipt(sample_receipt_data)

        # Increment retry count to simulate failures
        for i in range(20):
            increment_retry_count(receipt_id, f"Error {i}")

        # Move to DLQ
        result = move_to_dlq(receipt_id, reason="max_retries_exceeded")
        assert result == True

        # Verify DLQ entry
        conn = get_db()
        cursor = conn.execute("""
            SELECT * FROM dlq WHERE original_receipt_id = ?
        """, (receipt_id,))
        dlq_entry = cursor.fetchone()

        assert dlq_entry is not None
        assert dlq_entry['reason'] == "max_retries_exceeded"
        assert dlq_entry['retry_attempts'] == 20

    def test_move_to_dlq_status_changed(self, in_memory_db, sample_receipt_data):
        """Receipt status changed to 'failed' after move to DLQ"""
        receipt_id = insert_receipt(sample_receipt_data)
        move_to_dlq(receipt_id, reason="test_failure")

        receipt = get_receipt_by_id(receipt_id)
        assert receipt.status == 'failed'

    def test_move_to_dlq_event_logged(self, in_memory_db, sample_receipt_data):
        """move_to_dlq logs event to buffer_events"""
        receipt_id = insert_receipt(sample_receipt_data)
        move_to_dlq(receipt_id, reason="test_failure")

        # Check buffer_events
        conn = get_db()
        cursor = conn.execute("""
            SELECT * FROM buffer_events
            WHERE event_type = 'receipt_failed'
            AND receipt_id = ?
        """, (receipt_id,))
        event = cursor.fetchone()

        assert event is not None
        assert event['event_type'] == 'receipt_failed'

    def test_move_to_dlq_receipt_not_found(self, in_memory_db):
        """move_to_dlq returns False for invalid ID"""
        fake_id = str(uuid.uuid4())
        result = move_to_dlq(fake_id, reason="test")
        assert result == False


# ====================
# Buffer Status Tests
# ====================

class TestBufferStatus:
    """Test buffer status queries"""

    def test_get_buffer_status_empty(self, in_memory_db):
        """Empty buffer returns correct status"""
        status = get_buffer_status()

        assert status.total_receipts == 0
        assert status.pending == 0
        assert status.syncing == 0
        assert status.synced == 0
        assert status.failed == 0
        assert status.dlq_size == 0
        assert status.capacity == 200
        assert status.percent_full == 0.0

    def test_get_buffer_status_with_receipts(self, in_memory_db):
        """Buffer status with receipts shows correct counts"""
        # Insert 5 receipts
        receipt_ids = []
        for i in range(5):
            receipt_id = insert_receipt({
                'pos_id': f'POS-{i}',
                'fiscal_doc': {'total': 1000}
            })
            receipt_ids.append(receipt_id)

        # Mark 2 as synced
        mark_synced(receipt_ids[0], int(time.time()))
        mark_synced(receipt_ids[1], int(time.time()))

        # Move 1 to DLQ
        move_to_dlq(receipt_ids[2], reason="test")

        status = get_buffer_status()

        assert status.total_receipts == 5
        assert status.pending == 2  # receipts[3] and receipts[4]
        assert status.synced == 2
        assert status.failed == 1
        assert status.dlq_size == 1

    def test_get_buffer_status_percent_full(self, in_memory_db):
        """Buffer percent_full calculated correctly"""
        # Insert 100 receipts (50% of capacity)
        for i in range(100):
            insert_receipt({
                'pos_id': f'POS-{i}',
                'fiscal_doc': {'total': 1000}
            })

        status = get_buffer_status()
        assert status.percent_full == 50.0


# ====================
# Helper Function Tests
# ====================

class TestHelperFunctions:
    """Test helper functions"""

    def test_update_receipt_status(self, in_memory_db, sample_receipt_data):
        """update_receipt_status changes status"""
        receipt_id = insert_receipt(sample_receipt_data)

        result = update_receipt_status(receipt_id, 'syncing')
        assert result == True

        receipt = get_receipt_by_id(receipt_id)
        assert receipt.status == 'syncing'

    def test_increment_retry_count(self, in_memory_db, sample_receipt_data):
        """increment_retry_count increments counter"""
        receipt_id = insert_receipt(sample_receipt_data)

        new_count = increment_retry_count(receipt_id, error="Connection timeout")
        assert new_count == 1

        # Increment again
        new_count = increment_retry_count(receipt_id, error="Connection timeout 2")
        assert new_count == 2

        # Verify in DB
        receipt = get_receipt_by_id(receipt_id)
        assert receipt.retry_count == 2
        assert receipt.last_error == "Connection timeout 2"

    def test_get_receipt_by_id_found(self, in_memory_db, sample_receipt_data):
        """get_receipt_by_id returns receipt when found"""
        receipt_id = insert_receipt(sample_receipt_data)
        receipt = get_receipt_by_id(receipt_id)

        assert receipt is not None
        assert receipt.id == receipt_id
        assert receipt.pos_id == sample_receipt_data['pos_id']

    def test_get_receipt_by_id_not_found(self, in_memory_db):
        """get_receipt_by_id returns None when not found"""
        fake_id = str(uuid.uuid4())
        receipt = get_receipt_by_id(fake_id)
        assert receipt is None


# ====================
# Thread Safety Tests
# ====================

class TestThreadSafety:
    """Test thread safety of concurrent operations"""

    def test_concurrent_inserts(self, in_memory_db):
        """Concurrent inserts are thread-safe"""
        results = []
        lock = threading.Lock()

        def insert_receipts():
            for i in range(10):
                receipt_id = insert_receipt({
                    'pos_id': f'POS-{threading.current_thread().name}-{i}',
                    'fiscal_doc': {'total': 1000}
                })
                with lock:
                    results.append(receipt_id)

        # Create 5 threads
        threads = [threading.Thread(target=insert_receipts, name=f'T{i}') for i in range(5)]

        for t in threads:
            t.start()

        for t in threads:
            t.join()

        # Verify 50 receipts inserted (5 threads × 10 receipts)
        assert len(results) == 50

        # All receipt IDs should be unique
        assert len(set(results)) == 50

    def test_concurrent_updates(self, in_memory_db):
        """Concurrent updates are thread-safe"""
        # Insert receipts first
        receipt_ids = []
        for i in range(20):
            receipt_id = insert_receipt({
                'pos_id': f'POS-{i}',
                'fiscal_doc': {'total': 1000}
            })
            receipt_ids.append(receipt_id)

        # Concurrently update status and retry count
        def update_receipts():
            for receipt_id in receipt_ids[::2]:  # Update every other receipt
                update_receipt_status(receipt_id, 'syncing')
                increment_retry_count(receipt_id, error="Test error")

        threads = [threading.Thread(target=update_receipts) for _ in range(3)]

        for t in threads:
            t.start()

        for t in threads:
            t.join()

        # Verify no data corruption
        for i, receipt_id in enumerate(receipt_ids):
            receipt = get_receipt_by_id(receipt_id)
            assert receipt is not None
            if i % 2 == 0:
                assert receipt.status == 'syncing'
                assert receipt.retry_count == 3  # Updated by 3 threads


# ====================
# Edge Case Tests
# ====================

class TestEdgeCases:
    """Test edge cases and error handling"""

    def test_insert_receipt_missing_fields(self, in_memory_db):
        """Insert receipt raises ValueError for missing fields"""
        # Missing pos_id
        with pytest.raises(ValueError, match="Missing required field: pos_id"):
            insert_receipt({'fiscal_doc': {'total': 1000}})

        # Missing fiscal_doc
        with pytest.raises(ValueError, match="Missing required field: fiscal_doc"):
            insert_receipt({'pos_id': 'POS-001'})

    def test_update_invalid_status(self, in_memory_db, sample_receipt_data):
        """update_receipt_status raises ValueError for invalid status"""
        receipt_id = insert_receipt(sample_receipt_data)

        with pytest.raises(ValueError, match="Invalid status"):
            update_receipt_status(receipt_id, 'invalid_status')

    def test_receipt_to_dict(self, in_memory_db, sample_receipt_data):
        """Receipt.to_dict() converts receipt to dictionary"""
        receipt_id = insert_receipt(sample_receipt_data)
        receipt = get_receipt_by_id(receipt_id)

        receipt_dict = receipt.to_dict()

        assert isinstance(receipt_dict, dict)
        assert receipt_dict['id'] == receipt_id
        assert receipt_dict['pos_id'] == sample_receipt_data['pos_id']
        assert isinstance(receipt_dict['fiscal_doc'], dict)
        assert receipt_dict['fiscal_doc']['total'] == 1000
