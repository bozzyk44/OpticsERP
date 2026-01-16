# System Requirements

**Last Updated:** 2025-11-30
**OpticsERP Version:** 1.0.0 (MVP)

---

## 📋 Overview

This document outlines the minimum, recommended, and production-level system requirements for deploying OpticsERP.

**Quick Reference:**
- **Minimum:** Development/testing environment (1 user)
- **Recommended:** Small business deployment (5-10 users, 2-5 POS terminals)
- **Production:** Enterprise deployment (20+ users, 10-40 POS terminals)

---

## 💻 Hardware Requirements

### Server Hardware

| Component | Minimum | Recommended | Production |
|-----------|---------|-------------|------------|
| **CPU** | 2 cores @ 2.0 GHz | 4 cores @ 2.5 GHz | 8 cores @ 3.0 GHz |
| **RAM** | 4 GB | 8 GB | 16-32 GB |
| **Storage** | 50 GB SSD | 100 GB SSD | 500 GB SSD (NVMe) |
| **RAID** | None | Software RAID 1 | Hardware RAID 10 |
| **Network** | 100 Mbps | 1 Gbps | 1 Gbps (redundant NICs) |

### POS Terminal Hardware

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| **CPU** | 2 cores @ 1.5 GHz | 4 cores @ 2.0 GHz |
| **RAM** | 4 GB | 8 GB |
| **Storage** | 64 GB SSD | 128 GB SSD |
| **Display** | 1024x768 | 1920x1080 touchscreen |
| **Receipt Printer** | 54-ФЗ compliant KKT | Modern fiscal printer with auto-cutter |
| **Network** | 100 Mbps Ethernet | 1 Gbps Ethernet + WiFi backup |

### UPS Requirements

**Critical:** All POS terminals and server must have UPS backup

| Deployment Size | UPS Capacity | Runtime |
|----------------|--------------|---------|
| 1-2 POS | 1000 VA / 600 W | 15-30 min |
| 3-5 POS | 1500 VA / 900 W | 30-60 min |
| 6-10 POS | 3000 VA / 1800 W | 60-120 min |
| Server | 1500 VA / 900 W | 30-60 min |

**Why UPS is critical:**
- Prevents data corruption during power loss
- Ensures proper shutdown of SQLite buffer
- Protects against fiscal data loss
- Required for 54-ФЗ compliance

---

## 🖥️ Operating System Requirements

### Supported Operating Systems

| OS | Version | Status | Notes |
|----|---------|--------|-------|
| **Ubuntu Server** | 22.04 LTS | ✅ Recommended | Primary platform |
| **Ubuntu Server** | 20.04 LTS | ✅ Supported | Stable, tested |
| **Ubuntu Server** | 24.04 LTS | ⚠️ Experimental | Not yet tested |
| **Debian** | 11 (Bullseye) | ⚠️ Untested | Should work |
| **CentOS/RHEL** | 8+ | ❌ Not supported | Use Ubuntu |
| **Windows** | 10/11 | ❌ Not supported | Docker Desktop only for dev |

**Recommended:** Ubuntu Server 22.04 LTS (64-bit)

### Why Ubuntu?

1. **Long-term support** - 5 years of updates
2. **Docker compatibility** - Excellent Docker support
3. **Package availability** - All required packages available
4. **Community support** - Large user base
5. **Security** - Regular security updates

---

## 🐳 Software Requirements

### Core Software

| Software | Minimum Version | Recommended Version | Purpose |
|----------|----------------|---------------------|---------|
| **Docker Engine** | 20.10+ | 24.0+ | Container runtime |
| **Docker Compose** | 2.0+ | 2.20+ | Multi-container orchestration |
| **Git** | 2.30+ | 2.40+ | Version control |
| **Python** | 3.9+ | 3.11+ | Scripts and validation |
| **curl/wget** | Any | Latest | Downloads |

### Optional Software

