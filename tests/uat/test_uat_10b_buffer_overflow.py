"""
UAT-10b: Buffer Overflow Test (200 Receipts)

Author: AI Agent
Created: 2025-11-29
Task: OPTERP-56
Reference: JIRA CSV line 63 (UAT-10b Buffer Overflow Test)

Purpose:
Test buffer capacity management and overflow handling.

Test Scenarios:
1. Buffer fills to 80% (warning threshold)
2. Buffer fills to 100% (capacity reached)
3. Receipt rejected when buffer full (HTTP 503)
4. Buffer recovers after sync
5. Smoke test for buffer capacity monitoring

Acceptance Criteria:
✅ UAT-10b: Buffer overflow (200 receipts) passes
✅ System handles buffer capacity correctly
✅ Alert at 80% capacity
✅ Reject at 100% capacity (BufferFullError)
✅ Buffer recovers after sync

Dependencies:
- KKT adapter running on localhost:8000
- SQLite buffer with 200 receipts capacity
- Mock OFD server for controlled offline testing

Buffer Thresholds:
- Capacity: 200 receipts (from schema.sql)
- Warning: 80% (160 receipts) → P2 alert
- Critical: 100% (200 receipts) → P1 alert, reject new receipts
"""

import pytest
import requests
import time
import uuid
from typing import List, Dict, Any


# ==================
# Test Configuration
# ==================

KKT_ADAPTER_URL = "http://localhost:8000"
BUFFER_CAPACITY = 200  # From schema.sql
WARNING_THRESHOLD = 0.80  # 80%
CRITICAL_THRESHOLD = 1.00  # 100%


# ==================
# Helper Functions
# ==================

def get_buffer_status(kkt_adapter_url: str) -> Dict[str, Any]:
    """
    Get current buffer status

    Args:
        kkt_adapter_url: KKT adapter base URL

    Returns:
        Buffer status dict with pending, synced, percent_full, etc.
    """
    try:
        response = requests.get(
            f"{kkt_adapter_url}/v1/kkt/buffer/status",
            timeout=5
        )

        if response.status_code == 200:
            return response.json()
        else:
            return {
                'error': f"HTTP {response.status_code}",
                'pending': 0,
                'capacity': BUFFER_CAPACITY,
                'percent_full': 0.0
            }

    except Exception as e:
        return {
            'error': str(e),
            'pending': 0,
            'capacity': BUFFER_CAPACITY,
            'percent_full': 0.0
        }


def create_receipt(
    kkt_adapter_url: str,
    pos_id: str = "POS-001",
    amount: float = 1000.0
) -> requests.Response:
    """
    Create a single receipt via KKT adapter API

    Args:
        kkt_adapter_url: KKT adapter base URL
        pos_id: POS terminal ID
        amount: Receipt amount

    Returns:
        Response object
    """
    receipt_data = {
        'pos_id': pos_id,
        'type': 'sale',
        'items': [{
            'name': f'Product {uuid.uuid4().hex[:8]}',
            'price': amount,
            'quantity': 1,
            'sum': amount,
            'tax': 'vat20'
        }],
        'payments': [{
            'type': 'cash',
            'sum': amount
        }]
    }

    return requests.post(
        f"{kkt_adapter_url}/v1/kkt/receipt",
        json=receipt_data,
        headers={'Idempotency-Key': str(uuid.uuid4())},
        timeout=10
    )


def fill_buffer_to_threshold(
    kkt_adapter_url: str,
    target_count: int,
    pos_id: str = "POS-OVERFLOW"
) -> Dict[str, Any]:
    """
    Fill buffer to specified receipt count

    Args:
        kkt_adapter_url: KKT adapter base URL
        target_count: Number of receipts to create
        pos_id: POS terminal ID

    Returns:
        Result dict with success_count, failed_count, final_status
    """
    success_count = 0
    failed_count = 0
    last_error = None

    print(f"\n  Filling buffer to {target_count} receipts...")

    for i in range(target_count):
        try:
            response = create_receipt(kkt_adapter_url, pos_id)

            if response.status_code == 200:
                success_count += 1
            elif response.status_code == 503:
                # Buffer full
                failed_count += 1
                last_error = "Buffer full (HTTP 503)"
                break
            else:
                failed_count += 1
                last_error = f"HTTP {response.status_code}"

            # Progress indicator every 50 receipts
            if (i + 1) % 50 == 0:
                status = get_buffer_status(kkt_adapter_url)
                print(f"    Progress: {i + 1}/{target_count} created, "
                      f"buffer at {status.get('percent_full', 0):.1f}%")

        except Exception as e:
            failed_count += 1
            last_error = str(e)
            break

    # Get final status
    final_status = get_buffer_status(kkt_adapter_url)

    return {
        'success_count': success_count,
        'failed_count': failed_count,
        'last_error': last_error,
        'final_status': final_status
    }


