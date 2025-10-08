-- SQLite Schema for KKT Adapter Offline Buffer
-- Author: AI Bootstrap
-- Date: 2025-10-08
-- Purpose: Offline buffer for fiscal receipts (54-ФЗ compliant)
-- Reference: CLAUDE.md §4.1

-- ====================
-- Main Receipts Table
-- ====================

CREATE TABLE IF NOT EXISTS receipts (
  -- Primary Key
  id TEXT PRIMARY KEY,              -- UUIDv4 (Idempotency-Key)

  -- POS Identification
  pos_id TEXT NOT NULL,             -- e.g., "POS-001"

  -- Timestamps
  created_at INTEGER NOT NULL,      -- Unix timestamp (local time)

  -- Hybrid Logical Clock (HLC) for ordering
  -- See docs/5. Руководство по офлайн-режиму.md §5.5
  hlc_local_time INTEGER NOT NULL,      -- Local Unix timestamp
  hlc_logical_counter INTEGER NOT NULL, -- Monotonic counter
  hlc_server_time INTEGER,              -- Server time (assigned during sync)

  -- Fiscal Data
  fiscal_doc TEXT NOT NULL,         -- JSON: ФФД 1.2 compliant document

  -- Sync Status
  status TEXT NOT NULL DEFAULT 'pending',  -- pending|syncing|synced|failed
  retry_count INTEGER DEFAULT 0,           -- Number of retry attempts
  last_error TEXT,                         -- Last error message
  synced_at INTEGER,                       -- Unix timestamp of successful sync

  -- Constraints
  CHECK (status IN ('pending', 'syncing', 'synced', 'failed')),
  CHECK (retry_count >= 0),
  CHECK (hlc_logical_counter >= 0)
);

-- ====================
-- Indexes
-- ====================

-- For sync worker (select pending receipts)
CREATE INDEX IF NOT EXISTS idx_receipts_status
  ON receipts(status);

-- For time-based queries
CREATE INDEX IF NOT EXISTS idx_receipts_created_at
  ON receipts(created_at);

-- For HLC ordering (critical for conflict resolution)
CREATE INDEX IF NOT EXISTS idx_receipts_hlc
  ON receipts(hlc_server_time, hlc_local_time, hlc_logical_counter);

-- For per-POS queries
CREATE INDEX IF NOT EXISTS idx_receipts_pos_id
  ON receipts(pos_id);

-- For retry logic (find receipts with high retry_count)
CREATE INDEX IF NOT EXISTS idx_receipts_retry
  ON receipts(retry_count, status);

-- ====================
-- Dead Letter Queue
-- ====================

CREATE TABLE IF NOT EXISTS dlq (
  id TEXT PRIMARY KEY,                  -- UUIDv4
  original_receipt_id TEXT NOT NULL,    -- Reference to receipts.id
  failed_at INTEGER NOT NULL,           -- Unix timestamp
  reason TEXT NOT NULL,                 -- Failure reason
  fiscal_doc TEXT NOT NULL,             -- Copy of fiscal document
  retry_attempts INTEGER NOT NULL,      -- Total attempts before DLQ
  last_error TEXT,                      -- Last error message
  resolved_at INTEGER,                  -- Resolution timestamp
  resolved_by TEXT,                     -- User/system who resolved

  FOREIGN KEY (original_receipt_id) REFERENCES receipts(id)
);

CREATE INDEX IF NOT EXISTS idx_dlq_failed_at
  ON dlq(failed_at);

CREATE INDEX IF NOT EXISTS idx_dlq_resolved_at
  ON dlq(resolved_at);

CREATE INDEX IF NOT EXISTS idx_dlq_original_receipt
  ON dlq(original_receipt_id);

-- ====================
-- Event Sourcing
-- ====================

CREATE TABLE IF NOT EXISTS buffer_events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  event_type TEXT NOT NULL,         -- Event type (see CHECK constraint)
  receipt_id TEXT,                  -- Optional reference to receipt
  timestamp INTEGER NOT NULL,       -- Unix timestamp
  metadata TEXT,                    -- Optional JSON metadata

  -- Event Types:
  -- - receipt_added: New receipt added to buffer
  -- - receipt_synced: Receipt successfully synced to OFD
  -- - receipt_failed: Receipt failed sync (moved to DLQ)
  -- - circuit_opened: Circuit Breaker opened
  -- - circuit_closed: Circuit Breaker closed
  -- - sync_started: Sync worker started
  -- - sync_completed: Sync worker completed
  -- - sync_failed: Sync worker failed

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

