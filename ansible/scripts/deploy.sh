#!/bin/bash
# OpticsERP Deployment Script
# Usage: ./deploy.sh [environment] [mode]
#   environment: production (default), staging
#   mode: prepare, full (default), app-only

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Default values
ENVIRONMENT="${1:-production}"
MODE="${2:-full}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ANSIBLE_DIR="$(dirname "$SCRIPT_DIR")"
PROJECT_ROOT="$(dirname "$ANSIBLE_DIR")"

# Paths
INVENTORY_FILE="$ANSIBLE_DIR/inventories/$ENVIRONMENT/hosts.yml"
ENV_FILE="$ANSIBLE_DIR/.env"

echo ""
echo "=========================================="
echo "  OpticsERP Deployment Script"
echo "=========================================="
echo ""
echo "Environment: $ENVIRONMENT"
echo "Mode: $MODE"
echo "Inventory: $INVENTORY_FILE"
echo ""

# Function to print section header
print_section() {
    echo ""
    echo "=========================================="
    echo "  $1"
    echo "=========================================="
    echo ""
}

# Function to check requirements
check_requirements() {
    print_section "Checking Requirements"

    # Check Ansible
    if ! command -v ansible &> /dev/null; then
        echo -e "${RED}✗${NC} Ansible not found!"
        echo "Run: ./ansible/scripts/install_ansible.sh"
        exit 1
    fi
    echo -e "${GREEN}✓${NC} Ansible: $(ansible --version | head -n1 | awk '{print $2}')"

    # Check inventory file
    if [ ! -f "$INVENTORY_FILE" ]; then
        echo -e "${RED}✗${NC} Inventory file not found: $INVENTORY_FILE"
        echo ""
        echo "Please create inventory file:"
        echo "  cp $ANSIBLE_DIR/inventories/$ENVIRONMENT/hosts.yml.example \\"
        echo "     $INVENTORY_FILE"
        exit 1
    fi
    echo -e "${GREEN}✓${NC} Inventory file exists"

    # Check .env file
    if [ ! -f "$ENV_FILE" ]; then
        echo -e "${YELLOW}⚠${NC} Environment file not found: $ENV_FILE"
        echo ""
        echo "Creating from template..."
        cp "$ANSIBLE_DIR/.env.example" "$ENV_FILE"
        echo -e "${YELLOW}⚠${NC} Please edit $ENV_FILE with your passwords!"
        echo "Press Enter to continue after editing .env file..."
        read -r
    fi

    # Load environment variables
    if [ -f "$ENV_FILE" ]; then
        echo -e "${GREEN}✓${NC} Loading environment variables from .env"
        # shellcheck disable=SC1090
        source "$ENV_FILE"
    fi

    # Validate required variables
    if [ -z "$POSTGRES_PASSWORD" ]; then
        echo -e "${RED}✗${NC} POSTGRES_PASSWORD not set in .env file!"
        exit 1
    fi
    echo -e "${GREEN}✓${NC} Environment variables loaded"
}

# Function to test connectivity
test_connectivity() {
    print_section "Testing Server Connectivity"

    echo "Pinging all hosts..."
    if ansible all -i "$INVENTORY_FILE" -m ping; then
        echo ""
        echo -e "${GREEN}✓${NC} All hosts are reachable"
    else
        echo ""
        echo -e "${RED}✗${NC} Some hosts are unreachable!"
        echo "Please check:"
        echo "  - SSH access is configured"
        echo "  - IP addresses in inventory are correct"
        echo "  - Firewall allows SSH connections"
        exit 1
    fi
}

# Function to run playbook with confirmation
run_playbook() {
    local playbook=$1
    local description=$2
    local extra_args=${3:-""}

    print_section "$description"

    echo "About to run: $playbook"
    echo "Environment: $ENVIRONMENT"

    if [ "$MODE" != "auto" ]; then
        echo ""
        echo "Continue? (y/n)"
        read -r response
        if [[ ! "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
            echo "Aborted by user"
            exit 1
        fi
    fi

    echo ""
    # shellcheck disable=SC2086
    ansible-playbook -i "$INVENTORY_FILE" "$playbook" $extra_args

    local exit_code=$?
    if [ $exit_code -eq 0 ]; then
        echo ""
        echo -e "${GREEN}✓${NC} $description completed successfully"
    else
        echo ""
        echo -e "${RED}✗${NC} $description failed with exit code $exit_code"
        exit $exit_code
    fi
}

# Function to show post-deployment info
show_post_deployment() {
    print_section "Deployment Summary"

    echo "Checking service status on remote hosts..."
    echo ""

    ansible all -i "$INVENTORY_FILE" -m shell \
        -a "systemctl is-active docker nginx postgresql redis chrony || true" \
        --become || true

    echo ""
    echo -e "${GREEN}✓${NC} Deployment completed successfully!"
    echo ""
    echo "Access points:"
    echo "  - Grafana: http://YOUR_SERVER:3000 (admin/GRAFANA_PASSWORD)"
    echo "  - Prometheus: http://YOUR_SERVER:9090"
    echo ""
    echo "Next steps:"
    echo "  1. Deploy application: ./ansible/scripts/start_app.sh $ENVIRONMENT"
    echo "  2. Check Prometheus targets: http://YOUR_SERVER:9090/targets"
    echo "  3. Import Grafana dashboards"
    echo "  4. Configure alerting"
    echo ""
}

# Main execution
main() {
    check_requirements

    case "$MODE" in
        prepare)
            # Basic server preparation only
            test_connectivity
            run_playbook "$ANSIBLE_DIR/prepare-server.yml" "Server Preparation"
            ;;

        full)
            # Full infrastructure deployment
            test_connectivity
            run_playbook "$ANSIBLE_DIR/site.yml" "Full Infrastructure Deployment"
            show_post_deployment
            ;;

        infra)
            # Infrastructure only (no app)
            test_connectivity
            run_playbook "$ANSIBLE_DIR/site.yml" "Infrastructure Deployment" "--skip-tags app"
            show_post_deployment
            ;;

        app)
            # Application deployment only
            test_connectivity
            run_playbook "$ANSIBLE_DIR/deploy-app.yml" "Application Deployment"
            ;;

        check)
            # Dry-run mode
            check_requirements
            test_connectivity
            echo ""
            echo -e "${GREEN}✓${NC} All checks passed!"
            echo ""
            echo "Run without 'check' mode to deploy:"
            echo "  ./deploy.sh $ENVIRONMENT full"
            ;;

        *)
            echo -e "${RED}✗${NC} Invalid mode: $MODE"
            echo ""
            echo "Usage: $0 [environment] [mode]"
            echo ""
            echo "Environments:"
            echo "  production  - Production deployment (default)"
            echo "  staging     - Staging deployment"
            echo ""
            echo "Modes:"
            echo "  prepare     - Basic server preparation only"
            echo "  full        - Full infrastructure + app deployment (default)"
            echo "  infra       - Infrastructure only (Docker, DB, monitoring)"
            echo "  app         - Application deployment only"
            echo "  check       - Dry-run, check configuration only"
            echo ""
            echo "Examples:"
            echo "  $0                           # Full production deployment"
            echo "  $0 staging prepare           # Prepare staging server"
            echo "  $0 production check          # Check production setup"
            echo "  $0 staging full              # Full staging deployment"
            exit 1
            ;;
    esac
}

# Run main function
main
