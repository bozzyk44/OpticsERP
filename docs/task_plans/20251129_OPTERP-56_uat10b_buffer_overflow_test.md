# Task Plan: OPTERP-56 - Create UAT-10b Buffer Overflow Test

**Created:** 2025-11-29
**Status:** ✅ Completed
**Sprint:** Phase 2 MVP - Week 9
**Labels:** mvp, week9, uat, uat-10b, offline

---

## 📋 Task Summary

**JIRA Reference:** OPTERP-56
**Summary:** Create UAT-10b Buffer Overflow Test
**Description:** Create tests/uat/test_uat_10b_buffer_overflow.py - Test buffer capacity management with 200 receipts

**Acceptance Criteria:**
- ✅ UAT-10b: Buffer overflow (200 receipts) passes
- ✅ System handles buffer capacity correctly
- ✅ Alert at 80% capacity (warning)
- ✅ Reject at 100% capacity (critical)
- ✅ Buffer recovers after sync

---

## 🎯 Implementation Approach

### Buffer Capacity Management

**Capacity:** 200 receipts (defined in schema.sql)

**Thresholds:**
- **50%** (100 receipts): Normal operation, no alerts
- **80%** (160 receipts): Warning threshold → P2 alert
- **100%** (200 receipts): Critical threshold → P1 alert, reject new receipts

**Overflow Handling:**
```python
# From buffer.py:235-237
status = get_buffer_status()
if status.pending >= status.capacity:
    raise BufferFullError(f"Buffer full: {status.pending}/{status.capacity}")
```

**HTTP Response:**
- **Accepted:** HTTP 200 (receipt buffered)
- **Rejected:** HTTP 503 Service Unavailable (BufferFullError)

**Error Message:**
```
Buffer full: 200/200. Cannot accept new receipts.
```

### Test Structure

**Full E2E Tests:**
1. `test_uat_10b_buffer_overflow_200_receipts()` - Fill to 100%, verify rejection, sync recovery
2. `test_uat_10b_buffer_recovery_after_overflow()` - Emergency sync and recovery
3. `test_uat_10b_buffer_threshold_alerts()` - 50%, 80%, 100% thresholds

**Smoke Tests:**
1. `test_uat_10b_smoke_test_buffer_capacity()` - Capacity monitoring
2. `test_uat_10b_smoke_test_buffer_full_error()` - Error structure validation

---

## 📁 Files Created

### 1. tests/uat/test_uat_10b_buffer_overflow.py (750 lines)

**Helper Functions:**
```python
get_buffer_status(kkt_adapter_url) -> Dict
create_receipt(kkt_adapter_url, pos_id, amount) -> Response
fill_buffer_to_threshold(kkt_adapter_url, target_count) -> Dict
trigger_sync_and_wait(kkt_adapter_url, expected_synced, timeout) -> bool
```

**Test Coverage:**
- Buffer fills to 80% (160 receipts)
- Buffer fills to 100% (200 receipts)
- 201st receipt rejected (HTTP 503)
- Emergency sync recovery
- Threshold alerts (50%, 80%, 100%)

---

## 🧪 Test Details

### E2E Test 1: Buffer Overflow (200 Receipts)

**Steps:**
1. Set OFD offline (prevent sync)
2. Fill buffer to 80% (160 receipts) → Warning threshold
3. Fill buffer to 100% (200 receipts) → Critical threshold
4. Attempt 201st receipt → Rejected (HTTP 503)
5. Restore OFD and trigger sync
6. Verify buffer recovered (pending = 0)

**Assertions:**
- 200 receipts accepted
- 201st receipt rejected with HTTP 503
- Error message: "Buffer full: 200/200"
- After sync: pending = 0, synced = 200
- percent_full < 10%

### E2E Test 2: Buffer Recovery After Overflow

**Steps:**
1. Fill buffer to 100%
2. Verify new receipts rejected (HTTP 503)
3. Trigger emergency sync
4. Verify buffer has space
5. Create new receipt (should succeed with HTTP 200)

**Assertions:**
- Buffer full → rejection
- Emergency sync → buffer empty
- New receipt accepted after recovery

### E2E Test 3: Buffer Threshold Alerts

**Steps:**
1. Fill to 50% → No alert expected
2. Fill to 80% → Warning alert (P2)
3. Fill to 100% → Critical alert (P1)

**Assertions:**
- percent_full = 50% → No alert
- percent_full >= 80% → Warning
- percent_full >= 99% → Critical

### Smoke Test 1: Buffer Capacity Monitoring

**Checks:**
- Buffer status has 'capacity' field
- Buffer status has 'percent_full' field
- capacity = 200
- percent_full between 0-100

### Smoke Test 2: BufferFullError Structure

**Checks:**
- Error response has 'detail' field
- Error contains "Buffer full"
- Error contains capacity info (200/200)

---

## 📊 Buffer Capacity Calculations

| Receipts | Percent | Status | Action |
|----------|---------|--------|--------|
| 0-99 | 0-49% | Normal | No action |
| 100-159 | 50-79% | Normal | Monitor |
| 160-199 | 80-99% | Warning | P2 alert, prepare for emergency sync |
| 200 | 100% | Critical | P1 alert, reject new receipts |
| 201+ | >100% | Overflow | HTTP 503 rejection |

---

## 🔧 Technical Details

### Buffer Status Response

```json
{
  "total_capacity": 200,
  "current_queued": 200,
  "percent_full": 100.0,
  "network_status": "offline",
  "total_receipts": 200,
  "pending": 200,
  "synced": 0,
  "failed": 0,
  "dlq_size": 0
}
```

### BufferFullError Response

```json
{
  "detail": "Buffer full: 200/200. Cannot accept new receipts."
}
```

### Emergency Sync

**Trigger:** `POST /v1/kkt/buffer/sync`

**Timeout:** 180 seconds (3 minutes for 200 receipts)

**Expected Performance:**
- Sync rate: ~70 receipts/minute
- 200 receipts: ~3 minutes

---

## 📈 Metrics

- **Lines of Code:** 750 lines
- **Test Count:** 5 tests (3 E2E + 2 smoke)
- **Coverage:** Buffer overflow, capacity management, threshold alerts
- **Buffer Capacity:** 200 receipts
- **Thresholds Tested:** 50%, 80%, 100%

---

## ✅ Completion Checklist

- [x] JIRA requirements reviewed
- [x] Buffer capacity logic checked (buffer.py:235-237)
- [x] Threshold values identified (80%, 100%)
- [x] Test file created
- [x] Helper functions implemented
- [x] 3 E2E tests created
- [x] 2 smoke tests created
- [x] Task plan documented
- [x] Ready for commit

---

**Task Status:** ✅ Completed
**Next Task:** OPTERP-57 (Create UAT-10c Power Loss Test)
