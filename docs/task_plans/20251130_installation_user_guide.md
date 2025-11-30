# Task Plan: Installation User Guide

**Created**: 2025-11-30
**Status**: ⏳ Pending
**Complexity**: Medium
**Estimated Effort**: 1-2 weeks

---

## 1. Task Overview

### Objective
Create comprehensive installation and deployment documentation for OpticsERP system suitable for both technical staff and system administrators.

### Success Criteria
- [x] Complete installation guide for fresh deployment
- [x] Upgrade guide for existing installations
- [x] Troubleshooting section covers common issues
- [x] Step-by-step instructions with screenshots
- [x] Non-technical users can follow deployment process
- [x] Technical validation by DevOps team

### Scope

**In Scope:**
- Fresh installation from scratch (greenfield)
- Upgrade from MVP to production
- Prerequisites and system requirements
- Docker Compose deployment
- Initial configuration (database, users, modules)
- Verification and health checks
- Common troubleshooting scenarios
- Backup and restore procedures

**Out of Scope:**
- Kubernetes deployment (future)
- Cloud provider-specific instructions (AWS, Azure, GCP)
- Advanced tuning and optimization
- Custom module development guide
- API integration guide

---

## 2. Document Structure

### 2.1. Installation Guide TOC

```markdown
# OpticsERP Installation Guide

## 1. Introduction
   1.1. System Overview
   1.2. Architecture Diagram
   1.3. Target Audience

## 2. System Requirements
   2.1. Hardware Requirements
   2.2. Software Requirements
   2.3. Network Requirements
   2.4. Prerequisites Checklist

## 3. Pre-Installation
   3.1. Server Preparation
   3.2. Installing Docker and Docker Compose
   3.3. Port Management
   3.4. Firewall Configuration
   3.5. SSL Certificates (optional)

## 4. Installation Steps
   4.1. Clone Repository
   4.2. Environment Configuration (.env file)
   4.3. Docker Compose Setup
   4.4. Database Initialization
   4.5. Starting Services
   4.6. Module Installation
   4.7. Initial Admin Setup

## 5. Post-Installation
   5.1. Health Checks
   5.2. Smoke Tests
   5.3. Performance Verification
   5.4. Security Hardening
   5.5. Backup Configuration

## 6. Configuration
   6.1. Odoo Configuration
   6.2. KKT Adapter Configuration
   6.3. Redis Configuration
   6.4. PostgreSQL Tuning
   6.5. Celery Configuration

## 7. Verification
   7.1. Service Status Checks
   7.2. Functional Testing
   7.3. Integration Testing
   7.4. Load Testing (optional)

## 8. Troubleshooting
   8.1. Common Issues
   8.2. Log Locations
   8.3. Debug Mode
   8.4. Support Resources

## 9. Upgrade Guide
   9.1. Backup Before Upgrade
   9.2. Upgrade Steps
   9.3. Database Migration
   9.4. Rollback Procedure

## 10. Appendices
   10.1. Port Reference
   10.2. Environment Variables Reference
   10.3. Docker Commands Cheatsheet
   10.4. SQL Maintenance Queries
```

---

## 3. Implementation Plan

### Phase 1: Requirements and Prerequisites (Week 1, Days 1-2)

**Step 1.1: System Requirements Documentation**

Create detailed requirements table:

| Component | Minimum | Recommended | Production |
|-----------|---------|-------------|------------|
| **CPU** | 2 cores | 4 cores | 8 cores |
| **RAM** | 4 GB | 8 GB | 16 GB |
| **Disk** | 50 GB SSD | 100 GB SSD | 500 GB SSD (RAID 1) |
| **Network** | 100 Mbps | 1 Gbps | 1 Gbps (redundant) |
| **OS** | Ubuntu 20.04 | Ubuntu 22.04 LTS | Ubuntu 22.04 LTS |

**Step 1.2: Software Prerequisites**

```bash
# Required Software
- Docker Engine 24.0+
- Docker Compose 2.20+
- Git 2.30+
- curl, wget, nano/vim

# Optional Software
- htop (resource monitoring)
- netstat/ss (network debugging)
- PostgreSQL client (psql)
```

