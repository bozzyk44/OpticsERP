# Task Plan: OPTERP-41 - Create Import Profile Model

**Date:** 2025-11-27
**Status:** ✅ Completed
**Priority:** High
**Assignee:** AI Agent
**Phase:** Phase 2 - MVP (Week 7, Day 1-2)
**Related Commit:** (to be committed)

---

## Objective

Create Odoo model for import profile configuration (connector_b module) with column mapping for supplier catalog imports.

---

## Context

**Background:**
- Part of Week 7: connector_b Module Development
- Import Profile configures how to import supplier catalogs (Excel/CSV)
- Supports 3+ suppliers with customizable column mappings
- Column mapping stored as JSON (flexible schema)

**Scope:**
- Import Profile model with JSON column mapping
- File format configuration (XLSX, CSV UTF-8, CSV Windows-1251)
- Upsert settings (match field, create/update flags)
- Views (tree, form, search) with JSON editor
- Menu integration

---

## Implementation

### 1. Domain Model (from CLAUDE.md)

**Import Profile Purpose:**
- Configure supplier-specific import settings
- Map Excel/CSV columns to Odoo product fields
- Define file format and parsing rules
- Configure upsert behavior (create vs update)

**Supported File Formats:**
- XLSX (Excel 2007+)
- CSV (UTF-8)
- CSV (Windows-1251)

**Column Mapping Example:**
```json
{
  "default_code": "SKU",
  "name": "Product Name",
  "list_price": "Price",
  "standard_price": "Cost",
  "qty_available": "Stock",
  "barcode": "Barcode"
}
```

**Upsert Fields:**
- `default_code` (Product Code) - most common
- `barcode` (Barcode)
- `name` (Product Name)

### 2. Model Created

#### Model: `connector.import.profile` (333 lines)

**Fields:**

**Basic Information:**
- `name` — Profile name (e.g., "Essilor Price List")
- `active` — Active flag (enable/disable profile)
- `sequence` — Ordering sequence

**Supplier Information:**
- `supplier_id` — Many2one to res.partner (supplier)
- `supplier_code` — Optional supplier code

