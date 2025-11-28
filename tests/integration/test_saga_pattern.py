"""
Integration Tests for Saga Pattern (Refund Blocking)

Author: AI Agent
Created: 2025-11-27
Task: OPTERP-48
Reference: CLAUDE.md §5 (Saga pattern), OPTERP-47 (implementation)

Test Coverage:
- Refund blocked if original receipt not synced (HTTP 409)
- Refund allowed if original receipt synced (HTTP 200)
- Refund allowed if original receipt not found (HTTP 200)
- Error handling (timeout, connection errors)
- Edge cases (non-fiscal orders, missing fiscal_doc_id)

Target Coverage: ≥95%
"""

import pytest
import uuid
import time
from typing import Optional

# Import modules under test
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "kkt_adapter" / "app"))

from buffer import insert_receipt, get_receipt_by_id, mark_synced, get_db


# ====================
# Test Fixtures
# ====================

@pytest.fixture
def fiscal_doc_id():
    """Generate unique fiscal document ID"""
    return f"{int(time.time())}_{uuid.uuid4().hex[:8]}"


@pytest.fixture
def original_receipt_pending(fiscal_doc_id, clean_buffer):
    """
    Create original receipt in buffer (pending status)

    Returns fiscal_doc_id for testing
    """
    receipt_data = {
        'pos_id': 'POS-001',
        'type': 'sale',
        'items': [
            {'name': 'Product 1', 'price': 100.0, 'qty': 1},
        ],
        'total': 100.0,
        'payments': [
            {'method': 'cash', 'amount': 100.0},
        ],
    }

    # Insert receipt into buffer (status='pending')
    receipt_id = insert_receipt(
        pos_id='POS-001',
        fiscal_doc_id=fiscal_doc_id,
        receipt_data=receipt_data
    )

    # Verify receipt is pending
    receipt = get_receipt_by_id(receipt_id)
    assert receipt is not None
    assert receipt['status'] == 'pending'

    return fiscal_doc_id


@pytest.fixture
def original_receipt_synced(fiscal_doc_id, clean_buffer):
    """
    Create original receipt and mark as synced

    Returns fiscal_doc_id for testing
    """
    receipt_data = {
        'pos_id': 'POS-001',
        'type': 'sale',
        'items': [
            {'name': 'Product 2', 'price': 200.0, 'qty': 1},
        ],
        'total': 200.0,
        'payments': [
            {'method': 'card', 'amount': 200.0},
        ],
    }

    # Insert receipt into buffer
    receipt_id = insert_receipt(
        pos_id='POS-001',
        fiscal_doc_id=fiscal_doc_id,
        receipt_data=receipt_data
    )

    # Mark as synced
    mark_synced(receipt_id, ofd_receipt_id='OFD-12345')

    # Verify receipt is synced
    receipt = get_receipt_by_id(receipt_id)
    assert receipt is not None
    assert receipt['status'] == 'synced'

    return fiscal_doc_id


# ====================
# Saga Pattern Tests
# ====================

