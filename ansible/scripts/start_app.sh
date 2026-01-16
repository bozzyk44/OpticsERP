#!/bin/bash
# Application startup script for OpticsERP
# Usage: ./start_app.sh [environment] [component]
#   environment: production, staging
#   component: all (default), odoo, kkt-adapter, monitoring

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Default values
ENVIRONMENT="${1:-production}"
COMPONENT="${2:-all}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ANSIBLE_DIR="$(dirname "$SCRIPT_DIR")"

INVENTORY_FILE="$ANSIBLE_DIR/inventories/$ENVIRONMENT/hosts.yml"

echo ""
echo "=========================================="
echo "  OpticsERP Application Startup"
echo "=========================================="
echo ""
echo "Environment: $ENVIRONMENT"
echo "Component: $COMPONENT"
echo ""

# Function to start Odoo
start_odoo() {
    echo ""
    echo -e "${BLUE}→${NC} Starting Odoo on odoo_servers..."
    ansible odoo_servers -i "$INVENTORY_FILE" -m shell \
        -a "cd /opt/opticserp && docker compose up -d odoo" \
        --become-user deploy || true

    echo -e "${GREEN}✓${NC} Odoo startup command sent"
}

# Function to start KKT Adapter (now part of main docker-compose.yml)
start_kkt_adapter() {
    echo ""
    echo -e "${BLUE}→${NC} Starting KKT Adapter on odoo_servers..."
    ansible odoo_servers -i "$INVENTORY_FILE" -m shell \
        -a "cd /opt/opticserp && docker compose up -d kkt_adapter celery_worker celery_flower" \
        --become-user deploy || true

    echo -e "${GREEN}✓${NC} KKT Adapter startup command sent"
}

# Function to start monitoring
start_monitoring() {
    echo ""
    echo -e "${BLUE}→${NC} Starting Monitoring stack on monitoring_servers..."
    ansible monitoring_servers -i "$INVENTORY_FILE" -m shell \
        -a "cd /opt/monitoring && docker compose up -d" \
        --become-user deploy || true

    echo -e "${GREEN}✓${NC} Monitoring startup command sent"
}

# Function to check status
check_status() {
    echo ""
    echo "=========================================="
    echo "  Service Status"
    echo "=========================================="
    echo ""

    case "$COMPONENT" in
        odoo)
            echo -e "${BLUE}→${NC} Checking Odoo status..."
            ansible odoo_servers -i "$INVENTORY_FILE" -m shell \
                -a "cd /opt/opticserp && docker compose ps" \
                --become-user deploy || true
            ;;

        kkt-adapter)
            echo -e "${BLUE}→${NC} Checking KKT Adapter status..."
            ansible odoo_servers -i "$INVENTORY_FILE" -m shell \
                -a "cd /opt/opticserp && docker compose ps kkt_adapter celery_worker celery_flower" \
                --become-user deploy || true
            ;;

        monitoring)
            echo -e "${BLUE}→${NC} Checking Monitoring status..."
            ansible monitoring_servers -i "$INVENTORY_FILE" -m shell \
                -a "cd /opt/monitoring && docker compose ps" \
                --become-user deploy || true
            ;;

        all)
            echo -e "${BLUE}→${NC} Checking all services status..."
            ansible all -i "$INVENTORY_FILE" -m shell \
                -a "systemctl is-active docker nginx postgresql redis || true" \
                --become || true

            echo ""
            ansible odoo_servers -i "$INVENTORY_FILE" -m shell \
                -a "cd /opt/opticserp && docker compose ps || echo 'Not deployed yet'" \
                --become-user deploy || true
            ;;
    esac
}

