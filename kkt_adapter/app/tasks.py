"""
Celery Tasks for KKT Adapter

Author: AI Agent
Created: 2025-11-29
Task: OPTERP-48 (Implement Bulkhead Pattern - Celery Queues)

Purpose:
Define Celery tasks routed to different priority queues:
- sync_buffer, sync_receipt → critical queue
- process_payment, confirm_order → high queue
- cleanup_old_receipts, generate_analytics → default queue
- send_email, send_sms → low queue

Reference: CLAUDE.md §8 (Bulkhead Pattern)
"""

import logging
import time
import json
from typing import Dict, Any, Optional
from celery import Task

from .celery_app import app

# Import buffer operations
try:
    from .buffer import (
        get_pending_receipts,
        mark_synced,
        increment_retry_count,
        move_to_dlq,
        get_receipt_by_id,
    )
    from .circuit_breaker import get_circuit_breaker
    from .ofd_client import get_ofd_client, OFDClientError
except ImportError:
    # Fallback for standalone execution
    from buffer import (
        get_pending_receipts,
        mark_synced,
        increment_retry_count,
        move_to_dlq,
        get_receipt_by_id,
    )
    from circuit_breaker import get_circuit_breaker
    from ofd_client import get_ofd_client, OFDClientError

import pybreaker

logger = logging.getLogger(__name__)

# ====================
# Configuration
# ====================

MAX_RETRY_ATTEMPTS = 20  # Move to DLQ after 20 failed attempts
SYNC_BATCH_SIZE = 50  # Process up to 50 receipts per sync

# ====================
# Custom Task Base Class
# ====================

