# OpticsERP - Offline-First POS/ERP for Optical Retail

**Version:** 1.0 (POC Phase)
**Status:** Active Development
**Tech Stack:** Odoo 17, Python 3.11, FastAPI, PostgreSQL, SQLite, Redis

---

## 🎯 Project Overview

OpticsERP is an enterprise resource planning and point-of-sale system designed specifically for optical retail chains in Russia, with **full compliance to 54-ФЗ** (Russian fiscal legislation) and **offline-first architecture** for maximum business continuity.

### Key Features

✅ **Offline-First Architecture** - 8+ hours autonomous operation without OFD connectivity
✅ **54-ФЗ Compliance** - Full fiscal integration (ККТ, ОФД, ФФД 1.2)
✅ **Two-Phase Fiscalization** - Local print → async OFD sync
✅ **Guaranteed Delivery** - 100% receipt delivery to OFD via SQLite buffer
✅ **Circuit Breaker Pattern** - Automatic failover and recovery
✅ **Hybrid Logical Clock** - NTP-independent event ordering
✅ **Multi-Location Support** - 20+ retail locations, 40+ POS terminals

### Target Scale

- **Locations:** 20 optical stores
- **POS Terminals:** 40 cash registers
- **Products:** 10,000+ SKUs (frames, lenses, accessories)
- **Daily Transactions:** 500+ receipts
- **Business Availability:** ≥99.5% uptime SLA

---

## 📚 Documentation

### Quick Links

| Document | Description |
|----------|-------------|
| **[Developer Setup Guide](docs/development/DEVELOPER_SETUP_GUIDE.md)** | 🚀 **START HERE** - Development environment setup |
| **[KKT Emulation Guide](docs/testing/KKT_EMULATION_GUIDE.md)** | Mock ККТ/ОФД testing without hardware |
| **[Docker Testing Guide](docs/testing/DOCKER_TESTING_GUIDE.md)** | E2E testing with Docker Compose |
| **[Installation Guide](docs/installation/)** | Production deployment instructions |
| **[CLAUDE.md](CLAUDE.md)** | AI assistant instructions & architecture |
| **[GLOSSARY.md](GLOSSARY.md)** | Russian fiscal terminology reference |

### Architecture Documents

- **[Requirements](docs/2.%20Требования.md)** - Functional and non-functional requirements
- **[Architecture](docs/3.%20Архитектура.md)** - System architecture and design decisions
- **[Roadmap](docs/4.%20Дорожная%20карта.md)** - Development roadmap and milestones
- **[Offline Mode](docs/5.%20Офлайн-режим.md)** - Offline-first architecture details

---

## 🚀 Quick Start

### For Developers

```bash
# 1. Clone repository
git clone https://github.com/bozzyk44/OpticsERP.git
cd OpticsERP

# 2. Copy development configuration
cp .env.dev .env

# 3. Start development environment (with mock services)
docker-compose -f docker-compose.dev.yml up -d

# 4. Verify all services are healthy
docker-compose -f docker-compose.dev.yml ps

# 5. Open Odoo
# http://localhost:8069
# Login: admin / admin
```

**Read full setup guide:** [docs/development/DEVELOPER_SETUP_GUIDE.md](docs/development/DEVELOPER_SETUP_GUIDE.md)

### For Production

```bash
# 1. Clone repository
git clone https://github.com/bozzyk44/OpticsERP.git
cd OpticsERP

# 2. Configure environment
cp .env.example .env
nano .env  # Edit production settings

# 3. Start production stack
docker-compose up -d

# 4. Initialize database
docker-compose exec odoo odoo -d opticserp_prod -i base --stop-after-init

# 5. Access Odoo
# http://your-domain.com:8069
```

**Read full installation guide:** [docs/installation/01_introduction.md](docs/installation/01_introduction.md)

---

## 🏗️ Architecture

### System Components

```
┌─────────────────────────────────────────────────────────┐
│                    Odoo 17 (POS/ERP)                    │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐     │
│  │ optics_core │  │optics_pos_  │  │ connector_b │     │
│  │             │  │   ru54fz    │  │             │     │
│  └─────────────┘  └─────────────┘  └─────────────┘     │
└──────────────────────┬──────────────────────────────────┘
                       │ HTTP API
                       ▼
┌─────────────────────────────────────────────────────────┐
│              KKT Adapter (FastAPI)                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │ Mock KKT     │  │ SQLite Buffer│  │ Circuit      │  │
│  │ Driver       │  │ (Offline)    │  │ Breaker      │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
└──────────────────────┬──────────────────────────────────┘
                       │ Async Sync
                       ▼
┌─────────────────────────────────────────────────────────┐
│                  ОФД Operator API                       │
│              (or Mock OFD for testing)                  │
└─────────────────────────────────────────────────────────┘
```

