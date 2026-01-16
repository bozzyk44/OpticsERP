"""
OFD Client with Mock and HTTP Modes

Author: AI Agent
Created: 2025-10-08
Updated: 2025-10-09 (OPTERP-13)
Purpose: OFD API client with support for both mock and real HTTP modes

Modes:
- mock_mode=True: Internal mock for unit tests (fast, no network)
- mock_mode=False: Real HTTP calls to OFD server (integration tests)
"""

import logging
import time
import requests
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class OFDClientError(Exception):
    """OFD client error"""
    pass


class OFDClient:
    """
    OFD Client with Mock and HTTP modes

    Modes:
    - mock_mode=True: Internal mock for unit tests (fast, no network)
    - mock_mode=False: Real HTTP calls to OFD server (integration tests)
    """

    def __init__(
        self,
        base_url: str = "http://localhost:9000",
        mock_mode: bool = True,
        timeout: int = 10
    ):
        """
        Initialize OFD Client

        Args:
            base_url: Base URL for OFD API (used in HTTP mode)
            mock_mode: If True, use internal mock (no network)
            timeout: HTTP request timeout in seconds (default: 10)
        """
        self.base_url = base_url
        self.mock_mode = mock_mode
        self.timeout = timeout
        self._fail_next = False  # For testing (mock mode only)
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

        if self.mock_mode:
            return self._mock_send_receipt(receipt_data)
        else:
            return self._http_send_receipt(receipt_data)

    def _mock_send_receipt(self, receipt_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Mock implementation (for unit tests)

        Args:
            receipt_data: Receipt data to send

        Returns:
            Mock OFD response

        Raises:
            OFDClientError: Simulated failure
        """
        # Simulate network delay
        time.sleep(0.1)

        # For testing: simulate failure if flag set
        if self._fail_next:
            logger.error("OFD Client (mock): Simulated failure")
            raise OFDClientError("OFD service unavailable")

        # Mock successful response
        logger.info(f"OFD Client (mock): Receipt sent successfully for POS {receipt_data.get('pos_id')}")

        return {
            "fiscal_doc_number": f"FD-{self._call_count}",
            "fiscal_doc_datetime": "2025-10-08T12:00:00Z",
            "fiscal_sign": f"FS{self._call_count:010d}",
            "status": "accepted",
            "ofd_receipt_url": f"https://ofd.example.com/receipt/{self._call_count}"
        }

    def _http_send_receipt(self, receipt_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Real HTTP implementation (for integration tests)

        Args:
            receipt_data: Receipt data to send

        Returns:
            OFD API response

        Raises:
            OFDClientError: HTTP error or timeout
        """
        url = f"{self.base_url}/ofd/v1/receipt"

        try:
            response = requests.post(
                url,
                json=receipt_data,
                timeout=self.timeout
            )

            # Check HTTP status
            if response.status_code != 200:
                error_msg = response.json().get("error", "Unknown error")
                logger.error(f"OFD Client (HTTP): Failed with status {response.status_code}: {error_msg}")
                raise OFDClientError(f"OFD returned {response.status_code}: {error_msg}")

            # Success
            logger.info(f"OFD Client (HTTP): Receipt sent successfully for POS {receipt_data.get('pos_id')}")
            return response.json()

        except requests.exceptions.Timeout:
            logger.error(f"OFD Client (HTTP): Request timeout after {self.timeout}s")
            raise OFDClientError(f"OFD request timeout after {self.timeout}s")

        except requests.exceptions.ConnectionError as e:
            logger.error(f"OFD Client (HTTP): Connection error: {e}")
            raise OFDClientError(f"OFD connection error: {e}")

        except requests.exceptions.RequestException as e:
            logger.error(f"OFD Client (HTTP): Request error: {e}")
            raise OFDClientError(f"OFD request error: {e}")

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
    Configuration is read from environment variables:
    - OFD_BASE_URL: Base URL for OFD API (default: http://localhost:9000)
    - OFD_MOCK_MODE: If 'true', use internal mock (default: true)
    - OFD_TIMEOUT: HTTP request timeout in seconds (default: 10)
    """
    import os
    global _ofd_client
    if _ofd_client is None:
        # Read configuration from environment variables
        base_url = os.getenv('OFD_BASE_URL', 'http://localhost:9000')
        mock_mode = os.getenv('OFD_MOCK_MODE', 'true').lower() == 'true'
        timeout = int(os.getenv('OFD_TIMEOUT', '10'))

        logger.info(f"Initializing OFD Client: base_url={base_url}, mock_mode={mock_mode}, timeout={timeout}s")

        _ofd_client = OFDClient(
            base_url=base_url,
            mock_mode=mock_mode,
            timeout=timeout
        )
    return _ofd_client


def reset_ofd_client():
    """Reset global OFD client (for testing)"""
    global _ofd_client
    _ofd_client = None
