# Task Plan: OPTERP-43 - Create Import Wizard

**Date:** 2025-11-27
**Status:** ✅ Completed
**Priority:** High
**Assignee:** AI Agent
**Related Tasks:** OPTERP-41 (Import Profile), OPTERP-42 (Import Job)
**Phase:** Phase 2 - MVP (Week 7, Day 5)
**Related Commit:** (to be committed)

---

## Objective

Create Odoo wizard for supplier catalog import with file upload, profile selection, and preview functionality.

---

## Context

**Background:**
- Part of Week 7: connector_b Module Development
- Import Wizard provides user-friendly UI for importing supplier catalogs
- Allows file upload, profile selection, and preview before import
- Creates Import Job and triggers execution

**Scope:**
- Wizard model (TransientModel)
- File upload widget (binary field)
- Profile selection (many2one)
- Preview computation (first 10 rows)
- Wizard actions (preview, import, cancel)
- Wizard view (form with footer buttons)
- Menu integration

---

## Implementation

### 1. Domain Model (from CLAUDE.md)

**Import Wizard Purpose:**
- User-friendly interface for importing supplier catalogs
- Step 1: Select import profile
- Step 2: Upload file (Excel/CSV)
- Step 3: Preview first 10 rows (optional)
- Step 4: Confirm import (creates Import Job)

**Workflow:**
1. User opens wizard (menu item)
2. Selects import profile
3. Uploads file
4. (Optional) Clicks "Preview" to see first 10 rows
5. Clicks "Import" to create job and run import
6. Wizard closes and opens Import Job form

### 2. Model Created

#### Model: `connector.import.wizard` (226 lines)

**Type:** TransientModel (temporary, not stored in database)

**Fields:**

**Import Configuration:**
- `profile_id` — Many2one to connector.import.profile (required)
  - Domain: `[('active', '=', True)]` (only active profiles)

**File Upload:**
- `file_name` — Char (uploaded file name)
- `file_data` — Binary (file content, required)

**Preview:**
- `preview_data` — Text (computed, formatted preview of first 10 rows)
- `show_preview` — Boolean (toggle preview display, default: False)

**Computed Methods:**
- `_compute_preview_data()` — Parse file and generate preview
- `_parse_xlsx_preview(file_content, profile)` — Parse Excel for preview
- `_parse_csv_preview(file_content, profile, encoding)` — Parse CSV for preview

**Wizard Actions:**
- `action_preview()` — Show preview (sets show_preview=True, reloads wizard)
- `action_import()` — Create Import Job and run import
- `action_cancel()` — Close wizard

**Total Lines:** **226 lines** (import_wizard.py)

### 3. Views Created

**File:** `addons/connector_b/wizards/import_wizard_views.xml` (45 lines)

**Views:**

1. **Wizard Form View** (`view_connector_import_wizard_form`)

**Layout:**
- **Sheet:**
  - **Group 1: Import Configuration**
    - profile_id (many2one, no_create)

  - **Group 2: File Upload**
    - file_data (binary widget with filename)

  - **Group 3: Preview (conditional)**
    - preview_data (text widget)
    - Visible only if `show_preview = True`

- **Footer (Buttons):**
  - **Preview** button (secondary, hidden if preview shown)
  - **Import** button (primary)
  - **Cancel** button (secondary)

**Features:**
- Modal dialog (target: new)
- Conditional preview display
- File upload widget
- Footer buttons for actions

2. **Wizard Action** (`action_connector_import_wizard`)
- View mode: form
- Target: new (modal dialog)

3. **Menu Item** (`menu_connector_import_wizard`)
- Parent: `menu_connector_root` (Connector B)
- Action: `action_connector_import_wizard`
- Sequence: 5 (top of menu)

**Menu Structure:**
```
Connector B
├── Import Catalog ← NEW (wizard, sequence 5)
├── Import Profiles (sequence 10)
├── Import Jobs (sequence 20)
└── Configuration (sequence 100)
```

### 4. Preview Functionality

**Preview Format:**
```
Profile: Essilor Price List
Format: Excel (XLSX)
Total Rows: 500

First 10 Rows:
--------------------------------------------------------------------------------
Row 1:
  SKU: ESS-123
  Product Name: Single Vision CR-39
  Price: 1500
  Cost: 500

Row 2:
  SKU: ESS-124
  Product Name: Progressive 1.67
  Price: 9000
  Cost: 3000

...

Row 10:
  ...

... and 490 more rows
```

**Implementation:**
- Uses same parsing logic as Import Job
- Parses file content based on profile.file_format
- Extracts first 10 rows (configurable)
- Formats as human-readable text

---

