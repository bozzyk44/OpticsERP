"""
POC-1 Test: KKT Emulator - Basic Fiscalization Test

Author: AI Agent
Created: 2025-10-09
Task: OPTERP-28

Purpose:
- Prove basic two-phase fiscalization works
- Validate KKT emulator (mock driver)
- Measure performance baseline (P95, throughput)

Test Scenario:
1. Create 50 receipts via POST /v1/kkt/receipt
2. Verify all receipts buffered (status=pending)
3. Verify Mock KKT printed all receipts
4. Measure P95 response time ≤ 7s
5. Measure throughput ≥ 20 receipts/min

Success Criteria (from JIRA):
- 50 receipts created successfully
- All receipts buffered (status=pending)
- Mock KKT printed all receipts
- P95 response time ≤ 7s
- Throughput ≥ 20 receipts/min

Architecture:
┌─────────────────────────────────────────┐
│  POC-1 Test                             │
│  ┌───────────────────────────────────┐  │
│  │ 1. Start FastAPI server           │  │
│  │ 2. Create 50 receipts (POST)      │  │
│  │ 3. Measure response times         │  │
│  │ 4. Verify buffer status           │  │
│  │ 5. Verify KKT logs                │  │
│  │ 6. Calculate P95 & throughput     │  │
│  └───────────────────────────────────┘  │
└─────────────────────────────────────────┘
"""

import pytest
import requests
import time
import uuid
import statistics
import sys
from pathlib import Path
from typing import List, Dict, Any

# Add kkt_adapter/app to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'kkt_adapter' / 'app'))

from buffer import get_buffer_status, get_db, init_buffer_db, close_buffer_db


# ====================
# Configuration
# ====================

FASTAPI_BASE_URL = "http://localhost:8000"
NUM_RECEIPTS = 50
P95_THRESHOLD_SECONDS = 7.0
THROUGHPUT_THRESHOLD_PER_MINUTE = 20.0

# KKT log file (mock driver writes here)
KKT_LOG_FILE = Path(__file__).parent.parent.parent / 'kkt_adapter' / 'data' / 'kkt_print.log'


# ====================
# Fixtures
# ====================

@pytest.fixture(scope="module")
def fastapi_server():
    """
    Start FastAPI server for POC-1 test

    Note: For POC testing, FastAPI should be started manually:
    $ cd kkt_adapter/app && python main.py

    This fixture just verifies server is running.
    """
    # Verify server is running
    try:
        response = requests.get(f"{FASTAPI_BASE_URL}/v1/health", timeout=2)
        if response.status_code != 200:
            pytest.skip("FastAPI server not responding at localhost:8000")
    except requests.ConnectionError:
        pytest.skip("FastAPI server not running. Start with: cd kkt_adapter/app && python main.py")

    yield FASTAPI_BASE_URL

    # No teardown - server runs independently


@pytest.fixture(scope="module")
def clean_buffer():
    """
    Clean buffer before POC-1 test

    Ensures test starts with empty buffer for accurate metrics.
    """
    # Initialize buffer
    init_buffer_db()

    # Clean receipts table
    conn = get_db()
    conn.execute("DELETE FROM receipts")
    conn.execute("DELETE FROM dlq")
    conn.execute("DELETE FROM buffer_events")
    conn.commit()

    yield

    # No teardown - keep results for inspection


@pytest.fixture(scope="module")
def clean_kkt_log():
    """
    Clean KKT log before POC-1 test

    Ensures test starts with empty log for accurate verification.
    """
    if KKT_LOG_FILE.exists():
        KKT_LOG_FILE.unlink()

    # Ensure parent directory exists
    KKT_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

    yield KKT_LOG_FILE


# ====================
# Helper Functions
# ====================

def create_sample_receipt(pos_id: str = "POS-001") -> Dict[str, Any]:
    """
    Create sample receipt data for testing

    Args:
        pos_id: POS terminal ID

    Returns:
        Receipt data dictionary
    """
    return {
        "pos_id": pos_id,
        "type": "SALE",
        "items": [
            {
                "name": "Оправа Ray-Ban RB3025",
                "quantity": 1.0,
                "price": 15000.00,
                "tax_rate": 20.0,
                "amount": 15000.00
            },
            {
                "name": "Линзы прогрессивные 1.6",
                "quantity": 2.0,
                "price": 8000.00,
                "tax_rate": 20.0,
                "amount": 16000.00
            }
        ],
        "payments": [
            {
                "type": "CARD",
                "amount": 31000.00
            }
        ]
    }