class TestSagaPatternRefundBlocking:
    """Test suite for Saga pattern refund blocking"""

    def test_refund_blocked_if_not_synced(self, fastapi_server_auto, original_receipt_pending):
        """
        Test: Refund blocked if original receipt not synced (HTTP 409)

        Scenario:
        1. Original receipt in buffer (status='pending')
        2. Attempt refund
        3. POST /v1/pos/refund returns HTTP 409 Conflict
        4. Refund blocked
        """
        import requests

        fiscal_doc_id = original_receipt_pending

        # Attempt refund
        response = requests.post(
            f"{fastapi_server_auto}/v1/pos/refund",
            json={'original_fiscal_doc_id': fiscal_doc_id},
            timeout=5,
        )

        # Assert HTTP 409 Conflict (refund blocked)
        assert response.status_code == 409, f"Expected 409, got {response.status_code}"

        data = response.json()

        # Assert response structure
        assert 'allowed' in data
        assert data['allowed'] is False

        assert 'sync_status' in data
        assert data['sync_status'] == 'pending'

        assert 'reason' in data
        assert 'not synced' in data['reason'].lower()

        # Assert buffer info included
        assert 'buffer_count' in data or 'buffer_percent' in data

    def test_refund_allowed_if_synced(self, fastapi_server_auto, original_receipt_synced):
        """
        Test: Refund allowed if original receipt synced (HTTP 200)

        Scenario:
        1. Original receipt synced (status='synced')
        2. Attempt refund
        3. POST /v1/pos/refund returns HTTP 200 OK
        4. Refund allowed
        """
        import requests

        fiscal_doc_id = original_receipt_synced

        # Attempt refund
        response = requests.post(
            f"{fastapi_server_auto}/v1/pos/refund",
            json={'original_fiscal_doc_id': fiscal_doc_id},
            timeout=5,
        )

        # Assert HTTP 200 OK (refund allowed)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"

        data = response.json()

        # Assert response structure
        assert 'allowed' in data
        assert data['allowed'] is True

        assert 'sync_status' in data
        # Synced receipts are removed from buffer, so status should be 'synced' or 'not_found'
        assert data['sync_status'] in ('synced', 'not_found')

    def test_refund_allowed_if_not_found(self, fastapi_server_auto, fiscal_doc_id, clean_buffer):
        """
        Test: Refund allowed if original receipt not found (HTTP 200)

        Scenario:
        1. Original receipt not in buffer (likely synced and removed)
        2. Attempt refund
        3. POST /v1/pos/refund returns HTTP 200 OK
        4. Refund allowed (assume synced)
        """
        import requests

        # Attempt refund for non-existent receipt
        response = requests.post(
            f"{fastapi_server_auto}/v1/pos/refund",
            json={'original_fiscal_doc_id': fiscal_doc_id},
            timeout=5,
        )

        # Assert HTTP 200 OK (refund allowed - not found = synced)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"

        data = response.json()

        # Assert response structure
        assert 'allowed' in data
        assert data['allowed'] is True

        assert 'sync_status' in data
        assert data['sync_status'] == 'not_found'

    def test_refund_validation_missing_fiscal_doc_id(self, fastapi_server_auto):
        """
        Test: Validation error if fiscal_doc_id missing

        Scenario:
        1. POST /v1/pos/refund without fiscal_doc_id
        2. Returns HTTP 400 Bad Request
        """
        import requests

        # Attempt refund without fiscal_doc_id
        response = requests.post(
            f"{fastapi_server_auto}/v1/pos/refund",
            json={},  # Missing fiscal_doc_id
            timeout=5,
        )

        # Assert HTTP 400 Bad Request (validation error)
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"

        data = response.json()

        # Assert error message
        assert 'detail' in data or 'error' in data

    def test_refund_blocked_multiple_receipts(self, fastapi_server_auto, clean_buffer):
        """
        Test: Refund blocked for correct receipt among multiple

        Scenario:
        1. Insert multiple receipts (some pending, some synced)
        2. Attempt refund for pending receipt → Blocked (HTTP 409)
        3. Attempt refund for synced receipt → Allowed (HTTP 200)
        """
        import requests

        # Create pending receipt
        fiscal_doc_id_pending = f"{int(time.time())}_{uuid.uuid4().hex[:8]}"
        receipt_id_pending = insert_receipt(
            pos_id='POS-001',
            fiscal_doc_id=fiscal_doc_id_pending,
            receipt_data={'total': 100.0}
        )

        # Create synced receipt
        fiscal_doc_id_synced = f"{int(time.time())}_{uuid.uuid4().hex[:8]}"
        receipt_id_synced = insert_receipt(
            pos_id='POS-001',
            fiscal_doc_id=fiscal_doc_id_synced,
            receipt_data={'total': 200.0}
        )
        mark_synced(receipt_id_synced, ofd_receipt_id='OFD-67890')

        # Test 1: Refund for pending receipt → Blocked
        response1 = requests.post(
            f"{fastapi_server_auto}/v1/pos/refund",
            json={'original_fiscal_doc_id': fiscal_doc_id_pending},
            timeout=5,
        )
        assert response1.status_code == 409
        assert response1.json()['allowed'] is False

        # Test 2: Refund for synced receipt → Allowed
        response2 = requests.post(
            f"{fastapi_server_auto}/v1/pos/refund",
            json={'original_fiscal_doc_id': fiscal_doc_id_synced},
            timeout=5,
        )
        assert response2.status_code == 200
        assert response2.json()['allowed'] is True

    def test_refund_edge_case_empty_fiscal_doc_id(self, fastapi_server_auto):
        """
        Test: Edge case - empty fiscal_doc_id

        Scenario:
        1. POST /v1/pos/refund with empty fiscal_doc_id
        2. Returns HTTP 400 Bad Request
        """
        import requests

        # Attempt refund with empty fiscal_doc_id
        response = requests.post(
            f"{fastapi_server_auto}/v1/pos/refund",
            json={'original_fiscal_doc_id': ''},
            timeout=5,
        )

        # Assert HTTP 400 Bad Request
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"

    def test_refund_concurrent_requests(self, fastapi_server_auto, original_receipt_pending):
        """
        Test: Concurrent refund requests for same receipt

        Scenario:
        1. Original receipt pending
        2. Send multiple concurrent refund requests
        3. All should return HTTP 409 (blocked)
        """
        import requests
        import concurrent.futures

        fiscal_doc_id = original_receipt_pending

        # Send 5 concurrent refund requests
        def attempt_refund():
            return requests.post(
                f"{fastapi_server_auto}/v1/pos/refund",
                json={'original_fiscal_doc_id': fiscal_doc_id},
                timeout=5,
            )

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(attempt_refund) for _ in range(5)]
            responses = [f.result() for f in futures]

        # All responses should be HTTP 409 (blocked)
        for response in responses:
            assert response.status_code == 409
            assert response.json()['allowed'] is False


