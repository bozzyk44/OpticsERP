# Task Plan: OPTERP-39 - Create Import Job Model

**Date:** 2025-11-27
**Status:** ✅ Completed
**Priority:** High
**Assignee:** AI Agent
**Related Task:** OPTERP-38 (Create Import Profile Model)
**Phase:** Phase 2 - MVP (Week 7, Day 3-4)
**Related Commit:** (to be committed)

---

## Objective

Create Odoo models for import job execution (connector_b module) with state machine, file parsing, and logging.

---

## Context

**Background:**
- Part of Week 7: connector_b Module Development
- Import Job executes supplier catalog imports using Import Profiles
- State machine: draft → running → done/failed
- Supports Excel (XLSX) and CSV (UTF-8, Windows-1251)
- Logging with pagination (one2many to import_log)

**Scope:**
- Import Job model with workflow (draft/running/done/failed/cancelled)
- Import Log model for error/warning/info messages
- File parsing (Excel + CSV)
- Upsert logic (create/update products)
- Views (tree, form, search) with progress bar
- Menu integration

---

## Implementation

### 1. Domain Model (from CLAUDE.md)

**Import Job Purpose:**
- Execute supplier catalog import using configured profile
- Upload Excel/CSV file
- Parse file and import products (create/update)
- Log errors and warnings with pagination
- Track statistics (created, updated, skipped, errors)

**Workflow States:**
- **draft:** Initial state (file uploaded, not started)
- **running:** Import in progress
- **done:** Import completed successfully
- **failed:** Import failed with errors
- **cancelled:** Import cancelled by user

**File Formats Supported:**
- XLSX (Excel 2007+) - via openpyxl
- CSV UTF-8 - via csv module
- CSV Windows-1251 - via csv module with cp1251 encoding

**Upsert Logic:**
- Match existing products by upsert_field (from profile)
- Create new products if not found (profile.create_missing = True)
- Update existing products if found (profile.update_existing = True)

### 2. Models Created

#### Model 1: `connector.import.job` (546 lines)

**Fields:**

**Basic Information:**
- `name` — Job reference (auto-generated from ir.sequence)
- `active` — Active flag

**Import Configuration:**
- `profile_id` — Many2one to connector.import.profile (required)
- `file_name` — Uploaded file name
- `file_data` — Binary field (file upload)

**Workflow State:**
```python
state = fields.Selection([
    ('draft', 'Draft'),
    ('running', 'Running'),
    ('done', 'Done'),
    ('failed', 'Failed'),
    ('cancelled', 'Cancelled'),
], default='draft', tracking=True)
```

**Dates:**
- `start_date` — When import started (readonly)
- `end_date` — When import finished (readonly)
- `duration` — Duration in seconds (computed)

**Statistics:**
- `total_rows` — Total rows in file (readonly)
- `processed_rows` — Rows processed (readonly)
- `created_count` — Products created (readonly)
- `updated_count` — Products updated (readonly)
- `skipped_count` — Rows skipped (readonly)
- `error_count` — Rows with errors (readonly)

**Progress:**
- `progress_percent` — Computed (processed_rows / total_rows * 100)

**Logging:**
- `log_ids` — One2many to connector.import.log
- `log_count` — Computed (count of log entries)

**Error Summary:**
- `error_message` — Text (error message if import failed)

**Additional:**
- `notes` — Text (additional notes)

**Workflow Action Methods:**
1. `action_run_import()` — Run import (draft → running → done/failed)
2. `action_cancel()` — Cancel import
3. `action_reset_to_draft()` — Reset to draft (only from failed/cancelled)

**Business Methods:**
- `_do_import()` — Main import logic
- `_parse_file(file_content)` — Parse file based on format
- `_parse_xlsx(file_content)` — Parse Excel file (openpyxl)
- `_parse_csv(file_content, encoding)` — Parse CSV file (csv module)
- `_import_row(row, mapping)` — Import single row (create/update product)
- `_log_error(row_number, row, message)` — Log error
- `_log_warning(row_number, row, message)` — Log warning
- `action_view_logs()` — Open logs for this job
- `get_summary()` — Get formatted import summary

**Computed Methods:**
- `_compute_duration()` — Calculate duration (start_date → end_date)
- `_compute_progress_percent()` — Calculate progress (processed / total * 100)
- `_compute_log_count()` — Count log entries

**CRUD Methods:**
- `create()` — Override to generate sequence for job reference

**Total Lines:** **546 lines** (import_job.py)

#### Model 2: `connector.import.log` (80 lines)

**Fields:**

**Import Job:**
- `job_id` — Many2one to connector.import.job (required, ondelete='cascade', index)

**Log Level:**
```python
level = fields.Selection([
    ('info', 'Info'),
    ('warning', 'Warning'),
    ('error', 'Error'),
], default='info')
```

**Message:**
- `message` — Text (log message, required)

**Row Information:**
- `row_number` — Integer (row number in file, 0 = general message)
- `row_data` — Text (row data in JSON format)

**Timestamp:**
- `create_date` — Datetime (readonly, auto-filled)

**SQL Constraints:**
- `check_row_number_positive` — Row number ≥ 0

**Total Lines:** **80 lines** (import_log.py)

### 3. Views Created

**File:** `addons/connector_b/views/import_job_views.xml` (219 lines)

**Views for Import Job:**

1. **Tree View** (`view_connector_import_job_tree`)
   - Columns: name, profile, file_name, start_date, duration, total_rows, created/updated/error counts, state
   - Decorations: done=green, failed=red, running=orange, cancelled=grey
   - Badge widget for state

2. **Form View** (`view_connector_import_job_form`)
   - **Header:** Workflow buttons + statusbar
     - Run Import (visible in draft)
     - Cancel (visible except done/failed/cancelled)
     - Reset to Draft (visible in failed/cancelled)
   - **Alert Banner:** Error message (visible if error_message set)
   - **Progress Bar:** Shows progress_percent (visible in running/done)
   - **Groups:**
     - Import Configuration (profile, file upload)
     - Timing (start_date, end_date, duration)
     - Statistics (total/processed rows, created/updated/skipped/errors)
   - **Notebook:**
     - **Page 1: Logs** - One2many field log_ids (tree with decorations)
     - **Page 2: Notes** - Additional notes
   - **Chatter:** Message tracking (tracking=True on state)

3. **Search View** (`view_connector_import_job_search`)
   - Search fields: name, profile_id, file_name
   - **Filters:**
     - By state: Draft, Running, Done, Failed, Cancelled
     - Has Errors (error_count > 0)
     - Today, This Week
   - **Group by:** Profile, Status, Start Date

4. **Action** (`action_connector_import_job`)

**Views for Import Log:**

5. **Tree View** (`view_connector_import_log_tree`)
   - Columns: create_date, job_id, level, row_number, message
   - Decorations: error=red, warning=orange
   - Badge widget for level

6. **Form View** (`view_connector_import_log_form`)
   - Fields: job_id, level (radio), row_number, create_date, message, row_data (JSON editor)

### 4. Data Files Created

**File:** `addons/connector_b/data/ir_sequence_data.xml` (11 lines)

**Sequence:**
- Code: `connector.import.job`
- Prefix: `IMP/`
- Padding: 5
- Format: `IMP/00001`, `IMP/00002`, etc.

### 5. Menu Integration

**Updated:** `addons/connector_b/views/menu_views.xml`

**Changed:**
- Added `action="action_connector_import_job"` to Import Jobs menu item

**Menu Structure:**
```
Connector B
├── Import Profiles
├── Import Jobs ← UPDATED (now functional)
└── Configuration
```

---

## Files Created/Modified

### Created
1. **`addons/connector_b/models/import_job.py`** (546 lines)
   - connector.import.job model
   - State machine (draft → running → done/failed)
   - File parsing (Excel + CSV)
   - Upsert logic (create/update products)
   - Logging methods
   - Business methods (run, cancel, reset, view logs, summary)

2. **`addons/connector_b/models/import_log.py`** (80 lines)
   - connector.import.log model
   - Log levels (info, warning, error)
   - Row tracking (row_number, row_data)

3. **`addons/connector_b/views/import_job_views.xml`** (219 lines)
   - Tree view with decorations (color-coded states)
   - Form view with progress bar, workflow buttons
   - Search view with filters
   - Log tree/form views
   - 2 actions

