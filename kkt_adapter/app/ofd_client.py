"""
Mock OFD Client for Testing

Author: AI Agent
Created: 2025-10-08
Purpose: Mock OFD API client for Circuit Breaker testing

Note: Real OFD client implementation will come in Phase 2 (OPTERP-12)

This mock client allows testing Circuit Breaker behavior without
actual OFD service integration.
"""

import logging
import time
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class OFDClientError(Exception):
    """OFD client error"""
    pass


class OFDClient:
    """
    Mock OFD Client for testing Circuit Breaker

    Real implementation will be added in Phase 2.

    For testing, this client can be configured to fail on demand.
    """

    def __init__(self, base_url: str = "https://ofd.example.com"):
        """
        Initialize OFD Client

        Args:
            base_url: Base URL for OFD API (not used in mock)
        """
        self.base_url = base_url
        self._fail_next = False  # For testing
        self._call_count = 0

    def send_receipt(self, receipt_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Send receipt to OFD

        Args:
            receipt_data: Receipt data to send

        Returns:
            OFD response with fiscal document

        Raises:
            OFDClientError: OFD unavailable or error
        """
        self._call_count += 1

        # Simulate network delay
        time.sleep(0.1)

        # For testing: simulate failure if flag set
        if self._fail_next:
            logger.error("OFD Client: Simulated failure")
            raise OFDClientError("OFD service unavailable")

        # Mock successful response
        logger.info(f"OFD Client: Receipt sent successfully for POS {receipt_data.get('pos_id')}")

        return {
            "fiscal_doc_number": f"FD-{self._call_count}",
            "fiscal_doc_datetime": "2025-10-08T12:00:00Z",
            "fiscal_sign": f"FS{self._call_count:010d}",
            "status": "accepted",
            "ofd_receipt_url": f"https://ofd.example.com/receipt/{self._call_count}"
        }

    def set_fail_next(self, fail: bool = True):
        """
        Set flag to fail next request (for testing)

        Args:
            fail: If True, next call will raise OFDClientError
        """
        self._fail_next = fail

    def get_call_count(self) -> int:
        """Get number of calls made"""
        return self._call_count


# Global instance
_ofd_client: Optional[OFDClient] = None


def get_ofd_client() -> OFDClient:
    """
    Get global OFD client instance

    Returns singleton instance of OFDClient.
    """
    global _ofd_client
    if _ofd_client is None:
        _ofd_client = OFDClient()
    return _ofd_client


def reset_ofd_client():
    """Reset global OFD client (for testing)"""
    global _ofd_client
    _ofd_client = None
