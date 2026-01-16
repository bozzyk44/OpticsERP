# Configuration Guide

**Last Updated:** 2025-11-30

---

## 📋 Overview

This guide covers advanced configuration options for OpticsERP after initial installation.

**Topics covered:**
- Environment variables (.env)
- Odoo configuration
- PostgreSQL tuning
- KKT Adapter settings
- Performance optimization
- Security hardening

---

## 🔧 Environment Variables (.env)

### Critical Variables

**Must be changed from defaults:**

```bash
# PostgreSQL - CHANGE PASSWORD!
POSTGRES_PASSWORD=YourStrongPasswordHere123!

# Odoo - CHANGE PASSWORD!
ODOO_ADMIN_PASSWORD=YourAdminPasswordHere123!

# KKT Adapter - YOUR OFD CREDENTIALS
KKT_OFD_API_URL=https://your-ofd-provider.ru/api/v1
KKT_OFD_API_TOKEN=your_actual_ofd_token_here
```

### PostgreSQL Configuration

```bash
# Database connection
POSTGRES_DB=opticserp
POSTGRES_USER=odoo
POSTGRES_PASSWORD=ChangeMeInProduction!
POSTGRES_HOST=postgres
POSTGRES_PORT=5432

# Performance tuning (production)
POSTGRES_MAX_CONNECTIONS=200
POSTGRES_SHARED_BUFFERS=2GB
POSTGRES_EFFECTIVE_CACHE_SIZE=6GB
POSTGRES_WORK_MEM=50MB
```

**Tuning guidelines:**
- `SHARED_BUFFERS`: 25% of RAM
- `EFFECTIVE_CACHE_SIZE`: 50-75% of RAM
- `WORK_MEM`: RAM / (max_connections * 2)

### Odoo Configuration

```bash
# Basic settings
ODOO_VERSION=17.0
ODOO_ADMIN_PASSWORD=AdminPasswordHere!
ODOO_DB_FILTER=opticserp

# Worker configuration (production)
ODOO_WORKERS=4                    # Number of worker processes
ODOO_MAX_CRON_THREADS=2           # Cron threads
ODOO_LIMIT_MEMORY_SOFT=2147483648 # 2 GB soft limit
ODOO_LIMIT_MEMORY_HARD=2684354560 # 2.5 GB hard limit

# Logging
ODOO_LOG_LEVEL=info
ODOO_LOG_HANDLER=:INFO
```

**Worker calculation:**
```
workers = (2 * CPU_cores) + 1
# Example: 4 cores = (2 * 4) + 1 = 9 workers
```

### KKT Adapter Configuration

```bash
# Server settings
KKT_ADAPTER_HOST=0.0.0.0
KKT_ADAPTER_PORT=8000

# OFD API
KKT_OFD_API_URL=https://ofd.example.ru/api/v1
KKT_OFD_API_TOKEN=your_token_here

# Buffer settings
KKT_BUFFER_MAX_SIZE=1000
KKT_BUFFER_PATH=/app/data/buffer.db

# Circuit Breaker
KKT_CIRCUIT_BREAKER_THRESHOLD=5
KKT_CIRCUIT_BREAKER_TIMEOUT=60
KKT_CIRCUIT_BREAKER_RECOVERY_TIMEOUT=300

# Sync settings
KKT_HLC_SYNC_INTERVAL=30
KKT_HEARTBEAT_INTERVAL=30
```

### Redis & Celery

```bash
# Redis connection
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=

# Celery
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0
CELERY_WORKERS=4
CELERY_MAX_TASKS_PER_CHILD=100
```

### Monitoring (Optional)

```bash
# Prometheus
PROMETHEUS_ENABLED=false
PROMETHEUS_PORT=9090

# Grafana
GRAFANA_PORT=3000
GRAFANA_ADMIN_USER=admin
GRAFANA_ADMIN_PASSWORD=admin

# Flower (Celery monitoring)
FLOWER_PORT=5555
FLOWER_BASIC_AUTH=admin:admin
```

---

## ⚙️ Odoo Configuration

### Via Web Interface

1. **Login** as admin
2. **Settings → General Settings**

### Company Configuration

**Settings → Users & Companies → Companies**

```
Company Name: Ваша Оптика ООО
Address: ул. Ленина, д. 1, г. Москва, 101000
Phone: +7 (495) 123-45-67
Email: info@your-optics.ru
Tax ID (ИНН): 1234567890
```

### Language & Localization

**Settings → General Settings → Languages**

- Install Russian: `ru_RU` ✅ Already done
- Set as default
- Configure date format: `dd.mm.yyyy`
- Time format: 24-hour

### POS Configuration

**Point of Sale → Configuration → Point of Sale**

```
Name: Касса 1
Allowed Companies: Ваша Оптика ООО
Available Payment Methods: Cash, Bank
Receipt Printer: Enable

# Fiscal settings (54-ФЗ)
Enable KKT Adapter: ✓
KKT Adapter URL: http://kkt_adapter:8000
```

### User Management

**Settings → Users & Companies → Users**

**Cashier user example:**
```
Name: Иванов Иван
Email: ivanov@example.ru
Access Rights:
  - Point of Sale / User
  - Sales / User
Security Groups:
  - Fiscal Operations / Allowed
```

---

## 🗄️ PostgreSQL Tuning

### Access PostgreSQL

```bash
# Via Docker
docker-compose exec postgres psql -U odoo -d opticserp

# Check connections
SELECT count(*) FROM pg_stat_activity;

# Check database size
SELECT pg_size_pretty(pg_database_size('opticserp'));
```

