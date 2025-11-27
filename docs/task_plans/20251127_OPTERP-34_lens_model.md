# Task Plan: OPTERP-34 - Create Lens Model

**Date:** 2025-11-27
**Status:** ✅ Completed
**Priority:** Medium
**Assignee:** AI Agent
**Phase:** Phase 2 - MVP (Week 6, Day 3-4)
**Related Commit:** (to be committed)

---

## Objective

Create Odoo model for optical lens catalog with specifications (type, index, material, coatings).

---

## Context

**Background:**
- Part of Week 6: Odoo Models (optics_core)
- Lens model represents lens products in optical retail catalog
- Used in Manufacturing Orders to specify which lens to produce

**Scope:**
- Lens model with full specifications
- Coating model (many2many relation)
- Views (tree, form, search)
- Menu integration

---

## Implementation

### 1. Domain Model (from GLOSSARY.md)

**Lens Types:**
- Single Vision (одна оптическая сила)
- Bifocal (две зоны: даль + близь)
- Progressive (плавный переход)

**Refractive Index:**
- 1.5 (standard)
- 1.6 (thin)
- 1.67 (ultra-thin)
- 1.74 (super-thin)
- Range: 1.5-1.9

**Materials:**
- CR-39 (Plastic) - standard plastic
- Polycarbonate - impact resistant
- Trivex - lightweight, impact resistant
- High-Index Glass - thinnest, heaviest

**Coatings (many2many):**
- AR (Anti-Reflective) - антибликовое
- HC (Hard Coating) - упрочняющее
- UV - УФ-защита
- Photochromic - фотохромное (затемнение)

### 2. Models Created

#### Model: `optics.lens` (318 lines)

**Fields:**
- **Basic:** name, active
- **Specification:** type (selection), index (float 1.5-1.9), material (selection)
- **Coatings:** coating_ids (many2many → optics.lens.coating)
- **Pricing:** cost_price, sale_price
- **Physical:** diameter, center_thickness, weight
- **Manufacturer:** manufacturer, sku (unique)
- **Info:** description, notes
- **Computed:** display_name, coating_summary

**Validations:**
1. **Index range:** 1.5-1.9 (SQL + Python)
2. **Prices positive:** cost_price ≥ 0, sale_price ≥ 0
3. **Dimensions positive:** diameter > 0, center_thickness > 0, weight > 0
4. **Unique SKU:** SKU must be unique (SQL)

**SQL Constraints:** 4
- check_index_range
- check_cost_price_positive
- check_sale_price_positive
- unique_sku

**Python Constraints:** 3
- _check_index_range()
- _check_prices_positive()
- _check_dimensions_positive()

**Business Methods:**
- `_compute_display_name()`: "Name (Type, Index)"
- `_compute_coating_summary()`: "AR+HC+UV"
- `get_full_specification()`: Full lens spec as formatted string

#### Model: `optics.lens.coating` (87 lines)

**Fields:**
- name (coating full name)
- code (short code: AR, HC, UV)
- description (benefits and features)
- sequence (display order)
- active
- additional_cost (added to lens price)

**SQL Constraints:** 1
- unique_code (coating code must be unique)

**Total Lines:** 318 + 87 = **405 lines** (lens.py)

### 3. Views Created

**File:** `addons/optics_core/views/lens_views.xml` (210 lines)

**Views for optics.lens:**
1. **Tree View** (`view_optics_lens_tree`)
   - Columns: name, type, index, material, coating_summary, manufacturer, sale_price

2. **Form View** (`view_optics_lens_form`)
   - Groups: Specification, Manufacturer, Pricing, Physical Properties
   - Notebook: Description, Internal Notes
   - Button box: Archive button

3. **Search View** (`view_optics_lens_search`)
   - Search fields: name, manufacturer, sku, type, material, coating_ids
   - Filters: Single Vision, Bifocal, Progressive, Archived
   - Group by: Type, Material, Manufacturer

4. **Action** (`action_optics_lens`)
   - Default filter: Single Vision lenses

**Views for optics.lens.coating:**
5. **Tree View** (`view_optics_lens_coating_tree`)
   - Editable: bottom (quick editing)
   - Columns: sequence (handle), name, code, additional_cost, description

6. **Form View** (`view_optics_lens_coating_form`)
   - Fields: name, code, sequence, additional_cost, description

7. **Action** (`action_optics_lens_coating`)

### 4. Menu Integration

**Updated:** `addons/optics_core/views/menu_views.xml`