CREATE INDEX IF NOT EXISTS idx_events_timestamp
  ON buffer_events(timestamp);

CREATE INDEX IF NOT EXISTS idx_events_type
  ON buffer_events(event_type);

CREATE INDEX IF NOT EXISTS idx_events_receipt_id
  ON buffer_events(receipt_id);

-- ====================
-- Configuration Table
-- ====================

CREATE TABLE IF NOT EXISTS config (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL,
  updated_at INTEGER NOT NULL      -- Unix timestamp
);

-- Insert default configuration
INSERT OR IGNORE INTO config (key, value, updated_at)
VALUES
  ('version', '1.0.0', strftime('%s', 'now')),
  ('buffer_capacity', '200', strftime('%s', 'now')),
  ('circuit_breaker_threshold', '5', strftime('%s', 'now')),
  ('circuit_breaker_timeout', '60', strftime('%s', 'now')),
  ('max_retry_attempts', '20', strftime('%s', 'now'));

-- ====================
-- Views for Monitoring
-- ====================

-- Buffer status view
CREATE VIEW IF NOT EXISTS v_buffer_status AS
SELECT
  COUNT(*) AS total_receipts,
  SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) AS pending,
  SUM(CASE WHEN status = 'syncing' THEN 1 ELSE 0 END) AS syncing,
  SUM(CASE WHEN status = 'synced' THEN 1 ELSE 0 END) AS synced,
  SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) AS failed,
  (SELECT COUNT(*) FROM dlq WHERE resolved_at IS NULL) AS dlq_size,
  (SELECT value FROM config WHERE key = 'buffer_capacity') AS capacity,
  ROUND(
    CAST(SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) AS FLOAT) /
    CAST((SELECT value FROM config WHERE key = 'buffer_capacity') AS FLOAT) * 100,
    2
  ) AS percent_full
FROM receipts;

-- Recent events view (last 100)
CREATE VIEW IF NOT EXISTS v_recent_events AS
SELECT
  id,
  event_type,
  receipt_id,
  datetime(timestamp, 'unixepoch') AS event_time,
  metadata
FROM buffer_events
ORDER BY timestamp DESC
LIMIT 100;

-- ====================
-- Triggers
-- ====================

-- Automatically log receipt_added event
CREATE TRIGGER IF NOT EXISTS trg_receipt_added
AFTER INSERT ON receipts
BEGIN
  INSERT INTO buffer_events (event_type, receipt_id, timestamp, metadata)
  VALUES (
    'receipt_added',
    NEW.id,
    strftime('%s', 'now'),
    json_object('pos_id', NEW.pos_id, 'status', NEW.status)
  );
END;

-- Automatically log receipt_synced event
CREATE TRIGGER IF NOT EXISTS trg_receipt_synced
AFTER UPDATE ON receipts
WHEN NEW.status = 'synced' AND OLD.status != 'synced'
BEGIN
  INSERT INTO buffer_events (event_type, receipt_id, timestamp, metadata)
  VALUES (
    'receipt_synced',
    NEW.id,
    strftime('%s', 'now'),
    json_object('retry_count', NEW.retry_count, 'duration_seconds', NEW.synced_at - NEW.created_at)
  );
END;

-- ====================
-- Comments
-- ====================

-- PRAGMA settings (must be set at runtime):
-- PRAGMA journal_mode=WAL;        -- Write-Ahead Logging (CRITICAL)
-- PRAGMA synchronous=FULL;         -- Full fsync (CRITICAL for durability)
-- PRAGMA wal_autocheckpoint=100;   -- Checkpoint every 100 pages
-- PRAGMA cache_size=-64000;        -- 64 MB cache
-- PRAGMA foreign_keys=ON;          -- Enable FK constraints

-- Usage example:
-- 1. Create database: sqlite3 buffer.db < schema.sql
-- 2. Set PRAGMA: sqlite3 buffer.db "PRAGMA journal_mode=WAL; PRAGMA synchronous=FULL;"
-- 3. Verify: sqlite3 buffer.db "PRAGMA journal_mode; PRAGMA synchronous;"
