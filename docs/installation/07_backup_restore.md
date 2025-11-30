# Backup & Restore Guide

**Last Updated:** 2025-11-30

---

## 📋 Overview

This guide covers backup and disaster recovery procedures for OpticsERP.

**Topics covered:**
- Automated backup configuration
- Manual backup procedures
- Restore from backup
- Disaster recovery scenarios
- Backup testing and validation
- Off-site backup strategies

---

## 🎯 Backup Strategy

### What Gets Backed Up

**Critical data (daily backups):**
- PostgreSQL database (`opticserp`)
- Odoo filestore (attachments, images)
- KKT Adapter SQLite buffer
- Configuration files (`.env`, `docker-compose.yml`)

**Optional (weekly backups):**
- Docker volumes
- Application logs
- Grafana dashboards

**NOT backed up:**
- Docker images (can be rebuilt)
- System packages (can be reinstalled)
- Temporary files

### Backup Retention Policy

| Backup Type | Frequency | Retention | Storage |
|-------------|-----------|-----------|---------|
| **Full** | Daily 02:00 | 90 days | Local + Off-site |
| **Incremental** | Every 6h | 7 days | Local only |
| **Weekly** | Sunday 03:00 | 1 year | Off-site only |
| **Pre-upgrade** | Before each upgrade | 30 days | Local only |

**Estimated storage:**
- Fresh installation: ~500 MB/backup
- Production (1 year): ~5-10 GB/backup
- Total (90 days retention): ~500 GB

---

## 🔧 Automated Backup Setup

### Using backup.sh Script

**Location:** `scripts/backup.sh`

**What it does:**
1. Creates PostgreSQL dump (gzip compressed)
2. Archives Odoo filestore
3. Copies KKT Adapter SQLite buffer
4. Backs up configuration files
5. Generates backup manifest
6. Auto-cleanup (90-day retention)

### Configure Automated Daily Backups

**Option 1: Using cron (Recommended)**

```bash
# Edit crontab
crontab -e

# Add daily backup at 02:00 AM
0 2 * * * cd /path/to/OpticsERP && bash scripts/backup.sh >> /var/log/opticserp-backup.log 2>&1

# Add weekly cleanup at 03:00 AM Sunday
0 3 * * 0 find /opt/opticserp/backups -name "*.gz" -mtime +90 -delete
```

**Option 2: Using systemd timer**

Create service file:
```bash
sudo nano /etc/systemd/system/opticserp-backup.service
```

```ini
[Unit]
Description=OpticsERP Backup Service
After=docker.service

[Service]
Type=oneshot
User=opticserp
WorkingDirectory=/opt/opticserp/OpticsERP
ExecStart=/bin/bash scripts/backup.sh
StandardOutput=append:/var/log/opticserp-backup.log
StandardError=append:/var/log/opticserp-backup.log
```

Create timer file:
```bash
sudo nano /etc/systemd/system/opticserp-backup.timer
```

```ini
[Unit]
Description=OpticsERP Backup Timer
Requires=opticserp-backup.service

[Timer]
OnCalendar=daily
OnCalendar=02:00
Persistent=true

[Install]
WantedBy=timers.target
```

Enable timer:
```bash
sudo systemctl daemon-reload
sudo systemctl enable opticserp-backup.timer
sudo systemctl start opticserp-backup.timer

# Check timer status
sudo systemctl status opticserp-backup.timer
```

### Configure Backup Directory

**Edit `.env` file:**
```bash
# Backup configuration
BACKUP_RETENTION_DAYS=90
BACKUP_PATH=/opt/opticserp/backups
BACKUP_COMPRESS=true
BACKUP_OFFSITE_ENABLED=false
# BACKUP_OFFSITE_PATH=/mnt/nas/opticserp-backups  # NFS/CIFS mount
```

**Create backup directory:**
```bash
sudo mkdir -p /opt/opticserp/backups
sudo chown -R $USER:$USER /opt/opticserp/backups
sudo chmod 750 /opt/opticserp/backups
```

