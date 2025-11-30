# Verification & Testing Guide

**Last Updated:** 2025-11-30

---

## 📋 Overview

This guide covers verification procedures after OpticsERP installation to ensure all components are working correctly.

**Topics covered:**
- Service health checks
- Smoke tests (basic functionality)
- Functional testing checklist
- Performance verification
- Integration testing
- Security verification

---

## ✅ Installation Verification Checklist

After completing [Installation Steps](02_installation_steps.md), verify each component:

- [ ] All Docker containers running
- [ ] PostgreSQL accessible
- [ ] Odoo web interface accessible
- [ ] Admin login works
- [ ] Russian locale active
- [ ] Custom modules installed
- [ ] KKT Adapter API accessible
- [ ] Redis connection OK
- [ ] Celery workers running
- [ ] No errors in logs

**Estimated time:** 15-30 minutes

---

## 🔍 Service Health Checks

### Docker Containers Status

```bash
# Check all containers are running
docker-compose ps

# Expected output (all "Up"):
NAME                   STATUS              PORTS
opticserp_odoo         Up 5 minutes        0.0.0.0:8069->8069/tcp
opticserp_postgres     Up 5 minutes        0.0.0.0:5432->5432/tcp
opticserp_redis        Up 5 minutes        0.0.0.0:6379->6379/tcp
opticserp_kkt_adapter  Up 5 minutes        0.0.0.0:8000->8000/tcp
opticserp_celery       Up 5 minutes
```

**If any service shows "Exit" or "Restarting":**
```bash
# Check logs for that service
docker-compose logs [service-name] --tail=50

# Example
docker-compose logs odoo --tail=50
```

### PostgreSQL Health

```bash
# Connect to PostgreSQL
docker-compose exec postgres psql -U odoo -d opticserp

# Check database exists
\l opticserp

# Check tables exist (should show 300+ tables)
\dt

# Check Odoo base tables
SELECT COUNT(*) FROM res_users;  -- Should return ≥2 (admin + default)
SELECT COUNT(*) FROM ir_module_module WHERE state='installed';  -- Should return ≥30

# Exit psql
\q
```

### Redis Connection

```bash
# Test Redis connection
docker-compose exec redis redis-cli ping

# Expected output:
PONG

# Check Celery queue
docker-compose exec redis redis-cli LLEN celery

# Expected: 0 or small number
```

### Odoo Web Interface

**Browser test:**
```
URL: http://your-server-ip:8069
```

**Expected:**
- ✅ Odoo login page loads (≤5 seconds)
- ✅ No 502/503 errors
- ✅ HTTPS redirect works (production only)

**If page doesn't load:**
```bash
# Check Odoo logs
docker-compose logs odoo --tail=100

# Check port is listening
netstat -tulpn | grep 8069

# Restart Odoo
docker-compose restart odoo
```

### KKT Adapter API

**Check API documentation:**
```bash
# Via curl
curl -s http://localhost:8000/docs | grep "FastAPI"

# Or open in browser
http://your-server-ip:8000/docs
```

**Expected:**
- ✅ Swagger UI loads
- ✅ Shows endpoints: `/v1/kkt/receipt`, `/v1/kkt/buffer/status`, `/v1/health`

**Health check endpoint:**
```bash
curl -s http://localhost:8000/v1/health | jq

# Expected output:
{
  "status": "healthy",
  "database": "ok",
  "circuit_breaker": "closed",
  "buffer_fullness": 0.0
}
```

### Celery Workers

```bash
# Check Celery is running
docker-compose exec celery celery -A opticserp status

# Expected output:
celery@hostname: OK

# Check active tasks
docker-compose exec celery celery -A opticserp inspect active

# Expected: Empty dict {} or list of tasks
```

---

## 🧪 Smoke Tests (Basic Functionality)

### Test 1: Admin Login

**Steps:**
1. Open `http://your-server-ip:8069`
2. Login:
   - Email: `admin`
   - Password: `[your ODOO_ADMIN_PASSWORD from .env]`
3. Verify dashboard loads

**Expected:**
- ✅ Login successful
- ✅ Dashboard shows apps
- ✅ No error messages
- ✅ UI in Russian (if configured)

**If login fails:**
- Check `.env` file: `grep ODOO_ADMIN_PASSWORD .env`
- Reset admin password: See [Troubleshooting Guide](05_troubleshooting.md)

