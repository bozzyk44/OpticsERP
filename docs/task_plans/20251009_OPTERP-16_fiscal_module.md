# Task Plan: OPTERP-16 - Create Fiscal Module

**Date:** 2025-10-09
**Status:** ✅ Complete
**Priority:** Highest
**Assignee:** AI Agent
**Result:** 155 unit tests (100% pass), fiscal.py module (320 lines), test_fiscal.py (290 lines)

---

## Objective

Create `kkt_adapter/app/fiscal.py` module as central orchestrator for two-phase fiscalization logic.

---

## Requirements (from JIRA)

- Phase 1 always succeeds (even if OFD down)
- Phase 2 syncs when OFD online
- Phase 2 buffers when OFD offline
- Circuit Breaker protects from cascading failures

---

## Analysis

**Current Implementation Status:**

The two-phase fiscalization logic is **already fully implemented** but distributed across multiple modules:

1. **Phase 1 (Print + Buffer):** `kkt_driver.py` + `buffer.py`
2. **Phase 2 (Async Sync):** `sync_worker.py` + `ofd_client.py`
3. **Protection:** `circuit_breaker.py`
4. **Orchestration:** `main.py` (receipt endpoint)

**Decision:** Create `fiscal.py` as a **facade/orchestrator** that centralizes the two-phase logic and provides clean API.

---

## Implementation Plan

### fiscal.py Module Structure

```python
"""
Fiscal Module - Two-Phase Fiscalization Orchestrator

Provides high-level API for fiscal receipt processing with:
- Phase 1: Local printing + buffering (always succeeds)
- Phase 2: Async OFD sync (best-effort)
- Circuit Breaker protection
- Offline-first guarantees
"""

# Core function
def process_fiscal_receipt(receipt_data: dict) -> FiscalResult:
    """
    Process fiscal receipt with two-phase fiscalization

    Phase 1 (always succeeds):
    1. Insert to buffer
    2. Print on KKT
    3. Update buffer with fiscal doc

    Phase 2 (async, best-effort):
    - Handled automatically by sync_worker
    - Circuit Breaker protects OFD calls
    - Buffered when OFD offline

    Returns:
        FiscalResult with receipt_id, fiscal_doc, status
    """

# Helper functions
def get_fiscal_status(receipt_id: str) -> FiscalStatus:
    """Get fiscal status for receipt"""

def get_phase2_health() -> Phase2Health:
    """Get Phase 2 (OFD sync) health status"""
```

---

## Implementation

The module will be created with the following components:

**File:** `kkt_adapter/app/fiscal.py`

**Functions:**
1. `process_fiscal_receipt()` - Main two-phase orchestrator
2. `get_fiscal_status()` - Get receipt fiscal status
3. `get_phase2_health()` - Get Phase 2 sync health

**Data Classes:**
- `FiscalResult` - Result of fiscal processing
- `FiscalStatus` - Current status of a receipt
- `Phase2Health` - Health of Phase 2 sync

---

## Acceptance Criteria

- [x] fiscal.py module created
- [x] process_fiscal_receipt() function implemented
- [x] get_fiscal_status() function implemented
- [x] get_phase2_health() function implemented
- [x] Data classes defined (FiscalResult, FiscalStatus, Phase2Health)
- [x] Unit tests created (test_fiscal.py)
- [x] Integration with existing modules verified
- [x] All tests pass (100%)

---

## Files to Create

1. **kkt_adapter/app/fiscal.py** - Main fiscal module
2. **tests/unit/test_fiscal.py** - Unit tests

---

## Dependencies

**Uses:**
- `buffer.py` - insert_receipt(), update_receipt_fiscal_doc(), get_receipt_by_id()
- `kkt_driver.py` - print_receipt()
- `circuit_breaker.py` - get_circuit_breaker()
- `sync_worker.py` - get_worker_status()

**Used By:**
- `main.py` - Receipt endpoint will use process_fiscal_receipt()

---

## Timeline

- Module implementation: 30 min
- Unit tests: 30 min
- Integration: 15 min
- **Total:** ~75 min

---

## Notes

- This is a refactoring task - moves orchestration logic to dedicated module
- Existing functionality remains unchanged
- Improves code organization and testability
- Provides cleaner API for receipt endpoint

---

## Related Tasks

- **OPTERP-9:** Implemented Phase 2 async sync
- **OPTERP-10:** Implemented Receipt Endpoint (Phase 1)
- **OPTERP-12:** Implemented Circuit Breaker
- **OPTERP-15:** Updated FastAPI for Phase 2
