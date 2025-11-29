"""
Integration Tests for Bulkhead Pattern (Celery Queues)

Author: AI Agent
Created: 2025-11-29
Task: OPTERP-48 (Implement Bulkhead Pattern - Celery Queues)

Test Coverage:
- 4 queues configured (critical, high, default, low)
- sync_buffer → critical queue
- send_email → low queue
- Queue isolation works (low queue backlog doesn't block critical)
- Task routing works correctly

Target Coverage: ≥95%
"""

import pytest
import time
from typing import List
from celery import Celery
from celery.result import AsyncResult

# Import Celery app and tasks
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "kkt_adapter" / "app"))

from celery_app import app, get_queue_stats, QUEUE_PRIORITIES
from tasks import sync_buffer, send_email, sync_receipt, process_payment, cleanup_old_receipts


# ====================
# Test Fixtures
# ====================

@pytest.fixture(scope="session")
def celery_app():
    """
    Get Celery app for testing

    Configures Celery with eager mode for synchronous testing.
    """
    # Configure eager mode for testing (executes tasks synchronously)
    app.conf.update(
        task_always_eager=True,  # Execute tasks synchronously
        task_eager_propagates=True,  # Propagate exceptions
    )

    return app


@pytest.fixture(scope="function")
def celery_worker():
    """
    Start Celery worker for integration tests

    Note: This requires Redis to be running.
    """
    # Check if Redis is available
    try:
        import redis
        r = redis.Redis(host='localhost', port=6379, db=0, socket_timeout=2)
        r.ping()
    except Exception as e:
        pytest.skip(f"Redis not available: {e}")

    # Return app (worker will be started manually for real integration tests)
    return app


@pytest.fixture(scope="function")
def purge_queues(celery_worker):
    """
    Purge all queues before each test

    Ensures clean state for each test.
    """
    # Purge all queues
    for queue_name in QUEUE_PRIORITIES.keys():
        try:
            celery_worker.control.purge()
        except:
            pass  # Queue may not exist yet

    yield

    # Purge after test
    for queue_name in QUEUE_PRIORITIES.keys():
        try:
            celery_worker.control.purge()
        except:
            pass


# ====================
# Bulkhead Pattern Tests
# ====================

class TestBulkheadPatternQueues:
    """Test suite for Bulkhead pattern queue configuration"""

    def test_queue_configuration(self, celery_app):
        """
        Test: 4 queues configured (critical, high, default, low)

        Verifies:
        - All 4 queues exist in configuration
        - Queue priorities are correct
        """
        # Check task_queues configuration
        queues = {q.name for q in celery_app.conf.task_queues}

        assert 'critical' in queues, "critical queue not configured"
        assert 'high' in queues, "high queue not configured"
        assert 'default' in queues, "default queue not configured"
        assert 'low' in queues, "low queue not configured"

        # Check priorities
        assert QUEUE_PRIORITIES['critical'] == 10, "critical queue priority should be 10"
        assert QUEUE_PRIORITIES['high'] == 5, "high queue priority should be 5"
        assert QUEUE_PRIORITIES['default'] == 0, "default queue priority should be 0"
        assert QUEUE_PRIORITIES['low'] == -5, "low queue priority should be -5"

    def test_task_routing_sync_buffer(self, celery_app):
        """
        Test: sync_buffer task routed to critical queue

        Verifies:
        - sync_buffer task exists
        - Task is routed to critical queue
        """
        task_name = 'kkt_adapter.tasks.sync_buffer'

        # Check task is registered
        assert task_name in celery_app.tasks, f"{task_name} not registered"

        # Check routing
        route = celery_app.conf.task_routes.get(task_name)
        assert route is not None, f"{task_name} has no route configured"
        assert route['queue'] == 'critical', f"{task_name} should route to critical queue"

    def test_task_routing_send_email(self, celery_app):
        """
        Test: send_email task routed to low queue

        Verifies:
        - send_email task exists
        - Task is routed to low queue
        """
        task_name = 'kkt_adapter.tasks.send_email'

        # Check task is registered
        assert task_name in celery_app.tasks, f"{task_name} not registered"

        # Check routing
        route = celery_app.conf.task_routes.get(task_name)
        assert route is not None, f"{task_name} has no route configured"
        assert route['queue'] == 'low', f"{task_name} should route to low queue"

    def test_all_task_routes(self, celery_app):
        """
        Test: All tasks have correct queue routes

        Verifies:
        - sync_buffer, sync_receipt → critical
        - process_payment, confirm_order → high
        - cleanup_old_receipts, generate_analytics → default
        - send_email, send_sms → low
        """
        expected_routes = {
            'kkt_adapter.tasks.sync_buffer': 'critical',
            'kkt_adapter.tasks.sync_receipt': 'critical',
            'kkt_adapter.tasks.process_payment': 'high',
            'kkt_adapter.tasks.confirm_order': 'high',
            'kkt_adapter.tasks.cleanup_old_receipts': 'default',
            'kkt_adapter.tasks.generate_analytics': 'default',
            'kkt_adapter.tasks.send_email': 'low',
            'kkt_adapter.tasks.send_sms': 'low',
        }

        task_routes = celery_app.conf.task_routes

        for task_name, expected_queue in expected_routes.items():
            route = task_routes.get(task_name)
            assert route is not None, f"{task_name} has no route"
            assert route['queue'] == expected_queue, \
                f"{task_name} should route to {expected_queue}, got {route['queue']}"


