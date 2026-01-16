"""
Unit tests for Mock KKT Driver

Author: AI Agent
Created: 2025-10-08
Task: OPTERP-10, OPTERP-17

Test Coverage:
- print_receipt() - Mock fiscal document generation
- get_kkt_status() - KKT status retrieval
- get_shift_info() - Shift information
- Sequential fiscal doc numbering
- Print delay simulation
- Thread safety
"""

import pytest
import time
import threading
from decimal import Decimal

# Import module under test
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "kkt_adapter" / "app"))

from kkt_driver import (
    print_receipt,
    get_kkt_status,
    get_shift_info,
    reset_counter,
    MOCK_KKT_CONFIG
)


# ====================
# Fixtures
# ====================

@pytest.fixture(autouse=True)
def reset_fiscal_counter():
    """Reset fiscal document counter before each test"""
    reset_counter()
    yield
    reset_counter()


@pytest.fixture
def sample_receipt_data():
    """Sample receipt data for testing"""
    return {
        'pos_id': 'POS-001',
        'fiscal_doc': {
            'type': 'sale',
            'items': [
                {
                    'name': 'Test Product',
                    'price': 100.00,
                    'quantity': 2,
                    'vat_rate': 20
                }
            ],
            'payments': [
                {
                    'type': 'cash',
                    'amount': 200.00
                }
            ],
            'idempotency_key': 'test-key-001'
        }
    }


# ====================
# Tests: print_receipt()
# ====================

class TestPrintReceipt:
    """Tests for print_receipt function"""

    def test_print_receipt_success(self, sample_receipt_data):
        """Test successful receipt printing"""
        fiscal_doc = print_receipt(sample_receipt_data)

        # Verify fiscal document structure
        assert 'fiscal_doc_number' in fiscal_doc
        assert 'fiscal_sign' in fiscal_doc
        assert 'fiscal_datetime' in fiscal_doc
        assert 'fn_number' in fiscal_doc
        assert 'kkt_number' in fiscal_doc
        assert 'qr_code_data' in fiscal_doc
        assert 'shift_number' in fiscal_doc
        assert 'receipt_number' in fiscal_doc
        assert 'total' in fiscal_doc

        # Verify values
        assert fiscal_doc['fiscal_doc_number'] == 1  # First receipt
        assert fiscal_doc['fn_number'] == MOCK_KKT_CONFIG['fn_number']
        assert fiscal_doc['kkt_number'] == MOCK_KKT_CONFIG['kkt_number']
        assert fiscal_doc['total'] == 200.00  # 100 * 2
        assert len(fiscal_doc['fiscal_sign']) == 10  # Mock sign length

    def test_print_receipt_sequential_numbering(self, sample_receipt_data):
        """Test sequential fiscal doc numbering"""
        fiscal_doc1 = print_receipt(sample_receipt_data)
        fiscal_doc2 = print_receipt(sample_receipt_data)
        fiscal_doc3 = print_receipt(sample_receipt_data)

        assert fiscal_doc1['fiscal_doc_number'] == 1
        assert fiscal_doc2['fiscal_doc_number'] == 2
        assert fiscal_doc3['fiscal_doc_number'] == 3

    def test_print_receipt_delay(self, sample_receipt_data):
        """Test print delay simulation (200-500ms)"""
        start = time.time()
        print_receipt(sample_receipt_data)
        duration = time.time() - start

        # Verify delay is within expected range
        assert 0.2 <= duration <= 0.6  # Allow 100ms margin

    def test_print_receipt_qr_code_format(self, sample_receipt_data):
        """Test QR code data format"""
        fiscal_doc = print_receipt(sample_receipt_data)
        qr_data = fiscal_doc['qr_code_data']

        # Verify QR code format (ФФД 1.2)
        assert 't=' in qr_data  # timestamp
        assert 's=' in qr_data  # sum
        assert 'fn=' in qr_data  # FN number
        assert 'i=' in qr_data  # fiscal doc number
        assert 'fp=' in qr_data  # fiscal sign
        assert 'n=1' in qr_data  # receipt type (sale=1)

    def test_print_receipt_multiple_items(self, sample_receipt_data):
        """Test receipt with multiple items"""
        sample_receipt_data['fiscal_doc']['items'] = [
            {'name': 'Item 1', 'price': 50.0, 'quantity': 2, 'vat_rate': 20},
            {'name': 'Item 2', 'price': 75.0, 'quantity': 1, 'vat_rate': 20},
        ]
        sample_receipt_data['fiscal_doc']['payments'][0]['amount'] = 175.0

        fiscal_doc = print_receipt(sample_receipt_data)

        # Verify total calculation
        assert fiscal_doc['total'] == 175.0  # (50*2) + (75*1)

    def test_print_receipt_missing_fiscal_doc(self):
        """Test error handling for missing fiscal_doc"""
        invalid_data = {'pos_id': 'POS-001'}

        with pytest.raises(ValueError, match="missing 'fiscal_doc'"):
            print_receipt(invalid_data)

    def test_print_receipt_empty_items(self, sample_receipt_data):
        """Test error handling for empty items"""
        sample_receipt_data['fiscal_doc']['items'] = []

        with pytest.raises(ValueError, match="missing or empty 'items'"):
            print_receipt(sample_receipt_data)

    def test_print_receipt_empty_payments(self, sample_receipt_data):
        """Test error handling for empty payments"""
        sample_receipt_data['fiscal_doc']['payments'] = []

        with pytest.raises(ValueError, match="missing or empty 'payments'"):
            print_receipt(sample_receipt_data)

    def test_print_receipt_fiscal_sign_uniqueness(self, sample_receipt_data):
        """Test fiscal sign uniqueness across receipts"""
        fiscal_doc1 = print_receipt(sample_receipt_data)
        time.sleep(0.01)  # Small delay to ensure different timestamps
        fiscal_doc2 = print_receipt(sample_receipt_data)

        # Fiscal signs should be different
        assert fiscal_doc1['fiscal_sign'] != fiscal_doc2['fiscal_sign']


# ====================
# Tests: get_kkt_status()
# ====================

class TestGetKKTStatus:
    """Tests for get_kkt_status function"""

    def test_get_kkt_status_structure(self):
        """Test KKT status structure"""
        status = get_kkt_status()

        assert 'online' in status
        assert 'fn_space_left' in status
        assert 'shift_open' in status
        assert 'kkt_number' in status
        assert 'fn_number' in status
        assert 'ofd_name' in status
        assert 'last_fiscal_doc' in status

    def test_get_kkt_status_values(self):
        """Test KKT status default values"""
        status = get_kkt_status()

        assert status['online'] is True
        assert status['fn_space_left'] == 365  # Mock: 1 year
        assert status['shift_open'] is True
        assert status['kkt_number'] == MOCK_KKT_CONFIG['kkt_number']
        assert status['fn_number'] == MOCK_KKT_CONFIG['fn_number']

    def test_get_kkt_status_tracks_receipts(self, sample_receipt_data):
        """Test status tracks fiscal doc counter"""
        status_before = get_kkt_status()
        assert status_before['last_fiscal_doc'] == 0

        print_receipt(sample_receipt_data)
        print_receipt(sample_receipt_data)

        status_after = get_kkt_status()
        assert status_after['last_fiscal_doc'] == 2


# ====================
# Tests: get_shift_info()
# ====================

class TestGetShiftInfo:
    """Tests for get_shift_info function"""

    def test_get_shift_info_structure(self):
        """Test shift info structure"""
        shift = get_shift_info()

        assert 'shift_number' in shift
        assert 'shift_open' in shift
        assert 'shift_open_datetime' in shift
        assert 'receipts_count' in shift

    def test_get_shift_info_values(self):
        """Test shift info default values"""
        shift = get_shift_info()

        assert shift['shift_number'] == 1  # Mock: always shift 1
        assert shift['shift_open'] is True
        assert isinstance(shift['shift_open_datetime'], str)
        assert 'Z' in shift['shift_open_datetime']  # UTC timezone

    def test_get_shift_info_tracks_receipts(self, sample_receipt_data):
        """Test shift info tracks receipts count"""
        shift_before = get_shift_info()
        assert shift_before['receipts_count'] == 0

        print_receipt(sample_receipt_data)
        print_receipt(sample_receipt_data)
        print_receipt(sample_receipt_data)

        shift_after = get_shift_info()
        assert shift_after['receipts_count'] == 3


# ====================
# Tests: Thread Safety
# ====================

class TestThreadSafety:
    """Tests for thread safety of fiscal doc counter"""

    def test_concurrent_printing(self, sample_receipt_data):
        """Test concurrent receipt printing maintains sequential numbering"""
        num_threads = 10
        results = []
        lock = threading.Lock()

        def print_worker():
            fiscal_doc = print_receipt(sample_receipt_data)
            with lock:
                results.append(fiscal_doc['fiscal_doc_number'])

        # Create and start threads
        threads = [threading.Thread(target=print_worker) for _ in range(num_threads)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        # Verify all numbers are unique and sequential
        assert len(results) == num_threads
        assert len(set(results)) == num_threads  # All unique
        assert set(results) == set(range(1, num_threads + 1))  # Sequential 1..N

    def test_no_duplicate_fiscal_doc_numbers(self, sample_receipt_data):
        """Test no duplicate fiscal doc numbers under concurrent load"""
        num_receipts = 50
        fiscal_numbers = []
        lock = threading.Lock()

        def print_worker():
            for _ in range(5):
                fiscal_doc = print_receipt(sample_receipt_data)
                with lock:
                    fiscal_numbers.append(fiscal_doc['fiscal_doc_number'])

        threads = [threading.Thread(target=print_worker) for _ in range(10)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        # Verify no duplicates
        assert len(fiscal_numbers) == num_receipts
        assert len(set(fiscal_numbers)) == num_receipts


# ====================
# Tests: Edge Cases
# ====================

class TestEdgeCases:
    """Tests for edge cases and error handling"""

    def test_print_receipt_with_none_data(self):
        """Test error handling for None receipt data"""
        with pytest.raises(ValueError):
            print_receipt(None)

    def test_print_receipt_with_empty_dict(self):
        """Test error handling for empty dict"""
        with pytest.raises(ValueError, match="missing 'fiscal_doc'"):
            print_receipt({})

    def test_reset_counter_functionality(self, sample_receipt_data):
        """Test counter reset functionality"""
        print_receipt(sample_receipt_data)
        print_receipt(sample_receipt_data)

        status_before = get_kkt_status()
        assert status_before['last_fiscal_doc'] == 2

        reset_counter()

        status_after = get_kkt_status()
        assert status_after['last_fiscal_doc'] == 0

        # Next receipt should start from 1 again
        fiscal_doc = print_receipt(sample_receipt_data)
        assert fiscal_doc['fiscal_doc_number'] == 1