### Performance Queries

```sql
-- Slow queries
SELECT query, calls, total_time, mean_time
FROM pg_stat_statements
ORDER BY mean_time DESC
LIMIT 10;

-- Table sizes
SELECT schemaname, tablename,
       pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename))
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
LIMIT 10;

-- Index usage
SELECT schemaname, tablename, indexname,
       idx_scan, idx_tup_read, idx_tup_fetch
FROM pg_stat_user_indexes
ORDER BY idx_scan DESC;
```

### Maintenance

```bash
# Vacuum (weekly)
docker-compose exec postgres psql -U odoo -d opticserp -c "VACUUM ANALYZE;"

# Reindex (monthly)
docker-compose exec postgres psql -U odoo -d opticserp -c "REINDEX DATABASE opticserp;"
```

---

## 🔐 Security Configuration

### SSL/TLS (Production)

**Using Let's Encrypt:**

```bash
# Install certbot
sudo apt install certbot

# Get certificate
sudo certbot certonly --standalone -d your-domain.com

# Certificates will be in:
# /etc/letsencrypt/live/your-domain.com/
```

**Update .env:**
```bash
SSL_ENABLED=true
SSL_CERT_PATH=/etc/letsencrypt/live/your-domain.com/fullchain.pem
SSL_KEY_PATH=/etc/letsencrypt/live/your-domain.com/privkey.pem
```

### Firewall Rules

```bash
# Enable UFW
sudo ufw enable

# SSH (administration)
sudo ufw allow 22/tcp

# Odoo (HTTPS only in production)
sudo ufw allow 443/tcp

# KKT Adapter (from POS terminals only)
sudo ufw allow from 192.168.1.0/24 to any port 8000 proto tcp

# Deny HTTP in production
# sudo ufw deny 80/tcp
```

### Password Policy

**Strong passwords:**
```bash
# Generate strong password
openssl rand -base64 32

# Example output:
# 7xK9mP2qL5nR8tY3wV6zB4cF1dG0hJ

# Use in .env
POSTGRES_PASSWORD=7xK9mP2qL5nR8tY3wV6zB4cF1dG0hJ
```

**Requirements:**
- Minimum 16 characters
- Mixed case letters
- Numbers and symbols
- No dictionary words
- Unique per service

---

## 📊 Performance Optimization

### Docker Resource Limits

**docker-compose.yml adjustments:**

```yaml
services:
  odoo:
    deploy:
      resources:
        limits:
          cpus: '4'
          memory: 8G
        reservations:
          cpus: '2'
          memory: 4G
```

### Log Rotation

**docker-compose.yml:**

```yaml
services:
  odoo:
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

### Database Connection Pooling

**pgbouncer (optional for high load):**

```bash
# Add to docker-compose.yml
pgbouncer:
  image: pgbouncer/pgbouncer
  environment:
    DATABASES_HOST: postgres
    DATABASES_PORT: 5432
    DATABASES_DBNAME: opticserp
```

---

## 🔄 Backup Configuration

### Automated Daily Backups

```bash
# Edit crontab
crontab -e

# Add daily backup at 2 AM
0 2 * * * cd /path/to/OpticsERP && bash scripts/backup.sh >> /var/log/opticserp-backup.log 2>&1

# Weekly cleanup at 3 AM Sunday
0 3 * * 0 find /opt/opticserp/backups -name "*.gz" -mtime +90 -delete
```

### Backup Retention

**Edit .env:**
```bash
BACKUP_RETENTION_DAYS=90  # Keep 90 days
BACKUP_PATH=/opt/opticserp/backups
```

---

## 🌐 Network Configuration

### Static IP Configuration

**Ubuntu netplan:**

```bash
# Edit /etc/netplan/01-netcfg.yaml
sudo nano /etc/netplan/01-netcfg.yaml
```

```yaml
network:
  version: 2
  ethernets:
    eth0:
      addresses:
        - 192.168.1.10/24
      gateway4: 192.168.1.1
      nameservers:
        addresses:
          - 8.8.8.8
          - 8.8.4.4
```

```bash
# Apply configuration
sudo netplan apply
```

### DNS Configuration

```bash
# Edit /etc/hosts
sudo nano /etc/hosts

# Add entry
192.168.1.10    opticserp.local
```

---

## 📈 Monitoring Setup

### Enable Prometheus

```bash
# Edit .env
PROMETHEUS_ENABLED=true
PROMETHEUS_PORT=9090

# Restart services
docker-compose up -d prometheus
```

**Access:** http://your-server:9090

### Grafana Dashboards

```bash
# Start Grafana
docker-compose up -d grafana

# Access: http://your-server:3000
# Login: admin / admin (change immediately!)
```

**Import dashboards:**
1. Login to Grafana
2. Dashboards → Import
3. Import from grafana.com:
   - PostgreSQL: ID 9628
   - Docker: ID 893
   - Redis: ID 763

---

## ✅ Configuration Checklist

**After installation:**

- [ ] Changed all default passwords
- [ ] Configured company information
- [ ] Set up POS terminals
- [ ] Configured KKT Adapter with OFD credentials
- [ ] Enabled SSL/TLS (production)
- [ ] Configured firewall rules
- [ ] Set up automated backups
- [ ] Configured static IP
- [ ] Enabled monitoring (optional)
- [ ] Tested POS operations
- [ ] Verified fiscal receipts
- [ ] Documented custom configurations

---

**Configuration complete?** Proceed to [Verification Guide →](04_verification.md)

**Need help?** See [Troubleshooting Guide](05_troubleshooting.md)
