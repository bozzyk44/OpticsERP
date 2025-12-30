#!/bin/bash
# Ansible installation check and setup script
# Usage: ./install_ansible.sh

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

REQUIRED_ANSIBLE_VERSION="2.12"

echo "=========================================="
echo "  Ansible Installation Check"
echo "=========================================="
echo ""

# Function to compare versions
version_gt() {
    test "$(printf '%s\n' "$@" | sort -V | head -n 1)" != "$1"
}

# Check if Ansible is installed
if command -v ansible &> /dev/null; then
    ANSIBLE_VERSION=$(ansible --version | head -n1 | awk '{print $2}')
    echo -e "${GREEN}✓${NC} Ansible is installed: version ${ANSIBLE_VERSION}"

    # Check if version is sufficient
    if version_gt $REQUIRED_ANSIBLE_VERSION $ANSIBLE_VERSION; then
        echo -e "${YELLOW}⚠${NC} Ansible version ${ANSIBLE_VERSION} is older than recommended ${REQUIRED_ANSIBLE_VERSION}"
        echo -e "${YELLOW}⚠${NC} Consider upgrading: pip install --upgrade ansible"
    else
        echo -e "${GREEN}✓${NC} Ansible version is sufficient (>= ${REQUIRED_ANSIBLE_VERSION})"
    fi
else
    echo -e "${RED}✗${NC} Ansible is not installed"
    echo ""
    echo "Would you like to install Ansible now? (y/n)"
    read -r response

    if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
        echo ""
        echo "Installing Ansible..."

        # Detect OS
        if [[ "$OSTYPE" == "linux-gnu"* ]]; then
            # Linux
            if command -v apt-get &> /dev/null; then
                # Debian/Ubuntu
                echo "Detected Debian/Ubuntu system"
                sudo apt-get update
                sudo apt-get install -y software-properties-common
                sudo apt-add-repository --yes --update ppa:ansible/ansible
                sudo apt-get install -y ansible
            elif command -v yum &> /dev/null; then
                # RHEL/CentOS
                echo "Detected RHEL/CentOS system"
                sudo yum install -y epel-release
                sudo yum install -y ansible
            else
                echo -e "${RED}✗${NC} Unsupported Linux distribution"
                echo "Please install Ansible manually: https://docs.ansible.com/ansible/latest/installation_guide/intro_installation.html"
                exit 1
            fi
        elif [[ "$OSTYPE" == "darwin"* ]]; then
            # macOS
            echo "Detected macOS system"
            if command -v brew &> /dev/null; then
                brew install ansible
            else
                echo -e "${YELLOW}⚠${NC} Homebrew not found. Installing via pip..."
                pip3 install ansible
            fi
        elif [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "cygwin" ]]; then
            # Windows (Git Bash / Cygwin)
            echo "Detected Windows system"
            echo "Installing via pip..."
            pip install ansible
        else
            echo -e "${RED}✗${NC} Unsupported operating system: $OSTYPE"
            echo "Please install Ansible manually: https://docs.ansible.com/ansible/latest/installation_guide/intro_installation.html"
            exit 1
        fi

        echo ""
        echo -e "${GREEN}✓${NC} Ansible installed successfully!"
        ansible --version
    else
        echo -e "${RED}✗${NC} Ansible installation cancelled"
        exit 1
    fi
fi

echo ""
echo "=========================================="
echo "  Checking Ansible Collections"
echo "=========================================="
echo ""

# Required collections
COLLECTIONS=(
    "community.docker"
    "community.postgresql"
)

for collection in "${COLLECTIONS[@]}"; do
    if ansible-galaxy collection list | grep -q "$collection"; then
        echo -e "${GREEN}✓${NC} Collection installed: $collection"
    else
        echo -e "${YELLOW}⚠${NC} Installing collection: $collection"
        ansible-galaxy collection install "$collection"
    fi
done

echo ""
echo "=========================================="
echo "  Python Dependencies Check"
echo "=========================================="
echo ""

# Required Python packages for Ansible modules
PYTHON_PACKAGES=(
    "docker"
    "psycopg2-binary"
)

for package in "${PYTHON_PACKAGES[@]}"; do
    if python3 -c "import ${package//-/_}" &> /dev/null; then
        echo -e "${GREEN}✓${NC} Python package installed: $package"
    else
        echo -e "${YELLOW}⚠${NC} Installing Python package: $package"
        pip3 install "$package" || pip install "$package"
    fi
done

echo ""
echo "=========================================="
echo "  Installation Summary"
echo "=========================================="
echo ""

ansible --version | head -n 5
echo ""
echo -e "${GREEN}✓${NC} Ansible setup complete!"
echo ""
echo "Next steps:"
echo "  1. Configure inventory: ansible/inventories/production/hosts.yml"
echo "  2. Setup secrets: cp ansible/.env.example ansible/.env"
echo "  3. Run deployment: ./ansible/scripts/deploy.sh"
echo ""
