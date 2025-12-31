#!/bin/bash
# OpticsERP Master Deployment Wrapper
# Complete automation: check → install → validate → deploy → start
# Usage: ./deploy-wrapper.sh [environment] [skip-checks]

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m'

ENVIRONMENT="${1:-production}"
SKIP_CHECKS="${2:-false}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# WSL/Linux check (Ansible requires Unix-like environment)
if [[ ! -f /proc/version ]] || [[ ! $(grep -i "linux" /proc/version 2>/dev/null) ]]; then
    echo ""
    echo "==========================================="
    echo -e "  ${RED}ERROR: Not running in WSL/Linux${NC}"
    echo "==========================================="
    echo ""
    echo "Ansible requires WSL (Windows Subsystem for Linux) on Windows."
    echo ""
    echo "To install WSL:"
    echo "  1. Open PowerShell as Administrator"
    echo "  2. Run: wsl --install -d Ubuntu-20.04"
    echo "  3. Restart Windows"
    echo "  4. Open WSL terminal and navigate to:"
    echo "     cd /mnt/d/OpticsERP/ansible"
    echo "  5. Run this script again from WSL"
    echo ""
    echo "See CLAUDE.md section 2.1 for detailed instructions."
    echo ""
    exit 1
fi

# Check if running in Git Bash (which doesn't support Ansible properly)
if [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "win32" ]]; then
    echo ""
    echo "==========================================="
    echo -e "  ${RED}ERROR: Running in Git Bash${NC}"
    echo "==========================================="
    echo ""
    echo "Ansible does NOT work in Git Bash on Windows."
    echo "Please use WSL instead (see instructions above)."
    echo ""
    exit 1
fi

echo ""
echo "==========================================="
echo -e "  ${BOLD}OpticsERP Master Deployment${NC}"
echo "==========================================="
echo ""
echo "Environment: $ENVIRONMENT"
echo "Script Directory: $SCRIPT_DIR"
echo ""

# Function to print step
print_step() {
    echo ""
    echo "==========================================="
    echo -e "  ${BLUE}STEP $1: $2${NC}"
    echo "==========================================="
    echo ""
}

# Function to confirm
confirm() {
    if [ "$SKIP_CHECKS" = "true" ]; then
        return 0
    fi

    echo ""
    echo -e "${YELLOW}Continue? (y/n)${NC}"
    read -r response
    if [[ ! "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
        echo "Aborted by user"
        exit 1
    fi
}

# Step 1: Check and install Ansible
print_step "1" "Ansible Installation Check"
bash "$SCRIPT_DIR/install_ansible.sh"
confirm

# Step 2: Validate inventory
print_step "2" "Inventory Validation"
bash "$SCRIPT_DIR/check_inventory.sh" "$ENVIRONMENT"
confirm

# Step 3: Validate secrets
print_step "3" "Secrets Validation"
bash "$SCRIPT_DIR/validate_secrets.sh"
confirm

# Step 4: Deploy infrastructure
print_step "4" "Infrastructure Deployment"
echo "This will deploy:"
echo "  - System packages and dependencies"
echo "  - Docker + Docker Compose"
echo "  - PostgreSQL 15"
echo "  - Redis 7.2"
echo "  - Nginx"
echo "  - Prometheus + Grafana"
echo "  - Security hardening (UFW, fail2ban, SSH)"
echo ""
confirm

bash "$SCRIPT_DIR/deploy.sh" "$ENVIRONMENT" "full"

# Step 5: Wait for infrastructure to stabilize
print_step "5" "Infrastructure Stabilization"
echo "Waiting 30 seconds for infrastructure services to stabilize..."
sleep 30

# Step 6: Deploy Odoo application
print_step "6" "Odoo Application Deployment"
echo "This will deploy:"
echo "  - Odoo 17 (ERP/POS)"
echo "  - KKT Adapter (FastAPI)"
echo "  - Celery Worker (4 queues)"
echo "  - Celery Flower (monitoring)"
echo "  - Custom addons (optics_core, optics_pos_ru54fz, connector_b, ru_accounting_extras)"
echo ""
confirm

cd "$(dirname "$SCRIPT_DIR")" || exit 1
source .env
ansible-playbook -i "inventories/$ENVIRONMENT/hosts.yml" deploy-odoo.yml

# Step 7: Wait for applications to stabilize
print_step "7" "Application Stabilization"
echo "Waiting 30 seconds for applications to stabilize..."
sleep 30

# Step 8: Final health check
print_step "8" "Final Health Check"
bash "$SCRIPT_DIR/health_check.sh" "$ENVIRONMENT"

# Summary
echo ""
echo "==========================================="
echo -e "  ${GREEN}${BOLD}✓ DEPLOYMENT COMPLETE!${NC}"
echo "==========================================="
echo ""
echo "Services deployed:"
echo ""
echo "Infrastructure:"
echo "  - PostgreSQL 15 on port 5432"
echo "  - Redis 7.2 on port 6379"
echo "  - Prometheus: http://YOUR_SERVER:9090"
echo "  - Grafana: http://YOUR_SERVER:3000"
echo ""
echo "Applications:"
echo "  - Odoo 17: http://YOUR_SERVER:8069"
echo "  - KKT Adapter: http://YOUR_SERVER:8000"
echo "  - Celery Flower: http://YOUR_SERVER:5555"
echo ""
echo "Next steps:"
echo "  1. Open Odoo: http://YOUR_SERVER:8069"
echo "  2. Create database or login"
echo "  3. Install custom modules: optics_core, optics_pos_ru54fz, connector_b, ru_accounting_extras"
echo "  4. Open Grafana: http://YOUR_SERVER:3000"
echo "  5. Import dashboards from docs/monitoring/"
echo "  6. Test POS functionality with KKT Adapter"
echo "  7. Setup backup verification"
echo ""
echo "Documentation: docs/deployment/ansible-guide.md"
echo ""