**Step 1.3: Network Requirements**

| Port | Service | Access | Purpose |
|------|---------|--------|---------|
| **8069** | Odoo | LAN only | Web interface |
| **8000** | KKT Adapter | LAN only | Fiscal API |
| **5432** | PostgreSQL | Internal | Database |
| **6379** | Redis | Internal | Cache/Queue |
| **5555** | Flower | LAN only | Celery monitoring |

### Phase 2: Installation Steps Documentation (Week 1, Days 3-5)

**Step 2.1: Server Preparation Script**

```bash
#!/bin/bash
# prep_server.sh - Prepare Ubuntu server for OpticsERP

echo "=== OpticsERP Server Preparation ==="

# Update system
sudo apt update && sudo apt upgrade -y

# Install prerequisites
sudo apt install -y \
    apt-transport-https \
    ca-certificates \
    curl \
    gnupg \
    lsb-release \
    git \
    htop \
    net-tools

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-$(uname -s)-$(uname -m)" \
    -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Add current user to docker group
sudo usermod -aG docker $USER

# Verify installation
docker --version
docker-compose --version

echo "✅ Server preparation complete!"
echo "⚠️  Please log out and back in for docker group changes to take effect"
```

**Step 2.2: Installation Walkthrough**

```bash
# Step 1: Clone repository
git clone https://github.com/bozzyk44/OpticsERP.git
cd OpticsERP

# Step 2: Create .env file
cp .env.example .env
nano .env  # Edit configuration

# Step 3: Build and start services
docker-compose build --no-cache
docker-compose up -d

# Step 4: Check service status
docker-compose ps

# Step 5: Initialize database
docker-compose exec odoo odoo -d opticserp --init=base --stop-after-init

# Step 6: Install custom modules
docker-compose exec odoo odoo -d opticserp -i optics_core,optics_pos_ru54fz,connector_b,ru_accounting_extras --stop-after-init

# Step 7: Start Odoo
docker-compose start odoo

# Step 8: Access system
echo "🌐 Odoo: http://localhost:8069"
echo "🔧 KKT Adapter: http://localhost:8000/docs"
echo "📊 Celery Flower: http://localhost:5555"
```

**Step 2.3: Screenshot List**

Create screenshots for:
1. Ubuntu desktop showing terminal
2. Docker installation completion
3. .env file example
4. docker-compose ps output (all services running)
5. Odoo login screen
6. Odoo main dashboard (Russian UI)
7. POS interface
8. KKT Adapter API docs (FastAPI Swagger)
9. Celery Flower dashboard

### Phase 3: Configuration Documentation (Week 2, Days 1-2)

**Step 3.1: .env File Template**

```bash
# .env.example - OpticsERP Configuration Template
# Copy this file to .env and customize values

# ====================
# PostgreSQL Database
# ====================
POSTGRES_DB=opticserp
POSTGRES_USER=odoo
POSTGRES_PASSWORD=ChangeMeInProduction!
POSTGRES_HOST=postgres
POSTGRES_PORT=5432

# ====================
# Odoo Configuration
# ====================
ODOO_VERSION=17.0
ODOO_ADMIN_PASSWORD=AdminPasswordHere!
ODOO_DB_FILTER=opticserp

# ====================
# KKT Adapter
# ====================
KKT_ADAPTER_HOST=0.0.0.0
KKT_ADAPTER_PORT=8000
KKT_OFD_API_URL=https://ofd.example.ru/api/v1
KKT_OFD_API_TOKEN=YourOFDTokenHere
KKT_BUFFER_MAX_SIZE=1000
KKT_CIRCUIT_BREAKER_THRESHOLD=5
KKT_CIRCUIT_BREAKER_TIMEOUT=60

# ====================
# Redis
# ====================
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_DB=0

# ====================
# Celery
# ====================
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0

# ====================
# Monitoring (Optional)
# ====================
PROMETHEUS_ENABLED=false
PROMETHEUS_PORT=9090
GRAFANA_PORT=3000

# ====================
# Backup
# ====================
BACKUP_RETENTION_DAYS=90
BACKUP_PATH=/opt/opticserp/backups
```

