# OpticsERP Installation Guide

**Version:** 1.0.0
**Last Updated:** 2025-11-30
**Target Platform:** Ubuntu 20.04/22.04 LTS
**Deployment Method:** Docker Compose

---

## 📋 Overview

This guide provides step-by-step instructions for installing and deploying OpticsERP system for optical retail businesses. OpticsERP is an Odoo 17-based ERP/POS solution with Russian 54-ФЗ compliance and offline-first architecture.

**What you'll learn:**
- System requirements and prerequisites
- Fresh installation from scratch
- Configuration and setup
- Verification and health checks
- Troubleshooting common issues
- Backup, restore, and upgrade procedures

---

## 🎯 Target Audience

This guide is for:
- **System Administrators** - Primary audience, experienced with Linux/Docker
- **IT Managers** - Secondary audience, moderate technical skills
- **DevOps Engineers** - Advanced users, looking for automation

**Prerequisites knowledge:**
- Basic Linux command line
- Docker and Docker Compose basics
- Text editing (nano/vim)
- Basic networking concepts

---

## 📚 Guide Structure

| Section | Description | Audience | Time |
|---------|-------------|----------|------|
| [01. System Requirements](01_system_requirements.md) | Hardware, software, network requirements | All | 15 min |
| [02. Installation Steps](02_installation_steps.md) | Step-by-step installation guide | All | 1-2 hours |
| [03. Configuration](03_configuration.md) | Environment configuration and tuning | SysAdmin | 30 min |
| [04. Verification](04_verification.md) | Health checks and smoke tests | All | 15 min |
| [05. Troubleshooting](05_troubleshooting.md) | Common issues and solutions | All | As needed |
| [06. Upgrade Guide](06_upgrade_guide.md) | Upgrade procedures and rollback | SysAdmin | 30 min |
| [07. Backup & Restore](07_backup_restore.md) | Backup and disaster recovery | SysAdmin | 30 min |
| [Appendix A: Ports](appendix_a_ports.md) | Port reference and firewall rules | SysAdmin | Reference |
| [Appendix B: Environment Variables](appendix_b_env_vars.md) | Complete .env reference | SysAdmin | Reference |

---

## 🚀 Quick Start

**For experienced users who want to get started immediately:**

```bash
# 1. Install prerequisites
sudo bash scripts/prep_server.sh

# 2. Clone repository
git clone https://github.com/bozzyk44/OpticsERP.git
cd OpticsERP

# 3. Configure environment
cp .env.example .env
nano .env  # Edit configuration

# 4. Validate configuration
python scripts/validate_config.py

# 5. Deploy
docker-compose build --no-cache
docker-compose up -d

# 6. Initialize database
docker-compose exec odoo odoo -d opticserp --init=base --stop-after-init

# 7. Install modules
docker-compose exec odoo odoo -d opticserp \
  -i optics_core,optics_pos_ru54fz,connector_b,ru_accounting_extras \
  --stop-after-init

# 8. Start services
docker-compose start odoo

# 9. Access system
echo "🌐 Odoo: http://localhost:8069"
echo "Login: admin / [your ODOO_ADMIN_PASSWORD from .env]"
```

**Total time:** ~1-2 hours (including Docker builds)

---

## 📖 Detailed Installation Path

**For first-time users or production deployments:**

### Phase 1: Planning (30 minutes)
1. Read [System Requirements](01_system_requirements.md)
2. Verify hardware and network availability
3. Plan deployment architecture (single server vs. multi-server)
4. Prepare server credentials and access

### Phase 2: Server Preparation (30 minutes)
1. Provision Ubuntu 22.04 LTS server
2. Run [prep_server.sh](../scripts/prep_server.sh) script
3. Verify Docker installation
4. Configure firewall rules (see [Appendix A](appendix_a_ports.md))

### Phase 3: Installation (1 hour)
1. Clone OpticsERP repository
2. Create and edit `.env` file
3. Run configuration validator
4. Build Docker images
5. Start services
6. Initialize database
7. Install custom modules

### Phase 4: Configuration (30 minutes)
1. Configure Odoo settings
2. Set up KKT Adapter
3. Configure backup schedule
4. Enable monitoring (optional)

### Phase 5: Verification (30 minutes)
1. Run health checks
2. Perform smoke tests
3. Test POS functionality
4. Verify fiscal receipt printing
5. Test offline mode

**Total time:** ~3-4 hours (with testing)

---

## ⚠️ Important Notes

### Before You Begin

1. **Backup existing data** - If upgrading, always backup first
2. **Use strong passwords** - Never use default passwords in production
3. **Plan for downtime** - Schedule installation during off-hours
4. **Test in staging** - Test the installation process in a staging environment first
5. **Document changes** - Keep notes of any custom configurations

### Security Considerations

- Change all default passwords in `.env` file
- Use HTTPS in production (see SSL configuration)
- Restrict network access to required ports only
- Keep system and Docker up to date
- Regular security audits

### Production vs. Development

This guide covers **development/staging** deployments using Docker Compose.

For production deployments, consider:
- High availability (load balancing, redundancy)
- SSL/TLS certificates
- Managed PostgreSQL (RDS, Cloud SQL)
- Container orchestration (Kubernetes)
- Monitoring and alerting
- Automated backups

---

## 🆘 Getting Help

### Documentation Resources

- **Installation Issues:** [Troubleshooting Guide](05_troubleshooting.md)
- **Configuration Help:** [Configuration Guide](03_configuration.md)
- **System Requirements:** [Requirements](01_system_requirements.md)

### Support Channels

- **GitHub Issues:** https://github.com/bozzyk44/OpticsERP/issues
- **Email Support:** support@example.com (if applicable)
- **Community Forum:** (if applicable)

### Professional Services

For professional installation, configuration, and support:
- Contact: professional-services@example.com

---

## 📝 Changelog

### Version 1.0.0 (2025-11-30)
- Initial installation guide release
- Covers OpticsERP MVP deployment
- Tested on Ubuntu 22.04 LTS
- Docker Compose deployment method

---

## 📄 License

This documentation is part of OpticsERP project and is licensed under the same terms as the main project.

---

## ✅ Pre-Flight Checklist

Before starting installation, ensure:

- [ ] Ubuntu 20.04 or 22.04 LTS server ready
- [ ] Root/sudo access available
- [ ] Minimum 4 GB RAM, 50 GB disk space
- [ ] Internet connection available
- [ ] Ports 8069, 8000, 5432, 6379 available
- [ ] Docker and Docker Compose will be installed
- [ ] `.env` configuration values ready
- [ ] OFD API credentials available (for 54-ФЗ compliance)
- [ ] Backup plan prepared
- [ ] Rollback plan prepared

---

**Ready to begin?** Start with [System Requirements →](01_system_requirements.md)
