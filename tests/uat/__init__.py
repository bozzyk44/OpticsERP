"""
UAT (User Acceptance Testing) Package

Author: AI Agent
Created: 2025-11-29
Task: OPTERP-50

UAT Tests:
- UAT-01: Sale with prescription
- UAT-02: Refund
- UAT-03: Supplier price import
- UAT-04: X/Z reports
- UAT-08: Offline mode (8h, 50 receipts)
- UAT-09: Refund blocked (Saga pattern)
- UAT-10: Buffer overflow handling
- UAT-11: Circuit Breaker OPEN/HALF_OPEN

All tests require real Odoo instance running.
Smoke tests can run without Odoo (KKT adapter only).
"""

__version__ = "1.0.0"
