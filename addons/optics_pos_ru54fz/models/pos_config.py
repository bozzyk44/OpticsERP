# -*- coding: utf-8 -*-
"""
POS Config Extension - KKT Adapter Configuration

Author: AI Agent
Created: 2025-11-27
Task: OPTERP-46
Reference: CLAUDE.md §3.2 (optics_pos_ru54fz module)

Purpose:
Extend pos.config model to add KKT adapter configuration.
Allows cashiers to configure KKT adapter URL per POS terminal.

Business Rules:
- kkt_adapter_url field (Char, URL format)
- Validation: URL format (http://host:port)
- Default: http://localhost:8000 (local KKT adapter)
- Used by offline_indicator and kkt_adapter_api controller
"""

from odoo import models, fields, api
from odoo.exceptions import ValidationError
import re


class PosConfig(models.Model):
    """POS Configuration Extension for KKT Adapter"""

    _inherit = 'pos.config'

    # ==================
    # Fields
    # ==================

    kkt_adapter_url = fields.Char(
        string='KKT Adapter URL',
        help='URL of KKT adapter service (e.g., http://localhost:8000)',
        default='http://localhost:8000',
    )

    kkt_adapter_enabled = fields.Boolean(
        string='Enable KKT Adapter',
        default=True,
        help='Enable integration with KKT adapter for fiscal printing',
    )

    # Test connection result
    kkt_adapter_status = fields.Char(
        string='Connection Status',
        compute='_compute_kkt_adapter_status',
        help='KKT adapter connection status',
    )

    # ==================
    # Computed Methods
    # ==================

    @api.depends('kkt_adapter_url', 'kkt_adapter_enabled')
    def _compute_kkt_adapter_status(self):
        """Compute KKT adapter connection status"""
        for record in self:
            if not record.kkt_adapter_enabled:
                record.kkt_adapter_status = 'Disabled'
            elif not record.kkt_adapter_url:
                record.kkt_adapter_status = 'Not configured'
            else:
                # Connection status will be tested via action_test_kkt_connection()
                record.kkt_adapter_status = 'Not tested'

    # ==================
    # Validation Methods
    # ==================

    @api.constrains('kkt_adapter_url')
    def _check_kkt_adapter_url(self):
        """Validate KKT adapter URL format"""
        for record in self:
            if record.kkt_adapter_url:
                url = record.kkt_adapter_url.strip()

                # Check URL format (http://host:port or https://host:port)
                url_pattern = r'^https?://[\w\.\-]+(:\d+)?(/.*)?$'

                if not re.match(url_pattern, url):
                    raise ValidationError(_(
                        "Invalid KKT adapter URL format. "
                        "Expected: http://host:port or https://host:port\n"
                        "Example: http://localhost:8000"
                    ))

    # ==================
    # Business Methods
    # ==================

    def action_test_kkt_connection(self):
        """Test connection to KKT adapter"""
        self.ensure_one()

        if not self.kkt_adapter_enabled:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('KKT Adapter Disabled'),
                    'message': _('KKT adapter integration is disabled for this POS.'),
                    'type': 'warning',
                    'sticky': False,
                }
            }

        if not self.kkt_adapter_url:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('URL Not Configured'),
                    'message': _('Please configure KKT adapter URL first.'),
                    'type': 'danger',
                    'sticky': False,
                }
            }

        try:
            import requests

            # Test connection to health endpoint
            url = self.kkt_adapter_url.rstrip('/')
            response = requests.get(f"{url}/v1/health", timeout=5)

            response.raise_for_status()
            data = response.json()

            # Success
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Connection Successful'),
                    'message': _('Connected to KKT adapter at %(url)s\nStatus: %(status)s') % {
                        'url': url,
                        'status': data.get("status", "OK")
                    },
                    'type': 'success',
                    'sticky': False,
                }
            }

        except requests.Timeout:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Connection Timeout'),
                    'message': _('KKT adapter at %(url)s is not responding (timeout 5s).') % {
                        'url': self.kkt_adapter_url
                    },
                    'type': 'danger',
                    'sticky': True,
                }
            }

        except requests.RequestException as e:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Connection Failed'),
                    'message': _('Failed to connect to KKT adapter:\n%(error)s') % {
                        'error': str(e)
                    },
                    'type': 'danger',
                    'sticky': True,
                }
            }

        except Exception as e:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Error'),
                    'message': _('Unexpected error:\n%(error)s') % {
                        'error': str(e)
                    },
                    'type': 'danger',
                    'sticky': True,
                }
            }

    def get_kkt_adapter_url(self):
        """Get KKT adapter URL (convenience method)"""
        self.ensure_one()
        if self.kkt_adapter_enabled and self.kkt_adapter_url:
            return self.kkt_adapter_url.rstrip('/')
        return None
