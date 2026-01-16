# OPTERP-4: Implement SQLite Buffer CRUD

**Task:** Implement SQLite buffer database CRUD operations for offline receipt buffering

**Story Points:** 5
**Sprint:** Phase 1 - POC (Week 1)
**Status:** In Progress
**Created:** 2025-10-08
**Assignee:** AI Agent

---

## 📋 Task Description

Implement SQLite buffer CRUD operations for the KKT adapter offline-first architecture. The buffer stores fiscal receipts when the ОФД is unavailable and provides guaranteed delivery with retry logic.

**References:**
- CLAUDE.md §4.1 (Офлайн-буфер SQLite)
- CLAUDE.md §4.2 (Двухфазная фискализация)
- `bootstrap/kkt_adapter_skeleton/schema.sql` (Database schema)

---

## 🎯 Acceptance Criteria

- [ ] **AC1:** `init_buffer_db()` creates database with correct PRAGMA settings
- [ ] **AC2:** `insert_receipt()` adds new receipt with HLC timestamp
- [ ] **AC3:** `get_pending_receipts()` retrieves receipts ordered by HLC
- [ ] **AC4:** `mark_synced()` updates receipt status and assigns server_time
- [ ] **AC5:** `move_to_dlq()` moves failed receipt to Dead Letter Queue
- [ ] **AC6:** `get_buffer_status()` returns current buffer metrics
- [ ] **AC7:** All operations are thread-safe (use connection locks)
- [ ] **AC8:** Idempotency: duplicate inserts are rejected gracefully

---

## 📐 Implementation Plan

### Step 1: Create `kkt_adapter/app/buffer.py` skeleton (15 min)

**File:** `kkt_adapter/app/buffer.py`

**Structure:**
```python
"""
SQLite Buffer CRUD Operations

Author: AI Agent
Created: 2025-10-08
Purpose: Offline buffer for fiscal receipts with CRUD operations

Reference: CLAUDE.md §4.1
"""

import sqlite3
import threading
import time
import uuid
from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from pathlib import Path

from .hlc import HybridTimestamp, generate_hlc

# Thread-safe connection pool
_db_lock = threading.Lock()
_db_connection = None

@dataclass
class Receipt:
    """Receipt dataclass"""
    id: str
    pos_id: str
    created_at: int
    hlc_local_time: int
    hlc_logical_counter: int
    hlc_server_time: Optional[int]
    fiscal_doc: str
    status: str
    retry_count: int
    last_error: Optional[str]
    synced_at: Optional[int]

@dataclass
class BufferStatus:
    """Buffer status metrics"""
    total_receipts: int
    pending: int
    syncing: int
    synced: int
    failed: int
    dlq_size: int
    capacity: int
    percent_full: float
```

### Step 2: Implement `init_buffer_db()` (20 min)

**Function signature:**
```python
def init_buffer_db(db_path: str = 'kkt_adapter/data/buffer.db') -> sqlite3.Connection:
    """
    Initialize SQLite buffer database with correct PRAGMA settings

    Args:
        db_path: Path to SQLite database file

    Returns:
        SQLite connection object

    Raises:
        sqlite3.Error: If database initialization fails
    """
```

**Implementation:**
- Create parent directory if it doesn't exist
- Execute schema from `bootstrap/kkt_adapter_skeleton/schema.sql`
- Set PRAGMA: `journal_mode=WAL`, `synchronous=FULL`, `foreign_keys=ON`
- Set cache_size, wal_autocheckpoint
- Store connection globally with thread lock
- Return connection

**Critical PRAGMA settings (from CLAUDE.md §4.1):**
```python
conn.execute("PRAGMA journal_mode=WAL")        # CRITICAL: WAL for durability
conn.execute("PRAGMA synchronous=FULL")        # CRITICAL: Full fsync
conn.execute("PRAGMA wal_autocheckpoint=100")
conn.execute("PRAGMA cache_size=-64000")       # 64 MB
conn.execute("PRAGMA foreign_keys=ON")
```

### Step 3: Implement `insert_receipt()` (25 min)

**Function signature:**
```python
def insert_receipt(receipt_data: Dict[str, Any]) -> str:
    """
    Insert new receipt into buffer

    Args:
        receipt_data: Dict with keys:
            - pos_id: str (e.g., "POS-001")
            - fiscal_doc: dict (ФФД 1.2 JSON)

    Returns:
        receipt_id: UUIDv4 string

    Raises:
        sqlite3.IntegrityError: If receipt with same ID already exists
        ValueError: If buffer is full (capacity reached)
    """
```

