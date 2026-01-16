# pos_monitor/app/models.py
"""Pydantic models for POS Monitor API"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class BufferStatus(BaseModel):
    """Buffer state"""
    pending: int = Field(..., description="Number of pending (unsent) receipts")
    dlq: int = Field(..., description="Number of receipts in Dead Letter Queue")
    percent_full: float = Field(..., ge=0, le=100, description="Buffer capacity percentage")
    last_sync: Optional[int] = Field(None, description="Timestamp of last successful sync (Unix epoch)")


class KKTStatus(BaseModel):
    """KKT Adapter status"""
    is_online: bool = Field(..., description="Whether KKT Adapter is responding")
    circuit_breaker_state: str = Field(..., description="Circuit Breaker state: CLOSED|OPEN|HALF_OPEN")
    last_heartbeat: int = Field(..., description="Timestamp of last heartbeat (Unix epoch)")
    ofd_status: str = Field(..., description="OFD connection status: online|offline")


class POSStatus(BaseModel):
    """Overall POS status"""
    cash_balance: float = Field(..., ge=0, description="Current cash balance in session")
    card_balance: float = Field(..., ge=0, description="Current card balance in session")
    buffer: BufferStatus
    kkt_status: KKTStatus
    timestamp: int = Field(..., description="Status snapshot timestamp (Unix epoch)")


class Alert(BaseModel):
    """Alert model"""
    level: str = Field(..., description="Alert severity: P1|P2|INFO")
    message: str = Field(..., description="Alert message")
    action: str = Field(..., description="Recommended action for user")
    timestamp: int = Field(..., description="Alert creation timestamp (Unix epoch)")


class HealthResponse(BaseModel):
    """Health check response"""
    status: str = Field(..., description="Health status: ok|degraded|error")
    timestamp: int = Field(..., description="Health check timestamp")
    buffer_accessible: bool = Field(..., description="Whether buffer.db is accessible")


class SalesDataPoint(BaseModel):
    """Sales data for charts"""
    hour: int = Field(..., ge=0, le=23, description="Hour of day (0-23)")
    revenue: float = Field(..., ge=0, description="Total revenue for the hour")
    count: int = Field(..., ge=0, description="Number of receipts in the hour")


class SalesTodayResponse(BaseModel):
    """Sales summary for today"""
    total_revenue: float = Field(..., ge=0, description="Total revenue for today")
    total_count: int = Field(..., ge=0, description="Total number of receipts")
    hourly_data: List[SalesDataPoint] = Field(default_factory=list, description="Hourly breakdown")
    date: str = Field(..., description="Date (YYYY-MM-DD)")
