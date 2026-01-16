# Appendix B: Environment Variables Reference

**Last Updated:** 2025-11-30

---

## 📋 Overview

Complete reference for all environment variables used in OpticsERP `.env` file.

**Configuration file:** `.env` (root directory)
**Template:** `.env.example`

---

## 🔐 PostgreSQL Configuration

### Basic Connection

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `POSTGRES_DB` | string | `opticserp` | Database name |
| `POSTGRES_USER` | string | `odoo` | Database user |
| `POSTGRES_PASSWORD` | **secret** | ⚠️ CHANGE ME | Database password (≥16 chars) |
| `POSTGRES_HOST` | string | `postgres` | Database host (Docker service name) |
| `POSTGRES_PORT` | int | `5432` | PostgreSQL port |

**Example:**
```bash
POSTGRES_DB=opticserp
POSTGRES_USER=odoo
POSTGRES_PASSWORD=YourStrongPasswordHere123!
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
```

### Performance Tuning

| Variable | Type | Default | Production | Description |
|----------|------|---------|------------|-------------|
| `POSTGRES_MAX_CONNECTIONS` | int | `100` | `200` | Maximum concurrent connections |
| `POSTGRES_SHARED_BUFFERS` | size | `128MB` | `2GB` | Shared memory buffer (25% RAM) |
| `POSTGRES_EFFECTIVE_CACHE_SIZE` | size | `4GB` | `6GB` | OS cache estimate (50-75% RAM) |
| `POSTGRES_WORK_MEM` | size | `4MB` | `50MB` | Per-operation memory (RAM / max_conn / 2) |
| `POSTGRES_MAINTENANCE_WORK_MEM` | size | `64MB` | `512MB` | VACUUM/CREATE INDEX memory |
| `POSTGRES_WAL_BUFFERS` | size | `16MB` | `32MB` | Write-ahead log buffers |

**Example (production, 16 GB RAM):**
```bash
POSTGRES_MAX_CONNECTIONS=200
POSTGRES_SHARED_BUFFERS=2GB
POSTGRES_EFFECTIVE_CACHE_SIZE=6GB
POSTGRES_WORK_MEM=50MB
POSTGRES_MAINTENANCE_WORK_MEM=512MB
POSTGRES_WAL_BUFFERS=32MB
```

### Connection Pooling (pgbouncer)

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `PGBOUNCER_ENABLED` | bool | `false` | Enable pgbouncer |
| `PGBOUNCER_POOL_MODE` | enum | `transaction` | Pooling mode: `session`, `transaction`, `statement` |
| `PGBOUNCER_MAX_CLIENT_CONN` | int | `1000` | Maximum client connections |
| `PGBOUNCER_DEFAULT_POOL_SIZE` | int | `25` | Connections per database/user |

---

## 🌐 Odoo Configuration

### Basic Settings

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `ODOO_VERSION` | string | `17.0` | Odoo version |
| `ODOO_ADMIN_PASSWORD` | **secret** | ⚠️ CHANGE ME | Master admin password |
| `ODOO_DB_FILTER` | string | `opticserp` | Database filter (regex) |
| `ODOO_PORT` | int | `8069` | Web server port |
| `ODOO_LONGPOLLING_PORT` | int | `8072` | Longpolling/Websocket port |

**Example:**
```bash
ODOO_VERSION=17.0
ODOO_ADMIN_PASSWORD=YourAdminPasswordHere123!
ODOO_DB_FILTER=opticserp
ODOO_PORT=8069
ODOO_LONGPOLLING_PORT=8072
```

### Worker Configuration (Production)

