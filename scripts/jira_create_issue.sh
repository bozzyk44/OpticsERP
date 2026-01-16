#!/bin/bash
# JIRA Issue Creation Script
# Usage: ./scripts/jira_create_issue.sh
#
# Reads issue details from stdin (JSON format)
# Requires: .env file with JIRA credentials

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Load environment variables
if [ -f .env ]; then
    source .env
else
    echo -e "${RED}Error: .env file not found${NC}"
    exit 1
fi

# Validate required variables
if [ -z "$JIRA_URL" ] || [ -z "$JIRA_EMAIL" ] || [ -z "$JIRA_API_TOKEN" ]; then
    echo -e "${RED}Error: Missing JIRA credentials in .env${NC}"
    echo "Required: JIRA_URL, JIRA_EMAIL, JIRA_API_TOKEN"
    exit 1
fi

# Function to create issue
create_issue() {
    local json_payload="$1"

    echo -e "${YELLOW}Creating JIRA issue...${NC}"

    response=$(curl -s -w "\n%{http_code}" -X POST \
        -H "Content-Type: application/json" \
        -u "${JIRA_EMAIL}:${JIRA_API_TOKEN}" \
        -d "$json_payload" \
        "${JIRA_URL}/rest/api/3/issue")

    http_code=$(echo "$response" | tail -n 1)
    body=$(echo "$response" | sed '$d')

    if [ "$http_code" -eq 201 ]; then
        issue_key=$(echo "$body" | grep -o '"key":"[^"]*"' | cut -d'"' -f4)
        issue_url="${JIRA_URL}/browse/${issue_key}"

        echo -e "${GREEN}✅ Issue created successfully!${NC}"
        echo -e "Key: ${GREEN}${issue_key}${NC}"
        echo -e "URL: ${GREEN}${issue_url}${NC}"

        return 0
    else
        echo -e "${RED}❌ Failed to create issue${NC}"
        echo -e "HTTP Code: $http_code"
        echo -e "Response: $body"

        return 1
    fi
}

# Function to add comment to issue
add_comment() {
    local issue_key="$1"
    local comment_body="$2"

    echo -e "${YELLOW}Adding comment to ${issue_key}...${NC}"

    comment_payload=$(cat <<EOF
{
  "body": {
    "type": "doc",
    "version": 1,
    "content": [
      {
        "type": "paragraph",
        "content": [
          {
            "type": "text",
            "text": "$comment_body"
          }
        ]
      }
    ]
  }
}
EOF
)

    response=$(curl -s -w "\n%{http_code}" -X POST \
        -H "Content-Type: application/json" \
        -u "${JIRA_EMAIL}:${JIRA_API_TOKEN}" \
        -d "$comment_payload" \
        "${JIRA_URL}/rest/api/3/issue/${issue_key}/comment")

    http_code=$(echo "$response" | tail -n 1)

    if [ "$http_code" -eq 201 ]; then
        echo -e "${GREEN}✅ Comment added successfully${NC}"
        return 0
    else
        echo -e "${RED}❌ Failed to add comment${NC}"
        return 1
    fi
}

# Read JSON payload from stdin or argument
if [ -n "$1" ]; then
    json_payload="$1"
else
    echo -e "${YELLOW}Reading JSON payload from stdin...${NC}"
    json_payload=$(cat)
fi

# Create issue
create_issue "$json_payload"