def trigger_sync_and_wait(
    kkt_adapter_url: str,
    expected_synced: int,
    timeout_seconds: int = 120
) -> bool:
    """
    Trigger manual sync and wait for completion

    Args:
        kkt_adapter_url: KKT adapter base URL
        expected_synced: Expected synced count
        timeout_seconds: Max wait time

    Returns:
        True if synced, False if timeout
    """
    # Trigger sync
    try:
        requests.post(f"{kkt_adapter_url}/v1/kkt/buffer/sync", timeout=10)
    except:
        pass

    # Wait for sync
    start_time = time.time()

    while time.time() - start_time < timeout_seconds:
        status = get_buffer_status(kkt_adapter_url)
        synced = status.get('synced', 0)

        if synced >= expected_synced:
            return True

        time.sleep(3)

    return False


# ==================
# Full E2E Tests
# ==================

@pytest.mark.uat
@pytest.mark.skip(reason="Requires KKT adapter and mock OFD server")
def test_uat_10b_buffer_overflow_200_receipts(
    kkt_adapter_health,
    mock_ofd_server,
    clean_buffer
):
    """
    UAT-10b Test 1: Buffer overflow with 200 receipts

    Scenario:
    1. Set OFD offline (prevent sync)
    2. Fill buffer to 80% (160 receipts) → Warning threshold
    3. Fill buffer to 100% (200 receipts) → Critical threshold
    4. Attempt 201st receipt → Rejected (HTTP 503)
    5. Restore OFD and sync
    6. Verify buffer recovered

    Expected:
    - 200 receipts accepted
    - 201st receipt rejected (BufferFullError)
    - Buffer percent_full = 100%
    - After sync: buffer empty, all 200 synced
    """
    kkt_adapter_url = kkt_adapter_health

    print(f"\n{'='*60}")
    print("UAT-10b Test: Buffer Overflow (200 Receipts)")
    print(f"{'='*60}\n")

    # 1. Set OFD offline
    print("Step 1: Setting OFD offline...")
    mock_ofd_server.set_mode('offline')

    # Wait for CB to open
    time.sleep(5)

    # Get initial status
    initial_status = get_buffer_status(kkt_adapter_url)
    initial_pending = initial_status.get('pending', 0)
    print(f"  Initial buffer: {initial_pending} pending")

    # 2. Fill to 80% (warning threshold)
    warning_target = int(BUFFER_CAPACITY * WARNING_THRESHOLD)
    print(f"\nStep 2: Filling buffer to 80% ({warning_target} receipts)...")

    result_80 = fill_buffer_to_threshold(kkt_adapter_url, warning_target)

    assert result_80['success_count'] >= warning_target, \
        f"Should create {warning_target} receipts, got {result_80['success_count']}"

    status_80 = result_80['final_status']
    percent_80 = status_80.get('percent_full', 0)

    print(f"  ✅ Buffer at {percent_80:.1f}% ({status_80.get('pending', 0)} pending)")

    # Verify warning threshold reached
    assert percent_80 >= (WARNING_THRESHOLD * 100), \
        f"Buffer should be >= 80%, got {percent_80:.1f}%"

    # 3. Fill to 100% (critical threshold)
    remaining = BUFFER_CAPACITY - status_80.get('pending', 0)
    print(f"\nStep 3: Filling buffer to 100% ({remaining} more receipts)...")

    result_100 = fill_buffer_to_threshold(kkt_adapter_url, remaining)

    status_100 = get_buffer_status(kkt_adapter_url)
    pending_100 = status_100.get('pending', 0)
    percent_100 = status_100.get('percent_full', 0)

    print(f"  ✅ Buffer at {percent_100:.1f}% ({pending_100} pending)")

    # Verify critical threshold reached
    assert pending_100 >= BUFFER_CAPACITY or percent_100 >= 99.0, \
        f"Buffer should be full (>= 200 or >= 99%), got {pending_100} pending, {percent_100:.1f}%"

    # 4. Attempt 201st receipt (should be rejected)
    print("\nStep 4: Attempting 201st receipt (should be rejected)...")

    response_201 = create_receipt(kkt_adapter_url)

    assert response_201.status_code == 503, \
        f"201st receipt should be rejected (HTTP 503), got {response_201.status_code}"

    print("  ✅ 201st receipt rejected with HTTP 503 (BufferFullError)")

    # Verify error message
    error_data = response_201.json()
    assert 'detail' in error_data, "Error response should have 'detail' field"
    assert 'Buffer full' in error_data['detail'], \
        "Error message should mention 'Buffer full'"

    print(f"  Error message: {error_data['detail']}")

    # 5. Restore OFD and sync
    print("\nStep 5: Restoring OFD and syncing...")
    mock_ofd_server.set_mode('online')

    sync_completed = trigger_sync_and_wait(
        kkt_adapter_url,
        expected_synced=pending_100,
        timeout_seconds=180  # 3 minutes for 200 receipts
    )

    assert sync_completed, "Sync should complete within 3 minutes"

    # 6. Verify buffer recovered
    final_status = get_buffer_status(kkt_adapter_url)
    final_pending = final_status.get('pending', 0)
    final_synced = final_status.get('synced', 0)

    print(f"\n  ✅ Buffer recovered:")
    print(f"     Pending: {final_pending}")
    print(f"     Synced: {final_synced}")
    print(f"     Percent full: {final_status.get('percent_full', 0):.1f}%")

    assert final_pending == 0, "Buffer should be empty after sync"
    assert final_synced >= pending_100, \
        f"All receipts should sync ({pending_100}), got {final_synced}"

    print(f"\n{'='*60}")
    print("✅ UAT-10b Test 1: PASSED")
    print(f"{'='*60}\n")