| Variable | Type | Default | Production | Description |
|----------|------|---------|------------|-------------|
| `ODOO_WORKERS` | int | `0` | `4-9` | Number of worker processes ((CPU*2)+1) |
| `ODOO_MAX_CRON_THREADS` | int | `2` | `2` | Cron worker threads |
| `ODOO_LIMIT_MEMORY_SOFT` | bytes | `2147483648` | `2147483648` | Soft memory limit (2 GB) |
| `ODOO_LIMIT_MEMORY_HARD` | bytes | `2684354560` | `2684354560` | Hard memory limit (2.5 GB) |
| `ODOO_LIMIT_TIME_CPU` | int | `60` | `600` | CPU time limit (seconds) |
| `ODOO_LIMIT_TIME_REAL` | int | `120` | `1200` | Real time limit (seconds) |
| `ODOO_LIMIT_REQUEST` | int | `8192` | `8192` | Requests before worker restart |

**Worker calculation:**
```bash
# Formula: workers = (2 * CPU_cores) + 1
# Example: 4 cores = (2 * 4) + 1 = 9 workers
ODOO_WORKERS=9
```

### Logging

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `ODOO_LOG_LEVEL` | enum | `info` | Log level: `debug`, `info`, `warn`, `error`, `critical` |
| `ODOO_LOG_HANDLER` | string | `:INFO` | Handler-specific log levels |
| `ODOO_LOG_DB` | bool | `false` | Log database queries |
| `ODOO_LOG_DB_LEVEL` | enum | `warning` | Database log level |

**Example (production):**
```bash
ODOO_LOG_LEVEL=info
ODOO_LOG_HANDLER=:INFO,werkzeug:WARNING,odoo.sql_db:WARNING
ODOO_LOG_DB=false
```

**Example (debug):**
```bash
ODOO_LOG_LEVEL=debug
ODOO_LOG_HANDLER=:DEBUG
ODOO_LOG_DB=true
ODOO_LOG_DB_LEVEL=debug
```

### Email Configuration

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `ODOO_EMAIL_FROM` | email | `` | Default "From" email |
| `ODOO_SMTP_SERVER` | string | `localhost` | SMTP server hostname |
| `ODOO_SMTP_PORT` | int | `25` | SMTP port (25, 465, 587) |
| `ODOO_SMTP_USER` | string | `` | SMTP username |
| `ODOO_SMTP_PASSWORD` | **secret** | `` | SMTP password |
| `ODOO_SMTP_SSL` | bool | `false` | Use SSL (port 465) |
| `ODOO_SMTP_STARTTLS` | bool | `false` | Use STARTTLS (port 587) |

**Example (Gmail):**
```bash
ODOO_EMAIL_FROM=noreply@youroptics.ru
ODOO_SMTP_SERVER=smtp.gmail.com
ODOO_SMTP_PORT=587
ODOO_SMTP_USER=your-email@gmail.com
ODOO_SMTP_PASSWORD=your-app-password
ODOO_SMTP_SSL=false
ODOO_SMTP_STARTTLS=true
```

---

## 🧾 KKT Adapter Configuration (54-ФЗ)

### Server Settings

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `KKT_ADAPTER_HOST` | string | `0.0.0.0` | Listen address |
| `KKT_ADAPTER_PORT` | int | `8000` | FastAPI server port |
| `KKT_DEBUG` | bool | `false` | Debug mode |
| `KKT_LOG_LEVEL` | enum | `INFO` | Log level |

**Example:**
```bash
KKT_ADAPTER_HOST=0.0.0.0
KKT_ADAPTER_PORT=8000
KKT_DEBUG=false
KKT_LOG_LEVEL=INFO
```

### OFD API (Operator Fiscal Data)

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `KKT_OFD_API_URL` | url | ⚠️ REQUIRED | OFD provider API URL |
| `KKT_OFD_API_TOKEN` | **secret** | ⚠️ REQUIRED | OFD API authentication token |
| `KKT_OFD_TIMEOUT` | int | `10` | Request timeout (seconds) |
| `KKT_OFD_RETRY_ATTEMPTS` | int | `3` | Retry attempts |
| `KKT_OFD_RETRY_DELAY` | int | `5` | Delay between retries (seconds) |

**Example:**
```bash
KKT_OFD_API_URL=https://your-ofd-provider.ru/api/v1
KKT_OFD_API_TOKEN=your_actual_ofd_token_here
KKT_OFD_TIMEOUT=10
KKT_OFD_RETRY_ATTEMPTS=3
KKT_OFD_RETRY_DELAY=5
```

