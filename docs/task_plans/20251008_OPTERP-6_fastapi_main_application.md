# OPTERP-6: Create FastAPI Main Application

**Task:** Create FastAPI main application for KKT Adapter with core API endpoints

**Story Points:** 3
**Sprint:** Phase 1 - POC (Week 1)
**Status:** In Progress
**Created:** 2025-10-08
**Assignee:** AI Agent

---

## 📋 Task Description

Create FastAPI application for the KKT adapter with core API endpoints for receipt creation, buffer status, and health checks. This is the main entry point for the offline-first fiscal receipt adapter.

**References:**
- CLAUDE.md §4.4 (API endpoints адаптера)
- CLAUDE.md §3.1 (Структура проекта)
- OPTERP-4: SQLite Buffer CRUD (completed)

---

## 🎯 Acceptance Criteria

- [ ] **AC1:** FastAPI application initialized with proper config
- [ ] **AC2:** POST /v1/kkt/receipt endpoint implemented
- [ ] **AC3:** GET /v1/kkt/buffer/status endpoint implemented
- [ ] **AC4:** GET /v1/health endpoint implemented
- [ ] **AC5:** Pydantic models for request/response validation
- [ ] **AC6:** Error handling middleware
- [ ] **AC7:** CORS middleware configured
- [ ] **AC8:** API docs available at /docs (Swagger UI)
- [ ] **AC9:** Application starts without errors
- [ ] **AC10:** Manual smoke test passed (all endpoints)

---

## 📐 Implementation Plan

### Step 1: Create FastAPI application skeleton (20 min)

**File:** `kkt_adapter/app/main.py`

**Structure:**
```python
"""
FastAPI Main Application for KKT Adapter

Author: AI Agent
Created: 2025-10-08
Purpose: Main entry point for offline-first fiscal receipt adapter

Reference: CLAUDE.md §4.4
"""

from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
import logging
from typing import Optional

from .buffer import (
    insert_receipt,
    get_buffer_status,
    get_pending_receipts,
    BufferFullError
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="KKT Adapter API",
    description="Offline-first fiscal receipt adapter with SQLite buffering",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure properly in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Step 2: Create Pydantic models (25 min)

**File:** `kkt_adapter/app/models.py`

**Models:**
```python
"""
Pydantic Models for API Request/Response

Author: AI Agent
Created: 2025-10-08
"""

from pydantic import BaseModel, Field, validator
from typing import List, Optional, Literal
from decimal import Decimal


class ReceiptItem(BaseModel):
    """Receipt item (товар)"""
    name: str = Field(..., min_length=1, max_length=255)
    price: Decimal = Field(..., gt=0)
    quantity: Decimal = Field(..., gt=0)
    total: Decimal = Field(..., gt=0)
    vat_rate: Optional[int] = Field(None, ge=0, le=20)  # НДС %

    @validator('total')
    def validate_total(cls, v, values):
        if 'price' in values and 'quantity' in values:
            expected = values['price'] * values['quantity']
            if abs(v - expected) > Decimal('0.01'):
                raise ValueError('Total does not match price * quantity')
        return v


class ReceiptPayment(BaseModel):
    """Payment method"""
    type: Literal['cash', 'card', 'other']
    amount: Decimal = Field(..., gt=0)


class CreateReceiptRequest(BaseModel):
    """Request to create fiscal receipt"""
    pos_id: str = Field(..., min_length=1)
    type: Literal['sale', 'refund', 'correction']
    items: List[ReceiptItem] = Field(..., min_items=1)
    payments: List[ReceiptPayment] = Field(..., min_items=1)

    @validator('payments')
    def validate_payments_total(cls, v, values):
        if 'items' in values:
            items_total = sum(item.total for item in values['items'])
            payments_total = sum(payment.amount for payment in v)
            if abs(items_total - payments_total) > Decimal('0.01'):
                raise ValueError('Payments total does not match items total')
        return v


class CreateReceiptResponse(BaseModel):
    """Response from receipt creation"""
    status: Literal['printed', 'buffered']
    receipt_id: str
    fiscal_doc: Optional[dict] = None
    message: Optional[str] = None


class BufferStatusResponse(BaseModel):
    """Buffer status response"""
    total_capacity: int
    current_queued: int
    percent_full: float
    network_status: Literal['online', 'offline', 'degraded']
    total_receipts: int
    pending: int
    synced: int
    failed: int
    dlq_size: int


class HealthCheckResponse(BaseModel):
    """Health check response"""
    status: Literal['healthy', 'degraded', 'unhealthy']
    components: dict
    version: str = "0.1.0"
