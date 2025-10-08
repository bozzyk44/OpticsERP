"""
Pydantic Models for API Request/Response

Author: AI Agent
Created: 2025-10-08
Purpose: Data validation models for KKT Adapter API endpoints

Reference: CLAUDE.md §4.4
"""

from pydantic import BaseModel, Field, validator
from typing import List, Optional, Literal
from decimal import Decimal


class ReceiptItem(BaseModel):
    """
    Receipt item (товар)

    Represents a single item in a fiscal receipt with price, quantity,
    and VAT information.
    """
    name: str = Field(..., min_length=1, max_length=255, description="Item name")
    price: Decimal = Field(..., gt=0, description="Item price per unit")
    quantity: Decimal = Field(..., gt=0, description="Quantity")
    total: Decimal = Field(..., gt=0, description="Total amount (price * quantity)")
    vat_rate: Optional[int] = Field(None, ge=0, le=20, description="VAT rate in %")

    @validator('total')
    def validate_total(cls, v, values):
        """Validate that total matches price * quantity"""
        if 'price' in values and 'quantity' in values:
            expected = values['price'] * values['quantity']
            if abs(v - expected) > Decimal('0.01'):
                raise ValueError('Total does not match price * quantity')
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Product A",
                "price": 100.00,
                "quantity": 2,
                "total": 200.00,
                "vat_rate": 20
            }
        }


class ReceiptPayment(BaseModel):
    """
    Payment method

    Represents a payment method used in the receipt (cash, card, etc.)
    """
    type: Literal['cash', 'card', 'other'] = Field(..., description="Payment type")
    amount: Decimal = Field(..., gt=0, description="Payment amount")

    class Config:
        json_schema_extra = {
            "example": {
                "type": "cash",
                "amount": 200.00
            }
        }


class CreateReceiptRequest(BaseModel):
    """
    Request to create fiscal receipt

    Validates the complete fiscal receipt request including items,
    payments, and ensures total amounts match.
    """
    pos_id: str = Field(..., min_length=1, description="POS terminal ID")
    type: Literal['sale', 'refund', 'correction'] = Field(..., description="Receipt type")
    items: List[ReceiptItem] = Field(..., min_items=1, description="Receipt items")
    payments: List[ReceiptPayment] = Field(..., min_items=1, description="Payment methods")

    @validator('payments')
    def validate_payments_total(cls, v, values):
        """Validate that payments total matches items total"""
        if 'items' in values:
            items_total = sum(item.total for item in values['items'])
            payments_total = sum(payment.amount for payment in v)
            if abs(items_total - payments_total) > Decimal('0.01'):
                raise ValueError('Payments total does not match items total')
        return v

    class Config:
        json_schema_extra = {
            "example": {
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
        }


class CreateReceiptResponse(BaseModel):
    """
    Response from receipt creation

    Returns the receipt ID and status after two-phase fiscalization.
    """
    status: Literal['printed', 'buffered'] = Field(..., description="Receipt status")
    receipt_id: str = Field(..., description="Unique receipt ID (UUID)")
    fiscal_doc: Optional[dict] = Field(None, description="Fiscal document (after OFD sync)")
    message: Optional[str] = Field(None, description="Additional information")

    class Config:
        json_schema_extra = {
            "example": {
                "status": "buffered",
                "receipt_id": "550e8400-e29b-41d4-a716-446655440000",
                "fiscal_doc": None,
                "message": "Receipt saved to buffer successfully"
            }
        }


class BufferStatusResponse(BaseModel):
    """
    Buffer status response

    Provides detailed metrics about the offline buffer state.
    """
    total_capacity: int = Field(..., description="Maximum buffer capacity")
    current_queued: int = Field(..., description="Currently queued receipts")
    percent_full: float = Field(..., description="Buffer fullness percentage")
    network_status: Literal['online', 'offline', 'degraded'] = Field(..., description="Network state")
    total_receipts: int = Field(..., description="Total receipts in buffer")
    pending: int = Field(..., description="Pending receipts")
    synced: int = Field(..., description="Synced receipts")
    failed: int = Field(..., description="Failed receipts")
    dlq_size: int = Field(..., description="Dead Letter Queue size")

    class Config:
        json_schema_extra = {
            "example": {
                "total_capacity": 200,
                "current_queued": 5,
                "percent_full": 2.5,
                "network_status": "offline",
                "total_receipts": 10,
                "pending": 5,
                "synced": 4,
                "failed": 1,
                "dlq_size": 0
            }
        }


class HealthCheckResponse(BaseModel):
    """
    Health check response

    Returns application health status and component states.
    """
    status: Literal['healthy', 'degraded', 'unhealthy'] = Field(..., description="Overall health status")
    components: dict = Field(..., description="Component health states")
    version: str = Field(default="0.1.0", description="API version")

    class Config:
        json_schema_extra = {
            "example": {
                "status": "healthy",
                "components": {
                    "buffer": {
                        "status": "healthy",
                        "percent_full": 2.5,
                        "dlq_size": 0
                    },
                    "circuit_breaker": {
                        "state": "CLOSED"
                    }
                },
                "version": "0.1.0"
            }
        }
