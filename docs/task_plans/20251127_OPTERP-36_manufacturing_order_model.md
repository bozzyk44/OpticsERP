# Task Plan: OPTERP-36 - Create Manufacturing Order Model

**Date:** 2025-11-27
**Status:** ✅ Completed
**Priority:** Medium
**Assignee:** AI Agent
**Phase:** Phase 2 - MVP (Week 6, Day 5)
**Related Commit:** (to be committed)

---

## Objective

Create Odoo model for lens manufacturing work orders with complete workflow (Draft → Confirmed → In Production → Ready → Delivered).

---

## Context

**Background:**
- Part of Week 6: Odoo Models (optics_core)
- Manufacturing Order represents work order for lens production
- Links prescription and lens specification
- Tracks timeline from order to delivery (3-14 days depending on lens type)

**Scope:**
- Manufacturing Order model with workflow state machine
- Date tracking for each workflow stage
- Expected delivery calculation based on lens type
- Views (tree, form, search) with workflow buttons
- Menu integration

---

## Implementation

### 1. Domain Model (from GLOSSARY.md)

**Manufacturing Order (MO) Definition:**
- Рабочий заказ на изготовление линзы
- Links: Prescription → Lens → Work Order
- Timeline: 3-14 days (зависит от типа линзы)
- Workflow: Draft → Confirmed → In Production → Ready → Delivered

**Lead Times:**
- Single Vision: 3 days (стандартные линзы)
- Bifocal: 7 days (бифокальные)
- Progressive: 14 days (прогрессивные, сложнее изготовить)

**Business Rules:**
- Cannot skip workflow states (must follow sequence)
- State transitions validated (only valid next states allowed)
- Timeline tracked from confirmation to delivery
- Can cancel at any stage (except delivered)
- Can reset cancelled orders to draft

### 2. Model Created

#### Model: `optics.manufacturing.order` (402 lines)

**Fields:**

**Basic Information:**
- `name` — Order Reference (auto-generated from ir.sequence)
- `active` — Archive flag

**Customer and Prescription:**
- `customer_id` — Many2one to res.partner (required)
- `prescription_id` — Many2one to optics.prescription (required)
- `lens_id` — Many2one to optics.lens (required)

**Dates (Timeline):**
- `date_order` — Order creation date (default: now)
- `date_confirmed` — When order was confirmed (readonly)
- `date_production_start` — When production started (readonly)
- `date_ready` — When order ready for delivery (readonly)
- `date_delivered` — When order delivered to customer (readonly)

**Workflow State:**
```python
state = fields.Selection([
    ('draft', 'Draft'),
    ('confirmed', 'Confirmed'),
    ('production', 'In Production'),
    ('ready', 'Ready'),
    ('delivered', 'Delivered'),
    ('cancelled', 'Cancelled')
], default='draft', tracking=True)
```

**Additional Information:**
- `notes` — Customer-facing notes and special instructions
- `production_notes` — Internal notes for production team

**Computed Fields:**
- `expected_delivery_date` — Calculated from confirmation date + lead time (based on lens type)
- `duration_days` — Actual duration from confirmation to delivery
- `is_late` — Boolean flag if order past expected delivery date

