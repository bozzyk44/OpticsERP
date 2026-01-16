# Appendix A: Port Reference

**Last Updated:** 2025-11-30

---

## 📋 Overview

Complete reference of all network ports used by OpticsERP components.

**Critical rule:** ALWAYS use standard ports. NEVER change unless absolutely necessary.

---

## 🔌 Standard Port Allocation

### Core Services

| Service | Port | Protocol | Purpose | Access |
|---------|------|----------|---------|--------|
| **Odoo Web** | **8069** | HTTP | Web interface, REST API | Public (LAN/WAN) |
| **Odoo Longpolling** | 8072 | HTTP | Real-time notifications | Public (LAN/WAN) |
| **PostgreSQL** | **5432** | TCP | Database server | Internal only |
| **Redis** | **6379** | TCP | Cache, message broker | Internal only |
| **KKT Adapter** | **8000** | HTTP | Fiscal device API | LAN only |

### Optional/Monitoring Services

| Service | Port | Protocol | Purpose | Access |
|---------|------|----------|---------|--------|
| Celery Flower | 5555 | HTTP | Celery task monitoring | Internal/Admin |
| Prometheus | 9090 | HTTP | Metrics collection | Internal/Admin |
| Grafana | 3000 | HTTP | Monitoring dashboards | Internal/Admin |
| Node Exporter | 9100 | HTTP | System metrics | Internal only |
| PostgreSQL Exporter | 9187 | HTTP | Database metrics | Internal only |
| Redis Exporter | 9121 | HTTP | Redis metrics | Internal only |

### Production (HTTPS)

| Service | Port | Protocol | Purpose | Access |
|---------|------|----------|---------|--------|
| Nginx/Traefik | 443 | HTTPS | Reverse proxy (SSL) | Public (WAN) |
| Nginx/Traefik | 80 | HTTP | HTTP → HTTPS redirect | Public (WAN) |

### Administration

| Service | Port | Protocol | Purpose | Access |
|---------|------|----------|---------|--------|
| SSH | 22 | TCP | Remote administration | Admin only |
| NTP | 123 | UDP | Time synchronization | Outbound only |
| DNS | 53 | UDP | Name resolution | Outbound only |

---

## 🏢 Deployment Scenarios

### Development Environment (Single Server)

**Open ports:**
```
8069 (Odoo Web)
8000 (KKT Adapter)
5432 (PostgreSQL) - localhost only
6379 (Redis) - localhost only
5555 (Flower) - localhost only
```

**Docker Compose mapping:**
```yaml
services:
  odoo:
    ports:
      - "8069:8069"  # Odoo Web
      - "8072:8072"  # Longpolling

  postgres:
    ports:
      - "127.0.0.1:5432:5432"  # Localhost only

  redis:
    ports:
      - "127.0.0.1:6379:6379"  # Localhost only

  kkt_adapter:
    ports:
      - "8000:8000"  # KKT API

  flower:
    ports:
      - "127.0.0.1:5555:5555"  # Monitoring (localhost)
```

### Production Environment (Multi-Server)

**Server 1 (Application):**
```
443 (HTTPS - Nginx)
80 (HTTP redirect)
22 (SSH - admin only)
```

**Server 2 (Database):**
```
5432 (PostgreSQL - app server only)
22 (SSH - admin only)
```

**Server 3 (KKT Adapter - POS terminals):**
```
8000 (KKT API - LAN only)
22 (SSH - admin only)
```

**Server 4 (Monitoring):**
```
3000 (Grafana - admin VPN)
9090 (Prometheus - internal)
22 (SSH - admin only)
```

---

## 🔐 Firewall Configuration

### Ubuntu UFW (Development)

```bash
# Enable firewall
sudo ufw enable

# SSH (administration)
sudo ufw allow 22/tcp

# Odoo Web Interface
sudo ufw allow 8069/tcp

# KKT Adapter (from LAN only)
sudo ufw allow from 192.168.1.0/24 to any port 8000 proto tcp

# Deny all other incoming
sudo ufw default deny incoming
sudo ufw default allow outgoing

# Check status
sudo ufw status verbose
```

**Expected output:**
```
Status: active

To                         Action      From
--                         ------      ----
22/tcp                     ALLOW       Anywhere
8069/tcp                   ALLOW       Anywhere
8000/tcp                   ALLOW       192.168.1.0/24
```

### Ubuntu UFW (Production)

