# Troubleshooting Guide

**Last Updated:** 2025-11-30

---

## 🔍 Common Issues

### 1. Port Already in Use

**Symptoms:**
```
Error: Bind for 0.0.0.0:8069 failed: port is already allocated
```

**Solution:**
```bash
# Method 1: Use kill_port.py script
python3 scripts/kill_port.py 8069

# Method 2: Find and kill process manually
sudo netstat -tulpn | grep 8069
sudo kill -9 <PID>

# Method 3: Change port in .env
nano .env
# Change ODOO_PORT=8069 to ODOO_PORT=8070
docker-compose up -d
```

---

### 2. Database Connection Failed

**Symptoms:**
```
psycopg2.OperationalError: could not connect to server
FATAL: password authentication failed for user "odoo"
```

**Solutions:**

**A. PostgreSQL not running:**
```bash
# Check status
docker-compose ps postgres

# Start PostgreSQL
docker-compose up -d postgres

# Check logs
docker-compose logs postgres --tail=50
```

**B. Wrong credentials:**
```bash
# Verify .env file
grep POSTGRES .env

# Match values in docker-compose.yml
cat docker-compose.yml | grep -A5 postgres
```

**C. Corrupt database:**
```bash
# Restore from backup
./scripts/restore.sh YYYYMMDD_HHMMSS

# Or recreate database
docker-compose exec postgres psql -U postgres -c "DROP DATABASE opticserp;"
docker-compose exec postgres psql -U postgres -c "CREATE DATABASE opticserp OWNER odoo;"
```

---

### 3. Module Installation Error

**Symptoms:**
```
ERROR: Module optics_core: installation failed
SyntaxError: invalid syntax
```

**Solutions:**

**A. Python syntax error:**
```bash
# Check Python files
docker-compose run --rm odoo python3 -m py_compile /mnt/extra-addons/optics_core/models/*.py

# Fix syntax errors in code
nano addons/optics_core/models/[file].py
```

**B. Missing dependencies:**
```bash
# Check __manifest__.py
cat addons/optics_core/__manifest__.py | grep depends

# Install missing modules first
docker-compose run --rm odoo odoo -d opticserp -i base,sale,point_of_sale --stop-after-init
```

**C. Clear Odoo cache:**
```bash
docker-compose restart odoo
```

---

### 4. KKT Adapter Unavailable

**Symptoms:**
```
POS: Cannot connect to KKT Adapter
Connection refused: http://kkt_adapter:8000
```

**Solutions:**

**A. Service not running:**
```bash
# Check status
docker-compose ps kkt_adapter

# Start service
docker-compose up -d kkt_adapter

# Check logs
docker-compose logs kkt_adapter --tail=50
```

**B. Wrong URL configuration:**
```bash
# Verify internal Docker network name
docker-compose exec odoo ping kkt_adapter

# Should resolve to 172.17.0.x
# If not, check docker-compose.yml service name
```

**C. Port mismatch:**
```bash
# Verify port in .env
grep KKT_ADAPTER_PORT .env

# Should match docker-compose.yml expose
cat docker-compose.yml | grep -A3 kkt_adapter | grep ports
```

---

### 5. Buffer Full / Sync Failed

**Symptoms:**
```
KKT: Buffer at 95%, receipts pending sync
OFD sync failed: Connection timeout
```

**Solutions:**

**A. Manual sync:**
```bash
# Trigger manual sync
curl -X POST http://localhost:8000/v1/kkt/buffer/sync

# Check buffer status
curl http://localhost:8000/v1/kkt/buffer/status
```

**B. Check OFD connectivity:**
```bash
# Test OFD API
docker-compose exec kkt_adapter curl -v $KKT_OFD_API_URL/health

# Check network
docker-compose exec kkt_adapter ping -c 3 ofd-provider.ru
```

**C. Increase buffer size:**
```bash
# Edit .env
nano .env
# KKT_BUFFER_MAX_SIZE=2000  (increase from 1000)

# Restart adapter
docker-compose restart kkt_adapter
```

**D. Emergency: Clear old data:**
```bash
# DANGER: This deletes synced receipts from buffer
docker-compose exec kkt_adapter sqlite3 /app/data/buffer.db \
  "DELETE FROM receipts WHERE status='synced' AND created_at < datetime('now', '-7 days');"
```

---

### 6. Slow Performance

**Symptoms:**
- UI loads slowly (>5 seconds)
- POS operations lag
- High CPU/RAM usage

**Solutions:**

