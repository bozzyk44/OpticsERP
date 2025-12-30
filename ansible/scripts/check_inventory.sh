#!/bin/bash
# Inventory validation script
# Usage: ./check_inventory.sh [environment]

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
echo "  Inventory Validation"
echo "=========================================="
echo ""
echo "Environment: $ENVIRONMENT"
echo "File: $INVENTORY_FILE"
echo ""

# Check if file exists
if [ ! -f "$INVENTORY_FILE" ]; then
    echo -e "${RED}✗${NC} Inventory file not found!"
    echo ""
    echo "Create it from template:"
    echo "  cp $ANSIBLE_DIR/inventories/$ENVIRONMENT/hosts.yml.example \\"
    echo "     $INVENTORY_FILE"
    exit 1
fi
echo -e "${GREEN}✓${NC} Inventory file exists"

# Check for placeholder IPs
if grep -q "YOUR_SERVER_IP_HERE\|YOUR_.*_IP_HERE\|192.168.1.10" "$INVENTORY_FILE"; then
    echo -e "${YELLOW}⚠${NC} Found placeholder IP addresses in inventory!"
    echo ""
    echo "Please replace placeholder IPs with real server addresses:"
    grep -n "YOUR_.*_IP_HERE\|192.168.1.10" "$INVENTORY_FILE" || true
    echo ""
    echo -e "${YELLOW}⚠${NC} Edit $INVENTORY_FILE before deployment"
else
    echo -e "${GREEN}✓${NC} No placeholder IPs found"
fi

# List all hosts
echo ""
echo "Configured hosts:"
ansible all -i "$INVENTORY_FILE" --list-hosts

# Test SSH connectivity
echo ""
echo "Testing SSH connectivity..."
if ansible all -i "$INVENTORY_FILE" -m ping -o; then
    echo ""
    echo -e "${GREEN}✓${NC} All hosts are reachable"
else
    echo ""
    echo -e "${RED}✗${NC} Some hosts are unreachable!"
    echo ""
    echo "Troubleshooting:"
    echo "  1. Check SSH key is added: ssh-copy-id user@host"
    echo "  2. Test manually: ssh user@host"
    echo "  3. Check firewall allows SSH"
    echo "  4. Verify ansible_user in inventory"
    exit 1
fi

# Check system info
echo ""
echo "=========================================="
echo "  Server Information"
echo "=========================================="
echo ""

ansible all -i "$INVENTORY_FILE" -m setup \
    -a "filter=ansible_distribution,ansible_distribution_version,ansible_memtotal_mb,ansible_processor_vcpus" \
    --become || true

echo ""
echo -e "${GREEN}✓${NC} Inventory validation complete"
echo ""
