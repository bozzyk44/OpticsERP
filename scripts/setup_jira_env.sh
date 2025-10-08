#!/bin/bash
# JIRA Environment Setup Script
#
# Author: AI Agent
# Created: 2025-10-08
# Purpose: Configure JIRA API credentials for scripts

echo "🔧 JIRA API Configuration Setup"
echo "================================"
echo ""

# Step 1: Get Atlassian domain
read -p "Enter your Atlassian domain (e.g., your-company): " DOMAIN
export JIRA_URL="https://${DOMAIN}.atlassian.net"

# Step 2: Get email
read -p "Enter your Atlassian email [bozzyk44@gmail.com]: " EMAIL
EMAIL=${EMAIL:-bozzyk44@gmail.com}
export JIRA_EMAIL="$EMAIL"

# Step 3: Get API token
echo ""
echo "📝 Create API token:"
echo "   1. Open: https://id.atlassian.com/manage-profile/security/api-tokens"
echo "   2. Click 'Create API token'"
echo "   3. Label: 'Claude Code MCP'"
echo "   4. Copy the token"
echo ""
read -sp "Paste your API token: " API_TOKEN
echo ""
export JIRA_API_TOKEN="$API_TOKEN"

# Step 4: Get project key
read -p "Enter JIRA project key [OPTICS]: " PROJECT_KEY
PROJECT_KEY=${PROJECT_KEY:-OPTICS}
export JIRA_PROJECT_KEY="$PROJECT_KEY"

# Step 5: Save to .env file
ENV_FILE="$(dirname "$0")/../.env"
cat > "$ENV_FILE" << EOF
# JIRA API Configuration
# Generated: $(date)

export JIRA_URL="${JIRA_URL}"
export JIRA_EMAIL="${JIRA_EMAIL}"
export JIRA_API_TOKEN="${JIRA_API_TOKEN}"
export JIRA_PROJECT_KEY="${JIRA_PROJECT_KEY}"
EOF

echo ""
echo "✅ Configuration saved to: $ENV_FILE"
echo ""
echo "📋 Summary:"
echo "   JIRA URL:     $JIRA_URL"
echo "   Email:        $JIRA_EMAIL"
echo "   Project Key:  $JIRA_PROJECT_KEY"
echo "   API Token:    [hidden]"
echo ""
echo "🚀 Next steps:"
echo "   1. Source the environment:"
echo "      source $ENV_FILE"
echo ""
echo "   2. Test connection:"
echo "      python scripts/jira_create_test_issue.py"
echo ""
