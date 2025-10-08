#!/usr/bin/env python3
"""
JIRA Bulk Import from CSV

Author: AI Agent
Created: 2025-10-08
Purpose: Import all tasks from docs/jira/jira_import.csv into JIRA
"""

import os
import sys
import csv
import time
import requests
from requests.auth import HTTPBasicAuth

# Configuration
JIRA_URL = os.getenv("JIRA_URL")
JIRA_EMAIL = os.getenv("JIRA_EMAIL")
JIRA_API_TOKEN = os.getenv("JIRA_API_TOKEN")
PROJECT_KEY = os.getenv("JIRA_PROJECT_KEY")

# Rate limiting
DELAY_BETWEEN_REQUESTS = 0.5  # seconds


def parse_labels(labels_str):
    """Parse comma-separated labels"""
    if not labels_str or labels_str.strip() == "":
        return []
    return [label.strip() for label in labels_str.split(",")]


def parse_story_points(sp_str):
    """Parse story points (convert to number)"""
    if not sp_str or sp_str.strip() == "" or sp_str == "0":
        return None
    try:
        return int(sp_str)
    except ValueError:
        return None


def create_epic(row, auth, headers):
    """Create an Epic in JIRA"""
    url = f"{JIRA_URL}/rest/api/3/issue"

    # Epic Name (custom field - usually customfield_10011)
    epic_name = row["Summary"]

    payload = {
        "fields": {
            "project": {"key": PROJECT_KEY},
            "summary": row["Summary"],
            "description": {
                "type": "doc",
                "version": 1,
                "content": [
                    {
                        "type": "paragraph",
                        "content": [
                            {"type": "text", "text": row.get("Description", "")}
                        ]
                    }
                ]
            },
            "issuetype": {"name": "Epic"},
            "labels": parse_labels(row.get("Labels", "")),
        }
    }

    # Add Epic Name (custom field)
    # Note: Field ID may vary. Common: customfield_10011
    try:
        payload["fields"]["customfield_10011"] = epic_name
    except:
        pass

    # Add Story Points if exists
    sp = parse_story_points(row.get("Story Points", ""))
    if sp:
        try:
            payload["fields"]["customfield_10016"] = sp  # Story Points field
        except:
            pass

    response = requests.post(url, auth=auth, headers=headers, json=payload, timeout=10)

    if response.status_code == 201:
        issue_data = response.json()
        return issue_data["key"], issue_data["id"]
    else:
        print(f"   ❌ Error creating Epic: {response.status_code} - {response.text}")
        return None, None


def create_story(row, epic_key, auth, headers):
    """Create a Story in JIRA and link to Epic"""
    url = f"{JIRA_URL}/rest/api/3/issue"

    # Parse priority
    priority_map = {
        "Highest": "Highest",
        "High": "High",
        "Medium": "Medium",
        "Low": "Low",
        "Lowest": "Lowest"
    }
    priority = priority_map.get(row.get("Priority", "Medium"), "Medium")

    payload = {
        "fields": {
            "project": {"key": PROJECT_KEY},
            "summary": row["Summary"],
            "description": {
                "type": "doc",
                "version": 1,
                "content": [
                    {
                        "type": "paragraph",
                        "content": [
                            {"type": "text", "text": row.get("Description", "")}
                        ]
                    },
                    {
                        "type": "heading",
                        "attrs": {"level": 3},
                        "content": [
                            {"type": "text", "text": "Acceptance Criteria"}
                        ]
                    },
                    {
                        "type": "paragraph",
                        "content": [
                            {"type": "text", "text": row.get("Acceptance Criteria", "")}
                        ]
                    }
                ]
            },
            "issuetype": {"name": "Story"},
            "priority": {"name": priority},
            "labels": parse_labels(row.get("Labels", "")),
        }
    }

    # Add Story Points
    sp = parse_story_points(row.get("Story Points", ""))
    if sp:
        try:
            payload["fields"]["customfield_10016"] = sp  # Story Points field
        except:
            pass

    # Link to Epic (custom field - usually customfield_10014)
    if epic_key:
        try:
            payload["fields"]["customfield_10014"] = epic_key  # Epic Link field
        except:
            pass

    response = requests.post(url, auth=auth, headers=headers, json=payload, timeout=10)

    if response.status_code == 201:
        issue_data = response.json()
        return issue_data["key"], issue_data["id"]
    else:
        print(f"   ❌ Error creating Story: {response.status_code} - {response.text}")
        return None, None


