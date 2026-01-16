# OPTERP-5: Create Buffer DB Unit Tests

**Task:** Create comprehensive unit tests for SQLite buffer CRUD operations

**Story Points:** 3
**Sprint:** Phase 1 - POC (Week 1)
**Status:** In Progress
**Created:** 2025-10-08
**Assignee:** AI Agent

---

## 📋 Task Description

Create comprehensive unit tests for the SQLite buffer module (`kkt_adapter/app/buffer.py`) to ensure all CRUD operations work correctly, including thread safety, capacity management, HLC ordering, and Dead Letter Queue functionality.

**References:**
- OPTERP-4: Implement SQLite Buffer CRUD (completed)
- CLAUDE.md §4.1 (Офлайн-буфер SQLite)
- kkt_adapter/app/buffer.py (530 lines)

---

## 🎯 Acceptance Criteria

- [ ] **AC1:** 20+ unit tests covering all buffer functions
- [ ] **AC2:** Coverage ≥95% for buffer.py
- [ ] **AC3:** All tests pass (0 FAILED)
- [ ] **AC4:** Thread safety verified (concurrent operations)
- [ ] **AC5:** Capacity enforcement tested (BufferFullError)
- [ ] **AC6:** HLC ordering verified (correct receipt order)
- [ ] **AC7:** DLQ functionality tested (move_to_dlq)
- [ ] **AC8:** Edge cases covered (empty buffer, not found, etc)
- [ ] **AC9:** Test log saved to tests/logs/unit/

---

## 📐 Implementation Plan

### Step 1: Create test file skeleton (15 min)

**File:** `tests/unit/test_buffer.py`

**Structure:**
```python
"""
Unit tests for SQLite Buffer CRUD Operations

Author: AI Agent
Created: 2025-10-08
Purpose: Test buffer.py CRUD operations, thread safety, HLC ordering

Reference: CLAUDE.md §4.1, OPTERP-4
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

# Pytest fixtures
@pytest.fixture
def in_memory_db():
    """Fixture for in-memory database"""
    # Implementation
    pass

@pytest.fixture
def sample_receipt_data():
    """Fixture for sample receipt data"""
    # Implementation
    pass
```

### Step 2: Implement database initialization tests (20 min)

**Test class:** `TestDatabaseInitialization`

**Tests (3 tests):**
1. `test_init_buffer_db_creates_tables` - verify all tables created
2. `test_init_buffer_db_pragma_settings` - verify WAL mode, synchronous=FULL
3. `test_init_buffer_db_default_config` - verify config table populated

**Example:**
```python
class TestDatabaseInitialization:
    def test_init_buffer_db_creates_tables(self):
        """Database initialization creates all required tables"""
        conn = init_buffer_db(':memory:')

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

    def test_init_buffer_db_pragma_settings(self):
        """PRAGMA settings are correctly set"""
        conn = init_buffer_db(':memory:')

        # Check journal_mode (should be WAL or memory for :memory: db)
        cursor = conn.execute("PRAGMA journal_mode")
        journal_mode = cursor.fetchone()[0]
        assert journal_mode in ['wal', 'memory']

        # Check foreign_keys
        cursor = conn.execute("PRAGMA foreign_keys")
        fk_enabled = cursor.fetchone()[0]
        assert fk_enabled == 1
```

### Step 3: Implement insert_receipt tests (25 min)

**Test class:** `TestInsertReceipt`

**Tests (4 tests):**
1. `test_insert_receipt_success` - basic insertion
2. `test_insert_receipt_generates_uuid` - UUID format validation
3. `test_insert_receipt_assigns_hlc` - HLC timestamp assigned
4. `test_insert_receipt_capacity_check` - BufferFullError when capacity reached

**Example:**
```python
class TestInsertReceipt:
    def test_insert_receipt_success(self, in_memory_db, sample_receipt_data):
        """Insert receipt successfully"""
        receipt_id = insert_receipt(sample_receipt_data)

        assert receipt_id is not None
        assert len(receipt_id) == 36  # UUID length

        # Verify in database
        receipt = get_receipt_by_id(receipt_id)
        assert receipt is not None
        assert receipt.pos_id == sample_receipt_data['pos_id']
        assert receipt.status == 'pending'

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
```

### Step 4: Implement get_pending_receipts tests (25 min)

**Test class:** `TestGetPendingReceipts`

**Tests (4 tests):**
1. `test_get_pending_receipts_empty` - empty buffer returns []
2. `test_get_pending_receipts_limit` - respects limit parameter
3. `test_get_pending_receipts_hlc_ordering` - correct HLC order
4. `test_get_pending_receipts_excludes_synced` - only pending receipts