### Test 2: Module Installation Verification

**Steps:**
1. Login as admin
2. Go to **Settings → Apps** (Настройки → Приложения)
3. Remove "Apps" filter
4. Search for "optics"

**Expected installed modules:**
- ✅ **Optics Core** (`optics_core`)
- ✅ **Optics POS RU 54-FZ** (`optics_pos_ru54fz`)
- ✅ **Connector B** (`connector_b`)
- ✅ **RU Accounting Extras** (`ru_accounting_extras`)

**All 4 modules should show "Installed" status.**

**If modules missing:**
```bash
# Reinstall modules
docker-compose run --rm odoo odoo -d opticserp \
  -i optics_core,optics_pos_ru54fz,connector_b,ru_accounting_extras \
  --stop-after-init

# Restart Odoo
docker-compose restart odoo
```

### Test 3: Create Test Prescription

**Steps:**
1. Go to **Optics → Prescriptions → Create**
2. Fill in test data:
   - Patient Name: Тестов Тест Тестович
   - Issue Date: Today
   - OD Sphere: -2.50
   - OS Sphere: -3.00
3. Click **Save**

**Expected:**
- ✅ Prescription created successfully
- ✅ All fields in Russian (if locale configured)
- ✅ No validation errors
- ✅ Prescription appears in list view

**If fields still in English:**
- See [Troubleshooting Guide](05_troubleshooting.md) → "Russian Translation Missing"

### Test 4: KKT Adapter Receipt Test (Offline Mode)

**Test offline receipt creation:**

```bash
# Create test receipt via API
curl -X POST http://localhost:8000/v1/kkt/receipt \
  -H "Content-Type: application/json" \
  -d '{
    "pos_id": "test-pos-1",
    "order_id": "TEST-001",
    "items": [
      {
        "name": "Линзы CR-39",
        "quantity": 1,
        "price": 2500.00,
        "vat_rate": 20
      }
    ],
    "total": 2500.00,
    "payment_method": "cash"
  }'

# Expected response:
{
  "status": "buffered",
  "receipt_id": "...",
  "hlc_timestamp": {...},
  "fiscal_number": "..."
}
```

**Check buffer status:**
```bash
curl -s http://localhost:8000/v1/kkt/buffer/status | jq

# Expected:
{
  "buffer_fullness": 0.1,  # 0-100%
  "pending_receipts": 1,
  "dlq_size": 0,
  "circuit_breaker_state": "closed"
}
```

**Verify receipt in SQLite buffer:**
```bash
docker-compose exec kkt_adapter sqlite3 /app/data/buffer.db \
  "SELECT id, status, created_at FROM receipts ORDER BY created_at DESC LIMIT 1;"

# Expected output:
1|pending|2025-11-30 12:00:00
```

---

## 📊 Functional Testing Checklist

### Optics Core Module

- [ ] **Prescriptions:**
  - [ ] Create prescription with OD/OS values
  - [ ] Save and retrieve prescription
  - [ ] Print prescription report
  - [ ] Archive old prescription

- [ ] **Lenses:**
  - [ ] Create lens product (CR-39, Index 1.56, Anti-glare)
  - [ ] Set lens pricing
  - [ ] Link lens to prescription

- [ ] **Manufacturing Orders:**
  - [ ] Create MO from prescription
  - [ ] Assign to production
  - [ ] Mark as completed
  - [ ] Verify workflow (Draft → Confirmed → In Production → Ready → Delivered)

### POS Module (optics_pos_ru54fz)

- [ ] **POS Session:**
  - [ ] Open POS session
  - [ ] Create test sale (cash payment)
  - [ ] Close POS session
  - [ ] Generate X/Z reports

- [ ] **Fiscal Integration:**
  - [ ] Verify KKT Adapter connection (Settings → POS → Configuration)
  - [ ] Test fiscal receipt generation
  - [ ] Check receipt in buffer
  - [ ] Verify electronic receipt (email/SMS if configured)

### Connector B Module

- [ ] **Import Profile:**
  - [ ] Create import profile for test supplier
  - [ ] Map columns (SKU, Name, Price, Stock)
  - [ ] Save profile

- [ ] **Import Job:**
  - [ ] Upload test CSV (10 products)
  - [ ] Preview import
  - [ ] Execute import
  - [ ] Verify products created
  - [ ] Check import log (no errors)

