# -*- coding: utf-8 -*-
"""
Import Profile Model - Supplier Catalog Import Configuration

Author: AI Agent
Created: 2025-11-27
Task: OPTERP-38
Reference: CLAUDE.md §3.2 (connector_b module)

Purpose:
Model for configuring supplier import profiles with column mapping.
Supports Excel/CSV import with customizable field mappings for 3+ suppliers.

Business Rules:
- Column mapping stored as JSON (flexible schema)
- Each profile is supplier-specific
- Active flag for enabling/disabling profiles
- Supports multiple file formats (XLSX, CSV)
"""

from odoo import models, fields, api
from odoo.exceptions import ValidationError
import json


class ConnectorImportProfile(models.Model):
    """Import Profile for Supplier Catalog Configuration"""

    _name = 'connector.import.profile'
    _description = 'Import Profile'
    _order = 'sequence, name'
    _rec_name = 'name'

    # ==================
    # Fields
    # ==================

    # Basic Information
    name = fields.Char(
        string='Profile Name',
        required=True,
        help='Name of the import profile (e.g., "Essilor Price List")'
    )

    active = fields.Boolean(
        string='Active',
        default=True,
        help='Set to False to disable this profile'
    )

    sequence = fields.Integer(
        string='Sequence',
        default=10,
        help='Sequence for ordering profiles'
    )

    # Supplier Information
    supplier_id = fields.Many2one(
        comodel_name='res.partner',
        string='Supplier',
        domain=[('supplier_rank', '>', 0)],
        help='Supplier associated with this import profile'
    )

    supplier_code = fields.Char(
        string='Supplier Code',
        help='Optional supplier code for identification'
    )

    # File Format
    file_format = fields.Selection(
        selection=[
            ('xlsx', 'Excel (XLSX)'),
            ('csv_utf8', 'CSV (UTF-8)'),
            ('csv_cp1251', 'CSV (Windows-1251)'),
        ],
        string='File Format',
        required=True,
        default='xlsx',
        help='Expected file format for this profile'
    )

    # CSV-specific settings
    csv_delimiter = fields.Char(
        string='CSV Delimiter',
        default=',',
        help='Delimiter for CSV files (e.g., comma, semicolon, tab)'
    )

    csv_quote_char = fields.Char(
        string='CSV Quote Character',
        default='"',
        help='Quote character for CSV fields'
    )

    # Column Mapping (JSON)
    column_mapping = fields.Text(
        string='Column Mapping',
        required=True,
        default='{}',
        help='JSON mapping of file columns to Odoo fields'
    )

    column_mapping_json = fields.Json(
        string='Column Mapping (JSON)',
        compute='_compute_column_mapping_json',
        inverse='_inverse_column_mapping_json',
        store=True,
        help='JSON representation of column mapping'
    )

    # Import Settings
    header_row = fields.Integer(
        string='Header Row',
        default=1,
        help='Row number where headers are located (1-indexed)'
    )

    data_start_row = fields.Integer(
        string='Data Start Row',
        default=2,
        help='Row number where data starts (1-indexed)'
    )

    skip_empty_rows = fields.Boolean(
        string='Skip Empty Rows',
        default=True,
        help='Skip rows with all empty cells'
    )

    # Upsert Configuration
    upsert_field = fields.Selection(
        selection=[
            ('default_code', 'Product Code (default_code)'),
            ('barcode', 'Barcode'),
            ('name', 'Product Name'),
        ],
        string='Upsert Field',
        default='default_code',
        required=True,
        help='Field used to match existing products (for update)'
    )

    create_missing = fields.Boolean(
        string='Create Missing Products',
        default=True,
        help='Create new products if not found (otherwise skip)'
    )

    update_existing = fields.Boolean(
        string='Update Existing Products',
        default=True,
        help='Update existing products if found'
    )

    # Validation Rules
    validation_rules = fields.Text(
        string='Validation Rules',
        help='JSON configuration for validation rules (optional)'
    )

    # Additional Information
    notes = fields.Text(
        string='Notes',
        help='Additional notes about this import profile'
    )

    # Statistics
    job_count = fields.Integer(
        string='Import Jobs',
        compute='_compute_job_count',
        help='Number of import jobs using this profile'
    )

    last_import_date = fields.Datetime(
        string='Last Import',
        compute='_compute_last_import_date',
        help='Date of last successful import'
    )

    # ==================
    # Computed Methods
    # ==================

    @api.depends('column_mapping')
    def _compute_column_mapping_json(self):
        """Convert column_mapping text to JSON"""
        for record in self:
            if record.column_mapping:
                try:
                    record.column_mapping_json = json.loads(record.column_mapping)
                except (json.JSONDecodeError, TypeError):
                    record.column_mapping_json = {}
            else:
                record.column_mapping_json = {}

    def _inverse_column_mapping_json(self):
        """Convert JSON back to text"""
        for record in self:
            if record.column_mapping_json:
                record.column_mapping = json.dumps(record.column_mapping_json, ensure_ascii=False, indent=2)
            else:
                record.column_mapping = '{}'

    def _compute_job_count(self):
        """Count import jobs using this profile"""
        for record in self:
            record.job_count = self.env['connector.import.job'].search_count([
                ('profile_id', '=', record.id)
            ])

    def _compute_last_import_date(self):
        """Get date of last successful import"""
        for record in self:
            last_job = self.env['connector.import.job'].search([
                ('profile_id', '=', record.id),
                ('state', '=', 'done'),
            ], order='end_date desc', limit=1)

            record.last_import_date = last_job.end_date if last_job else False

    # ==================
    # Validation Methods
    # ==================

    @api.constrains('header_row', 'data_start_row')
    def _check_row_numbers(self):
        """Validate row numbers"""
        for record in self:
            if record.header_row < 1:
                raise ValidationError("Header row must be ≥ 1")
            if record.data_start_row < 1:
                raise ValidationError("Data start row must be ≥ 1")
            if record.data_start_row <= record.header_row:
                raise ValidationError(
                    f"Data start row ({record.data_start_row}) must be after "
                    f"header row ({record.header_row})"
                )

    @api.constrains('column_mapping')
    def _check_column_mapping_json(self):
        """Validate that column_mapping is valid JSON"""
        for record in self:
            if record.column_mapping:
                try:
                    mapping = json.loads(record.column_mapping)
                    if not isinstance(mapping, dict):
                        raise ValidationError("Column mapping must be a JSON object (dict)")
                except json.JSONDecodeError as e:
                    raise ValidationError(f"Invalid JSON in column mapping: {e}")

    @api.constrains('csv_delimiter')
    def _check_csv_delimiter(self):
        """Validate CSV delimiter"""
        for record in self:
            if record.file_format in ('csv_utf8', 'csv_cp1251'):
                if not record.csv_delimiter:
                    raise ValidationError("CSV delimiter is required for CSV format")
                if len(record.csv_delimiter) > 1:
                    # Allow special cases like '\t'
                    if record.csv_delimiter not in ('\\t', '\\n', '\\r'):
                        raise ValidationError("CSV delimiter must be a single character")

    # ==================
    # Business Methods
    # ==================

    def get_column_mapping_dict(self):
        """Get column mapping as Python dict"""
        self.ensure_one()
        if self.column_mapping:
            try:
                return json.loads(self.column_mapping)
            except (json.JSONDecodeError, TypeError):
                return {}
        return {}

    def set_column_mapping_dict(self, mapping):
        """Set column mapping from Python dict"""
        self.ensure_one()
        if not isinstance(mapping, dict):
            raise ValueError("Mapping must be a dictionary")
        self.column_mapping = json.dumps(mapping, ensure_ascii=False, indent=2)

    def action_view_import_jobs(self):
        """Open import jobs for this profile"""
        self.ensure_one()
        return {
            'name': f'Import Jobs - {self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'connector.import.job',
            'view_mode': 'tree,form',
            'domain': [('profile_id', '=', self.id)],
            'context': {'default_profile_id': self.id},
        }

    def get_mapping_summary(self):
        """Get formatted mapping summary"""
        self.ensure_one()
        mapping = self.get_column_mapping_dict()

        lines = []
        lines.append(f"Profile: {self.name}")
        lines.append(f"Format: {dict(self._fields['file_format'].selection).get(self.file_format)}")
        lines.append(f"Upsert Field: {dict(self._fields['upsert_field'].selection).get(self.upsert_field)}")
        lines.append("")
        lines.append("Column Mapping:")

        if mapping:
            for odoo_field, file_column in mapping.items():
                lines.append(f"  {odoo_field} ← {file_column}")
        else:
            lines.append("  (no mappings defined)")

        return "\n".join(lines)

    # ==================
    # CRUD Methods
    # ==================

    def copy(self, default=None):
        """Override copy to append (copy) to name"""
        default = dict(default or {})
        if 'name' not in default:
            default['name'] = f"{self.name} (copy)"
        return super().copy(default)
