# -*- coding: utf-8 -*-
"""
Import Log Model - Import Job Logging

Author: AI Agent
Created: 2025-11-27
Task: OPTERP-39
Reference: CLAUDE.md §3.2 (connector_b module)

Purpose:
Model for logging import job errors, warnings, and information.
Supports pagination for large imports.

Business Rules:
- One2many relation to import_job
- Log levels: info, warning, error
- Row number and row data tracking
- Pagination support
"""

from odoo import models, fields, api


class ConnectorImportLog(models.Model):
    """Import Log for Import Job Messages"""

    _name = 'connector.import.log'
    _description = 'Import Log'
    _order = 'create_date desc, id desc'
    _rec_name = 'message'

    # ==================
    # Fields
    # ==================

    # Import Job
    job_id = fields.Many2one(
        comodel_name='connector.import.job',
        string='Import Job',
        required=True,
        ondelete='cascade',
        index=True,
        help='Import job this log belongs to'
    )

    # Log Level
    level = fields.Selection(
        selection=[
            ('info', 'Info'),
            ('warning', 'Warning'),
            ('error', 'Error'),
        ],
        string='Level',
        required=True,
        default='info',
        help='Log level'
    )

    # Message
    message = fields.Text(
        string='Message',
        required=True,
        help='Log message'
    )

    # Row Information
    row_number = fields.Integer(
        string='Row Number',
        help='Row number in file (0 = general message)'
    )

    row_data = fields.Text(
        string='Row Data',
        help='Row data (JSON format)'
    )

    # Timestamp
    create_date = fields.Datetime(
        string='Date',
        readonly=True,
        help='Log entry creation date'
    )

    # ==================
    # SQL Constraints
    # ==================

    _sql_constraints = [
        (
            'check_row_number_positive',
            'CHECK (row_number >= 0)',
            'Row number must be ≥ 0'
        ),
    ]
