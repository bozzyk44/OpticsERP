"""
SQLite Buffer CRUD Operations

Author: AI Agent
Created: 2025-10-08
Purpose: Offline buffer for fiscal receipts with CRUD operations

Reference: CLAUDE.md §4.1

This module provides thread-safe CRUD operations for the offline receipt buffer.
The buffer stores fiscal receipts when ОФД is unavailable and ensures guaranteed
delivery with retry logic and Dead Letter Queue (DLQ) support.

Key Features:
- Thread-safe operations with connection pooling
- WAL mode for durability (PRAGMA synchronous=FULL)
- HLC-based ordering for conflict resolution
- Capacity management (200 receipts max)
- Dead Letter Queue for failed receipts
- Event sourcing for audit trail
"""

import sqlite3
import threading
import time
import uuid
import json
from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from pathlib import Path

# Import HLC - handle both package and direct execution
try:
    from hlc import HybridTimestamp, generate_hlc
except ImportError:
    from hlc import HybridTimestamp, generate_hlc


# ====================
# Custom Exceptions
# ====================

class BufferFullError(Exception):
    """Buffer capacity reached"""
    pass


class ReceiptNotFoundError(Exception):
    """Receipt not found in buffer"""
    pass


# ====================
# Data Classes
# ====================

@dataclass
class Receipt:
    """Receipt dataclass representing a fiscal receipt in the buffer"""
    id: str
    pos_id: str
    created_at: int
    hlc_local_time: int
    hlc_logical_counter: int
    hlc_server_time: Optional[int]
    fiscal_doc: str  # JSON string
    status: str  # pending|syncing|synced|failed
    retry_count: int
    last_error: Optional[str]
    synced_at: Optional[int]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'id': self.id,
            'pos_id': self.pos_id,
            'created_at': self.created_at,
            'hlc_local_time': self.hlc_local_time,
            'hlc_logical_counter': self.hlc_logical_counter,
            'hlc_server_time': self.hlc_server_time,
            'fiscal_doc': json.loads(self.fiscal_doc),
            'status': self.status,
            'retry_count': self.retry_count,
            'last_error': self.last_error,
            'synced_at': self.synced_at
        }


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


# ====================
# Connection Management
# ====================

# Thread-safe connection pool (RLock for reentrant calls)
_db_lock = threading.RLock()
_db_connection: Optional[sqlite3.Connection] = None


def init_buffer_db(db_path: str = 'kkt_adapter/data/buffer.db') -> sqlite3.Connection:
    """
    Initialize SQLite buffer database with correct PRAGMA settings

    This function creates the database file, executes the schema, and sets
    critical PRAGMA settings for durability and performance.

    Args:
        db_path: Path to SQLite database file

    Returns:
        SQLite connection object

    Raises:
        sqlite3.Error: If database initialization fails
    """
    # Create parent directory if it doesn't exist
    db_file = Path(db_path)
    db_file.parent.mkdir(parents=True, exist_ok=True)

    # Connect to database
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row  # Access columns by name

    # CRITICAL: Set PRAGMA for durability and performance
    # See CLAUDE.md §4.1 for explanation
    conn.execute("PRAGMA journal_mode=WAL")         # Write-Ahead Logging (CRITICAL)
    conn.execute("PRAGMA synchronous=FULL")          # Full fsync (CRITICAL for durability)
    conn.execute("PRAGMA wal_autocheckpoint=100")   # Checkpoint every 100 pages
    conn.execute("PRAGMA cache_size=-64000")        # 64 MB cache
    conn.execute("PRAGMA foreign_keys=ON")          # Enable FK constraints

    # Execute schema from bootstrap directory
    # Try multiple paths to find schema file
    possible_paths = [
        Path('bootstrap/kkt_adapter_skeleton/schema.sql'),  # From project root
        Path('../../bootstrap/kkt_adapter_skeleton/schema.sql'),  # From kkt_adapter/app/
        Path(__file__).parent.parent.parent / 'bootstrap' / 'kkt_adapter_skeleton' / 'schema.sql'  # Absolute
    ]

    schema_path = None
    for path in possible_paths:
        if path.exists():
            schema_path = path
            break

    if schema_path:
        with open(schema_path, 'r', encoding='utf-8') as f:
            schema_sql = f.read()
            conn.executescript(schema_sql)
    else:
        # If schema file not found, assume database already initialized
        # (e.g., for testing with :memory:)
        pass

    conn.commit()
    return conn


