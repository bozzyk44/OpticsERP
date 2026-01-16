# -*- coding: utf-8 -*-
"""
KKT Adapter API Controller - Odoo ↔ KKT Adapter Communication

Author: AI Agent
Created: 2025-11-27
Task: OPTERP-45 (partial)
Reference: CLAUDE.md §3.2 (optics_pos_ru54fz module)

Purpose:
Controller for proxying requests between Odoo POS and KKT adapter.
Provides endpoints for buffer status, fiscal printing, and reports.

Endpoints:
- /pos/kkt/buffer_status — GET buffer status for offline indicator
- /pos/kkt/print_receipt — POST fiscal receipt printing (2-phase)
- /pos/kkt/check_refund — POST check if refund allowed (Saga pattern)
- /pos/kkt/x_report — POST X-report
- /pos/kkt/z_report — POST Z-report
"""

from odoo import http
from odoo.http import request
import requests
import logging

_logger = logging.getLogger(__name__)


class KKTAdapterController(http.Controller):
    """Controller for KKT adapter communication"""

    def _get_kkt_adapter_url(self):
        """Get KKT adapter URL from POS config"""
        # Get current POS session
        pos_session = request.env['pos.session'].sudo().search([
            ('state', '=', 'opened'),
            ('user_id', '=', request.env.user.id),
        ], limit=1)

        if not pos_session:
            _logger.warning("No open POS session found for current user")
            return None

        # Get KKT adapter URL from config
        kkt_adapter_url = pos_session.config_id.kkt_adapter_url

        if not kkt_adapter_url:
            _logger.warning("KKT adapter URL not configured in POS config")
            return None

        return kkt_adapter_url.rstrip('/')

    @http.route('/pos/kkt/buffer_status', type='json', auth='user', methods=['POST'])
    def get_buffer_status(self):
        """
        Get buffer status from KKT adapter

        Returns:
        {
            'buffer_percent': 12.5,
            'buffer_count': 15,
            'network_status': 'online',  # 'online', 'offline'
            'cb_state': 'CLOSED',  # 'CLOSED', 'OPEN', 'HALF_OPEN'
        }
        """
        try:
            kkt_adapter_url = self._get_kkt_adapter_url()

            if not kkt_adapter_url:
                return {
                    'buffer_percent': 0,
                    'buffer_count': 0,
                    'network_status': 'unknown',
                    'cb_state': 'unknown',
                    'error': 'KKT adapter URL not configured',
                }

            # Call KKT adapter API
            response = requests.get(
                f"{kkt_adapter_url}/v1/kkt/buffer/status",
                timeout=5,
            )

            response.raise_for_status()
            data = response.json()

            return {
                'buffer_percent': data.get('buffer_percent', 0),
                'buffer_count': data.get('buffer_count', 0),
                'network_status': data.get('network_status', 'unknown'),
                'cb_state': data.get('cb_state', 'unknown'),
            }

        except requests.Timeout:
            _logger.error("KKT adapter timeout")
            return {
                'buffer_percent': 0,
                'buffer_count': 0,
                'network_status': 'offline',
                'cb_state': 'unknown',
                'error': 'Request timeout',
            }

        except requests.RequestException as e:
            _logger.exception(f"Failed to get buffer status: {e}")
            return {
                'buffer_percent': 0,
                'buffer_count': 0,
                'network_status': 'offline',
                'cb_state': 'unknown',
                'error': str(e),
            }

        except Exception as e:
            _logger.exception(f"Unexpected error: {e}")
            return {
                'buffer_percent': 0,
                'buffer_count': 0,
                'network_status': 'unknown',
                'cb_state': 'unknown',
                'error': str(e),
            }

    @http.route('/pos/kkt/print_receipt', type='json', auth='user', methods=['POST'])
    def print_receipt(self, receipt_data):
        """
        Print fiscal receipt via KKT adapter (2-phase fiscalization)

        Args:
            receipt_data (dict): Receipt data (items, totals, payment, etc.)

        Returns:
            dict: {
                'success': True/False,
                'fiscal_doc': {...},  # Fiscal document data
                'error': 'Error message' (if failed),
            }
        """
        try:
            kkt_adapter_url = self._get_kkt_adapter_url()

            if not kkt_adapter_url:
                return {
                    'success': False,
                    'error': 'KKT adapter URL not configured',
                }

            # Call KKT adapter API
            response = requests.post(
                f"{kkt_adapter_url}/v1/kkt/receipt",
                json=receipt_data,
                timeout=10,
            )

            response.raise_for_status()
            data = response.json()

            return {
                'success': True,
                'fiscal_doc': data.get('fiscal_doc'),
            }

        except requests.RequestException as e:
            _logger.exception(f"Failed to print receipt: {e}")
            return {
                'success': False,
                'error': str(e),
            }

    @http.route('/pos/kkt/x_report', type='json', auth='user', methods=['POST'])
    def print_x_report(self):
        """
        Print X-report (shift report without closing)

        Returns:
            dict: {
                'success': True/False,
                'report_data': {...},
                'error': 'Error message' (if failed),
            }
        """
        try:
            kkt_adapter_url = self._get_kkt_adapter_url()

            if not kkt_adapter_url:
                return {
                    'success': False,
                    'error': 'KKT adapter URL not configured',
                }

            # Call KKT adapter API
            response = requests.post(
                f"{kkt_adapter_url}/v1/kkt/x_report",
                timeout=10,
            )

            response.raise_for_status()
            data = response.json()

            return {
                'success': True,
                'report_data': data,
            }

        except requests.RequestException as e:
            _logger.exception(f"Failed to print X-report: {e}")
            return {
                'success': False,
                'error': str(e),
            }

    @http.route('/pos/kkt/z_report', type='json', auth='user', methods=['POST'])
    def print_z_report(self):
        """
        Print Z-report (shift close report)

        Returns:
            dict: {
                'success': True/False,
                'report_data': {...},
                'error': 'Error message' (if failed),
            }
        """
        try:
            kkt_adapter_url = self._get_kkt_adapter_url()

            if not kkt_adapter_url:
                return {
                    'success': False,
                    'error': 'KKT adapter URL not configured',
                }

            # Call KKT adapter API
            response = requests.post(
                f"{kkt_adapter_url}/v1/kkt/z_report",
                timeout=10,
            )

            response.raise_for_status()
            data = response.json()

            return {
                'success': True,
                'report_data': data,
            }

        except requests.RequestException as e:
            _logger.exception(f"Failed to print Z-report: {e}")
            return {
                'success': False,
                'error': str(e),
            }

    @http.route('/pos/kkt/check_refund', type='json', auth='user', methods=['POST'])
    def check_refund_allowed(self, original_fiscal_doc_id):
        """
        Check if refund is allowed (Saga pattern)

        Args:
            original_fiscal_doc_id (str): Fiscal document ID of original receipt

        Returns:
            dict: {
                'allowed': True/False,
                'reason': 'Reason if blocked',
                'sync_status': 'pending'/'synced'/'not_found',
            }
        """
        try:
            kkt_adapter_url = self._get_kkt_adapter_url()

            if not kkt_adapter_url:
                return {
                    'allowed': False,
                    'reason': 'KKT adapter URL not configured',
                    'sync_status': 'unknown',
                }

            # Call KKT adapter API to check buffer
            response = requests.post(
                f"{kkt_adapter_url}/v1/pos/refund",
                json={'original_fiscal_doc_id': original_fiscal_doc_id},
                timeout=5,
            )

            # HTTP 409 Conflict = refund blocked (original not synced)
            if response.status_code == 409:
                data = response.json()
                return {
                    'allowed': False,
                    'reason': data.get('reason', 'Original receipt not synced to OFD'),
                    'sync_status': 'pending',
                }

            # HTTP 200 OK = refund allowed
            response.raise_for_status()
            data = response.json()

            return {
                'allowed': True,
                'reason': '',
                'sync_status': data.get('sync_status', 'synced'),
            }

        except requests.Timeout:
            _logger.error("KKT adapter timeout during refund check")
            return {
                'allowed': False,
                'reason': 'Connection timeout (KKT adapter not responding)',
                'sync_status': 'unknown',
            }

        except requests.RequestException as e:
            _logger.exception(f"Failed to check refund: {e}")
            return {
                'allowed': False,
                'reason': f'Connection error: {str(e)}',
                'sync_status': 'unknown',
            }

        except Exception as e:
            _logger.exception(f"Unexpected error during refund check: {e}")
            return {
                'allowed': False,
                'reason': f'Unexpected error: {str(e)}',
                'sync_status': 'unknown',
            }
