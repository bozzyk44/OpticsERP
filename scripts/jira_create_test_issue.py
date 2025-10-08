#!/usr/bin/env python3
"""
JIRA Test Issue Creator

Author: AI Agent
Created: 2025-10-08
Purpose: Create a test issue in JIRA via REST API to verify connectivity
"""

import os
import sys
import json
import requests
from requests.auth import HTTPBasicAuth

# Configuration
JIRA_URL = os.getenv("JIRA_URL", "https://your-domain.atlassian.net")
JIRA_EMAIL = os.getenv("JIRA_EMAIL", "bozzyk44@gmail.com")
JIRA_API_TOKEN = os.getenv("JIRA_API_TOKEN")
PROJECT_KEY = os.getenv("JIRA_PROJECT_KEY", "OPTICS")


def create_test_issue():
    """Create a test issue in JIRA"""

    if not JIRA_API_TOKEN:
        print("❌ Error: JIRA_API_TOKEN environment variable not set")
        print("\nSetup:")
        print("1. Create API token: https://id.atlassian.com/manage-profile/security/api-tokens")
        print("2. Export environment variables:")
        print(f'   export JIRA_API_TOKEN="your_token_here"')
        print(f'   export JIRA_URL="https://your-domain.atlassian.net"')
        print(f'   export JIRA_EMAIL="{JIRA_EMAIL}"')
        return False

    # API endpoint
    url = f"{JIRA_URL}/rest/api/3/issue"

    # Authentication
    auth = HTTPBasicAuth(JIRA_EMAIL, JIRA_API_TOKEN)

    # Headers
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json"
    }

    # Issue data
    payload = {
        "fields": {
            "project": {
                "key": PROJECT_KEY
            },
            "summary": "🧪 Test Issue - JIRA Integration Verification",
            "description": {
                "type": "doc",
                "version": 1,
                "content": [
                    {
                        "type": "paragraph",
                        "content": [
                            {
                                "type": "text",
                                "text": "This is a test issue created via JIRA REST API to verify integration."
                            }
                        ]
                    },
                    {
                        "type": "heading",
                        "attrs": {"level": 2},
                        "content": [
                            {
                                "type": "text",
                                "text": "Purpose"
                            }
                        ]
                    },
                    {
                        "type": "paragraph",
                        "content": [
                            {
                                "type": "text",
                                "text": "Verify JIRA API connectivity and issue creation functionality."
                            }
                        ]
                    },
                    {
                        "type": "heading",
                        "attrs": {"level": 2},
                        "content": [
                            {
                                "type": "text",
                                "text": "Test Details"
                            }
                        ]
                    },
                    {
                        "type": "bulletList",
                        "content": [
                            {
                                "type": "listItem",
                                "content": [
                                    {
                                        "type": "paragraph",
                                        "content": [
                                            {
                                                "type": "text",
                                                "text": "Project: OpticsERP"
                                            }
                                        ]
                                    }
                                ]
                            },
                            {
                                "type": "listItem",
                                "content": [
                                    {
                                        "type": "paragraph",
                                        "content": [
                                            {
                                                "type": "text",
                                                "text": "Created via: REST API"
                                            }
                                        ]
                                    }
                                ]
                            },
                            {
                                "type": "listItem",
                                "content": [
                                    {
                                        "type": "paragraph",
                                        "content": [
                                            {
                                                "type": "text",
                                                "text": "Authentication: API Token"
                                            }
                                        ]
                                    }
                                ]
                            }
                        ]
                    }
                ]
            },
            "issuetype": {
                "name": "Task"
            },
            "priority": {
                "name": "Medium"
            },
            "labels": [
                "test",
                "api",
                "integration"
            ]
        }
    }

    print(f"📡 Connecting to JIRA: {JIRA_URL}")
    print(f"📧 Email: {JIRA_EMAIL}")
    print(f"📁 Project: {PROJECT_KEY}")
    print(f"🔧 Creating test issue...")

    try:
        response = requests.post(url, auth=auth, headers=headers, json=payload, timeout=10)

        if response.status_code == 201:
            issue_data = response.json()
            issue_key = issue_data.get("key")
            issue_id = issue_data.get("id")
            issue_url = f"{JIRA_URL}/browse/{issue_key}"

            print(f"\n✅ Success! Test issue created:")
            print(f"   Key: {issue_key}")
            print(f"   ID: {issue_id}")
            print(f"   URL: {issue_url}")
            print(f"\n🌐 Open in browser: {issue_url}")

            return True
        else:
            print(f"\n❌ Error {response.status_code}: {response.reason}")
            print(f"Response: {response.text}")

            if response.status_code == 401:
                print("\n💡 Hint: Check your API token and email")
            elif response.status_code == 404:
                print(f"\n💡 Hint: Project '{PROJECT_KEY}' not found. Check project key.")
            elif response.status_code == 400:
                error_detail = response.json()
                print(f"\n💡 Hint: {json.dumps(error_detail, indent=2)}")

            return False

    except requests.exceptions.Timeout:
        print("\n❌ Timeout: Could not connect to JIRA")
        return False
    except requests.exceptions.ConnectionError:
        print(f"\n❌ Connection Error: Could not reach {JIRA_URL}")
        return False
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        return False


if __name__ == "__main__":
    success = create_test_issue()
    sys.exit(0 if success else 1)
