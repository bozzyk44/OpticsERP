#!/usr/bin/env python3
"""
JIRA Issue Creation Script
Usage: python scripts/jira_create_issue.py

Reads issue details from JSON file or stdin
Requires: .env file with JIRA credentials
"""

import os
import sys
import json
import requests
from pathlib import Path


def load_env():
    """Load environment variables from .env file"""
    env_file = Path(__file__).parent.parent / '.env'

    if not env_file.exists():
        print("❌ Error: .env file not found")
        sys.exit(1)

    env_vars = {}
    with open(env_file, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                # Remove 'export ' prefix if present
                line = line.replace('export ', '')
                key, value = line.split('=', 1)
                # Remove quotes
                value = value.strip('"').strip("'")
                env_vars[key] = value

    return env_vars


def create_jira_issue(env_vars, issue_data):
    """Create JIRA issue via REST API"""

    jira_url = env_vars.get('JIRA_URL')
    jira_email = env_vars.get('JIRA_EMAIL')
    jira_token = env_vars.get('JIRA_API_TOKEN')

    if not all([jira_url, jira_email, jira_token]):
        print("❌ Error: Missing JIRA credentials in .env")
        print("Required: JIRA_URL, JIRA_EMAIL, JIRA_API_TOKEN")
        sys.exit(1)

    print("🔄 Creating JIRA issue...")

    url = f"{jira_url}/rest/api/3/issue"
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }
    auth = (jira_email, jira_token)

    try:
        response = requests.post(
            url,
            headers=headers,
            auth=auth,
            json=issue_data,
            timeout=30
        )

        if response.status_code == 201:
            result = response.json()
            issue_key = result.get('key')
            issue_url = f"{jira_url}/browse/{issue_key}"

            print(f"✅ Issue created successfully!")
            print(f"Key: {issue_key}")
            print(f"URL: {issue_url}")

            return issue_key
        else:
            print(f"❌ Failed to create issue")
            print(f"Status Code: {response.status_code}")
            print(f"Response: {response.text}")
            sys.exit(1)

    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")
        sys.exit(1)


def add_comment(env_vars, issue_key, comment_text):
    """Add comment to JIRA issue"""

    jira_url = env_vars.get('JIRA_URL')
    jira_email = env_vars.get('JIRA_EMAIL')
    jira_token = env_vars.get('JIRA_API_TOKEN')

    print(f"💬 Adding comment to {issue_key}...")

    url = f"{jira_url}/rest/api/3/issue/{issue_key}/comment"
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }
    auth = (jira_email, jira_token)

    comment_payload = {
        "body": {
            "type": "doc",
            "version": 1,
            "content": [
                {
                    "type": "paragraph",
                    "content": [
                        {
                            "type": "text",
                            "text": comment_text
                        }
                    ]
                }
            ]
        }
    }

    try:
        response = requests.post(
            url,
            headers=headers,
            auth=auth,
            json=comment_payload,
            timeout=30
        )

        if response.status_code == 201:
            print(f"✅ Comment added successfully")
            return True
        else:
            print(f"❌ Failed to add comment: {response.status_code}")
            return False

    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")
        return False


def main():
    # Load environment variables
    env_vars = load_env()

    # Read JSON payload
    if len(sys.argv) > 1:
        # From file argument
        with open(sys.argv[1], 'r') as f:
            issue_data = json.load(f)
    else:
        # From stdin
        print("📥 Reading JSON payload from stdin...")
        issue_data = json.load(sys.stdin)

    # Create issue
    issue_key = create_jira_issue(env_vars, issue_data)

    # Add completion comment if this is OPTERP-31
    if issue_data['fields']['summary'] == 'Setup Test Infrastructure Automation':
        comment = """✅ Задача выполнена

**Выполнено:**
- [x] pytest.ini created with 6 markers
- [x] tests/conftest.py created with 8 fixtures
- [x] Makefile created with 9 commands
- [x] docker-compose.test.yml created with Redis service
- [x] All 3 POC tests updated to use shared fixtures
- [x] make test-all works without manual infrastructure startup
- [ ] Test execution time <2 min (pytest-xdist not installed - Phase 2)
- [x] Documentation updated

**Файлы:**
- Created: pytest.ini, tests/conftest.py, docker-compose.test.yml, Makefile
- Created: docs/TEST_INFRASTRUCTURE_PLAN.md, docs/task_plans/20251009_OPTERP-31_test_infrastructure.md
- Modified: tests/poc/test_poc_1_emulator.py, test_poc_4_offline.py, test_poc_5_splitbrain.py

**Commit:** [1dfd534](https://github.com/bozzyk44/OpticsERP/commit/1dfd534)
**Task Plan:** docs/task_plans/20251009_OPTERP-31_test_infrastructure.md

**Тесты:** Ready to run with `make test-all`

🤖 Generated with [Claude Code](https://claude.com/claude-code)"""

        add_comment(env_vars, issue_key, comment)


if __name__ == '__main__':
    main()
