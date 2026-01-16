# Ansible Playbooks Index

**OpticsERP Production Deployment**
**Last Updated:** 2025-12-31

---

## 📋 Active Playbooks

### Core Deployment

#### `deploy-production.yml` ⭐ **MASTER DEPLOYMENT PLAYBOOK**
**Purpose:** Complete OpticsERP production deployment from scratch
**Status:** ✅ Production Ready
**Recommended:** Use this for new deployments

**Usage:**
```bash
ansible-playbook -i inventories/production/hosts.yml deploy-production.yml
```

**What it does (8 Phases):**
1. **Phase 1:** Server preparation (common, security, Docker)
2. **Phase 2:** Database & cache (PostgreSQL 15, Redis 7.2, disable system Redis)
3. **Phase 3:** Nginx reverse proxy (basic configuration)
4. **Phase 4:** Odoo application deployment (Docker Compose, DB init)
5. **Phase 5:** ⭐ **WebSocket configuration** (CRITICAL - prevents "Connection Lost")
6. **Phase 6:** Custom modules installation (optics_core, optics_pos_ru54fz, connector_b, ru_accounting_extras)
7. **Phase 7:** Mock services (optional, --tags mock)
8. **Phase 8:** Monitoring (optional, --tags monitoring)
9. **FINAL:** Verification and status display

**Includes:**
- ✅ Complete WebSocket setup (Nginx + Odoo)
- ✅ System Redis conflict prevention
- ✅ All custom modules
- ✅ Health checks and verification
- ✅ Detailed progress reporting

---

#### `site.yml`
**Purpose:** Update existing infrastructure or selective deployment
**Status:** ✅ Active
**Use When:** Updating already deployed servers

**Usage:**
```bash
# Full update
ansible-playbook -i inventories/production/hosts.yml site.yml

# Only WebSocket configuration
ansible-playbook -i inventories/production/hosts.yml site.yml --tags websocket

# Selective roles
ansible-playbook -i inventories/production/hosts.yml site.yml --tags nginx,docker
```

**What it does:**
- Runs all roles (common, security, docker, nginx, postgresql, redis, odoo)
- Applies WebSocket configuration
- Verifies deployment

---

#### `deploy-base.yml`
**Purpose:** Initial server setup and base configuration
**Status:** ⚠️ Deprecated - Use `deploy-production.yml` instead
**Usage:**
```bash
ansible-playbook -i inventories/production/hosts.yml deploy-base.yml
```
**What it does:**
- System packages installation
- User and directory setup
- Base security configuration

**Note:** This is now part of Phase 1 in `deploy-production.yml`

---

#### `deploy-postgresql.yml`
**Purpose:** Deploy and configure PostgreSQL 15
**Status:** ✅ Deployed
**Usage:**
```bash
ansible-playbook -i inventories/production/hosts.yml deploy-postgresql.yml
```
**What it does:**
- Install PostgreSQL 15
- Configure authentication
- Create odoo_production database
- Set up user permissions

---

#### `deploy-odoo.yml`
**Purpose:** Deploy Odoo 17 with Docker Compose
**Status:** ✅ Deployed
**Usage:**
```bash
ansible-playbook -i inventories/production/hosts.yml deploy-odoo.yml
```
**What it does:**
- Deploy docker-compose.yml
- Configure odoo.conf
- Start Odoo container
- Verify health

---

### WebSocket Configuration

#### `configure-odoo-websocket.yml` ⭐ **MASTER PLAYBOOK**
**Purpose:** Complete Odoo WebSocket configuration
**Status:** ✅ Production Ready
**Issue Resolved:** "Connection Lost" errors in Odoo web interface

**Usage:**
```bash
ansible-playbook -i inventories/production/hosts.yml configure-odoo-websocket.yml
```

**What it does:**
1. Adds WebSocket map directive to nginx.conf
2. Configures Nginx site with WebSocket locations
3. Tests and reloads Nginx
4. Adds websocket_url to odoo.conf
5. Restarts Odoo
6. Verifies complete configuration

**Documentation:** `WEBSOCKET_CONFIG_README.md`