**Implementation:**
1. Check buffer capacity (query `v_buffer_status` view)
2. If >= capacity → raise `ValueError("Buffer full")`
3. Generate receipt_id = `str(uuid.uuid4())`
4. Generate HLC timestamp using `generate_hlc()`
5. Convert fiscal_doc dict to JSON string
6. Insert into `receipts` table with status='pending'
7. Commit transaction
8. Return receipt_id

**SQL:**
```sql
INSERT INTO receipts (
    id, pos_id, created_at,
    hlc_local_time, hlc_logical_counter, hlc_server_time,
    fiscal_doc, status, retry_count
) VALUES (?, ?, ?, ?, ?, ?, ?, 'pending', 0)
```

### Step 4: Implement `get_pending_receipts()` (20 min)

**Function signature:**
```python
def get_pending_receipts(limit: int = 50) -> List[Receipt]:
    """
    Get pending receipts ordered by HLC (oldest first)

    Args:
        limit: Maximum number of receipts to return

    Returns:
        List of Receipt objects ordered by HLC
    """
```

**Implementation:**
1. Query receipts with `status='pending'`
2. Order by HLC (server_time, local_time, logical_counter)
3. Limit results
4. Convert rows to Receipt dataclass instances
5. Return list

**SQL:**
```sql
SELECT * FROM receipts
WHERE status = 'pending'
ORDER BY
    COALESCE(hlc_server_time, hlc_local_time),
    hlc_logical_counter
LIMIT ?
```

### Step 5: Implement `mark_synced()` (20 min)

**Function signature:**
```python
def mark_synced(receipt_id: str, server_time: int) -> bool:
    """
    Mark receipt as successfully synced

    Args:
        receipt_id: Receipt UUID
        server_time: Server timestamp (Unix seconds)

    Returns:
        True if updated, False if receipt not found
    """
```

**Implementation:**
1. Update receipt: status='synced', hlc_server_time=server_time, synced_at=now
2. Check if rowcount == 1
3. Commit
4. Return True/False

**SQL:**
```sql
UPDATE receipts
SET status = 'synced',
    hlc_server_time = ?,
    synced_at = ?
WHERE id = ?
```

### Step 6: Implement `move_to_dlq()` (25 min)

**Function signature:**
```python
def move_to_dlq(receipt_id: str, reason: str) -> bool:
    """
    Move failed receipt to Dead Letter Queue

    Args:
        receipt_id: Receipt UUID
        reason: Failure reason (e.g., "max_retries_exceeded")

    Returns:
        True if moved, False if receipt not found
    """
```

**Implementation:**
1. Fetch receipt by ID
2. If not found → return False
3. Insert into `dlq` table with failure details
4. Update receipt status to 'failed'
5. Log event to `buffer_events`
6. Commit transaction
7. Return True

**SQL:**
```sql
-- 1. Insert to DLQ
INSERT INTO dlq (
    id, original_receipt_id, failed_at, reason,
    fiscal_doc, retry_attempts, last_error
) VALUES (?, ?, ?, ?, ?, ?, ?)

-- 2. Update receipt
UPDATE receipts SET status = 'failed' WHERE id = ?

-- 3. Log event (manual insert, bypass trigger)
INSERT INTO buffer_events (event_type, receipt_id, timestamp, metadata)
VALUES ('receipt_failed', ?, ?, ?)
```

### Step 7: Implement `get_buffer_status()` (15 min)

**Function signature:**
```python
def get_buffer_status() -> BufferStatus:
    """
    Get current buffer status metrics

    Returns:
        BufferStatus dataclass with current metrics
    """
```

**Implementation:**
1. Query `v_buffer_status` view
2. Convert row to BufferStatus dataclass
3. Return

**SQL:**
```sql
SELECT * FROM v_buffer_status
```

### Step 8: Implement helper functions (20 min)

**Functions:**

```python
def update_receipt_status(receipt_id: str, status: str) -> bool:
    """Update receipt status (for sync worker)"""

def increment_retry_count(receipt_id: str, error: str) -> int:
    """Increment retry count and update last_error. Returns new count."""

def get_receipt_by_id(receipt_id: str) -> Optional[Receipt]:
    """Get receipt by ID"""

def close_buffer_db() -> None:
    """Close database connection (for cleanup)"""
```

### Step 9: Add connection management (15 min)

**Context manager:**
```python
def get_db() -> sqlite3.Connection:
    """Get thread-safe database connection"""
    global _db_connection

    with _db_lock:
        if _db_connection is None:
            _db_connection = init_buffer_db()
        return _db_connection
```

**Thread safety:**
- All CRUD operations use `with _db_lock:`
- Connection is reused (not created per-request)

### Step 10: Add error handling (10 min)

