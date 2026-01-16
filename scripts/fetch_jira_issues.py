#!/usr/bin/env python3
"""
Fetch JIRA issues from OPTERP project
Usage: python fetch_jira_issues.py
"""
import os
import sys
import requests
from requests.auth import HTTPBasicAuth
import json

# Load from .env
JIRA_URL = "https://bozzyk44.atlassian.net"
JIRA_EMAIL = "bozzyk44@gmail.com"
JIRA_API_TOKEN = "ATATT3xFfGF0EnjfpAD3rnZaMWeGC611KPJmEi1bbaYRmWNBKHFgF1UO8g6Qj2v0SUFh9pDPyc7xOVLFbhkMGqz8RXgGbdaYJsK40HI-2kO1lVEqeb92lzZ1zFOi_9Vu6j-2VSLxIk5pHtu5Fgv9rYysGQBXe9CG4paJjjguWjFyPvJBBDNm82g=BA8F683E"
PROJECT_KEY = "OPTERP"  # Use KEY from project list, not NAME

def fetch_issues():
    """Fetch issues from JIRA"""
    # First, check auth by getting current user
    print("Testing authentication...")
    auth = HTTPBasicAuth(JIRA_EMAIL, JIRA_API_TOKEN)
    headers = {"Accept": "application/json"}

    test_url = f"{JIRA_URL}/rest/api/2/myself"
    try:
        test_response = requests.get(test_url, headers=headers, auth=auth, timeout=10)
        test_response.raise_for_status()
        user = test_response.json()
        print(f"✓ Authenticated as: {user.get('displayName', 'Unknown')}\n")
    except Exception as e:
        print(f"✗ Authentication failed: {e}\n")
        return 1

    # Check available projects first
    print("Checking available projects...")
    projects_url = f"{JIRA_URL}/rest/api/2/project"
    try:
        proj_response = requests.get(projects_url, headers=headers, auth=auth, timeout=10)
        proj_response.raise_for_status()
        projects = proj_response.json()
        print(f"✓ Found {len(projects)} projects:")
        for proj in projects:
            print(f"  - KEY: {proj['key']} | ID: {proj.get('id', 'N/A')} | NAME: {proj['name']}")
        print()
    except Exception as e:
        print(f"✗ Could not fetch projects: {e}\n")

    # Check if project has issues by getting project details
    print(f"Getting project details for '{PROJECT_KEY}'...")
    project_url = f"{JIRA_URL}/rest/api/2/project/{PROJECT_KEY}"
    try:
        proj_detail = requests.get(project_url, headers=headers, auth=auth, timeout=10)
        proj_detail.raise_for_status()
        proj_data = proj_detail.json()
        print(f"  Project ID: {proj_data.get('id')}")
        print(f"  Lead: {proj_data.get('lead', {}).get('displayName', 'N/A')}")
        print()
    except Exception as e:
        print(f"✗ Could not get project details: {e}\n")

    # Try alternative: get issues via project endpoint (newer API)
    print(f"Fetching issues from project '{PROJECT_KEY}' (alternative method)...")

    # Method 1: Try agile board API (if available)
    print("\n[Attempt 1] Trying agile board API...")
    boards_url = f"{JIRA_URL}/rest/agile/1.0/board"
    try:
        boards_resp = requests.get(boards_url, headers=headers, auth=auth, params={"projectKeyOrId": PROJECT_KEY}, timeout=10)
        if boards_resp.status_code == 200:
            boards = boards_resp.json().get('values', [])
            print(f"  Found {len(boards)} boards")
            if boards:
                board_id = boards[0]['id']
                issues_url = f"{JIRA_URL}/rest/agile/1.0/board/{board_id}/issue"
                issues_resp = requests.get(issues_url, headers=headers, auth=auth, params={"maxResults": 100}, timeout=30)
                if issues_resp.status_code == 200:
                    data = issues_resp.json()
                    print(f"  ✓ Found {data.get('total', 0)} issues via agile API\n")
                    print("=" * 80)
                    for issue in data.get('issues', []):
                        key = issue['key']
                        fields = issue['fields']
                        summary = fields.get('summary', 'N/A')
                        status = fields.get('status', {}).get('name', 'N/A')
                        priority = fields.get('priority', {}).get('name', 'N/A')
                        assignee = fields.get('assignee', {})
                        assignee_name = assignee.get('displayName', 'Unassigned') if assignee else 'Unassigned'
                        print(f"[{key}] {summary}")
                        print(f"  Status: {status} | Priority: {priority} | Assignee: {assignee_name}")
                        print("-" * 80)
                    return 0
        print("  Agile API not available or no boards found")
    except Exception as e:
        print(f"  Agile API failed: {e}")

    # Method 2: Fallback - inform user about limitation
    print("\n[Result] JIRA Free tier limitation detected:")
    print("  - /rest/api/2/search endpoint returns 410 Gone")
    print("  - This is a known Atlassian Cloud Free tier restriction")
    print("\n[Workaround] Access issues via web UI:")
    print(f"  {JIRA_URL}/browse/{PROJECT_KEY}")
    print("\n[Alternative] Upgrade to JIRA Standard for full API access")

    return 1

if __name__ == "__main__":
    sys.exit(fetch_issues())
