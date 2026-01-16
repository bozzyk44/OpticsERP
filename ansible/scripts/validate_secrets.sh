#!/bin/bash
# Secrets validation script
# Usage: ./validate_secrets.sh

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ANSIBLE_DIR="$(dirname "$SCRIPT_DIR")"
ENV_FILE="$ANSIBLE_DIR/.env"

echo ""
echo "=========================================="
echo "  Secrets Validation"
echo "=========================================="
echo ""

# Check if .env exists
if [ ! -f "$ENV_FILE" ]; then
    echo -e "${RED}✗${NC} .env file not found!"
    echo ""
    echo "Create it from template:"
    echo "  cp $ANSIBLE_DIR/.env.example $ENV_FILE"
    echo "  vim $ENV_FILE"
    exit 1
fi
echo -e "${GREEN}✓${NC} .env file exists"

# Fix line endings (Windows CRLF -> Unix LF) if needed
if file "$ENV_FILE" | grep -q "CRLF"; then
    echo -e "${YELLOW}⚠${NC} Converting .env from Windows (CRLF) to Unix (LF) format..."
    sed -i 's/\r$//' "$ENV_FILE"
    echo -e "${GREEN}✓${NC} Line endings fixed"
fi

# Load .env
# shellcheck disable=SC1090
source "$ENV_FILE"

# Required variables
REQUIRED_VARS=(
    "POSTGRES_PASSWORD"
    "REDIS_PASSWORD"
    "GRAFANA_PASSWORD"
    "ODOO_ADMIN_PASSWORD"
)

# Check each required variable
MISSING_VARS=0
WEAK_PASSWORDS=0

for var in "${REQUIRED_VARS[@]}"; do
    value="${!var}"

    if [ -z "$value" ]; then
        echo -e "${RED}✗${NC} $var is not set"
        MISSING_VARS=$((MISSING_VARS + 1))
    elif [ ${#value} -lt 8 ]; then
        echo -e "${YELLOW}⚠${NC} $var is too short (< 8 characters)"
        WEAK_PASSWORDS=$((WEAK_PASSWORDS + 1))
    elif [[ "$value" == *"your_"* ]] || [[ "$value" == *"changeme"* ]] || [[ "$value" == *"password"* ]]; then
        echo -e "${YELLOW}⚠${NC} $var looks like a placeholder or weak password"
        WEAK_PASSWORDS=$((WEAK_PASSWORDS + 1))
    else
        echo -e "${GREEN}✓${NC} $var is set (length: ${#value})"
    fi
done

echo ""

# Summary
if [ $MISSING_VARS -gt 0 ]; then
    echo -e "${RED}✗${NC} $MISSING_VARS required variable(s) missing!"
    echo "Please edit $ENV_FILE and set all required passwords"
    exit 1
fi

if [ $WEAK_PASSWORDS -gt 0 ]; then
    echo -e "${YELLOW}⚠${NC} $WEAK_PASSWORDS password(s) may be weak"
    echo ""
    echo "Recommendations for strong passwords:"
    echo "  - At least 12 characters"
    echo "  - Mix of uppercase, lowercase, numbers, symbols"
    echo "  - No dictionary words"
    echo "  - Use password manager to generate"
    echo ""
    echo "Continue anyway? (y/n)"
    read -r response
    if [[ ! "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
        exit 1
    fi
fi

echo -e "${GREEN}✓${NC} All required secrets are set"
echo ""
echo "Note: Secrets are loaded from $ENV_FILE"
echo "Make sure this file is in .gitignore!"
echo ""

# Check if .env is in .gitignore
if [ -f "$ANSIBLE_DIR/.gitignore" ]; then
    if grep -q "^\.env$" "$ANSIBLE_DIR/.gitignore"; then
        echo -e "${GREEN}✓${NC} .env is in .gitignore"
    else
        echo -e "${YELLOW}⚠${NC} .env is NOT in .gitignore!"
        echo "Add it to prevent committing secrets"
    fi
fi

echo ""
