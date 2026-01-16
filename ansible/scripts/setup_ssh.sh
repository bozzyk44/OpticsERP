#!/bin/bash
# SSH setup script for OpticsERP deployment
# Usage: ./setup_ssh.sh [server_ip] [username]

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

SERVER_IP="${1:-194.87.235.33}"
USERNAME="${2:-bozzyk44}"
SSH_KEY_PATH="$HOME/.ssh/opticserp"

echo ""
echo "=========================================="
echo "  SSH Setup for OpticsERP"
echo "=========================================="
echo ""
echo "Server: $USERNAME@$SERVER_IP"
echo "SSH Key: $SSH_KEY_PATH"
echo ""

# Step 1: Check if key exists
if [ -f "$SSH_KEY_PATH" ]; then
    echo -e "${GREEN}✓${NC} SSH key already exists: $SSH_KEY_PATH"
else
    echo -e "${YELLOW}⚠${NC} SSH key not found: $SSH_KEY_PATH"
    echo ""
    echo "Options:"
    echo "  1. Create new key: $SSH_KEY_PATH"
    echo "  2. Use existing key: $HOME/.ssh/id_rsa"
    echo "  3. Exit and update inventory file"
    echo ""
    read -p "Choose option (1/2/3): " option

    case $option in
        1)
            echo ""
            echo "Creating new SSH key..."
            ssh-keygen -t rsa -b 4096 -f "$SSH_KEY_PATH" -N "" -C "opticserp-deployment"
            echo -e "${GREEN}✓${NC} SSH key created: $SSH_KEY_PATH"
            ;;
        2)
            echo ""
            echo "Using existing key: $HOME/.ssh/id_rsa"
            echo "Update inventory file:"
            echo "  ansible_ssh_private_key_file: ~/.ssh/id_rsa"
            SSH_KEY_PATH="$HOME/.ssh/id_rsa"
            ;;
        3)
            echo "Exiting..."
            exit 0
            ;;
        *)
            echo -e "${RED}✗${NC} Invalid option"
            exit 1
            ;;
    esac
fi

# Step 2: Copy public key to server
echo ""
echo "=========================================="
echo "  Copying SSH key to server"
echo "=========================================="
echo ""

if [ -f "${SSH_KEY_PATH}.pub" ]; then
    echo "Public key: ${SSH_KEY_PATH}.pub"
    echo ""
    echo "Copying to $USERNAME@$SERVER_IP..."
    echo "You will be prompted for your password:"
    echo ""

    if ssh-copy-id -i "${SSH_KEY_PATH}.pub" "$USERNAME@$SERVER_IP"; then
        echo ""
        echo -e "${GREEN}✓${NC} SSH key copied successfully"
    else
        echo ""
        echo -e "${RED}✗${NC} Failed to copy SSH key"
        echo ""
        echo "Manual setup:"
        echo "  1. Copy public key:"
        echo "     cat ${SSH_KEY_PATH}.pub"
        echo "  2. Login to server and add to authorized_keys:"
        echo "     ssh $USERNAME@$SERVER_IP"
        echo "     mkdir -p ~/.ssh"
        echo "     echo 'YOUR_PUBLIC_KEY' >> ~/.ssh/authorized_keys"
        echo "     chmod 700 ~/.ssh"
        echo "     chmod 600 ~/.ssh/authorized_keys"
        exit 1
    fi
else
    echo -e "${RED}✗${NC} Public key not found: ${SSH_KEY_PATH}.pub"
    exit 1
fi

# Step 3: Test SSH connection
echo ""
echo "=========================================="
echo "  Testing SSH connection"
echo "=========================================="
echo ""

if ssh -i "$SSH_KEY_PATH" -o BatchMode=yes -o ConnectTimeout=5 "$USERNAME@$SERVER_IP" "echo 'Connection successful'" 2>/dev/null; then
    echo -e "${GREEN}✓${NC} SSH connection successful!"
else
    echo -e "${YELLOW}⚠${NC} SSH connection test failed"
    echo ""
    echo "Try manual connection:"
    echo "  ssh -i $SSH_KEY_PATH $USERNAME@$SERVER_IP"
    echo ""
    echo "If it works manually, check:"
    echo "  1. SSH agent is running: eval \$(ssh-agent)"
    echo "  2. Key is added: ssh-add $SSH_KEY_PATH"
fi

# Step 4: Check sudo permissions
echo ""
echo "=========================================="
echo "  Checking sudo permissions"
echo "=========================================="
echo ""

echo "Testing sudo access on server..."
if ssh -i "$SSH_KEY_PATH" "$USERNAME@$SERVER_IP" "sudo -n true" 2>/dev/null; then
    echo -e "${GREEN}✓${NC} Passwordless sudo is configured"
else
    echo -e "${YELLOW}⚠${NC} Passwordless sudo is NOT configured"
    echo ""
    echo "To enable passwordless sudo on the server:"
    echo "  1. Login: ssh -i $SSH_KEY_PATH $USERNAME@$SERVER_IP"
    echo "  2. Run: sudo visudo"
    echo "  3. Add line: $USERNAME ALL=(ALL) NOPASSWD:ALL"
    echo "  4. Save and exit"
    echo ""
    echo "Or run Ansible with --ask-become-pass flag"
fi

# Summary
echo ""
echo "=========================================="
echo "  Setup Summary"
echo "=========================================="
echo ""
echo "SSH Key: $SSH_KEY_PATH"
echo "Server: $USERNAME@$SERVER_IP"
echo ""
echo "Next steps:"
echo "  1. Verify inventory: ansible/inventories/production/hosts.yml"
echo "  2. Run deployment: ./deploy-wrapper.sh production"
echo ""