**Example:**
```python
class TestGetPendingReceipts:
    def test_get_pending_receipts_hlc_ordering(self, in_memory_db):
        """Receipts ordered by HLC (oldest first)"""
        reset_hlc()

        # Insert 5 receipts with delays to ensure different HLC
        receipt_ids = []
        for i in range(5):
            receipt_id = insert_receipt({
                'pos_id': f'POS-{i}',
                'fiscal_doc': {'total': 1000 * (i+1)}
            })
            receipt_ids.append(receipt_id)
            time.sleep(0.01)  # Small delay

        # Get pending receipts
        pending = get_pending_receipts(limit=10)

        # Should be in insertion order (HLC monotonic)
        assert len(pending) == 5
        for i, receipt in enumerate(pending):
            assert receipt.id == receipt_ids[i]
```

### Step 5: Implement mark_synced tests (20 min)

**Test class:** `TestMarkSynced`

**Tests (3 tests):**
1. `test_mark_synced_success` - status updated to 'synced'
2. `test_mark_synced_assigns_server_time` - hlc_server_time assigned
3. `test_mark_synced_receipt_not_found` - returns False for invalid ID

### Step 6: Implement move_to_dlq tests (25 min)

**Test class:** `TestMoveToDLQ`

**Tests (4 tests):**
1. `test_move_to_dlq_success` - receipt moved to DLQ
2. `test_move_to_dlq_status_changed` - receipt status = 'failed'
3. `test_move_to_dlq_event_logged` - event in buffer_events
4. `test_move_to_dlq_receipt_not_found` - returns False for invalid ID

**Example:**
```python
class TestMoveToDLQ:
    def test_move_to_dlq_success(self, in_memory_db, sample_receipt_data):
        """Move receipt to DLQ successfully"""
        # Insert receipt
        receipt_id = insert_receipt(sample_receipt_data)

        # Increment retry count to max
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
```

### Step 7: Implement buffer_status tests (20 min)

**Test class:** `TestBufferStatus`

**Tests (3 tests):**
1. `test_get_buffer_status_empty` - empty buffer metrics
2. `test_get_buffer_status_with_receipts` - correct counts
3. `test_get_buffer_status_percent_full` - capacity percentage calculation

### Step 8: Implement helper function tests (20 min)

**Test class:** `TestHelperFunctions`

**Tests (4 tests):**
1. `test_update_receipt_status` - status update
2. `test_increment_retry_count` - retry count incremented
3. `test_get_receipt_by_id_found` - receipt found
4. `test_get_receipt_by_id_not_found` - returns None

### Step 9: Implement thread safety tests (25 min)

**Test class:** `TestThreadSafety`

**Tests (2 tests):**
1. `test_concurrent_inserts` - no race conditions on insert
2. `test_concurrent_updates` - no race conditions on update

**Example:**
```python
class TestThreadSafety:
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
        threads = [threading.Thread(target=insert_receipts) for _ in range(5)]

        for t in threads:
            t.start()

        for t in threads:
            t.join()

        # Verify 50 receipts inserted (5 threads × 10 receipts)
        assert len(results) == 50

        # All receipt IDs should be unique
        assert len(set(results)) == 50
```

### Step 10: Implement edge case tests (20 min)

**Test class:** `TestEdgeCases`

**Tests (3 tests):**
1. `test_insert_receipt_missing_fields` - ValueError for missing fields
2. `test_update_invalid_status` - ValueError for invalid status
3. `test_receipt_to_dict` - Receipt.to_dict() conversion

### Step 11: Run tests and verify coverage (15 min)

**Commands:**
```bash
# Create log directory
mkdir -p tests/logs/unit

# Run tests with coverage and save log
pytest tests/unit/test_buffer.py -v \
  --cov=kkt_adapter/app/buffer \
  --cov-report=term-missing \
  2>&1 | tee tests/logs/unit/$(date +%Y%m%d)_OPTERP-5_buffer_tests.log

# Check coverage percentage
pytest tests/unit/test_buffer.py \
  --cov=kkt_adapter/app/buffer \
  --cov-report=term | grep TOTAL
```

**Expected result:**
- ✅ 25+ tests passed
- ✅ Coverage ≥95%
- ✅ 0 FAILED

---

## 🧪 Test Structure Summary