### RU Accounting Extras Module

- [ ] **Cash Accounts:**
  - [ ] Create cash account for location
  - [ ] Record cash deposit
  - [ ] Record cash withdrawal
  - [ ] View cash balance

- [ ] **GP Report:**
  - [ ] Generate GP report for location
  - [ ] Verify sales/costs calculation
  - [ ] Export to Excel

---

## ⚡ Performance Verification

### Response Time Tests

**Odoo Web Interface:**
```bash
# Measure page load time
curl -o /dev/null -s -w "Time: %{time_total}s\n" http://localhost:8069/web/login

# Expected: ≤2 seconds (production) or ≤5 seconds (development)
```

**KKT Adapter API:**
```bash
# Measure receipt creation time
time curl -X POST http://localhost:8000/v1/kkt/receipt -H "Content-Type: application/json" -d @test_receipt.json

# Expected: ≤1 second (offline mode)
```

### Database Performance

```bash
# Check query performance
docker-compose exec postgres psql -U odoo -d opticserp -c \
  "SELECT query, calls, mean_exec_time FROM pg_stat_statements ORDER BY mean_exec_time DESC LIMIT 10;"

# Expected: P95 query time ≤50ms (empty database) or ≤200ms (production load)
```

### Load Test (Optional)

**Install Apache Bench:**
```bash
sudo apt install apache2-utils -y
```

**Test Odoo login page:**
```bash
ab -n 100 -c 10 http://localhost:8069/web/login

# Expected:
# - Requests per second: ≥10 (development) or ≥50 (production)
# - Failed requests: 0
```

**Test KKT Adapter:**
```bash
ab -n 100 -c 10 -p test_receipt.json -T application/json http://localhost:8000/v1/kkt/receipt

# Expected:
# - Requests per second: ≥50
# - Failed requests: 0
```

---

## 🔗 Integration Testing

### Test 1: POS → KKT Adapter → Buffer

**Scenario:** Offline sale with fiscal receipt

**Steps:**
1. Open POS session in Odoo
2. Add product to cart
3. Process payment (cash)
4. Generate fiscal receipt
5. Verify receipt buffered in KKT Adapter

**Verification:**
```bash
# Check buffer
curl -s http://localhost:8000/v1/kkt/buffer/status | jq '.pending_receipts'

# Expected: 1 (or more)
```

### Test 2: Buffer Sync (Online Mode)

**Prerequisites:** OFD API credentials configured in `.env`

**Steps:**
1. Create test receipt (see Test 4)
2. Trigger manual sync:
   ```bash
   curl -X POST http://localhost:8000/v1/kkt/buffer/sync
   ```
3. Check buffer status:
   ```bash
   curl -s http://localhost:8000/v1/kkt/buffer/status | jq
   ```

**Expected:**
- `pending_receipts` decreases
- `circuit_breaker_state`: "closed"
- No receipts in DLQ (`dlq_size: 0`)

**If sync fails:**
- Check OFD credentials: `grep KKT_OFD .env`
- Check network: `docker-compose exec kkt_adapter ping -c 3 ofd-provider.ru`
- Check logs: `docker-compose logs kkt_adapter --tail=50`

### Test 3: Import → Inventory Sync

**Scenario:** Import products and verify stock levels

**Steps:**
1. Create CSV file (`test_products.csv`):
   ```csv
   SKU,Name,Price,Stock
   LENS-001,CR-39 Single Vision,2500,100
   LENS-002,Polycarbonate Bifocal,3500,50
   ```
2. Import via Connector B:
   - Go to **Import/Export → Import Profiles**
   - Select profile
   - Upload `test_products.csv`
   - Preview and execute
3. Verify products:
   - Go to **Inventory → Products**
   - Search for "LENS-001"
   - Check stock quantity = 100

**Expected:**
- ✅ All products imported
- ✅ Stock levels correct
- ✅ Prices match CSV

---

## 🔒 Security Verification

### Password Security

**Check default passwords changed:**
```bash
# DANGER: These should NOT match defaults!
grep POSTGRES_PASSWORD .env
grep ODOO_ADMIN_PASSWORD .env

# Expected: Strong passwords (≥16 chars, mixed case, symbols)
```

