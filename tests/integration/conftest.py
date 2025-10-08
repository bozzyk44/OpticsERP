"""
Pytest Fixtures for Integration Tests

Author: AI Agent
Created: 2025-10-09
Task: OPTERP-11
"""

import pytest
import pytest_asyncio
import sys
import os
from pathlib import Path
import asyncio
from httpx import AsyncClient, ASGITransport

# Add kkt_adapter to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "kkt_adapter" / "app"))

from main import app
from buffer import init_buffer_db, close_buffer_db, get_db
from circuit_breaker import reset_circuit_breaker
from kkt_driver import reset_counter


# ====================
# Fixtures
# ====================

@pytest.fixture(scope="function")
def reset_database():
    """
    Reset SQLite database before each test

    Uses DELETE + VACUUM approach:
    - DELETE removes all data from tables
    - VACUUM rebuilds database, reclaiming space and resetting AUTOINCREMENT
    - Avoids Windows file lock issues (vs DROP TABLE or file deletion)
    """
    # Close existing connection if any
    try:
        close_buffer_db()
    except:
        pass

    # Re-initialize database (creates tables if not exist)
    init_buffer_db()

    # Get connection and clear all tables
    conn = get_db()

    # Delete all data (tables become empty)
    conn.execute("DELETE FROM receipts")
    conn.execute("DELETE FROM dlq")
    conn.execute("DELETE FROM buffer_events")
    conn.commit()

    # VACUUM rebuilds database:
    # - Resets AUTOINCREMENT counters (tables are empty)
    # - Reclaims disk space (removes fragmentation)
    # - Optimizes page layout and indexes
    # Note: VACUUM requires isolation_level=None (autocommit)
    conn.isolation_level = None  # Enable autocommit for VACUUM
    conn.execute("VACUUM")
    conn.isolation_level = ""    # Restore default

    yield

    # Cleanup
    try:
        close_buffer_db()
    except:
        pass


@pytest.fixture(scope="function")
def reset_cb():
    """Reset Circuit Breaker before each test"""
    reset_circuit_breaker()
    yield
    reset_circuit_breaker()


@pytest.fixture(scope="function")
def reset_kkt():
    """Reset KKT fiscal counter before each test"""
    reset_counter()
    yield
    reset_counter()


@pytest_asyncio.fixture
async def client(reset_database, reset_cb, reset_kkt):
    """
    Async HTTP client for FastAPI app

    Uses httpx.AsyncClient with ASGITransport for testing FastAPI app.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture(scope="function")
def sample_receipt_data():
    """Sample receipt data for testing"""
    return {
        "pos_id": "POS-001",
        "type": "sale",
        "items": [
            {
                "name": "Test Product",
                "price": 100.00,
                "quantity": 2,
                "total": 200.00,
                "vat_rate": 20
            }
        ],
        "payments": [
            {
                "type": "cash",
                "amount": 200.00
            }
        ]
    }


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()
