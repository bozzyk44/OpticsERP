# Installation Steps

**Last Updated:** 2025-11-30
**Estimated Time:** 1-2 hours (fresh installation)
**Difficulty:** Intermediate

---

## 📋 Prerequisites

Before starting, ensure:
- [ ] Ubuntu 22.04 LTS server ready
- [ ] [System requirements](01_system_requirements.md) verified
- [ ] Root/sudo access available
- [ ] Internet connection active
- [ ] OFD API credentials ready (for 54-ФЗ compliance)

---

## 🚀 Installation Overview

The installation process consists of 4 main phases:

1. **Server Preparation** (15-30 min) - Install Docker and prerequisites
2. **Code Deployment** (15 min) - Clone repository and configure
3. **Service Deployment** (30-45 min) - Build and start containers
4. **System Initialization** (15-30 min) - Configure Odoo and modules

**Total time:** 1.5-2.5 hours

---

## Phase 1: Server Preparation

### Step 1.1: Update System

```bash
# Update package lists
sudo apt update

# Upgrade existing packages
sudo apt upgrade -y

# Reboot if kernel was updated (optional)
# sudo reboot
```

### Step 1.2: Run Preparation Script

We provide an automated script that installs all prerequisites:

```bash
# Download preparation script
wget https://raw.githubusercontent.com/bozzyk44/OpticsERP/main/scripts/prep_server.sh

# Make executable
chmod +x prep_server.sh

# Run script
sudo bash prep_server.sh
```

**What the script does:**
- Installs Docker Engine 24.0+
- Installs Docker Compose 2.20+
- Installs Git, curl, htop, net-tools
- Adds current user to docker group
- Verifies installation

**Expected output:**
```
==========================================
  OpticsERP Server Preparation Complete!
==========================================

✅ Docker Engine installed
✅ Docker Compose installed
✅ Prerequisites installed

Next Steps:
1. Log out and log back in (for docker group changes)
2. Clone OpticsERP repository
3. Follow installation guide
```

### Step 1.3: Apply Group Changes

**IMPORTANT:** Log out and log back in for docker group changes to take effect.

```bash
# Log out
exit

# SSH back in
ssh user@your-server

# Verify docker works without sudo
docker ps
```

---

## Phase 2: Code Deployment

### Step 2.1: Clone Repository

```bash
# Clone OpticsERP repository
git clone https://github.com/bozzyk44/OpticsERP.git

# Enter directory
cd OpticsERP

# Verify structure
ls -la
```

**Expected structure:**
```
OpticsERP/
├── addons/              # Custom Odoo modules
├── docs/                # Documentation
├── kkt_adapter/         # KKT Adapter service
├── scripts/             # Utility scripts
├── docker-compose.yml   # Service orchestration
├── .env.example         # Configuration template
└── README.md
```

### Step 2.2: Create Configuration File

```bash
# Copy environment template
cp .env.example .env

# Edit configuration
nano .env
```

**Critical variables to configure:**

```bash
# PostgreSQL (change password!)
POSTGRES_PASSWORD=YourStrongPasswordHere123!

# Odoo (change password!)
ODOO_ADMIN_PASSWORD=YourAdminPasswordHere123!

# KKT Adapter - OFD credentials
KKT_OFD_API_URL=https://your-ofd-provider.ru/api/v1
KKT_OFD_API_TOKEN=your_ofd_api_token_here

# Optional: JIRA integration
# JIRA_URL=https://your-company.atlassian.net
# JIRA_EMAIL=your-email@example.com
# JIRA_API_TOKEN=your_jira_token
```

**Save and exit:** Press `Ctrl+X`, then `Y`, then `Enter`

### Step 2.3: Validate Configuration

```bash
# Run configuration validator
python3 scripts/validate_config.py
```

**Expected output:**
```
=== OpticsERP Configuration Validation ===

=== Python Version ===
✅ Python version OK: 3.11.x

=== Docker ===
✅ Docker installed: Docker version 24.0.x
✅ Docker service is running

=== Docker Compose ===
✅ Docker Compose installed: v2.20.x

=== Environment File ===
✅ .env file exists
✅ All required environment variables present

=== Port Availability ===
✅ Port 8069 (Odoo Web) is available
✅ Port 8000 (KKT Adapter) is available
✅ Port 5432 (PostgreSQL) is available
✅ Port 6379 (Redis) is available

=== Disk Space ===
✅ Disk space OK: 150 GB available

✅ All checks passed! System is ready for deployment.
```