```

### Step 3: Implement POST /v1/kkt/receipt endpoint (30 min)

**Endpoint implementation:**
```python
@app.post(
    "/v1/kkt/receipt",
    response_model=CreateReceiptResponse,
    status_code=200,
    summary="Create fiscal receipt",
    description="Create fiscal receipt with two-phase fiscalization"
)
async def create_receipt(
    request: CreateReceiptRequest,
    idempotency_key: str = Header(..., alias="Idempotency-Key")
):
    """
    Create fiscal receipt with two-phase fiscalization:

    Phase 1: Print receipt and save to local buffer (always succeeds)
    Phase 2: Send to OFD asynchronously (best-effort)

    Args:
        request: Receipt data
        idempotency_key: UUID for idempotency

    Returns:
        Receipt ID and status

    Raises:
        503: Buffer full
        400: Invalid request
    """
    logger.info(f"Creating receipt for POS {request.pos_id}, idempotency_key={idempotency_key}")

    try:
        # Convert to dict for buffer.insert_receipt()
        receipt_data = {
            'pos_id': request.pos_id,
            'fiscal_doc': {
                'type': request.type,
                'items': [item.dict() for item in request.items],
                'payments': [payment.dict() for payment in request.payments],
                'idempotency_key': idempotency_key
            }
        }

        # Phase 1: Insert into buffer (local)
        receipt_id = insert_receipt(receipt_data)

        logger.info(f"Receipt created successfully: {receipt_id}")

        return CreateReceiptResponse(
            status='buffered',  # Will be 'printed' after KKT driver integration
            receipt_id=receipt_id,
            fiscal_doc=None,  # Populated after OFD sync
            message="Receipt saved to buffer successfully"
        )

    except BufferFullError as e:
        logger.error(f"Buffer full: {e}")
        raise HTTPException(status_code=503, detail=str(e))

    except ValueError as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))

    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
```

### Step 4: Implement GET /v1/kkt/buffer/status endpoint (20 min)

**Endpoint implementation:**
```python
@app.get(
    "/v1/kkt/buffer/status",
    response_model=BufferStatusResponse,
    status_code=200,
    summary="Get buffer status",
    description="Get current offline buffer status and metrics"
)
async def get_buffer_status_endpoint():
    """
    Get buffer status including:
    - Capacity and current queue size
    - Percent full
    - Network status
    - Receipt counts by status

    Returns:
        Buffer status metrics
    """
    try:
        status = get_buffer_status()

        # Determine network status (simplified - will be enhanced later)
        network_status = 'online' if status.pending == 0 else 'offline'

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
        logger.exception(f"Error getting buffer status: {e}")
        raise HTTPException(status_code=500, detail="Failed to get buffer status")
```

### Step 5: Implement GET /v1/health endpoint (15 min)

**Endpoint implementation:**
```python
@app.get(
    "/v1/health",
    response_model=HealthCheckResponse,
    status_code=200,
    summary="Health check",
    description="Check application health and component status"
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

        # Determine overall health
        if status.dlq_size > 50 or status.percent_full > 90:
            overall_status = 'degraded'
        elif status.dlq_size > 100 or status.percent_full >= 100:
            overall_status = 'unhealthy'
        else:
            overall_status = 'healthy'

        return HealthCheckResponse(
            status=overall_status,
            components={
                'buffer': {
                    'status': 'healthy' if buffer_healthy else 'unhealthy',
                    'percent_full': status.percent_full,
                    'dlq_size': status.dlq_size
                },
                'circuit_breaker': {
                    'state': 'CLOSED'  # Placeholder - will implement later
                }
            }
        )

    except Exception as e:
        logger.exception(f"Health check failed: {e}")
        return HealthCheckResponse(
            status='unhealthy',
            components={
                'buffer': {'status': 'unhealthy', 'error': str(e)},
                'circuit_breaker': {'state': 'UNKNOWN'}
            }
        )
```

### Step 6: Add error handling middleware (15 min)

**Middleware:**
```python
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler"""
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
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )
```

### Step 7: Add startup/shutdown events (10 min)

**Event handlers:**
```python
@app.on_event("startup")
async def startup_event():
    """Application startup"""
    logger.info("KKT Adapter starting up...")

    # Initialize buffer database
    from .buffer import init_buffer_db
    init_buffer_db()

    logger.info("KKT Adapter started successfully")


@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown"""
    logger.info("KKT Adapter shutting down...")

    # Close database connections
    from .buffer import close_buffer_db
    close_buffer_db()

    logger.info("KKT Adapter shut down successfully")
```

### Step 8: Add main entry point (10 min)

**Main function:**
```python
if __name__ == "__main__":
    uvicorn.run(
        "kkt_adapter.app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,  # Development only
        log_level="info"
    )
```

### Step 9: Create requirements.txt (10 min)

**File:** `kkt_adapter/requirements.txt`

```txt
fastapi==0.104.1
uvicorn[standard]==0.24.0
pydantic==2.5.0
python-multipart==0.0.6
```

### Step 10: Manual smoke test (20 min)

**Test script:** `scripts/test_api_smoke.sh`

```bash
#!/bin/bash

# Test FastAPI endpoints

BASE_URL="http://localhost:8000"

echo "=== KKT Adapter API Smoke Test ==="

# 1. Health check
echo -e "\n1. Testing GET /v1/health"
curl -X GET "$BASE_URL/v1/health" -H "Content-Type: application/json"

# 2. Buffer status
echo -e "\n\n2. Testing GET /v1/kkt/buffer/status"
curl -X GET "$BASE_URL/v1/kkt/buffer/status"

# 3. Create receipt
echo -e "\n\n3. Testing POST /v1/kkt/receipt"
curl -X POST "$BASE_URL/v1/kkt/receipt" \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: $(uuidgen)" \
  -d '{
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
  }'