4. **`addons/connector_b/data/ir_sequence_data.xml`** (11 lines)
   - Sequence for import job reference (IMP/00001)

### Modified
5. **`addons/connector_b/views/menu_views.xml`**
   - Added action to Import Jobs menu item

6. **`addons/connector_b/__manifest__.py`**
   - Added `'data/ir_sequence_data.xml'` to data list

### Already Prepared (Bootstrap)
7. **`addons/connector_b/models/__init__.py`**
   - Already includes: `from . import import_job` and `from . import import_log` ✅

8. **`addons/connector_b/security/ir.model.access.csv`**
   - Already configured: access rules for import_job and import_log ✅

---

## Acceptance Criteria

- ✅ Import Job model created (`connector.import.job`)
- ✅ Import Log model created (`connector.import.log`)
- ✅ State machine implemented (draft/running/done/failed/cancelled)
- ✅ Workflow action methods (run, cancel, reset)
- ✅ File upload (binary field)
- ✅ File parsing (Excel XLSX via openpyxl)
- ✅ File parsing (CSV UTF-8 and Windows-1251 via csv module)
- ✅ Upsert logic (create/update products based on profile settings)
- ✅ Statistics tracking (created, updated, skipped, errors)
- ✅ Progress calculation (processed_rows / total_rows)
- ✅ Logging with levels (info, warning, error)
- ✅ Row tracking in logs (row_number, row_data JSON)
- ✅ Duration calculation (start → end in seconds)
- ✅ Sequence generation for job reference (IMP/00001)
- ✅ Tree/Form/Search views created
- ✅ Progress bar in form view
- ✅ Workflow buttons (run, cancel, reset)
- ✅ Log viewer (one2many field with decorations)
- ✅ Menu item updated with action
- ✅ Security rules configured (already in bootstrap)

---

## Data Model

### connector_import_job (Main Table)

```sql
CREATE TABLE connector_import_job (
    id SERIAL PRIMARY KEY,
    name VARCHAR NOT NULL DEFAULT 'New',
    active BOOLEAN DEFAULT TRUE,
    profile_id INTEGER REFERENCES connector_import_profile(id) NOT NULL,

    -- File Upload
    file_name VARCHAR,
    file_data BYTEA NOT NULL,

    -- State
    state VARCHAR CHECK (state IN ('draft', 'running', 'done', 'failed', 'cancelled')) DEFAULT 'draft',

    -- Dates
    start_date TIMESTAMP,
    end_date TIMESTAMP,

    -- Statistics
    total_rows INTEGER DEFAULT 0,
    processed_rows INTEGER DEFAULT 0,
    created_count INTEGER DEFAULT 0,
    updated_count INTEGER DEFAULT 0,
    skipped_count INTEGER DEFAULT 0,
    error_count INTEGER DEFAULT 0,

    -- Error
    error_message TEXT,

    -- Notes
    notes TEXT
);
```

### connector_import_log (Log Table)

```sql
CREATE TABLE connector_import_log (
    id SERIAL PRIMARY KEY,
    job_id INTEGER REFERENCES connector_import_job(id) ON DELETE CASCADE NOT NULL,
    level VARCHAR CHECK (level IN ('info', 'warning', 'error')) DEFAULT 'info',
    message TEXT NOT NULL,
    row_number INTEGER CHECK (row_number >= 0),
    row_data TEXT,
    create_date TIMESTAMP NOT NULL,

    INDEX idx_job_id (job_id)
);
```

---

## Example Workflow

### Scenario: Import Essilor Price List

**Step 1: Create Draft Job**
```python
job = self.env['connector.import.job'].create({
    'profile_id': essilor_profile.id,
    'file_name': 'essilor_prices_2025.xlsx',
    'file_data': base64.b64encode(file_content),
})
# name = 'IMP/00001' (auto-generated)
# state = 'draft'
```

**Step 2: Run Import**
```python
job.action_run_import()
# state = 'running' (start_date set)
# Parses Excel file
# Imports 500 rows:
#   - 450 updated (existing products)
#   - 40 created (new products)
#   - 10 errors (logged to import_log)
# state = 'done' (end_date set)
# Statistics:
#   total_rows = 500
#   processed_rows = 500
#   created_count = 40
#   updated_count = 450
#   error_count = 10
```

