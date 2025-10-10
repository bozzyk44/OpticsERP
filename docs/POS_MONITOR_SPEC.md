# POS Monitor - Technical Specification

**Version:** 1.0
**Date:** 2025-10-09
**Component:** Local monitoring dashboard for POS terminals
**Related:** OPTERP-104 (Session State Persistence)

---

## 1. Overview

**Purpose:** Real-time monitoring of POS terminal status from local network without dependency on Odoo.

**Use Cases:**
- Manager checks cash balance from tablet without opening POS
- Cashier monitors buffer status during offline mode
- Administrator receives local alerts for critical issues
- Accountant verifies daily sales without accessing Odoo

**Deployment:** Docker container on same PC as KKT Adapter

---

## 2. Architecture

### 2.1 System Context

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
│  │                  │                              │
│  │ - receipts       │                              │
│  │ - pos_sessions   │                              │
│  │ - cash_trans     │                              │
│  └──────────────────┘                              │
│                                                      │
└─────────────────────────────────────────────────────┘
                     │
                     │ HTTP :8001
                     ▼
         ┌────────────────────────┐
         │ Browser (tablet/PC)    │
         │ http://192.168.1.X:8001│
         └────────────────────────┘
```

### 2.2 Technology Stack

| Component | Technology | Version |
|-----------|-----------|---------|
| **Backend** | Python + FastAPI | 3.11+ / 0.104+ |
| **Frontend** | React + TailwindCSS | 18+ / 3+ |
| **Real-time** | WebSocket (FastAPI) | - |
| **Charts** | Chart.js / Recharts | 4+ / 2+ |
| **Data Source** | SQLite (read-only) | 3.40+ |
| **Container** | Docker + Compose | 24+ |
| **HTTP Server** | Uvicorn | 0.24+ |

---

## 3. Component Specification

### 3.1 Backend (FastAPI)

**File Structure:**
```
pos_monitor/
├── app/
│   ├── main.py              # FastAPI app, routes
│   ├── database.py          # Read-only SQLite connection
│   ├── models.py            # Pydantic models
│   ├── alerts.py            # Alert checking logic
│   ├── websocket.py         # WebSocket handler
│   └── config.py            # Configuration
├── static/                  # React build (production)
├── requirements.txt
├── Dockerfile
└── docker-compose.yml
```

#### 3.1.1 API Endpoints

| Endpoint | Method | Purpose | Response Time |
|----------|--------|---------|---------------|
| `/api/v1/status` | GET | Current POS status | <100ms |
| `/api/v1/inventory/top` | GET | Top 10 products | <200ms |
| `/api/v1/sales/today` | GET | Sales for today | <150ms |
| `/api/v1/alerts` | GET | Active alerts | <50ms |
| `/ws/realtime` | WebSocket | Real-time updates | 2s interval |
| `/health` | GET | Health check | <10ms |

#### 3.1.2 Data Models

```python
# pos_monitor/app/models.py
from pydantic import BaseModel
from typing import Optional, List

class POSStatus(BaseModel):
    """Overall POS status"""
    cash_balance: float
    card_balance: float
    buffer: BufferStatus
    kkt_status: KKTStatus
    timestamp: int

class BufferStatus(BaseModel):
    """Buffer state"""
    pending: int          # Unsent receipts
    dlq: int              # Failed receipts
    percent_full: float   # Buffer capacity %
    last_sync: Optional[int]  # Last successful sync timestamp

class KKTStatus(BaseModel):
    """KKT Adapter status"""
    is_online: bool
    circuit_breaker_state: str  # CLOSED|OPEN|HALF_OPEN
    last_heartbeat: int
    ofd_status: str  # online|offline

class Alert(BaseModel):
    """Alert model"""
    level: str  # P1|P2|INFO
    message: str
    action: str  # Recommended action
    timestamp: int

class SalesDataPoint(BaseModel):
    """Sales data for charts"""
    hour: int
    revenue: float
    count: int
```

#### 3.1.3 Database Access (Read-Only)

```python
# pos_monitor/app/database.py
import sqlite3
from contextlib import contextmanager

BUFFER_DB_PATH = "../kkt_adapter/data/buffer.db"

@contextmanager
def get_db():
    """Read-only connection to buffer.db"""
    conn = sqlite3.connect(
        f"file:{BUFFER_DB_PATH}?mode=ro",  # ⚠️ Read-only mode
        uri=True,
        check_same_thread=False
    )
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

