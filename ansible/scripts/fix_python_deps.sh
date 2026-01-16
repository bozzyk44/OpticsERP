#!/bin/bash
# Quick fix for Python dependencies on PEP 668 systems (Ubuntu 23.04+, Debian 12+)
# Usage: ./fix_python_deps.sh

set -e

echo "=========================================="
echo "  Python Dependencies Fix"
echo "=========================================="
echo ""
echo "This script will install Python packages needed for Ansible"
echo "on systems with PEP 668 (externally-managed-environment)"
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Method 1: Install via apt (recommended for Debian/Ubuntu)
echo "Method 1: Installing via apt..."
sudo apt-get update
sudo apt-get install -y python3-docker python3-psycopg2

echo ""
echo -e "${GREEN}✓${NC} Python dependencies installed via apt"
echo ""

# Verify installation
echo "Verifying installation..."
if python3 -c "import docker" 2>/dev/null; then
    echo -e "${GREEN}✓${NC} docker module: OK"
else
    echo -e "${YELLOW}⚠${NC} docker module: Not found"
fi

if python3 -c "import psycopg2" 2>/dev/null; then
    echo -e "${GREEN}✓${NC} psycopg2 module: OK"
else
    echo -e "${YELLOW}⚠${NC} psycopg2 module: Not found"
fi

echo ""
echo "=========================================="
echo "  Installation Complete"
echo "=========================================="
echo ""
echo "You can now run: ./deploy-wrapper.sh production"
echo ""