| Software | Purpose | When Needed |
|----------|---------|-------------|
| **htop** | Resource monitoring | Recommended for all |
| **netstat/ss** | Network debugging | Troubleshooting |
| **PostgreSQL client (psql)** | Database debugging | Troubleshooting |
| **SQLite3** | Buffer inspection | Troubleshooting |
| **Nginx** | Reverse proxy/SSL | Production deployments |

### Installation Script

All required software can be installed using our preparation script:

```bash
sudo bash scripts/prep_server.sh
```

This script installs:
- Docker Engine and Docker Compose
- Git, curl, wget
- Common utilities (htop, net-tools, vim)
- Configures user permissions

---

## 🌐 Network Requirements

### Port Requirements

**External Access (from user devices):**

| Port | Service | Protocol | Required For |
|------|---------|----------|--------------|
| **8069** | Odoo Web | HTTP/HTTPS | Web interface access |
| **8000** | KKT Adapter | HTTP | POS fiscal API |

**Internal Services (Docker network only):**

| Port | Service | Protocol | Access |
|------|---------|----------|--------|
| **5432** | PostgreSQL | TCP | Docker internal |
| **6379** | Redis | TCP | Docker internal |
| **5555** | Flower | HTTP | LAN only (monitoring) |

**Optional Monitoring:**

| Port | Service | Purpose |
|------|---------|---------|
| **9090** | Prometheus | Metrics collection |
| **3000** | Grafana | Dashboards |
| **16686** | Jaeger | Distributed tracing |

### Firewall Configuration

**Minimal firewall rules:**

```bash
# Allow SSH (administration)
sudo ufw allow 22/tcp

# Allow Odoo web interface
sudo ufw allow 8069/tcp

# Allow KKT Adapter (POS terminals only)
sudo ufw allow from 192.168.1.0/24 to any port 8000 proto tcp

# Enable firewall
sudo ufw enable
```

### Bandwidth Requirements

| Scenario | Bandwidth | Notes |
|----------|-----------|-------|
| **Single POS terminal** | 0.5 Mbps | Normal operation |
| **5 POS terminals** | 2-3 Mbps | Peak hours |
| **10 POS terminals** | 5-10 Mbps | Peak hours |
| **Initial deployment** | 50-100 Mbps | Docker image downloads |

### Network Topology

**Recommended network setup:**

```
Internet
   │
   ├─ Router/Firewall
   │     │
   │     ├─ Server (192.168.1.10)
   │     │     └─ Docker Network (172.17.0.0/16)
   │     │           ├─ Odoo (172.17.0.2)
   │     │           ├─ PostgreSQL (172.17.0.3)
   │     │           ├─ KKT Adapter (172.17.0.4)
   │     │           └─ Redis (172.17.0.5)
   │     │
   │     └─ POS Terminals (192.168.1.100-139)
   │           ├─ Terminal 1 → http://192.168.1.10:8069
   │           ├─ Terminal 2 → http://192.168.1.10:8069
   │           └─ Terminal N → http://192.168.1.10:8069
   │
   └─ OFD Operator (external)
        └─ Fiscal data sync
```

**Key considerations:**
- Server and POS terminals on same LAN (low latency)
- Dedicated server IP (static)
- Redundant internet connection for OFD sync
- VPN for remote access (optional)

---

## 📦 Storage Requirements

### Disk Space Breakdown

| Component | Size | Purpose |
|-----------|------|---------|
| **Ubuntu OS** | 10 GB | Base system |
| **Docker images** | 5 GB | Odoo, PostgreSQL, Redis |
| **PostgreSQL database** | 5-50 GB | Grows with usage |
| **Odoo filestore** | 5-100 GB | Attachments, documents |
| **SQLite buffers** | 100-500 MB | Offline receipts |
| **Logs** | 1-10 GB | Application logs |
| **Backups** | 50-200 GB | 90-day retention |
| **Free space (buffer)** | 20% | Recommended |

**Total minimum:** 50 GB
**Recommended:** 100-200 GB
**Production:** 500 GB - 1 TB

