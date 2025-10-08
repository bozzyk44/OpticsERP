# JIRA Import Instructions

**Author:** AI Agent
**Created:** 2025-10-08
**Purpose:** Instructions for importing OpticsERP project structure into JIRA

---

## Overview

This directory contains files for importing the complete OpticsERP project structure into JIRA:

- **7 Epics** (Phases 0-6)
- **77 Stories** (detailed tasks from PROJECT_PHASES.md)
- **269 Story Points** total
- **Labels** for filtering (poc, mvp, buffer, pilot, week1-14, etc.)

---

## Files

| File | Purpose | Format |
|------|---------|--------|
| `jira_import.csv` | Import to JIRA via CSV | CSV |
| `README.md` | This file | Markdown |

---

## Method 1: CSV Import (Recommended)

### Prerequisites

- JIRA Cloud or Server instance
- Admin or Project Admin permissions
- Project created (e.g., "OPTICS" or "OpticsERP")

### Steps

1. **Login to JIRA**
   - Navigate to your JIRA instance
   - Select or create project (e.g., key: OPTICS)

2. **Access CSV Importer**
   ```
   Settings (⚙️) → System → External System Import → CSV
   ```

   Or navigate directly:
   ```
   https://your-jira-instance.atlassian.net/secure/admin/ExternalImport1.jspa
   ```

3. **Upload CSV File**
   - Click "Select File"
   - Choose `jira_import.csv`
   - Click "Next"

4. **Map CSV Fields to JIRA Fields**

   JIRA will auto-detect most fields. Verify mappings:

   | CSV Column | JIRA Field | Type |
   |------------|------------|------|
   | Issue Type | Issue Type | System |
   | Summary | Summary | System |
   | Description | Description | System |
   | Epic Link | Epic Link | Custom (if exists) or Epic Name |
   | Priority | Priority | System |
   | Story Points | Story Points | Custom |
   | Labels | Labels | System |
   | Acceptance Criteria | Custom field or Description | Custom |
   | Start Date | Start Date | System |
   | End Date | Due Date | System |

   **Important:**
   - If "Epic Link" field doesn't exist, map to "Epic Name" for Epics
   - For Stories, you'll need to manually link them to Epics after import
   - Story Points may need custom field configuration

5. **Configure Import Settings**
   - **Project:** Select your project (e.g., OPTICS)
   - **Issue Type Mappings:**
     - Epic → Epic
     - Story → Story (or Task if Story not available)
   - **Email notifications:** Disable during bulk import

6. **Execute Import**
   - Click "Begin Import"
   - Wait for completion (77 issues may take 1-2 minutes)

7. **Verify Import**
   ```bash
   # Expected results:
   # - 7 Epics visible in Epics panel
   # - 77 Stories distributed across phases
   # - Labels applied (filter by "poc", "mvp", etc.)
   ```

8. **Post-Import Cleanup**

   After import, you may need to:

   a) **Link Stories to Epics** (if Epic Link didn't work):
   ```
   # For each Epic:
   1. Open Epic
   2. Click "Add Issue to Epic"
   3. Select Stories with matching labels
   ```

   b) **Verify Story Points**:
   - Total should be ~269 points
   - Check Epic rollup shows correct totals

   c) **Configure Board**:
   ```
   Boards → Create Board → Scrum/Kanban
   - Filter by labels: poc, mvp, buffer, pilot
   - Add Epic swimlanes
   ```

---

## Method 2: Manual Creation (Alternative)

If CSV import fails, manually create issues using this structure:

### Epics

1. **Phase 0: Bootstrap** (0 SP, Done)
2. **Phase 1: POC** (89 SP, To Do)
3. **Phase 2: MVP** (118 SP, To Do)
4. **Phase 3: Stabilization** (21 SP, To Do)
5. **Phase 4: Pilot** (41 SP, To Do)
6. **Phase 5: Soft Launch** (0 SP, To Do)
7. **Phase 6: Production** (0 SP, To Do)

### Stories (Example)

```
Summary: Implement Hybrid Logical Clock (HLC)
Epic: Phase 1: POC
Priority: Highest
Story Points: 3
Labels: poc, week1, hlc, core

Description:
Create kkt_adapter/app/hlc.py with HybridTimestamp dataclass and thread-safe implementation

Acceptance Criteria:
- HLC generates monotonic timestamps
- Logical counter increments within same second
- Ordering works: server_time > local_time > logical_counter
- Thread-safe: 100 concurrent calls without race conditions
```

---

## Method 3: JIRA REST API (Advanced)

For automation, use JIRA REST API with credentials:

### Setup

1. **Generate API Token**
   ```
   https://id.atlassian.com/manage-profile/security/api-tokens
   ```

2. **Install Python Libraries**
   ```bash
   pip install jira requests
   ```