def get_cash_balance() -> tuple[float, float]:
    """Get current cash and card balance"""
    with get_db() as db:
        row = db.execute(
            """SELECT cash_balance, card_balance
               FROM pos_sessions
               WHERE status = 'open'"""
        ).fetchone()

        if row:
            return row['cash_balance'], row['card_balance']
        return 0.0, 0.0

def get_buffer_status() -> dict:
    """Get buffer state"""
    with get_db() as db:
        pending = db.execute(
            "SELECT COUNT(*) as count FROM receipts WHERE status = 'pending'"
        ).fetchone()['count']

        dlq = db.execute(
            "SELECT COUNT(*) as count FROM dlq"
        ).fetchone()['count']

        last_sync = db.execute(
            """SELECT MAX(synced_at) as last_sync
               FROM receipts
               WHERE status = 'synced'"""
        ).fetchone()['last_sync']

        # Buffer capacity (assume max 500 receipts)
        percent_full = (pending / 500) * 100

        return {
            "pending": pending,
            "dlq": dlq,
            "percent_full": percent_full,
            "last_sync": last_sync
        }
```

#### 3.1.4 Alert Logic

```python
# pos_monitor/app/alerts.py
import time
import requests
from typing import List
from .models import Alert

def check_alerts() -> List[Alert]:
    """Check all alert conditions"""
    alerts = []

    # 1. Buffer overflow
    buffer = get_buffer_status()
    if buffer['pending'] >= 100:
        alerts.append(Alert(
            level="P1",
            message=f"Буфер переполнен: {buffer['pending']} чеков",
            action="Проверьте связь с ОФД. Вызовите техподдержку.",
            timestamp=int(time.time())
        ))
    elif buffer['pending'] >= 50:
        alerts.append(Alert(
            level="P2",
            message=f"Буфер заполнен: {buffer['pending']} чеков",
            action="Дождитесь синхронизации или проверьте сеть.",
            timestamp=int(time.time())
        ))

    # 2. DLQ warnings
    if buffer['dlq'] > 0:
        alerts.append(Alert(
            level="P1",
            message=f"Ошибки отправки: {buffer['dlq']} чеков",
            action="КРИТИЧНО: Чеки не отправлены в ОФД. Вызовите администратора.",
            timestamp=int(time.time())
        ))

    # 3. KKT Adapter offline
    try:
        response = requests.get("http://localhost:8000/health", timeout=2)
        if response.status_code != 200:
            raise Exception("Unhealthy")
    except:
        alerts.append(Alert(
            level="P1",
            message="ККТ Adapter не отвечает",
            action="Перезапустите контейнер kkt_adapter.",
            timestamp=int(time.time())
        ))

    # 4. OFD offline (check Circuit Breaker state)
    try:
        response = requests.get("http://localhost:8000/v1/health", timeout=2)
        health = response.json()
        if health.get('circuit_breaker_state') == 'OPEN':
            alerts.append(Alert(
                level="P2",
                message="ОФД недоступен (Circuit Breaker OPEN)",
                action="Чеки сохраняются локально. Ожидайте восстановления связи.",
                timestamp=int(time.time())
            ))
    except:
        pass

    return alerts
```

#### 3.1.5 WebSocket Handler

```python
# pos_monitor/app/websocket.py
from fastapi import WebSocket
import asyncio
import json

async def websocket_handler(websocket: WebSocket):
    """Real-time updates via WebSocket"""
    await websocket.accept()

    last_status = None

    try:
        while True:
            # Fetch current status
            cash, card = get_cash_balance()
            buffer = get_buffer_status()
            alerts = check_alerts()

            current_status = {
                "cash_balance": cash,
                "card_balance": card,
                "buffer": buffer,
                "alerts": [a.dict() for a in alerts],
                "timestamp": int(time.time())
            }

            # Send only if changed
            if current_status != last_status:
                await websocket.send_text(json.dumps(current_status))
                last_status = current_status

            await asyncio.sleep(2)  # Update every 2 seconds

    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        await websocket.close()
```

#### 3.1.6 Main Application

```python
# pos_monitor/app/main.py
from fastapi import FastAPI, WebSocket
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from .database import get_cash_balance, get_buffer_status
from .alerts import check_alerts
from .websocket import websocket_handler
from .models import POSStatus, Alert