def get_db() -> sqlite3.Connection:
    """
    Get thread-safe database connection

    Returns cached connection or initializes new one if not exists.

    Returns:
        SQLite connection object
    """
    global _db_connection

    with _db_lock:
        if _db_connection is None:
            _db_connection = init_buffer_db()
        return _db_connection


def close_buffer_db() -> None:
    """
    Close database connection (for cleanup)

    Should be called on application shutdown.
    """
    global _db_connection

    with _db_lock:
        if _db_connection is not None:
            _db_connection.close()
            _db_connection = None


# ====================
# CRUD Operations
# ====================

def insert_receipt(receipt_data: Dict[str, Any]) -> str:
    """
    Insert new receipt into buffer

    This function performs capacity check, generates HLC timestamp,
    and inserts the receipt with status='pending'.

    Args:
        receipt_data: Dict with keys:
            - pos_id: str (e.g., "POS-001")
            - fiscal_doc: dict (ФФД 1.2 JSON)

    Returns:
        receipt_id: UUIDv4 string

    Raises:
        BufferFullError: If buffer capacity reached
        sqlite3.IntegrityError: If receipt with same ID already exists
        ValueError: If required fields missing
    """
    # Validate input
    if 'pos_id' not in receipt_data:
        raise ValueError("Missing required field: pos_id")
    if 'fiscal_doc' not in receipt_data:
        raise ValueError("Missing required field: fiscal_doc")

    conn = get_db()

    with _db_lock:
        # Check buffer capacity
        status = get_buffer_status()
        if status.pending >= status.capacity:
            raise BufferFullError(f"Buffer full: {status.pending}/{status.capacity}")

        # Generate receipt ID and HLC timestamp
        receipt_id = str(uuid.uuid4())
        hlc = generate_hlc()
        current_time = int(time.time())

        # Convert fiscal_doc to JSON string
        fiscal_doc_json = json.dumps(receipt_data['fiscal_doc'])

        # Insert receipt
        conn.execute("""
            INSERT INTO receipts (
                id, pos_id, created_at,
                hlc_local_time, hlc_logical_counter, hlc_server_time,
                fiscal_doc, status, retry_count
            ) VALUES (?, ?, ?, ?, ?, ?, ?, 'pending', 0)
        """, (
            receipt_id,
            receipt_data['pos_id'],
            current_time,
            hlc.local_time,
            hlc.logical_counter,
            None,  # server_time assigned during sync
            fiscal_doc_json
        ))

        conn.commit()
        return receipt_id


def get_pending_receipts(limit: int = 50) -> List[Receipt]:
    """
    Get pending receipts ordered by HLC (oldest first)

    Receipts are ordered by effective time (server_time if present, else local_time)
    and then by logical_counter as tie-breaker.

    Args:
        limit: Maximum number of receipts to return (default: 50)

    Returns:
        List of Receipt objects ordered by HLC
    """
    conn = get_db()

    with _db_lock:
        cursor = conn.execute("""
            SELECT
                id, pos_id, created_at,
                hlc_local_time, hlc_logical_counter, hlc_server_time,
                fiscal_doc, status, retry_count, last_error, synced_at
            FROM receipts
            WHERE status = 'pending'
            ORDER BY
                COALESCE(hlc_server_time, hlc_local_time),
                hlc_logical_counter
            LIMIT ?
        """, (limit,))

        receipts = []
        for row in cursor.fetchall():
            receipts.append(Receipt(
                id=row['id'],
                pos_id=row['pos_id'],
                created_at=row['created_at'],
                hlc_local_time=row['hlc_local_time'],
                hlc_logical_counter=row['hlc_logical_counter'],
                hlc_server_time=row['hlc_server_time'],
                fiscal_doc=row['fiscal_doc'],
                status=row['status'],
                retry_count=row['retry_count'],
                last_error=row['last_error'],
                synced_at=row['synced_at']
            ))

        return receipts


