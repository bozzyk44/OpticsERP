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

# Check and install Python packages needed for Ansible modules
check_and_install_python_package() {
    local package=$1
    local import_name=${package//-/_}
    local apt_package=$2

    if python3 -c "import ${import_name}" &> /dev/null; then
        echo -e "${GREEN}✓${NC} Python package installed: $package"
        return 0
    fi

    echo -e "${YELLOW}⚠${NC} Installing Python package: $package"

    # Try apt first (Debian/Ubuntu with PEP 668)
    if [[ "$OSTYPE" == "linux-gnu"* ]] && command -v apt-get &> /dev/null; then
        if [ -n "$apt_package" ]; then
            echo "  → Trying apt install $apt_package..."
            if sudo apt-get install -y "$apt_package" &> /dev/null; then
                echo -e "${GREEN}✓${NC} Installed via apt: $apt_package"
                return 0
            fi
        fi
    fi

    # Try pip with --break-system-packages (for PEP 668 systems)
    echo "  → Trying pip install..."
    if pip3 install "$package" --break-system-packages &> /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC} Installed via pip: $package"
        return 0
    elif pip3 install "$package" &> /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC} Installed via pip: $package"
        return 0
    elif pip install "$package" &> /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC} Installed via pip: $package"
        return 0
    fi

    echo -e "${YELLOW}⚠${NC} Could not install $package automatically"
    echo "  Please install manually:"
    if [ -n "$apt_package" ]; then
        echo "    sudo apt install $apt_package"
    fi
    echo "    OR: pip3 install $package --break-system-packages"
    return 1
}

# Required Python packages for Ansible modules
# Format: "pip_package apt_package"
check_and_install_python_package "docker" "python3-docker"
check_and_install_python_package "psycopg2" "python3-psycopg2"

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