---

## Phase 3: Service Deployment

### Step 3.1: Build Docker Images

```bash
# Build all containers (first time: 10-20 minutes)
docker-compose build --no-cache
```

**Expected output:**
```
Building postgres...
Building redis...
Building odoo...
Building kkt_adapter...
Successfully built ...
Successfully tagged opticserp_odoo:latest
```

**Note:** First build downloads base images and compiles dependencies. Subsequent builds are faster.

### Step 3.2: Start Infrastructure Services

```bash
# Start database and cache first
docker-compose up -d postgres redis

# Wait for services to be ready
sleep 10

# Verify services are running
docker-compose ps
```

**Expected output:**
```
NAME                 STATUS              PORTS
opticserp_postgres   Up 10 seconds       0.0.0.0:5432->5432/tcp
opticserp_redis      Up 10 seconds       0.0.0.0:6379->6379/tcp
```

### Step 3.3: Initialize Database

```bash
# Initialize Odoo database with base module
docker-compose run --rm odoo odoo \
  -d opticserp \
  --init=base \
  --stop-after-init \
  --no-http
```

**Expected output (last lines):**
```
INFO opticserp odoo.modules.loading: Modules loaded.
INFO opticserp odoo.service.server: Stopping gracefully
```

**This creates:**
- Database `opticserp`
- Admin user (password from .env)
- Base Odoo modules installed

---

## Phase 4: System Initialization

### Step 4.1: Install Custom Modules

```bash
# Install all OpticsERP custom modules
docker-compose run --rm odoo odoo \
  -d opticserp \
  -i optics_core,optics_pos_ru54fz,connector_b,ru_accounting_extras \
  --stop-after-init \
  --no-http
```

**Expected output:**
```
INFO opticserp odoo.modules.loading: Loading module optics_core
INFO opticserp odoo.modules.loading: Loading module optics_pos_ru54fz
INFO opticserp odoo.modules.loading: Loading module connector_b
INFO opticserp odoo.modules.loading: Loading module ru_accounting_extras
INFO opticserp odoo.modules.loading: Modules loaded.
```

**Modules installed:**
- `optics_core` - Prescriptions, lenses, manufacturing orders
- `optics_pos_ru54fz` - POS with 54-ФЗ compliance
- `connector_b` - Excel/CSV import
- `ru_accounting_extras` - Russian accounting features

### Step 4.2: Load Russian Language Pack

```bash
# Load Russian translations
docker-compose run --rm odoo odoo \
  -d opticserp \
  --load-language=ru_RU \
  --stop-after-init \
  --no-http
```

**Expected output:**
```
INFO opticserp odoo.addons.base.models.ir_module: loading translation file for language ru_RU
INFO opticserp odoo.addons.base.models.ir_module: module base: loaded
```

### Step 4.3: Configure Russian Locale

```bash
# Run locale configuration script
python3 scripts/setup_russian_locale.py
```

**This configures:**
- Date format: dd.mm.yyyy
- Time format: 24-hour
- Number format: 1 234,56
- Week start: Monday
- Admin user language: Russian

### Step 4.4: Start All Services

```bash
# Start all services
docker-compose up -d

# Wait for services to start
sleep 15

# Check service status
docker-compose ps
```

**Expected output (all services "Up"):**
```
NAME                   STATUS              PORTS
opticserp_celery       Up 15 seconds
opticserp_kkt_adapter  Up 15 seconds       0.0.0.0:8000->8000/tcp
opticserp_odoo         Up 15 seconds       0.0.0.0:8069->8069/tcp
opticserp_postgres     Up 5 minutes        0.0.0.0:5432->5432/tcp
opticserp_redis        Up 5 minutes        0.0.0.0:6379->6379/tcp
```

---

## ✅ Verification

### Step 5.1: Access Web Interface

Open browser and navigate to:
```
http://your-server-ip:8069
```

**You should see:**
- Odoo login screen
- Language: Russian (if configured)

**Login credentials:**
- Email: `admin`
- Password: `[your ODOO_ADMIN_PASSWORD from .env]`