def mark_synced(receipt_id: str, server_time: int) -> bool:
    """
    Mark receipt as successfully synced

    Updates receipt status to 'synced' and assigns server_time for HLC ordering.

    Args:
        receipt_id: Receipt UUID
        server_time: Server timestamp (Unix seconds)

    Returns:
        True if updated, False if receipt not found
    """
    conn = get_db()
    current_time = int(time.time())

    with _db_lock:
        cursor = conn.execute("""
            UPDATE receipts
            SET status = 'synced',
                hlc_server_time = ?,
                synced_at = ?
            WHERE id = ?
        """, (server_time, current_time, receipt_id))

        conn.commit()
        return cursor.rowcount > 0


def move_to_dlq(receipt_id: str, reason: str) -> bool:
    """
    Move failed receipt to Dead Letter Queue

    This function moves a receipt that exceeded max retry attempts to the DLQ
    for manual investigation. It performs the following:
    1. Fetch receipt from receipts table
    2. Insert copy into dlq table
    3. Update receipt status to 'failed'
    4. Log event to buffer_events

    Args:
        receipt_id: Receipt UUID
        reason: Failure reason (e.g., "max_retries_exceeded")

    Returns:
        True if moved, False if receipt not found
    """
    conn = get_db()

    with _db_lock:
        # Fetch receipt
        cursor = conn.execute("""
            SELECT * FROM receipts WHERE id = ?
        """, (receipt_id,))

        row = cursor.fetchone()
        if row is None:
            return False

        # Insert into DLQ
        dlq_id = str(uuid.uuid4())
        current_time = int(time.time())

        conn.execute("""
            INSERT INTO dlq (
                id, original_receipt_id, failed_at, reason,
                fiscal_doc, retry_attempts, last_error
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            dlq_id,
            receipt_id,
            current_time,
            reason,
            row['fiscal_doc'],
            row['retry_count'],
            row['last_error']
        ))

        # Update receipt status
        conn.execute("""
            UPDATE receipts SET status = 'failed' WHERE id = ?
        """, (receipt_id,))

        # Log event (manual, since trigger only fires on status change to 'synced')
        conn.execute("""
            INSERT INTO buffer_events (event_type, receipt_id, timestamp, metadata)
            VALUES ('receipt_failed', ?, ?, ?)
        """, (
            receipt_id,
            current_time,
            json.dumps({'reason': reason, 'retry_attempts': row['retry_count']})
        ))

        conn.commit()
        return True


def get_buffer_status() -> BufferStatus:
    """
    Get current buffer status metrics

    Queries the v_buffer_status view which provides aggregated metrics.

    Returns:
        BufferStatus dataclass with current metrics
    """
    conn = get_db()

    with _db_lock:
        cursor = conn.execute("SELECT * FROM v_buffer_status")
        row = cursor.fetchone()

        if row is None:
            # Empty buffer
            return BufferStatus(
                total_receipts=0,
                pending=0,
                syncing=0,
                synced=0,
                failed=0,
                dlq_size=0,
                capacity=200,  # Default from schema
                percent_full=0.0
            )

        return BufferStatus(
            total_receipts=row['total_receipts'] or 0,
            pending=row['pending'] or 0,
            syncing=row['syncing'] or 0,
            synced=row['synced'] or 0,
            failed=row['failed'] or 0,
            dlq_size=row['dlq_size'] or 0,
            capacity=int(row['capacity']),
            percent_full=float(row['percent_full'] or 0.0)
        )


# ====================
# Helper Functions
# ====================

def update_receipt_status(receipt_id: str, status: str) -> bool:
    """
    Update receipt status (for sync worker)

    Args:
        receipt_id: Receipt UUID
        status: New status (pending|syncing|synced|failed)

    Returns:
        True if updated, False if receipt not found

    Raises:
        ValueError: If status is invalid
    """
    valid_statuses = ['pending', 'syncing', 'synced', 'failed']
    if status not in valid_statuses:
        raise ValueError(f"Invalid status: {status}. Must be one of {valid_statuses}")

    conn = get_db()

    with _db_lock:
        cursor = conn.execute("""
            UPDATE receipts SET status = ? WHERE id = ?
        """, (status, receipt_id))

        conn.commit()
        return cursor.rowcount > 0


def update_receipt_fiscal_doc(receipt_id: str, fiscal_doc_update: Dict[str, Any]) -> bool:
    """
    Update receipt fiscal_doc with data from KKT driver (after printing)

    This merges the fiscal document data (fiscal_doc_number, fiscal_sign, etc.)
    into the existing fiscal_doc JSON.

    Args:
        receipt_id: Receipt UUID
        fiscal_doc_update: Dict with fiscal doc fields to merge:
            - fiscal_doc_number: int
            - fiscal_sign: str
            - fiscal_datetime: str
            - fn_number: str
            - kkt_number: str
            - qr_code_data: str
            - shift_number: int
            - receipt_number: int

    Returns:
        True if updated, False if receipt not found

    Raises:
        ValueError: If receipt_id invalid or fiscal_doc malformed
    """
    conn = get_db()

    with _db_lock:
        # Get existing fiscal_doc
        cursor = conn.execute("""
            SELECT fiscal_doc FROM receipts WHERE id = ?
        """, (receipt_id,))

        row = cursor.fetchone()
        if not row:
            return False

        # Parse existing fiscal_doc
        try:
            fiscal_doc = json.loads(row[0])
        except json.JSONDecodeError as e:
            raise ValueError(f"Malformed fiscal_doc JSON: {e}")

        # Merge update into existing fiscal_doc
        fiscal_doc.update(fiscal_doc_update)

        # Update database
        conn.execute("""
            UPDATE receipts SET fiscal_doc = ? WHERE id = ?
        """, (json.dumps(fiscal_doc), receipt_id))

        conn.commit()
        return True


def increment_retry_count(receipt_id: str, error: str) -> int:
    """
    Increment retry count and update last_error

    Args:
        receipt_id: Receipt UUID
        error: Error message to store

    Returns:
        New retry count, or -1 if receipt not found
    """
    conn = get_db()

    with _db_lock:
        cursor = conn.execute("""
            UPDATE receipts
            SET retry_count = retry_count + 1,
                last_error = ?
            WHERE id = ?
        """, (error, receipt_id))

        if cursor.rowcount == 0:
            return -1

        # Fetch new retry count
        cursor = conn.execute("""
            SELECT retry_count FROM receipts WHERE id = ?
        """, (receipt_id,))

        row = cursor.fetchone()
        conn.commit()

        return row['retry_count'] if row else -1


def get_receipt_by_id(receipt_id: str) -> Optional[Receipt]:
    """
    Get receipt by ID

    Args:
        receipt_id: Receipt UUID

    Returns:
        Receipt object or None if not found
    """
    conn = get_db()

    with _db_lock:
        cursor = conn.execute("""
            SELECT
                id, pos_id, created_at,
                hlc_local_time, hlc_logical_counter, hlc_server_time,
                fiscal_doc, status, retry_count, last_error, synced_at
            FROM receipts
            WHERE id = ?
        """, (receipt_id,))

        row = cursor.fetchone()
        if row is None:
            return None

        return Receipt(
            id=row['id'],
            pos_id=row['pos_id'],
            created_at=row['created_at'],
            hlc_local_time=row['hlc_local_time'],
            hlc_logical_counter=row['hlc_logical_counter'],
            hlc_server_time=row['hlc_server_time'],
            fiscal_doc=row['fiscal_doc'],
            status=row['status'],
            retry_count=row['retry_count'],
            last_error=row['last_error'],
            synced_at=row['synced_at']
        )


# ====================
# Session State Persistence (OPTERP-104)
# ====================

def restore_session_state(pos_id: str) -> Optional[Dict[str, Any]]:
    """
    Restore POS session state after restart (OPTERP-104)

    Retrieves cash_balance, card_balance, and session metadata from SQLite
    to recover in-memory state after KKT Adapter restart/crash.

    Args:
        pos_id: POS terminal ID (e.g., "POS-001")

    Returns:
        Dictionary with session state or None if no open session exists:
        {
            'session_id': str,
            'cash_balance': float,
            'card_balance': float,
            'opened_at': int,
            'last_updated': int,
            'unsynced_transactions': int
        }
    """
    conn = get_db()

    with _db_lock:
        # Find open session
        cursor = conn.execute("""
            SELECT
                pos_id, session_id, opened_at, closed_at,
                cash_balance, card_balance,
                z_report_data, last_updated, status
            FROM pos_sessions
            WHERE pos_id = ? AND status = 'open'
        """, (pos_id,))

        row = cursor.fetchone()

        if row is None:
            return None

        # Count unsynced transactions
        cursor = conn.execute("""
            SELECT COUNT(*) as count
            FROM cash_transactions
            WHERE pos_id = ? AND synced_to_odoo = 0
        """, (pos_id,))

        unsynced_row = cursor.fetchone()
        unsynced_count = unsynced_row['count'] if unsynced_row else 0

        return {
            'session_id': row['session_id'],
            'cash_balance': row['cash_balance'],
            'card_balance': row['card_balance'],
            'opened_at': row['opened_at'],
            'last_updated': row['last_updated'],
            'unsynced_transactions': unsynced_count,
            'z_report_data': row['z_report_data']
        }


def reconcile_session(pos_id: str) -> Dict[str, Any]:
    """
    Reconcile session balance with transactions (OPTERP-104)

    Calculates expected balance from cash_transactions table and compares
    with actual cash_balance in pos_sessions. Used for integrity checks.

    Args:
        pos_id: POS terminal ID

    Returns:
        Dictionary with reconciliation result:
        {
            'expected_balance': float,
            'actual_balance': float,
            'difference': float,
            'reconciled': bool
        }
    """
    conn = get_db()

    with _db_lock:
        # Get current session balance
        cursor = conn.execute("""
            SELECT cash_balance
            FROM pos_sessions
            WHERE pos_id = ? AND status = 'open'
        """, (pos_id,))

        session_row = cursor.fetchone()

        if session_row is None:
            return {
                'expected_balance': 0.0,
                'actual_balance': 0.0,
                'difference': 0.0,
                'reconciled': False,
                'error': 'No open session found'
            }

        actual_balance = session_row['cash_balance']

        # Calculate expected balance from transactions
        cursor = conn.execute("""
            SELECT
                SUM(CASE
                    WHEN transaction_type = 'sale' AND payment_method = 'cash' THEN amount
                    WHEN transaction_type = 'refund' AND payment_method = 'cash' THEN -amount
                    WHEN transaction_type = 'cash_in' THEN amount
                    WHEN transaction_type = 'cash_out' THEN -amount
                    ELSE 0
                END) as balance
            FROM cash_transactions
            WHERE pos_id = ?
        """, (pos_id,))

        calc_row = cursor.fetchone()
        expected_balance = calc_row['balance'] if calc_row['balance'] is not None else 0.0

        difference = abs(expected_balance - actual_balance)
        tolerance = 0.01  # 1 kopek tolerance for floating point

        return {
            'expected_balance': expected_balance,
            'actual_balance': actual_balance,
            'difference': difference,
            'reconciled': difference <= tolerance
        }


def update_session_balance(pos_id: str, cash_amount: float, card_amount: float) -> None:
    """
    Update session balance after transaction (OPTERP-104)

    Args:
        pos_id: POS terminal ID
        cash_amount: Cash amount to add (negative for refunds/cash-out)
        card_amount: Card amount to add (negative for refunds)
    """
    conn = get_db()

    with _db_lock:
        cursor = conn.execute("""
            UPDATE pos_sessions
            SET
                cash_balance = cash_balance + ?,
                card_balance = card_balance + ?,
                last_updated = ?
            WHERE pos_id = ? AND status = 'open'
        """, (cash_amount, card_amount, int(time.time()), pos_id))

        if cursor.rowcount == 0:
            raise ValueError(f"No open session found for {pos_id}")

        conn.commit()


def log_cash_transaction(
    pos_id: str,
    receipt_id: Optional[str],
    transaction_type: str,
    amount: float,
    payment_method: str
) -> str:
    """
    Log cash transaction for audit trail (OPTERP-104)

    Args:
        pos_id: POS terminal ID
        receipt_id: Optional receipt ID (for sale/refund)
        transaction_type: sale|refund|cash_in|cash_out
        amount: Transaction amount (always positive)
        payment_method: cash|card|mixed

    Returns:
        Transaction ID (UUIDv4)
    """
    conn = get_db()
    tx_id = str(uuid.uuid4())

    with _db_lock:
        conn.execute("""
            INSERT INTO cash_transactions (
                id, pos_id, receipt_id, transaction_type,
                amount, payment_method, timestamp,
                synced_to_odoo, synced_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, 0, NULL)
        """, (
            tx_id, pos_id, receipt_id, transaction_type,
            amount, payment_method, int(time.time())
        ))

        conn.commit()

    return tx_id


def open_pos_session(pos_id: str, session_id: str) -> None:
    """
    Open new POS session (OPTERP-104)

    Args:
        pos_id: POS terminal ID
        session_id: Odoo session ID
    """
    conn = get_db()
    timestamp = int(time.time())

    with _db_lock:
        # Close any existing open session (failsafe)
        conn.execute("""
            UPDATE pos_sessions
            SET status = 'closed', closed_at = ?
            WHERE pos_id = ? AND status = 'open'
        """, (timestamp, pos_id))

        # Insert new session
        conn.execute("""
            INSERT OR REPLACE INTO pos_sessions (
                pos_id, session_id, opened_at, closed_at,
                cash_balance, card_balance, z_report_data,
                last_updated, status
            ) VALUES (?, ?, ?, NULL, 0, 0, NULL, ?, 'open')
        """, (pos_id, session_id, timestamp, timestamp))

        conn.commit()


def close_pos_session(pos_id: str, z_report_data: Optional[str] = None) -> None:
    """
    Close POS session (OPTERP-104)

    Args:
        pos_id: POS terminal ID
        z_report_data: Optional Z-report JSON data
    """
    conn = get_db()
    timestamp = int(time.time())

    with _db_lock:
        conn.execute("""
            UPDATE pos_sessions
            SET
                status = 'closed',
                closed_at = ?,
                z_report_data = ?,
                last_updated = ?
            WHERE pos_id = ? AND status = 'open'
        """, (timestamp, z_report_data, timestamp, pos_id))

        conn.commit()


# ====================
# Example Usage
# ====================

if __name__ == "__main__":
    print("=== SQLite Buffer CRUD Demo ===\n")

    # Initialize database
    print("1. Initializing database...")
    init_buffer_db(':memory:')  # Use in-memory database for demo

    # Insert receipt
    print("\n2. Inserting receipt...")
    receipt_id = insert_receipt({
        'pos_id': 'POS-001',
        'fiscal_doc': {
            'type': 'sale',
            'total': 1000,
            'items': [{'name': 'Product A', 'price': 1000, 'qty': 1}]
        }
    })
    print(f"   Receipt ID: {receipt_id}")

    # Get pending receipts
    print("\n3. Getting pending receipts...")
    pending = get_pending_receipts(limit=10)
    print(f"   Found {len(pending)} pending receipt(s)")
    if pending:
        print(f"   First receipt: {pending[0].id}")

    # Buffer status
    print("\n4. Buffer status:")
    status = get_buffer_status()
    print(f"   Total: {status.total_receipts}")
    print(f"   Pending: {status.pending}")
    print(f"   Capacity: {status.capacity}")
    print(f"   Percent full: {status.percent_full}%")

    # Mark synced
    print("\n5. Marking receipt as synced...")
    server_time = int(time.time())
    result = mark_synced(receipt_id, server_time)
    print(f"   Result: {'Success' if result else 'Failed'}")

    # Final status
    print("\n6. Final buffer status:")
    status = get_buffer_status()
    print(f"   Synced: {status.synced}")
    print(f"   Pending: {status.pending}")

    print("\n=== Demo Complete ===")
