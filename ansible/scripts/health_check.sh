#!/bin/bash
# Health check script for deployed services
# Usage: ./health_check.sh [environment]

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

ENVIRONMENT="${1:-production}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ANSIBLE_DIR="$(dirname "$SCRIPT_DIR")"
INVENTORY_FILE="$ANSIBLE_DIR/inventories/$ENVIRONMENT/hosts.yml"

echo ""
echo "=========================================="
echo "  Health Check - $ENVIRONMENT"
echo "=========================================="
echo ""

FAILED_CHECKS=0

# Function to check service
check_service() {
    local service=$1
    local host_group=$2

    echo -n "Checking $service... "

    if ansible "$host_group" -i "$INVENTORY_FILE" -m shell \
        -a "systemctl is-active $service" --become &> /dev/null; then
        echo -e "${GREEN}✓ RUNNING${NC}"
    else
        echo -e "${RED}✗ NOT RUNNING${NC}"
        FAILED_CHECKS=$((FAILED_CHECKS + 1))
    fi
}

# Function to check port
check_port() {
    local port=$1
    local host_group=$2
    local service_name=$3

    echo -n "Checking port $port ($service_name)... "

    if ansible "$host_group" -i "$INVENTORY_FILE" -m shell \
        -a "netstat -tuln | grep -q :$port" --become &> /dev/null; then
        echo -e "${GREEN}✓ LISTENING${NC}"
    else
        echo -e "${RED}✗ NOT LISTENING${NC}"
        FAILED_CHECKS=$((FAILED_CHECKS + 1))
    fi
}

# Function to check HTTP endpoint
check_http() {
    local url=$1
    local description=$2

    echo -n "Checking $description... "

    if ansible all -i "$INVENTORY_FILE" -m uri \
        -a "url=$url status_code=200" &> /dev/null; then
        echo -e "${GREEN}✓ OK${NC}"
    else
        echo -e "${YELLOW}⚠ UNREACHABLE${NC}"
        # Don't increment FAILED_CHECKS as this might be expected
    fi
}

# System services
echo "System Services:"
check_service "docker" "all"
check_service "nginx" "odoo_servers"
check_service "postgresql" "db_servers"
check_service "redis" "db_servers"
check_service "chrony" "all"

echo ""

# Ports
echo "Network Ports:"
check_port "5432" "db_servers" "PostgreSQL"
check_port "6379" "db_servers" "Redis"
check_port "8069" "odoo_servers" "Odoo"
check_port "8000" "kkt_adapters" "KKT Adapter"
check_port "9090" "monitoring_servers" "Prometheus"
check_port "3000" "monitoring_servers" "Grafana"
check_port "80" "odoo_servers" "Nginx HTTP"

echo ""

# Docker containers
echo "Docker Containers:"
echo -n "Checking Prometheus... "
if ansible monitoring_servers -i "$INVENTORY_FILE" -m shell \
    -a "docker ps | grep -q prometheus" --become-user deploy &> /dev/null; then
    echo -e "${GREEN}✓ RUNNING${NC}"
else
    echo -e "${YELLOW}⚠ NOT RUNNING${NC}"
fi

echo -n "Checking Grafana... "
if ansible monitoring_servers -i "$INVENTORY_FILE" -m shell \
    -a "docker ps | grep -q grafana" --become-user deploy &> /dev/null; then
    echo -e "${GREEN}✓ RUNNING${NC}"
else
    echo -e "${YELLOW}⚠ NOT RUNNING${NC}"
fi

echo ""

# Database connectivity
echo "Database Connectivity:"
echo -n "Checking PostgreSQL connection... "
if ansible db_servers -i "$INVENTORY_FILE" -m shell \
    -a "sudo -u postgres psql -c 'SELECT 1' &> /dev/null" --become &> /dev/null; then
    echo -e "${GREEN}✓ OK${NC}"
else
    echo -e "${RED}✗ FAILED${NC}"
    FAILED_CHECKS=$((FAILED_CHECKS + 1))
fi

echo -n "Checking Redis connection... "
if ansible db_servers -i "$INVENTORY_FILE" -m shell \
    -a "redis-cli ping | grep -q PONG" --become &> /dev/null; then
    echo -e "${GREEN}✓ OK${NC}"
else
    echo -e "${RED}✗ FAILED${NC}"
    FAILED_CHECKS=$((FAILED_CHECKS + 1))
fi

echo ""

# NTP sync
echo "Time Synchronization:"
ansible all -i "$INVENTORY_FILE" -m shell \
    -a "chronyc tracking | grep 'System time'" --become | \
    grep -E "System time.*seconds" || echo -e "${YELLOW}⚠ Check chrony status${NC}"

echo ""

# Summary
echo "=========================================="
if [ $FAILED_CHECKS -eq 0 ]; then
    echo -e "${GREEN}✓ ALL CHECKS PASSED${NC}"
    echo "=========================================="
    echo ""
    echo "System is healthy and ready for use!"
    exit 0
else
    echo -e "${RED}✗ $FAILED_CHECKS CHECK(S) FAILED${NC}"
    echo "=========================================="
    echo ""
    echo "Please investigate failed checks above"
    echo "Check logs: journalctl -u <service> -n 50"
    exit 1
fi