| Test Class | Tests | Focus |
|------------|-------|-------|
| TestDatabaseInitialization | 3 | DB creation, PRAGMA settings |
| TestInsertReceipt | 4 | Insert, UUID, HLC, capacity |
| TestGetPendingReceipts | 4 | Query, ordering, filtering |
| TestMarkSynced | 3 | Sync status update |
| TestMoveToDLQ | 4 | DLQ operations, events |
| TestBufferStatus | 3 | Metrics, capacity |
| TestHelperFunctions | 4 | Helper operations |
| TestThreadSafety | 2 | Concurrent operations |
| TestEdgeCases | 3 | Error handling, validation |
| **TOTAL** | **30 tests** | **Comprehensive coverage** |

---

## 📦 Deliverables

- [ ] `tests/unit/test_buffer.py` (≈600 lines)
- [ ] Test log: `tests/logs/unit/20251008_OPTERP-5_buffer_tests.log`
- [ ] Coverage report (≥95%)
- [ ] Code committed to `feature/phase1-poc` branch

---

## ⏱️ Time Estimate

| Step | Task | Time |
|------|------|------|
| 1 | Create test skeleton | 15 min |
| 2 | Database initialization tests | 20 min |
| 3 | insert_receipt tests | 25 min |
| 4 | get_pending_receipts tests | 25 min |
| 5 | mark_synced tests | 20 min |
| 6 | move_to_dlq tests | 25 min |
| 7 | buffer_status tests | 20 min |
| 8 | Helper function tests | 20 min |
| 9 | Thread safety tests | 25 min |
| 10 | Edge case tests | 20 min |
| 11 | Run tests, verify coverage | 15 min |
| **TOTAL** | **3h 50min** |

---

## 🔗 Dependencies

**Requires:**
- ✅ OPTERP-2: Hybrid Logical Clock (completed)
- ✅ OPTERP-3: HLC Unit Tests (completed)
- ✅ OPTERP-4: SQLite Buffer CRUD (completed)

**Blocks:**
- OPTERP-6: Create FastAPI Main Application

---

## 📝 Notes

### Critical Test Requirements

1. **In-memory database:** Use `:memory:` for all tests (fast, isolated)
2. **HLC reset:** Call `reset_hlc()` in fixtures to avoid state leakage
3. **Thread safety:** Test concurrent operations (5 threads minimum)
4. **Capacity enforcement:** Verify BufferFullError at 200 receipts
5. **HLC ordering:** Verify correct ordering with time.sleep() delays

### Pytest Fixtures

**Required fixtures:**
```python
@pytest.fixture
def in_memory_db():
    """Initialize in-memory database"""
    reset_hlc()
    conn = init_buffer_db(':memory:')
    yield conn
    close_buffer_db()

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
```

### Coverage Target Areas

**Must cover (≥95%):**
- All CRUD functions (insert, get, update, delete)
- Helper functions (update_status, increment_retry, get_by_id)
- Exception handling (BufferFullError, ReceiptNotFoundError)
- Thread safety (concurrent inserts/updates)
- HLC ordering logic
- DLQ operations

**Edge cases:**
- Empty buffer queries
- Receipt not found scenarios
- Invalid status values
- Missing required fields
- Capacity boundary (199, 200, 201 receipts)

### Test Log Format

**File:** `tests/logs/unit/20251008_OPTERP-5_buffer_tests.log`

**Must include:**
```
=== Test Log ===
Date: 2025-10-08 HH:MM:SS
Task: OPTERP-5 (Create Buffer DB Unit Tests)
Type: Unit Tests
File: tests/unit/test_buffer.py
Python: 3.11.7
OS: Windows 11

Command:
pytest tests/unit/test_buffer.py -v --cov=kkt_adapter/app/buffer

Output:
[full pytest output]

Coverage:
Name                       Stmts   Miss  Cover   Missing
--------------------------------------------------------
kkt_adapter/app/buffer.py    152      5    97%   [lines]
--------------------------------------------------------

Summary:
✅ 30 tests passed
✅ 0 tests failed
✅ Coverage: 97%
✅ Duration: X.XXs

Result: SUCCESS
```

---

## ✅ Definition of Done

- [ ] All 30 tests implemented
- [ ] All tests PASS (0 FAILED)
- [ ] Coverage ≥95% for buffer.py
- [ ] Thread safety verified (concurrent operations)
- [ ] Test log saved to `tests/logs/unit/20251008_OPTERP-5_buffer_tests.log`
- [ ] No linter errors
- [ ] Committed to `feature/phase1-poc` with message: `test(buffer): add comprehensive unit tests for buffer CRUD [OPTERP-5]`

---

## 🚀 Ready to Implement

This task plan is complete and ready for execution. Proceed with Step 1.