**Verify permissions:**
```bash
ls -ld /opt/opticserp/backups

# Expected output:
# drwxr-x--- 2 opticserp opticserp 4096 Nov 30 12:00 /opt/opticserp/backups
```

---

## 💾 Manual Backup Procedures

### Full System Backup

**Using automated script:**
```bash
# From OpticsERP directory
bash scripts/backup.sh

# Expected output:
==========================================
OpticsERP Backup Script
==========================================
Backup ID: 20251130_140000

[1/6] Creating backup directory...
✅ Created: /opt/opticserp/backups/20251130_140000

[2/6] Backing up PostgreSQL database...
✅ Database backup: db_20251130_140000.sql.gz (1.2 GB)

[3/6] Backing up Odoo filestore...
✅ Filestore backup: filestore_20251130_140000.tar.gz (450 MB)

[4/6] Backing up KKT Adapter buffer...
✅ Buffer backup: buffer_20251130_140000.db (12 MB)

[5/6] Backing up configuration...
✅ Config backup: env_20251130_140000.bak

[6/6] Creating backup manifest...
✅ Manifest: manifest_20251130_140000.txt

==========================================
Backup Complete!
==========================================
Backup ID: 20251130_140000
Location: /opt/opticserp/backups
Total size: 1.66 GB
Duration: 3m 24s

Files created:
  - db_20251130_140000.sql.gz
  - filestore_20251130_140000.tar.gz
  - buffer_20251130_140000.db
  - env_20251130_140000.bak
  - manifest_20251130_140000.txt
```

### Database-Only Backup (Quick)

```bash
# Manual PostgreSQL dump
docker-compose exec -T postgres pg_dump -U odoo opticserp | gzip > backup_db_$(date +%Y%m%d_%H%M%S).sql.gz

# Expected: ~1-5 GB compressed file
```

### Filestore-Only Backup

```bash
# Archive Odoo filestore
docker-compose exec -T odoo tar czf - /var/lib/odoo/filestore/opticserp > backup_filestore_$(date +%Y%m%d_%H%M%S).tar.gz

# Expected: ~100-500 MB file
```

### KKT Buffer Backup

```bash
# Copy SQLite database
docker-compose exec -T kkt_adapter cat /app/data/buffer.db > backup_buffer_$(date +%Y%m%d_%H%M%S).db

# Important: Also checkpoint WAL first
docker-compose exec kkt_adapter sqlite3 /app/data/buffer.db "PRAGMA wal_checkpoint(TRUNCATE);"
```

### Configuration Backup

```bash
# Backup .env and docker-compose.yml
cp .env .env.backup_$(date +%Y%m%d_%H%M%S)
cp docker-compose.yml docker-compose.yml.backup_$(date +%Y%m%d_%H%M%S)
```

---

## 🔄 Restore Procedures

### Full System Restore

**Using automated restore script:**

```bash
# List available backups
ls -lh /opt/opticserp/backups/db_*.sql.gz

# Output:
-rw-r----- 1 opticserp opticserp 1.2G Nov 30 02:00 db_20251130_020000.sql.gz
-rw-r----- 1 opticserp opticserp 1.1G Nov 29 02:00 db_20251129_020000.sql.gz
-rw-r----- 1 opticserp opticserp 1.0G Nov 28 02:00 db_20251128_020000.sql.gz

# Restore from backup (DANGER: overwrites current data!)
bash scripts/restore.sh 20251130_020000
```

**Restore workflow:**
1. User confirmation prompt
2. Create pre-restore safety backup
3. Stop services
4. Drop and recreate database
5. Restore database from backup
6. Restore filestore
7. Restore KKT buffer
8. Optionally restore configuration
9. Start services
10. Verify restore

