#!/usr/bin/env python3
"""
Add Missing Stories for Phase 5 and Phase 6

Author: AI Agent
Created: 2025-10-08
Purpose: Create missing stories for Soft Launch and Production phases
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

# Epic keys (already created)
EPIC_PHASE5 = "OPTERP-84"  # Phase 5: Soft Launch
EPIC_PHASE6 = "OPTERP-85"  # Phase 6: Production Rollout

# Missing stories for Phase 5: Soft Launch (Week 15-16)
PHASE5_STORIES = [
    {
        "summary": "Deploy to 5 Additional Stores (Total 10 POS)",
        "description": "Scale deployment from pilot (2 stores) to soft launch (5 stores, 10 POS terminals total)",
        "acceptance_criteria": """
- 6 additional KKT adapters installed (2+4 from pilot = 10 total)
- All 10 POS terminals connected to Odoo
- Network connectivity verified (≥10 Mbps)
- Heartbeat from all 10 terminals active
- Buffer databases initialized on all terminals
        """,
        "labels": ["soft-launch", "week15", "deployment"],
        "priority": "High",
        "story_points": 5
    },
    {
        "summary": "Execute Simplified Load Test (5 POS, 1000 Receipts/Day)",
        "description": "Run simplified load test scenario 4: 5 POS terminals, 1000 receipts per day",
        "acceptance_criteria": """
- Locust load test configured for 5 POS
- 1000 receipts/day distributed across 5 terminals
- Test runs for 8 hours
- P95 latency ≤7s
- 0% errors
- All receipts synced to OFD
        """,
        "labels": ["soft-launch", "week15", "load-test"],
        "priority": "Highest",
        "story_points": 3
    },
    {
        "summary": "Collect Capacity Metrics (PostgreSQL, Celery, Odoo)",
        "description": "Monitor and analyze capacity metrics to identify bottlenecks before full production",
        "acceptance_criteria": """
- PostgreSQL query P95 <50ms (verified via Grafana)
- Celery critical queue <30 tasks at all times
- Odoo CPU usage <70% average
- No OOM errors in logs
- No CPU throttling detected
- Metrics exported to CSV for analysis
        """,
        "labels": ["soft-launch", "week16", "monitoring", "capacity"],
        "priority": "Highest",
        "story_points": 3
    },
    {
        "summary": "Identify and Document Performance Bottlenecks",
        "description": "Analyze capacity metrics, identify bottlenecks, document findings and optimization plan",
        "acceptance_criteria": """
- Performance analysis report created
- Top 3 bottlenecks identified (e.g., slow queries, queue backlog)
- Optimization plan documented with priorities
- Estimated impact of optimizations (% improvement)
- Sign-off from technical lead
        """,
        "labels": ["soft-launch", "week16", "optimization", "documentation"],
        "priority": "High",
        "story_points": 3
    },
    {
        "summary": "Create Store Addition Procedure and Test",
        "description": "Document and test procedure for adding new stores to production",
        "acceptance_criteria": """
- Procedure documented in runbook (step-by-step)
- Includes: hardware setup, KKT adapter installation, network config, Odoo config
- Test procedure by adding 1 store end-to-end
- Procedure takes ≤2 hours per store
- Checklist for verification created
        """,
        "labels": ["soft-launch", "week16", "procedure", "documentation"],
        "priority": "High",
        "story_points": 2
    },
    {
        "summary": "Optimize Performance Issues from Capacity Metrics",
        "description": "Implement optimizations identified from capacity metrics analysis",
        "acceptance_criteria": """
- Top 3 bottlenecks addressed
- PostgreSQL query optimization (if needed)
- Celery queue tuning (if needed)
- Code-level optimizations deployed
- Re-run capacity metrics → improvements verified
        """,
        "labels": ["soft-launch", "week16", "optimization"],
        "priority": "High",
        "story_points": 5
    },
    {
        "summary": "Create Soft Launch Sign-Off Document",
        "description": "Verify soft launch DoD criteria and create sign-off document",
        "acceptance_criteria": """
- All capacity metrics within thresholds
- Load test passed (scenario 4)
- 0 P1/P2 defects
- Performance bottlenecks documented/addressed
- Sign-off approved by stakeholders
        """,
        "labels": ["soft-launch", "week16", "sign-off"],
        "priority": "High",
        "story_points": 2
    }
]

# Missing stories for Phase 6: Production Rollout (Week 17-20)
PHASE6_STORIES = [
    {
        "summary": "Deploy to Remaining 15 Stores (Total 40 POS)",
        "description": "Full production deployment: scale from 10 POS (soft launch) to 40 POS (20 stores)",
        "acceptance_criteria": """
