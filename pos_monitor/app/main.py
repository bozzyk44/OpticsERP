# pos_monitor/app/main.py
"""POS Monitor - Local dashboard for POS terminals"""
import logging
import time
from pathlib import Path
from fastapi import FastAPI, WebSocket, Request
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import List

from .database import (
    get_cash_balance,
    get_buffer_status,
    get_sales_today,
    check_buffer_accessible
)
from .alerts import check_alerts, get_kkt_status
from .websocket import websocket_handler
from .models import (
    POSStatus,
    Alert,
    HealthResponse,
    SalesTodayResponse,
    BufferStatus,
    KKTStatus
)
from .config import LOG_LEVEL, LOG_FILE

# Configure logging
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="POS Monitor",
    description="Local monitoring dashboard for POS terminals",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# CORS middleware (for development)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all HTTP requests"""
    start_time = time.time()

    try:
        response = await call_next(request)
        process_time = time.time() - start_time

        logger.info(
            f"{request.method} {request.url.path} - "
            f"Status: {response.status_code} - "
            f"Duration: {process_time:.3f}s"
        )

        return response

    except Exception as e:
        logger.error(f"Request failed: {request.method} {request.url.path} - Error: {e}")
        raise


# API Endpoints
@app.get("/api/v1/status", response_model=POSStatus)
async def get_status():
    """
    Get current POS status (cash, card, buffer, KKT)

    Returns:
        POSStatus: Complete POS status snapshot
    """
    try:
        cash, card = get_cash_balance()
        buffer = get_buffer_status()
        kkt_status = get_kkt_status()

        return POSStatus(
            cash_balance=cash,
            card_balance=card,
            buffer=BufferStatus(**buffer),
            kkt_status=KKTStatus(**kkt_status),
            timestamp=int(time.time())
        )

    except Exception as e:
        logger.error(f"Error getting status: {e}")
        raise


@app.get("/api/v1/alerts", response_model=List[Alert])
async def get_alerts():
    """
    Get active alerts (P1, P2, INFO)

    Returns:
        List[Alert]: Active alerts with severity and recommended actions
    """
    try:
        return check_alerts()

    except Exception as e:
        logger.error(f"Error checking alerts: {e}")
        return []


@app.get("/api/v1/sales/today", response_model=SalesTodayResponse)
async def get_sales_today_endpoint():
    """
    Get sales data for current day

    Returns:
        SalesTodayResponse: Total revenue, count, and hourly breakdown
    """
    try:
        sales_data = get_sales_today()
        return SalesTodayResponse(**sales_data)

    except Exception as e:
        logger.error(f"Error getting sales data: {e}")
        raise


@app.websocket("/ws/realtime")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time status updates

    Sends status updates every 2 seconds (configurable)
    """
    await websocket_handler(websocket)


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint

    Returns:
        HealthResponse: Service health status
    """
    buffer_accessible = check_buffer_accessible()

    status = "ok" if buffer_accessible else "degraded"

    return HealthResponse(
        status=status,
        timestamp=int(time.time()),
        buffer_accessible=buffer_accessible
    )


# Exception handlers
@app.exception_handler(FileNotFoundError)
async def file_not_found_handler(request: Request, exc: FileNotFoundError):
    """Handle database file not found errors"""
    logger.error(f"File not found: {exc}")
    return JSONResponse(
        status_code=503,
        content={
            "detail": "Database not accessible. Check that buffer.db exists and is readable.",
            "error": str(exc)
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle all other exceptions"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "error": str(exc)
        }
    )


# Startup/Shutdown events
@app.on_event("startup")
async def startup_event():
    """Application startup"""
    logger.info("🚀 POS Monitor starting up...")

    # Check buffer.db accessibility
    if check_buffer_accessible():
        logger.info("✅ buffer.db accessible")
    else:
        logger.warning("⚠️ buffer.db not accessible - check database path")

    logger.info("✅ POS Monitor ready on port 8001")


@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown"""
    logger.info("⏹️ POS Monitor shutting down...")


# Serve React SPA (static files)
# This should be last so it doesn't override API routes
static_dir = Path(__file__).parent.parent / "static"
if static_dir.exists():
    app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="static")
    logger.info(f"✅ Serving static files from {static_dir}")
else:
    logger.warning(f"⚠️ Static directory not found: {static_dir}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8001,
        reload=True,
        log_level="info"
    )
