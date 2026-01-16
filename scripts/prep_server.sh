#!/bin/bash
# ==============================================
# OpticsERP Server Preparation Script
# ==============================================
# Prepares Ubuntu server for OpticsERP deployment
# Tested on: Ubuntu 20.04 LTS, 22.04 LTS
#
# Usage: sudo bash prep_server.sh
#
# What this script does:
# 1. Updates system packages
# 2. Installs Docker Engine
# 3. Installs Docker Compose
# 4. Installs common utilities
# 5. Configures user permissions
# 6. Verifies installation
#
# Last Updated: 2025-11-30
# ==============================================

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_root() {
    if [ "$EUID" -ne 0 ]; then
        log_error "This script must be run as root (use sudo)"
        exit 1
    fi
}

check_ubuntu() {
    if [ ! -f /etc/os-release ]; then
        log_error "Cannot detect OS. This script is for Ubuntu only."
        exit 1
    fi

    . /etc/os-release
    if [ "$ID" != "ubuntu" ]; then
        log_error "This script is designed for Ubuntu. Detected: $ID"
        exit 1
    fi

    log_info "Detected Ubuntu $VERSION_ID"
}

update_system() {
    log_info "Updating system packages..."
    apt update -qq
    apt upgrade -y -qq
    log_info "✅ System updated"
}

install_prerequisites() {
    log_info "Installing prerequisites..."
    apt install -y -qq \
        apt-transport-https \
        ca-certificates \
        curl \
        gnupg \
        lsb-release \
        git \
        htop \
        net-tools \
        vim \
        wget \
        unzip \
        software-properties-common

    log_info "✅ Prerequisites installed"
}

install_docker() {
    if command -v docker &> /dev/null; then
        log_warn "Docker is already installed ($(docker --version))"
        return 0
    fi

    log_info "Installing Docker Engine..."

    # Add Docker's official GPG key
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg

    # Set up the stable repository
    echo \
      "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu \
      $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null

    # Install Docker Engine
    apt update -qq
    apt install -y -qq docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

    # Start and enable Docker
    systemctl start docker
    systemctl enable docker

    log_info "✅ Docker Engine installed: $(docker --version)"
}

install_docker_compose() {
    if command -v docker-compose &> /dev/null; then
        log_warn "Docker Compose is already installed ($(docker-compose --version))"
        return 0
    fi

    log_info "Installing Docker Compose (standalone)..."

    # Get latest version
    COMPOSE_VERSION=$(curl -s https://api.github.com/repos/docker/compose/releases/latest | grep 'tag_name' | cut -d\" -f4)

    # Download and install
    curl -L "https://github.com/docker/compose/releases/download/${COMPOSE_VERSION}/docker-compose-$(uname -s)-$(uname -m)" \
        -o /usr/local/bin/docker-compose

    chmod +x /usr/local/bin/docker-compose

    log_info "✅ Docker Compose installed: $(docker-compose --version)"
}

configure_user() {
    # Get the original user (who ran sudo)
    ORIGINAL_USER=${SUDO_USER:-$USER}

    if [ "$ORIGINAL_USER" == "root" ]; then
        log_warn "Running as root. Skipping user configuration."
        return 0
    fi

    log_info "Configuring user permissions for: $ORIGINAL_USER"

    # Add user to docker group
    usermod -aG docker $ORIGINAL_USER

    log_info "✅ User added to docker group"
    log_warn "Please log out and log back in for group changes to take effect"
}

verify_installation() {
    log_info "Verifying installation..."

    # Check Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker installation failed"
        return 1
    fi
    echo "   Docker: $(docker --version)"

    # Check Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose installation failed"
        return 1
    fi
    echo "   Docker Compose: $(docker-compose --version)"

    # Check Docker service
    if ! systemctl is-active --quiet docker; then
        log_error "Docker service is not running"
        return 1
    fi
    echo "   Docker Service: Active"

    # Check Git
    if ! command -v git &> /dev/null; then
        log_error "Git installation failed"
        return 1
    fi
    echo "   Git: $(git --version)"

    log_info "✅ All checks passed!"
}

print_next_steps() {
    echo ""
    echo "=========================================="
    echo "  OpticsERP Server Preparation Complete!"
    echo "=========================================="
    echo ""
    echo "✅ Docker Engine installed"
    echo "✅ Docker Compose installed"
    echo "✅ Prerequisites installed"
    echo ""
    echo "Next Steps:"
    echo "1. Log out and log back in (for docker group changes)"
    echo "2. Clone OpticsERP repository:"
    echo "   git clone https://github.com/bozzyk44/OpticsERP.git"
    echo "3. Follow installation guide:"
    echo "   cd OpticsERP"
    echo "   cat docs/installation/02_installation_steps.md"
    echo ""
    echo "For detailed instructions, see:"
    echo "   docs/installation/00_README.md"
    echo ""
}

# Main execution
main() {
    echo "=========================================="
    echo "  OpticsERP Server Preparation Script"
    echo "=========================================="
    echo ""

    check_root
    check_ubuntu
    update_system
    install_prerequisites
    install_docker
    install_docker_compose
    configure_user
    verify_installation
    print_next_steps
}

# Run main function
main