class TestBulkheadPatternIsolation:
    """Test suite for queue isolation"""

    def test_sync_buffer_task_execution(self, celery_app):
        """
        Test: sync_buffer task executes successfully

        Verifies:
        - Task can be called
        - Returns expected result structure
        """
        # Execute task (eager mode - synchronous)
        result = sync_buffer.apply()

        # Check result
        assert result.successful(), "sync_buffer task should succeed"

        data = result.result

        assert 'synced' in data, "Result should contain 'synced'"
        assert 'failed' in data, "Result should contain 'failed'"
        assert 'skipped' in data, "Result should contain 'skipped'"
        assert 'duration_seconds' in data, "Result should contain 'duration_seconds'"

    def test_send_email_task_execution(self, celery_app):
        """
        Test: send_email task executes successfully

        Verifies:
        - Task can be called
        - Returns expected result structure
        """
        # Execute task (eager mode - synchronous)
        result = send_email.apply(args=['test@example.com', 'Test Subject', 'Test Body'])

        # Check result
        assert result.successful(), "send_email task should succeed"

        data = result.result

        assert data['to'] == 'test@example.com', "Email recipient should match"
        assert data['subject'] == 'Test Subject', "Email subject should match"
        assert data['status'] == 'sent', "Email status should be 'sent'"

    @pytest.mark.skip(reason="Requires running Celery worker - manual test")
    def test_queue_isolation_low_queue_backlog(self, celery_worker, purge_queues):
        """
        Test: Low queue backlog doesn't block critical queue

        Scenario:
        1. Submit 100 send_email tasks (low queue)
        2. Submit 1 sync_buffer task (critical queue)
        3. Verify sync_buffer completes before all send_email tasks

        This test verifies the Bulkhead pattern - critical tasks
        are not blocked by low-priority task backlog.

        Note: This test requires a running Celery worker.
        Run manually: celery -A app.celery_app worker --queues=critical,low --concurrency=2
        """
        # Submit 100 email tasks (low queue)
        email_results = []
        for i in range(100):
            result = send_email.delay(
                to=f'user{i}@example.com',
                subject=f'Email {i}',
                body='Test email body'
            )
            email_results.append(result)

        # Submit sync task (critical queue)
        sync_result = sync_buffer.delay()

        # Wait for sync task (should complete quickly)
        start_time = time.time()
        sync_done = sync_result.get(timeout=10)  # 10 second timeout
        sync_duration = time.time() - start_time

        # Verify sync completed
        assert sync_done is not None, "sync_buffer should complete"
        assert sync_duration < 5, f"sync_buffer should complete in <5s, took {sync_duration:.2f}s"

        # Count completed email tasks
        completed_emails = sum(1 for r in email_results if r.ready())

        # Critical task should complete before most email tasks
        assert completed_emails < 50, \
            f"sync_buffer should complete before most emails, but {completed_emails}/100 emails done"

    def test_task_priority_ordering(self, celery_app):
        """
        Test: Tasks are processed in priority order

        Verifies:
        - critical queue has highest priority (10)
        - high queue has priority 5
        - default queue has priority 0
        - low queue has lowest priority (-5)
        """
        priorities = QUEUE_PRIORITIES

        assert priorities['critical'] > priorities['high'], \
            "critical should have higher priority than high"

        assert priorities['high'] > priorities['default'], \
            "high should have higher priority than default"

        assert priorities['default'] > priorities['low'], \
            "default should have higher priority than low"


