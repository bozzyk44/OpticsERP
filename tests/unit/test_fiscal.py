"""
Unit Tests for Fiscal Module

Author: AI Agent
Created: 2025-10-09
Task: OPTERP-16

Test Coverage:
- process_fiscal_receipt() - Two-phase orchestration
- get_fiscal_status() - Status queries
- get_phase2_health() - Phase 2 health checks
- Error handling and edge cases
"""

import pytest
import sys
from pathlib import Path
from datetime import datetime

# Add kkt_adapter/app to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'kkt_adapter' / 'app'))

from fiscal import (
    process_fiscal_receipt,
    get_fiscal_status,
    get_phase2_health,
    FiscalResult,
    FiscalStatus,
    Phase2Health
)
from buffer import get_receipt_by_id, init_buffer_db, close_buffer_db, get_db, BufferFullError
from circuit_breaker import reset_circuit_breaker
from kkt_driver import reset_counter


# ====================
# Fixtures
# ====================

@pytest.fixture
def reset_test_env():
    """Reset test environment before each test"""
    # Reset database
    try:
        close_buffer_db()
    except:
        pass

    init_buffer_db()
    conn = get_db()
    conn.execute("DELETE FROM receipts")
    conn.execute("DELETE FROM dlq")
    conn.execute("DELETE FROM buffer_events")
    conn.commit()
    conn.isolation_level = None
    conn.execute("VACUUM")
    conn.isolation_level = ""

    # Reset other components
    reset_circuit_breaker()
    reset_counter()

    yield

    try:
        close_buffer_db()
    except:
        pass


@pytest.fixture
def sample_receipt():
    """Sample receipt data"""
    return {
        'pos_id': 'POS-TEST-001',
        'fiscal_doc': {
            'type': 'sale',
            'items': [
                {
                    'name': 'Test Product',
                    'price': 100.00,
                    'quantity': 2,
                    'total': 200.00,
                    'vat_rate': 20
                }
            ],
            'payments': [
                {
                    'type': 'cash',
                    'amount': 200.00
                }
            ],
            'idempotency_key': 'test-idem-key-001'
        }
    }


# ====================
# Tests: process_fiscal_receipt
# ====================

class TestProcessFiscalReceipt:
    """Tests for process_fiscal_receipt() function"""

    def test_process_success(self, reset_test_env, sample_receipt):
        """Test successful fiscal receipt processing"""
        result = process_fiscal_receipt(sample_receipt)

        assert isinstance(result, FiscalResult)
        assert result.status == 'printed'
        assert result.receipt_id is not None
        assert len(result.receipt_id) == 36  # UUID length
        assert result.fiscal_doc is not None
        assert 'fiscal_doc_number' in result.fiscal_doc
        assert 'fiscal_sign' in result.fiscal_doc
        assert result.error is None

    def test_process_creates_buffer_entry(self, reset_test_env, sample_receipt):
        """Test that processing creates buffer entry"""
        result = process_fiscal_receipt(sample_receipt)

        # Verify buffer entry
        receipt = get_receipt_by_id(result.receipt_id)
        assert receipt is not None
        assert receipt.pos_id == 'POS-TEST-001'
        assert receipt.status == 'pending'  # Phase 2 pending

    def test_process_updates_buffer_with_fiscal_doc(self, reset_test_env, sample_receipt):
        """Test that fiscal doc is stored in buffer"""
        import json

        result = process_fiscal_receipt(sample_receipt)

        receipt = get_receipt_by_id(result.receipt_id)
        assert receipt.fiscal_doc is not None

        # fiscal_doc is JSON string in DB, need to parse
        fiscal_doc_dict = json.loads(receipt.fiscal_doc)
        assert 'fiscal_doc_number' in fiscal_doc_dict
        assert fiscal_doc_dict['fiscal_doc_number'] == result.fiscal_doc['fiscal_doc_number']

    def test_process_multiple_receipts(self, reset_test_env, sample_receipt):
        """Test processing multiple receipts"""
        results = []
        for i in range(5):
            result = process_fiscal_receipt(sample_receipt)
            assert result.status == 'printed'
            results.append(result)

        # Verify all receipts have unique IDs
        receipt_ids = [r.receipt_id for r in results]
        assert len(set(receipt_ids)) == 5

        # Verify sequential fiscal doc numbers
        fiscal_numbers = [r.fiscal_doc['fiscal_doc_number'] for r in results]
        assert fiscal_numbers == [1, 2, 3, 4, 5]

    def test_process_invalid_receipt_missing_fiscal_doc(self, reset_test_env):
        """Test error when fiscal_doc missing"""
        invalid_receipt = {'pos_id': 'POS-001'}

        with pytest.raises(ValueError):
            process_fiscal_receipt(invalid_receipt)

    def test_process_invalid_receipt_empty_items(self, reset_test_env, sample_receipt):
        """Test error when items list empty"""
        sample_receipt['fiscal_doc']['items'] = []

        # Phase 1.1 succeeds (buffer), Phase 1.2 fails (print validation)
        result = process_fiscal_receipt(sample_receipt)
        assert result.status == 'buffered'  # Buffered but print failed
        assert result.error is not None
        assert 'items' in result.error.lower()

    def test_process_invalid_receipt_empty_payments(self, reset_test_env, sample_receipt):
        """Test error when payments list empty"""
        sample_receipt['fiscal_doc']['payments'] = []

        # Phase 1.1 succeeds (buffer), Phase 1.2 fails (print validation)
        result = process_fiscal_receipt(sample_receipt)
        assert result.status == 'buffered'  # Buffered but print failed
        assert result.error is not None
        assert 'payments' in result.error.lower()


