"""
Global pytest fixtures for OpticsERP tests

Provides shared fixtures for:
- FastAPI server (automatic startup)
- Mock OFD Server (reusable)
- Mock Odoo Server (reusable)
- Redis connection
- Buffer cleanup
"""

import pytest
import requests
import time
import subprocess
import sys
from pathlib import Path

# Add paths
sys.path.insert(0, str(Path(__file__).parent / 'integration'))
sys.path.insert(0, str(Path(__file__).parent.parent / 'kkt_adapter' / 'app'))

from mock_ofd_server import MockOFDServer
from mock_odoo_server import MockOdooServer
from buffer import init_buffer_db, get_db, close_buffer_db


# ====================
# Configuration
# ====================

FASTAPI_BASE_URL = "http://localhost:8000"
MOCK_OFD_PORT = 8080
MOCK_ODOO_PORT = 8069


# ====================
# FastAPI Server Fixtures
# ====================

@pytest.fixture(scope="session")
def fastapi_server_auto():
    """
    Automatically start FastAPI server for session

    Starts server in background process.
    Stops server at end of session.

    Marks: fastapi
    """
    # Check if already running
    try:
        response = requests.get(f"{FASTAPI_BASE_URL}/v1/health", timeout=2)
        if response.status_code == 200:
            print("✅ FastAPI server already running")
            yield FASTAPI_BASE_URL
            return
    except:
        pass

    # Start server in background
    print("🚀 Starting FastAPI server...")

    process = subprocess.Popen(
        [sys.executable, "main.py"],
        cwd=Path(__file__).parent.parent / "kkt_adapter" / "app",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

    # Wait for server to be ready (max 10s)
    start_time = time.time()
    while time.time() - start_time < 10:
        try:
            response = requests.get(f"{FASTAPI_BASE_URL}/v1/health", timeout=1)
            if response.status_code == 200:
                print("✅ FastAPI server started")
                break
        except:
            time.sleep(0.5)
    else:
        process.kill()
        pytest.fail("FastAPI server failed to start within 10s")

    yield FASTAPI_BASE_URL

    # Stop server
    print("🛑 Stopping FastAPI server...")
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait()


@pytest.fixture(scope="function")
def fastapi_server():
    """
    Check FastAPI server is running (manual start)

    Use this for quick local testing where you
    start server manually.

    Marks: fastapi
    """
    try:
        response = requests.get(f"{FASTAPI_BASE_URL}/v1/health", timeout=2)
        if response.status_code != 200:
            pytest.skip("FastAPI server not responding")
    except:
        pytest.skip("FastAPI server not running. Start with: cd kkt_adapter/app && python main.py")

    yield FASTAPI_BASE_URL


# ====================
# Mock Server Fixtures
# ====================

@pytest.fixture(scope="session")
def mock_ofd_server_session():
    """
    Session-scoped Mock OFD Server

    Shared across all tests in session.
    Reset state between tests with mock_ofd_server fixture.
    """
    server = MockOFDServer(port=MOCK_OFD_PORT)
    server.start()
    time.sleep(1)

    yield server

    server.stop()


@pytest.fixture
def mock_ofd_server(mock_ofd_server_session):
    """
    Function-scoped Mock OFD Server (reset state)

    Resets server state before each test.
    """
    server = mock_ofd_server_session
    server.reset()
    server.set_success()  # Default: success mode

    yield server

    # Cleanup after test
    server.reset()


@pytest.fixture(scope="session")
def mock_odoo_server_session():
    """
    Session-scoped Mock Odoo Server

    Shared across all tests in session.
    """
    server = MockOdooServer(port=MOCK_ODOO_PORT)
    server.start()
    time.sleep(1)

    yield server

    server.stop()


@pytest.fixture
def mock_odoo_server(mock_odoo_server_session):
    """
    Function-scoped Mock Odoo Server (reset state)
    """
    server = mock_odoo_server_session
    server.reset()
    server.set_success()

    yield server

    server.reset()


# ====================
# Buffer Cleanup Fixture
# ====================

@pytest.fixture
def clean_buffer():
    """
    Clean buffer before test

    Deletes all receipts, DLQ, and events.
    """
    init_buffer_db()

    conn = get_db()
    conn.execute("DELETE FROM receipts")
    conn.execute("DELETE FROM dlq")
    conn.execute("DELETE FROM buffer_events")
    conn.commit()

    yield

    # Optional: cleanup after test
    # (usually not needed, next test will clean)


@pytest.fixture
def clean_kkt_log():
    """
    Clean KKT print log before test
    """
    kkt_log_path = Path(__file__).parent.parent / "kkt_adapter" / "data" / "kkt_print.log"

    if kkt_log_path.exists():
        kkt_log_path.unlink()

    yield

    # Optional: cleanup after test


# ====================
# Redis Fixture
# ====================

@pytest.fixture
def redis_available():
    """
    Check Redis is available

    Marks: redis
    """
    import redis
    try:
        client = redis.Redis(host='localhost', port=6379, db=0)
        client.ping()
        yield client
    except:
        pytest.skip("Redis not running. Start with: docker-compose up -d redis")


# ====================
# Pytest Hooks
# ====================

def pytest_configure(config):
    """
    Configure pytest session
    """
    config.addinivalue_line("markers", "unit: Unit tests")
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "poc: POC tests")
    config.addinivalue_line("markers", "slow: Slow tests")
    config.addinivalue_line("markers", "redis: Tests requiring Redis")
    config.addinivalue_line("markers", "fastapi: Tests requiring FastAPI")