### Buffer Configuration (SQLite)

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `KKT_BUFFER_PATH` | path | `/app/data/buffer.db` | SQLite buffer database path |
| `KKT_BUFFER_MAX_SIZE` | int | `1000` | Maximum receipts in buffer |
| `KKT_BUFFER_ALERT_THRESHOLD` | float | `0.8` | Alert threshold (80%) |
| `KKT_BUFFER_BLOCK_THRESHOLD` | float | `1.0` | Block new receipts (100%) |

**Example:**
```bash
KKT_BUFFER_PATH=/app/data/buffer.db
KKT_BUFFER_MAX_SIZE=1000
KKT_BUFFER_ALERT_THRESHOLD=0.8  # Alert at 800 receipts
KKT_BUFFER_BLOCK_THRESHOLD=1.0  # Block at 1000 receipts
```

### Circuit Breaker

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `KKT_CIRCUIT_BREAKER_THRESHOLD` | int | `5` | Failures before OPEN state |
| `KKT_CIRCUIT_BREAKER_TIMEOUT` | int | `60` | Timeout in OPEN state (seconds) |
| `KKT_CIRCUIT_BREAKER_RECOVERY_TIMEOUT` | int | `300` | Recovery period (seconds) |

**States:**
- **CLOSED** - Normal operation
- **OPEN** - OFD unavailable, buffer-only mode
- **HALF_OPEN** - Testing recovery

**Example:**
```bash
KKT_CIRCUIT_BREAKER_THRESHOLD=5        # 5 failures → OPEN
KKT_CIRCUIT_BREAKER_TIMEOUT=60         # Wait 60s before test
KKT_CIRCUIT_BREAKER_RECOVERY_TIMEOUT=300  # 5min recovery period
```

### Sync Configuration

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `KKT_HLC_SYNC_INTERVAL` | int | `30` | Buffer sync interval (seconds) |
| `KKT_HEARTBEAT_INTERVAL` | int | `30` | Heartbeat to Odoo (seconds) |
| `KKT_SYNC_BATCH_SIZE` | int | `100` | Receipts per sync batch |
| `KKT_SYNC_WORKERS` | int | `4` | Concurrent sync workers |

**Example:**
```bash
KKT_HLC_SYNC_INTERVAL=30  # Sync every 30 seconds
KKT_HEARTBEAT_INTERVAL=30  # Health check every 30s
KKT_SYNC_BATCH_SIZE=100   # Send 100 receipts per batch
KKT_SYNC_WORKERS=4        # Use 4 worker threads
```

### Hybrid Logical Clock (HLC)

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `KKT_HLC_ENABLED` | bool | `true` | Enable HLC timestamps |
| `KKT_HLC_NTP_SERVER` | string | `pool.ntp.org` | NTP server for time sync |
| `KKT_HLC_DRIFT_ALERT` | int | `1000` | Alert on drift >1000ms |

---

## 📦 Redis Configuration

### Connection

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `REDIS_HOST` | string | `redis` | Redis host |
| `REDIS_PORT` | int | `6379` | Redis port |
| `REDIS_DB` | int | `0` | Database number (0-15) |
| `REDIS_PASSWORD` | **secret** | `` | Redis password (optional) |

**Example:**
```bash
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=  # Empty = no auth
```

### Performance

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `REDIS_MAXMEMORY` | size | `256MB` | Maximum memory |
| `REDIS_MAXMEMORY_POLICY` | enum | `allkeys-lru` | Eviction policy |

**Eviction policies:**
- `noeviction` - Return errors when memory limit reached
- `allkeys-lru` - Evict least recently used keys
- `allkeys-lfu` - Evict least frequently used keys
- `volatile-lru` - Evict LRU keys with TTL

---

## 🐝 Celery Configuration