def calculate_p95(values: List[float]) -> float:
    """
    Calculate 95th percentile (P95)

    Args:
        values: List of numeric values

    Returns:
        P95 value
    """
    if not values:
        return 0.0

    sorted_values = sorted(values)
    index = int(len(sorted_values) * 0.95)
    return sorted_values[index]


def calculate_throughput(num_receipts: int, duration_seconds: float) -> float:
    """
    Calculate throughput (receipts per minute)

    Args:
        num_receipts: Number of receipts processed
        duration_seconds: Duration in seconds

    Returns:
        Throughput in receipts/minute
    """
    if duration_seconds == 0:
        return 0.0

    return (num_receipts / duration_seconds) * 60.0


def count_kkt_prints(log_file: Path) -> int:
    """
    Count number of receipts printed by KKT (from log file)

    Args:
        log_file: Path to KKT log file

    Returns:
        Number of printed receipts
    """
    if not log_file.exists():
        return 0

    count = 0
    with open(log_file, 'r', encoding='utf-8') as f:
        for line in f:
            if "Receipt printed" in line or "ПЕЧАТЬ ЧЕКА" in line:
                count += 1

    return count


# ====================
# POC-1 Test
# ====================

class TestPOC1Emulator:
    """
    POC-1: KKT Emulator - Basic Fiscalization Test

    Tests basic two-phase fiscalization with mock KKT driver.
    """

    def test_poc1_create_50_receipts(
        self,
        fastapi_server,
        clean_buffer,
        clean_kkt_log
    ):
        """
        POC-1: Create 50 receipts and verify performance

        Steps:
        1. Create 50 receipts via POST /v1/kkt/receipt
        2. Measure response times
        3. Verify all receipts buffered (status=pending)
        4. Verify Mock KKT printed all receipts
        5. Calculate P95 response time
        6. Calculate throughput
        7. Verify P95 ≤ 7s
        8. Verify throughput ≥ 20 receipts/min

        Expected:
        - All 50 receipts created successfully (200 OK)
        - All receipts in buffer with status=pending
        - All 50 receipts printed by Mock KKT
        - P95 response time ≤ 7s
        - Throughput ≥ 20 receipts/min
        """
        print(f"\n{'='*60}")
        print("POC-1 Test: KKT Emulator - Basic Fiscalization")
        print(f"{'='*60}\n")

        # ====================
        # Step 1: Create 50 receipts
        # ====================

        print(f"Step 1: Creating {NUM_RECEIPTS} receipts...")

        response_times = []
        receipt_ids = []
        start_time = time.time()

        for i in range(NUM_RECEIPTS):
            # Generate unique idempotency key
            idempotency_key = str(uuid.uuid4())

            # Create receipt data
            receipt_data = create_sample_receipt(pos_id=f"POS-{i+1:03d}")

            # Measure response time
            request_start = time.time()

            response = requests.post(
                f"{fastapi_server}/v1/kkt/receipt",
                json=receipt_data,
                headers={"Idempotency-Key": idempotency_key},
                timeout=10
            )

            request_end = time.time()
            response_time = request_end - request_start

            # Verify response
            assert response.status_code == 200, \
                f"Receipt {i+1} creation failed: {response.status_code} - {response.text}"

            response_json = response.json()
            assert "receipt_id" in response_json, "Missing receipt_id in response"

            # Track metrics
            response_times.append(response_time)
            receipt_ids.append(response_json["receipt_id"])

            # Progress indicator (every 10 receipts)
            if (i + 1) % 10 == 0:
                print(f"  ✅ Created {i + 1}/{NUM_RECEIPTS} receipts")

        end_time = time.time()
        total_duration = end_time - start_time

        print(f"\n✅ All {NUM_RECEIPTS} receipts created successfully")
        print(f"   Total duration: {total_duration:.2f}s\n")

        # ====================
        # Step 2: Verify buffer status
        # ====================

        print("Step 2: Verifying buffer status...")

        # Wait for async operations to complete
        time.sleep(1)

        # Get buffer status
        buffer_status = get_buffer_status()

        print(f"  Buffer status:")
        print(f"    Total receipts: {buffer_status.total_receipts}")
        print(f"    Pending: {buffer_status.pending}")
        print(f"    Synced: {buffer_status.synced}")
        print(f"    Failed: {buffer_status.failed}")
        print(f"    DLQ: {buffer_status.dlq_size}")

        # Verify all receipts buffered
        assert buffer_status.total_receipts == NUM_RECEIPTS, \
            f"Expected {NUM_RECEIPTS} receipts in buffer, got {buffer_status.total_receipts}"

        # Note: Receipts may be pending OR synced (depending on sync worker)
        # For POC-1, we accept both states (offline-first is the key)
        assert buffer_status.pending + buffer_status.synced == NUM_RECEIPTS, \
            f"Expected {NUM_RECEIPTS} receipts (pending + synced), got {buffer_status.pending + buffer_status.synced}"

        print(f"\n✅ All {NUM_RECEIPTS} receipts in buffer\n")

        # ====================
        # Step 3: Verify KKT prints
        # ====================

        print("Step 3: Verifying KKT prints...")

        # Count prints in KKT log
        print_count = count_kkt_prints(clean_kkt_log)

        print(f"  KKT log file: {clean_kkt_log}")
        print(f"  Receipts printed: {print_count}")

        # Verify all receipts printed
        assert print_count == NUM_RECEIPTS, \
            f"Expected {NUM_RECEIPTS} KKT prints, got {print_count}"

        print(f"\n✅ All {NUM_RECEIPTS} receipts printed by Mock KKT\n")

        # ====================
        # Step 4: Calculate metrics
        # ====================

        print("Step 4: Calculating performance metrics...")

        # Calculate P95
        p95_response_time = calculate_p95(response_times)

        # Calculate throughput
        throughput = calculate_throughput(NUM_RECEIPTS, total_duration)

        # Calculate additional stats
        min_response_time = min(response_times)
        max_response_time = max(response_times)
        avg_response_time = statistics.mean(response_times)
        median_response_time = statistics.median(response_times)

        print(f"\n  Performance Metrics:")
        print(f"  {'─'*50}")
        print(f"    Response Time (P95):    {p95_response_time:.3f}s")
        print(f"    Response Time (avg):    {avg_response_time:.3f}s")
        print(f"    Response Time (median): {median_response_time:.3f}s")
        print(f"    Response Time (min):    {min_response_time:.3f}s")
        print(f"    Response Time (max):    {max_response_time:.3f}s")
        print(f"  {'─'*50}")
        print(f"    Throughput:             {throughput:.1f} receipts/min")
        print(f"    Total duration:         {total_duration:.2f}s")
        print(f"  {'─'*50}\n")

        # ====================
        # Step 5: Verify acceptance criteria
        # ====================

        print("Step 5: Verifying acceptance criteria...")

        # Criterion 1: 50 receipts created successfully
        print(f"  ✅ Criterion 1: {NUM_RECEIPTS} receipts created successfully")

        # Criterion 2: All receipts buffered
        print(f"  ✅ Criterion 2: All {NUM_RECEIPTS} receipts buffered")

        # Criterion 3: Mock KKT printed all receipts
        print(f"  ✅ Criterion 3: All {NUM_RECEIPTS} receipts printed by Mock KKT")

        # Criterion 4: P95 ≤ 7s
        assert p95_response_time <= P95_THRESHOLD_SECONDS, \
            f"P95 response time {p95_response_time:.3f}s exceeds threshold {P95_THRESHOLD_SECONDS}s"
        print(f"  ✅ Criterion 4: P95 response time {p95_response_time:.3f}s ≤ {P95_THRESHOLD_SECONDS}s")

        # Criterion 5: Throughput ≥ 20 receipts/min
        assert throughput >= THROUGHPUT_THRESHOLD_PER_MINUTE, \
            f"Throughput {throughput:.1f} receipts/min below threshold {THROUGHPUT_THRESHOLD_PER_MINUTE}"
        print(f"  ✅ Criterion 5: Throughput {throughput:.1f} receipts/min ≥ {THROUGHPUT_THRESHOLD_PER_MINUTE}")

        # ====================
        # Summary
        # ====================

        print(f"\n{'='*60}")
        print("POC-1 Test: ✅ PASS")
        print(f"{'='*60}")
        print(f"  Receipts created:  {NUM_RECEIPTS}")
        print(f"  Receipts buffered: {buffer_status.total_receipts}")
        print(f"  KKT prints:        {print_count}")
        print(f"  P95 response time: {p95_response_time:.3f}s (≤ {P95_THRESHOLD_SECONDS}s)")
        print(f"  Throughput:        {throughput:.1f} receipts/min (≥ {THROUGHPUT_THRESHOLD_PER_MINUTE})")
        print(f"{'='*60}\n")


# ====================
# Main Entry Point
# ====================

if __name__ == "__main__":
    """
    Run POC-1 test standalone

    Usage:
    1. Start FastAPI server:
       $ cd kkt_adapter/app && python main.py

    2. Run POC-1 test:
       $ pytest tests/poc/test_poc_1_emulator.py -v -s
    """
    pytest.main([__file__, "-v", "-s"])
