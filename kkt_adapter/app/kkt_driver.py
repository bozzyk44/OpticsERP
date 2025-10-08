"""
Mock KKT Driver for POC

Author: AI Agent
Created: 2025-10-08
Purpose: Emulate fiscal receipt printing for offline-first testing

This is a MOCK driver for POC phase. Real driver integration in Phase 2.

Reference: CLAUDE.md §7 (Two-Phase Fiscalization)
Task: OPTERP-10, OPTERP-17

Key Features:
- Mock fiscal document generation
- Simulated print delay (200-500ms)
- Sequential fiscal document numbering
- Mock QR code generation
- Always succeeds (no errors for POC)
"""

import time
import hashlib
import threading
from typing import Dict, Any
from datetime import datetime

# ====================
# Global State
# ====================

# Thread-safe counter for fiscal document numbers
_fiscal_doc_counter = 0
_counter_lock = threading.Lock()

# Mock KKT configuration
MOCK_KKT_CONFIG = {
    "kkt_number": "0000000000001234",  # Mock ККТ registration number
    "fn_number": "9999999999999999",    # Mock Fiscal Module serial
    "ofd_name": "Платформа ОФД",        # Mock OFD provider
    "inn": "7707083893",                 # Mock company INN
    "rn_kkt": "0000000000001234",        # Mock ККТ registration number
}


# ====================
# Helper Functions
# ====================

def _get_next_fiscal_doc_number() -> int:
    """
    Get next fiscal document number (thread-safe)

    Returns:
        Sequential fiscal document number
    """
    global _fiscal_doc_counter
    with _counter_lock:
        _fiscal_doc_counter += 1
        return _fiscal_doc_counter


def _generate_fiscal_sign(receipt_data: dict, fiscal_doc_number: int) -> str:
    """
    Generate mock fiscal sign (hash)

    In real implementation, this is cryptographic signature from FN.
    For POC, we use simple hash for uniqueness.

    Args:
        receipt_data: Receipt data
        fiscal_doc_number: Fiscal document number

    Returns:
        Mock fiscal sign (10-digit hex)
    """
    # Create deterministic hash from receipt data + fiscal doc number
    data_str = f"{fiscal_doc_number}_{receipt_data.get('pos_id', '')}_{datetime.now().isoformat()}"
    hash_obj = hashlib.sha256(data_str.encode('utf-8'))
    fiscal_sign = hash_obj.hexdigest()[:10]  # First 10 chars
    return fiscal_sign.upper()


def _generate_qr_code_data(fiscal_doc_number: int, fiscal_sign: str, total: float, datetime_str: str) -> str:
    """
    Generate mock QR code data (for receipt verification)

    Real format: t=YYYYMMDDTHHMM&s=TOTAL&fn=FN_NUMBER&i=FISCAL_DOC&fp=FISCAL_SIGN&n=1

    Args:
        fiscal_doc_number: Fiscal document number
        fiscal_sign: Fiscal sign
        total: Receipt total
        datetime_str: Receipt datetime (ISO format)

    Returns:
        Mock QR code data string
    """
    # Convert datetime to ФФД format YYYYMMDDTHHMM
    dt = datetime.fromisoformat(datetime_str.replace('Z', '+00:00'))
    t = dt.strftime("%Y%m%dT%H%M")

    qr_data = (
        f"t={t}"
        f"&s={total:.2f}"
        f"&fn={MOCK_KKT_CONFIG['fn_number']}"
        f"&i={fiscal_doc_number}"
        f"&fp={fiscal_sign}"
        f"&n=1"
    )

    return qr_data


# ====================
# Public API
# ====================

def print_receipt(receipt_data: dict) -> Dict[str, Any]:
    """
    Mock fiscal receipt printing

    Simulates:
    - 200-500ms print delay
    - Fiscal document generation
    - Sequential fiscal doc numbering

    Args:
        receipt_data: Receipt data with structure:
            {
                'pos_id': str,
                'fiscal_doc': {
                    'type': 'sale' | 'refund',
                    'items': [...],
                    'payments': [...],
                    'idempotency_key': str
                }
            }

    Returns:
        Fiscal document dict:
            {
                'fiscal_doc_number': int,
                'fiscal_sign': str,
                'fiscal_datetime': str (ISO 8601),
                'fn_number': str,
                'kkt_number': str,
                'qr_code_data': str,
                'shift_number': int,
                'receipt_number': int
            }

    Raises:
        ValueError: Invalid receipt data
    """
    # Validate input
    if not receipt_data or 'fiscal_doc' not in receipt_data:
        raise ValueError("Invalid receipt data: missing 'fiscal_doc'")

    fiscal_doc_data = receipt_data['fiscal_doc']

    if 'items' not in fiscal_doc_data or not fiscal_doc_data['items']:
        raise ValueError("Invalid receipt data: missing or empty 'items'")

    if 'payments' not in fiscal_doc_data or not fiscal_doc_data['payments']:
        raise ValueError("Invalid receipt data: missing or empty 'payments'")

    # Calculate total from items (convert to float for safety)
    total = sum(
        float(item.get('price', 0)) * float(item.get('quantity', 1))
        for item in fiscal_doc_data['items']
    )

    # Simulate print delay (200-500ms)
    import random
    print_delay = random.uniform(0.2, 0.5)
    time.sleep(print_delay)

    # Generate fiscal document
    fiscal_doc_number = _get_next_fiscal_doc_number()
    fiscal_datetime = datetime.utcnow().isoformat() + 'Z'
    fiscal_sign = _generate_fiscal_sign(receipt_data, fiscal_doc_number)
    qr_code_data = _generate_qr_code_data(fiscal_doc_number, fiscal_sign, total, fiscal_datetime)

    fiscal_document = {
        'fiscal_doc_number': fiscal_doc_number,
        'fiscal_sign': fiscal_sign,
        'fiscal_datetime': fiscal_datetime,
        'fn_number': MOCK_KKT_CONFIG['fn_number'],
        'kkt_number': MOCK_KKT_CONFIG['kkt_number'],
        'qr_code_data': qr_code_data,
        'shift_number': 1,  # Mock shift number (always 1 for POC)
        'receipt_number': fiscal_doc_number,  # For simplicity, same as fiscal doc number
        'ofd_name': MOCK_KKT_CONFIG['ofd_name'],
        'inn': MOCK_KKT_CONFIG['inn'],
        'rn_kkt': MOCK_KKT_CONFIG['rn_kkt'],
        'total': total
    }

    return fiscal_document


def get_kkt_status() -> Dict[str, Any]:
    """
    Get mock KKT status

    Returns:
        KKT status dict:
            {
                'online': bool,
                'fn_space_left': int (days),
                'shift_open': bool,
                'kkt_number': str,
                'fn_number': str
            }
    """
    return {
        'online': True,
        'fn_space_left': 365,  # Mock: 1 year left
        'shift_open': True,
        'kkt_number': MOCK_KKT_CONFIG['kkt_number'],
        'fn_number': MOCK_KKT_CONFIG['fn_number'],
        'ofd_name': MOCK_KKT_CONFIG['ofd_name'],
        'last_fiscal_doc': _fiscal_doc_counter
    }


def get_shift_info() -> Dict[str, Any]:
    """
    Get mock shift information

    Returns:
        Shift info dict:
            {
                'shift_number': int,
                'shift_open': bool,
                'shift_open_datetime': str,
                'receipts_count': int
            }
    """
    return {
        'shift_number': 1,
        'shift_open': True,
        'shift_open_datetime': datetime.utcnow().isoformat() + 'Z',
        'receipts_count': _fiscal_doc_counter
    }


def reset_counter():
    """
    Reset fiscal document counter (for testing only)

    WARNING: For testing purposes only. Do NOT use in production.
    """
    global _fiscal_doc_counter
    with _counter_lock:
        _fiscal_doc_counter = 0
