"""
FastAPI Main Application for KKT Adapter

Author: AI Agent
Created: 2025-10-08
Purpose: Main entry point for offline-first fiscal receipt adapter

Reference: CLAUDE.md §4.4

This application provides REST API for:
- Creating fiscal receipts with two-phase fiscalization
- Monitoring offline buffer status
- Health checks

Key Features:
- Offline-first architecture with SQLite buffer
- Automatic failover to buffer when OFD unavailable
- HLC-based timestamp ordering
- Pydantic validation for all requests
"""

from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
import logging
from typing import Optional

# Import buffer operations
try:
    from .buffer import (
        insert_receipt,
        get_buffer_status,
        init_buffer_db,
        close_buffer_db,
        BufferFullError
    )
    from .models import (
        CreateReceiptRequest,
        CreateReceiptResponse,
        BufferStatusResponse,
        HealthCheckResponse
    )
    from .circuit_breaker import get_circuit_breaker
except ImportError:
    # Handle direct execution
    from buffer import (
        insert_receipt,
        get_buffer_status,
        init_buffer_db,
        close_buffer_db,
        BufferFullError
    )
    from models import (
        CreateReceiptRequest,
        CreateReceiptResponse,
        BufferStatusResponse,
        HealthCheckResponse
    )
    from circuit_breaker import get_circuit_breaker


# ====================
# Logging Configuration
# ====================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ====================
# FastAPI Application
# ====================

app = FastAPI(
    title="KKT Adapter API",
    description="Offline-first fiscal receipt adapter with SQLite buffering and HLC ordering",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    contact={
        "name": "OpticsERP Team",
        "email": "support@example.com"
    },
    license_info={
        "name": "Proprietary"
    }
)


# ====================
# CORS Middleware
# ====================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: Configure properly in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ====================
# Exception Handlers
# ====================

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler for unhandled exceptions"""
    logger.exception(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "type": type(exc).__name__
        }
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """HTTP exception handler"""
    logger.warning(f"HTTP {exc.status_code}: {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )


# ====================
# Lifecycle Events
# ====================

@app.on_event("startup")
async def startup_event():
    """Application startup event"""
    logger.info("=== KKT Adapter starting up ===")

    try:
        # Initialize buffer database
        init_buffer_db()
        logger.info("✅ Buffer database initialized")

        # Log startup completion
        logger.info("=== KKT Adapter started successfully ===")
        logger.info(f"API docs available at: http://localhost:8000/docs")

    except Exception as e:
        logger.exception(f"❌ Startup failed: {e}")
        raise


@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown event"""
    logger.info("=== KKT Adapter shutting down ===")

    try:
        # Close database connections
        close_buffer_db()
        logger.info("✅ Database connections closed")

        logger.info("=== KKT Adapter shut down successfully ===")

    except Exception as e:
        logger.exception(f"❌ Shutdown error: {e}")


# ====================
# API Endpoints
# ====================

@app.post(
    "/v1/kkt/receipt",
    response_model=CreateReceiptResponse,
    status_code=200,
    summary="Create fiscal receipt",
    description="""
    Create fiscal receipt with two-phase fiscalization:

    **Phase 1 (Local):** Print receipt and save to offline buffer (always succeeds)
    **Phase 2 (Remote):** Send to OFD asynchronously (best-effort)

    Requires Idempotency-Key header (UUID) to prevent duplicate receipts.
    """,
    tags=["Receipts"]
)
async def create_receipt(
    request: CreateReceiptRequest,
    idempotency_key: str = Header(..., alias="Idempotency-Key", description="UUID for idempotency")
):
    """
    Create fiscal receipt with two-phase fiscalization

    Args:
        request: Receipt data (POS ID, items, payments)
        idempotency_key: UUID for idempotency protection

    Returns:
        Receipt ID and status

    Raises:
        400: Invalid request data
        503: Buffer full (capacity reached)
        500: Internal server error
    """
    logger.info(f"Creating receipt for POS {request.pos_id}, idempotency_key={idempotency_key}")

    try:
        # Convert Pydantic model to dict for buffer.insert_receipt()
        # Use model_dump() instead of deprecated dict()
        # mode='json' ensures Decimal is converted to float for JSON serialization
        receipt_data = {
            'pos_id': request.pos_id,
            'fiscal_doc': {
                'type': request.type,
                'items': [item.model_dump(mode='json') for item in request.items],
                'payments': [payment.model_dump(mode='json') for payment in request.payments],
                'idempotency_key': idempotency_key
            }
        }

        # Phase 1: Insert into buffer (local)
        receipt_id = insert_receipt(receipt_data)

        logger.info(f"✅ Receipt created successfully: {receipt_id}")

        # TODO: Phase 2: Send to OFD asynchronously (OPTERP-8)

        return CreateReceiptResponse(
            status='buffered',  # Will be 'printed' after KKT driver integration
            receipt_id=receipt_id,
            fiscal_doc=None,  # Populated after OFD sync
            message="Receipt saved to buffer successfully"
        )

    except BufferFullError as e:
        logger.error(f"❌ Buffer full: {e}")
        raise HTTPException(
            status_code=503,
            detail=f"Buffer full: {str(e)}. Cannot accept new receipts."
        )

    except ValueError as e:
        logger.error(f"❌ Validation error: {e}")
        raise HTTPException(
            status_code=400,
            detail=f"Invalid request: {str(e)}"
        )

    except Exception as e:
        logger.exception(f"❌ Unexpected error creating receipt: {e}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error"
        )


