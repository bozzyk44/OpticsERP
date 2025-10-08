#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Initialize SQLite buffer database for KKT Adapter

Author: AI Bootstrap
Date: 2025-10-08
Purpose: Create and configure SQLite offline buffer with WAL mode and durability settings

Usage:
    python scripts/init/init_buffer_db.py
    python scripts/init/init_buffer_db.py --db-path /custom/path/buffer.db
"""

import sqlite3
import os
import sys
from pathlib import Path

# Default database path
DEFAULT_DB_PATH = "kkt_adapter/data/buffer.db"

# SQLite schema based on CLAUDE.md §4.1
SCHEMA_SQL = """
-- Main receipts table
CREATE TABLE IF NOT EXISTS receipts (
  id TEXT PRIMARY KEY,              -- UUIDv4
  pos_id TEXT NOT NULL,
  created_at INTEGER NOT NULL,      -- Unix timestamp
  hlc_local_time INTEGER NOT NULL,  -- Hybrid Logical Clock
  hlc_logical_counter INTEGER NOT NULL,
  hlc_server_time INTEGER,          -- Assigned during sync
  fiscal_doc TEXT NOT NULL,         -- JSON FFD (Формат Фискальных Данных)
  status TEXT NOT NULL DEFAULT 'pending',  -- pending|syncing|synced|failed
  retry_count INTEGER DEFAULT 0,
  last_error TEXT,
  synced_at INTEGER,
  CHECK (status IN ('pending', 'syncing', 'synced', 'failed'))
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_receipts_status ON receipts(status);
CREATE INDEX IF NOT EXISTS idx_receipts_created_at ON receipts(created_at);
CREATE INDEX IF NOT EXISTS idx_receipts_hlc ON receipts(
  hlc_server_time,
  hlc_local_time,
  hlc_logical_counter
);
CREATE INDEX IF NOT EXISTS idx_receipts_pos_id ON receipts(pos_id);

-- Dead Letter Queue for failed receipts
CREATE TABLE IF NOT EXISTS dlq (
  id TEXT PRIMARY KEY,
  original_receipt_id TEXT NOT NULL,
  failed_at INTEGER NOT NULL,
  reason TEXT NOT NULL,
  fiscal_doc TEXT NOT NULL,
  retry_attempts INTEGER NOT NULL,
  last_error TEXT,
  resolved_at INTEGER,
  resolved_by TEXT,
  FOREIGN KEY (original_receipt_id) REFERENCES receipts(id)
);

CREATE INDEX IF NOT EXISTS idx_dlq_failed_at ON dlq(failed_at);
CREATE INDEX IF NOT EXISTS idx_dlq_resolved_at ON dlq(resolved_at);

-- Event Sourcing table for audit log
CREATE TABLE IF NOT EXISTS buffer_events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  event_type TEXT NOT NULL,
  receipt_id TEXT,
  timestamp INTEGER NOT NULL,
  metadata TEXT,
  CHECK (event_type IN (
    'receipt_added',
    'receipt_synced',
    'receipt_failed',
    'circuit_opened',
    'circuit_closed',
    'sync_started',
    'sync_completed',
    'sync_failed'
  ))
);

CREATE INDEX IF NOT EXISTS idx_events_timestamp ON buffer_events(timestamp);
CREATE INDEX IF NOT EXISTS idx_events_type ON buffer_events(event_type);
CREATE INDEX IF NOT EXISTS idx_events_receipt_id ON buffer_events(receipt_id);
"""


def init_buffer_db(db_path=DEFAULT_DB_PATH):
    """
    Initialize SQLite buffer database with proper settings

    Args:
        db_path: Path to database file

    Returns:
        bool: True if successful
    """
    try:
        # Ensure parent directory exists
        db_file = Path(db_path)
        db_file.parent.mkdir(parents=True, exist_ok=True)

        # Connect to database
        conn = sqlite3.connect(db_path)

        # CRITICAL: Configure for maximum durability (protection from power loss)
        # See CLAUDE.md §4.1
        conn.execute("PRAGMA journal_mode=WAL")        # Write-Ahead Logging
        conn.execute("PRAGMA synchronous=FULL")        # !!!CRITICAL for durability
        conn.execute("PRAGMA wal_autocheckpoint=100")  # Checkpoint every 100 pages
        conn.execute("PRAGMA cache_size=-64000")       # 64 MB cache
        conn.execute("PRAGMA foreign_keys=ON")         # Enable FK constraints

        # Verify WAL mode
        result = conn.execute("PRAGMA journal_mode").fetchone()
        if result[0].upper() != 'WAL':
            print("⚠️  WARNING: WAL mode not enabled!", file=sys.stderr)

        # Verify synchronous mode
        result = conn.execute("PRAGMA synchronous").fetchone()
        if result[0] != 2:  # 2 = FULL
            print("⚠️  WARNING: synchronous=FULL not set!", file=sys.stderr)

        # Create schema
        conn.executescript(SCHEMA_SQL)
        conn.commit()

        # Verify tables
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        ).fetchall()

        expected_tables = ['buffer_events', 'dlq', 'receipts']
        actual_tables = [t[0] for t in tables]

        for expected in expected_tables:
            if expected not in actual_tables:
                print(f"❌ Table '{expected}' not created!", file=sys.stderr)
                return False

        # Insert initial event
        import time
        conn.execute(
            """INSERT INTO buffer_events (event_type, timestamp, metadata)
               VALUES ('sync_started', ?, ?)""",
            (int(time.time()), '{"message": "Database initialized"}')
        )
        conn.commit()

        conn.close()

        print(f"✅ SQLite buffer database initialized: {db_path}")
        print(f"   - WAL mode: enabled")
        print(f"   - Synchronous: FULL")
        print(f"   - Tables: {', '.join(expected_tables)}")
        print(f"   - Size: {db_file.stat().st_size if db_file.exists() else 0} bytes")

        return True

    except Exception as e:
        print(f"❌ Error initializing database: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Initialize SQLite buffer database")
    parser.add_argument(
        "--db-path",
        default=DEFAULT_DB_PATH,
        help=f"Path to database file (default: {DEFAULT_DB_PATH})"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing database"
    )

    args = parser.parse_args()

    # Check if database already exists
    if Path(args.db_path).exists() and not args.force:
        print(f"⚠️  Database already exists: {args.db_path}")
        print("   Use --force to overwrite")
        sys.exit(0)

    success = init_buffer_db(args.db_path)
    sys.exit(0 if success else 1)