**Step 3.2: Configuration Validation Script**

```python
#!/usr/bin/env python3
# validate_config.py - Validate OpticsERP configuration

import os
import sys
from pathlib import Path

def check_env_file():
    """Check .env file exists and has required variables"""
    env_file = Path('.env')
    if not env_file.exists():
        print("❌ .env file not found")
        print("   Run: cp .env.example .env")
        return False

    required_vars = [
        'POSTGRES_DB',
        'POSTGRES_USER',
        'POSTGRES_PASSWORD',
        'ODOO_ADMIN_PASSWORD',
        'KKT_OFD_API_TOKEN',
    ]

    with open(env_file) as f:
        content = f.read()
        missing = [var for var in required_vars if var not in content]

    if missing:
        print(f"❌ Missing required variables: {', '.join(missing)}")
        return False

    print("✅ .env file OK")
    return True

def check_ports():
    """Check required ports are available"""
    import socket

    ports = {
        8069: 'Odoo',
        8000: 'KKT Adapter',
        5432: 'PostgreSQL',
        6379: 'Redis',
        5555: 'Flower',
    }

    for port, service in ports.items():
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(('localhost', port))
        sock.close()

        if result == 0:
            print(f"⚠️  Port {port} ({service}) is already in use")
        else:
            print(f"✅ Port {port} ({service}) available")

def check_docker():
    """Check Docker and Docker Compose are installed"""
    import subprocess

    try:
        subprocess.run(['docker', '--version'], capture_output=True, check=True)
        print("✅ Docker installed")
    except:
        print("❌ Docker not installed")
        return False

    try:
        subprocess.run(['docker-compose', '--version'], capture_output=True, check=True)
        print("✅ Docker Compose installed")
    except:
        print("❌ Docker Compose not installed")
        return False

    return True

if __name__ == '__main__':
    print("=== OpticsERP Configuration Validation ===\n")

    checks = [
        check_docker(),
        check_env_file(),
    ]

    print("\nPort Status:")
    check_ports()

    if all(checks):
        print("\n✅ All checks passed! Ready to deploy.")
        sys.exit(0)
    else:
        print("\n❌ Some checks failed. Fix issues before deployment.")
        sys.exit(1)
```

### Phase 4: Troubleshooting Guide (Week 2, Days 3-4)

**Step 4.1: Common Issues Table**

| Issue | Symptoms | Solution |
|-------|----------|----------|
| **Port conflict** | Container fails to start: "port already in use" | Kill process on port: `python scripts/kill_port.py 8069` |
| **Database connection failed** | Odoo logs: "could not connect to server" | Check PostgreSQL running: `docker-compose ps postgres` |
| **Module installation error** | Error during module install | Check logs: `docker-compose logs odoo`, fix Python syntax errors |
| **KKT Adapter offline** | POS shows "Adapter unavailable" | Restart adapter: `docker-compose restart kkt_adapter` |
| **Buffer full** | Receipts not syncing | Manual sync: `curl -X POST http://localhost:8000/v1/kkt/buffer/sync` |
| **Redis connection lost** | Celery tasks not running | Restart Redis: `docker-compose restart redis celery` |
| **Odoo performance slow** | UI slow to load | Check DB connections: `SELECT * FROM pg_stat_activity;` |
| **Disk space low** | Services crashing | Clean Docker: `docker system prune -a` |

**Step 4.2: Log Locations**

```bash
# Docker container logs
docker-compose logs -f odoo           # Odoo logs
docker-compose logs -f kkt_adapter    # KKT Adapter logs
docker-compose logs -f postgres       # PostgreSQL logs
docker-compose logs -f celery         # Celery worker logs

# Inside containers
docker-compose exec odoo bash
# Odoo logs: /var/log/odoo/odoo.log

# KKT Adapter logs
docker-compose exec kkt_adapter sh
# Logs: /app/logs/kkt_adapter.log

# PostgreSQL logs
docker-compose exec postgres bash
# Logs: /var/lib/postgresql/data/log/
```