app = FastAPI(title="POS Monitor", version="1.0.0")

# CORS for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/v1/status", response_model=POSStatus)
async def get_status():
    """Get current POS status"""
    cash, card = get_cash_balance()
    buffer = get_buffer_status()

    return POSStatus(
        cash_balance=cash,
        card_balance=card,
        buffer=buffer,
        kkt_status={"is_online": True, "circuit_breaker_state": "CLOSED"},
        timestamp=int(time.time())
    )

@app.get("/api/v1/alerts", response_model=List[Alert])
async def get_alerts():
    """Get active alerts"""
    return check_alerts()

@app.websocket("/ws/realtime")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket for real-time updates"""
    await websocket_handler(websocket)

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "ok"}

# Serve React SPA
app.mount("/", StaticFiles(directory="static", html=True), name="static")
```

---

### 3.2 Frontend (React)

**File Structure:**
```
pos_monitor/frontend/
├── src/
│   ├── App.jsx              # Main app component
│   ├── components/
│   │   ├── CashBalanceCard.jsx
│   │   ├── BufferStatusCard.jsx
│   │   ├── KKTStatusCard.jsx
│   │   ├── AlertsPanel.jsx
│   │   └── SalesChart.jsx
│   ├── hooks/
│   │   └── useWebSocket.js  # WebSocket hook
│   ├── utils/
│   │   └── formatters.js    # Currency, date formatters
│   └── index.jsx
├── public/
├── package.json
└── tailwind.config.js
```

#### 3.2.1 Dashboard UI Mockup

```
┌────────────────────────────────────────────────────┐
│ 🖥️ POS Monitor - Касса #1          🟢 Online      │
├────────────────────────────────────────────────────┤
│                                                     │
│  ┌──────────────────┐  ┌──────────────────┐       │
│  │ 💰 Наличные      │  │ 💳 Карты         │       │
│  │                  │  │                  │       │
│  │   50,000₽       │  │   120,000₽      │       │
│  │   +12,500₽ ↑    │  │   +34,000₽ ↑    │       │
│  └──────────────────┘  └──────────────────┘       │
│                                                     │
│  ┌──────────────────┐  ┌──────────────────┐       │
│  │ 📨 Буфер         │  │ 🖨️ ККТ           │       │
│  │                  │  │                  │       │
│  │  12 чеков       │  │  🟢 Онлайн       │       │
│  │  5% заполнено   │  │  ОФД: OK         │       │
│  └──────────────────┘  └──────────────────┘       │
│                                                     │
│  ┌──────────────────────────────────────────────┐ │
│  │ 🚨 Алерты                                    │ │
│  │                                               │ │
│  │  🟢 Нет активных алертов                     │ │
│  │                                               │ │
│  └──────────────────────────────────────────────┘ │
│                                                     │
│  ┌──────────────────────────────────────────────┐ │
│  │ 📊 Продажи за день                           │ │
│  │                                               │ │
│  │    50k ┤     ╭─╮                             │ │
│  │    40k ┤   ╭─╯ ╰─╮                           │ │
│  │    30k ┤  ╭╯     ╰╮                          │ │
│  │    20k ┤╭─╯       ╰─╮                        │ │
│  │    10k ┼──────────────╮                      │ │
│  │        09 10 11 12 13 14 15 16 17 18 19     │ │
│  │                                               │ │
│  │  Всего: 170,000₽  |  53 чека                │ │
│  └──────────────────────────────────────────────┘ │
│                                                     │
│  Last updated: 14:23:45                            │
└────────────────────────────────────────────────────┘
```

#### 3.2.2 Main Component

```jsx
// pos_monitor/frontend/src/App.jsx
import React from 'react';
import { useWebSocket } from './hooks/useWebSocket';
import CashBalanceCard from './components/CashBalanceCard';
import BufferStatusCard from './components/BufferStatusCard';
import KKTStatusCard from './components/KKTStatusCard';
import AlertsPanel from './components/AlertsPanel';
import SalesChart from './components/SalesChart';

function App() {
  const { status, isConnected } = useWebSocket('ws://localhost:8001/ws/realtime');

  if (!isConnected) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto"></div>
          <p className="mt-4 text-gray-600">Подключение к POS Monitor...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-100 p-6">
      {/* Header */}
      <header className="mb-6 flex justify-between items-center">
        <h1 className="text-3xl font-bold text-gray-800">
          🖥️ POS Monitor - Касса #1
        </h1>
        <div className="flex items-center">
          <span className={`h-3 w-3 rounded-full ${isConnected ? 'bg-green-500' : 'bg-red-500'} mr-2`}></span>
          <span className="text-sm text-gray-600">
            {isConnected ? 'Online' : 'Offline'}
          </span>
        </div>
      </header>

      {/* Main Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-6">
        <CashBalanceCard balance={status.cash_balance} />
        <CardBalanceCard balance={status.card_balance} />
        <BufferStatusCard buffer={status.buffer} />
        <KKTStatusCard status={status.kkt_status} />
      </div>

      {/* Alerts Panel */}
      <AlertsPanel alerts={status.alerts} />

      {/* Sales Chart */}
      <SalesChart />

      {/* Footer */}
      <footer className="mt-6 text-center text-sm text-gray-500">
        Last updated: {new Date(status.timestamp * 1000).toLocaleTimeString('ru-RU')}
      </footer>
    </div>
  );
}

export default App;
```

#### 3.2.3 WebSocket Hook

```jsx
// pos_monitor/frontend/src/hooks/useWebSocket.js
import { useState, useEffect, useRef } from 'react';

export function useWebSocket(url) {
  const [status, setStatus] = useState({
    cash_balance: 0,
    card_balance: 0,
    buffer: { pending: 0, dlq: 0, percent_full: 0 },
    alerts: [],
    timestamp: Date.now() / 1000
  });
  const [isConnected, setIsConnected] = useState(false);
  const wsRef = useRef(null);

  useEffect(() => {
    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => {
      console.log('✅ WebSocket connected');
      setIsConnected(true);
    };

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      setStatus(data);
    };

    ws.onerror = (error) => {
      console.error('❌ WebSocket error:', error);
      setIsConnected(false);
    };

    ws.onclose = () => {
      console.log('WebSocket disconnected, reconnecting...');
      setIsConnected(false);

      // Reconnect after 3 seconds
      setTimeout(() => {
        window.location.reload();
      }, 3000);
    };

    return () => {
      ws.close();
    };
  }, [url]);

  return { status, isConnected };
}
```

---

### 3.3 Docker Deployment

#### 3.3.1 Dockerfile

```dockerfile
# pos_monitor/Dockerfile
FROM node:18-alpine AS frontend-builder

WORKDIR /app/frontend

# Install dependencies
COPY frontend/package*.json ./
RUN npm ci

# Build React app
COPY frontend/ ./
RUN npm run build

# ----- Backend -----
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY app/ ./app/

# Copy frontend build from previous stage
COPY --from=frontend-builder /app/frontend/build ./static

# Expose port
EXPOSE 8001

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD python -c "import requests; requests.get('http://localhost:8001/health', timeout=2)"

# Run application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001", "--workers", "1"]
```

#### 3.3.2 docker-compose.yml Integration

```yaml
# docker-compose.yml (updated)
version: '3.8'

services:
  kkt_adapter:
    build: ./kkt_adapter
    container_name: kkt_adapter
    ports:
      - "8000:8000"
    volumes:
      - ./kkt_adapter/data:/app/data
      - ./kkt_adapter/config.toml:/app/config.toml
    restart: unless-stopped
    networks:
      - pos_network

  pos_monitor:
    build: ./pos_monitor
    container_name: pos_monitor
    ports:
      - "8001:8001"
    volumes:
      - ./kkt_adapter/data:/app/data:ro  # ⚠️ Read-only access to buffer.db
    depends_on:
      - kkt_adapter
    restart: unless-stopped
    networks:
      - pos_network
    environment:
      - BUFFER_DB_PATH=/app/data/buffer.db

networks:
  pos_network:
    driver: bridge
```

---

## 4. Features

### 4.1 Core Features (MVP)

| Feature | Priority | Description |
|---------|----------|-------------|
| Real-time balance | P0 | Cash and card balance updates every 2s |
| Buffer status | P0 | Pending receipts, DLQ, percentage full |
| KKT status | P0 | Online/offline indicator, Circuit Breaker state |
| Alerts panel | P0 | P1/P2 alerts with action recommendations |
| WebSocket updates | P0 | No page refresh required |
| Mobile-responsive | P1 | Tablet/phone access |

### 4.2 Advanced Features (Phase 2)

| Feature | Priority | Description |
|---------|----------|-------------|
| Sales chart | P1 | Hourly revenue chart for current day |
| Top products | P2 | Top 10 selling products from cache |
| Sound alerts | P2 | Audio notification for P1 alerts |
| Multi-POS view | P2 | Monitor multiple POS from single dashboard |
| Historical data | P3 | 7-day sales history |
| Export data | P3 | CSV export for reconciliation |

---

## 5. Performance Requirements

| Metric | Target | Measurement |
|--------|--------|-------------|
| **API Response Time** | <200ms (P95) | `/api/v1/status` |
| **WebSocket Latency** | <100ms | Message delivery |
| **UI Render** | <16ms (60 FPS) | React component updates |
| **Memory Usage** | <100 MB | Docker container |
| **DB Query Time** | <50ms | SQLite read queries |
| **Update Frequency** | 2s | WebSocket polling interval |

---

## 6. Security

### 6.1 Access Control

**Phase 1 (MVP):**
- No authentication (local network only)
- Port 8001 NOT exposed to internet

**Phase 2:**
- Basic HTTP auth (username/password)
- JWT tokens for API access
- Role-based access (admin/cashier/viewer)

### 6.2 Network Isolation

**Firewall Rules:**
```bash
# Allow only local network
iptables -A INPUT -p tcp --dport 8001 -s 192.168.1.0/24 -j ACCEPT
iptables -A INPUT -p tcp --dport 8001 -j DROP
```

**Docker Network:**
- Use bridge network (not host)
- No direct internet access required

---

## 7. Monitoring & Logging

### 7.1 Application Logs

```python
# pos_monitor/app/main.py
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/app/logs/pos_monitor.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

@app.middleware("http")
async def log_requests(request, call_next):
    logger.info(f"{request.method} {request.url.path}")
    response = await call_next(request)
    logger.info(f"Status: {response.status_code}")
    return response
```

### 7.2 Prometheus Metrics (Optional)

```python
from prometheus_client import Counter, Histogram, generate_latest

# Metrics
http_requests_total = Counter('http_requests_total', 'Total HTTP requests')
websocket_connections = Counter('websocket_connections_total', 'Total WebSocket connections')
api_response_time = Histogram('api_response_time_seconds', 'API response time')

@app.get("/metrics")
async def metrics():
    return Response(content=generate_latest(), media_type="text/plain")
```

---

## 8. Testing Strategy

### 8.1 Unit Tests

```python
# tests/unit/test_database.py
import pytest
from pos_monitor.app.database import get_cash_balance, get_buffer_status

def test_get_cash_balance(mock_db):
    """Test cash balance retrieval"""
    cash, card = get_cash_balance()
    assert cash >= 0
    assert card >= 0

def test_get_buffer_status(mock_db):
    """Test buffer status retrieval"""
    status = get_buffer_status()
    assert 'pending' in status
    assert 'dlq' in status
    assert status['percent_full'] <= 100
```

### 8.2 Integration Tests

```python
# tests/integration/test_api.py
from fastapi.testclient import TestClient
from pos_monitor.app.main import app

client = TestClient(app)

def test_get_status():
    """Test /api/v1/status endpoint"""
    response = client.get("/api/v1/status")
    assert response.status_code == 200
    data = response.json()
    assert 'cash_balance' in data
    assert 'buffer' in data

def test_websocket():
    """Test WebSocket connection"""
    with client.websocket_connect("/ws/realtime") as websocket:
        data = websocket.receive_json()
        assert 'cash_balance' in data
```

### 8.3 E2E Tests (Playwright)

```javascript
// tests/e2e/dashboard.spec.js
import { test, expect } from '@playwright/test';

test('Dashboard loads and displays data', async ({ page }) => {
  await page.goto('http://localhost:8001');

  // Check main cards are visible
  await expect(page.locator('text=Наличные')).toBeVisible();
  await expect(page.locator('text=Карты')).toBeVisible();
  await expect(page.locator('text=Буфер')).toBeVisible();

  // Wait for WebSocket data
  await page.waitForTimeout(3000);

  // Check balance is updated
  const balance = await page.locator('[data-testid="cash-balance"]').textContent();
  expect(balance).toMatch(/\d+₽/);
});
```

---

## 9. Deployment Checklist

### 9.1 Pre-deployment

- [ ] `buffer.db` exists with correct schema (OPTERP-104)
- [ ] KKT Adapter is running on port 8000
- [ ] Docker and Docker Compose installed
- [ ] Port 8001 is available
- [ ] Firewall allows local network access to 8001

### 9.2 Deployment Steps

```bash
# 1. Build containers
cd pos_monitor
docker-compose build

# 2. Start services
docker-compose up -d

# 3. Verify health
curl http://localhost:8001/health
# Expected: {"status": "ok"}

# 4. Test WebSocket
# Open browser: http://localhost:8001
# Expected: Dashboard loads with real-time data

# 5. Check logs
docker logs pos_monitor -f
```

### 9.3 Post-deployment

- [ ] Dashboard accessible from tablet/PC in local network
- [ ] Real-time updates work (WebSocket)
- [ ] Alerts panel shows correct status
- [ ] No errors in logs (`docker logs pos_monitor`)
- [ ] Buffer status matches KKT Adapter data

---

## 10. Maintenance

### 10.1 Log Rotation

```yaml
# docker-compose.yml (add logging config)
services:
  pos_monitor:
    # ... existing config ...
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

### 10.2 Backup Strategy

**No backups needed** - POS Monitor reads data from `buffer.db` (already backed up with KKT Adapter)

### 10.3 Update Procedure

```bash
# 1. Pull latest code
git pull origin main

# 2. Rebuild container
docker-compose build pos_monitor

# 3. Restart with zero downtime
docker-compose up -d --no-deps pos_monitor

# 4. Verify
curl http://localhost:8001/health
```

---

## 11. Future Enhancements

### Phase 2 (2-3 weeks)

1. **Multi-POS Support**
   - Monitor 2+ POS terminals from single dashboard
   - Grid view with status indicators

2. **Historical Data**
   - 7-day sales chart
   - Week-over-week comparison

3. **Sound Alerts**
   - Audio notification for P1 alerts
   - Configurable alert sounds

4. **Export Functionality**
   - CSV export for reconciliation
   - PDF reports

### Phase 3 (3-4 weeks)

1. **Mobile App**
   - React Native app (iOS/Android)
   - Push notifications for alerts

2. **Advanced Analytics**
   - Product category breakdown
   - Hourly traffic patterns
   - Cashier performance

3. **Integration with Odoo**
   - Sync status to Odoo (optional)
   - Cross-reference with ERP data

---

## 12. Dependencies

### 12.1 Backend Requirements

```txt
# pos_monitor/requirements.txt
fastapi==0.104.1
uvicorn==0.24.0
websockets==12.0
pydantic==2.5.0
requests==2.31.0
prometheus-client==0.19.0  # Optional
```

### 12.2 Frontend Requirements

```json
{
  "name": "pos-monitor-frontend",
  "version": "1.0.0",
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "chart.js": "^4.4.0",
    "react-chartjs-2": "^5.2.0",
    "tailwindcss": "^3.3.0"
  },
  "devDependencies": {
    "@vitejs/plugin-react": "^4.2.0",
    "vite": "^5.0.0"
  }
}
```

---

## 13. Acceptance Criteria

### MVP Checklist

- [ ] Dashboard loads on `http://localhost:8001`
- [ ] Cash balance updates in real-time (2s interval)
- [ ] Card balance updates in real-time
- [ ] Buffer status shows pending/DLQ counts
- [ ] KKT status indicator (online/offline)
- [ ] Alerts panel shows active alerts
- [ ] WebSocket reconnects automatically on disconnect
- [ ] Mobile-responsive layout (tablet/phone)
- [ ] Health check endpoint returns 200
- [ ] No errors in browser console
- [ ] Container restarts automatically on failure
- [ ] Read-only access to `buffer.db` (no writes)

---

## 14. References

- **Related Tasks:** OPTERP-104 (Session State Persistence)
- **Related Docs:** `docs/5. Руководство по офлайн-режиму.md`
- **Tech Stack Docs:**
  - FastAPI: https://fastapi.tiangolo.com
  - React: https://react.dev
  - WebSocket API: https://developer.mozilla.org/en-US/docs/Web/API/WebSocket
  - Chart.js: https://www.chartjs.org
  - TailwindCSS: https://tailwindcss.com

---

**End of Specification**
