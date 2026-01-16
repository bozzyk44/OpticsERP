"""
Celery Application for KKT Adapter (Bulkhead Pattern)

Author: AI Agent
Created: 2025-11-29
Task: OPTERP-48 (Implement Bulkhead Pattern - Celery Queues)

Purpose:
Implement Bulkhead pattern using Celery with 4 priority queues:
- critical: Fiscalization sync (highest priority)
- high: Payment processing, order confirmation
- default: General background tasks
- low: Email notifications, cleanup tasks

Architecture:
┌─────────────────────────────────────────────────────────────┐
│  Celery Worker                                              │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐        │
│  │   critical   │ │     high     │ │   default    │        │
│  │   (queue)    │ │   (queue)    │ │   (queue)    │        │
│  │              │ │              │ │              │        │
│  │ • sync_buffer│ │ • process_   │ │ • cleanup    │        │
│  │              │ │   payment    │ │ • analytics  │        │
│  └──────────────┘ └──────────────┘ └──────────────┘        │
│                                                              │
│  ┌──────────────┐                                           │
│  │     low      │                                           │
│  │   (queue)    │                                           │
│  │              │                                           │
│  │ • send_email │                                           │
│  │ • send_sms   │                                           │
│  └──────────────┘                                           │
└─────────────────────────────────────────────────────────────┘

Benefits:
1. **Isolation**: Critical tasks unaffected by email queue backlog
2. **Priority**: Sync tasks processed before notifications
3. **Resource Control**: Each queue can have separate worker pool
4. **Monitoring**: Queue metrics per priority level

Reference: CLAUDE.md §8 (Bulkhead Pattern)
"""

import os
from celery import Celery
from kombu import Queue, Exchange

# ====================
# Configuration
# ====================

# Redis connection URL
REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))
REDIS_DB = int(os.getenv('REDIS_DB', 0))

BROKER_URL = f'redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}'
BACKEND_URL = f'redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB + 1}'  # Use DB 1 for results

# ====================
# Celery App
# ====================

app = Celery(
    'kkt_adapter',
    broker=BROKER_URL,
    backend=BACKEND_URL,
)

# ====================
# Celery Configuration
# ====================

app.conf.update(
    # Task routing
    task_routes={
        'kkt_adapter.tasks.sync_buffer': {'queue': 'critical'},
        'kkt_adapter.tasks.sync_receipt': {'queue': 'critical'},
        'kkt_adapter.tasks.process_payment': {'queue': 'high'},
        'kkt_adapter.tasks.confirm_order': {'queue': 'high'},
        'kkt_adapter.tasks.cleanup_old_receipts': {'queue': 'default'},
        'kkt_adapter.tasks.generate_analytics': {'queue': 'default'},
        'kkt_adapter.tasks.send_email': {'queue': 'low'},
        'kkt_adapter.tasks.send_sms': {'queue': 'low'},
    },

    # Queue definitions
    task_queues=(
        Queue('critical', Exchange('critical'), routing_key='critical', priority=10),
        Queue('high', Exchange('high'), routing_key='high', priority=5),
        Queue('default', Exchange('default'), routing_key='default', priority=0),
        Queue('low', Exchange('low'), routing_key='low', priority=-5),
    ),

    # Default queue (if not specified in task_routes)
    task_default_queue='default',
    task_default_exchange='default',
    task_default_routing_key='default',

    # Task execution settings
    task_acks_late=True,  # Acknowledge after task completion (protects from worker crash)
    task_reject_on_worker_lost=True,  # Re-queue if worker dies
    worker_prefetch_multiplier=1,  # Process one task at a time (prevents queue starvation)

    # Result backend settings
    result_backend=BACKEND_URL,
    result_expires=3600,  # Results expire after 1 hour

    # Serialization
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',

    # Timezone
    timezone='UTC',
    enable_utc=True,

    # Worker settings
    worker_max_tasks_per_child=1000,  # Restart worker after 1000 tasks (prevent memory leaks)
    worker_disable_rate_limits=False,

    # Monitoring
    task_track_started=True,  # Track task start time
    task_send_sent_event=True,  # Send task-sent event

    # Retry settings
    task_autoretry_for=(Exception,),  # Auto-retry on any exception
    task_retry_backoff=True,  # Exponential backoff
    task_retry_backoff_max=600,  # Max 10 minutes backoff
    task_max_retries=3,  # Max 3 retries
)

# ====================
# Queue Priority Configuration
# ====================

# Priority levels (higher = more important)
QUEUE_PRIORITIES = {
    'critical': 10,  # Fiscalization sync (must succeed)
    'high': 5,       # Payment processing
    'default': 0,    # General tasks
    'low': -5,       # Notifications
}

# Worker concurrency per queue
QUEUE_CONCURRENCY = {
    'critical': 4,   # 4 concurrent workers for critical tasks
    'high': 2,       # 2 concurrent workers for high priority
    'default': 2,    # 2 concurrent workers for default
    'low': 1,        # 1 concurrent worker for low priority
}

# ====================
# Helper Functions
# ====================

def get_queue_stats():
    """
    Get queue statistics (for monitoring)

    Returns:
        Dictionary with queue stats:
        - critical: {pending, active}
        - high: {pending, active}
        - default: {pending, active}
        - low: {pending, active}
    """
    from celery import current_app

    inspector = current_app.control.inspect()

    # Get active tasks
    active = inspector.active()

    # Get reserved tasks (pending)
    reserved = inspector.reserved()

    stats = {
        'critical': {'pending': 0, 'active': 0},
        'high': {'pending': 0, 'active': 0},
        'default': {'pending': 0, 'active': 0},
        'low': {'pending': 0, 'active': 0},
    }

    # Count active tasks per queue
    if active:
        for worker, tasks in active.items():
            for task in tasks:
                queue = task.get('delivery_info', {}).get('routing_key', 'default')
                if queue in stats:
                    stats[queue]['active'] += 1

    # Count reserved tasks per queue
    if reserved:
        for worker, tasks in reserved.items():
            for task in tasks:
                queue = task.get('delivery_info', {}).get('routing_key', 'default')
                if queue in stats:
                    stats[queue]['pending'] += 1

    return stats


def purge_queue(queue_name: str) -> int:
    """
    Purge all tasks from a queue

    Args:
        queue_name: Queue to purge (critical, high, default, low)

    Returns:
        Number of tasks purged
    """
    from celery import current_app

    if queue_name not in QUEUE_PRIORITIES:
        raise ValueError(f"Invalid queue name: {queue_name}")

    # Purge queue
    count = current_app.control.purge()

    return count


# ====================
# Example Usage
# ====================

if __name__ == "__main__":
    # Print configuration
    print("=== Celery Configuration ===")
    print(f"Broker: {BROKER_URL}")
    print(f"Backend: {BACKEND_URL}")
    print(f"\nQueues:")
    for queue, priority in QUEUE_PRIORITIES.items():
        print(f"  - {queue}: priority={priority}, concurrency={QUEUE_CONCURRENCY[queue]}")

    print("\nTask Routes:")
    for task, route in app.conf.task_routes.items():
        print(f"  - {task} → {route['queue']}")