**Custom exceptions:**
```python
class BufferFullError(Exception):
    """Buffer capacity reached"""
    pass

class ReceiptNotFoundError(Exception):
    """Receipt not found in buffer"""
    pass
```

---

## 🧪 Testing Strategy

Unit tests will be created in OPTERP-5 (next task). For this task:

**Manual verification:**
```python
# Test 1: Init database
conn = init_buffer_db(':memory:')
assert conn is not None

# Test 2: Insert receipt
receipt_id = insert_receipt({
    'pos_id': 'POS-001',
    'fiscal_doc': {'type': 'sale', 'total': 1000}
})
assert len(receipt_id) == 36  # UUID length

# Test 3: Get pending
receipts = get_pending_receipts(limit=10)
assert len(receipts) == 1
assert receipts[0].id == receipt_id

# Test 4: Mark synced
result = mark_synced(receipt_id, server_time=int(time.time()))
assert result == True

# Test 5: Buffer status
status = get_buffer_status()
assert status.synced == 1
```

---

## 📦 Deliverables

- [ ] `kkt_adapter/app/buffer.py` (≈300 lines)
- [ ] `kkt_adapter/data/` directory created
- [ ] Manual smoke test passed
- [ ] Code committed to `feature/phase1-poc` branch

---

## ⏱️ Time Estimate

| Step | Task | Time |
|------|------|------|
| 1 | Create skeleton | 15 min |
| 2 | `init_buffer_db()` | 20 min |
| 3 | `insert_receipt()` | 25 min |
| 4 | `get_pending_receipts()` | 20 min |
| 5 | `mark_synced()` | 20 min |
| 6 | `move_to_dlq()` | 25 min |
| 7 | `get_buffer_status()` | 15 min |
| 8 | Helper functions | 20 min |
| 9 | Connection management | 15 min |
| 10 | Error handling | 10 min |
| 11 | Manual testing | 15 min |
| **TOTAL** | **3h 20min** |

---

## 🔗 Dependencies

**Requires:**
- ✅ OPTERP-2: Hybrid Logical Clock (completed)
- ✅ SQLite schema (`bootstrap/kkt_adapter_skeleton/schema.sql`)

**Blocks:**
- OPTERP-5: Create Buffer DB Unit Tests
- OPTERP-6: Create FastAPI Main Application

---

## 📝 Notes

### Critical Requirements

1. **Thread Safety:** All operations use `_db_lock`
2. **Durability:** `PRAGMA synchronous=FULL` is CRITICAL
3. **WAL Mode:** `PRAGMA journal_mode=WAL` for concurrent reads
4. **Capacity Check:** Reject inserts when buffer full
5. **Idempotency:** Use `INSERT` (not `INSERT OR REPLACE`) to detect duplicates

### Schema Highlights

**Tables:**
- `receipts` - main buffer (200 capacity)
- `dlq` - dead letter queue for failed receipts
- `buffer_events` - event sourcing log
- `config` - runtime configuration

**Indexes:**
- `idx_receipts_status` - for sync worker queries
- `idx_receipts_hlc` - for HLC ordering (CRITICAL)
- `idx_receipts_pos_id` - per-POS filtering

**Triggers:**
- `trg_receipt_added` - auto-log receipt_added event
- `trg_receipt_synced` - auto-log receipt_synced event

### HLC Integration

```python
from .hlc import generate_hlc, HybridTimestamp

# Generate HLC on insert
hlc = generate_hlc()

# Store in DB
hlc_local_time = hlc.local_time
hlc_logical_counter = hlc.logical_counter
hlc_server_time = None  # Assigned during sync
```

### Buffer Capacity

Default capacity: **200 receipts**

**Capacity check:**
```sql
SELECT percent_full FROM v_buffer_status
```

If `percent_full >= 100` → raise `BufferFullError`

### Ordering by HLC

**Correct ordering (CRITICAL):**
```sql
ORDER BY
    COALESCE(hlc_server_time, hlc_local_time),  -- Effective time
    hlc_logical_counter                         -- Tie-breaker
```

This ensures:
- Receipts with `server_time` come after local-only receipts
- Within same effective time, logical_counter provides order

---

## ✅ Definition of Done

- [ ] All 10 implementation steps completed
- [ ] `buffer.py` created with all functions
- [ ] Database initialized with schema
- [ ] Manual smoke test passed (5 operations)
- [ ] Code follows project style (docstrings, type hints)
- [ ] No linter errors
- [ ] Committed to `feature/phase1-poc` with message: `feat(buffer): implement SQLite buffer CRUD [OPTERP-4]`

---

## 🚀 Ready to Implement

This task plan is complete and ready for execution. Proceed with Step 1.