def import_csv(csv_path):
    """Import all issues from CSV"""

    if not all([JIRA_URL, JIRA_EMAIL, JIRA_API_TOKEN, PROJECT_KEY]):
        print("❌ Error: Environment variables not set. Run: source .env")
        return False

    auth = HTTPBasicAuth(JIRA_EMAIL, JIRA_API_TOKEN)
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json"
    }

    print(f"📡 JIRA URL: {JIRA_URL}")
    print(f"📧 Email: {JIRA_EMAIL}")
    print(f"📁 Project: {PROJECT_KEY}")
    print(f"📄 CSV File: {csv_path}\n")

    # Read CSV
    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
    except FileNotFoundError:
        print(f"❌ Error: File not found: {csv_path}")
        return False

    # Separate Epics and Stories
    epics = [row for row in rows if row["Issue Type"] == "Epic"]
    stories = [row for row in rows if row["Issue Type"] == "Story"]

    print(f"📊 Total issues to import:")
    print(f"   Epics: {len(epics)}")
    print(f"   Stories: {len(stories)}")
    print(f"   Total: {len(rows)}\n")

    # Confirm
    response = input("Continue with import? (yes/no): ")
    if response.lower() != "yes":
        print("❌ Import cancelled")
        return False

    print("\n🚀 Starting import...\n")

    # Phase 1: Create Epics
    epic_mapping = {}  # Map Epic Summary -> Epic Key

    print("📌 Phase 1: Creating Epics")
    print("-" * 60)

    for i, epic_row in enumerate(epics, 1):
        epic_summary = epic_row["Summary"]
        print(f"[{i}/{len(epics)}] Creating Epic: {epic_summary[:50]}...")

        epic_key, epic_id = create_epic(epic_row, auth, headers)

        if epic_key:
            epic_mapping[epic_summary] = epic_key
            print(f"   ✅ Created: {epic_key} (ID: {epic_id})")
        else:
            print(f"   ❌ Failed to create Epic")

        time.sleep(DELAY_BETWEEN_REQUESTS)

    print(f"\n✅ Created {len(epic_mapping)}/{len(epics)} Epics\n")

    # Phase 2: Create Stories
    print("📌 Phase 2: Creating Stories")
    print("-" * 60)

    created_stories = 0
    failed_stories = 0

    for i, story_row in enumerate(stories, 1):
        story_summary = story_row["Summary"]
        epic_link = story_row.get("Epic Link", "")

        # Find Epic key
        epic_key = epic_mapping.get(epic_link, None)

        print(f"[{i}/{len(stories)}] Creating Story: {story_summary[:40]}...")

        story_key, story_id = create_story(story_row, epic_key, auth, headers)

        if story_key:
            created_stories += 1
            epic_info = f" → {epic_key}" if epic_key else ""
            print(f"   ✅ Created: {story_key}{epic_info}")
        else:
            failed_stories += 1
            print(f"   ❌ Failed")

        time.sleep(DELAY_BETWEEN_REQUESTS)

    print("\n" + "=" * 60)
    print("📊 Import Summary")
    print("=" * 60)
    print(f"Epics:   {len(epic_mapping)}/{len(epics)} created")
    print(f"Stories: {created_stories}/{len(stories)} created")
    print(f"Failed:  {failed_stories}")
    print(f"\n🌐 View in JIRA: {JIRA_URL}/jira/software/c/projects/{PROJECT_KEY}/issues")
    print("=" * 60)

    return True


if __name__ == "__main__":
    csv_file = sys.argv[1] if len(sys.argv) > 1 else "docs/jira/jira_import.csv"
    import_csv(csv_file)