**A. Check resources:**
```bash
# Host resources
htop

# Docker stats
docker stats

# Check disk I/O
iostat -x 1
```

**B. Optimize PostgreSQL:**
```bash
# Edit .env - Add tuning parameters
POSTGRES_SHARED_BUFFERS=2GB
POSTGRES_EFFECTIVE_CACHE_SIZE=6GB
POSTGRES_MAX_CONNECTIONS=100

# Restart
docker-compose restart postgres
```

**C. Clear logs:**
```bash
# Truncate logs
docker-compose exec odoo sh -c "echo > /var/log/odoo/odoo.log"

# Or use Docker log rotation (docker-compose.yml)
```

**D. Vacuum database:**
```bash
docker-compose exec postgres psql -U odoo -d opticserp -c "VACUUM ANALYZE;"
```

---

### 7. Disk Space Full

**Symptoms:**
```
ERROR: No space left on device
Docker build failed: disk quota exceeded
```

**Solutions:**

**A. Clean Docker:**
```bash
# Remove unused images
docker system prune -a

# Remove volumes (DANGER: deletes data!)
# docker volume prune
```

**B. Clean old backups:**
```bash
# Auto-cleanup runs in backup.sh, or manual:
find /opt/opticserp/backups -name "*.gz" -mtime +90 -delete
```

**C. Clean logs:**
```bash
# Truncate Docker logs
truncate -s 0 $(docker inspect --format='{{.LogPath}}' opticserp_odoo)
```

---

### 8. Russian Translation Missing

**Symptoms:**
- UI still in English after loading ru_RU
- Some fields not translated

**Solutions:**

**A. Reload translations:**
```bash
docker-compose exec odoo odoo -d opticserp \
  --load-language=ru_RU \
  --i18n-overwrite \
  --stop-after-init
```

**B. Configure user language:**
```bash
# Via web UI:
# Settings → Users → Admin → Preferences → Language → Russian
```

**C. Clear translation cache:**
```bash
docker-compose restart odoo
```

---

## 📋 Log Locations

### Docker Logs
```bash
# Odoo
docker-compose logs odoo -f

# KKT Adapter
docker-compose logs kkt_adapter -f

# PostgreSQL
docker-compose logs postgres -f

# All services (last 100 lines)
docker-compose logs --tail=100 -f
```

### Inside Containers
```bash
# Odoo logs
docker-compose exec odoo cat /var/log/odoo/odoo.log

# KKT Adapter logs
docker-compose exec kkt_adapter cat /app/logs/kkt_adapter.log

# PostgreSQL logs
docker-compose exec postgres cat /var/lib/postgresql/data/log/postgresql.log
```

---

## 🔧 Debug Mode

### Enable Odoo Debug Mode

**Method 1: URL Parameter**
```
http://localhost:8069/web?debug=1
```

**Method 2: Developer Mode**
1. Login to Odoo
2. Settings → General Settings
3. Developer Tools → Activate Developer Mode

**Method 3: Environment Variable**
```bash
# Edit .env
ODOO_DEBUG_MODE=1

# Restart
docker-compose restart odoo
```

### Enable KKT Adapter Debug

```bash
# Edit .env
KKT_DEBUG=1

# Restart
docker-compose restart kkt_adapter

# View debug logs
docker-compose logs kkt_adapter -f
```

---

## 🆘 Emergency Procedures

### Complete System Reset

**DANGER: This deletes ALL data!**

```bash
# Stop all services
docker-compose down

# Remove volumes (deletes database!)
docker-compose down -v

# Remove all containers and images
docker system prune -a

# Reinstall from scratch
docker-compose build --no-cache
docker-compose up -d
./scripts/initialize_fresh.sh  # If you have one
```

### Restore from Backup

```bash
# List available backups
ls -lh /opt/opticserp/backups/db_*.sql.gz

# Restore specific backup
./scripts/restore.sh YYYYMMDD_HHMMSS
```

---

## 📞 Getting Help

### Check Documentation
1. [Installation Guide](02_installation_steps.md)
2. [Configuration Guide](03_configuration.md)
3. [System Requirements](01_system_requirements.md)

### Community Support
- GitHub Issues: https://github.com/bozzyk44/OpticsERP/issues
- Search existing issues first
- Provide logs and error messages

### Professional Support
Contact: support@opticserp.example.com

---

**Still stuck?** Open a GitHub issue with:
- Full error message
- Relevant logs (`docker-compose logs`)
- Steps to reproduce
- System info (`docker version`, `docker-compose version`)