**Expected output:**
```
==========================================
  OpticsERP Restore Script
==========================================

[INFO] Checking backup files for: 20251130_020000
[INFO] ✅ Database backup found
[INFO] ✅ Filestore backup found
[INFO] ✅ KKT buffer backup found
[INFO] ✅ .env backup found

==========================================
  ⚠️  WARNING: DESTRUCTIVE OPERATION
==========================================

This will restore from backup: 20251130_020000

The following will be OVERWRITTEN:
  - PostgreSQL database (opticserp)
  - Odoo filestore (if backup exists)
  - KKT Adapter buffer (if backup exists)

Current data will be LOST!

Type 'yes' to continue, anything else to cancel: yes

[WARN] User confirmed restore operation
[INFO] Creating pre-restore backup (safety measure)...
[INFO] ✅ Pre-restore backup saved: db_20251130_143000_pre_restore.sql.gz
[INFO] Stopping services...
[INFO] ✅ Services stopped
[INFO] Restoring PostgreSQL database...
[INFO] ✅ Database restored
[INFO] Restoring Odoo filestore...
[INFO] ✅ Filestore restored
[INFO] Restoring KKT Adapter SQLite buffer...
[INFO] ✅ KKT buffer restored
[INFO] Starting services...
[INFO] ✅ Services started
[INFO] Verifying restore...
[INFO] ✅ Odoo database accessible
[INFO] ✅ Services running
[INFO] ✅ Restore verification passed

==========================================
  Restore Complete!
==========================================

Restored from backup: 20251130_020000
Location: /opt/opticserp/backups

Restored components:
  ✅ PostgreSQL database
  ✅ Odoo filestore
  ✅ KKT Adapter buffer

Next steps:
1. Verify data integrity
2. Test critical functionality
3. Check logs for errors

[INFO] ✅ Restore completed successfully!
```

### Database-Only Restore

```bash
# Stop Odoo and Celery (PostgreSQL continues running)
docker-compose stop odoo celery

# Drop database
docker-compose exec -T postgres psql -U odoo -d postgres -c "DROP DATABASE IF EXISTS opticserp;"

# Create database
docker-compose exec -T postgres psql -U odoo -d postgres -c "CREATE DATABASE opticserp OWNER odoo;"

# Restore from backup
gunzip < /opt/opticserp/backups/db_20251130_020000.sql.gz | \
  docker-compose exec -T postgres psql -U odoo -d opticserp

# Start services
docker-compose start odoo celery
```

### Filestore-Only Restore

```bash
# Stop Odoo
docker-compose stop odoo

# Remove old filestore
docker-compose exec odoo rm -rf /var/lib/odoo/filestore/opticserp

# Restore filestore
docker-compose exec -T odoo tar xzf - -C / < /opt/opticserp/backups/filestore_20251130_020000.tar.gz

# Start Odoo
docker-compose start odoo
```

### KKT Buffer Restore

```bash
# Stop KKT Adapter
docker-compose stop kkt_adapter

# Restore buffer database
cat /opt/opticserp/backups/buffer_20251130_020000.db | \
  docker-compose exec -T kkt_adapter sh -c "cat > /app/data/buffer.db"

# Set permissions
docker-compose exec kkt_adapter chmod 644 /app/data/buffer.db

# Start KKT Adapter
docker-compose start kkt_adapter
```

---

## 🆘 Disaster Recovery Scenarios

### Scenario 1: Database Corruption

**Symptoms:**
- Odoo won't start
- Error: "database is corrupted"
- PostgreSQL errors in logs

**Recovery:**
```bash
# 1. Stop services
docker-compose stop

# 2. Restore from latest backup
bash scripts/restore.sh $(ls -t /opt/opticserp/backups/db_*.sql.gz | head -1 | sed 's/.*db_\\(.*\\)\\.sql\\.gz/\\1/')

# 3. Verify
docker-compose logs odoo --tail=50
```

**RTO:** ≤30 minutes
**RPO:** ≤24 hours (last daily backup)

### Scenario 2: Filestore Deleted

**Symptoms:**
- Attachments missing
- Images not loading
- "File not found" errors

**Recovery:**
```bash
# Restore filestore only (no database downtime)
docker-compose stop odoo
docker-compose exec -T odoo tar xzf - -C / < /opt/opticserp/backups/filestore_YYYYMMDD_HHMMSS.tar.gz
docker-compose start odoo
```

**RTO:** ≤10 minutes
**RPO:** ≤24 hours

### Scenario 3: Complete Server Failure