### Broker & Backend

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `CELERY_BROKER_URL` | url | `redis://redis:6379/0` | Message broker URL |
| `CELERY_RESULT_BACKEND` | url | `redis://redis:6379/0` | Result backend URL |

### Workers

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `CELERY_WORKERS` | int | `4` | Number of worker processes |
| `CELERY_MAX_TASKS_PER_CHILD` | int | `100` | Tasks before worker restart |
| `CELERY_TASK_TIME_LIMIT` | int | `300` | Task timeout (seconds) |
| `CELERY_TASK_SOFT_TIME_LIMIT` | int | `240` | Soft timeout (seconds) |

**Example:**
```bash
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0
CELERY_WORKERS=4
CELERY_MAX_TASKS_PER_CHILD=100
CELERY_TASK_TIME_LIMIT=300
```

---

## 📊 Monitoring Configuration

### Prometheus

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `PROMETHEUS_ENABLED` | bool | `false` | Enable Prometheus |
| `PROMETHEUS_PORT` | int | `9090` | Prometheus web port |
| `PROMETHEUS_RETENTION` | string | `15d` | Data retention period |

### Grafana

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `GRAFANA_PORT` | int | `3000` | Grafana web port |
| `GRAFANA_ADMIN_USER` | string | `admin` | Admin username |
| `GRAFANA_ADMIN_PASSWORD` | **secret** | `admin` | Admin password (⚠️ CHANGE!) |

### Flower (Celery Monitoring)

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `FLOWER_PORT` | int | `5555` | Flower web port |
| `FLOWER_BASIC_AUTH` | string | `admin:admin` | Basic auth (user:pass) |

**Example:**
```bash
PROMETHEUS_ENABLED=true
PROMETHEUS_PORT=9090
PROMETHEUS_RETENTION=90d

GRAFANA_PORT=3000
GRAFANA_ADMIN_USER=admin
GRAFANA_ADMIN_PASSWORD=StrongGrafanaPassword123!

FLOWER_PORT=5555
FLOWER_BASIC_AUTH=admin:FlowerPassword123!
```

---

## 🔒 Security Configuration

### SSL/TLS (Production)

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `SSL_ENABLED` | bool | `false` | Enable HTTPS |
| `SSL_CERT_PATH` | path | `` | SSL certificate path |
| `SSL_KEY_PATH` | path | `` | SSL private key path |
| `SSL_REDIRECT_HTTP` | bool | `true` | Redirect HTTP → HTTPS |