class CallbackTask(Task):
    """
    Custom task base class with callbacks

    Provides:
    - on_success callback
    - on_failure callback
    - on_retry callback
    """

    def on_success(self, retval, task_id, args, kwargs):
        """Called on task success"""
        logger.info(f"✅ Task {self.name} succeeded: {task_id}")
        return super().on_success(retval, task_id, args, kwargs)

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Called on task failure"""
        logger.error(f"❌ Task {self.name} failed: {task_id}, error: {exc}")
        return super().on_failure(exc, task_id, args, kwargs, einfo)

    def on_retry(self, exc, task_id, args, kwargs, einfo):
        """Called on task retry"""
        logger.warning(f"🔄 Task {self.name} retrying: {task_id}, error: {exc}")
        return super().on_retry(exc, task_id, args, kwargs, einfo)


# ====================
# Critical Queue Tasks
# ====================

@app.task(bind=True, base=CallbackTask, max_retries=3, name='kkt_adapter.tasks.sync_buffer')
def sync_buffer(self) -> Dict[str, Any]:
    """
    Sync pending receipts to OFD (critical queue)

    This task processes pending receipts from the buffer and sends them to OFD.
    Runs in the critical queue to ensure fiscalization is never blocked.

    Returns:
        Dictionary with sync results:
        - synced: int
        - failed: int
        - skipped: int
        - duration_seconds: float
    """
    logger.info("🚀 sync_buffer task started (critical queue)")

    start_time = time.time()

    # Get pending receipts
    receipts = get_pending_receipts(limit=SYNC_BATCH_SIZE)

    if not receipts:
        return {
            "synced": 0,
            "failed": 0,
            "skipped": 0,
            "duration_seconds": 0.0,
            "message": "No pending receipts"
        }

    synced_count = 0
    failed_count = 0
    skipped_count = 0

    # Process each receipt
    for receipt in receipts:
        try:
            # Call sync_receipt task synchronously (or could be async)
            result = sync_receipt.apply(args=[receipt.id])

            if result.successful():
                synced_count += 1
            else:
                failed_count += 1

        except Exception as e:
            logger.error(f"Error processing receipt {receipt.id}: {e}")
            failed_count += 1

    duration = time.time() - start_time

    logger.info(
        f"✅ sync_buffer completed: synced={synced_count}, failed={failed_count}, "
        f"skipped={skipped_count}, duration={duration:.2f}s"
    )

    return {
        "synced": synced_count,
        "failed": failed_count,
        "skipped": skipped_count,
        "duration_seconds": round(duration, 2)
    }


@app.task(bind=True, base=CallbackTask, max_retries=20, name='kkt_adapter.tasks.sync_receipt')
def sync_receipt(self, receipt_id: str) -> bool:
    """
    Sync single receipt to OFD (critical queue)

    Args:
        receipt_id: Receipt UUID

    Returns:
        True if synced successfully, False otherwise

    Raises:
        Retry on OFD errors (up to max_retries)
    """
    cb = get_circuit_breaker()
    ofd = get_ofd_client()

    # Fetch receipt
    receipt = get_receipt_by_id(receipt_id)
    if not receipt:
        logger.error(f"❌ Receipt {receipt_id} not found in buffer")
        return False

    # Skip if already synced
    if receipt.status == 'synced':
        logger.debug(f"Receipt {receipt_id} already synced, skipping")
        return True

    try:
        # Parse fiscal document
        fiscal_doc = json.loads(receipt.fiscal_doc)

        # Send to OFD via Circuit Breaker
        logger.debug(f"Sending receipt {receipt_id} to OFD (attempt {self.request.retries + 1})")

        result = cb.call(ofd.send_receipt, fiscal_doc)

        # Mark as synced
        server_time = int(time.time())
        mark_synced(receipt_id, server_time)

        logger.info(f"✅ Receipt {receipt_id} synced successfully (POS: {receipt.pos_id})")
        return True

    except pybreaker.CircuitBreakerError:
        # Circuit is OPEN - retry later
        logger.warning(f"⚠️ Circuit Breaker OPEN, retrying receipt {receipt_id}")
        raise self.retry(countdown=60)  # Retry after 60 seconds

    except OFDClientError as e:
        # OFD error - increment retry count
        new_count = increment_retry_count(receipt_id, str(e))
        logger.error(f"❌ OFD error for receipt {receipt_id}: {e}, retry_count={new_count}")

        # Move to DLQ if max retries exceeded
        if new_count >= MAX_RETRY_ATTEMPTS:
            move_to_dlq(receipt_id, reason="max_retries_exceeded")
            logger.error(f"🚨 Receipt {receipt_id} moved to DLQ (max retries: {MAX_RETRY_ATTEMPTS})")
            return False

        # Retry with exponential backoff
        raise self.retry(exc=e, countdown=2 ** self.request.retries)

    except Exception as e:
        # Unexpected error - retry
        logger.exception(f"❌ Unexpected error processing receipt {receipt_id}: {e}")
        raise self.retry(exc=e, countdown=2 ** self.request.retries)


# ====================
# High Queue Tasks
# ====================

@app.task(bind=True, base=CallbackTask, max_retries=3, name='kkt_adapter.tasks.process_payment')
def process_payment(self, payment_id: str, amount: float, method: str) -> Dict[str, Any]:
    """
    Process payment (high queue)

    Args:
        payment_id: Payment UUID
        amount: Payment amount
        method: Payment method (cash, card, etc.)

    Returns:
        Payment result
    """
    logger.info(f"💳 Processing payment {payment_id}: {amount} via {method}")

    # Placeholder implementation
    time.sleep(0.5)  # Simulate processing

    return {
        "payment_id": payment_id,
        "status": "success",
        "amount": amount,
        "method": method
    }


@app.task(bind=True, base=CallbackTask, max_retries=3, name='kkt_adapter.tasks.confirm_order')
def confirm_order(self, order_id: str) -> Dict[str, Any]:
    """
    Confirm order (high queue)

    Args:
        order_id: Order UUID

    Returns:
        Order confirmation result
    """
    logger.info(f"✅ Confirming order {order_id}")

    # Placeholder implementation
    time.sleep(0.3)  # Simulate processing

    return {
        "order_id": order_id,
        "status": "confirmed"
    }


# ====================
# Default Queue Tasks
# ====================

@app.task(bind=True, base=CallbackTask, name='kkt_adapter.tasks.cleanup_old_receipts')
def cleanup_old_receipts(self, days: int = 90) -> Dict[str, Any]:
    """
    Cleanup old receipts (default queue)

    Args:
        days: Delete receipts older than N days

    Returns:
        Cleanup result
    """
    logger.info(f"🧹 Cleaning up receipts older than {days} days")

    # Placeholder implementation
    # TODO: Implement actual cleanup logic

    return {
        "deleted": 0,
        "message": f"Receipts older than {days} days deleted"
    }


@app.task(bind=True, base=CallbackTask, name='kkt_adapter.tasks.generate_analytics')
def generate_analytics(self) -> Dict[str, Any]:
    """
    Generate analytics report (default queue)

    Returns:
        Analytics result
    """
    logger.info("📊 Generating analytics")

    # Placeholder implementation
    # TODO: Implement actual analytics logic

    return {
        "status": "success",
        "message": "Analytics generated"
    }


# ====================
# Low Queue Tasks
# ====================

@app.task(bind=True, base=CallbackTask, max_retries=3, name='kkt_adapter.tasks.send_email')
def send_email(self, to: str, subject: str, body: str) -> Dict[str, Any]:
    """
    Send email (low queue)

    Args:
        to: Recipient email
        subject: Email subject
        body: Email body

    Returns:
        Email send result
    """
    logger.info(f"📧 Sending email to {to}: {subject}")

    # Placeholder implementation
    # TODO: Implement actual email sending (SMTP, SendGrid, etc.)
    time.sleep(1.0)  # Simulate email sending

    return {
        "to": to,
        "subject": subject,
        "status": "sent"
    }


@app.task(bind=True, base=CallbackTask, max_retries=3, name='kkt_adapter.tasks.send_sms')
def send_sms(self, to: str, message: str) -> Dict[str, Any]:
    """
    Send SMS (low queue)

    Args:
        to: Recipient phone number
        message: SMS message

    Returns:
        SMS send result
    """
    logger.info(f"📱 Sending SMS to {to}: {message}")

    # Placeholder implementation
    # TODO: Implement actual SMS sending (Twilio, etc.)
    time.sleep(0.5)  # Simulate SMS sending

    return {
        "to": to,
        "message": message,
        "status": "sent"
    }


# ====================
# Periodic Tasks (Optional - Celery Beat)
# ====================

# Uncomment to enable periodic sync
# from celery.schedules import crontab
#
# app.conf.beat_schedule = {
#     'sync-buffer-every-minute': {
#         'task': 'kkt_adapter.tasks.sync_buffer',
#         'schedule': 60.0,  # Every 60 seconds
#     },
#     'cleanup-old-receipts-daily': {
#         'task': 'kkt_adapter.tasks.cleanup_old_receipts',
#         'schedule': crontab(hour=2, minute=0),  # 2:00 AM daily
#     },
# }


# ====================
# Example Usage
# ====================

if __name__ == "__main__":
    # Example: trigger sync_buffer task
    result = sync_buffer.delay()
    print(f"Task ID: {result.id}")
    print(f"Task state: {result.state}")
