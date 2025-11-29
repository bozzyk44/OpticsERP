# pos_monitor/app/database.py
"""Read-only SQLite database access for POS Monitor"""
import sqlite3
import logging
from contextlib import contextmanager
from pathlib import Path
from typing import Tuple, Dict, List, Optional
from datetime import datetime, date
from .config import BUFFER_DB_PATH, BUFFER_CAPACITY

logger = logging.getLogger(__name__)


@contextmanager
def get_db():
    """
    Get read-only connection to buffer.db

    CRITICAL: Uses read-only mode (mode=ro) to prevent accidental writes
    """
    db_path = Path(BUFFER_DB_PATH)

    if not db_path.exists():
        logger.error(f"buffer.db not found at {db_path}")
        raise FileNotFoundError(f"Database not found: {db_path}")

    # Read-only URI mode
    conn = sqlite3.connect(
        f"file:{db_path}?mode=ro",
        uri=True,
        check_same_thread=False
    )
    conn.row_factory = sqlite3.Row  # Return dict-like rows

    try:
        yield conn
    finally:
        conn.close()


def get_cash_balance() -> Tuple[float, float]:
    """
    Get current cash and card balance from open POS session

    Returns:
        Tuple of (cash_balance, card_balance)
        Returns (0.0, 0.0) if no open session
    """
    try:
        with get_db() as db:
            row = db.execute(
                """SELECT cash_balance, card_balance
                   FROM pos_sessions
                   WHERE status = 'open'
                   ORDER BY id DESC
                   LIMIT 1"""
            ).fetchone()

            if row:
                return float(row['cash_balance'] or 0), float(row['card_balance'] or 0)

            logger.warning("No open POS session found")
            return 0.0, 0.0

    except sqlite3.Error as e:
        logger.error(f"Error fetching cash balance: {e}")
        return 0.0, 0.0


def get_buffer_status() -> Dict:
    """
    Get buffer state (pending, DLQ, percent_full, last_sync)

    Returns:
        Dict with keys: pending, dlq, percent_full, last_sync
    """
    try:
        with get_db() as db:
            # Count pending receipts
            pending_row = db.execute(
                "SELECT COUNT(*) as count FROM receipts WHERE status = 'pending'"
            ).fetchone()
            pending = pending_row['count'] if pending_row else 0

            # Count DLQ
            dlq_row = db.execute(
                "SELECT COUNT(*) as count FROM dlq"
            ).fetchone()
            dlq = dlq_row['count'] if dlq_row else 0

            # Last successful sync timestamp
            last_sync_row = db.execute(
                """SELECT MAX(synced_at) as last_sync
                   FROM receipts
                   WHERE status = 'synced'"""
            ).fetchone()
            last_sync = last_sync_row['last_sync'] if last_sync_row else None

            # Calculate percent full
            percent_full = (pending / BUFFER_CAPACITY) * 100 if BUFFER_CAPACITY > 0 else 0

            return {
                "pending": pending,
                "dlq": dlq,
                "percent_full": round(percent_full, 2),
                "last_sync": last_sync
            }

    except sqlite3.Error as e:
        logger.error(f"Error fetching buffer status: {e}")
        return {
            "pending": 0,
            "dlq": 0,
            "percent_full": 0.0,
            "last_sync": None
        }


def get_sales_today() -> Dict:
    """
    Get sales data for current day

    Returns:
        Dict with keys: total_revenue, total_count, hourly_data, date
    """
    try:
        with get_db() as db:
            today = date.today().isoformat()

            # Total sales today
            total_row = db.execute(
                """SELECT
                       COUNT(*) as count,
                       SUM(total) as revenue
                   FROM receipts
                   WHERE DATE(created_at) = ?
                   AND type = 'sale'""",
                (today,)
            ).fetchone()

            total_count = total_row['count'] if total_row else 0
            total_revenue = float(total_row['revenue'] or 0)

            # Hourly breakdown
            hourly_rows = db.execute(
                """SELECT
                       CAST(strftime('%H', created_at) AS INTEGER) as hour,
                       COUNT(*) as count,
                       SUM(total) as revenue
                   FROM receipts
                   WHERE DATE(created_at) = ?
                   AND type = 'sale'
                   GROUP BY hour
                   ORDER BY hour""",
                (today,)
            ).fetchall()

            hourly_data = [
                {
                    "hour": row['hour'],
                    "count": row['count'],
                    "revenue": float(row['revenue'] or 0)
                }
                for row in hourly_rows
            ]

            return {
                "total_revenue": total_revenue,
                "total_count": total_count,
                "hourly_data": hourly_data,
                "date": today
            }

    except sqlite3.Error as e:
        logger.error(f"Error fetching sales today: {e}")
        return {
            "total_revenue": 0.0,
            "total_count": 0,
            "hourly_data": [],
            "date": date.today().isoformat()
        }


def check_buffer_accessible() -> bool:
    """
    Check if buffer.db is accessible (for health checks)

    Returns:
        True if database is accessible, False otherwise
    """
    try:
        with get_db() as db:
            # Simple query to verify connection
            db.execute("SELECT 1").fetchone()
            return True
    except Exception as e:
        logger.error(f"Buffer database not accessible: {e}")
        return False
