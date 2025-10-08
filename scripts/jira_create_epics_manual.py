#!/usr/bin/env python3
"""
JIRA Create Epics (Manual)

Author: AI Agent
Created: 2025-10-08
Purpose: Create Epics without custom fields (using only standard fields)
"""

import os
import time
import requests
from requests.auth import HTTPBasicAuth

# Configuration
JIRA_URL = os.getenv("JIRA_URL")
JIRA_EMAIL = os.getenv("JIRA_EMAIL")
JIRA_API_TOKEN = os.getenv("JIRA_API_TOKEN")
PROJECT_KEY = os.getenv("JIRA_PROJECT_KEY")

# Epics data
EPICS = [
    {
        "summary": "Phase 0: Bootstrap Infrastructure",
        "description": "Setup development environment, Docker, Git, and project structure",
        "labels": ["bootstrap", "week0"],
    },
    {
        "summary": "Phase 1: POC (Proof of Concept)",
        "description": "Proof of concept for offline-first режим: SQLite buffer, HLC, Circuit Breaker, двухфазная фискализация",
        "labels": ["poc", "week1-5"],
    },
    {
        "summary": "Phase 2: MVP (Minimum Viable Product)",
        "description": "Full functionality: Odoo modules (optics_core, optics_pos_ru54fz, connector_b), офлайн UI, UAT tests",
        "labels": ["mvp", "week6-9"],
    },
    {
        "summary": "Phase 3: Stabilization (Buffer Week)",
        "description": "Load testing, performance optimization, documentation updates, CI/CD automation",
        "labels": ["buffer", "week10"],
    },
    {
        "summary": "Phase 4: Pilot Deployment",
        "description": "Deploy to 2 stores (4 POS), monitoring, stress testing, cashier training, real-world operations",
        "labels": ["pilot", "week11-14"],
    },
    {
        "summary": "Phase 5: Soft Launch",
        "description": "Scale to 5 stores (10 POS), capacity metrics, identify bottlenecks",
        "labels": ["soft-launch", "week15-16"],
    },
    {
        "summary": "Phase 6: Production Rollout",
        "description": "Full deployment to 20 stores (40 POS), DR testing, support procedures, SLA",
        "labels": ["production", "week17-20"],
    }
]


def create_epic_simple(epic_data, auth, headers):
    """Create Epic using only standard fields (no custom fields)"""
    url = f"{JIRA_URL}/rest/api/3/issue"

    payload = {
        "fields": {
            "project": {"key": PROJECT_KEY},
            "summary": epic_data["summary"],
            "description": {
                "type": "doc",
                "version": 1,
                "content": [
                    {
                        "type": "paragraph",
                        "content": [
                            {"type": "text", "text": epic_data["description"]}
                        ]
                    }
                ]
            },
            "issuetype": {"name": "Epic"},
            "labels": epic_data["labels"],
        }
    }

    response = requests.post(url, auth=auth, headers=headers, json=payload, timeout=10)

    if response.status_code == 201:
        issue_data = response.json()
        return issue_data["key"], issue_data["id"]
    else:
        print(f"   ❌ Error: {response.status_code} - {response.text}")
        return None, None


def main():
    if not all([JIRA_URL, JIRA_EMAIL, JIRA_API_TOKEN, PROJECT_KEY]):
        print("❌ Error: Environment variables not set. Run: source .env")
        return False

    auth = HTTPBasicAuth(JIRA_EMAIL, JIRA_API_TOKEN)
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json"
    }

    print(f"📡 JIRA URL: {JIRA_URL}")
    print(f"📁 Project: {PROJECT_KEY}")
    print(f"📊 Creating {len(EPICS)} Epics\n")

    created = 0
    failed = 0

    for i, epic_data in enumerate(EPICS, 1):
        print(f"[{i}/{len(EPICS)}] Creating: {epic_data['summary'][:50]}...")

        epic_key, epic_id = create_epic_simple(epic_data, auth, headers)

        if epic_key:
            created += 1
            print(f"   ✅ Created: {epic_key} (ID: {epic_id})")
        else:
            failed += 1
            print(f"   ❌ Failed")

        time.sleep(0.5)

    print("\n" + "=" * 60)
    print(f"✅ Created: {created}/{len(EPICS)} Epics")
    print(f"❌ Failed:  {failed}")
    print(f"\n🌐 View: {JIRA_URL}/jira/software/c/projects/{PROJECT_KEY}/issues")
    print("=" * 60)

    return True


if __name__ == "__main__":
    main()