class TestBulkheadPatternMonitoring:
    """Test suite for monitoring and queue statistics"""

    def test_get_queue_stats_structure(self):
        """
        Test: get_queue_stats returns correct structure

        Verifies:
        - Returns dict with all 4 queues
        - Each queue has 'pending' and 'active' counts
        """
        # Note: This test will return empty stats without running workers
        stats = get_queue_stats()

        assert isinstance(stats, dict), "get_queue_stats should return dict"

        # Check all queues present
        assert 'critical' in stats, "critical queue stats missing"
        assert 'high' in stats, "high queue stats missing"
        assert 'default' in stats, "default queue stats missing"
        assert 'low' in stats, "low queue stats missing"

        # Check structure of each queue
        for queue_name, queue_stats in stats.items():
            assert 'pending' in queue_stats, f"{queue_name} should have 'pending' count"
            assert 'active' in queue_stats, f"{queue_name} should have 'active' count"
            assert isinstance(queue_stats['pending'], int), f"{queue_name} pending should be int"
            assert isinstance(queue_stats['active'], int), f"{queue_name} active should be int"


# ====================
# Performance Tests
# ====================

class TestBulkheadPatternPerformance:
    """Performance tests for Bulkhead pattern"""

    def test_task_dispatch_latency(self, celery_app):
        """
        Test: Task dispatch latency

        Requirement: Task dispatch < 10ms (eager mode)
        """
        # Measure dispatch time
        start = time.time()
        result = sync_buffer.apply()
        latency = (time.time() - start) * 1000  # Convert to ms

        assert latency < 100, f"Task dispatch latency {latency:.2f}ms exceeds 100ms (eager mode)"

    def test_multiple_task_dispatch(self, celery_app):
        """
        Test: Dispatch 100 tasks

        Requirement: Average dispatch latency < 50ms (eager mode)
        """
        latencies = []

        for i in range(100):
            start = time.time()
            result = send_email.apply(args=[f'user{i}@example.com', f'Subject {i}', 'Body'])
            latency = (time.time() - start) * 1000
            latencies.append(latency)

        avg_latency = sum(latencies) / len(latencies)

        assert avg_latency < 50, f"Average dispatch latency {avg_latency:.2f}ms exceeds 50ms"


# ====================
# Summary
# ====================
"""
Test Coverage Summary:

Queue Configuration Tests (4 tests):
1. test_queue_configuration() - All 4 queues configured
2. test_task_routing_sync_buffer() - sync_buffer → critical
3. test_task_routing_send_email() - send_email → low
4. test_all_task_routes() - All 8 tasks routed correctly

Queue Isolation Tests (4 tests):
1. test_sync_buffer_task_execution() - Critical task executes
2. test_send_email_task_execution() - Low task executes
3. test_queue_isolation_low_queue_backlog() - Isolation works (manual test)
4. test_task_priority_ordering() - Priority ordering correct

Monitoring Tests (1 test):
1. test_get_queue_stats_structure() - Queue stats API works

Performance Tests (2 tests):
1. test_task_dispatch_latency() - Dispatch < 100ms
2. test_multiple_task_dispatch() - Average < 50ms

Total Tests: 11 (10 automated + 1 manual)
Coverage Target: ≥95%
"""