**Validations:**
1. **State Transitions:** Enforced by action methods (can't skip states)
2. **Chronological Dates:** `_check_dates_order()` ensures dates in correct sequence
3. **Required Fields at Confirmation:** Prescription and Lens required to confirm

**SQL Constraints:** 1
- `check_dates_positive` — Ensures dates are in chronological order (DB level)

**Python Constraints:** 1
- `_check_dates_order()` — Validates chronological order of workflow dates

**Workflow Action Methods:**
1. `action_confirm()` — Draft → Confirmed (sets date_confirmed)
2. `action_start_production()` — Confirmed → Production (sets date_production_start)
3. `action_mark_ready()` — Production → Ready (sets date_ready)
4. `action_deliver()` — Ready → Delivered (sets date_delivered)
5. `action_cancel()` — Any state → Cancelled (except delivered)
6. `action_reset_to_draft()` — Cancelled → Draft (clears all dates)

**Business Methods:**
- `_compute_expected_delivery_date()` — Calculate expected delivery based on lens type
- `_compute_duration_days()` — Calculate actual duration (confirmed → delivered)
- `_compute_is_late()` — Check if order past expected delivery date
- `get_workflow_info()` — Get formatted workflow information string

**CRUD Methods:**
- `create()` — Override to generate sequence for order reference

**Total Lines:** **402 lines** (manufacturing_order.py)

### 3. Views Created

**File:** `addons/optics_core/views/manufacturing_order_views.xml` (183 lines)

**Views:**

1. **Tree View** (`view_optics_manufacturing_order_tree`)
   - Columns: name, customer, prescription, lens, date_order, expected_delivery, state
   - Decoration: Late orders in red, cancelled in grey
   - Badge widget for state (color-coded)

2. **Form View** (`view_optics_manufacturing_order_form`)
   - **Header:** Workflow buttons + statusbar
     - Confirm (visible in draft)
     - Start Production (visible in confirmed)
     - Mark Ready (visible in production)
     - Deliver (visible in ready)
     - Cancel (visible except delivered/cancelled)
     - Reset to Draft (visible in cancelled)
   - **Alert Banner:** Warning for late orders (⚠️ Late Order!)
   - **Groups:**
     - Customer Information (customer_id, date_order)
     - Delivery Information (expected_delivery_date, duration_days)
     - Prescription (prescription_id)
     - Lens Specification (lens_id)
     - Timeline (all date fields readonly)
   - **Notebook:**
     - Notes (customer-facing)
     - Production Notes (internal)
   - **Chatter:** Message tracking (tracking=True on state)

3. **Search View** (`view_optics_manufacturing_order_search`)
   - Search fields: name, customer_id, prescription_id, lens_id
   - **Filters:**
     - By state: Draft, Confirmed, In Production, Ready, Delivered, Cancelled
     - Late Orders (is_late = True)
     - Active (states: draft/confirmed/production/ready)
     - Archived (active = False)
   - **Group by:** Status, Customer, Lens, Order Date

4. **Action** (`action_optics_manufacturing_order`)
   - Default filter: Active orders (search_default_filter_active)
   - Help text with guidance

### 4. Menu Integration

**Updated:** `addons/optics_core/views/menu_views.xml`

**Changed:**
- Removed "placeholder" comment
- Added `action="action_optics_manufacturing_order"` to menu item

**Menu Structure:**
```
Optics
├── Prescriptions
├── Lenses
├── Manufacturing Orders ← UPDATED (now functional)
└── Configuration
    └── Lens Coatings
```

---

## Files Created/Modified

### Created
1. **`addons/optics_core/models/manufacturing_order.py`** (402 lines)
   - optics.manufacturing.order model
   - 6 workflow action methods
   - 3 computed fields
   - 1 SQL constraint, 1 Python constraint
   - 1 business method (get_workflow_info)

2. **`addons/optics_core/views/manufacturing_order_views.xml`** (183 lines)
   - Tree view with decorations
   - Form view with workflow buttons, alert banner, timeline
   - Search view with filters and group by
   - Action with default filter

### Modified
3. **`addons/optics_core/views/menu_views.xml`**
   - Added action to Manufacturing Orders menu item

### Already Prepared (Bootstrap)
4. **`addons/optics_core/models/__init__.py`**
   - Already includes: `from . import manufacturing_order` ✅

5. **`addons/optics_core/__manifest__.py`**
   - Already includes: `'views/manufacturing_order_views.xml'` ✅

---

## Acceptance Criteria

- ✅ Manufacturing Order model created (`optics.manufacturing.order`)
- ✅ Workflow states implemented (draft/confirmed/production/ready/delivered/cancelled)
- ✅ State transition methods with validation (6 action methods)
- ✅ Date tracking for each workflow stage (5 date fields)
- ✅ Expected delivery calculation based on lens type (3/7/14 days)
- ✅ Duration calculation (confirmation → delivery)
- ✅ Late order detection (is_late computed field)
- ✅ Chronological date validation (SQL + Python)
- ✅ Sequence generation for order reference (ir.sequence)
- ✅ Tree/Form/Search views created
- ✅ Workflow buttons in form view (header)
- ✅ Late order alert banner in form view
- ✅ Menu item updated with action
- ✅ Chatter integration (message tracking)

---

## Data Model

### optics_manufacturing_order (Main Table)

```sql
CREATE TABLE optics_manufacturing_order (
    id SERIAL PRIMARY KEY,
    name VARCHAR NOT NULL DEFAULT 'New',
    active BOOLEAN DEFAULT TRUE,
    customer_id INTEGER REFERENCES res_partner(id) NOT NULL,
    prescription_id INTEGER REFERENCES optics_prescription(id) NOT NULL,
    lens_id INTEGER REFERENCES optics_lens(id) NOT NULL,

    -- Dates
    date_order TIMESTAMP NOT NULL DEFAULT NOW(),
    date_confirmed TIMESTAMP,
    date_production_start TIMESTAMP,
    date_ready TIMESTAMP,
    date_delivered TIMESTAMP,
    expected_delivery_date DATE,  -- Computed, stored

    -- Workflow
    state VARCHAR CHECK (state IN ('draft', 'confirmed', 'production', 'ready', 'delivered', 'cancelled')) DEFAULT 'draft',

    -- Notes
    notes TEXT,
    production_notes TEXT,

    -- Constraints
    CONSTRAINT check_dates_positive CHECK (
        date_order <= COALESCE(date_confirmed, date_order) AND
        COALESCE(date_confirmed, date_order) <= COALESCE(date_production_start, COALESCE(date_confirmed, date_order)) AND
        COALESCE(date_production_start, COALESCE(date_confirmed, date_order)) <= COALESCE(date_ready, COALESCE(date_production_start, COALESCE(date_confirmed, date_order))) AND
        COALESCE(date_ready, COALESCE(date_production_start, COALESCE(date_confirmed, date_order))) <= COALESCE(date_delivered, COALESCE(date_ready, COALESCE(date_production_start, COALESCE(date_confirmed, date_order))))
    )
);
```

---

## Example Workflow

### Scenario: Progressive Lens Order

**Step 1: Create Draft Order**
```python
order = self.env['optics.manufacturing.order'].create({
    'customer_id': customer.id,
    'prescription_id': prescription.id,
    'lens_id': progressive_lens.id,
    'notes': 'Customer prefers thin lenses',
})
# name = 'MO/2025/001' (auto-generated)
# state = 'draft'
```

**Step 2: Confirm Order**
```python
order.action_confirm()
# state = 'confirmed'
# date_confirmed = 2025-11-27 10:00:00
# expected_delivery_date = 2025-12-11 (14 days for progressive)
```

**Step 3: Start Production**
```python
order.action_start_production()
# state = 'production'
# date_production_start = 2025-11-27 11:00:00
```

**Step 4: Mark Ready**
```python
order.action_mark_ready()
# state = 'ready'
# date_ready = 2025-12-10 15:00:00
```

**Step 5: Deliver**
```python
order.action_deliver()
# state = 'delivered'
# date_delivered = 2025-12-10 16:00:00
# duration_days = 13 (within 14-day lead time)
# is_late = False
```

---

## Testing (OPTERP-37)

**Note:** Unit tests will be created in next task (OPTERP-37).

**Planned Tests:**
- test_create_manufacturing_order() — Create with all required fields
- test_workflow_draft_to_confirmed() — Test confirmation
- test_workflow_confirmed_to_production() — Test production start
- test_workflow_production_to_ready() — Test mark ready
- test_workflow_ready_to_delivered() — Test delivery
- test_workflow_cancel() — Test cancellation
- test_workflow_reset_to_draft() — Test reset from cancelled
- test_invalid_state_transitions() — Test validation (skip states → UserError)
- test_expected_delivery_calculation() — Test lead time (3/7/14 days)
- test_chronological_dates_validation() — Test date order constraint
- test_late_order_detection() — Test is_late computation
- test_duration_calculation() — Test duration_days
- test_sequence_generation() — Test auto-generated name
- test_get_workflow_info() — Test business method

**Coverage Target:** ≥95%

---

## Business Rules

1. **Workflow States (Cannot Skip):**
   ```
   Draft → Confirmed → In Production → Ready → Delivered
   Any state → Cancelled (except delivered)
   Cancelled → Draft (reset)
   ```

2. **Lead Times by Lens Type:**
   - Single Vision: 3 days (простые линзы)
   - Bifocal: 7 days (средняя сложность)
   - Progressive: 14 days (сложные, требуют точной подгонки)

3. **Date Tracking:**
   - All dates readonly except date_order
   - Dates set automatically on state transitions
   - Chronological order enforced (SQL + Python)

4. **Late Order Detection:**
   - Computed field `is_late`
   - Only active in states: confirmed, production, ready
   - Compares today vs expected_delivery_date
   - Visual alert in form view (red banner)

5. **Validation Rules:**
   - Prescription and Lens required to confirm order
   - Cannot confirm unless in draft state
   - Cannot start production unless confirmed
   - Cannot mark ready unless in production
   - Cannot deliver unless ready
   - Cannot cancel delivered orders
   - Cannot reset to draft unless cancelled

---

## Integration Points

### With Prescription Model (OPTERP-32)
- Manufacturing Order references prescription
- Prescription contains optical parameters (Sph, Cyl, Axis, Add)
- Prescription determines lens requirements

### With Lens Model (OPTERP-34)
- Manufacturing Order references lens
- Lens type determines lead time (3/7/14 days)
- Lens specifications used in production

### With POS Module (Future)
- POS order can create Manufacturing Order
- Links: sale.order → manufacturing.order
- Payment → trigger MO creation

### With Inventory (Future)
- MO completion → update stock (lens ready for pickup)
- Stock location: Work in Progress → Finished Goods

---

## UI/UX Features

### Form View Highlights

**1. Workflow Buttons (Header):**
- Context-aware (only show valid next actions)
- Color-coded: Primary buttons in blue (oe_highlight)
- Clear action names (Confirm, Start Production, Mark Ready, Deliver)

**2. Late Order Alert:**
```xml
<div class="alert alert-danger" role="alert" invisible="not is_late">
    <strong>⚠️ Late Order!</strong> This order is past its expected delivery date.
</div>
```

**3. Timeline Group:**
- Shows all workflow dates readonly
- Clear labels (Confirmed, Production Start, Ready, Delivered)
- Empty until state transition occurs

**4. Archive Button:**
- Stat button in button_box
- Terminology: "archive" (not "active")

**5. Chatter:**
- Message tracking (tracking=True on state field)
- Automatic messages on state changes
- Followers can subscribe to order updates

### Tree View Highlights

**1. Decorations:**
- Late orders: Red text (`decoration-danger="is_late"`)
- Cancelled orders: Grey text (`decoration-muted="state=='cancelled'"`)

**2. Badge Widget:**
```xml
<field name="state" widget="badge"
       decoration-info="state=='draft'"
       decoration-warning="state in ('confirmed','production')"
       decoration-success="state=='ready'"
       decoration-primary="state=='delivered'"
       decoration-muted="state=='cancelled'"/>
```

### Search View Highlights

**1. Quick Filters:**
- One-click access to each state
- Late Orders filter (critical for management)
- Active orders filter (default)

**2. Group By:**
- Status (see orders by workflow stage)
- Customer (see all orders for customer)
- Lens (see which lenses most ordered)
- Order Date (timeline view)

---

## Known Issues

None (model and views created, pending Odoo runtime for testing).

---

## Next Steps

1. **OPTERP-37:** Create Manufacturing Order Unit Tests
   - Test all workflow transitions
   - Test validation rules
   - Test computed fields (expected_delivery, duration, is_late)
   - Test chronological date validation
   - Coverage ≥95%

2. **Phase 2 Week 7:** Odoo Views refinements (if needed)

3. **Future Enhancements:**
   - Quality control step (before mark ready)
   - Auto-notification to customer when ready
   - Integration with external lab (for outsourced lenses)
   - Barcode scanning for tracking
   - Production time analytics (actual vs expected)
   - Capacity planning (workload by production stage)

---

## References

### Domain Documentation
- **GLOSSARY.md:** Lines 342-356 (Manufacturing Order definition)
- **CLAUDE.md:** §3.2 (optics_core module), §6 (Architecture)
- **PROJECT_PHASES.md:** Week 6 Day 5 (Manufacturing Order Model task)

### Related Tasks
- **OPTERP-32:** Create Prescription Model ✅ COMPLETED
- **OPTERP-33:** Create Prescription Unit Tests ✅ COMPLETED
- **OPTERP-34:** Create Lens Model ✅ COMPLETED
- **OPTERP-35:** Create Lens Unit Tests ✅ COMPLETED
- **OPTERP-36:** Create Manufacturing Order Model ✅ COMPLETED (this task)
- **OPTERP-37:** Create Manufacturing Order Unit Tests (Next)

### Odoo Documentation
- **Odoo 17 ORM:** Model definition, fields, computed fields, constraints
- **Odoo 17 Views:** Form, tree, search, statusbar widget, badge widget
- **Odoo 17 Workflow:** State field, action methods, tracking

---

## Timeline

- **Start:** 2025-11-27 16:00
- **End:** 2025-11-27 16:30
- **Duration:** ~30 minutes
- **Lines of Code:** 402 (manufacturing_order.py) + 183 (manufacturing_order_views.xml) = **585 lines**

---

**Status:** ✅ MODEL COMPLETE (Pending Odoo Runtime for Testing)

**Next Task:** OPTERP-37 (Create Manufacturing Order Unit Tests)

---

🤖 Generated with [Claude Code](https://claude.com/claude-code)