3. **Create Import Script**
   ```python
   from jira import JIRA
   import csv

   # Connect
   jira = JIRA(
       server='https://your-instance.atlassian.net',
       basic_auth=('your-email@example.com', 'YOUR_API_TOKEN')
   )

   # Import Epics
   with open('jira_import.csv') as f:
       reader = csv.DictReader(f)
       for row in reader:
           if row['Issue Type'] == 'Epic':
               issue = jira.create_issue(
                   project='OPTICS',
                   summary=row['Summary'],
                   description=row['Description'],
                   issuetype={'name': 'Epic'},
                   customfield_10011=row['Summary'],  # Epic Name
               )
               print(f"Created Epic: {issue.key}")

   # Import Stories (similar logic)
   ```

---

## Verification Checklist

After import, verify:

- [ ] **7 Epics created**
  - [ ] Phase 0: Bootstrap (Done)
  - [ ] Phase 1: POC
  - [ ] Phase 2: MVP
  - [ ] Phase 3: Stabilization
  - [ ] Phase 4: Pilot
  - [ ] Phase 5: Soft Launch
  - [ ] Phase 6: Production

- [ ] **77 Stories created**
  - [ ] 30 in Phase 1 (POC)
  - [ ] 32 in Phase 2 (MVP)
  - [ ] 6 in Phase 3 (Stabilization)
  - [ ] 10 in Phase 4 (Pilot)

- [ ] **Story Points total: 269**

- [ ] **Labels applied correctly**
  - Filter by `poc` → 30 stories
  - Filter by `mvp` → 32 stories
  - Filter by `week1` → 5 stories (HLC + Buffer)

- [ ] **Priorities set**
  - Highest: ~45 stories (POC critical path)
  - High: ~25 stories
  - Medium: ~7 stories

- [ ] **Epic Links work**
  - Each Story shows its Epic in "Epic Link" field
  - Epic rollup shows correct Story Points

---

## Roadmap View

After import, enable Roadmap:

1. **Navigate to Roadmap**
   ```
   Your Project → Roadmap (in left sidebar)
   ```

2. **Configure Timeline**
   - Group by: Epic
   - Color by: Priority
   - Show: Start Date → End Date

3. **Expected Timeline Visualization**
   ```
   Oct 2025        Nov         Dec         Jan 2026      Feb
   |               |           |           |             |
   [Phase 1: POC--------------------------------]
                               [Phase 2: MVP-----------]
                                           [Ph3][Phase 4: Pilot--------]
                                                         [Ph5][Phase 6-------]
   ```

---

## Filters and Dashboards

### Useful JQL Filters

**Current Sprint (Week 1):**
```jql
project = OPTICS AND labels = week1 ORDER BY priority DESC
```

**POC Phase:**
```jql
project = OPTICS AND labels = poc ORDER BY "Story Points" DESC
```

**Offline-related tasks:**
```jql
project = OPTICS AND labels IN (offline, buffer, sync) ORDER BY priority DESC
```

**High Priority Unassigned:**
```jql
project = OPTICS AND priority = Highest AND assignee IS EMPTY ORDER BY "Story Points" DESC
```

### Dashboard Widgets

Create dashboard with:

1. **Epic Burndown** (track progress per Epic)
2. **Sprint Burndown** (track weekly progress)
3. **Story Points by Label** (pie chart)
4. **Recently Created/Updated** (activity stream)

---

## Troubleshooting

### Issue: CSV Import Fails

**Solution:**
- Check CSV encoding (UTF-8)
- Verify no special characters in descriptions
- Try importing Epics first, then Stories separately

### Issue: Epic Link Not Working

**Solution:**
- Ensure "Epic Link" custom field exists (JIRA Software required)
- Manually link Stories to Epics after import
- Use "Epic Name" field for Epics during import

### Issue: Story Points Not Showing

**Solution:**
- Verify "Story Points" custom field is configured
- Map CSV column to correct custom field ID
- Check field is visible in issue view

### Issue: Labels Not Applied

**Solution:**
- Check CSV column has correct format: `"poc,week1,hlc"`
- Ensure no extra spaces around commas
- Re-import with labels column mapped correctly

---

## Support

For issues with JIRA import:

1. **Check JIRA Documentation:**
   - [CSV Import Guide](https://support.atlassian.com/jira-cloud-administration/docs/import-data-from-a-csv-file/)
   - [REST API Reference](https://developer.atlassian.com/cloud/jira/platform/rest/v3/intro/)

2. **Review Project Files:**
   - `docs/PROJECT_PHASES.md` — Source of truth
   - `docs/PROJECT_SUMMARY.md` — Quick overview

3. **Contact:**
   - Check JIRA admin for custom field configurations
   - Verify project permissions

---

## Next Steps After Import

1. **Assign Stories** to team members
2. **Create Sprints** (Week 1, Week 2, etc.)
3. **Configure Board** (Scrum/Kanban)
4. **Setup Automation** (auto-assign, notifications)
5. **Track Progress** (daily standups, burndown charts)

---

**Import Status:** ⏳ Ready for Import
**Last Updated:** 2025-10-08
**Total Issues:** 84 (7 Epics + 77 Stories)
