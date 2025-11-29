"""
UAT-11: Offline Reports Test (X/Z Reports Without OFD Connection)

Author: AI Agent
Created: 2025-11-29
Task: OPTERP-58
Reference: JIRA CSV line 65 (UAT-11 Offline Reports Test)

Purpose:
Test X/Z report generation in offline mode (without OFD connection).

Test Scenarios:
1. X-report generation while OFD offline
2. Z-report generation while OFD offline
3. Report data accuracy from buffered receipts
4. Report generation using local buffer data
5. Smoke tests for offline report structure

Acceptance Criteria:
✅ UAT-11: X/Z reports in offline mode pass
✅ Reports work without OFD connection
✅ Report data calculated from local buffer
✅ FFD 1.2 tags present (local generation)
✅ Totals accurate (cash, card, sales, refunds)

Dependencies:
- KKT adapter running on localhost:8000
- Odoo with optics_pos_ru54fz module (E2E tests)
- Mock OFD server (to control offline state)

Offline Report Generation:
- Reports generated from SQLite buffer (not OFD)
- Data source: receipts table (status='pending' or 'synced')
- Totals calculated locally (SUM, GROUP BY)
- fiscalDocumentNumber from local sequence
- fiscalSign from local KKT signature (mock)

Difference from UAT-04:
- UAT-04: Reports with OFD online (normal operation)
- UAT-11: Reports with OFD offline (degraded mode)
"""

import pytest
import requests
import time
from decimal import Decimal
from typing import Dict, Any, List


# ==================
# Test Configuration
# ==================

KKT_ADAPTER_URL = "http://localhost:8000"
ODOO_BASE_URL = "http://localhost:8069"


# ==================
# Helper Functions
# ==================

def verify_offline_report_structure(report_data: Dict[str, Any], report_type: str) -> Dict[str, Any]:
    """
    Verify offline report structure

    Args:
        report_data: Report JSON data
        report_type: 'X' or 'Z'

    Returns:
        Validation result with errors list
    """
    errors = []

    # Required fields for offline reports
    required_fields = [
        'reportType',
        'shiftNumber',
        'cashTotal',
        'cardTotal',
        'totalSales',
        'totalRefunds',
        'dateTime',
        'offline',  # Indicator that this is offline-generated
    ]

    for field in required_fields:
        if field not in report_data:
            errors.append(f"Missing required field: {field}")

    # Verify report type
    if 'reportType' in report_data:
        expected_type = 1 if report_type == 'X' else 2
        if report_data['reportType'] != expected_type:
            errors.append(
                f"Invalid reportType: expected {expected_type} ({report_type}-report), "
                f"got {report_data['reportType']}"
            )

    # Verify offline flag
    if 'offline' in report_data:
        if not isinstance(report_data['offline'], bool):
            errors.append("'offline' field should be boolean")
        if not report_data['offline']:
            errors.append("'offline' flag should be True for offline reports")

    # Verify totals are non-negative
    for total_field in ['cashTotal', 'cardTotal', 'totalSales', 'totalRefunds']:
        if total_field in report_data:
            try:
                value = float(report_data[total_field])
                if value < 0:
                    errors.append(f"{total_field} cannot be negative: {value}")
            except (ValueError, TypeError):
                errors.append(f"Invalid {total_field} format: {report_data[total_field]}")

    return {
        'valid': len(errors) == 0,
        'errors': errors,
        'fields_found': len([f for f in required_fields if f in report_data]),
        'fields_required': len(required_fields)
    }