**Configuration Applied:**
- Nginx: WebSocket proxy on /websocket → localhost:8072
- Odoo: websocket_url = ws://194.87.235.33/websocket
- Headers: Upgrade, Connection, Host, Origin
- Security: Port 8072 localhost-only

---

### Module Management

#### `install-modules-cli.yml`
**Purpose:** Install custom Odoo modules via CLI
**Status:** ✅ Working
**Usage:**
```bash
ansible-playbook -i inventories/production/hosts.yml install-modules-cli.yml
```
**What it does:**
- Install optics_core
- Install optics_pos_ru54fz
- Install connector_b
- Install ru_accounting_extras
- Verify installation

---

#### `check-modules.yml`
**Purpose:** Check installed module status
**Usage:**
```bash
ansible-playbook -i inventories/production/hosts.yml check-modules.yml
```
**What it does:**
- Query ir_module_module table
- Display module states
- Count modules by status

---

### Nginx Management

#### `deploy-nginx.yml`
**Purpose:** Deploy and configure Nginx reverse proxy
**Status:** ✅ Deployed (with WebSocket support)
**Usage:**
```bash
ansible-playbook -i inventories/production/hosts.yml deploy-nginx.yml
```

---

### Mock Services (Development/Testing)

#### `start-mock-services.yml`
**Purpose:** Start mock OFD and Odoo API services
**Status:** ✅ Working
**Usage:**
```bash
ansible-playbook -i inventories/production/hosts.yml start-mock-services.yml
```
**What it does:**
- Build mock OFD Docker image
- Build mock Odoo API Docker image
- Start services with docker-compose.mock.yml
- Health check verification

**Services:**
- Mock OFD: http://localhost:9000
- Mock Odoo API: http://localhost:8070

---

### System Management

#### `disable-system-redis.yml`
**Purpose:** Disable system Redis to prevent port conflicts
**Status:** ✅ Applied
**Usage:**
```bash
ansible-playbook -i inventories/production/hosts.yml disable-system-redis.yml
```
**What it does:**
- Stop redis-server service
- Disable and mask redis services
- Free port 6379 for Docker Redis

---

## 🗄️ Archived Playbooks

**Location:** `archived/`
**Documentation:** `archived/README.md`

These playbooks are **not for production use** - kept for historical reference only.

**Files:**
- `fix-nginx-websocket.yml` - Initial attempt (crashed Nginx)
- `restore-nginx-emergency.yml` - Emergency rollback
- `fix-nginx-websocket-v2.yml` - Second attempt (partial)
- `fix-websocket-origin-header.yml` - Added Origin header
- `fix-odoo-websocket-url.yml` - Added Odoo websocket_url
- `fix-websocket-port.yml` - Port 8072 configuration

**Use instead:** `configure-odoo-websocket.yml` (consolidated master)

---

### Test Data Management

#### `load-test-data.yml`
**Purpose:** Load test data into OpticsERP database
**Status:** ✅ Working
**Usage:**
```bash
ansible-playbook -i inventories/production/hosts.yml load-test-data.yml
```

**What it does:**
1. Display warning about test data loading
2. Request manual confirmation (yes/no)
3. Create automatic database backup
4. Verify optics_core module is installed
5. Copy SQL file to server
6. Load test data via PostgreSQL
7. Verify loaded data (users, customers, products, prescriptions, sales)
8. Display summary with test credentials
9. Cleanup temporary files

**Test Data Includes:**
- 4 test users (manager, 2 cashiers, optician)
- 5 customers
- 3 suppliers
- ~20 products (lenses, frames, sunglasses, accessories)
- 5 prescriptions
- 6 lens types
- 4 manufacturing orders
- 5 sales orders with line items

**Test Credentials:**
```
Manager:   manager@optics.ru   / manager123
Cashier 1: cashier1@optics.ru  / cashier123
Cashier 2: cashier2@optics.ru  / cashier123
Optician:  optician@optics.ru  / optician123
```