**Step 3: View Logs**
```python
job.action_view_logs()
# Opens tree view with 10 error logs
# Each log has row_number, message, row_data (JSON)
```

---

## Testing (Future: OPTERP-XX)

**Note:** Unit tests will be created in a future task.

**Planned Tests:**
- test_create_import_job() — Create with profile and file
- test_run_import_draft_to_done() — Draft → Running → Done
- test_run_import_xlsx() — Parse Excel file successfully
- test_run_import_csv_utf8() — Parse CSV UTF-8 successfully
- test_run_import_csv_cp1251() — Parse CSV Windows-1251 successfully
- test_upsert_create_new_products() — Create missing products
- test_upsert_update_existing_products() — Update existing products
- test_upsert_skip_if_not_found() — Skip if create_missing=False
- test_error_logging() — Errors logged correctly
- test_warning_logging() — Warnings logged correctly
- test_progress_calculation() — Progress percent computed correctly
- test_duration_calculation() — Duration in seconds
- test_cancel_job() — Cancel running job
- test_reset_to_draft() — Reset failed job to draft
- test_cannot_run_non_draft_job() — Only draft can be run
- test_sequence_generation() — Auto-generated IMP/00001

**Coverage Target:** ≥95%

---

## Business Rules

1. **Workflow States:**
   ```
   draft → running → done/failed
   Any (except done/failed) → cancelled
   failed/cancelled → draft (reset)
   ```

2. **File Parsing:**
   - **Excel (XLSX):** Uses openpyxl library
   - **CSV:** Uses csv module with configurable delimiter and quote char
   - **Encoding:** UTF-8 or Windows-1251 (cp1251)
   - **Row Configuration:** header_row, data_start_row from profile
   - **Skip Empty Rows:** Configurable per profile

3. **Upsert Logic:**
   - Match field: profile.upsert_field (default_code, barcode, or name)
   - Create missing: profile.create_missing (True/False)
   - Update existing: profile.update_existing (True/False)
   - Result: 'created', 'updated', or 'skipped'

4. **Logging:**
   - Levels: info, warning, error
   - Row tracking: row_number (1-indexed), row_data (JSON)
   - Pagination: One2many relation (Odoo handles pagination automatically)

5. **Statistics:**
   - total_rows: Total rows in file (excluding header)
   - processed_rows: Rows processed so far
   - created_count, updated_count, skipped_count, error_count
   - progress_percent: (processed / total) * 100

6. **Error Handling:**
   - Errors during import set state = 'failed'
   - error_message field contains exception message
   - Detailed errors logged to import_log table
   - Job can be reset to draft for retry

---

## Integration Points

### With Import Profile (OPTERP-38)
- Job.profile_id references Import Profile
- Uses profile settings: column_mapping, file_format, upsert_field, create/update flags
- Profile.job_count computed from Import Job records
- Profile.last_import_date from latest successful job

### With Product Model (Odoo Core)
- Creates/updates product.product records
- Maps file columns to product fields via profile.column_mapping
- Upsert based on profile.upsert_field (default_code, barcode, name)

### With KKT Adapter (Future)
- TODO: Block import if offline buffers not synced
- Check buffer sync status before running import
- Prevents data inconsistency during offline mode

---

## UI/UX Features

### Form View Highlights

**1. Progress Bar:**
```xml
<div class="o_progressbar">
    <div class="o_progressbar_title">
        Progress: <field name="progress_percent"/>%
    </div>
    <div class="o_progressbar_bar">
        <div class="o_progressbar_complete" style="width: {{progress_percent}}%"/>
    </div>
</div>
```
- Visual feedback during import
- Shows processed / total rows percentage

**2. Error Alert Banner:**
```xml
<div class="alert alert-danger" invisible="not error_message">
    <strong>Error:</strong>
    <field name="error_message" readonly="1"/>
</div>
```
- Prominent display of critical errors
- Only visible if import failed

**3. Workflow Buttons:**
- Context-aware (only show valid actions)
- Run Import (draft only)
- Cancel (running only)
- Reset to Draft (failed/cancelled only)