**Added:**
1. **Lenses** menu item (parent: Optics root, action: action_optics_lens)
2. **Lens Coatings** menu item (parent: Configuration, action: action_optics_lens_coating)

**Menu Structure:**
```
Optics
├── Prescriptions
├── Lenses ← NEW
├── Manufacturing Orders (placeholder)
└── Configuration
    └── Lens Coatings ← NEW
```

---

## Files Created/Modified

### Created
1. **`addons/optics_core/models/lens.py`** (405 lines)
   - optics.lens model (318 lines)
   - optics.lens.coating model (87 lines)

2. **`addons/optics_core/views/lens_views.xml`** (210 lines)
   - 7 views (tree, form, search for both models)
   - 2 actions

### Modified
3. **`addons/optics_core/views/menu_views.xml`**
   - Added Lenses menu item
   - Added Lens Coatings menu item (under Configuration)

### Already Prepared (Bootstrap)
4. **`addons/optics_core/models/__init__.py`**
   - Already includes: `from . import lens` ✅

5. **`addons/optics_core/__manifest__.py`**
   - Already includes: `'views/lens_views.xml'` ✅

---

## Acceptance Criteria

- ✅ Lens model created (`optics.lens`)
- ✅ Lens Coating model created (`optics.lens.coating`)
- ✅ Types (single/bifocal/progressive) implemented as selection
- ✅ Index validation (1.5-1.9) with SQL + Python constraints
- ✅ Material selection (CR-39, Polycarbonate, Trivex, High-Index)
- ✅ Coatings (many2many relation)
- ✅ Pricing fields (cost_price, sale_price) with validation
- ✅ Physical properties (diameter, thickness, weight) with validation
- ✅ SKU uniqueness constraint
- ✅ Display name computed: "Name (Type, Index)"
- ✅ Coating summary computed: "AR+HC+UV"
- ✅ Tree/Form/Search views created
- ✅ Menu items added (Lenses, Lens Coatings)
- ✅ Business method: get_full_specification()

---

## Data Model

### optics.lens (Main Table)

```sql
CREATE TABLE optics_lens (
    id SERIAL PRIMARY KEY,
    name VARCHAR NOT NULL,
    active BOOLEAN DEFAULT TRUE,
    type VARCHAR CHECK (type IN ('single', 'bifocal', 'progressive')),
    index NUMERIC(3,2) CHECK (index >= 1.5 AND index <= 1.9),
    material VARCHAR CHECK (material IN ('cr39', 'polycarbonate', 'trivex', 'high_index')),
    cost_price NUMERIC CHECK (cost_price >= 0 OR cost_price IS NULL),
    sale_price NUMERIC CHECK (sale_price >= 0 OR sale_price IS NULL),
    diameter NUMERIC,
    center_thickness NUMERIC(4,2),
    weight NUMERIC(5,2),
    manufacturer VARCHAR,
    sku VARCHAR UNIQUE,
    description TEXT,
    notes TEXT
);
```

### optics_lens_coating (Coating Table)

```sql
CREATE TABLE optics_lens_coating (
    id SERIAL PRIMARY KEY,
    name VARCHAR NOT NULL,
    code VARCHAR UNIQUE NOT NULL,
    description TEXT,
    sequence INTEGER DEFAULT 10,
    active BOOLEAN DEFAULT TRUE,
    additional_cost NUMERIC
);
```

### optics_lens_coating_rel (Many2Many Relation)

```sql
CREATE TABLE optics_lens_coating_rel (
    lens_id INTEGER REFERENCES optics_lens(id),
    coating_id INTEGER REFERENCES optics_lens_coating(id),
    PRIMARY KEY (lens_id, coating_id)
);
```

---

## Example Data

### Sample Lenses

```python
# Single Vision Standard
{
    'name': 'Single Vision CR-39 1.5',
    'type': 'single',
    'index': 1.5,
    'material': 'cr39',
    'manufacturer': 'Essilor',
    'sku': 'ESS-SV-CR39-15',
    'cost_price': 500.0,
    'sale_price': 1500.0,
}

# Progressive High-Index
{
    'name': 'Varilux Progressive 1.67',
    'type': 'progressive',
    'index': 1.67,
    'material': 'high_index',
    'manufacturer': 'Essilor',
    'sku': 'ESS-VLX-HI-167',
    'cost_price': 5000.0,
    'sale_price': 15000.0,
    'coating_ids': [(6, 0, [ar_id, hc_id, uv_id])],  # AR+HC+UV
}

# Polycarbonate Impact-Resistant
{
    'name': 'Polycarbonate Safety Lens',
    'type': 'single',
    'index': 1.59,
    'material': 'polycarbonate',
    'manufacturer': 'Hoya',
    'sku': 'HOYA-POLY-159',
    'cost_price': 800.0,
    'sale_price': 2400.0,
}
```

