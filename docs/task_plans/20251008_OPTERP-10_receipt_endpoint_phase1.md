# Task Plan: OPTERP-10 - Implement Receipt Endpoint (Phase 1)

**Date:** 2025-10-08
**Status:** In Progress
**Priority:** Highest
**Assignee:** AI Agent

---

## Objective

Complete Phase 1 implementation of `/v1/kkt/receipt` endpoint with KKT driver integration for fiscal receipt printing.

---

## Current State

**✅ Already Implemented:**
- FastAPI endpoint `/v1/kkt/receipt` exists (main.py:187-272)
- SQLite buffer insertion works
- HLC timestamp generation works
- Pydantic validation works
- Idempotency-Key header support

**❌ Missing (Blockers):**
- KKT Driver integration (no `kkt_driver.py`)
- Actual receipt printing (Phase 1 requirement)
- Fiscal document generation

---

## Requirements (from CLAUDE.md §7)

**Phase 1 (ALWAYS succeeds):**
1. ✅ Generate HLC timestamp
2. ✅ Insert to SQLite (`status='pending'`)
3. ❌ **Print на ККТ** ← **BLOCKER**
4. ✅ Log event (`receipt_added`)

**Phase 2 (async, best-effort):**
- Already implemented via sync_worker.py (OPTERP-21)

---

## Implementation Plan

### Step 1: Create Mock KKT Driver (OPTERP-17)
**File:** `kkt_adapter/app/kkt_driver.py`

**Functions:**
- `print_receipt(receipt_data: dict) -> dict` - Mock print, return fiscal doc
- `get_kkt_status() -> dict` - Return mock status (online, FN space, etc.)
- `get_shift_info() -> dict` - Return current shift info

**Mock Behavior:**
- Simulate 200-500ms print delay
- Generate mock fiscal document:
  - `fiscal_doc_number` (sequential)
  - `fiscal_sign` (mock hash)
  - `fn_number` (mock FN serial)
  - `kkt_number` (mock ККТ serial)
  - `qr_code_data` (mock QR URL)
- Always succeed (no errors for POC)

### Step 2: Integrate KKT Driver into Receipt Endpoint
**File:** `kkt_adapter/app/main.py`

**Changes:**
1. Import `kkt_driver.print_receipt`
2. Update `create_receipt()` endpoint:
   - After buffer insert → call `print_receipt()`
   - Update receipt with fiscal doc
   - Return `status='printed'` instead of `'buffered'`

**Pseudo-code:**
```python
# Phase 1: Insert into buffer (local)
receipt_id = insert_receipt(receipt_data)

# Print on KKT
fiscal_doc = print_receipt(receipt_data)

# Update receipt with fiscal doc
update_receipt_fiscal_doc(receipt_id, fiscal_doc)

return CreateReceiptResponse(
    status='printed',
    receipt_id=receipt_id,
    fiscal_doc=fiscal_doc,
    message="Receipt printed successfully"
)
```

### Step 3: Create Mock KKT Driver Tests (OPTERP-17)
**File:** `tests/unit/test_kkt_driver.py`

**Test Cases:**
- `test_print_receipt_success` - Verify fiscal doc returned
- `test_print_receipt_delay` - Verify 200-500ms delay
- `test_get_kkt_status` - Verify status dict
- `test_fiscal_doc_sequential_numbers` - Verify incrementing fiscal_doc_number

### Step 4: Update Receipt Endpoint Tests
**File:** `tests/unit/test_fastapi_endpoints.py`

**Changes:**
- Mock `kkt_driver.print_receipt` in tests
- Verify `status='printed'` returned
- Verify `fiscal_doc` populated

---

## Acceptance Criteria

- [ ] Mock KKT Driver created (`kkt_driver.py`)
- [ ] Driver returns valid fiscal document structure
- [ ] Receipt endpoint calls driver after buffer insert
- [ ] Response includes `status='printed'` and `fiscal_doc`
- [ ] All tests pass (≥95% coverage)
- [ ] Test log saved to `tests/logs/unit/20251008_OPTERP-10_*.log`

---

## Files to Modify

1. **Create:** `kkt_adapter/app/kkt_driver.py`
2. **Update:** `kkt_adapter/app/main.py` (import + integration)
3. **Create:** `tests/unit/test_kkt_driver.py`
4. **Update:** `tests/unit/test_fastapi_endpoints.py` (mock driver)

---

## Dependencies

- **Blocks:** OPTERP-18 (Complete Receipt Endpoint Implementation)
- **Blocked By:** None (OPTERP-2 to OPTERP-9 completed)

---

## Timeline

- **Step 1-2:** 30 min (driver + integration)
- **Step 3-4:** 20 min (tests)
- **Total:** ~50 min

---

## Risks

- **None** (Mock driver, no external dependencies)

---

## Notes

- Mock driver for POC only
- Real driver integration in OPTERP-18 (requires hardware/SDK)
- Fiscal doc structure must match ФФД 1.2 format (simplified for mock)