**Example (Let's Encrypt):**
```bash
SSL_ENABLED=true
SSL_CERT_PATH=/etc/letsencrypt/live/your-domain.com/fullchain.pem
SSL_KEY_PATH=/etc/letsencrypt/live/your-domain.com/privkey.pem
SSL_REDIRECT_HTTP=true
```

### Session Security

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `ODOO_SESSION_TIMEOUT` | int | `7200` | Session timeout (seconds, 2h) |
| `ODOO_SESSION_COOKIE_SECURE` | bool | `false` | HTTPS-only cookies |
| `ODOO_SESSION_COOKIE_HTTPONLY` | bool | `true` | JavaScript-proof cookies |

---

## 💾 Backup Configuration

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `BACKUP_ENABLED` | bool | `true` | Enable automated backups |
| `BACKUP_PATH` | path | `/opt/opticserp/backups` | Backup directory |
| `BACKUP_RETENTION_DAYS` | int | `90` | Retention period (days) |
| `BACKUP_COMPRESS` | bool | `true` | Gzip compression |
| `BACKUP_OFFSITE_ENABLED` | bool | `false` | Enable off-site backup |
| `BACKUP_OFFSITE_PATH` | path | `` | NFS/CIFS mount path |

**Example:**
```bash
BACKUP_ENABLED=true
BACKUP_PATH=/opt/opticserp/backups
BACKUP_RETENTION_DAYS=90
BACKUP_COMPRESS=true
BACKUP_OFFSITE_ENABLED=true
BACKUP_OFFSITE_PATH=/mnt/nas/opticserp-backups
```

---

## 🌍 Localization

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `TZ` | string | `Europe/Moscow` | Timezone (tz database) |
| `LANG` | string | `ru_RU.UTF-8` | System locale |
| `ODOO_LANG` | string | `ru_RU` | Odoo default language |

**Common timezones:**
- `Europe/Moscow` - MSK (UTC+3)
- `Europe/Samara` - SAMT (UTC+4)
- `Asia/Yekaterinburg` - YEKT (UTC+5)
- `Asia/Novosibirsk` - NOVT (UTC+7)

---

## 🔧 Development Configuration

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `ENVIRONMENT` | enum | `production` | Environment: `development`, `production` |
| `DEBUG` | bool | `false` | Enable debug mode |
| `DEV_MODE` | bool | `false` | Developer mode (auto-reload) |
| `ODOO_DEV_MODE` | string | `` | Odoo dev options: `all`, `qweb`, `assets` |

**Example (development):**
```bash
ENVIRONMENT=development
DEBUG=true
DEV_MODE=true
ODOO_DEV_MODE=all
ODOO_LOG_LEVEL=debug
```

---

## 🔗 JIRA Integration (Optional)

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `JIRA_URL` | url | `` | JIRA instance URL |
| `JIRA_EMAIL` | email | `` | JIRA user email |
| `JIRA_API_TOKEN` | **secret** | `` | JIRA API token |
| `JIRA_PROJECT_KEY` | string | `OPTERP` | JIRA project key |

**Example:**
```bash
JIRA_URL=https://your-company.atlassian.net
JIRA_EMAIL=admin@youroptics.ru
JIRA_API_TOKEN=your_jira_api_token_here
JIRA_PROJECT_KEY=OPTERP
```

---

## ✅ Configuration Validation

### Required Variables (Production)

**Must be set before deployment:**
```bash
# Passwords (NEVER use defaults!)
POSTGRES_PASSWORD=...
ODOO_ADMIN_PASSWORD=...

# OFD Credentials (54-ФЗ compliance)
KKT_OFD_API_URL=https://...
KKT_OFD_API_TOKEN=...

# Email (for notifications)
ODOO_EMAIL_FROM=...
ODOO_SMTP_SERVER=...
ODOO_SMTP_PASSWORD=...
```

### Validate Configuration

**Using validation script:**
```bash
python3 scripts/validate_config.py

# Expected output:
=== OpticsERP Configuration Validation ===

=== Environment File ===
✅ .env file exists
✅ All required environment variables present
✅ POSTGRES_PASSWORD: Strong (24 chars)
✅ ODOO_ADMIN_PASSWORD: Strong (28 chars)
✅ KKT_OFD_API_TOKEN: Set

=== Warnings ===
⚠️  SSL_ENABLED=false (production should use HTTPS)
⚠️  BACKUP_OFFSITE_ENABLED=false (recommended for production)

=== Recommendations ===
- Enable SSL for production deployment
- Configure off-site backups
- Change default Grafana password

✅ Configuration is valid
```

**Manual validation:**
```bash
# Check required variables
grep -E "^(POSTGRES_PASSWORD|ODOO_ADMIN_PASSWORD|KKT_OFD_API_TOKEN)=" .env

# Check password strength
echo "$POSTGRES_PASSWORD" | wc -c  # Should be ≥16

# Verify no default passwords
grep -i "change" .env  # Should return 0 matches
```

---

## 📝 Configuration Examples

### Development Environment

```bash
# === Development Configuration ===
ENVIRONMENT=development
DEBUG=true
DEV_MODE=true

# PostgreSQL
POSTGRES_PASSWORD=devpassword123
ODOO_ADMIN_PASSWORD=admin123

# Odoo
ODOO_WORKERS=0  # Single-threaded for debugging
ODOO_LOG_LEVEL=debug
ODOO_DEV_MODE=all

# KKT Adapter
KKT_DEBUG=true
KKT_OFD_API_URL=https://test-ofd.example.ru/api/v1  # Test OFD
KKT_OFD_API_TOKEN=test_token

# Monitoring
PROMETHEUS_ENABLED=false
GRAFANA_ADMIN_PASSWORD=admin
```

### Production Environment

```bash
# === Production Configuration ===
ENVIRONMENT=production
DEBUG=false

# PostgreSQL (16 GB RAM server)
POSTGRES_PASSWORD=P@ssw0rd_Str0ng_32Ch@rs_H3r3!
POSTGRES_MAX_CONNECTIONS=200
POSTGRES_SHARED_BUFFERS=2GB
POSTGRES_EFFECTIVE_CACHE_SIZE=6GB
POSTGRES_WORK_MEM=50MB

# Odoo (8 core CPU)
ODOO_ADMIN_PASSWORD=@dm1n_P@ssw0rd_V3ry_S3cur3_H3r3!
ODOO_WORKERS=17  # (8*2)+1
ODOO_MAX_CRON_THREADS=2
ODOO_LOG_LEVEL=info

# KKT Adapter
KKT_OFD_API_URL=https://ofd.taxcom.ru/api/v1
KKT_OFD_API_TOKEN=prod_ofd_token_secure_32_chars_here
KKT_BUFFER_MAX_SIZE=2000
KKT_CIRCUIT_BREAKER_THRESHOLD=5

# SSL
SSL_ENABLED=true
SSL_CERT_PATH=/etc/letsencrypt/live/erp.youroptics.ru/fullchain.pem
SSL_KEY_PATH=/etc/letsencrypt/live/erp.youroptics.ru/privkey.pem

# Backup
BACKUP_ENABLED=true
BACKUP_PATH=/opt/opticserp/backups
BACKUP_RETENTION_DAYS=90
BACKUP_OFFSITE_ENABLED=true
BACKUP_OFFSITE_PATH=/mnt/nas/opticserp-backups

# Monitoring
PROMETHEUS_ENABLED=true
GRAFANA_ADMIN_PASSWORD=Gr@f@n@_S3cur3_P@ssw0rd_H3r3!
FLOWER_BASIC_AUTH=admin:Fl0w3r_P@ssw0rd_H3r3!

# Email
ODOO_EMAIL_FROM=noreply@youroptics.ru
ODOO_SMTP_SERVER=smtp.gmail.com
ODOO_SMTP_PORT=587
ODOO_SMTP_USER=noreply@youroptics.ru
ODOO_SMTP_PASSWORD=gmail_app_password_16_chars
ODOO_SMTP_STARTTLS=true
```

---

## 🛡️ Security Best Practices

### Password Requirements

**All production passwords MUST:**
- ≥16 characters
- Mixed case (upper + lower)
- Numbers + symbols
- NO dictionary words
- Unique per service

**Generate strong password:**
```bash
# Linux/macOS
openssl rand -base64 32

# Example output:
# 7xK9mP2qL5nR8tY3wV6zB4cF1dG0hJ8kM1nP4rS7uV9wX2yZ5aC6dF

# Use in .env
POSTGRES_PASSWORD=7xK9mP2qL5nR8tY3wV6zB4cF1dG0hJ8k
```

### Secrets Management

**DO NOT commit secrets to Git:**
```bash
# .gitignore (already configured)
.env
.env.local
.env.production
*.bak
```

**Use environment-specific files:**
```bash
.env.development  # Development config (can commit with dummy data)
.env.production   # Production config (NEVER commit)
.env.example      # Template (commit this)
```

### Access Control

**Restrict .env file permissions:**
```bash
chmod 600 .env
chown root:root .env  # Or opticserp:opticserp
```

**Verify permissions:**
```bash
ls -l .env

# Expected:
# -rw------- 1 root root 4096 Nov 30 12:00 .env
```

---

**Need help?** See:
- [Configuration Guide](03_configuration.md) - Detailed configuration examples
- [Installation Steps](02_installation_steps.md) - Initial setup
- [Troubleshooting](05_troubleshooting.md) - Configuration issues

---

**Last Updated:** 2025-11-30