### Two-Phase Fiscalization

**Phase 1 (Synchronous, ALWAYS succeeds):**
1. Generate Hybrid Logical Clock timestamp
2. Insert receipt into SQLite buffer (`status='pending'`)
3. Print fiscal receipt on ККТ (or mock print)
4. Return success to POS

**Phase 2 (Asynchronous, best-effort):**
1. Check Circuit Breaker state
2. Send receipt to ОФД API (timeout 10s)
3. Update buffer status to `synced`
4. On failure: retry up to 20 times → Dead Letter Queue

**Result:** POS operation NEVER blocks on ОФД availability!

---

## 🛠️ Tech Stack

### Backend
- **Odoo 17** - ERP/POS framework (Python 3.11)
- **FastAPI** - KKT Adapter REST API
- **PostgreSQL 15** - Main database
- **SQLite (WAL mode)** - Offline buffer
- **Redis 7** - Distributed lock, Celery broker
- **Celery** - Background tasks

### Frontend
- **Odoo Web Client** - JavaScript/OWL framework
- **POS Module** - Point of Sale UI

### Infrastructure
- **Docker** - Containerization
- **Docker Compose** - Multi-container orchestration
- **Nginx** - Reverse proxy (production)
- **Prometheus** - Metrics collection
- **Grafana** - Monitoring dashboards

### Testing
- **pytest** - Unit and integration tests
- **Flask** - Mock OFD/Odoo servers
- **Apache Bench** - Load testing

---

## 📁 Project Structure

```
OpticsERP/
├── addons/                      # Odoo custom modules
│   ├── optics_core/             # Domain models (prescriptions, lenses)
│   ├── optics_pos_ru54fz/       # POS + 54-ФЗ + offline mode
│   ├── connector_b/             # Excel/CSV import
│   └── ru_accounting_extras/    # Cash accounts, GP reports
│
├── kkt_adapter/                 # KKT Adapter service (FastAPI)
│   ├── app/
│   │   ├── main.py              # FastAPI application
│   │   ├── buffer.py            # SQLite buffer CRUD
│   │   ├── kkt_driver.py        # Mock KKT driver
│   │   ├── ofd_client.py        # ОФД API client + Circuit Breaker
│   │   ├── sync_worker.py       # Background sync worker
│   │   ├── heartbeat.py         # Heartbeat to Odoo (30s)
│   │   └── hlc.py               # Hybrid Logical Clock
│   ├── data/
│   │   └── buffer.db            # SQLite offline buffer
│   └── Dockerfile
│
├── tests/
│   ├── unit/                    # Unit tests (pytest)
│   ├── integration/             # Integration tests + mock servers
│   │   ├── mock_ofd_server.py
│   │   └── mock_odoo_server.py
│   ├── poc/                     # POC acceptance tests
│   └── uat/                     # UAT scenarios
│
├── docs/
│   ├── development/             # Developer guides
│   │   └── DEVELOPER_SETUP_GUIDE.md
│   ├── testing/                 # Testing guides
│   │   ├── KKT_EMULATION_GUIDE.md
│   │   └── DOCKER_TESTING_GUIDE.md
│   ├── installation/            # Installation guides
│   └── [1-5].md                 # Core architecture docs
│
├── scripts/
│   ├── run_docker_tests.sh      # Docker test automation
│   └── kill_port.py             # Port management utility
│
├── docker-compose.yml           # Production stack
├── docker-compose.dev.yml       # Development stack (with mocks)
├── docker-compose.test.yml      # Test stack
├── .env.example                 # Production config template
├── .env.dev                     # Development config template
├── CLAUDE.md                    # AI assistant instructions
├── GLOSSARY.md                  # Terminology reference
└── README.md                    # This file
```

---

## 🧪 Testing

### Unit Tests

```bash
# All unit tests
pytest tests/unit -v

# Specific module
pytest tests/unit/test_buffer_db.py -v
pytest tests/unit/test_hlc.py -v

# With coverage
pytest tests/unit --cov=kkt_adapter --cov-report=html
```

### Integration Tests (Docker)

```bash
# All integration tests
./scripts/run_docker_tests.sh

# Specific test
./scripts/run_docker_tests.sh --filter test_two_phase_fiscalization

# Keep services running for debugging
./scripts/run_docker_tests.sh --keep-up
```

### Manual E2E Testing

```bash
# 1. Start development environment
docker-compose -f docker-compose.dev.yml up -d

# 2. Open Odoo POS
# http://localhost:8069 → Point of Sale

# 3. Create test sale

# 4. Verify fiscalization
curl http://localhost:8000/v1/kkt/buffer/status
```

