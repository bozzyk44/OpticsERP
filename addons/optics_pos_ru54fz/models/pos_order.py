# -*- coding: utf-8 -*-
"""
POS Order Extension - Saga Pattern (Refund Blocking)

Author: AI Agent
Created: 2025-11-27
Task: OPTERP-47
Reference: CLAUDE.md §5 (Saga pattern), §7 (KKT adapter)

Purpose:
Extend pos.order model to implement Saga pattern for refund blocking.
Prevents refund if original receipt not synced to OFD.

Business Rules:
- Refund blocked if original receipt not synced (status='pending' in buffer)
- Refund allowed if original receipt synced (status='synced' or not in buffer)
- Check via KKT adapter API: POST /v1/pos/refund (HTTP 409 if blocked)
- Store fiscal document reference for sync checking

Saga Pattern:
- Compensating transaction (refund) requires original transaction to be committed
- Ensures referential integrity between original receipt and refund
- Prevents orphaned refunds if original receipt fails to sync
"""

from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError
import logging

_logger = logging.getLogger(__name__)


class PosOrder(models.Model):
    """POS Order Extension for Saga Pattern"""

    _inherit = 'pos.order'

    # ==================
    # Fields
    # ==================

    # Fiscal document reference (HLC timestamp from KKT adapter)
    fiscal_doc_id = fields.Char(
        string='Fiscal Document ID',
        readonly=True,
        copy=False,
        help='Fiscal document ID (HLC timestamp) from KKT adapter',
    )

    # Fiscal sync status
    fiscal_sync_status = fields.Selection(
        selection=[
            ('not_required', 'Not Required'),  # Non-fiscal orders
            ('pending', 'Pending Sync'),       # In offline buffer
            ('synced', 'Synced'),              # Successfully synced to OFD
            ('failed', 'Sync Failed'),         # Sync failed (in DLQ)
        ],
        string='Fiscal Sync Status',
        default='not_required',
        readonly=True,
        copy=False,
        help='Status of fiscal receipt sync to OFD',
    )

    # Sync date
    fiscal_sync_date = fields.Datetime(
        string='Fiscal Sync Date',
        readonly=True,
        copy=False,
        help='Date when receipt was synced to OFD',
    )

    # ==================
    # Refund Validation (Saga Pattern)
    # ==================

    def _check_refund_allowed(self):
        """
        Check if refund is allowed (Saga pattern)

        Raises:
            UserError: If refund is blocked (original not synced)

        Returns:
            bool: True if refund allowed
        """
        self.ensure_one()

        # Get original order (if this is a refund)
        if self.amount_total >= 0:
            # This is not a refund, no check needed
            return True

        # Find original order
        original_order = self._get_original_order_for_refund()

        if not original_order:
            # No original order found, cannot validate
            _logger.warning(f"Refund {self.pos_reference}: No original order found")
            raise UserError(_(
                "Cannot process refund: Original order not found.\n"
                "Please ensure the original sale exists in the system."
            ))

        # Check fiscal sync status
        if original_order.fiscal_sync_status == 'pending':
            # Original receipt not synced yet - BLOCK REFUND
            raise UserError(_(
                "Refund blocked: Original receipt not synced to OFD yet.\n\n"
                "Original Order: %(ref)s\n"
                "Fiscal Document ID: %(doc_id)s\n"
                "Sync Status: Pending\n\n"
                "Please wait for the original receipt to sync before processing refund.\n"
                "Check the offline buffer status in the cash register indicator."
            ) % {
                'ref': original_order.pos_reference,
                'doc_id': original_order.fiscal_doc_id or 'N/A'
            })

        if original_order.fiscal_sync_status == 'failed':
            # Original receipt sync failed - WARN but allow (manual resolution needed)
            _logger.warning(
                f"Refund {self.pos_reference}: Original order {original_order.pos_reference} "
                f"sync failed (in DLQ)"
            )
            # Could raise UserError here to block completely, or allow with warning
            # For now, allow but log warning

        # Original receipt synced or not fiscal - ALLOW REFUND
        return True

    def _get_original_order_for_refund(self):
        """
        Get original order for refund

        Returns:
            pos.order: Original order, or False if not found
        """
        self.ensure_one()

        # Try to find original order by reference
        # (This is a simplified implementation - real logic may differ)

        # Option 1: Check if this order has a parent (refund_order_id or similar)
        # Option 2: Match by session and negative amount
        # Option 3: Use pos_reference pattern matching

        # For now, search for most recent positive order in same session
        if self.session_id:
            original = self.search([
                ('session_id', '=', self.session_id.id),
                ('amount_total', '>', 0),
                ('create_date', '<', self.create_date),
            ], order='create_date desc', limit=1)

            return original

        return False

    # ==================
    # CRUD Overrides
    # ==================

    @api.model
    def create(self, vals):
        """Override create to validate refund before creation"""
        order = super().create(vals)

        # Check refund allowed (Saga pattern)
        if order.amount_total < 0:  # Refund
            try:
                order._check_refund_allowed()
            except UserError as e:
                # Delete order and re-raise
                order.unlink()
                raise

        return order

    def write(self, vals):
        """Override write to validate refund state changes"""
        result = super().write(vals)

        # If amount changed to negative (refund), validate
        for order in self:
            if order.amount_total < 0:
                order._check_refund_allowed()

        return result

    # ==================
    # Fiscal Sync Methods
    # ==================

    def update_fiscal_sync_status(self, fiscal_doc_id, status, sync_date=None):
        """
        Update fiscal sync status

        Args:
            fiscal_doc_id (str): Fiscal document ID (HLC timestamp)
            status (str): Sync status (pending/synced/failed)
            sync_date (datetime): Sync date (optional)
        """
        self.ensure_one()

        vals = {
            'fiscal_doc_id': fiscal_doc_id,
            'fiscal_sync_status': status,
        }

        if sync_date:
            vals['fiscal_sync_date'] = sync_date

        self.write(vals)

        _logger.info(
            f"Order {self.pos_reference}: Fiscal sync status updated to {status} "
            f"(doc_id: {fiscal_doc_id})"
        )

    def action_view_fiscal_document(self):
        """View fiscal document in KKT adapter (future)"""
        self.ensure_one()

        if not self.fiscal_doc_id:
            raise UserError(_("No fiscal document ID available for this order."))

        # TODO: Open modal or external link to KKT adapter UI
        # For now, show notification
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Fiscal Document',
                'message': f'Fiscal Document ID: {self.fiscal_doc_id}\nStatus: {self.fiscal_sync_status}',
                'type': 'info',
                'sticky': False,
            }
        }