# Function to show logs
show_logs() {
    local service=${1:-odoo}
    local lines=${2:-50}

    echo ""
    echo -e "${BLUE}→${NC} Showing last $lines lines of $service logs..."

    case "$service" in
        odoo)
            ansible odoo_servers -i "$INVENTORY_FILE" -m shell \
                -a "cd /opt/opticserp && docker compose logs --tail=$lines odoo" \
                --become-user deploy
            ;;

        kkt-adapter)
            ansible odoo_servers -i "$INVENTORY_FILE" -m shell \
                -a "cd /opt/opticserp && docker compose logs --tail=$lines kkt_adapter" \
                --become-user deploy
            ;;

        celery)
            ansible odoo_servers -i "$INVENTORY_FILE" -m shell \
                -a "cd /opt/opticserp && docker compose logs --tail=$lines celery_worker" \
                --become-user deploy
            ;;

        flower)
            ansible odoo_servers -i "$INVENTORY_FILE" -m shell \
                -a "cd /opt/opticserp && docker compose logs --tail=$lines celery_flower" \
                --become-user deploy
            ;;

        prometheus)
            ansible monitoring_servers -i "$INVENTORY_FILE" -m shell \
                -a "cd /opt/monitoring && docker compose logs --tail=$lines prometheus" \
                --become-user deploy
            ;;

        grafana)
            ansible monitoring_servers -i "$INVENTORY_FILE" -m shell \
                -a "cd /opt/monitoring && docker compose logs --tail=$lines grafana" \
                --become-user deploy
            ;;
    esac
}

# Main execution
case "$COMPONENT" in
    odoo)
        start_odoo
        sleep 3
        check_status
        ;;

    kkt-adapter)
        start_kkt_adapter
        sleep 3
        check_status
        ;;

    monitoring)
        start_monitoring
        sleep 3
        check_status
        ;;

    all)
        start_monitoring
        sleep 2
        start_odoo
        sleep 2
        start_kkt_adapter
        sleep 5
        check_status
        ;;

    status)
        check_status
        ;;

    logs)
        SERVICE="${3:-odoo}"
        LINES="${4:-50}"
        show_logs "$SERVICE" "$LINES"
        ;;

    restart)
        echo ""
        echo -e "${YELLOW}⚠${NC} Restarting all services..."
        ansible odoo_servers -i "$INVENTORY_FILE" -m shell \
            -a "cd /opt/opticserp && docker compose restart || true" \
            --become-user deploy
        ansible monitoring_servers -i "$INVENTORY_FILE" -m shell \
            -a "cd /opt/monitoring && docker compose restart || true" \
            --become-user deploy
        sleep 5
        check_status
        ;;

    stop)
        echo ""
        echo -e "${YELLOW}⚠${NC} Stopping all services..."
        ansible odoo_servers -i "$INVENTORY_FILE" -m shell \
            -a "cd /opt/opticserp && docker compose down || true" \
            --become-user deploy
        ansible monitoring_servers -i "$INVENTORY_FILE" -m shell \
            -a "cd /opt/monitoring && docker compose down || true" \
            --become-user deploy
        echo -e "${GREEN}✓${NC} All services stopped"
        ;;

    *)
        echo -e "${RED}✗${NC} Invalid component: $COMPONENT"
        echo ""
        echo "Usage: $0 [environment] [component]"
        echo ""
        echo "Environments:"
        echo "  production  - Production environment (default)"
        echo "  staging     - Staging environment"
        echo ""
        echo "Components:"
        echo "  all         - Start all components (default)"
        echo "  odoo        - Start Odoo only"
        echo "  kkt-adapter - Start KKT Adapter + Celery stack"
        echo "  monitoring  - Start Prometheus + Grafana only"
        echo "  status      - Show service status"
        echo "  logs        - Show logs (services: odoo, kkt-adapter, celery, flower, prometheus, grafana)"
        echo "  restart     - Restart all services"
        echo "  stop        - Stop all services"
        echo ""
        echo "Examples:"
        echo "  $0 production all              # Start all components"
        echo "  $0 staging odoo                # Start Odoo on staging"
        echo "  $0 production status           # Check status"
        echo "  $0 production logs odoo 100    # Show last 100 lines of Odoo logs"
        echo "  $0 production logs celery 50   # Show last 50 lines of Celery logs"
        echo "  $0 production restart          # Restart all services"
        exit 1
        ;;
esac

echo ""
echo -e "${GREEN}✓${NC} Operation completed!"
echo ""