**Safety Features:**
- ⚠️ Interactive confirmation required
- 💾 Automatic backup before loading
- ✅ Module verification (optics_core must be installed)
- 🧹 Automatic cleanup of temporary files

**Important:**
- 🔒 **ONLY use on development/staging environments!**
- Backup created: `/tmp/odoo_production_before_testdata_*.sql.gz`
- To restore: `gunzip < backup.sql.gz | docker exec -i opticserp_postgres psql -U odoo -d odoo_production`

**Data Location:** `test_data/sample_data.sql`

---

## 🔧 Utility Playbooks

### Diagnostic

#### `check-websocket-logs.yml`
**Purpose:** Check WebSocket connection logs
**Usage:**
```bash
ansible-playbook -i inventories/production/hosts.yml check-websocket-logs.yml
```
**What it shows:**
- Recent Odoo WebSocket errors
- Nginx WebSocket access logs
- Connection status

---

#### `test-websocket-endpoint.yml`
**Purpose:** Test WebSocket endpoint functionality
**Usage:**
```bash
ansible-playbook -i inventories/production/hosts.yml test-websocket-endpoint.yml
```
**What it does:**
- Send test WebSocket request
- Check Odoo response
- Verify Nginx proxy working

---

#### `check-nginx-conf.yml`
**Purpose:** Display nginx.conf content
**Usage:**
```bash
ansible-playbook -i inventories/production/hosts.yml check-nginx-conf.yml
```

---

## 📚 Documentation Files

### Configuration Documentation
- `WEBSOCKET_CONFIG_README.md` - Complete WebSocket setup guide
- `archived/README.md` - Historical development notes
- `PLAYBOOKS_INDEX.md` - This file

### Inventory
- `inventories/production/hosts.yml` - Production server inventory

### Roles
- `roles/common/` - Common server setup tasks
- `roles/docker/` - Docker and Docker Compose installation
- `roles/postgresql/` - PostgreSQL configuration
- `roles/nginx/` - Nginx setup and configuration
- `roles/odoo/` - Odoo deployment tasks

---

## 🚀 Deployment Workflow

### Initial Deployment (New Server) - RECOMMENDED

**Use the master deployment playbook (все в одном):**

```bash
cd /mnt/d/OpticsERP/ansible

# 1. Setup inventory
cp inventories/production/hosts.yml.example inventories/production/hosts.yml
vim inventories/production/hosts.yml  # Set your server IP and SSH user

# 2. Test connection
ansible all -i inventories/production/hosts.yml -m ping

# 3. Run complete deployment (includes WebSocket!)
ansible-playbook -i inventories/production/hosts.yml deploy-production.yml

# That's it! ✅
```

**This automatically executes all 8 phases:**
- Phase 1: Server Preparation
- Phase 2: Database & Cache (with Redis conflict fix)
- Phase 3: Nginx
- Phase 4: Odoo
- Phase 5: ⭐ **WebSocket Configuration** (critical!)
- Phase 6: Custom Modules
- Phase 7: Mock Services (optional, skipped by default)
- Phase 8: Monitoring (optional, skipped by default)
- FINAL: Verification

**Optional: Enable mock services or monitoring:**
```bash
# With mock services
ansible-playbook -i inventories/production/hosts.yml deploy-production.yml \
  --tags all,mock

# With monitoring
ansible-playbook -i inventories/production/hosts.yml deploy-production.yml \
  --tags all,monitoring

# With both
ansible-playbook -i inventories/production/hosts.yml deploy-production.yml \
  --tags all,mock,monitoring
```

---

### Initial Deployment (Legacy Method) - NOT RECOMMENDED