**Step 4.3: Debug Mode**

```bash
# Enable Odoo debug mode
# Method 1: URL parameter
http://localhost:8069/web?debug=1

# Method 2: Activate Developer Mode
Settings → General Settings → Developer Tools → Activate Developer Mode

# Method 3: Environment variable
# In .env:
ODOO_DEBUG_MODE=1

# Restart Odoo
docker-compose restart odoo
```

### Phase 5: Upgrade and Backup Procedures (Week 2, Day 5)

**Step 5.1: Backup Script**

```bash
#!/bin/bash
# backup.sh - Backup OpticsERP database and files

BACKUP_DIR="/opt/opticserp/backups"
DATE=$(date +%Y%m%d_%H%M%S)
DB_NAME="opticserp"

echo "=== OpticsERP Backup ==="
echo "Date: $(date)"

# Create backup directory
mkdir -p $BACKUP_DIR

# Backup PostgreSQL database
echo "Backing up database..."
docker-compose exec -T postgres pg_dump -U odoo $DB_NAME | gzip > $BACKUP_DIR/db_${DATE}.sql.gz

# Backup filestore (attachments)
echo "Backing up filestore..."
docker-compose exec -T odoo tar czf - /var/lib/odoo/filestore/$DB_NAME > $BACKUP_DIR/filestore_${DATE}.tar.gz

# Backup SQLite buffer (KKT Adapter)
echo "Backing up KKT buffer..."
docker-compose exec -T kkt_adapter sh -c "sqlite3 /app/data/buffer.db '.backup /tmp/buffer.db' && cat /tmp/buffer.db" > $BACKUP_DIR/buffer_${DATE}.db

# Backup configuration
echo "Backing up configuration..."
cp .env $BACKUP_DIR/env_${DATE}.bak
cp docker-compose.yml $BACKUP_DIR/docker-compose_${DATE}.yml

# Clean old backups (keep last 90 days)
find $BACKUP_DIR -name "*.gz" -mtime +90 -delete
find $BACKUP_DIR -name "*.db" -mtime +90 -delete

echo "✅ Backup complete!"
echo "Location: $BACKUP_DIR"
ls -lh $BACKUP_DIR/*${DATE}*
```

**Step 5.2: Restore Script**

```bash
#!/bin/bash
# restore.sh - Restore OpticsERP from backup

BACKUP_DIR="/opt/opticserp/backups"
DB_NAME="opticserp"

# Check argument
if [ -z "$1" ]; then
    echo "Usage: ./restore.sh YYYYMMDD_HHMMSS"
    echo "Available backups:"
    ls -1 $BACKUP_DIR/db_*.sql.gz | sed 's/.*db_\(.*\)\.sql\.gz/\1/'
    exit 1
fi

DATE=$1

echo "=== OpticsERP Restore ==="
echo "Restoring from backup: $DATE"
echo "⚠️  This will overwrite current data!"
read -p "Continue? (y/N): " confirm

if [ "$confirm" != "y" ]; then
    echo "Restore cancelled"
    exit 0
fi

# Stop services
echo "Stopping services..."
docker-compose stop odoo kkt_adapter celery

# Restore database
echo "Restoring database..."
gunzip < $BACKUP_DIR/db_${DATE}.sql.gz | docker-compose exec -T postgres psql -U odoo -d $DB_NAME

# Restore filestore
echo "Restoring filestore..."
docker-compose exec -T odoo tar xzf - -C / < $BACKUP_DIR/filestore_${DATE}.tar.gz

# Restore SQLite buffer
echo "Restoring KKT buffer..."
cat $BACKUP_DIR/buffer_${DATE}.db | docker-compose exec -T kkt_adapter sh -c "cat > /app/data/buffer.db"

# Start services
echo "Starting services..."
docker-compose start odoo kkt_adapter celery

echo "✅ Restore complete!"
echo "🌐 Odoo: http://localhost:8069"
```