### Step 5.2: Verify Modules

After login, check installed modules:

1. Go to **Settings → Apps** (Настройки → Приложения)
2. Remove "Apps" filter
3. Search for "optics"
4. Verify all 4 modules are installed:
   - ✅ Optics Core
   - ✅ Optics POS RU 54-FZ
   - ✅ Connector B
   - ✅ RU Accounting Extras

### Step 5.3: Verify KKT Adapter

Check KKT Adapter API documentation:
```
http://your-server-ip:8000/docs
```

**You should see:**
- FastAPI Swagger UI
- API endpoints listed:
  - POST /v1/kkt/receipt
  - GET /v1/kkt/buffer/status
  - GET /v1/health

### Step 5.4: Check Logs

```bash
# Odoo logs
docker-compose logs -f odoo --tail=50

# KKT Adapter logs
docker-compose logs -f kkt_adapter --tail=50

# All services
docker-compose logs -f --tail=20
```

**No errors should appear.** Warnings are OK.

---

## 🎉 Installation Complete!

Your OpticsERP system is now running!

**Quick links:**
- 🌐 **Odoo Web:** http://your-server-ip:8069
- 🔧 **KKT Adapter API:** http://your-server-ip:8000/docs
- 📊 **Celery Flower:** http://your-server-ip:5555 (if enabled)

**Default credentials:**
- Email: `admin`
- Password: From `.env` file (`ODOO_ADMIN_PASSWORD`)

---

## 🔧 Post-Installation

### Recommended Next Steps

1. **Change default password** (Security)
   - Settings → Users → Administrator → Change Password

2. **Configure company** (Settings → General Settings → Companies)
   - Company name
   - Address
   - Logo
   - Tax ID (ИНН)

3. **Configure fiscal settings** (for 54-ФЗ compliance)
   - POS → Configuration → Point of Sale
   - Enable KKT Adapter
   - Set KKT Adapter URL: `http://kkt_adapter:8000`

4. **Create first POS** (Point of Sale → Configuration → POS)
   - Name: "Касса 1"
   - Payment methods: Cash, Card
   - Enable receipt printing

5. **Import product catalog** (if you have one)
   - Use Connector B module
   - Import/Export → Import Profiles

6. **Configure backup schedule**
   ```bash
   # Add to crontab
   crontab -e

   # Daily backup at 2 AM
   0 2 * * * cd /path/to/OpticsERP && bash scripts/backup.sh
   ```

7. **Set up monitoring** (optional)
   - Enable Prometheus in `.env`
   - Configure Grafana dashboards

---

## 🆘 Troubleshooting

### Issue: Cannot access http://localhost:8069

**Solution:**
```bash
# Check if Odoo is running
docker-compose ps

# Check Odoo logs
docker-compose logs odoo --tail=50

# Restart Odoo
docker-compose restart odoo
```

### Issue: "Port already in use"

**Solution:**
```bash
# Kill process on port 8069
python3 scripts/kill_port.py 8069

# Or find and kill manually
sudo netstat -tulpn | grep 8069
sudo kill -9 <PID>
```

### Issue: Database connection failed

**Solution:**
```bash
# Check PostgreSQL is running
docker-compose ps postgres

# Check PostgreSQL logs
docker-compose logs postgres --tail=50

# Restart PostgreSQL
docker-compose restart postgres
```

### Issue: Module installation error

**Solution:**
```bash
# Check module syntax
docker-compose run --rm odoo odoo -d opticserp -c "print('ok')"

# Reinstall module
docker-compose run --rm odoo odoo \
  -d opticserp \
  -u optics_core \
  --stop-after-init
```

**For more troubleshooting, see:** [Troubleshooting Guide](05_troubleshooting.md)

---

## 📝 Summary

**What you've accomplished:**
- ✅ Installed Docker and prerequisites
- ✅ Deployed OpticsERP containers
- ✅ Initialized database
- ✅ Installed custom modules
- ✅ Configured Russian locale
- ✅ Verified system functionality

**Next:** [Configuration Guide](03_configuration.md) for advanced settings

---

**Installation successful?** Give yourself a pat on the back! 🎉

**Questions?** See [Troubleshooting Guide](05_troubleshooting.md) or open an issue on GitHub.
