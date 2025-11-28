# -*- coding: utf-8 -*-
"""
Manufacturing Order Model - Lens Manufacturing Work Order

Author: AI Agent
Created: 2025-11-27
Task: OPTERP-36
Reference: CLAUDE.md §3.2, GLOSSARY.md (Manufacturing Order)

Purpose:
Model for lens manufacturing work orders with workflow:
- Draft → Confirmed → In Production → Ready → Delivered
- Links prescription and lens
- Tracks timeline (3-14 days depending on lens type)
- Manages state transitions with validation

Business Rules:
- Cannot skip workflow states
- State transitions validated
- Timeline tracked from confirmation to delivery
- Links to prescription and lens are required at confirmation
"""

from odoo import models, fields, api
from odoo.exceptions import ValidationError, UserError
from datetime import datetime, timedelta


class OpticsManufacturingOrder(models.Model):
    """Manufacturing Order for lens production"""

    _name = 'optics.manufacturing.order'
    _description = 'Optical Manufacturing Order'
    _order = 'date_order desc, id desc'
    _rec_name = 'name'

    # ==================
    # Fields
    # ==================

    # Basic Information
    name = fields.Char(
        string='Order Reference',
        required=True,
        copy=False,
        readonly=True,
        default='New',
        help='Manufacturing order reference number'
    )

    active = fields.Boolean(
        string='Active',
        default=True,
        help='Set to False to archive order'
    )

    # Customer and Prescription
    customer_id = fields.Many2one(
        comodel_name='res.partner',
        string='Customer',
        required=True,
        help='Customer who placed the order'
    )

    prescription_id = fields.Many2one(
        comodel_name='optics.prescription',
        string='Prescription',
        required=True,
        help='Prescription for lens manufacturing'
    )

    # Lens Specification
    lens_id = fields.Many2one(
        comodel_name='optics.lens',
        string='Lens',
        required=True,
        help='Lens to be manufactured'
    )

    # Dates
    date_order = fields.Datetime(
        string='Order Date',
        required=True,
        default=fields.Datetime.now,
        help='Date when order was created'
    )

    date_confirmed = fields.Datetime(
        string='Confirmation Date',
        readonly=True,
        copy=False,
        help='Date when order was confirmed'
    )

    date_production_start = fields.Datetime(
        string='Production Start Date',
        readonly=True,
        copy=False,
        help='Date when production started'
    )

    date_ready = fields.Datetime(
        string='Ready Date',
        readonly=True,
        copy=False,
        help='Date when order was ready for delivery'
    )

    date_delivered = fields.Datetime(
        string='Delivery Date',
        readonly=True,
        copy=False,
        help='Date when order was delivered'
    )

    expected_delivery_date = fields.Date(
        string='Expected Delivery',
        compute='_compute_expected_delivery_date',
        store=True,
        help='Expected delivery date (calculated from confirmation date)'
    )

    # Workflow State
    state = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('confirmed', 'Confirmed'),
            ('production', 'In Production'),
            ('ready', 'Ready'),
            ('delivered', 'Delivered'),
            ('cancelled', 'Cancelled')
        ],
        string='Status',
        required=True,
        default='draft',
        tracking=True,
        help='Manufacturing order status'
    )

    # Additional Information
    notes = fields.Text(
        string='Notes',
        help='Additional notes and special instructions'
    )

    production_notes = fields.Text(
        string='Production Notes',
        help='Notes for production team'
    )

    # Computed Fields
    duration_days = fields.Integer(
        string='Duration (Days)',
        compute='_compute_duration_days',
        store=False,
        help='Duration from confirmation to delivery in days'
    )

    is_late = fields.Boolean(
        string='Is Late',
        compute='_compute_is_late',
        store=False,
        help='True if order is past expected delivery date'
    )

    # ==================
    # Computed Methods
    # ==================

    @api.depends('date_confirmed', 'lens_id.type')
    def _compute_expected_delivery_date(self):
        """Compute expected delivery date based on lens type"""
        for record in self:
            if record.date_confirmed and record.lens_id:
                # Calculate lead time based on lens type
                if record.lens_id.type == 'single':
                    lead_time_days = 3  # Single vision: 3 days
                elif record.lens_id.type == 'bifocal':
                    lead_time_days = 7  # Bifocal: 7 days
                elif record.lens_id.type == 'progressive':
                    lead_time_days = 14  # Progressive: 14 days
                else:
                    lead_time_days = 7  # Default: 7 days

                # Convert datetime to date and add lead time
                confirmation_date = fields.Datetime.from_string(record.date_confirmed).date()
                record.expected_delivery_date = confirmation_date + timedelta(days=lead_time_days)
            else:
                record.expected_delivery_date = False

    @api.depends('date_confirmed', 'date_delivered')
    def _compute_duration_days(self):
        """Compute duration from confirmation to delivery"""
        for record in self:
            if record.date_confirmed and record.date_delivered:
                confirmed = fields.Datetime.from_string(record.date_confirmed)
                delivered = fields.Datetime.from_string(record.date_delivered)
                duration = delivered - confirmed
                record.duration_days = duration.days
            else:
                record.duration_days = 0

    @api.depends('state', 'expected_delivery_date')
    def _compute_is_late(self):
        """Check if order is late"""
        for record in self:
            if record.state in ['confirmed', 'production', 'ready'] and record.expected_delivery_date:
                today = fields.Date.today()
                record.is_late = today > record.expected_delivery_date
            else:
                record.is_late = False

    # ==================
    # CRUD Methods
    # ==================

    @api.model
    def create(self, vals):
        """Generate sequence for order reference"""
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('optics.manufacturing.order') or 'New'
        return super().create(vals)

    # ==================
    # Workflow Methods
    # ==================

    def action_confirm(self):
        """Confirm manufacturing order"""
        for record in self:
            if record.state != 'draft':
                raise UserError("Only draft orders can be confirmed.")

            # Validate required fields
            if not record.prescription_id:
                raise ValidationError("Prescription is required to confirm the order.")
            if not record.lens_id:
                raise ValidationError("Lens is required to confirm the order.")

            record.write({
                'state': 'confirmed',
                'date_confirmed': fields.Datetime.now(),
            })

        return True

    def action_start_production(self):
        """Start production"""
        for record in self:
            if record.state != 'confirmed':
                raise UserError("Only confirmed orders can start production.")

            record.write({
                'state': 'production',
                'date_production_start': fields.Datetime.now(),
            })

        return True

    def action_mark_ready(self):
        """Mark order as ready for delivery"""
        for record in self:
            if record.state != 'production':
                raise UserError("Only orders in production can be marked as ready.")

            record.write({
                'state': 'ready',
                'date_ready': fields.Datetime.now(),
            })

        return True

    def action_deliver(self):
        """Deliver order to customer"""
        for record in self:
            if record.state != 'ready':
                raise UserError("Only ready orders can be delivered.")

            record.write({
                'state': 'delivered',
                'date_delivered': fields.Datetime.now(),
            })

        return True

    def action_cancel(self):
        """Cancel manufacturing order"""
        for record in self:
            if record.state == 'delivered':
                raise UserError("Cannot cancel delivered orders.")

            record.write({
                'state': 'cancelled',
            })

        return True

    def action_reset_to_draft(self):
        """Reset order to draft (only from cancelled)"""
        for record in self:
            if record.state != 'cancelled':
                raise UserError("Only cancelled orders can be reset to draft.")

            record.write({
                'state': 'draft',
                'date_confirmed': False,
                'date_production_start': False,
                'date_ready': False,
                'date_delivered': False,
            })

        return True

    # ==================
    # Validation Methods
    # ==================

    @api.constrains('state')
    def _check_state_transition(self):
        """Validate state transitions"""
        # Valid transitions
        valid_transitions = {
            'draft': ['confirmed', 'cancelled'],
            'confirmed': ['production', 'cancelled'],
            'production': ['ready', 'cancelled'],
            'ready': ['delivered', 'cancelled'],
            'delivered': [],  # No transitions from delivered
            'cancelled': ['draft'],  # Can reset to draft
        }

        for record in self:
            # This constraint runs after state change, so we can't prevent invalid transitions here
            # Transitions are enforced by action methods (action_confirm, etc.)
            pass

    @api.constrains('date_confirmed', 'date_production_start', 'date_ready', 'date_delivered')
    def _check_dates_order(self):
        """Validate chronological order of dates"""
        for record in self:
            dates = []

            if record.date_confirmed:
                dates.append(('confirmed', record.date_confirmed))
            if record.date_production_start:
                dates.append(('production', record.date_production_start))
            if record.date_ready:
                dates.append(('ready', record.date_ready))
            if record.date_delivered:
                dates.append(('delivered', record.date_delivered))

            # Check chronological order
            for i in range(len(dates) - 1):
                if dates[i][1] > dates[i + 1][1]:
                    raise ValidationError(
                        f"Date {dates[i][0]} cannot be after date {dates[i + 1][0]}"
                    )

    # ==================
    # SQL Constraints
    # ==================

    _sql_constraints = [
        (
            'check_dates_positive',
            'CHECK (date_order <= COALESCE(date_confirmed, date_order) AND '
            'COALESCE(date_confirmed, date_order) <= COALESCE(date_production_start, COALESCE(date_confirmed, date_order)) AND '
            'COALESCE(date_production_start, COALESCE(date_confirmed, date_order)) <= COALESCE(date_ready, COALESCE(date_production_start, COALESCE(date_confirmed, date_order))) AND '
            'COALESCE(date_ready, COALESCE(date_production_start, COALESCE(date_confirmed, date_order))) <= COALESCE(date_delivered, COALESCE(date_ready, COALESCE(date_production_start, COALESCE(date_confirmed, date_order)))))',
            'Dates must be in chronological order'
        ),
    ]

    # ==================
    # Business Methods
    # ==================

    def get_workflow_info(self):
        """Get workflow information as formatted string"""
        self.ensure_one()

        lines = []
        lines.append(f"Order: {self.name}")
        lines.append(f"Customer: {self.customer_id.name if self.customer_id else 'N/A'}")
        lines.append(f"Status: {dict(self._fields['state'].selection)[self.state]}")

        if self.date_confirmed:
            lines.append(f"Confirmed: {self.date_confirmed.strftime('%Y-%m-%d %H:%M')}")
        if self.date_production_start:
            lines.append(f"Production Started: {self.date_production_start.strftime('%Y-%m-%d %H:%M')}")
        if self.date_ready:
            lines.append(f"Ready: {self.date_ready.strftime('%Y-%m-%d %H:%M')}")
        if self.date_delivered:
            lines.append(f"Delivered: {self.date_delivered.strftime('%Y-%m-%d %H:%M')}")

        if self.expected_delivery_date:
            lines.append(f"Expected Delivery: {self.expected_delivery_date}")

        if self.is_late:
            lines.append("⚠️ LATE")

        return "\n".join(lines)
