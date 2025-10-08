#!/usr/bin/env python3
"""
JIRA Projects Lister

Author: AI Agent
Created: 2025-10-08
Purpose: List all accessible JIRA projects
"""

import os
import requests
from requests.auth import HTTPBasicAuth

# Configuration
JIRA_URL = os.getenv("JIRA_URL", "https://your-domain.atlassian.net")
JIRA_EMAIL = os.getenv("JIRA_EMAIL")
JIRA_API_TOKEN = os.getenv("JIRA_API_TOKEN")


def list_projects():
    """List all JIRA projects"""

    if not JIRA_API_TOKEN:
        print("❌ Error: JIRA_API_TOKEN not set")
        return False

    url = f"{JIRA_URL}/rest/api/3/project"
    auth = HTTPBasicAuth(JIRA_EMAIL, JIRA_API_TOKEN)
    headers = {"Accept": "application/json"}

    print(f"📡 Fetching projects from: {JIRA_URL}")
    print(f"📧 Email: {JIRA_EMAIL}\n")

    try:
        response = requests.get(url, auth=auth, headers=headers, timeout=10)

        if response.status_code == 200:
            projects = response.json()

            if not projects:
                print("⚠ No projects found")
                print("\n💡 Create a project:")
                print(f"   1. Open: {JIRA_URL}/jira/settings/projects")
                print("   2. Click 'Create project'")
                print("   3. Template: Scrum")
                print("   4. Name: OpticsERP")
                print("   5. Key: OPTICS")
                return False

            print(f"✅ Found {len(projects)} project(s):\n")
            print(f"{'Key':<15} {'Name':<30} {'Type':<15}")
            print("-" * 60)

            for project in projects:
                key = project.get('key', 'N/A')
                name = project.get('name', 'N/A')
                ptype = project.get('projectTypeKey', 'N/A')
                print(f"{key:<15} {name:<30} {ptype:<15}")

            print(f"\n💡 To use a project, update .env:")
            print(f'   export JIRA_PROJECT_KEY="{projects[0]["key"]}"')

            return True
        else:
            print(f"❌ Error {response.status_code}: {response.reason}")
            print(f"Response: {response.text}")
            return False

    except Exception as e:
        print(f"❌ Error: {e}")
        return False


if __name__ == "__main__":
    list_projects()