```bash
# SSH
sudo ufw allow 22/tcp

# HTTPS only (HTTP redirects to HTTPS)
sudo ufw allow 443/tcp
sudo ufw allow 80/tcp

# KKT Adapter (POS LAN only)
sudo ufw allow from 192.168.10.0/24 to any port 8000 proto tcp

# Admin monitoring (VPN only)
sudo ufw allow from 10.8.0.0/24 to any port 3000 proto tcp
sudo ufw allow from 10.8.0.0/24 to any port 9090 proto tcp

# Deny direct access to Odoo (use Nginx proxy)
sudo ufw deny 8069/tcp

# Status
sudo ufw status numbered
```

### iptables (Advanced)

```bash
# Flush existing rules
sudo iptables -F

# Default policies
sudo iptables -P INPUT DROP
sudo iptables -P FORWARD DROP
sudo iptables -P OUTPUT ACCEPT

# Allow loopback
sudo iptables -A INPUT -i lo -j ACCEPT

# Allow established connections
sudo iptables -A INPUT -m state --state ESTABLISHED,RELATED -j ACCEPT

# SSH
sudo iptables -A INPUT -p tcp --dport 22 -j ACCEPT

# HTTPS
sudo iptables -A INPUT -p tcp --dport 443 -j ACCEPT

# KKT Adapter (LAN only)
sudo iptables -A INPUT -s 192.168.10.0/24 -p tcp --dport 8000 -j ACCEPT

# Save rules
sudo iptables-save > /etc/iptables/rules.v4
```

### Cloud Provider Security Groups (AWS/Azure/GCP)

**Application server security group:**
```
Inbound:
  - 443/tcp from 0.0.0.0/0 (HTTPS)
  - 80/tcp from 0.0.0.0/0 (HTTP redirect)
  - 22/tcp from [admin-ip]/32 (SSH)

Outbound:
  - All traffic allowed
```

**Database server security group:**
```
Inbound:
  - 5432/tcp from [app-server-sg] (PostgreSQL)
  - 22/tcp from [admin-ip]/32 (SSH)

Outbound:
  - All traffic allowed
```

**KKT Adapter server security group:**
```
Inbound:
  - 8000/tcp from 192.168.10.0/24 (KKT API - POS LAN)
  - 22/tcp from [admin-ip]/32 (SSH)

Outbound:
  - 443/tcp to 0.0.0.0/0 (OFD API)
  - All traffic allowed
```

---

## 🌐 Network Topology

### Single-Server Deployment (Development/Small Business)

```
Internet
   |
   | :443 (HTTPS)
   | :80 (HTTP)
   |
[Ubuntu Server]
   |
   ├─ Nginx :443 → Odoo :8069
   ├─ Odoo :8069 (Web)
   ├─ PostgreSQL :5432 (localhost)
   ├─ Redis :6379 (localhost)
   ├─ KKT Adapter :8000 (LAN)
   └─ Celery workers (background)
```

**Network requirements:**
- **WAN:** 1 public IP, ≥10 Mbps upload
- **LAN:** 192.168.1.0/24, Gigabit Ethernet

### Multi-Server Deployment (Production)

```
Internet
   |
   | :443 (HTTPS)
   |
[Load Balancer]
   |
   | :8069 (internal)
   |
   ├─── [App Server 1] :8069
   |        └─ Odoo + Celery
   |
   ├─── [App Server 2] :8069
   |        └─ Odoo + Celery
   |
   └─── [Database Server] :5432
            └─ PostgreSQL + Redis

[POS Terminal LAN]
   |
   | :8000
   |
[KKT Adapter Server] :8000
   └─ FastAPI + SQLite buffer
```

**Network requirements:**
- **WAN:** ≥100 Mbps
- **LAN:** Gigabit Ethernet, isolated VLAN for POS terminals
- **Inter-server:** ≥10 Gbps (if same datacenter)

---

## 🔧 Port Conflict Resolution

### Check if Port is in Use

**Linux:**
```bash
# Check specific port
sudo netstat -tulpn | grep :8069

# Or with ss (modern)
sudo ss -tulpn | grep :8069

# Or with lsof
sudo lsof -i :8069
```

**Windows:**
```bash
netstat -ano | findstr :8069
```

**Expected output (port in use):**
```
tcp  0  0  0.0.0.0:8069  0.0.0.0:*  LISTEN  1234/python3
```

### Kill Process on Port

**Using kill_port.py script:**
```bash
# Kill single port
python scripts/kill_port.py 8069

# Kill multiple ports
python scripts/kill_port.py 8069 8000 5432
```

