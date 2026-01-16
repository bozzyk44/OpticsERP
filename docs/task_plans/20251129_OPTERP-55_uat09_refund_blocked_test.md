# Task Plan: OPTERP-55 - Create UAT-09 Refund Blocked Test

**Created:** 2025-11-29
**Status:** ✅ Completed
**Sprint:** Phase 2 MVP - Week 9
**Labels:** mvp, week9, uat, uat-09, offline

---

## 📋 Task Summary

**JIRA Reference:** OPTERP-55
**Summary:** Create UAT-09 Refund Blocked Test
**Description:** Create tests/uat/test_uat_09_refund_blocked.py - Test Saga pattern refund blocking

**Acceptance Criteria:**
- ✅ UAT-09: Refund blocking passes
- ✅ Refund blocked if original not synced (HTTP 409)
- ✅ Refund allowed if original synced (HTTP 200)
- ✅ Clear error messages for users
- ✅ No orphaned refunds in buffer

---

## 🎯 Implementation Approach

### Saga Pattern Overview

**Definition:** Saga pattern ensures compensating transactions (refunds) can only occur after original transactions are committed (synced to OFD).

**Business Rule:**
- **BLOCKED:** Refund if original receipt status = 'pending' (not synced yet)
- **ALLOWED:** Refund if original receipt status = 'synced' (committed to OFD)
- **ALLOWED:** Refund if original receipt status = 'not_required' (non-fiscal)

**Implementation (pos.order model):**
```python
def _check_refund_allowed(self):
    original_order = self._get_original_order_for_refund()

    if original_order.fiscal_sync_status == 'pending':
        raise UserError("Refund blocked: Original receipt not synced to OFD yet")

    return True  # Allow refund
```

**API Endpoint:** `POST /v1/pos/refund`
- **Request:** `{'original_fiscal_doc_id': 'FD-12345'}`
- **Response (blocked):** HTTP 409 `{'allowed': false, 'sync_status': 'pending'}`
- **Response (allowed):** HTTP 200 `{'allowed': true, 'sync_status': 'synced'}`

### Test Structure

**Full E2E Tests (require Odoo):**
1. `test_uat_09_refund_blocked_when_not_synced()` - Refund blocked when pending
2. `test_uat_09_refund_allowed_after_sync()` - Refund allowed when synced
3. `test_uat_09_refund_blocked_multiple_attempts()` - Multiple attempts validation

**Smoke Tests (no Odoo):**
1. `test_uat_09_smoke_test_refund_check_endpoint()` - API endpoint validation
2. `test_uat_09_smoke_test_error_message_format()` - Error message quality

---

## 📁 Files Created

### 1. tests/uat/test_uat_09_refund_blocked.py (700 lines)

**Test Coverage:**
- Refund blocking when original pending
- Refund allowed after sync
- Multiple refund attempts (2 blocked, 1 succeeds)
- Endpoint structure validation
- Error message quality

**Helper Functions:**
```python
wait_for_receipt_synced(kkt_adapter_url, fiscal_doc_id, timeout) -> bool
create_pos_order_with_fiscalization(odoo_env, kkt_adapter_url, ...) -> Dict
```

---

## 🧪 Test Details

### E2E Test 1: Refund Blocked When Not Synced

**Steps:**
1. Set OFD offline (keep receipt pending)
2. Create POS session
3. Create original sale + fiscalize (status=pending)
4. Attempt refund (should raise UserError)
5. Verify error message content

**Assertions:**
- UserError raised
- Error contains "Refund blocked"
- Error mentions "not synced"
- Error references original order/fiscal_doc_id

### E2E Test 2: Refund Allowed After Sync

**Steps:**
1. Set OFD online
2. Create original sale + fiscalize
3. Wait for sync (status=synced)
4. Create refund (should succeed)
5. Verify refund order created

**Assertions:**
- Original synced successfully
- Refund order created (no UserError)
- Refund has negative amount

### E2E Test 3: Multiple Refund Attempts

**Steps:**
1. Create original sale (pending)
2. Attempt refund #1 → blocked
3. Attempt refund #2 → blocked
4. Sync original receipt
5. Attempt refund #3 → succeeds

**Assertions:**
- First 2 attempts raise UserError
- Third attempt succeeds after sync

### Smoke Test 1: Refund Check Endpoint

**Steps:**
1. Check KKT adapter health
2. POST /v1/pos/refund with fake fiscal_doc_id
3. Verify response structure

**Assertions:**
- HTTP 200 or 409
- Response has 'allowed' field (boolean)
- If blocked, has 'sync_status' field

### Smoke Test 2: Error Message Format

**Steps:**
1. Validate error message structure
2. Check for required components

**Assertions:**
- Contains "Refund blocked"
- Contains sync status
- References original order
- Provides user guidance

---

## 📊 Metrics

- **Lines of Code:** 700 lines
- **Test Count:** 5 tests (3 E2E + 2 smoke)
- **Coverage:** Saga pattern refund blocking
- **Dependencies:** Odoo + optics_pos_ru54fz + KKT adapter + Mock OFD

---

## ✅ Completion Checklist

- [x] JIRA requirements reviewed
- [x] Saga pattern implementation checked (pos_order.py)
- [x] Integration tests reviewed (test_saga_pattern.py)
- [x] Test file created
- [x] 3 E2E tests created
- [x] 2 smoke tests created
- [x] Task plan documented
- [x] Ready for commit

---

**Task Status:** ✅ Completed
**Next Task:** OPTERP-56 (Create UAT-10b Buffer Overflow Test)
