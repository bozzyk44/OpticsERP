# Quick Start Guide
# Быстрый старт для разработчиков

**Время на настройку:** ~5 минут

---

## 🚀 Development Environment (with Mock Services)

### Prerequisites
- Docker 24.0+
- Docker Compose v2.20+
- Git 2.30+

### Steps

```bash
# 1. Clone repository
git clone https://github.com/bozzyk44/OpticsERP.git
cd OpticsERP

# 2. Copy development configuration
cp .env.dev .env

# 3. Start all services (Odoo + Mock ККТ/ОФД)
docker-compose -f docker-compose.dev.yml up -d

# 4. Wait for services to be healthy (~30-60s)
docker-compose -f docker-compose.dev.yml ps

# 5. Open Odoo in browser
# http://localhost:8069
# Login: admin / admin
```

### Verify Everything Works

```bash
# Odoo web interface
curl http://localhost:8069/web/health
# Expected: {"status": "ok"}

# KKT Adapter API
curl http://localhost:8000/v1/health
# Expected: {"status": "healthy", "circuit_breaker": "CLOSED", ...}

# Mock OFD Server
curl http://localhost:9000/ofd/v1/health
# Expected: {"status": "healthy", "receipts_received": 0, ...}

# Mock Odoo API
curl http://localhost:8070/api/v1/health
# Expected: {"status": "healthy", "heartbeats_received": 0}
```

### Test Fiscalization

```bash
# Create test receipt
curl -X POST http://localhost:8000/v1/kkt/receipt \
  -H "Content-Type: application/json" \
  -H "X-Idempotency-Key: test-receipt-001" \
  -d '{
    "pos_id": "POS-001",
    "items": [{"name": "Test Product", "quantity": 1, "price": 1000.00, "tax_rate": 20}],
    "total": 1000.00,
    "payment_method": "card"
  }'

# Check buffer status
curl http://localhost:8000/v1/kkt/buffer/status
# Expected: {"pending_count": 0, "synced_count": 1, ...}
```

### View Logs

```bash
# All services
docker-compose -f docker-compose.dev.yml logs -f

# Specific service
docker-compose -f docker-compose.dev.yml logs -f kkt_adapter
docker-compose -f docker-compose.dev.yml logs -f odoo
```

### Stop Services

```bash
# Stop and keep volumes
docker-compose -f docker-compose.dev.yml down

# Stop and remove volumes (clean slate)
docker-compose -f docker-compose.dev.yml down -v
```

---

## 🧪 Run Tests

```bash
# Unit tests
pytest tests/unit -v

# Integration tests (Docker)
./scripts/run_docker_tests.sh

# Specific test
./scripts/run_docker_tests.sh --filter test_two_phase_fiscalization
```

---

## 📚 Next Steps

1. **Read full setup guide:** [docs/development/DEVELOPER_SETUP_GUIDE.md](docs/development/DEVELOPER_SETUP_GUIDE.md)
2. **Understand KKT emulation:** [docs/testing/KKT_EMULATION_GUIDE.md](docs/testing/KKT_EMULATION_GUIDE.md)
3. **Learn Docker testing:** [docs/testing/DOCKER_TESTING_GUIDE.md](docs/testing/DOCKER_TESTING_GUIDE.md)
4. **Check architecture:** [CLAUDE.md](CLAUDE.md) §6

---

## 🆘 Troubleshooting

### Services not starting?

```bash
# Check logs
docker-compose -f docker-compose.dev.yml logs [service_name]

# Check ports (should be free: 8069, 8000, 5433, 6380, 9000, 8070)
netstat -tuln | grep -E "8069|8000|5433|6380|9000|8070"

# Kill processes on ports (Windows)
python scripts/kill_port.py 8069 8000 5433 6380 9000 8070

# Restart
docker-compose -f docker-compose.dev.yml down
docker-compose -f docker-compose.dev.yml up -d
```

### Services unhealthy?

```bash
# Check health manually
curl http://localhost:8000/v1/health
curl http://localhost:9000/ofd/v1/health

# Rebuild
docker-compose -f docker-compose.dev.yml build --no-cache
docker-compose -f docker-compose.dev.yml up -d
```

### Full reset?

```bash
# Remove all project containers, volumes, networks
docker-compose -f docker-compose.dev.yml down -v
docker volume prune -f
docker network prune -f

# Start fresh
docker-compose -f docker-compose.dev.yml up -d
```

---

## 📊 Service URLs

| Service | URL | Credentials |
|---------|-----|-------------|
| **Odoo** | http://localhost:8069 | admin / admin |
| **KKT Adapter API** | http://localhost:8000/docs | - |
| **Mock OFD** | http://localhost:9000/ofd/v1/health | - |
| **Mock Odoo API** | http://localhost:8070/api/v1/health | - |
| **PostgreSQL** | localhost:5433 | odoo / odoo_dev_password_123 |
| **Redis** | localhost:6380 | - |
| **Prometheus** | http://localhost:9091 | (optional, profile: monitoring) |
| **Grafana** | http://localhost:3001 | admin / admin (optional) |

---

**Last Updated:** 2025-11-30

🤖 Generated with [Claude Code](https://claude.com/claude-code)