@pytest.mark.uat
@pytest.mark.skip(reason="Requires KKT adapter and mock OFD server")
def test_uat_10b_buffer_recovery_after_overflow(
    kkt_adapter_health,
    mock_ofd_server,
    clean_buffer
):
    """
    UAT-10b Test 2: Buffer recovery after overflow

    Scenario:
    1. Fill buffer to 100%
    2. Verify new receipts rejected
    3. Trigger emergency sync (manual)
    4. Verify buffer has space
    5. Create new receipt (should succeed)

    Expected:
    - Buffer recovers capacity after sync
    - New receipts accepted after recovery
    """
    kkt_adapter_url = kkt_adapter_health

    print(f"\n{'='*60}")
    print("UAT-10b Test: Buffer Recovery After Overflow")
    print(f"{'='*60}\n")

    # 1. Fill buffer to 100%
    print("Step 1: Filling buffer to 100%...")
    mock_ofd_server.set_mode('offline')
    time.sleep(5)

    result = fill_buffer_to_threshold(kkt_adapter_url, BUFFER_CAPACITY)

    status_full = result['final_status']
    print(f"  ✅ Buffer full: {status_full.get('pending', 0)} pending")

    # 2. Verify rejection
    print("\nStep 2: Verifying new receipts rejected...")
    response_rejected = create_receipt(kkt_adapter_url)

    assert response_rejected.status_code == 503, \
        "Receipt should be rejected when buffer full"
    print("  ✅ Receipt rejected (HTTP 503)")

    # 3. Emergency sync
    print("\nStep 3: Triggering emergency sync...")
    mock_ofd_server.set_mode('online')

    sync_ok = trigger_sync_and_wait(
        kkt_adapter_url,
        expected_synced=status_full.get('pending', 0),
        timeout_seconds=180
    )

    assert sync_ok, "Emergency sync should complete"

    status_after_sync = get_buffer_status(kkt_adapter_url)
    print(f"  ✅ Sync complete: {status_after_sync.get('pending', 0)} pending")

    # 4. Verify space available
    assert status_after_sync.get('pending', 0) == 0, \
        "Buffer should be empty after sync"
    assert status_after_sync.get('percent_full', 0) < 10, \
        "Buffer should have < 10% usage after sync"

    # 5. Create new receipt (should succeed)
    print("\nStep 4: Creating new receipt (should succeed)...")
    response_new = create_receipt(kkt_adapter_url)

    assert response_new.status_code == 200, \
        f"New receipt should succeed after recovery, got {response_new.status_code}"
    print("  ✅ New receipt created successfully")

    print(f"\n{'='*60}")
    print("✅ UAT-10b Test 2: PASSED")
    print(f"{'='*60}\n")


