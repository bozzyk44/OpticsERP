# -*- coding: utf-8 -*-
from odoo import models, fields, api


class AccountCashTransfer(models.Model):
    """Cash transfers between accounts (e.g., store cash to collection account)"""
    _name = 'account.cash.transfer'
    _description = 'Cash Transfer'
    _order = 'date desc, id desc'

    name = fields.Char(
        string='Reference',
        required=True,
        default='/',
        readonly=True,
        copy=False
    )
    date = fields.Date(
        string='Date',
        required=True,
        default=fields.Date.context_today
    )
    source_account_id = fields.Many2one(
        'account.account',
        string='Source Account',
        required=True,
        domain=[('account_type', '=', 'asset_cash')]
    )
    destination_account_id = fields.Many2one(
        'account.account',
        string='Destination Account',
        required=True,
        domain=[('account_type', '=', 'asset_cash')]
    )
    amount = fields.Monetary(
        string='Amount',
        required=True,
        currency_field='currency_id'
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        required=True,
        default=lambda self: self.env.company.currency_id
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company
    )
    notes = fields.Text(string='Notes')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('posted', 'Posted'),
        ('cancelled', 'Cancelled')
    ], string='State', default='draft', required=True)
    move_id = fields.Many2one(
        'account.move',
        string='Journal Entry',
        readonly=True,
        copy=False
    )

    @api.model
    def create(self, vals):
        if vals.get('name', '/') == '/':
            vals['name'] = self.env['ir.sequence'].next_by_code('account.cash.transfer') or '/'
        return super().create(vals)

    def action_confirm(self):
        """Confirm the transfer"""
        self.write({'state': 'confirmed'})

    def action_post(self):
        """Create journal entry and post the transfer"""
        # TODO: Implement journal entry creation
        self.write({'state': 'posted'})

    def action_cancel(self):
        """Cancel the transfer"""
        # TODO: Cancel journal entry if exists
        self.write({'state': 'cancelled'})
