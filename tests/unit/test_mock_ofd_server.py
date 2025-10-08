"""
Unit Tests for Mock OFD Server

Author: AI Agent
Created: 2025-10-09
Task: OPTERP-13

Test Coverage:
- Mock OFD Server startup/shutdown
- Configurable failure modes
- Receipt tracking
- HTTP API endpoints
"""

import pytest
import requests
import time
import sys
from pathlib import Path

# Add tests/integration to path
sys.path.insert(0, str(Path(__file__).parent.parent / "integration"))

from mock_ofd_server import MockOFDServer


class TestMockOFDServerBasic:
    """Basic tests for Mock OFD Server"""

    def test_server_startup_shutdown(self):
        """Test server starts and stops cleanly"""
        server = MockOFDServer(port=9001)
        server.start()

        # Check server is running via health endpoint
        response = requests.get("http://localhost:9001/ofd/v1/health", timeout=5)
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"

        server.stop()

    def test_server_context_manager(self):
        """Test server works with context manager"""
        with MockOFDServer(port=9002) as server:
            response = requests.get("http://localhost:9002/ofd/v1/health", timeout=5)
            assert response.status_code == 200

    def test_receipt_success_mode(self):
        """Test receipt acceptance in success mode"""
        with MockOFDServer(port=9003) as server:
            server.set_success()

            # Send receipt
            receipt_data = {"pos_id": "POS-001", "fiscal_doc": {"doc_number": 1}}
            response = requests.post(
                "http://localhost:9003/ofd/v1/receipt",
                json=receipt_data,
                timeout=5
            )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "accepted"
            assert "ofd_id" in data

            # Verify receipt tracked
            received = server.get_received_receipts()
            assert len(received) == 1
            assert received[0]["pos_id"] == "POS-001"

    def test_receipt_permanent_failure(self):
        """Test receipt rejection in permanent failure mode"""
        with MockOFDServer(port=9004) as server:
            server.set_permanent_failure(True)

            receipt_data = {"pos_id": "POS-001", "fiscal_doc": {"doc_number": 1}}
            response = requests.post(
                "http://localhost:9004/ofd/v1/receipt",
                json=receipt_data,
                timeout=5
            )

            assert response.status_code == 503
            assert "error" in response.json()

            # Verify receipt not tracked
            received = server.get_received_receipts()
            assert len(received) == 0

    def test_receipt_temporary_failure(self):
        """Test temporary failure mode (fail N times, then succeed)"""
        with MockOFDServer(port=9005) as server:
            server.set_failure_count(2)  # Fail 2 times

            receipt_data = {"pos_id": "POS-001", "fiscal_doc": {"doc_number": 1}}

            # First attempt: fail
            response1 = requests.post("http://localhost:9005/ofd/v1/receipt", json=receipt_data, timeout=5)
            assert response1.status_code == 503

            # Second attempt: fail
            response2 = requests.post("http://localhost:9005/ofd/v1/receipt", json=receipt_data, timeout=5)
            assert response2.status_code == 503

            # Third attempt: succeed
            response3 = requests.post("http://localhost:9005/ofd/v1/receipt", json=receipt_data, timeout=5)
            assert response3.status_code == 200

            # Verify only successful receipt tracked
            received = server.get_received_receipts()
            assert len(received) == 1

    def test_call_count_tracking(self):
        """Test call count tracking"""
        with MockOFDServer(port=9006) as server:
            server.set_success()

            receipt_data = {"pos_id": "POS-001", "fiscal_doc": {"doc_number": 1}}

            # Make 3 requests
            for i in range(3):
                requests.post("http://localhost:9006/ofd/v1/receipt", json=receipt_data, timeout=5)

            # Check call count
            assert server.get_call_count() == 3

            # Check via health endpoint
            health = requests.get("http://localhost:9006/ofd/v1/health", timeout=5).json()
            assert health["call_count"] == 3

    def test_reset_functionality(self):
        """Test reset clears state"""
        with MockOFDServer(port=9007) as server:
            server.set_success()

            receipt_data = {"pos_id": "POS-001", "fiscal_doc": {"doc_number": 1}}

            # Send receipt
            requests.post("http://localhost:9007/ofd/v1/receipt", json=receipt_data, timeout=5)
            assert server.get_call_count() == 1
            assert len(server.get_received_receipts()) == 1

            # Reset
            server.reset()

            # Verify state cleared
            assert server.get_call_count() == 0
            assert len(server.get_received_receipts()) == 0

    def test_multiple_receipts_tracking(self):
        """Test tracking multiple receipts"""
        with MockOFDServer(port=9008) as server:
            server.set_success()

            # Send 5 receipts
            for i in range(5):
                receipt_data = {"pos_id": f"POS-{i:03d}", "fiscal_doc": {"doc_number": i+1}}
                response = requests.post(
                    "http://localhost:9008/ofd/v1/receipt",
                    json=receipt_data,
                    timeout=5
                )
                assert response.status_code == 200

            # Verify all tracked
            received = server.get_received_receipts()
            assert len(received) == 5

            # Verify order preserved
            for i, receipt in enumerate(received):
                assert receipt["pos_id"] == f"POS-{i:03d}"
                assert receipt["fiscal_doc"]["doc_number"] == i + 1