def create_sales_in_offline_mode(
    kkt_adapter_url: str,
    count: int,
    payment_mix: Dict[str, int] = None
) -> List[Dict[str, Any]]:
    """
    Create sales while in offline mode

    Args:
        kkt_adapter_url: KKT adapter base URL
        count: Number of sales to create
        payment_mix: Dict with 'cash' and 'card' counts (default: 50/50)

    Returns:
        List of created sales data
    """
    if payment_mix is None:
        payment_mix = {'cash': count // 2, 'card': count - (count // 2)}

    sales = []
    cash_created = 0
    card_created = 0

    for i in range(count):
        # Determine payment method
        if cash_created < payment_mix['cash']:
            payment_method = 'cash'
            cash_created += 1
        else:
            payment_method = 'card'
            card_created += 1

        # Create receipt
        amount = 1000.0 + (i * 100)

        try:
            response = requests.post(
                f"{kkt_adapter_url}/v1/kkt/receipt",
                json={
                    'pos_id': 'POS-OFFLINE-REPORTS',
                    'type': 'sale',
                    'items': [{
                        'name': f'Offline Product {i+1}',
                        'price': amount,
                        'quantity': 1,
                        'sum': amount,
                        'tax': 'vat20'
                    }],
                    'payments': [{
                        'type': payment_method,
                        'sum': amount
                    }]
                },
                headers={'Idempotency-Key': f'offline-report-{i}-{int(time.time())}'},
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                sales.append({
                    'amount': amount,
                    'payment_method': payment_method,
                    'fiscal_doc_id': data.get('fiscal_doc', {}).get('fiscalDocumentNumber')
                })

        except Exception as e:
            print(f"Error creating sale {i+1}: {e}")
            break

    return sales


def calculate_expected_totals(sales: List[Dict[str, Any]]) -> Dict[str, float]:
    """
    Calculate expected report totals from sales data

    Args:
        sales: List of sales data

    Returns:
        Dict with cashTotal, cardTotal, totalSales
    """
    cash_total = sum(s['amount'] for s in sales if s['payment_method'] == 'cash')
    card_total = sum(s['amount'] for s in sales if s['payment_method'] == 'card')

    return {
        'cashTotal': cash_total,
        'cardTotal': card_total,
        'totalSales': cash_total + card_total,
        'totalRefunds': 0.0  # No refunds in this test
    }


# ==================
# Full E2E Tests (require Odoo + KKT adapter)
# ==================

@pytest.mark.uat
@pytest.mark.skip(reason="Requires Odoo with optics_pos_ru54fz module and KKT adapter")
def test_uat_11_x_report_offline_mode(
    odoo_env,
    kkt_adapter_health,
    mock_ofd_server,
    clean_buffer
):
    """
    UAT-11 Test 1: X-report generation in offline mode

    Scenario:
    1. Set OFD offline (Circuit Breaker opens)
    2. Open POS session
    3. Create 10 sales (5 cash, 5 card)
    4. Generate X-report (should work offline)
    5. Verify report data matches buffered sales
    6. Verify 'offline' flag is True
    7. Verify session still open

    Expected:
    - X-report generated successfully despite OFD offline
    - Report data calculated from local buffer
    - Totals accurate (5000₽ cash, 5000₽ card)
    - offline = True
    - Session remains open
    """
    kkt_adapter_url = kkt_adapter_health

    print(f"\n{'='*60}")
    print("UAT-11 Test: X-Report Generation in Offline Mode")
    print(f"{'='*60}\n")

    # 1. Set OFD offline
    print("Step 1: Setting OFD offline...")
    mock_ofd_server.set_mode('offline')

    # Wait for Circuit Breaker to detect offline
    time.sleep(5)

    # 2. Open POS session
    print("Step 2: Creating POS session...")
    pos_config = odoo_env['pos.config'].search([('name', '=', 'Test POS')], limit=1)
    if not pos_config:
        pytest.skip("Test POS config not found")

    pos_session = odoo_env['pos.session'].create({
        'config_id': pos_config.id,
        'user_id': odoo_env.uid,
    })
    pos_session.action_pos_session_open()

    assert pos_session.state == 'opened', "Session should be opened"

    # 3. Create 10 sales (5 cash, 5 card)
    print("Step 3: Creating 10 sales (5 cash, 5 card)...")
    sales = create_sales_in_offline_mode(
        kkt_adapter_url,
        count=10,
        payment_mix={'cash': 5, 'card': 5}
    )

    assert len(sales) == 10, f"Should create 10 sales, got {len(sales)}"
    print(f"  ✅ Created {len(sales)} sales while offline")

    # 4. Generate X-report
    print("\nStep 4: Generating X-report (offline)...")
    x_report_response = requests.post(
        f"{kkt_adapter_url}/v1/kkt/report/x",
        json={
            'pos_id': pos_session.config_id.name,
            'session_id': pos_session.id,
        },
        timeout=10
    )

    assert x_report_response.status_code == 200, \
        f"X-report should generate offline: {x_report_response.text}"

    x_report_data = x_report_response.json()

    print(f"  ✅ X-report generated successfully")

    # 5. Verify report data
    print("\nStep 5: Verifying report data...")

    expected_totals = calculate_expected_totals(sales)

    assert 'reportType' in x_report_data, "Missing reportType"
    assert x_report_data['reportType'] == 1, "X-report should have reportType=1"

    # Verify totals (within 0.01 tolerance for floating point)
    assert abs(float(x_report_data['cashTotal']) - expected_totals['cashTotal']) < 0.01, \
        f"Cash total mismatch: expected {expected_totals['cashTotal']}, got {x_report_data['cashTotal']}"
    assert abs(float(x_report_data['cardTotal']) - expected_totals['cardTotal']) < 0.01, \
        f"Card total mismatch: expected {expected_totals['cardTotal']}, got {x_report_data['cardTotal']}"
    assert abs(float(x_report_data['totalSales']) - expected_totals['totalSales']) < 0.01, \
        f"Total sales mismatch: expected {expected_totals['totalSales']}, got {x_report_data['totalSales']}"

    print(f"  ✅ Report totals accurate:")
    print(f"     Cash: {x_report_data['cashTotal']}")
    print(f"     Card: {x_report_data['cardTotal']}")
    print(f"     Total: {x_report_data['totalSales']}")

    # 6. Verify offline flag
    assert x_report_data.get('offline') is True, \
        "Report should have 'offline' flag set to True"

    print(f"  ✅ Offline flag: {x_report_data.get('offline')}")

    # 7. Verify session still open
    pos_session.refresh()
    assert pos_session.state == 'opened', \
        "Session should remain open after X-report"

    print(f"  ✅ Session still open")

    print(f"\n{'='*60}")
    print("✅ UAT-11 Test 1: PASSED")
    print(f"{'='*60}\n")

    # Cleanup
    pos_session.action_pos_session_close()


@pytest.mark.uat
@pytest.mark.skip(reason="Requires Odoo with optics_pos_ru54fz module and KKT adapter")
def test_uat_11_z_report_offline_mode(
    odoo_env,
    kkt_adapter_health,
    mock_ofd_server,
    clean_buffer
):
    """
    UAT-11 Test 2: Z-report generation in offline mode

    Scenario:
    1. Set OFD offline
    2. Open POS session
    3. Create 8 sales (6 cash, 2 card)
    4. Generate Z-report (should work offline)
    5. Verify report data matches buffered sales
    6. Verify 'offline' flag is True
    7. Verify session closed

    Expected:
    - Z-report generated successfully despite OFD offline
    - Report data calculated from local buffer
    - Totals accurate
    - offline = True
    - Session closed after Z-report
    """
    kkt_adapter_url = kkt_adapter_health

    print(f"\n{'='*60}")
    print("UAT-11 Test: Z-Report Generation in Offline Mode")
    print(f"{'='*60}\n")

    # 1. Set OFD offline
    print("Step 1: Setting OFD offline...")
    mock_ofd_server.set_mode('offline')
    time.sleep(5)

    # 2. Open POS session
    print("Step 2: Creating POS session...")
    pos_config = odoo_env['pos.config'].search([('name', '=', 'Test POS')], limit=1)
    if not pos_config:
        pytest.skip("Test POS config not found")

    pos_session = odoo_env['pos.session'].create({
        'config_id': pos_config.id,
        'user_id': odoo_env.uid,
    })
    pos_session.action_pos_session_open()

    # 3. Create 8 sales (6 cash, 2 card)
    print("Step 3: Creating 8 sales (6 cash, 2 card)...")
    sales = create_sales_in_offline_mode(
        kkt_adapter_url,
        count=8,
        payment_mix={'cash': 6, 'card': 2}
    )

    assert len(sales) == 8, f"Should create 8 sales, got {len(sales)}"
    print(f"  ✅ Created {len(sales)} sales while offline")

    # 4. Generate Z-report
    print("\nStep 4: Generating Z-report (offline)...")
    z_report_response = requests.post(
        f"{kkt_adapter_url}/v1/kkt/report/z",
        json={
            'pos_id': pos_session.config_id.name,
            'session_id': pos_session.id,
        },
        timeout=10
    )

    assert z_report_response.status_code == 200, \
        f"Z-report should generate offline: {z_report_response.text}"

    z_report_data = z_report_response.json()

    print(f"  ✅ Z-report generated successfully")

    # 5. Verify report data
    print("\nStep 5: Verifying report data...")

    expected_totals = calculate_expected_totals(sales)

    assert 'reportType' in z_report_data, "Missing reportType"
    assert z_report_data['reportType'] == 2, "Z-report should have reportType=2"

    # Verify totals
    assert abs(float(z_report_data['cashTotal']) - expected_totals['cashTotal']) < 0.01, \
        f"Cash total mismatch"
    assert abs(float(z_report_data['cardTotal']) - expected_totals['cardTotal']) < 0.01, \
        f"Card total mismatch"
    assert abs(float(z_report_data['totalSales']) - expected_totals['totalSales']) < 0.01, \
        f"Total sales mismatch"

    print(f"  ✅ Report totals accurate")

    # 6. Verify offline flag
    assert z_report_data.get('offline') is True, \
        "Report should have 'offline' flag set to True"

    print(f"  ✅ Offline flag: True")

    # 7. Verify session closed
    pos_session.refresh()
    assert pos_session.state == 'closed', \
        "Session should be closed after Z-report"

    print(f"  ✅ Session closed")

    print(f"\n{'='*60}")
    print("✅ UAT-11 Test 2: PASSED")
    print(f"{'='*60}\n")


@pytest.mark.uat
@pytest.mark.skip(reason="Requires Odoo and KKT adapter")
def test_uat_11_offline_reports_sync_after_online(
    odoo_env,
    kkt_adapter_health,
    mock_ofd_server,
    clean_buffer
):
    """
    UAT-11 Test 3: Offline reports remain valid after OFD restored

    Scenario:
    1. Create sales and X-report while offline
    2. Restore OFD (go online)
    3. Sync buffered receipts
    4. Generate new X-report (now online)
    5. Verify both reports have same totals
    6. Verify offline report still valid

    Expected:
    - Offline report totals match online report
    - Report data consistency maintained
    - No discrepancy after sync
    """
    kkt_adapter_url = kkt_adapter_health

    print(f"\n{'='*60}")
    print("UAT-11 Test: Offline Reports Validity After Sync")
    print(f"{'='*60}\n")

    # 1. Set OFD offline and create sales
    print("Step 1: Creating sales offline...")
    mock_ofd_server.set_mode('offline')
    time.sleep(5)

    pos_config = odoo_env['pos.config'].search([('name', '=', 'Test POS')], limit=1)
    if not pos_config:
        pytest.skip("Test POS config not found")

    pos_session = odoo_env['pos.session'].create({
        'config_id': pos_config.id,
        'user_id': odoo_env.uid,
    })
    pos_session.action_pos_session_open()

    sales = create_sales_in_offline_mode(kkt_adapter_url, count=5, payment_mix={'cash': 3, 'card': 2})

    # Generate offline X-report
    print("\nStep 2: Generating offline X-report...")
    offline_report_response = requests.post(
        f"{kkt_adapter_url}/v1/kkt/report/x",
        json={'pos_id': pos_session.config_id.name, 'session_id': pos_session.id},
        timeout=10
    )

    assert offline_report_response.status_code == 200
    offline_report = offline_report_response.json()

    print(f"  ✅ Offline report generated")
    print(f"     Total: {offline_report['totalSales']}")

    # 2. Restore OFD
    print("\nStep 3: Restoring OFD and syncing...")
    mock_ofd_server.set_mode('online')

    # Trigger sync
    requests.post(f"{kkt_adapter_url}/v1/kkt/buffer/sync", timeout=10)
    time.sleep(5)

    # 3. Generate online X-report
    print("\nStep 4: Generating online X-report...")
    online_report_response = requests.post(
        f"{kkt_adapter_url}/v1/kkt/report/x",
        json={'pos_id': pos_session.config_id.name, 'session_id': pos_session.id},
        timeout=10
    )

    assert online_report_response.status_code == 200
    online_report = online_report_response.json()

    print(f"  ✅ Online report generated")
    print(f"     Total: {online_report['totalSales']}")

    # 4. Verify consistency
    print("\nStep 5: Verifying consistency...")

    assert abs(float(offline_report['totalSales']) - float(online_report['totalSales'])) < 0.01, \
        "Offline and online reports should have same totals"

    assert offline_report.get('offline') is True, \
        "Offline report should have offline flag"
    assert online_report.get('offline') is False or online_report.get('offline') is None, \
        "Online report should not have offline flag or it should be False"

    print(f"  ✅ Report totals consistent")
    print(f"     Offline: {offline_report['totalSales']}")
    print(f"     Online: {online_report['totalSales']}")

    print(f"\n{'='*60}")
    print("✅ UAT-11 Test 3: PASSED")
    print(f"{'='*60}\n")

    # Cleanup
    pos_session.action_pos_session_close()


# ==================
# Smoke Tests (no Odoo required)
# ==================

@pytest.mark.uat
@pytest.mark.smoke
def test_uat_11_smoke_test_offline_report_structure():
    """
    UAT-11 Smoke Test 1: Offline report structure validation

    Verify that offline report has required structure.

    Expected:
    - Has 'offline' flag
    - Has reportType
    - Has cash/card totals
    - Has dateTime
    """
    print(f"\n{'='*60}")
    print("UAT-11 Smoke Test: Offline Report Structure")
    print(f"{'='*60}\n")

    # Mock offline X-report
    mock_offline_report = {
        'reportType': 1,  # X-report
        'shiftNumber': 42,
        'cashTotal': 3000.0,
        'cardTotal': 2000.0,
        'totalSales': 5000.0,
        'totalRefunds': 0.0,
        'dateTime': '2025-11-29T14:30:00',
        'offline': True,  # CRITICAL: offline flag
    }

    # Validate structure
    validation = verify_offline_report_structure(mock_offline_report, 'X')

    assert validation['valid'], \
        f"Offline report validation failed: {', '.join(validation['errors'])}"

    print(f"  ✅ Offline report structure valid:")
    print(f"     Fields found: {validation['fields_found']}/{validation['fields_required']}")
    print(f"     Offline flag: {mock_offline_report.get('offline')}")
    print(f"     Report type: {mock_offline_report.get('reportType')}")

    print(f"\n{'='*60}")
    print("✅ UAT-11 Smoke Test 1: PASSED")
    print(f"{'='*60}\n")


@pytest.mark.uat
@pytest.mark.smoke
def test_uat_11_smoke_test_totals_calculation():
    """
    UAT-11 Smoke Test 2: Totals calculation logic

    Verify that totals are calculated correctly from sales data.

    Expected:
    - cashTotal = sum of cash payments
    - cardTotal = sum of card payments
    - totalSales = cashTotal + cardTotal
    """
    print(f"\n{'='*60}")
    print("UAT-11 Smoke Test: Totals Calculation")
    print(f"{'='*60}\n")

    # Mock sales data
    sales = [
        {'amount': 1000.0, 'payment_method': 'cash'},
        {'amount': 1500.0, 'payment_method': 'cash'},
        {'amount': 2000.0, 'payment_method': 'card'},
        {'amount': 2500.0, 'payment_method': 'card'},
        {'amount': 1200.0, 'payment_method': 'cash'},
    ]

    # Calculate totals
    totals = calculate_expected_totals(sales)

    # Verify calculations
    expected_cash = 1000.0 + 1500.0 + 1200.0  # = 3700
    expected_card = 2000.0 + 2500.0  # = 4500
    expected_total = expected_cash + expected_card  # = 8200

    assert totals['cashTotal'] == expected_cash, \
        f"Cash total incorrect: expected {expected_cash}, got {totals['cashTotal']}"
    assert totals['cardTotal'] == expected_card, \
        f"Card total incorrect: expected {expected_card}, got {totals['cardTotal']}"
    assert totals['totalSales'] == expected_total, \
        f"Total sales incorrect: expected {expected_total}, got {totals['totalSales']}"

    print(f"  ✅ Totals calculated correctly:")
    print(f"     Cash: {totals['cashTotal']} (expected {expected_cash})")
    print(f"     Card: {totals['cardTotal']} (expected {expected_card})")
    print(f"     Total: {totals['totalSales']} (expected {expected_total})")

    print(f"\n{'='*60}")
    print("✅ UAT-11 Smoke Test 2: PASSED")
    print(f"{'='*60}\n")


# ==================
# Pytest Configuration
# ==================

def pytest_configure(config):
    """Add custom markers"""
    config.addinivalue_line(
        "markers",
        "uat: User Acceptance Test (requires full infrastructure)"
    )
    config.addinivalue_line(
        "markers",
        "smoke: Smoke test (minimal dependencies)"
    )