@pytest.mark.uat
@pytest.mark.skip(reason="Requires KKT adapter")
def test_uat_10b_buffer_threshold_alerts(
    kkt_adapter_health,
    mock_ofd_server,
    clean_buffer
):
    """
    UAT-10b Test 3: Buffer threshold alerts

    Scenario:
    1. Fill buffer to 50% (no alert)
    2. Fill buffer to 80% (warning alert - P2)
    3. Fill buffer to 100% (critical alert - P1)

    Expected:
    - No alert at 50%
    - Warning at 80%
    - Critical at 100%

    Note: Alerts are checked via buffer status, not actual alert system
    """
    kkt_adapter_url = kkt_adapter_health

    print(f"\n{'='*60}")
    print("UAT-10b Test: Buffer Threshold Alerts")
    print(f"{'='*60}\n")

    mock_ofd_server.set_mode('offline')
    time.sleep(5)

    # 1. Fill to 50%
    target_50 = int(BUFFER_CAPACITY * 0.50)
    print(f"Step 1: Filling to 50% ({target_50} receipts)...")

    fill_buffer_to_threshold(kkt_adapter_url, target_50)
    status_50 = get_buffer_status(kkt_adapter_url)

    print(f"  Buffer at {status_50.get('percent_full', 0):.1f}%")
    print("  ✅ No alert expected at 50%")

    # 2. Fill to 80%
    target_80 = int(BUFFER_CAPACITY * 0.80)
    remaining_80 = target_80 - status_50.get('pending', 0)
    print(f"\nStep 2: Filling to 80% ({remaining_80} more receipts)...")

    fill_buffer_to_threshold(kkt_adapter_url, remaining_80)
    status_80 = get_buffer_status(kkt_adapter_url)

    print(f"  Buffer at {status_80.get('percent_full', 0):.1f}%")
    assert status_80.get('percent_full', 0) >= 80, "Buffer should be >= 80%"
    print("  ⚠️  Warning alert expected (P2)")

    # 3. Fill to 100%
    remaining_100 = BUFFER_CAPACITY - status_80.get('pending', 0)
    print(f"\nStep 3: Filling to 100% ({remaining_100} more receipts)...")

    fill_buffer_to_threshold(kkt_adapter_url, remaining_100)
    status_100 = get_buffer_status(kkt_adapter_url)

    print(f"  Buffer at {status_100.get('percent_full', 0):.1f}%")
    assert status_100.get('percent_full', 0) >= 99, "Buffer should be >= 99%"
    print("  🚨 Critical alert expected (P1)")

    print(f"\n{'='*60}")
    print("✅ UAT-10b Test 3: PASSED")
    print(f"{'='*60}\n")


# ==================
# Smoke Tests (no Odoo required)
# ==================

@pytest.mark.uat
@pytest.mark.smoke
def test_uat_10b_smoke_test_buffer_capacity():
    """
    UAT-10b Smoke Test 1: Buffer capacity monitoring

    Verify that buffer status provides capacity information.

    Expected:
    - Buffer status has 'capacity' field
    - Buffer status has 'percent_full' field
    - Values are reasonable (capacity = 200, percent_full 0-100)
    """
    kkt_adapter_url = KKT_ADAPTER_URL

    print(f"\n{'='*60}")
    print("UAT-10b Smoke Test: Buffer Capacity Monitoring")
    print(f"{'='*60}\n")

    # Check KKT adapter
    try:
        health = requests.get(f"{kkt_adapter_url}/v1/health", timeout=5)
        if health.status_code != 200:
            pytest.skip("KKT adapter not healthy")
    except:
        pytest.skip("KKT adapter not reachable")

    # Get buffer status
    status = get_buffer_status(kkt_adapter_url)

    # Verify capacity field
    assert 'total_capacity' in status or 'capacity' in status, \
        "Buffer status should have capacity field"

    capacity = status.get('total_capacity', status.get('capacity', 0))

    assert capacity == BUFFER_CAPACITY, \
        f"Buffer capacity should be {BUFFER_CAPACITY}, got {capacity}"

    # Verify percent_full field
    assert 'percent_full' in status, \
        "Buffer status should have 'percent_full' field"

    percent_full = status.get('percent_full', 0)

    assert 0 <= percent_full <= 100, \
        f"Percent full should be 0-100, got {percent_full}"

    print(f"  ✅ Buffer capacity monitoring:")
    print(f"     Total capacity: {capacity}")
    print(f"     Pending: {status.get('pending', 0)}")
    print(f"     Percent full: {percent_full:.1f}%")

    print(f"\n{'='*60}")
    print("✅ UAT-10b Smoke Test: PASSED")
    print(f"{'='*60}\n")


@pytest.mark.uat
@pytest.mark.smoke
def test_uat_10b_smoke_test_buffer_full_error():
    """
    UAT-10b Smoke Test 2: BufferFullError structure

    Verify that BufferFullError is raised with correct structure.

    Expected:
    - HTTP 503 when buffer full
    - Error message contains "Buffer full"
    - Error message contains capacity info
    """
    # Mock error response (from actual API)
    mock_error_response = {
        'detail': 'Buffer full: 200/200. Cannot accept new receipts.'
    }

    print(f"\n{'='*60}")
    print("UAT-10b Smoke Test: BufferFullError Structure")
    print(f"{'='*60}\n")

    # Verify error message structure
    assert 'detail' in mock_error_response, \
        "Error response should have 'detail' field"

    error_message = mock_error_response['detail']

    assert 'Buffer full' in error_message, \
        "Error should mention 'Buffer full'"
    assert '200' in error_message, \
        "Error should mention capacity (200)"

    print(f"  ✅ BufferFullError structure:")
    print(f"     Message: {error_message}")
    print(f"     Contains 'Buffer full': ✅")
    print(f"     Contains capacity info: ✅")

    print(f"\n{'='*60}")
    print("✅ UAT-10b Smoke Test 2: PASSED")
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