**Manual method (Linux):**
```bash
# Find PID
sudo lsof -ti:8069

# Kill process
sudo kill -9 $(sudo lsof -ti:8069)
```

**Manual method (Windows):**
```bash
# Find PID
netstat -ano | findstr :8069

# Kill process (replace 1234 with actual PID)
taskkill /PID 1234 /F
```

### Change Port (NOT RECOMMENDED)

**If you MUST change a port, update all configuration files:**

**1. .env file:**
```bash
# Change Odoo port
ODOO_PORT=8070  # Changed from 8069
```

**2. docker-compose.yml:**
```yaml
services:
  odoo:
    ports:
      - "${ODOO_PORT:-8070}:8069"  # Map to 8070
```

**3. Firewall:**
```bash
sudo ufw allow 8070/tcp
sudo ufw delete allow 8069/tcp
```

**4. Nginx config (if used):**
```nginx
upstream odoo {
    server localhost:8070;  # Changed from 8069
}
```

**5. Documentation:**
- Update all references to new port
- Document change in CHANGELOG.md

**⚠️ WARNING:** Changing standard ports complicates troubleshooting and future upgrades!

---

## 📊 Port Usage Monitoring

### Check Port Usage (Prometheus)

**Prometheus metrics:**
```yaml
# /etc/prometheus/prometheus.yml
- job_name: 'node'
  static_configs:
    - targets: ['localhost:9100']

# Query port listeners
sum by (port) (node_netstat_Tcp_CurrEstab)
```

### Grafana Dashboard

**Panel: Active Connections by Port**
```promql
sum by (port) (
  rate(node_netstat_Tcp_InSegs[5m])
)
```

### Log Port Connections

**Nginx access log:**
```nginx
log_format main '$remote_addr - $remote_user [$time_local] '
                '"$request" $status $body_bytes_sent '
                '"$http_referer" "$http_user_agent" '
                'upstream: $upstream_addr';

access_log /var/log/nginx/access.log main;
```

**PostgreSQL connection log:**
```bash
# Edit postgresql.conf
log_connections = on
log_disconnections = on
log_line_prefix = '%t [%p]: [%l-1] user=%u,db=%d,app=%a,client=%h '
```

---

## 🛡️ Security Best Practices

### Principle of Least Privilege

**Only expose necessary ports:**
- ✅ Production: 443, 80, 22 (admin IP only)
- ❌ Production: Do NOT expose 5432, 6379, 9090, etc.

**Use VPN for admin access:**
- Grafana :3000 → VPN only
- Prometheus :9090 → VPN only
- Flower :5555 → VPN only
- SSH :22 → VPN or specific IPs

### Port Scanning Detection

**Install fail2ban:**
```bash
sudo apt install fail2ban -y

# Configure /etc/fail2ban/jail.local
[ssh]
enabled = true
port = ssh
filter = sshd
logpath = /var/log/auth.log
maxretry = 3
bantime = 3600

[nginx-limit-req]
enabled = true
port = http,https
filter = nginx-limit-req
logpath = /var/log/nginx/error.log
maxretry = 5
```

### Rate Limiting

**Nginx rate limit (DDoS protection):**
```nginx
http {
    limit_req_zone $binary_remote_addr zone=one:10m rate=10r/s;

    server {
        listen 443 ssl;

        location / {
            limit_req zone=one burst=20 nodelay;
            proxy_pass http://odoo;
        }
    }
}
```

---

## 📝 Quick Reference Table

### Port Checklist for Fresh Installation

- [ ] **8069** - Odoo accessible from browser
- [ ] **5432** - PostgreSQL (localhost only)
- [ ] **6379** - Redis (localhost only)
- [ ] **8000** - KKT Adapter API (LAN accessible)
- [ ] **22** - SSH (admin IP only)
- [ ] **443** - HTTPS (production only)
- [ ] **9090** - Prometheus (if monitoring enabled)
- [ ] **3000** - Grafana (if monitoring enabled)

### Troubleshooting Commands

```bash
# List all listening ports
sudo netstat -tulpn

# Check specific service
docker-compose port odoo 8069

# Test connection
telnet localhost 8069
curl -I http://localhost:8069

# Check firewall
sudo ufw status verbose
sudo iptables -L -n -v
```

---

**Need more details?** See:
- [System Requirements](01_system_requirements.md) - Network topology
- [Configuration Guide](03_configuration.md) - Network configuration
- [Troubleshooting Guide](05_troubleshooting.md) - Port issues

---

**Last Updated:** 2025-11-30