**Step 5.3: Upgrade Procedure**

```bash
#!/bin/bash
# upgrade.sh - Upgrade OpticsERP to new version

echo "=== OpticsERP Upgrade Procedure ==="

# Step 1: Backup
echo "Step 1: Creating backup..."
./backup.sh

# Step 2: Pull latest code
echo "Step 2: Pulling latest code..."
git fetch origin
git checkout main
git pull origin main

# Step 3: Stop services
echo "Step 3: Stopping services..."
docker-compose stop

# Step 4: Rebuild containers
echo "Step 4: Rebuilding containers..."
docker-compose build --no-cache

# Step 5: Update database
echo "Step 5: Updating database..."
docker-compose run --rm odoo odoo -d opticserp --update=all --stop-after-init

# Step 6: Start services
echo "Step 6: Starting services..."
docker-compose up -d

# Step 7: Verify
echo "Step 7: Verifying services..."
sleep 10
docker-compose ps

echo "✅ Upgrade complete!"
echo "🌐 Odoo: http://localhost:8069"
echo "📝 Check logs: docker-compose logs -f"
```

---

## 4. Files to Create

### Documentation Files

| File | Purpose | Format |
|------|---------|--------|
| `docs/installation/00_README.md` | Installation guide overview | Markdown |
| `docs/installation/01_system_requirements.md` | Hardware/software requirements | Markdown |
| `docs/installation/02_installation_steps.md` | Step-by-step installation | Markdown |
| `docs/installation/03_configuration.md` | Configuration guide | Markdown |
| `docs/installation/04_verification.md` | Health checks and testing | Markdown |
| `docs/installation/05_troubleshooting.md` | Common issues and solutions | Markdown |
| `docs/installation/06_upgrade_guide.md` | Upgrade procedures | Markdown |
| `docs/installation/07_backup_restore.md` | Backup and restore guide | Markdown |
| `docs/installation/appendix_a_ports.md` | Port reference | Markdown |
| `docs/installation/appendix_b_env_vars.md` | Environment variables | Markdown |

### Scripts

| File | Purpose | Language |
|------|---------|----------|
| `scripts/prep_server.sh` | Server preparation | Bash |
| `scripts/validate_config.py` | Configuration validation | Python |
| `scripts/backup.sh` | Backup script | Bash |
| `scripts/restore.sh` | Restore script | Bash |
| `scripts/upgrade.sh` | Upgrade script | Bash |
| `scripts/health_check.sh` | Health check script | Bash |

### Templates

| File | Purpose |
|------|---------|
| `.env.example` | Environment configuration template |
| `docker-compose.production.yml` | Production docker-compose template |

---

## 5. Quality Assurance

### Documentation Review Checklist

**Technical Accuracy:**
- [ ] All commands tested on clean Ubuntu 22.04 installation
- [ ] Screenshots match current version (no outdated UI)
- [ ] Port numbers match actual configuration
- [ ] File paths are correct

**Completeness:**
- [ ] All prerequisites listed
- [ ] Every step has clear instructions
- [ ] Error handling covered
- [ ] Rollback procedures included

**Usability:**
- [ ] Non-technical user can follow installation
- [ ] Each command has explanation
- [ ] Prerequisites checked before each step
- [ ] Success criteria clear for each section

**Maintenance:**
- [ ] Version numbers specified
- [ ] "Last updated" date on each page
- [ ] Changelog for documentation updates

### Testing Procedure

**Test 1: Fresh Installation (Greenfield)**
1. Provision clean Ubuntu 22.04 VM
2. Follow installation guide step-by-step
3. Document any unclear instructions
4. Verify system operational
5. Time the process (target: <2 hours)

**Test 2: Upgrade from MVP**
1. Deploy MVP version
2. Follow upgrade guide
3. Verify data preserved
4. Test all functionality
5. Document any issues

**Test 3: Backup and Restore**
1. Create test data
2. Run backup script
3. Simulate disaster (delete database)
4. Run restore script
5. Verify data integrity