@app.get(
    "/v1/kkt/buffer/status",
    response_model=BufferStatusResponse,
    status_code=200,
    summary="Get buffer status",
    description="""
    Get current offline buffer status and metrics

    Returns information about:
    - Buffer capacity and current queue size
    - Percent full
    - Network status (online/offline/degraded)
    - Receipt counts by status (pending/synced/failed)
    - Dead Letter Queue size
    """,
    tags=["Buffer"]
)
async def get_buffer_status_endpoint():
    """
    Get buffer status

    Returns:
        Buffer status metrics

    Raises:
        500: Failed to get buffer status
    """
    try:
        # Get status from buffer
        status = get_buffer_status()

        # Determine network status (simplified - will be enhanced later)
        # TODO: Implement proper network detection (ping OFD, etc.)
        if status.pending == 0 and status.synced > 0:
            network_status = 'online'
        elif status.pending > 0 and status.pending < status.capacity * 0.5:
            network_status = 'degraded'
        else:
            network_status = 'offline'

        logger.debug(f"Buffer status: {status.pending}/{status.capacity} pending, network={network_status}")

        return BufferStatusResponse(
            total_capacity=status.capacity,
            current_queued=status.pending,
            percent_full=status.percent_full,
            network_status=network_status,
            total_receipts=status.total_receipts,
            pending=status.pending,
            synced=status.synced,
            failed=status.failed,
            dlq_size=status.dlq_size
        )

    except Exception as e:
        logger.exception(f"❌ Error getting buffer status: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to get buffer status"
        )


@app.get(
    "/v1/health",
    response_model=HealthCheckResponse,
    status_code=200,
    summary="Health check",
    description="""
    Check application health and component status

    Returns overall health status (healthy/degraded/unhealthy) and
    individual component states.

    Health criteria:
    - **Healthy:** DLQ < 50, Buffer < 90% full
    - **Degraded:** DLQ 50-100, Buffer 90-99% full
    - **Unhealthy:** DLQ > 100, Buffer 100% full
    """,
    tags=["Monitoring"]
)
async def health_check():
    """
    Health check endpoint

    Returns:
        Application health status and component states
    """
    try:
        # Check buffer connectivity
        status = get_buffer_status()
        buffer_healthy = True

        # Check circuit breaker status
        cb = get_circuit_breaker()
        cb_stats = cb.get_stats()

        # Determine overall health based on buffer metrics and circuit breaker
        if status.dlq_size > 50 or status.percent_full > 90 or cb_stats.state == 'OPEN':
            overall_status = 'degraded'
        elif status.dlq_size > 100 or status.percent_full >= 100:
            overall_status = 'unhealthy'
        else:
            overall_status = 'healthy'

        logger.debug(f"Health check: {overall_status}, DLQ={status.dlq_size}, buffer={status.percent_full}%, CB={cb_stats.state}")

        return HealthCheckResponse(
            status=overall_status,
            components={
                'buffer': {
                    'status': 'healthy' if buffer_healthy else 'unhealthy',
                    'percent_full': status.percent_full,
                    'dlq_size': status.dlq_size,
                    'pending': status.pending
                },
                'circuit_breaker': {
                    'state': cb_stats.state,
                    'failure_count': cb_stats.failure_count,
                    'success_count': cb_stats.success_count,
                    'last_failure': cb_stats.last_failure_time.isoformat() if cb_stats.last_failure_time else None
                },
                'database': {
                    'status': 'healthy',
                    'type': 'SQLite',
                    'mode': 'WAL'
                }
            },
            version="0.1.0"
        )

    except Exception as e:
        logger.exception(f"❌ Health check failed: {e}")
        return HealthCheckResponse(
            status='unhealthy',
            components={
                'buffer': {
                    'status': 'unhealthy',
                    'error': str(e)
                },
                'circuit_breaker': {
                    'state': 'UNKNOWN'
                },
                'database': {
                    'status': 'unhealthy',
                    'error': str(e)
                }
            },
            version="0.1.0"
        )


@app.get(
    "/",
    summary="Root endpoint",
    description="Welcome message and API information",
    tags=["General"]
)
async def root():
    """Root endpoint - welcome message"""
    return {
        "message": "KKT Adapter API",
        "version": "0.1.0",
        "docs": "/docs",
        "health": "/v1/health",
        "status": "operational"
    }


# ====================
# Main Entry Point
# ====================

if __name__ == "__main__":
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )
