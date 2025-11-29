# Task Plan: OPTERP-58 - Create UAT-11 Offline Reports Test

**Created:** 2025-11-29
**Status:** ✅ Completed
**Sprint:** Phase 2 MVP - Week 9
**Labels:** mvp, week9, uat, uat-11, offline

---

## 📋 Task Summary

**JIRA Reference:** OPTERP-58
**Summary:** Create UAT-11 Offline Reports Test
**Description:** Create tests/uat/test_uat_11_offline_reports.py - Test X/Z reports in offline mode

**Acceptance Criteria:**
- ✅ UAT-11: X/Z reports in offline mode pass
- ✅ Reports work without OFD connection
- ✅ Report data calculated from local buffer
- ✅ FFD 1.2 tags present (local generation)
- ✅ Totals accurate (cash, card, sales, refunds)

---

## 🎯 Implementation Approach

### Offline Report Generation

**Difference from UAT-04:**
- **UAT-04:** Reports with OFD online (normal operation, full FFD 1.2)
- **UAT-11:** Reports with OFD offline (degraded mode, local generation)

**Data Source:**
- **Online:** Reports sent to OFD, signed by OFD server
- **Offline:** Reports generated from local SQLite buffer

**Report Structure (Offline):**
```json
{
  "reportType": 1,          // 1=X, 2=Z
  "shiftNumber": 42,
  "cashTotal": 5000.0,
  "cardTotal": 3000.0,
  "totalSales": 8000.0,
  "totalRefunds": 500.0,
  "dateTime": "2025-11-29T14:30:00",
  "offline": true           // CRITICAL: offline indicator
}
```

**Calculation Logic:**
```sql
-- Cash total
SELECT SUM(amount) FROM receipts
WHERE payment_type = 'cash' AND session_id = ?

-- Card total
SELECT SUM(amount) FROM receipts
WHERE payment_type = 'card' AND session_id = ?

-- Total sales
SELECT SUM(amount) FROM receipts
WHERE type = 'sale' AND session_id = ?
```

### Test Structure

**Full E2E Tests:**
1. `test_uat_11_x_report_offline_mode()` - X-report with OFD offline
2. `test_uat_11_z_report_offline_mode()` - Z-report with OFD offline
3. `test_uat_11_offline_reports_sync_after_online()` - Consistency after OFD restored

**Smoke Tests:**
1. `test_uat_11_smoke_test_offline_report_structure()` - Structure validation
2. `test_uat_11_smoke_test_totals_calculation()` - Calculation logic

---

## 📁 Files Created

### 1. tests/uat/test_uat_11_offline_reports.py (650 lines)

**Helper Functions:**
```python
verify_offline_report_structure(report_data, report_type) -> Dict
  - Validates offline report structure
  - Checks for 'offline' flag
  - Verifies required fields

create_sales_in_offline_mode(kkt_adapter_url, count, payment_mix) -> List
  - Creates sales while OFD offline
  - Accepts payment mix (cash/card ratio)
  - Returns sales data for verification

calculate_expected_totals(sales) -> Dict
  - Calculates expected report totals
  - Returns cashTotal, cardTotal, totalSales
```

**Test Coverage:**
- X-report generation offline (10 sales: 5 cash, 5 card)
- Z-report generation offline (8 sales: 6 cash, 2 card)
- Report consistency after sync
- Offline flag validation
- Totals calculation accuracy

---

## 🧪 Test Details

### E2E Test 1: X-Report Offline Mode

**Scenario:**
1. Set OFD offline (Circuit Breaker opens)
2. Open POS session
3. Create 10 sales (5 cash × 1000₽, 5 card × 1000₽)
4. Generate X-report (should work offline)
5. Verify report totals match buffered sales
6. Verify 'offline' flag is True
7. Verify session still open

**Assertions:**
- X-report generated successfully (HTTP 200)
- reportType = 1
- cashTotal = 5000₽ (5 × 1000₽)
- cardTotal = 5000₽ (5 × 1000₽)
- totalSales = 10000₽
- offline = True
- Session state = 'opened'

### E2E Test 2: Z-Report Offline Mode

**Scenario:**
1. Set OFD offline
2. Open POS session
3. Create 8 sales (6 cash, 2 card)
4. Generate Z-report (should work offline)
5. Verify report totals accurate
6. Verify 'offline' flag is True
7. Verify session closed

**Assertions:**
- Z-report generated successfully
- reportType = 2
- Totals accurate
- offline = True
- Session state = 'closed'