**File Format:**
- `file_format` — Selection (xlsx / csv_utf8 / csv_cp1251)
- `csv_delimiter` — CSV delimiter (default: ,)
- `csv_quote_char` — CSV quote character (default: ")

**Column Mapping:**
- `column_mapping` — Text field (JSON string)
- `column_mapping_json` — Json field (computed/inverse)

**Import Settings:**
- `header_row` — Row number where headers are (default: 1)
- `data_start_row` — Row where data starts (default: 2)
- `skip_empty_rows` — Boolean (skip empty rows)

**Upsert Configuration:**
- `upsert_field` — Selection (default_code / barcode / name)
- `create_missing` — Boolean (create new products if not found)
- `update_existing` — Boolean (update existing products)

**Validation:**
- `validation_rules` — Text (JSON, optional)

**Statistics:**
- `job_count` — Computed (number of import jobs using this profile)
- `last_import_date` — Computed (date of last successful import)

**Additional:**
- `notes` — Text (additional notes)

**Validations:**
1. **Row Numbers:** header_row ≥ 1, data_start_row > header_row
2. **JSON Validation:** column_mapping must be valid JSON dict
3. **CSV Delimiter:** Required for CSV formats, must be single character

**Computed Methods:**
- `_compute_column_mapping_json()` — Convert text → JSON
- `_inverse_column_mapping_json()` — Convert JSON → text
- `_compute_job_count()` — Count import jobs
- `_compute_last_import_date()` — Get last successful import date

**Business Methods:**
- `get_column_mapping_dict()` — Get mapping as Python dict
- `set_column_mapping_dict(mapping)` — Set mapping from dict
- `action_view_import_jobs()` — Open import jobs for this profile
- `get_mapping_summary()` — Get formatted mapping summary

**CRUD Methods:**
- `copy()` — Override to append "(copy)" to name

**Total Lines:** **333 lines** (import_profile.py)

### 3. Views Created

**File:** `addons/connector_b/views/import_profile_views.xml` (171 lines)

**Views:**

1. **Tree View** (`view_connector_import_profile_tree`)
   - Handle widget for sequence (drag & drop)
   - Columns: sequence, name, supplier, format, upsert_field, job_count, last_import_date, active
   - Decoration: Inactive profiles in grey

2. **Form View** (`view_connector_import_profile_form`)
   - **Button Box:**
     - Stat button: Import Jobs count (opens jobs)
     - Archive button (active toggle)
   - **Groups:**
     - Basic Information (supplier, supplier_code, sequence)
     - Statistics (last_import_date readonly)
   - **Notebook:**
     - **Page 1: File Settings**
       - File format (radio widget)
       - CSV settings (visible only for CSV formats)
       - Row configuration (header_row, data_start_row, skip_empty_rows)
     - **Page 2: Column Mapping**
       - JSON editor with ace widget (mode: json)
       - Example mapping and supported fields documentation
     - **Page 3: Upsert Settings**
       - Upsert field (radio widget)
       - Create missing / Update existing flags
       - Documentation about upsert behavior
     - **Page 4: Validation**
       - Validation rules (JSON editor, optional)
     - **Page 5: Notes**
       - Additional notes text field

3. **Search View** (`view_connector_import_profile_search`)
   - Search fields: name, supplier_id, supplier_code
   - **Filters:**
     - Active / Inactive
     - Excel (XLSX) / CSV
   - **Group by:** Supplier, File Format

4. **Action** (`action_connector_import_profile`)
   - Default filter: Active profiles
   - Help text with guidance

### 4. Menu Integration

**Created:** `addons/connector_b/views/menu_views.xml` (23 lines)

**Menu Structure:**
```
Connector B (new root menu)
├── Import Profiles ← NEW (action: action_connector_import_profile)
├── Import Jobs (placeholder for OPTERP-39)
└── Configuration
```

---

## Files Created/Modified

### Created
1. **`addons/connector_b/models/import_profile.py`** (333 lines)
   - connector.import.profile model
   - JSON column mapping with computed/inverse
   - Row number validation
   - Business methods (get/set mapping dict, view jobs, summary)

2. **`addons/connector_b/views/import_profile_views.xml`** (171 lines)
   - Tree view with handle widget (sequence)
   - Form view with JSON editor (ace widget)
   - Search view with filters
   - Action with default filter

3. **`addons/connector_b/views/menu_views.xml`** (23 lines)
   - Root menu (Connector B)
   - Import Profiles menu item
   - Placeholders for future menus

### Already Prepared (Bootstrap)
4. **`addons/connector_b/models/__init__.py`**
   - Already includes: `from . import import_profile` ✅

5. **`addons/connector_b/__manifest__.py`**
   - Already includes: `'views/import_profile_views.xml'` and `'views/menu_views.xml'` ✅

6. **`addons/connector_b/security/ir.model.access.csv`**
   - Already configured: access rules for import_profile (user=read, manager=full) ✅

---

## Acceptance Criteria

- ✅ Import Profile model created (`connector.import.profile`)
- ✅ JSON column mapping (text + JSON field with computed/inverse)
- ✅ File format configuration (xlsx, csv_utf8, csv_cp1251)
- ✅ CSV-specific settings (delimiter, quote_char)
- ✅ Row configuration (header_row, data_start_row, skip_empty_rows)
- ✅ Upsert configuration (upsert_field, create_missing, update_existing)
- ✅ Validation rules (JSON, optional)
- ✅ Statistics (job_count, last_import_date computed fields)
- ✅ Row number validation (header < data_start)
- ✅ JSON validation (column_mapping must be valid JSON dict)
- ✅ CSV delimiter validation
- ✅ Business methods (get/set mapping dict, view jobs, summary)
- ✅ Tree/Form/Search views created
- ✅ JSON editor with ace widget (mode: json)
- ✅ Menu items added (Connector B root, Import Profiles)
- ✅ Security rules configured (already in bootstrap)

---

## Data Model

### connector_import_profile (Main Table)

```sql
CREATE TABLE connector_import_profile (
    id SERIAL PRIMARY KEY,
    name VARCHAR NOT NULL,
    active BOOLEAN DEFAULT TRUE,
    sequence INTEGER DEFAULT 10,
    supplier_id INTEGER REFERENCES res_partner(id),
    supplier_code VARCHAR,

    -- File Format
    file_format VARCHAR CHECK (file_format IN ('xlsx', 'csv_utf8', 'csv_cp1251')) NOT NULL DEFAULT 'xlsx',
    csv_delimiter VARCHAR DEFAULT ',',
    csv_quote_char VARCHAR DEFAULT '"',

    -- Column Mapping
    column_mapping TEXT NOT NULL DEFAULT '{}',

    -- Import Settings
    header_row INTEGER DEFAULT 1,
    data_start_row INTEGER DEFAULT 2,
    skip_empty_rows BOOLEAN DEFAULT TRUE,

    -- Upsert Configuration
    upsert_field VARCHAR CHECK (upsert_field IN ('default_code', 'barcode', 'name')) DEFAULT 'default_code',
    create_missing BOOLEAN DEFAULT TRUE,
    update_existing BOOLEAN DEFAULT TRUE,

    -- Validation
    validation_rules TEXT,

    -- Notes
    notes TEXT,

    -- Constraints
    CONSTRAINT check_row_numbers CHECK (header_row >= 1 AND data_start_row > header_row)
);
```

---

## Example Data

### Sample Import Profiles

**Profile 1: Essilor Price List (Excel)**
```python
{
    'name': 'Essilor Price List',
    'supplier_id': essilor_partner.id,
    'supplier_code': 'ESSILOR',
    'file_format': 'xlsx',
    'header_row': 1,
    'data_start_row': 2,
    'column_mapping': json.dumps({
        'default_code': 'SKU',
        'name': 'Product Name',
        'list_price': 'Retail Price',
        'standard_price': 'Cost',
        'barcode': 'EAN',
    }),
    'upsert_field': 'default_code',
    'create_missing': True,
    'update_existing': True,
}
```

**Profile 2: Hoya Catalog (CSV UTF-8)**
```python
{
    'name': 'Hoya Catalog',
    'supplier_id': hoya_partner.id,
    'file_format': 'csv_utf8',
    'csv_delimiter': ';',
    'header_row': 2,  # Headers on row 2
    'data_start_row': 3,
    'column_mapping': json.dumps({
        'default_code': 'Article Code',
        'name': 'Description',
        'list_price': 'Price EUR',
        'qty_available': 'Stock Qty',
    }),
    'upsert_field': 'default_code',
}
```

**Profile 3: Generic CSV (Windows-1251)**
```python
{
    'name': 'Generic Supplier (Russian)',
    'file_format': 'csv_cp1251',
    'csv_delimiter': ',',
    'header_row': 1,
    'data_start_row': 2,
    'column_mapping': json.dumps({
        'default_code': 'Артикул',
        'name': 'Наименование',
        'list_price': 'Цена',
    }),
    'upsert_field': 'barcode',
    'create_missing': False,  # Only update existing
    'update_existing': True,
}
```

---

## Testing (Future: OPTERP-XX)

**Note:** Unit tests will be created in a future task.

**Planned Tests:**
- test_create_import_profile() — Create with all fields
- test_column_mapping_json_conversion() — Text ↔ JSON conversion
- test_row_number_validation() — header_row < data_start_row
- test_invalid_json_mapping() — Invalid JSON → ValidationError
- test_csv_delimiter_validation() — Required for CSV formats
- test_get_column_mapping_dict() — Get mapping as dict
- test_set_column_mapping_dict() — Set mapping from dict
- test_action_view_import_jobs() — Open jobs for profile
- test_copy_profile() — Duplicate profile (name appends "(copy)")
- test_job_count_computation() — Count import jobs
- test_last_import_date_computation() — Get last successful import date

**Coverage Target:** ≥95%

---

## Business Rules

1. **Column Mapping:**
   - Stored as JSON string (text field)
   - Exposed as JSON field (computed/inverse)
   - Must be valid JSON dict
   - Maps Odoo field names to file column names

2. **Row Numbers:**
   - header_row ≥ 1 (1-indexed)
   - data_start_row > header_row (data must be after headers)

3. **File Format:**
   - XLSX: Excel 2007+ format
   - CSV UTF-8: Standard CSV with UTF-8 encoding
   - CSV Windows-1251: Legacy CSV for Russian suppliers

4. **CSV Settings:**
   - Delimiter required for CSV formats
   - Must be single character (except special: \t, \n, \r)
   - Quote character default: "

5. **Upsert Behavior:**
   - **Upsert Field:** Field used to match existing products
   - **Create Missing:** Create new products if not found
   - **Update Existing:** Update existing products if found
   - All combinations allowed (e.g., update only, create only, both)

---

## Integration Points

### With Import Job Model (OPTERP-39)
- Import Job references Import Profile (Many2one)
- Profile.job_count computed from Import Job records
- Profile.last_import_date from latest successful job

### With Product Model (Odoo Core)
- Column mapping maps to product.product fields
- Upsert field matches against product records
- Supported fields: default_code, name, list_price, standard_price, barcode, categ_id, qty_available

### With Supplier (res.partner)
- Profile.supplier_id links to partner (supplier)
- Domain: supplier_rank > 0

---

## UI/UX Features

### Form View Highlights

**1. JSON Editor (ace widget):**
```xml
<field name="column_mapping" widget="ace" options="{'mode': 'json'}" nolabel="1"/>
```
- Syntax highlighting for JSON
- Validation on save
- Example mapping shown below editor

**2. Conditional Fields:**
```xml
<field name="csv_delimiter" invisible="file_format not in ('csv_utf8', 'csv_cp1251')"/>
```
- CSV settings only visible for CSV formats
- Cleaner UI, less confusion

**3. Radio Widgets:**
```xml
<field name="file_format" widget="radio"/>
<field name="upsert_field" widget="radio"/>
```
- Better UX for selection fields (3 options)
- All options visible at once

**4. Stat Buttons:**
```xml
<button name="action_view_import_jobs" type="object" class="oe_stat_button" icon="fa-tasks">
    <field name="job_count" widget="statinfo" string="Import Jobs"/>
</button>
```
- Quick access to related import jobs
- Shows count of jobs using this profile

### Tree View Highlights

**1. Handle Widget (Sequence):**
```xml
<field name="sequence" widget="handle"/>
```
- Drag & drop to reorder profiles
- Intuitive ordering

**2. Boolean Toggle:**
```xml
<field name="active" widget="boolean_toggle"/>
```
- Quick enable/disable from tree view
- No need to open form

---

## Known Issues

None (model and views created, pending Odoo runtime for testing).

---

## Next Steps

1. **OPTERP-39:** Create Import Job Model
   - Import job with file upload
   - State machine (draft → running → done/failed)
   - Relation to import logs

2. **OPTERP-40:** Create Import Wizard
   - File upload widget
   - Profile selection
   - Preview first 10 rows
   - Confirm trigger

3. **Phase 2 Week 7:** Complete connector_b module

4. **Future Enhancements:**
   - Import scheduler (cron jobs)
   - Email notification on import completion
   - Import templates (pre-filled profiles for common suppliers)
   - Column mapping wizard (auto-detect columns)
   - Data transformation rules (e.g., price conversion, category mapping)

---

## References

### Domain Documentation
- **CLAUDE.md:** §3.2 (connector_b module overview)
- **PROJECT_PHASES.md:** Week 7 Day 1-2 (Import Profile task)

### Related Tasks
- **OPTERP-32:** Create Prescription Model ✅ COMPLETED
- **OPTERP-33:** Create Prescription Unit Tests ✅ COMPLETED
- **OPTERP-34:** Create Lens Model ✅ COMPLETED
- **OPTERP-35:** Create Lens Unit Tests ✅ COMPLETED
- **OPTERP-36:** Create Manufacturing Order Model ✅ COMPLETED
- **OPTERP-37:** Create Manufacturing Order Unit Tests ✅ COMPLETED
- **OPTERP-41:** Create Import Profile Model ✅ COMPLETED (this task)
- **OPTERP-42:** Create Import Job Model (Next)

### Odoo Documentation
- **Odoo 17 ORM:** Model definition, fields, JSON fields, computed/inverse
- **Odoo 17 Views:** Tree, form, search, ace widget, handle widget
- **Odoo 17 Widgets:** ace (JSON editor), handle (drag & drop), radio, boolean_toggle

---

## Timeline

- **Start:** 2025-11-27 17:20
- **End:** 2025-11-27 17:50
- **Duration:** ~30 minutes
- **Lines of Code:** 333 (import_profile.py) + 171 (import_profile_views.xml) + 23 (menu_views.xml) = **527 lines**

---

**Status:** ✅ MODEL COMPLETE (Pending Odoo Runtime for Testing)

**Next Task:** OPTERP-39 (Create Import Job Model)

---

🤖 Generated with [Claude Code](https://claude.com/claude-code)