## Files Created/Modified

### Created
1. **`addons/connector_b/wizards/import_wizard.py`** (226 lines)
   - connector.import.wizard model (TransientModel)
   - File upload and profile selection
   - Preview computation (first 10 rows)
   - Wizard actions (preview, import, cancel)

2. **`addons/connector_b/wizards/import_wizard_views.xml`** (45 lines)
   - Wizard form view
   - Wizard action (modal)
   - Menu item

### Already Prepared (Bootstrap)
3. **`addons/connector_b/wizards/__init__.py`**
   - Already includes: `from . import import_wizard` ✅

4. **`addons/connector_b/__manifest__.py`**
   - Already includes: `'wizards/import_wizard_views.xml'` ✅

---

## Acceptance Criteria

- ✅ Wizard model created (`connector.import.wizard`, TransientModel)
- ✅ Profile selection (many2one, domain: active only)
- ✅ File upload (binary field with filename)
- ✅ Preview computation (first 10 rows, formatted text)
- ✅ Preview action (show preview, reload wizard)
- ✅ Import action (create job, run import, open job form)
- ✅ Cancel action (close wizard)
- ✅ Wizard form view with conditional preview
- ✅ Footer buttons (preview, import, cancel)
- ✅ Modal dialog (target: new)
- ✅ Menu item added (Import Catalog, top of menu)
- ✅ Integration with Import Job (creates and triggers job)

---

## Data Flow

### Scenario: Import Essilor Price List

**Step 1: Open Wizard**
```
User clicks: Connector B → Import Catalog
→ Wizard opens (modal dialog)
```

**Step 2: Select Profile**
```
User selects: "Essilor Price List" profile
→ profile_id set
```

**Step 3: Upload File**
```
User uploads: essilor_prices_2025.xlsx
→ file_data set
→ file_name = "essilor_prices_2025.xlsx"
```

**Step 4: Preview (Optional)**
```
User clicks: "Preview" button
→ action_preview() called
→ _compute_preview_data() triggered
→ Parses file (Excel)
→ Extracts first 10 rows
→ Formats preview text
→ show_preview = True
→ Wizard reloads with preview visible
```

**Step 5: Import**
```
User clicks: "Import" button
→ action_import() called
→ Creates Import Job:
    job = env['connector.import.job'].create({
        'profile_id': profile_id,
        'file_name': file_name,
        'file_data': file_data,
    })
→ Runs import:
    job.action_run_import()
→ Opens Import Job form:
    return action to view job (res_id=job.id)
→ Wizard closes
```

---

## Testing (Future: OPTERP-XX)

**Note:** Unit tests will be created in a future task.

**Planned Tests:**
- test_create_wizard() — Create wizard instance
- test_select_profile() — Select profile
- test_upload_file() — Upload file
- test_preview_xlsx() — Preview Excel file (first 10 rows)
- test_preview_csv_utf8() — Preview CSV UTF-8
- test_preview_csv_cp1251() — Preview CSV Windows-1251
- test_action_import() — Create job and trigger import
- test_action_cancel() — Close wizard
- test_validation_no_file() — Error if no file uploaded
- test_validation_no_profile() — Error if no profile selected

**Coverage Target:** ≥95%

---

## Business Rules

1. **Wizard Type:**
   - TransientModel (temporary, not stored)
   - Deleted after session ends
   - Suitable for one-time operations

2. **Profile Selection:**
   - Only active profiles shown
   - Domain: `[('active', '=', True)]`
   - Required field

3. **File Upload:**
   - Binary field (file content)
   - Required field
   - Filename tracked separately

4. **Preview:**
   - Optional (user can skip)
   - Shows first 10 rows (configurable)
   - Formatted as human-readable text
   - Uses same parsing logic as Import Job

5. **Import Action:**
   - Creates Import Job record
   - Triggers `job.action_run_import()`
   - Opens Job form (user can monitor progress)
   - Wizard closes automatically

6. **Cancel Action:**
   - Closes wizard
   - No job created
   - No import executed

---

## Integration Points

### With Import Profile (OPTERP-41)
- Wizard.profile_id references Import Profile
- Uses profile settings for parsing
- Domain filters active profiles only

### With Import Job (OPTERP-42)
- Wizard creates Import Job record
- Passes profile_id, file_name, file_data
- Triggers job.action_run_import()
- Opens Job form after creation

### With Product Model (Odoo Core)
- Indirect: Wizard → Job → Product import
- No direct interaction

---

## UI/UX Features

### Wizard Form Highlights

**1. Modal Dialog:**
```xml
<field name="target">new</field>
```
- Opens as popup (not full page)
- Focused user experience
- Easy to cancel and return