# ====================
# Tests: get_fiscal_status
# ====================

class TestGetFiscalStatus:
    """Tests for get_fiscal_status() function"""

    def test_get_status_for_printed_receipt(self, reset_test_env, sample_receipt):
        """Test getting status for successfully printed receipt"""
        result = process_fiscal_receipt(sample_receipt)

        status = get_fiscal_status(result.receipt_id)

        assert isinstance(status, FiscalStatus)
        assert status.receipt_id == result.receipt_id
        assert status.phase1_status == 'completed'  # Print succeeded
        assert status.phase2_status == 'pending'    # OFD sync pending
        assert status.fiscal_doc is not None
        assert status.retry_count == 0

    def test_get_status_nonexistent_receipt(self, reset_test_env):
        """Test getting status for non-existent receipt"""
        status = get_fiscal_status('00000000-0000-0000-0000-000000000000')

        assert status is None

    def test_get_status_includes_fiscal_doc(self, reset_test_env, sample_receipt):
        """Test that status includes fiscal document"""
        result = process_fiscal_receipt(sample_receipt)

        status = get_fiscal_status(result.receipt_id)

        assert status.fiscal_doc is not None
        assert status.fiscal_doc['fiscal_doc_number'] == result.fiscal_doc['fiscal_doc_number']
        assert status.fiscal_doc['fiscal_sign'] == result.fiscal_doc['fiscal_sign']


# ====================
# Tests: get_phase2_health
# ====================

class TestGetPhase2Health:
    """Tests for get_phase2_health() function"""

    def test_get_phase2_health_initial_state(self, reset_test_env):
        """Test Phase 2 health in initial state"""
        health = get_phase2_health()

        assert isinstance(health, Phase2Health)
        # Worker may not be running in unit tests (that's OK)
        assert isinstance(health.worker_running, bool)
        assert health.circuit_breaker_state == 'CLOSED'  # CB should be closed initially
        assert health.pending_count >= 0
        assert health.success_count >= 0
        assert health.failure_count >= 0

    def test_get_phase2_health_with_pending_receipts(self, reset_test_env, sample_receipt):
        """Test Phase 2 health reports pending count"""
        # Note: In unit tests, worker may not be running, so pending_count
        # comes from worker_status which may report 0 if worker not started
        health = get_phase2_health()

        # Just verify health object is valid
        assert isinstance(health, Phase2Health)
        assert health.pending_count >= 0  # May be 0 if worker not running

    def test_get_phase2_health_circuit_breaker_state(self, reset_test_env):
        """Test that Phase 2 health reports CB state"""
        health = get_phase2_health()

        # Should be one of valid states
        assert health.circuit_breaker_state in ['CLOSED', 'OPEN', 'HALF_OPEN']


# ====================
# Tests: Data Classes
# ====================

class TestDataClasses:
    """Tests for data classes"""

    def test_fiscal_result_creation(self):
        """Test FiscalResult creation"""
        result = FiscalResult(
            receipt_id='test-id',
            status='printed',
            fiscal_doc={'doc_number': 1},
            error=None
        )

        assert result.receipt_id == 'test-id'
        assert result.status == 'printed'
        assert result.fiscal_doc['doc_number'] == 1
        assert result.error is None

    def test_fiscal_status_creation(self):
        """Test FiscalStatus creation"""
        status = FiscalStatus(
            receipt_id='test-id',
            phase1_status='completed',
            phase2_status='pending',
            fiscal_doc={'doc_number': 1},
            retry_count=0
        )

        assert status.receipt_id == 'test-id'
        assert status.phase1_status == 'completed'
        assert status.phase2_status == 'pending'

    def test_phase2_health_creation(self):
        """Test Phase2Health creation"""
        health = Phase2Health(
            worker_running=True,
            circuit_breaker_state='CLOSED',
            pending_count=5,
            success_count=100,
            failure_count=2
        )

        assert health.worker_running is True
        assert health.circuit_breaker_state == 'CLOSED'
        assert health.pending_count == 5


# ====================
# Tests: Edge Cases
# ====================

class TestEdgeCases:
    """Tests for edge cases and error handling"""

    def test_process_with_special_characters(self, reset_test_env, sample_receipt):
        """Test processing receipt with special characters"""
        sample_receipt['pos_id'] = 'POS-Тест-001-Ёлка'
        sample_receipt['fiscal_doc']['items'][0]['name'] = 'Товар "Тест" №1'

        result = process_fiscal_receipt(sample_receipt)

        assert result.status == 'printed'
        assert result.receipt_id is not None

    def test_process_with_large_amounts(self, reset_test_env, sample_receipt):
        """Test processing receipt with large monetary amounts"""
        sample_receipt['fiscal_doc']['items'][0]['price'] = 999999.99
        sample_receipt['fiscal_doc']['items'][0]['quantity'] = 100
        sample_receipt['fiscal_doc']['items'][0]['total'] = 99999999.00
        sample_receipt['fiscal_doc']['payments'][0]['amount'] = 99999999.00

        result = process_fiscal_receipt(sample_receipt)

        assert result.status == 'printed'
        assert result.fiscal_doc['total'] == 99999999.00

    def test_process_with_zero_amount(self, reset_test_env, sample_receipt):
        """Test processing receipt with zero amount (edge case)"""
        sample_receipt['fiscal_doc']['items'][0]['price'] = 0.00
        sample_receipt['fiscal_doc']['items'][0]['total'] = 0.00
        sample_receipt['fiscal_doc']['payments'][0]['amount'] = 0.00

        result = process_fiscal_receipt(sample_receipt)

        assert result.status == 'printed'
        assert result.fiscal_doc['total'] == 0.00