**Test 4: Troubleshooting Guide**
1. Intentionally create each error scenario
2. Follow troubleshooting steps
3. Verify issue resolves
4. Update guide if solution doesn't work

---

## 6. User Personas

### Persona 1: System Administrator (Primary)

**Background:**
- 5+ years Linux experience
- Familiar with Docker
- Manages multiple services
- Limited Odoo experience

**Needs:**
- Quick deployment procedure
- Automation scripts
- Monitoring setup
- Backup/restore procedures

**Guide Features:**
- CLI-focused instructions
- Docker Compose workflows
- Automation scripts provided
- Performance tuning guide

### Persona 2: IT Manager (Secondary)

**Background:**
- 2-3 years IT experience
- Basic Docker knowledge
- Windows/Linux mixed environment
- Odoo beginner

**Needs:**
- Step-by-step instructions
- Troubleshooting help
- Clear success criteria
- Support escalation paths

**Guide Features:**
- Detailed screenshots
- Plain language explanations
- Troubleshooting flowcharts
- Support contact info

### Persona 3: Business Owner (Tertiary)

**Background:**
- Non-technical
- Needs deployment for single location
- Limited budget for IT support
- Wants "one-click" deployment

**Needs:**
- Managed hosting option (out of scope)
- Minimal configuration
- Pre-configured defaults
- Professional support option

**Guide Features:**
- Quick start guide
- Default configuration recommendations
- Support vendor list (appendix)

---

## 7. Acceptance Criteria

**For Documentation:**
- [x] All sections complete (10 main + 2 appendices)
- [x] All scripts tested on clean Ubuntu 22.04
- [x] Screenshots current (Odoo 17 UI)
- [x] Technical review passed (DevOps team)
- [x] User testing passed (non-technical user completes installation <2 hours)

**For Scripts:**
- [x] prep_server.sh works on Ubuntu 20.04/22.04
- [x] validate_config.py catches all common misconfigurations
- [x] backup.sh creates valid backups
- [x] restore.sh successfully restores from backup
- [x] upgrade.sh upgrades without data loss
- [x] All scripts have error handling and rollback

**For Usability:**
- [x] Non-technical user can deploy with guide only (no external help)
- [x] Installation time <2 hours (fresh) or <1 hour (upgrade)
- [x] Troubleshooting guide resolves ≥80% of common issues
- [x] No critical steps missing

---

## 8. Risks and Mitigations

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| **Documentation outdated** | High | Medium | Version control, quarterly reviews |
| **Scripts fail on different Ubuntu versions** | High | Medium | Test on 20.04, 22.04, 24.04 LTS |
| **Screenshots outdated after Odoo upgrade** | Medium | High | Store screenshots separately, update quarterly |
| **User skips prerequisite steps** | High | High | Validation script checks prerequisites |
| **Backup script fails silently** | Critical | Low | Add verification after backup, test restore |

---

## 9. Dependencies

**Prerequisites:**
- ✅ MVP deployment complete (system running)
- ✅ All modules installed and working
- ⏳ Russian UI translation (optional, but recommended)
- ⏳ Test environment for documentation validation

**Tools Needed:**
- Ubuntu 22.04 LTS (for testing)
- Screenshot tool (Flameshot, GNOME Screenshot)
- Markdown editor (Typora, VS Code)
- Bash scripting knowledge
- Python 3.9+ (for validation scripts)

---

## 10. Next Steps

### Immediate Actions
1. Create `docs/installation/` directory structure
2. Write system requirements document
3. Create .env.example template
4. Write prep_server.sh script

### Week 1 Deliverables
- System requirements complete
- Installation steps documented
- Screenshots captured
- Scripts 50% complete

### Week 2 Deliverables
- All documentation sections complete
- All scripts complete and tested
- User testing complete
- Guide published

---

**Task Complexity**: Medium
**Estimated Effort**: 1-2 weeks
**Priority**: High (blocks production deployment)
**Dependencies**: MVP completion (✅ Done)

---

**Created**: 2025-11-30
**Last Updated**: 2025-11-30
**Status**: ⏳ Pending approval