### Sample Coatings

```python
[
    {'name': 'Anti-Reflective Coating', 'code': 'AR', 'additional_cost': 500.0},
    {'name': 'Hard Coating', 'code': 'HC', 'additional_cost': 300.0},
    {'name': 'UV Protection', 'code': 'UV', 'additional_cost': 200.0},
    {'name': 'Photochromic (Transitions)', 'code': 'PC', 'additional_cost': 2000.0},
    {'name': 'Blue Light Filter', 'code': 'BLF', 'additional_cost': 800.0},
]
```

---

## Testing (OPTERP-35)

**Note:** Unit tests will be created in next task (OPTERP-35).

**Planned Tests:**
- test_lens_types() - Single/Bifocal/Progressive
- test_index_range() - 1.5-1.9 validation
- test_index_out_of_range() - 1.4, 2.0 → ValidationError
- test_coating_options() - Many2many relation
- test_prices_positive() - Negative prices → ValidationError
- test_sku_unique() - Duplicate SKU → IntegrityError
- test_display_name() - "Name (Type, Index)"
- test_coating_summary() - "AR+HC+UV"
- test_get_full_specification() - Formatted string

**Coverage Target:** ≥95%

---

## Business Rules

1. **Index Range:** 1.5-1.9 (higher index = thinner lens)
2. **Material Properties:**
   - CR-39: Standard plastic, good optical clarity
   - Polycarbonate: Impact resistant, UV protection
   - Trivex: Lightweight, impact resistant
   - High-Index: Thinnest, best for strong prescriptions

3. **Pricing:**
   - Cost price = supplier cost
   - Sale price = retail price to customer
   - Additional coating costs added to base lens price

4. **Coatings:**
   - Multiple coatings can be combined (many2many)
   - Each coating has additional cost
   - Display as summary: "AR+HC+UV"

5. **SKU:**
   - Must be unique
   - Format: MANUFACTURER-TYPE-MATERIAL-INDEX (e.g., ESS-SV-CR39-15)

---

## Integration Points

### With Prescription Model
- Lens selected based on prescription parameters (Sph, Cyl, Axis)
- Progressive lenses for Add values (presbyopia)
- High index for strong prescriptions (Sph > ±6.00)

### With Manufacturing Order
- MO specifies which lens to produce
- Links: prescription_id → lens_id
- Workflow: Draft → Production → Ready → Delivered

### With Product Catalog
- Lens can be linked to product.product (stock management)
- Price from lens.sale_price
- Coatings affect final price

---

## Known Issues

None (model and views created, pending Odoo runtime for testing).

---

## Next Steps

1. **OPTERP-35:** Create Lens Unit Tests
   - 9+ test methods
   - Coverage ≥95%
   - Test execution when Odoo runtime ready

2. **Phase 2 Week 6 Day 5:** Manufacturing Order Model (OPTERP-36)

3. **Phase 2 Week 7:** Odoo Views for all models

4. **Future Enhancements:**
   - Lens availability/stock tracking
   - Lead time calculation
   - Vendor/supplier integration
   - Image attachments (lens photos)

---

## References

### Domain Documentation
- **GLOSSARY.md:** Lines 308-326 (Lens definition)
- **CLAUDE.md:** §3.2 (optics_core module)
- **PROJECT_PHASES.md:** Week 6 Day 3-4 (Lens Model task)

### Related Tasks
- **OPTERP-32:** Create Prescription Model ✅ COMPLETED
- **OPTERP-33:** Create Prescription Unit Tests ✅ COMPLETED
- **OPTERP-34:** Create Lens Model ✅ COMPLETED (this task)
- **OPTERP-35:** Create Lens Unit Tests (Next)
- **OPTERP-36:** Create Manufacturing Order Model (Pending)

---

## Timeline

- **Start:** 2025-11-27 14:30
- **End:** 2025-11-27 15:00
- **Duration:** ~30 minutes
- **Lines of Code:** 405 (lens.py) + 210 (lens_views.xml) = **615 lines**

---

**Status:** ✅ MODEL COMPLETE (Pending Odoo Runtime for Testing)

**Next Task:** OPTERP-35 (Create Lens Unit Tests)

---

🤖 Generated with [Claude Code](https://claude.com/claude-code)