### E2E Test 3: Offline Reports Validity After Sync

**Scenario:**
1. Create 5 sales and X-report while offline
2. Restore OFD (go online)
3. Sync buffered receipts
4. Generate new X-report (now online)
5. Verify both reports have same totals

**Assertions:**
- Offline report total = Online report total
- Offline report has offline=True
- Online report has offline=False or no offline field
- No discrepancy after sync

### Smoke Test 1: Offline Report Structure

**Checks:**
- Has 'offline' field (boolean)
- Has reportType (1 or 2)
- Has cash/card totals
- Has dateTime
- All required fields present

### Smoke Test 2: Totals Calculation

**Scenario:**
```python
sales = [
  {'amount': 1000.0, 'payment_method': 'cash'},
  {'amount': 1500.0, 'payment_method': 'cash'},
  {'amount': 2000.0, 'payment_method': 'card'},
  {'amount': 2500.0, 'payment_method': 'card'},
  {'amount': 1200.0, 'payment_method': 'cash'},
]
```

**Expected:**
- cashTotal = 3700₽ (1000 + 1500 + 1200)
- cardTotal = 4500₽ (2000 + 2500)
- totalSales = 8200₽ (3700 + 4500)

---

## 📊 Offline vs Online Reports

| Feature | Online Reports (UAT-04) | Offline Reports (UAT-11) |
|---------|-------------------------|--------------------------|
| **Data Source** | OFD server | Local SQLite buffer |
| **fiscalSign** | From OFD (crypto) | Local mock signature |
| **fiscalDocumentNumber** | From OFD sequence | Local sequence |
| **Availability** | Requires OFD | Works without OFD |
| **offline flag** | False or absent | True |
| **Legal validity** | Full (54-ФЗ) | Temporary (must sync) |
| **Totals** | From OFD records | Calculated locally |

---

## 🔧 Technical Details

### Offline Report Generation Flow

```
1. User requests X/Z report
   ↓
2. Check Circuit Breaker state
   ↓
3. If OFD offline:
   - Query local buffer (SQLite)
   - Calculate totals (SUM, GROUP BY)
   - Generate report with offline=True
   ↓
4. Return report to user
```

### Required Fields (Offline)

```python
{
  'reportType': int,        # 1 (X) or 2 (Z)
  'shiftNumber': int,       # Current shift
  'cashTotal': float,       # Sum of cash payments
  'cardTotal': float,       # Sum of card payments
  'totalSales': float,      # cashTotal + cardTotal
  'totalRefunds': float,    # Sum of refunds
  'dateTime': str,          # ISO 8601 timestamp
  'offline': bool,          # True for offline reports
}
```

### Optional Fields (Future)

```python
{
  'fiscalDocumentNumber': int,  # Local sequence
  'fiscalSign': str,            # Local mock signature
  'operatorName': str,          # Cashier name
  'kktRegNumber': str,          # KKT registration number
}
```

---

## 📈 Metrics

- **Lines of Code:** 650 lines
- **Test Count:** 5 tests (3 E2E + 2 smoke)
- **Coverage:** Offline X-report, offline Z-report, consistency validation
- **Payment Methods Tested:** Cash, Card

---

## ✅ Completion Checklist

- [x] JIRA requirements reviewed
- [x] UAT-04 reports test reviewed (for comparison)
- [x] Offline report structure defined
- [x] Test file created
- [x] Helper functions implemented
- [x] 3 E2E tests created
- [x] 2 smoke tests created
- [x] Task plan documented
- [x] Ready for commit

---

## 🎓 Key Learnings

1. **Offline-First Reporting:** Reports can be generated from local buffer without OFD
2. **offline Flag Critical:** Distinguishes local reports from OFD-signed reports
3. **Temporary Validity:** Offline reports valid until buffered receipts synced to OFD
4. **Calculation Logic:** Simple SUM queries on local buffer provide accurate totals
5. **Business Continuity:** Cashiers can close shifts even when OFD unavailable

---

## 🔍 Relationship to Other Tests

| Test | Focus | Connection to UAT-11 |
|------|-------|---------------------|
| **UAT-04** | X/Z reports (online) | Comparison baseline |
| **UAT-08** | Offline sales | Generates data for offline reports |
| **UAT-10b** | Buffer overflow | Reports must work when buffer near capacity |
| **UAT-10c** | Power loss | Reports must survive crashes |

---

**Task Status:** ✅ Completed
**Next Task:** All UAT tests complete!