- 30 additional KKT adapters installed (10 from soft launch + 30 = 40 total)
- All 40 POS terminals operational
- Network verified on all locations
- Heartbeat from all 40 terminals
- UPS configured on all terminals
        """,
        "labels": ["production", "week17-18", "deployment"],
        "priority": "Highest",
        "story_points": 8
    },
    {
        "summary": "Configure pgbouncer (If Needed)",
        "description": "Setup and configure pgbouncer connection pooler if PostgreSQL connection limits reached",
        "acceptance_criteria": """
- PostgreSQL max_connections analyzed (current vs required)
- pgbouncer installed if connections >80% limit
- Pool mode configured (transaction/session)
- Connection pool size tuned (min/max)
- Health check endpoint works
- Odoo connects via pgbouncer without errors
        """,
        "labels": ["production", "week17", "database", "optimization"],
        "priority": "Medium",
        "story_points": 3
    },
    {
        "summary": "Setup Daily Backups for Offline Buffers",
        "description": "Implement automated daily backups of SQLite offline buffers (all 40 POS)",
        "acceptance_criteria": """
- Backup script created (rsync or similar)
- Cron job scheduled (daily at 03:00)
- PRAGMA wal_checkpoint(TRUNCATE) before backup
- Backups stored in central location
- Retention: 7 days
- Test restore from backup → success
        """,
        "labels": ["production", "week17", "backup", "reliability"],
        "priority": "High",
        "story_points": 3
    },
    {
        "summary": "Execute DR Test (RTO≤1h, RPO≤24h)",
        "description": "Test disaster recovery procedures: server failure, restore from backup, verify RTO/RPO",
        "acceptance_criteria": """
- Simulate PostgreSQL server failure
- Restore from backup within 1 hour (RTO)
- Data loss ≤24 hours (RPO)
- All services resume (Odoo, KKT adapters)
- DR procedure documented in runbook
- DR test report created
        """,
        "labels": ["production", "week18", "dr", "reliability"],
        "priority": "Highest",
        "story_points": 5
    },
    {
        "summary": "Create Administrator Guide (≥50 Pages)",
        "description": "Comprehensive administrator guide for system operations and maintenance",
        "acceptance_criteria": """
- Architecture overview (5-10 pages)
- Installation guide (10-15 pages)
- Configuration reference (10-15 pages)
- Troubleshooting guide (10-15 pages)
- Backup/restore procedures (5 pages)
- Monitoring and alerts (5 pages)
- Total: ≥50 pages
- PDF + editable format (Markdown)
        """,
        "labels": ["production", "week19", "documentation"],
        "priority": "High",
        "story_points": 8
    },
    {
        "summary": "Create Runbook with ≥20 Scenarios",
        "description": "Operational runbook with step-by-step procedures for common scenarios",
        "acceptance_criteria": """
- ≥20 scenarios documented (e.g., buffer full, OFD down, ФН replacement)
- Each scenario has: symptoms, diagnosis steps, resolution steps, rollback
- Decision tree for L1/L2/L3 escalation
- Runbook in searchable format (wiki or PDF)
- Validated by operations team
        """,
        "labels": ["production", "week19", "documentation", "runbook"],
        "priority": "Highest",
        "story_points": 8
    },
    {
        "summary": "Define SLA and Incident Response Procedures",
        "description": "Create SLA definitions and incident management procedures",
        "acceptance_criteria": """
- SLA defined: P1 (≤15min response, ≤1h resolution), P2 (≤1h, ≤4h), P3 (≤24h, ≤3d)
- Incident escalation matrix (L1 → L2 → L3)
- On-call rotation schedule (1 week per engineer)
- Incident template (JIRA)
- Post-mortem template
- SLA tracking dashboard (Grafana)
        """,
        "labels": ["production", "week19", "sla", "process"],
        "priority": "High",
        "story_points": 5
    },
    {
        "summary": "Setup On-Call Procedures and Contacts",
        "description": "Configure on-call rotation, alert channels, contact information",
        "acceptance_criteria": """
- On-call rotation configured (PagerDuty or similar)
- Alert channels: email, Telegram, SMS
- Contact list updated (L1, L2, owner)
- On-call playbook created
- Test alert → on-call receives within 1 minute
        """,
        "labels": ["production", "week20", "on-call", "process"],
        "priority": "High",
        "story_points": 2
    },
    {
        "summary": "Create Support Maintenance Procedures",
        "description": "Document Day 2 operations: routine maintenance, health checks, log rotation",
        "acceptance_criteria": """