**Symptoms:**
- Hardware failure
- Ransomware attack
- Total data loss

**Recovery (requires off-site backups):**

1. **Provision new server:**
   ```bash
   # Install Ubuntu 22.04 LTS
   # Run preparation script
   wget https://raw.githubusercontent.com/bozzyk44/OpticsERP/main/scripts/prep_server.sh
   bash prep_server.sh
   ```

2. **Clone repository:**
   ```bash
   git clone https://github.com/bozzyk44/OpticsERP.git
   cd OpticsERP
   ```

3. **Copy backups from off-site:**
   ```bash
   # Mount NAS or download from cloud
   rsync -avz user@backup-server:/backups/ /opt/opticserp/backups/
   ```

4. **Restore configuration:**
   ```bash
   cp /opt/opticserp/backups/env_YYYYMMDD_HHMMSS.bak .env
   ```

5. **Deploy services:**
   ```bash
   docker-compose build --no-cache
   docker-compose up -d postgres redis
   sleep 10
   ```

6. **Restore data:**
   ```bash
   bash scripts/restore.sh YYYYMMDD_HHMMSS
   ```

7. **Verify:**
   ```bash
   docker-compose ps
   curl -s http://localhost:8069 | grep "Odoo"
   ```

**RTO:** ≤2 hours
**RPO:** ≤24 hours (daily off-site backup)

### Scenario 4: Accidental Data Deletion

**Symptoms:**
- User accidentally deleted records
- Need to recover specific data

**Recovery (point-in-time):**
```bash
# 1. Find backup before deletion
ls -lt /opt/opticserp/backups/db_*.sql.gz

# 2. Restore to temporary database
gunzip < /opt/opticserp/backups/db_20251130_020000.sql.gz | \
  docker-compose exec -T postgres psql -U odoo -d postgres -c "CREATE DATABASE opticserp_temp OWNER odoo;" && \
  docker-compose exec -T postgres psql -U odoo -d opticserp_temp

# 3. Export specific records (e.g., deleted prescriptions)
docker-compose exec -T postgres psql -U odoo -d opticserp_temp -c \
  "COPY (SELECT * FROM optics_prescription WHERE id IN (123, 456)) TO STDOUT WITH CSV HEADER" > recovered_prescriptions.csv

# 4. Import to production database
# ... (manual data import via Odoo UI or SQL)

# 5. Drop temporary database
docker-compose exec -T postgres psql -U odoo -d postgres -c "DROP DATABASE opticserp_temp;"
```

---

## ✅ Backup Testing & Validation

### Monthly Backup Drill

**Schedule:** First Sunday of each month

**Procedure:**
1. Select random backup from last 30 days
2. Restore to test environment
3. Verify data integrity
4. Test critical functionality
5. Document results

**Test checklist:**
- [ ] Backup files exist and not corrupted
- [ ] Restore completes without errors
- [ ] Database accessible
- [ ] Filestore attachments load
- [ ] KKT buffer intact
- [ ] Odoo login works
- [ ] Sample prescription loads
- [ ] POS session opens

### Automated Backup Validation

**Add to backup.sh script (bottom):**
```bash
# Validate backup integrity
echo "[INFO] Validating backup..."

# Test database backup
if gunzip -t "$BACKUP_DIR/db_${DATE}.sql.gz"; then
    echo "✅ Database backup valid"
else
    echo "❌ Database backup CORRUPTED!"
    exit 1
fi

# Test filestore archive
if tar tzf "$BACKUP_DIR/filestore_${DATE}.tar.gz" > /dev/null; then
    echo "✅ Filestore backup valid"
else
    echo "❌ Filestore backup CORRUPTED!"
    exit 1
fi
```

### Backup Monitoring

**Prometheus metrics:**
```yaml
# /etc/prometheus/prometheus.yml
- job_name: 'backup-monitor'
  static_configs:
    - targets: ['localhost:9100']
  metric_relabel_configs:
    - source_labels: [__name__]
      regex: 'node_filesystem_avail_bytes'
      target_label: backup_disk
```

