#!/usr/bin/env python
"""
Test script for FastAPI KKT Adapter endpoints

This script initializes the buffer database with the correct schema
and tests all API endpoints.
"""

import sys
import time
import json
import subprocess
from pathlib import Path

# Add kkt_adapter/app to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'kkt_adapter' / 'app'))

def init_database():
    """Initialize buffer database with schema"""
    from buffer import init_buffer_db, close_buffer_db

    print("Initializing buffer database...")
    conn = init_buffer_db()
    close_buffer_db()
    print("✅ Buffer database initialized")

def test_endpoints():
    """Test all FastAPI endpoints"""
    import requests

    base_url = "http://localhost:8001"

    print("\n=== Testing Root Endpoint ===")
    try:
        response = requests.get(f"{base_url}/")
        print(json.dumps(response.json(), indent=2))
        assert response.status_code == 200
        print("✅ Root endpoint OK")
    except Exception as e:
        print(f"❌ Root endpoint failed: {e}")

    print("\n=== Testing Health Check ===")
    try:
        response = requests.get(f"{base_url}/v1/health")
        print(json.dumps(response.json(), indent=2))
        assert response.status_code == 200
        print("✅ Health check OK")
    except Exception as e:
        print(f"❌ Health check failed: {e}")

    print("\n=== Testing Buffer Status ===")
    try:
        response = requests.get(f"{base_url}/v1/kkt/buffer/status")
        print(json.dumps(response.json(), indent=2))
        assert response.status_code == 200
        print("✅ Buffer status OK")
    except Exception as e:
        print(f"❌ Buffer status failed: {e}")

    print("\n=== Testing Receipt Creation ===")
    try:
        receipt_data = {
            "pos_id": "POS-001",
            "type": "sale",
            "items": [
                {
                    "name": "Product A",
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

        import uuid
        headers = {"Idempotency-Key": str(uuid.uuid4())}

        response = requests.post(
            f"{base_url}/v1/kkt/receipt",
            json=receipt_data,
            headers=headers
        )
        print(json.dumps(response.json(), indent=2))
        assert response.status_code == 200
        print("✅ Receipt creation OK")
    except Exception as e:
        print(f"❌ Receipt creation failed: {e}")

if __name__ == "__main__":
    init_database()
    print("\nWaiting for FastAPI server to be ready...")
    time.sleep(5)  # Give server time to start
    test_endpoints()