**Password strength test:**
```bash
# Check password entropy
echo "YourPassword" | wc -c  # Should be ≥16
```

### Firewall Check (Production)

```bash
# Check UFW status
sudo ufw status

# Expected (production):
# 22/tcp (SSH)        ALLOW
# 443/tcp (HTTPS)     ALLOW
# 8000/tcp (KKT)      ALLOW from LAN only
# 8069/tcp (HTTP)     DENY (or ALLOW for dev)
```

### SSL/TLS Verification (Production)

```bash
# Check SSL certificate
openssl s_client -connect your-domain.com:443 -servername your-domain.com

# Expected:
# - Certificate chain valid
# - Issuer: Let's Encrypt or trusted CA
# - Not expired
```

---

## 📝 Log Verification

### No Critical Errors

**Odoo logs:**
```bash
docker-compose logs odoo --tail=100 | grep -i error

# Expected: 0 critical errors (warnings OK)
```

**KKT Adapter logs:**
```bash
docker-compose logs kkt_adapter --tail=100 | grep -i error

# Expected: 0 errors
```

**PostgreSQL logs:**
```bash
docker-compose logs postgres --tail=100 | grep -i fatal

# Expected: 0 fatal errors
```

### Log Rotation Active

```bash
# Check Docker log sizes
docker inspect --format='{{.LogPath}}' opticserp_odoo | xargs ls -lh

# Expected: ≤10 MB per container (if log rotation configured)
```

---

## ✅ Final Verification Summary

**Before going to production, ALL items must pass:**

### Critical Checks (MUST PASS)
- [ ] All Docker containers "Up" status
- [ ] PostgreSQL accessible, ≥2 users, ≥30 modules
- [ ] Odoo web login works (admin)
- [ ] All 4 custom modules installed
- [ ] KKT Adapter API `/v1/health` returns "healthy"
- [ ] Test prescription created successfully
- [ ] Test receipt buffered in SQLite
- [ ] No critical errors in logs

### Production Checks (Production Only)
- [ ] SSL/TLS certificate valid
- [ ] Firewall rules configured
- [ ] Default passwords changed (≥16 chars)
- [ ] Backup automation configured (cron)
- [ ] Monitoring active (Prometheus/Grafana)
- [ ] UPS connected and tested
- [ ] NTP sync active (timedatectl)
- [ ] Disk space ≥20% free

### Performance Checks (Recommended)
- [ ] Odoo page load ≤5s
- [ ] KKT receipt creation ≤1s
- [ ] Database P95 query time ≤200ms
- [ ] Load test: 100 requests, 0 failures

---

## 📊 Verification Report Template

**After completing all checks, generate report:**

```markdown
# OpticsERP Verification Report

**Date:** YYYY-MM-DD
**Environment:** Production / Development
**Version:** [git commit hash]

## Summary
- ✅ Critical checks: X/Y passed
- ✅ Production checks: X/Y passed
- ✅ Performance checks: X/Y passed

## Service Status
- Odoo: ✅ Running (uptime: Xh)
- PostgreSQL: ✅ Running
- Redis: ✅ Running
- KKT Adapter: ✅ Running
- Celery: ✅ Running

## Smoke Tests
- Admin login: ✅ PASS
- Module installation: ✅ PASS (4/4)
- Prescription creation: ✅ PASS
- Receipt buffering: ✅ PASS

## Performance
- Odoo load time: X.XXs
- KKT API response: X.XXs
- DB query P95: XXXms

## Issues Found
[List any failures or warnings]

## Recommendation
✅ APPROVED for production
❌ NOT READY (blockers: ...)

**Signed:** [Your Name]
```

---

## 🆘 Troubleshooting

**If any verification fails:**
1. Check [Troubleshooting Guide](05_troubleshooting.md)
2. Review logs: `docker-compose logs -f --tail=100`
3. Verify configuration: `python3 scripts/validate_config.py`
4. Restart services: `docker-compose restart`

**Common issues:**
- Service won't start → Check logs and `.env` file
- Login fails → Reset admin password (see troubleshooting)
- Modules missing → Reinstall modules
- KKT Adapter unreachable → Check port 8000, firewall rules

---

**Verification complete?** Proceed to [Configuration Guide →](03_configuration.md) for advanced settings

**Need help?** See [Troubleshooting Guide](05_troubleshooting.md)
