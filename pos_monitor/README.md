# POS Monitor

**Local monitoring dashboard for POS terminals**

## Overview

POS Monitor is a lightweight FastAPI service that provides real-time monitoring of POS terminal status without dependency on Odoo. It reads data directly from the KKT Adapter's `buffer.db` (SQLite) in read-only mode.

## Features

- **Real-time status**: Cash/card balance, buffer status, KKT status
- **WebSocket updates**: Auto-refresh every 2 seconds
- **Alerts panel**: P1/P2/INFO alerts with recommended actions
- **Sales data**: Today's sales with hourly breakdown
- **Health monitoring**: Circuit Breaker state, OFD status
- **Read-only access**: No risk of corrupting buffer.db

## Quick Start

### 1. Prerequisites

- Docker and Docker Compose installed
- KKT Adapter running on port 8000
- `buffer.db` exists at `../kkt_adapter/data/buffer.db`

### 2. Build and Run

```bash
# Build container
docker-compose build

# Start service
docker-compose up -d

# Check logs
docker logs pos_monitor -f
```

### 3. Access Dashboard

- **Web UI**: http://localhost:8001
- **API Docs**: http://localhost:8001/api/docs
- **Health Check**: http://localhost:8001/health

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/status` | GET | Current POS status (cash, card, buffer, KKT) |
| `/api/v1/alerts` | GET | Active alerts (P1, P2, INFO) |
| `/api/v1/sales/today` | GET | Sales data for current day |
| `/ws/realtime` | WebSocket | Real-time status updates (2s interval) |
| `/health` | GET | Health check |

## Configuration

Environment variables (in `docker-compose.yml`):

- `BUFFER_DB_PATH`: Path to buffer.db (default: `/app/data/buffer.db`)
- `KKT_ADAPTER_URL`: KKT Adapter URL (default: `http://localhost:8000`)
- `LOG_LEVEL`: Logging level (default: `INFO`)

## Architecture

```
┌─────────────────────────────────────────────────────┐
│ PC на точке (Windows/Linux)                         │
├─────────────────────────────────────────────────────┤
│                                                      │
│  ┌──────────────────┐      ┌──────────────────┐   │
│  │ KKT Adapter      │      │ POS Monitor      │   │
│  │ (FastAPI:8000)   │◄─────┤ (FastAPI:8001)   │   │
│  │                  │      │                  │   │
│  │ - Fiscalization  │      │ - Dashboard UI   │   │
│  │ - Buffer CRUD    │      │ - Read-Only API  │   │
│  │ - OFD Sync       │      │ - WebSocket      │   │
│  └────────┬─────────┘      └────────┬─────────┘   │
│           │                         │              │
│           ▼                         │              │
│  ┌──────────────────┐              │              │
│  │ buffer.db        │◄─────────────┘              │
│  │ (SQLite WAL)     │ Read-Only Access            │
│  └──────────────────┘                              │
└─────────────────────────────────────────────────────┘
```

## Development

### Run Locally (without Docker)

```bash
# Install dependencies
pip install -r requirements.txt

# Run application
cd pos_monitor
python -m app.main

# Or with uvicorn
uvicorn app.main:app --reload --port 8001
```

### Run Tests

```bash
# Unit tests
pytest tests/unit/pos_monitor/ -v

# Integration tests
pytest tests/integration/pos_monitor/ -v

# All tests
pytest tests/ -k pos_monitor -v
```

## Alerts

| Level | Threshold | Message | Action |
|-------|-----------|---------|--------|
| **P1** | Buffer ≥100% | Буфер переполнен | Вызовите техподдержку немедленно |
| **P1** | DLQ > 0 | Ошибки отправки в ОФД | Вызовите администратора |
| **P1** | KKT offline | ККТ Adapter не отвечает | Перезапустите контейнер |
| **P2** | Buffer ≥80% | Буфер заполнен | Проверьте сетевое подключение |
| **P2** | CB OPEN | ОФД недоступен | Ожидайте восстановления связи |

## Troubleshooting

### Dashboard not loading

```bash
# Check service health
curl http://localhost:8001/health

# Check logs
docker logs pos_monitor

# Verify buffer.db exists
ls -la ../kkt_adapter/data/buffer.db
```

### WebSocket connection failed

- Check firewall allows port 8001
- Verify KKT Adapter is running
- Check browser console for errors

### No data displayed

- Verify `buffer.db` has data:
  ```bash
  sqlite3 ../kkt_adapter/data/buffer.db "SELECT COUNT(*) FROM receipts"
  ```
- Check POS session is open:
  ```bash
  sqlite3 ../kkt_adapter/data/buffer.db "SELECT * FROM pos_sessions WHERE status='open'"
  ```

## Security

**Phase 1 (MVP):**
- No authentication (local network only)
- Port 8001 NOT exposed to internet
- Read-only access to buffer.db

**Phase 2 (Future):**
- Basic HTTP authentication
- JWT tokens for API access
- Role-based access control

## References

- **Spec**: `docs/POS_MONITOR_SPEC.md`
- **JIRA**: OPTERP-105
- **Related**: OPTERP-104 (Session State Persistence)