- Daily health check procedure (automated)
- Weekly maintenance tasks (manual review)
- Monthly tasks (capacity planning, log cleanup)
- Quarterly tasks (DR test, security audit)
- Checklists for each task
- Procedures documented in runbook
        """,
        "labels": ["production", "week20", "maintenance", "day2ops"],
        "priority": "Medium",
        "story_points": 3
    },
    {
        "summary": "Verify Production DoD and Sign-Off",
        "description": "Verify all production criteria met and obtain final sign-off",
        "acceptance_criteria": """
- All 40 POS operational
- RTO≤1h, RPO≤24h verified
- Administrator guide complete (≥50 pages)
- Runbook complete (≥20 scenarios)
- SLA defined and tracked
- On-call rotation active
- Stakeholder sign-off obtained
        """,
        "labels": ["production", "week20", "sign-off"],
        "priority": "Highest",
        "story_points": 2
    }
]


def create_story(story_data, epic_key, auth, headers):
    """Create a story and link to epic"""
    url = f"{JIRA_URL}/rest/api/3/issue"

    # Parse priority
    priority_map = {
        "Highest": "Highest",
        "High": "High",
        "Medium": "Medium",
        "Low": "Low"
    }
    priority = priority_map.get(story_data.get("priority", "Medium"), "Medium")

    payload = {
        "fields": {
            "project": {"key": PROJECT_KEY},
            "summary": story_data["summary"],
            "description": {
                "type": "doc",
                "version": 1,
                "content": [
                    {
                        "type": "paragraph",
                        "content": [
                            {"type": "text", "text": story_data["description"]}
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
                            {"type": "text", "text": story_data["acceptance_criteria"]}
                        ]
                    }
                ]
            },
            "issuetype": {"name": "Story"},
            "priority": {"name": priority},
            "labels": story_data["labels"],
        }
    }

    # Add Story Points (if supported)
    sp = story_data.get("story_points")
    if sp:
        try:
            payload["fields"]["customfield_10016"] = sp
        except:
            pass

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
    print(f"📁 Project: {PROJECT_KEY}\n")

    total_stories = len(PHASE5_STORIES) + len(PHASE6_STORIES)
    print(f"📊 Creating {total_stories} missing stories:")
    print(f"   Phase 5 (Soft Launch): {len(PHASE5_STORIES)} stories")
    print(f"   Phase 6 (Production):  {len(PHASE6_STORIES)} stories\n")

    created = 0
    failed = 0

    # Phase 5 Stories
    print("📌 Phase 5: Soft Launch")
    print("-" * 60)

    for i, story_data in enumerate(PHASE5_STORIES, 1):
        print(f"[{i}/{len(PHASE5_STORIES)}] Creating: {story_data['summary'][:50]}...")

        story_key, story_id = create_story(story_data, EPIC_PHASE5, auth, headers)

        if story_key:
            created += 1
            print(f"   ✅ Created: {story_key} ({story_data['story_points']} SP)")
        else:
            failed += 1
            print(f"   ❌ Failed")

        time.sleep(0.5)

    print()

    # Phase 6 Stories
    print("📌 Phase 6: Production Rollout")
    print("-" * 60)

    for i, story_data in enumerate(PHASE6_STORIES, 1):
        print(f"[{i}/{len(PHASE6_STORIES)}] Creating: {story_data['summary'][:50]}...")

        story_key, story_id = create_story(story_data, EPIC_PHASE6, auth, headers)

        if story_key:
            created += 1
            print(f"   ✅ Created: {story_key} ({story_data['story_points']} SP)")
        else:
            failed += 1
            print(f"   ❌ Failed")

        time.sleep(0.5)

    print("\n" + "=" * 60)
    print("📊 Summary")
    print("=" * 60)
    print(f"✅ Created: {created}/{total_stories} stories")
    print(f"❌ Failed:  {failed}")

    # Calculate story points
    phase5_sp = sum(s["story_points"] for s in PHASE5_STORIES)
    phase6_sp = sum(s["story_points"] for s in PHASE6_STORIES)

    print(f"\n📈 Story Points:")
    print(f"   Phase 5: {phase5_sp} SP")
    print(f"   Phase 6: {phase6_sp} SP")
    print(f"   Total:   {phase5_sp + phase6_sp} SP")

    print(f"\n🌐 View: {JIRA_URL}/jira/software/c/projects/{PROJECT_KEY}/issues")
    print("=" * 60)

    return True


if __name__ == "__main__":
    main()