### Storage Performance

**I/O Requirements:**

| Component | IOPS | Throughput |
|-----------|------|------------|
| PostgreSQL | 1000+ random IOPS | 50+ MB/s |
| Odoo filestore | 500+ IOPS | 100+ MB/s |
| SQLite buffer | 100+ IOPS | 10+ MB/s |

**Recommended storage:**
- SSD for database and application
- NVMe for high-performance deployments
- Regular HDD acceptable for backups only

---

## 🔐 Security Requirements

### Minimum Security Measures

- [ ] Strong passwords (16+ characters, mixed case, numbers, symbols)
- [ ] Firewall enabled (ufw or iptables)
- [ ] SSH key authentication (disable password auth)
- [ ] Regular system updates (unattended-upgrades)
- [ ] Limited sudo access
- [ ] Fail2ban for brute force protection

### Production Security Additions

- [ ] SSL/TLS certificates (Let's Encrypt or commercial)
- [ ] VPN for remote administration
- [ ] Network segmentation (separate POS network)
- [ ] Intrusion detection (AIDE, OSSEC)
- [ ] Regular security audits
- [ ] Encrypted backups
- [ ] Two-factor authentication for admin

---

## ⏱️ Time Requirements

### Installation Timeline

| Phase | Duration | Notes |
|-------|----------|-------|
| Server preparation | 30 min | Including OS installation |
| Docker installation | 15 min | Via prep_server.sh |
| OpticsERP deployment | 45-60 min | First-time build |
| Configuration | 30 min | .env setup, module install |
| Testing | 30 min | Smoke tests, verification |
| **Total (fresh install)** | **2.5-3 hours** | Experienced admin |
| **Total (first-time)** | **4-5 hours** | With learning |

### Upgrade Timeline

| Type | Duration | Downtime |
|------|----------|----------|
| Minor version | 15-30 min | ~10 min |
| Major version | 45-60 min | ~30 min |
| Database migration | 1-2 hours | ~1 hour |

---

## 📊 Scalability Considerations

### Small Deployment (1-5 POS terminals)

**Server:** 4 GB RAM, 4 cores, 100 GB SSD
**Supports:**
- 5-10 concurrent users
- 20-30 receipts/hour peak
- 10,000 products
- 100,000 transactions/year

### Medium Deployment (6-20 POS terminals)

**Server:** 8 GB RAM, 8 cores, 250 GB SSD
**Supports:**
- 20-50 concurrent users
- 100-150 receipts/hour peak
- 50,000 products
- 500,000 transactions/year

### Large Deployment (21-40 POS terminals)

**Server:** 16 GB RAM, 16 cores, 500 GB SSD (RAID 10)
**Supports:**
- 50-100 concurrent users
- 300+ receipts/hour peak
- 100,000+ products
- 1,000,000+ transactions/year

**Note:** For >40 terminals, consider multi-server deployment with load balancing.

---

## ✅ Pre-Installation Checklist

Before proceeding with installation, verify:

### Hardware Checklist
- [ ] Server meets minimum requirements (4 GB RAM, 2 cores, 50 GB SSD)
- [ ] UPS installed and tested
- [ ] Network cabling installed and tested
- [ ] Static IP configured or DHCP reservation set

### Software Checklist
- [ ] Ubuntu 22.04 LTS installed
- [ ] Root/sudo access available
- [ ] Internet connectivity verified
- [ ] DNS resolution working

### Network Checklist
- [ ] Ports 8069, 8000 available
- [ ] Firewall rules planned
- [ ] POS terminals can ping server
- [ ] OFD API credentials obtained

### Documentation Checklist
- [ ] Installation guide reviewed
- [ ] `.env` values prepared
- [ ] Backup strategy planned
- [ ] Rollback plan prepared

---

**All requirements met?** Proceed to [Installation Steps →](02_installation_steps.md)

**Need help?** See [Troubleshooting Guide](05_troubleshooting.md)