**Full testing guide:** [docs/testing/DOCKER_TESTING_GUIDE.md](docs/testing/DOCKER_TESTING_GUIDE.md)

---

## 🔧 Development

### Prerequisites

- **Docker** 24.0+
- **Docker Compose** v2.20+
- **Git** 2.30+
- **Python** 3.11+ (for local development)

### Setup Development Environment

```bash
# 1. Clone and configure
git clone https://github.com/bozzyk44/OpticsERP.git
cd OpticsERP
cp .env.dev .env

# 2. Start services
docker-compose -f docker-compose.dev.yml up -d

# 3. Check health
docker-compose -f docker-compose.dev.yml ps
```

### Development Workflow

```bash
# Edit code (auto-reload enabled)
code addons/optics_pos_ru54fz/models/pos_session.py

# Run tests
pytest tests/unit/test_pos_session.py -v

# View logs
docker-compose -f docker-compose.dev.yml logs -f odoo
docker-compose -f docker-compose.dev.yml logs -f kkt_adapter

# Restart service
docker-compose -f docker-compose.dev.yml restart kkt_adapter
```

**Full development guide:** [docs/development/DEVELOPER_SETUP_GUIDE.md](docs/development/DEVELOPER_SETUP_GUIDE.md)

---

## 📊 Monitoring

### Metrics (Prometheus)

```bash
# Start with monitoring enabled
COMPOSE_PROFILES=monitoring docker-compose -f docker-compose.dev.yml up -d

# Access Prometheus
http://localhost:9091

# Access Grafana
http://localhost:3001
# Login: admin / admin
```

### Key Metrics

- `kkt_buffer_percent_full` - Buffer fullness (alert @80%)
- `kkt_circuit_breaker_state` - CB state (0=CLOSED, 1=OPEN, 2=HALF_OPEN)
- `kkt_sync_duration_seconds` - Sync latency (P95 < 10s)
- `kkt_dlq_size` - Dead Letter Queue size
- `kkt_hlc_drift_seconds` - HLC drift from NTP

---

## 📋 Roadmap

| Phase | Timeline | Status | Deliverables |
|-------|----------|--------|--------------|
| **POC** | W1-5 (Oct 06 - Nov 09) | ✅ Complete | SQLite buffer, Circuit Breaker, HLC, 8h offline |
| **MVP** | W6-9 (Nov 10 - Dec 07) | 🔄 In Progress | Full Odoo modules, UAT, connector_b |
| **Buffer** | W10 (Dec 08 - Dec 14) | ⏳ Pending | Load tests, optimization |
| **Pilot** | W11-14 (Dec 15 - Jan 11) | ⏳ Pending | 2 locations, 4 terminals |
| **Soft Launch** | W15-16 (Jan 12 - Jan 25) | ⏳ Pending | 5 locations, 10 terminals |
| **Production** | W17-20 (Jan 26 - Feb 22) | ⏳ Pending | 20 locations, 40 terminals |

**Total:** 19 weeks (T0 → T0+19)

---

## 🤝 Contributing

### Git Workflow

```bash
# 1. Create feature branch
git checkout -b feature/OPTERP-XXX-short-description

# 2. Commit with JIRA ID
git commit -m "feat(scope): description [OPTERP-XXX]"

# 3. Push
git push origin feature/OPTERP-XXX-short-description

# 4. Create Pull Request
# Title: [OPTERP-XXX] Short description
```

### Commit Types

- `feat(scope):` - New feature
- `fix(scope):` - Bug fix
- `docs(scope):` - Documentation
- `test(scope):` - Tests
- `refactor(scope):` - Code refactoring
- `chore(scope):` - Technical tasks

### Code Quality

```bash
# Linting
flake8 kkt_adapter/app
pylint kkt_adapter/app

# Formatting
black kkt_adapter/app
isort kkt_adapter/app

# Type checking
mypy kkt_adapter/app

# Tests (coverage ≥95%)
pytest tests/unit --cov=kkt_adapter --cov-report=term-missing
```

---

## 📄 License

**Proprietary** - Internal use only
© 2024-2025 bozzyk44

---

## 📞 Support

- **JIRA:** https://bozzyk44.atlassian.net/browse/OPTERP
- **Git:** https://github.com/bozzyk44/OpticsERP
- **Email:** bozzyk44@gmail.com

---

## 🙏 Acknowledgments

- **Odoo Community** - For the excellent ERP/POS framework
- **FastAPI** - For the modern async Python web framework
- **54-ФЗ Documentation** - For fiscal compliance guidelines

---

**Last Updated:** 2025-11-30
**Version:** 1.0
**Author:** Claude Code

🤖 Generated with [Claude Code](https://claude.com/claude-code)