**⚠️ Old step-by-step method (use only if you know what you're doing):**

```bash
cd /mnt/d/OpticsERP/ansible

# 1. Base system setup
ansible-playbook -i inventories/production/hosts.yml site.yml --tags common,security

# 2. Install Docker
ansible-playbook -i inventories/production/hosts.yml site.yml --tags docker

# 3. Deploy PostgreSQL
ansible-playbook -i inventories/production/hosts.yml site.yml --tags postgresql

# 4. Disable system Redis (prevent port conflict)
ansible-playbook -i inventories/production/hosts.yml disable-system-redis.yml

# 5. Deploy Nginx
ansible-playbook -i inventories/production/hosts.yml site.yml --tags nginx

# 6. Deploy Odoo
ansible-playbook -i inventories/production/hosts.yml deploy-odoo.yml

# 7. ⭐ Configure WebSocket support (CRITICAL!)
ansible-playbook -i inventories/production/hosts.yml configure-odoo-websocket.yml

# 8. Install custom modules
ansible-playbook -i inventories/production/hosts.yml install-modules-cli.yml

# 9. (Optional) Start mock services for testing
ansible-playbook -i inventories/production/hosts.yml start-mock-services.yml
```

**Problems with legacy method:**
- ❌ Easy to forget WebSocket configuration
- ❌ Easy to forget Redis conflict fix
- ❌ More error-prone
- ❌ Longer deployment time

**Use `deploy-production.yml` instead!**

---

### WebSocket Configuration (Existing Deployment)

If you need to add/fix WebSocket configuration on existing server:

```bash
# Run master WebSocket playbook
ansible-playbook -i inventories/production/hosts.yml configure-odoo-websocket.yml

# Verify configuration
ansible-playbook -i inventories/production/hosts.yml test-websocket-endpoint.yml
ansible-playbook -i inventories/production/hosts.yml check-websocket-logs.yml
```

---

### Module Updates

```bash
# Install/update modules
ansible-playbook -i inventories/production/hosts.yml install-modules-cli.yml

# Check installation status
ansible-playbook -i inventories/production/hosts.yml check-modules.yml
```

---

## ⚠️ Important Notes

### Before Running Playbooks

1. **Verify inventory:**
   ```bash
   ansible-inventory -i inventories/production/hosts.yml --list
   ```

2. **Test connection:**
   ```bash
   ansible -i inventories/production/hosts.yml odoo_servers -m ping
   ```

3. **Check SSH key:**
   ```bash
   ls -la ~/.ssh/opticserp
   ```

### Safety Checks

- **Backups created automatically** with date suffix (YYYY-MM-DD)
- **Nginx configs tested** before reload (`nginx -t`)
- **Rollback procedures** documented in WEBSOCKET_CONFIG_README.md

### Port Reference

| Service | Port | Access | Purpose |
|---------|------|--------|---------|
| Nginx | 80 | Public | HTTP reverse proxy |
| Odoo HTTP | 8069 | Public | Web interface |
| Odoo WebSocket | 8072 | Localhost | Real-time via Nginx |
| PostgreSQL | 5432 | Localhost | Database |
| Redis | 6379 | Localhost | Celery broker |
| Mock OFD | 9000 | Localhost | Testing |
| Mock Odoo API | 8070 | Localhost | Testing |

---

## 🔍 Quick Reference

### Check Service Status
```bash
# On server
sudo systemctl status nginx
docker ps --filter name=opticserp

# Via Ansible
ansible -i inventories/production/hosts.yml odoo_servers \
  -m shell -a "sudo systemctl status nginx" -b

ansible -i inventories/production/hosts.yml odoo_servers \
  -m shell -a "docker ps" -b
```

### View Logs
```bash
# Nginx
ansible -i inventories/production/hosts.yml odoo_servers \
  -m shell -a "tail -50 /var/log/nginx/194.87.235.33_access.log" -b

# Odoo
ansible -i inventories/production/hosts.yml odoo_servers \
  -m shell -a "docker logs opticserp_odoo --tail 100" -b
```

### Emergency Rollback
```bash
# If WebSocket config breaks
ssh bozzyk44@194.87.235.33
sudo cp /etc/nginx/nginx.conf.backup-YYYY-MM-DD /etc/nginx/nginx.conf
sudo cp /etc/nginx/sites-available/194.87.235.33.conf.backup-YYYY-MM-DD \
         /etc/nginx/sites-available/194.87.235.33.conf
sudo nginx -t && sudo systemctl reload nginx
```

---

Last Updated: 2025-12-31
Maintained by: OpticsERP DevOps Team