**2. File Upload Widget:**
```xml
<field name="file_data" filename="file_name" widget="binary"/>
```
- Standard Odoo file picker
- Filename automatically captured
- Supports large files

**3. Conditional Preview:**
```xml
<group name="preview" invisible="not show_preview">
    <field name="preview_data" widget="text"/>
</group>
```
- Hidden by default (reduces clutter)
- Shown after "Preview" button clicked
- Text widget for formatted display

**4. Footer Buttons:**
```xml
<footer>
    <button name="action_preview" class="btn-secondary" invisible="show_preview"/>
    <button name="action_import" class="btn-primary"/>
    <button name="action_cancel" class="btn-secondary"/>
</footer>
```
- Clear action buttons
- Import button highlighted (primary)
- Preview button hidden after preview shown

**5. Button Styling:**
- **Import:** `btn-primary` (blue, highlighted)
- **Preview:** `btn-secondary` (grey, optional)
- **Cancel:** `btn-secondary` (grey, safe exit)

### Wizard Workflow

**Minimal Flow (No Preview):**
1. Select profile
2. Upload file
3. Click "Import"
→ Done (3 clicks)

**Full Flow (With Preview):**
1. Select profile
2. Upload file
3. Click "Preview"
4. Review data
5. Click "Import"
→ Done (5 clicks)

---

## Known Issues

### Issue 1: Requires openpyxl Library
**Description:** Wizard uses openpyxl to parse Excel files for preview.

**Impact:** Same as Import Job (OPTERP-42).

**Resolution:**
- Add to `requirements.txt`: `openpyxl==3.1.2`
- Install when setting up Odoo environment

**Status:** ⏸️ Pending (add to requirements.txt in next phase)

### Issue 2: Preview Performance for Large Files
**Description:** Parsing large files (10k+ rows) for preview may be slow.

**Impact:** User may experience delay after clicking "Preview".

**Resolution:**
- Preview only parses first N rows (configurable)
- Could add loading indicator
- Could make preview async (future enhancement)

**Status:** ⏸️ Acceptable (preview is optional, import is async)

---

## Next Steps

1. **Phase 2 Week 8:** optics_pos_ru54fz Module
   - Offline indicator widget
   - POS config views for KKT adapter
   - Saga pattern (refund blocking)
   - Bulkhead pattern (Celery queues)

2. **Phase 2 Week 9:** UAT Testing
   - UAT-01 to UAT-11 test scenarios
   - Fix critical bugs
   - MVP sign-off

3. **Future Enhancements (connector_b):**
   - **Dry Run Mode:** Validate without importing
   - **Column Mapping Helper:** Auto-detect columns from file
   - **Import Scheduler:** Schedule recurring imports (cron)
   - **Email Notification:** Notify on import completion
   - **Import History:** Track all imports for profile
   - **Batch Import:** Upload multiple files at once
   - **Advanced Preview:** Show more rows (pagination)

---

## References

### Domain Documentation
- **CLAUDE.md:** §3.2 (connector_b module overview)
- **PROJECT_PHASES.md:** Week 7 Day 5 (Import Wizard task)

### Related Tasks
- **OPTERP-38:** Create Prescription Views ✅ COMPLETED
- **OPTERP-39:** Create Lens Views ✅ COMPLETED
- **OPTERP-40:** Create Manufacturing Order Views ✅ COMPLETED
- **OPTERP-41:** Create Import Profile Model ✅ COMPLETED
- **OPTERP-42:** Create Import Job Model ✅ COMPLETED
- **OPTERP-43:** Create Import Wizard ✅ COMPLETED (this task)
- **Phase 2 Week 8:** optics_pos_ru54fz Module (Next)

### Odoo Documentation
- **Odoo 17 Wizards:** TransientModel, act_window target='new'
- **Odoo 17 Views:** Form view, footer buttons, binary widget
- **Odoo 17 Actions:** act_window, act_window_close

### Python Libraries
- **openpyxl:** Excel file parsing (XLSX)
- **csv:** CSV file parsing (built-in)

---

## Timeline

- **Start:** 2025-11-27 19:30
- **End:** 2025-11-27 19:50
- **Duration:** ~20 minutes
- **Lines of Code:** 226 (import_wizard.py) + 45 (import_wizard_views.xml) = **271 lines**

---

**Status:** ✅ WIZARD COMPLETE (Pending Odoo Runtime for Testing)

**Module Status:** connector_b ✅ **COMPLETE** (Profile + Job + Wizard)

**Next Phase:** Week 8 - optics_pos_ru54fz Module

---

🤖 Generated with [Claude Code](https://claude.com/claude-code)