# 4. Check buffer status again
echo -e "\n\n4. Testing buffer status after receipt"
curl -X GET "$BASE_URL/v1/kkt/buffer/status"

echo -e "\n\n=== Smoke Test Complete ==="
```

---

## 🧪 Testing Strategy

**Manual testing (this task):**
1. Start FastAPI application
2. Open Swagger UI at http://localhost:8000/docs
3. Test each endpoint manually
4. Run smoke test script
5. Verify all responses

**Unit tests (OPTERP-7 - next task):**
- Test each endpoint with pytest + httpx
- Mock buffer operations
- Test error handling
- Test validation

---

## 📦 Deliverables

- [ ] `kkt_adapter/app/main.py` (≈250 lines)
- [ ] `kkt_adapter/app/models.py` (≈120 lines)
- [ ] `kkt_adapter/requirements.txt`
- [ ] `scripts/test_api_smoke.sh`
- [ ] Manual smoke test passed
- [ ] Code committed to `feature/phase1-poc` branch
- [ ] Changes pushed to remote

---

## ⏱️ Time Estimate

| Step | Task | Time |
|------|------|------|
| 1 | Create FastAPI skeleton | 20 min |
| 2 | Create Pydantic models | 25 min |
| 3 | Implement POST /v1/kkt/receipt | 30 min |
| 4 | Implement GET /v1/kkt/buffer/status | 20 min |
| 5 | Implement GET /v1/health | 15 min |
| 6 | Add error handling middleware | 15 min |
| 7 | Add startup/shutdown events | 10 min |
| 8 | Add main entry point | 10 min |
| 9 | Create requirements.txt | 10 min |
| 10 | Manual smoke test | 20 min |
| **TOTAL** | **2h 55min** |

---

## 🔗 Dependencies

**Requires:**
- ✅ OPTERP-2: Hybrid Logical Clock (completed)
- ✅ OPTERP-4: SQLite Buffer CRUD (completed)
- ✅ OPTERP-5: Buffer Unit Tests (completed)

**Blocks:**
- OPTERP-7: FastAPI Unit Tests

---

## 📝 Notes

### API Design Principles

1. **RESTful:** Standard REST conventions
2. **Idempotency:** Idempotency-Key header for receipts
3. **Validation:** Pydantic models for request/response
4. **Error Handling:** Proper HTTP status codes
5. **Documentation:** Auto-generated Swagger UI

### Endpoints Summary

| Method | Path | Purpose | Auth |
|--------|------|---------|------|
| POST | /v1/kkt/receipt | Create receipt | Required |
| GET | /v1/kkt/buffer/status | Buffer status | None |
| GET | /v1/health | Health check | None |
| GET | /docs | Swagger UI | None |

### Future Enhancements (not in this task)

- POST /v1/kkt/buffer/sync - Manual sync trigger
- Authentication/Authorization
- Rate limiting
- Request/Response logging
- Metrics (Prometheus)
- Circuit breaker integration
- KKT driver integration (print receipt)
- OFD client integration (Phase 2)

### Configuration

For now, hardcoded values. Later will move to config file:
- Host: 0.0.0.0
- Port: 8000
- CORS: Allow all origins (dev only)
- Log level: INFO

---

## ✅ Definition of Done

- [ ] All 10 implementation steps completed
- [ ] FastAPI application starts without errors
- [ ] Swagger UI accessible at /docs
- [ ] All 3 endpoints respond correctly
- [ ] Pydantic validation working
- [ ] Error handling tested
- [ ] Smoke test script passes
- [ ] Code follows project style
- [ ] No linter errors
- [ ] Committed with message: `feat(fastapi): create main application with core endpoints [OPTERP-6]`
- [ ] Pushed to remote

---

## 🚀 Ready to Implement

This task plan is complete and ready for execution. Proceed with Step 1.
