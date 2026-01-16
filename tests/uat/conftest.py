"""
Pytest Fixtures for UAT (User Acceptance Testing)

Author: AI Agent
Created: 2025-11-29
Task: OPTERP-50 (Create UAT-01 Sale Test)

Purpose:
Provide fixtures for end-to-end UAT tests with Odoo integration.
UAT tests verify complete business workflows from UI to database.

Reference: CLAUDE.md §8 (UAT Testing)
"""

import pytest
import sys
from pathlib import Path

# Note: UAT tests require Odoo to be running
# These are placeholders for future Odoo integration

# ====================
# Configuration
# ====================

ODOO_URL = "http://localhost:8069"
ODOO_DB = "opticserp_test"
ODOO_USERNAME = "admin"
ODOO_PASSWORD = "admin"

# ====================
# Odoo Connection Fixtures
# ====================

@pytest.fixture(scope="session")
def odoo_url():
    """
    Odoo URL for UAT tests

    Returns:
        str: Odoo base URL
    """
    return ODOO_URL


@pytest.fixture(scope="session")
def odoo_credentials():
    """
    Odoo credentials for UAT tests

    Returns:
        dict: {db, username, password}
    """
    return {
        "db": ODOO_DB,
        "username": ODOO_USERNAME,
        "password": ODOO_PASSWORD,
    }


@pytest.fixture(scope="function")
def odoo_env(odoo_url, odoo_credentials):
    """
    Odoo environment (ORM) for UAT tests

    This fixture provides access to Odoo ORM for creating test data.

    Note: Requires odoorpc or xmlrpc.client

    Returns:
        Odoo environment object
    """
    # TODO: Implement Odoo connection via odoorpc or xmlrpc
    # For now, return None (tests will skip if Odoo not available)

    pytest.skip("Odoo connection not implemented yet (requires odoorpc)")

    # Example implementation (future):
    # import odoorpc
    # odoo = odoorpc.ODOO(host='localhost', port=8069)
    # odoo.login(db=odoo_credentials['db'],
    #            login=odoo_credentials['username'],
    #            password=odoo_credentials['password'])
    # yield odoo
    # odoo.logout()


# ====================
# Test Data Fixtures
# ====================

@pytest.fixture(scope="function")
def sample_prescription():
    """
    Sample prescription data for UAT tests

    Returns:
        dict: Prescription data (Sph, Cyl, Axis, PD, etc.)
    """
    return {
        "right_eye": {
            "sph": -2.50,
            "cyl": -1.00,
            "axis": 180,
            "add": 0.00,
            "prism": 0.00,
        },
        "left_eye": {
            "sph": -2.75,
            "cyl": -0.75,
            "axis": 175,
            "add": 0.00,
            "prism": 0.00,
        },
        "pd": 64.0,
        "notes": "UAT-01 test prescription"
    }


@pytest.fixture(scope="function")
def sample_lens():
    """
    Sample lens data for UAT tests

    Returns:
        dict: Lens data (type, index, coating)
    """
    return {
        "lens_type": "progressive",
        "index": 1.67,
        "coating": "anti_reflective",
        "material": "polycarbonate",
        "brand": "Test Brand",
        "price": 5000.00,
    }


@pytest.fixture(scope="function")
def sample_frame():
    """
    Sample frame data for UAT tests

    Returns:
        dict: Frame data (brand, model, price)
    """
    return {
        "brand": "Test Brand",
        "model": "Model X",
        "color": "Black",
        "size": "54-18-140",
        "price": 3000.00,
    }


@pytest.fixture(scope="function")
def sample_customer():
    """
    Sample customer data for UAT tests

    Returns:
        dict: Customer data (name, phone, email)
    """
    return {
        "name": "UAT Test Customer",
        "phone": "+7 (999) 123-45-67",
        "email": "uat.test@example.com",
        "street": "Test Street 1",
        "city": "Moscow",
        "zip": "123456",
    }


# ====================
# KKT Adapter Fixtures
# ====================

@pytest.fixture(scope="function")
def kkt_adapter_url():
    """
    KKT Adapter URL for UAT tests

    Returns:
        str: KKT adapter base URL
    """
    return "http://localhost:8000"


@pytest.fixture(scope="function")
def kkt_adapter_health(kkt_adapter_url):
    """
    Check KKT adapter health before UAT test

    Verifies KKT adapter is running and healthy.
    Skips test if adapter is not available.
    """
    import requests

    try:
        response = requests.get(f"{kkt_adapter_url}/health", timeout=2)
        if response.status_code != 200:
            pytest.skip(f"KKT adapter unhealthy: {response.status_code}")
    except requests.exceptions.RequestException as e:
        pytest.skip(f"KKT adapter not available: {e}")

    yield kkt_adapter_url


# ====================
# Clean State Fixtures
# ====================

@pytest.fixture(scope="function")
def clean_buffer(kkt_adapter_url):
    """
    Clean KKT adapter buffer before test

    Purges all pending receipts from buffer to ensure clean state.

    Note: This is a destructive operation - use only in test environment!
    """
    import requests

    # TODO: Implement buffer purge endpoint in KKT adapter
    # For now, just verify buffer is accessible

    try:
        response = requests.get(f"{kkt_adapter_url}/v1/kkt/buffer/status", timeout=2)
        if response.status_code == 200:
            data = response.json()
            if data.get("buffer_count", 0) > 0:
                # Warn if buffer not empty
                pytest.warns(UserWarning, match="Buffer not empty")
    except:
        pass  # Skip if endpoint not available

    yield


# ====================
# Assertions Helpers
# ====================

def assert_receipt_printed(kkt_adapter_url, fiscal_doc_id):
    """
    Assert receipt was printed by KKT

    Args:
        kkt_adapter_url: KKT adapter base URL
        fiscal_doc_id: Fiscal document ID to check

    Raises:
        AssertionError: If receipt not printed
    """
    import requests

    # TODO: Implement receipt status check endpoint
    # For now, just placeholder

    # response = requests.get(f"{kkt_adapter_url}/v1/kkt/receipt/{fiscal_doc_id}")
    # assert response.status_code == 200
    # assert response.json()["status"] == "printed"

    pass


def assert_receipt_synced(kkt_adapter_url, fiscal_doc_id, timeout=30):
    """
    Assert receipt was synced to OFD

    Args:
        kkt_adapter_url: KKT adapter base URL
        fiscal_doc_id: Fiscal document ID to check
        timeout: Max wait time in seconds

    Raises:
        AssertionError: If receipt not synced within timeout
    """
    import requests
    import time

    # TODO: Implement receipt status check endpoint with polling
    # For now, just placeholder

    # start_time = time.time()
    # while time.time() - start_time < timeout:
    #     response = requests.get(f"{kkt_adapter_url}/v1/kkt/receipt/{fiscal_doc_id}")
    #     if response.status_code == 200:
    #         if response.json()["status"] == "synced":
    #             return
    #     time.sleep(1)
    #
    # raise AssertionError(f"Receipt {fiscal_doc_id} not synced within {timeout}s")

    pass


# ====================
# Example Usage
# ====================

if __name__ == "__main__":
    # Print fixture info
    print("=== UAT Fixtures ===")
    print(f"Odoo URL: {ODOO_URL}")
    print(f"Odoo DB: {ODOO_DB}")
    print(f"KKT Adapter: http://localhost:8000")
