# Task Plan: OPTERP-18 - Complete Receipt Endpoint Implementation

**Date:** 2025-10-09
**Status:** In Progress
**Priority:** Highest
**Assignee:** AI Agent

---

## Objective

Complete receipt endpoint implementation by refactoring to use the new fiscal module (OPTERP-16).

---

## Current State

**Receipt endpoint exists** but implements two-phase logic inline:
- File: `kkt_adapter/app/main.py`
- Endpoint: `POST /v1/kkt/receipt`
- Status: Functional but tightly coupled

**Implementation:**
```python
@app.post("/v1/kkt/receipt")
async def create_receipt(...):
    # Inline Phase 1 logic
    receipt_id = insert_receipt(receipt_data)
    fiscal_doc = print_receipt(receipt_data)
    update_receipt_fiscal_doc(receipt_id, fiscal_doc)

    return CreateReceiptResponse(...)
```

**Problem:**
- Two-phase logic embedded in endpoint
- No use of fiscal module (created in OPTERP-16)
- Duplication of orchestration logic

---

## Required Changes

### 1. Refactor to Use Fiscal Module

**Before:**
```python
# main.py - Inline implementation
receipt_id = insert_receipt(receipt_data)
fiscal_doc = print_receipt(receipt_data)
update_receipt_fiscal_doc(receipt_id, fiscal_doc)
```

**After:**
```python
# main.py - Use fiscal module
from fiscal import process_fiscal_receipt, FiscalResult

result = process_fiscal_receipt(receipt_data)
return CreateReceiptResponse(
    status=result.status,
    receipt_id=result.receipt_id,
    fiscal_doc=result.fiscal_doc,
    message=...
)
```

### 2. Benefits

- **Cleaner code:** Endpoint delegates to fiscal module
- **Better separation:** Orchestration logic centralized
- **Easier testing:** Fiscal logic tested independently
- **Consistency:** All fiscal operations go through same module

---

## Implementation Plan

### Step 1: Update Imports

Add fiscal module imports to main.py:
```python
from fiscal import process_fiscal_receipt, FiscalResult
```

### Step 2: Refactor create_receipt()

Replace inline Phase 1 logic with fiscal module call:

```python
@app.post("/v1/kkt/receipt")
async def create_receipt(
    request: CreateReceiptRequest,
    idempotency_key: str = Header(...)
):
    logger.info(f"Creating receipt for POS {request.pos_id}")

    try:
        # Convert Pydantic model to dict
        receipt_data = {
            'pos_id': request.pos_id,
            'fiscal_doc': {
                'type': request.type,
                'items': [item.model_dump(mode='json') for item in request.items],
                'payments': [payment.model_dump(mode='json') for payment in request.payments],
                'idempotency_key': idempotency_key
            }
        }

        # Use fiscal module for two-phase processing
        result = process_fiscal_receipt(receipt_data)

        # Map FiscalResult to CreateReceiptResponse
        if result.status == 'printed':
            message = "Receipt printed successfully"
        elif result.status == 'buffered':
            message = f"Receipt buffered, print failed: {result.error}"
        else:
            message = f"Receipt processing failed: {result.error}"

        return CreateReceiptResponse(
            status=result.status,
            receipt_id=result.receipt_id,
            fiscal_doc=result.fiscal_doc,
            message=message
        )

    except BufferFullError as e:
        raise HTTPException(status_code=503, detail=f"Buffer full: {str(e)}")

    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid request: {str(e)}")

    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
```

### Step 3: Remove Obsolete Imports

Remove direct imports that are now encapsulated in fiscal module:
```python
# Remove these (now handled by fiscal module):
# from buffer import insert_receipt, update_receipt_fiscal_doc
# from kkt_driver import print_receipt
```

Keep only what's needed for endpoint:
```python
from buffer import BufferFullError  # Exception still needed
from fiscal import process_fiscal_receipt  # New import
```

---

## Testing Strategy

### 1. Existing Tests Should Pass

All existing endpoint tests should continue to pass:
- `tests/unit/test_fastapi_endpoints.py` (22 tests)
- `tests/integration/test_receipt_workflow.py` (20 tests)

### 2. Behavior Unchanged

- ✅ Receipt creation still works
- ✅ Phase 1 (buffer + print) still executes
- ✅ Phase 2 (async sync) still handled by worker
- ✅ Error handling unchanged
- ✅ Idempotency-Key still required

---

## Acceptance Criteria

- [ ] Receipt endpoint refactored to use fiscal module
- [ ] Imports updated (add fiscal, remove duplicates)
- [ ] All existing tests pass (42 tests)
- [ ] Code is cleaner and more maintainable
- [ ] No behavioral changes (drop-in refactoring)
- [ ] Documentation updated

---

## Files to Modify

1. **kkt_adapter/app/main.py**
   - Update imports
   - Refactor create_receipt() function
   - Remove inline Phase 1 logic

---

## Risks

**Low Risk Refactoring:**
- Fiscal module already tested (19 tests)
- Logic unchanged, just reorganized
- All existing tests provide regression coverage

**Rollback Plan:**
- Git revert if tests fail
- No API changes, fully backward compatible

---

## Timeline

- Refactoring: 15 min
- Testing: 10 min
- Documentation: 5 min
- **Total:** ~30 min

---

## Related Tasks

- **OPTERP-10:** Implemented Receipt Endpoint (Phase 1) - original implementation
- **OPTERP-16:** Created Fiscal Module - provides process_fiscal_receipt()
- **OPTERP-19:** Create Two-Phase Integration Tests - will test refactored endpoint