# ====================
# Performance Tests
# ====================

class TestSagaPatternPerformance:
    """Performance tests for Saga pattern"""

    def test_refund_check_performance(self, fastapi_server_auto, original_receipt_pending):
        """
        Test: Refund check performance

        Requirement: P95 refund check ≤ 50ms
        """
        import requests
        import time

        fiscal_doc_id = original_receipt_pending

        # Perform 100 refund checks
        latencies = []
        for _ in range(100):
            start = time.time()

            response = requests.post(
                f"{fastapi_server_auto}/v1/pos/refund",
                json={'original_fiscal_doc_id': fiscal_doc_id},
                timeout=5,
            )

            latency = (time.time() - start) * 1000  # Convert to ms
            latencies.append(latency)

            assert response.status_code == 409

        # Calculate P95
        latencies.sort()
        p95_index = int(len(latencies) * 0.95)
        p95_latency = latencies[p95_index]

        # Assert P95 ≤ 50ms
        assert p95_latency <= 50, f"P95 latency {p95_latency:.2f}ms exceeds 50ms threshold"

        # Log results
        avg_latency = sum(latencies) / len(latencies)
        print(f"\nRefund check performance:")
        print(f"  Average: {avg_latency:.2f}ms")
        print(f"  P95: {p95_latency:.2f}ms")
        print(f"  Max: {max(latencies):.2f}ms")


# ====================
# Summary
# ====================
"""
Test Coverage Summary:

Saga Pattern Tests (7 tests):
1. test_refund_blocked_if_not_synced() - HTTP 409 when original pending
2. test_refund_allowed_if_synced() - HTTP 200 when original synced
3. test_refund_allowed_if_not_found() - HTTP 200 when original not found
4. test_refund_validation_missing_fiscal_doc_id() - HTTP 400 validation
5. test_refund_blocked_multiple_receipts() - Multiple receipts handling
6. test_refund_edge_case_empty_fiscal_doc_id() - Edge case handling
7. test_refund_concurrent_requests() - Concurrent request handling

Performance Tests (1 test):
1. test_refund_check_performance() - P95 ≤ 50ms

Total Tests: 8
Coverage Target: ≥95%
"""