**Grafana alert:**
```yaml
alert: BackupFailed
expr: time() - backup_last_success_timestamp > 86400  # 24h
for: 15m
labels:
  severity: critical
annotations:
  summary: "Backup failed for 24+ hours"
```

---

## 🌐 Off-Site Backup Strategies

### Option 1: NFS/CIFS Mount

**Mount network share:**
```bash
# Install CIFS utils
sudo apt install cifs-utils -y

# Create mount point
sudo mkdir -p /mnt/nas/opticserp-backups

# Add to /etc/fstab
sudo nano /etc/fstab

# Add line:
//nas-server/backups /mnt/nas/opticserp-backups cifs credentials=/root/.smbcredentials,uid=1000,gid=1000 0 0

# Mount
sudo mount -a
```

**Update .env:**
```bash
BACKUP_OFFSITE_ENABLED=true
BACKUP_OFFSITE_PATH=/mnt/nas/opticserp-backups
```

**Automated sync:**
```bash
# Add to backup.sh (after local backup completes)
rsync -avz "$BACKUP_DIR/" "$BACKUP_OFFSITE_PATH/"
```

### Option 2: Cloud Storage (S3/Minio)

**Install AWS CLI:**
```bash
sudo apt install awscli -y
aws configure  # Enter credentials
```

**Sync to S3:**
```bash
# Add to backup.sh
aws s3 sync "$BACKUP_DIR/" s3://opticserp-backups/ --exclude "*" --include "db_*.sql.gz" --include "filestore_*.tar.gz"
```

### Option 3: Rsync to Remote Server

**Setup SSH key:**
```bash
ssh-keygen -t ed25519 -C "opticserp-backup"
ssh-copy-id backup-user@backup-server
```

**Automated sync:**
```bash
# Add to cron (after daily backup)
5 2 * * * rsync -avz --delete /opt/opticserp/backups/ backup-user@backup-server:/backups/opticserp/
```

---

## 📊 Backup Checklist

### Weekly Backup Verification
- [ ] Check backup logs for errors: `tail -100 /var/log/opticserp-backup.log`
- [ ] Verify backup files exist: `ls -lh /opt/opticserp/backups/db_$(date +%Y%m%d)*.sql.gz`
- [ ] Check backup sizes (not 0 bytes)
- [ ] Verify off-site sync (if configured)
- [ ] Check disk space: `df -h /opt/opticserp/backups` (≥20% free)

### Monthly Backup Drill
- [ ] Select random backup
- [ ] Restore to test environment
- [ ] Verify data integrity
- [ ] Test Odoo login
- [ ] Document drill results

### Quarterly DR Test
- [ ] Simulate complete server failure
- [ ] Restore from off-site backup
- [ ] Measure RTO (should be ≤2h)
- [ ] Measure RPO (should be ≤24h)
- [ ] Update DR procedures if needed

---

## 🔧 Troubleshooting Backups

### Issue: Backup script fails

**Check logs:**
```bash
tail -100 /var/log/opticserp-backup.log
```

**Common errors:**
- **Disk full:** `df -h` → clean old backups or increase disk
- **Permission denied:** `ls -l /opt/opticserp/backups` → fix ownership
- **Docker not running:** `docker-compose ps` → start services

### Issue: Restore fails with "permission denied"

**Fix permissions:**
```bash
sudo chown -R $USER:$USER /opt/opticserp/backups
chmod 640 /opt/opticserp/backups/*.sql.gz
```

### Issue: Backup file corrupted

**Test file integrity:**
```bash
# Test gzip file
gunzip -t /opt/opticserp/backups/db_20251130_020000.sql.gz

# Test tar file
tar tzf /opt/opticserp/backups/filestore_20251130_020000.tar.gz > /dev/null
```

**If corrupted:**
- Use previous backup
- Check disk health: `sudo smartctl -a /dev/sda`
- File system check: `sudo fsck /dev/sda1` (unmount first!)

---

**Backup strategy configured?** Return to [Installation Guide →](00_README.md)

**Need help?** See [Troubleshooting Guide](05_troubleshooting.md)