**4. Log Viewer (One2many):**
```xml
<field name="log_ids">
    <tree decoration-danger="level=='error'" decoration-warning="level=='warning'">
        <field name="create_date"/>
        <field name="level" widget="badge"/>
        <field name="row_number"/>
        <field name="message"/>
    </tree>
</field>
```
- Color-coded logs (errors in red, warnings in orange)
- Badge widget for log level
- Pagination handled automatically by Odoo

### Tree View Highlights

**1. Decorations:**
- Done: Green text (`decoration-success="state=='done'"`)
- Failed: Red text (`decoration-danger="state=='failed'"`)
- Running: Orange text (`decoration-warning="state=='running'"`)
- Cancelled: Grey text (`decoration-muted="state=='cancelled'"`)

**2. Duration Widget:**
```xml
<field name="duration" widget="float_time"/>
```
- Displays duration in human-readable format (HH:MM:SS)

---

## Known Issues

### Issue 1: Requires openpyxl Library
**Description:** Import Job uses openpyxl to parse Excel files.

**Impact:** Need to add openpyxl to requirements.txt.

**Resolution:**
- Add to `requirements.txt`: `openpyxl==3.1.2`
- Install when setting up Odoo environment

**Status:** ⏸️ Pending (add to requirements.txt in next phase)

### Issue 2: Buffer Sync Check Not Implemented
**Description:** CLAUDE.md requires blocking import when offline buffers not synced.

**Impact:** Import currently does not check KKT adapter buffer status.

**Resolution:**
- Implement `_check_buffer_synced()` method
- Call KKT adapter API to check buffer status
- Raise UserError if buffers not synced

**Status:** ⏸️ TODO (Phase 2 Week 8: optics_pos_ru54fz integration)

---

## Next Steps

1. **OPTERP-40:** Create Import Wizard
   - Wizard for file upload and preview
   - Show first 10 rows before import
   - Confirm trigger for action_run_import()

2. **Phase 2 Week 7:** Complete connector_b module

3. **Phase 2 Week 8:** Integrate with KKT adapter (buffer sync check)

4. **Future Enhancements:**
   - Import preview (show first N rows before running)
   - Dry run mode (validate without importing)
   - Import scheduler (cron jobs for automatic imports)
   - Email notification on import completion
   - Data transformation rules (e.g., price conversion, category mapping)
   - Import templates (pre-configured profiles for common suppliers)
   - Batch import (multiple files at once)

---

## References

### Domain Documentation
- **CLAUDE.md:** §3.2 (connector_b module overview)
- **PROJECT_PHASES.md:** Week 7 Day 3-4 (Import Job task)

### Related Tasks
- **OPTERP-32:** Create Prescription Model ✅ COMPLETED
- **OPTERP-33:** Create Prescription Unit Tests ✅ COMPLETED
- **OPTERP-34:** Create Lens Model ✅ COMPLETED
- **OPTERP-35:** Create Lens Unit Tests ✅ COMPLETED
- **OPTERP-36:** Create Manufacturing Order Model ✅ COMPLETED
- **OPTERP-37:** Create Manufacturing Order Unit Tests ✅ COMPLETED
- **OPTERP-38:** Create Import Profile Model ✅ COMPLETED
- **OPTERP-39:** Create Import Job Model ✅ COMPLETED (this task)
- **OPTERP-40:** Create Import Wizard (Next)

### Odoo Documentation
- **Odoo 17 ORM:** Model definition, fields, Binary fields, One2many/Many2one
- **Odoo 17 Views:** Tree, form, search, progress bar, badge widget
- **Odoo 17 Widgets:** binary (file upload), float_time (duration), ace (JSON editor)

### Python Libraries
- **openpyxl:** Excel file parsing (XLSX)
- **csv:** CSV file parsing (built-in)
- **json:** JSON serialization for row_data

---

## Timeline

- **Start:** 2025-11-27 18:00
- **End:** 2025-11-27 18:40
- **Duration:** ~40 minutes
- **Lines of Code:** 546 (import_job.py) + 80 (import_log.py) + 219 (import_job_views.xml) + 11 (ir_sequence_data.xml) = **856 lines**

---

**Status:** ✅ MODELS COMPLETE (Pending Odoo Runtime for Testing)

**Next Task:** OPTERP-40 (Create Import Wizard)

---

🤖 Generated with [Claude Code](https://claude.com/claude-code)
