# -*- coding: utf-8 -*-
"""
Import Wizard - Supplier Catalog Import Wizard

Author: AI Agent
Created: 2025-11-27
Task: OPTERP-43
Reference: CLAUDE.md §3.2 (connector_b module)

Purpose:
Wizard for importing supplier catalogs with file upload and preview.
Allows user to select profile, upload file, preview data, and confirm import.

Business Rules:
- File upload (binary field)
- Profile selection (many2one)
- Preview first 10 rows before import
- Confirm button triggers import job creation
"""

from odoo import models, fields, api
from odoo.exceptions import ValidationError
import base64
import logging

_logger = logging.getLogger(__name__)


class ConnectorImportWizard(models.TransientModel):
    """Import Wizard for Supplier Catalog Import"""

    _name = 'connector.import.wizard'
    _description = 'Import Wizard'

    # ==================
    # Fields
    # ==================

    # Import Profile
    profile_id = fields.Many2one(
        comodel_name='connector.import.profile',
        string='Import Profile',
        required=True,
        domain=[('active', '=', True)],
        help='Select import profile to use'
    )

    # File Upload
    file_name = fields.Char(
        string='File Name',
        help='Name of uploaded file'
    )

    file_data = fields.Binary(
        string='File',
        required=True,
        help='Excel or CSV file to import'
    )

    # Preview
    preview_data = fields.Text(
        string='Preview Data',
        compute='_compute_preview_data',
        help='Preview of first 10 rows'
    )

    show_preview = fields.Boolean(
        string='Show Preview',
        default=False,
        help='Toggle preview display'
    )

    # ==================
    # Computed Methods
    # ==================

    @api.depends('file_data', 'profile_id')
    def _compute_preview_data(self):
        """Compute preview of first 10 rows"""
        for record in self:
            if not record.file_data or not record.profile_id:
                record.preview_data = ''
                continue

            try:
                # Parse file
                file_content = base64.b64decode(record.file_data)
                profile = record.profile_id
                file_format = profile.file_format

                rows = []

                if file_format == 'xlsx':
                    rows = record._parse_xlsx_preview(file_content, profile)
                elif file_format in ('csv_utf8', 'csv_cp1251'):
                    encoding = 'utf-8' if file_format == 'csv_utf8' else 'cp1251'
                    rows = record._parse_csv_preview(file_content, profile, encoding)

                # Format preview (first 10 rows)
                preview_lines = []
                preview_lines.append(f"Profile: {profile.name}")
                preview_lines.append(f"Format: {dict(profile._fields['file_format'].selection).get(file_format)}")
                preview_lines.append(f"Total Rows: {len(rows)}")
                preview_lines.append("")
                preview_lines.append("First 10 Rows:")
                preview_lines.append("-" * 80)

                for idx, row in enumerate(rows[:10], start=1):
                    preview_lines.append(f"Row {idx}:")
                    for key, value in row.items():
                        preview_lines.append(f"  {key}: {value}")
                    preview_lines.append("")

                if len(rows) > 10:
                    preview_lines.append(f"... and {len(rows) - 10} more rows")

                record.preview_data = "\n".join(preview_lines)

            except Exception as e:
                _logger.exception(f"Error parsing preview: {e}")
                record.preview_data = f"Error: {str(e)}"

    def _parse_xlsx_preview(self, file_content, profile):
        """Parse Excel file for preview"""
        import openpyxl
        from io import BytesIO

        wb = openpyxl.load_workbook(BytesIO(file_content), data_only=True)
        sheet = wb.active

        rows = []
        headers = []

        for idx, row in enumerate(sheet.iter_rows(values_only=True), start=1):
            if idx == profile.header_row:
                headers = [str(cell) if cell else '' for cell in row]
            elif idx >= profile.data_start_row:
                # Skip empty rows
                if profile.skip_empty_rows and all(cell is None or cell == '' for cell in row):
                    continue

                # Convert row to dict
                row_dict = {}
                for col_idx, cell in enumerate(row):
                    if col_idx < len(headers):
                        row_dict[headers[col_idx]] = cell

                rows.append(row_dict)

        return rows

    def _parse_csv_preview(self, file_content, profile, encoding):
        """Parse CSV file for preview"""
        import csv
        from io import StringIO

        text_content = file_content.decode(encoding)
        reader = csv.reader(
            StringIO(text_content),
            delimiter=profile.csv_delimiter,
            quotechar=profile.csv_quote_char,
        )

        rows = []
        headers = []

        for idx, row in enumerate(reader, start=1):
            if idx == profile.header_row:
                headers = [str(cell).strip() for cell in row]
            elif idx >= profile.data_start_row:
                # Skip empty rows
                if profile.skip_empty_rows and all(cell == '' for cell in row):
                    continue

                # Convert row to dict
                row_dict = {}
                for col_idx, cell in enumerate(row):
                    if col_idx < len(headers):
                        row_dict[headers[col_idx]] = cell.strip()

                rows.append(row_dict)

        return rows

    # ==================
    # Wizard Actions
    # ==================

    def action_preview(self):
        """Show preview"""
        self.ensure_one()
        self.show_preview = True
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'connector.import.wizard',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'new',
        }

    def action_import(self):
        """Create import job and run import"""
        self.ensure_one()

        if not self.file_data:
            raise ValidationError("Please upload a file.")

        if not self.profile_id:
            raise ValidationError("Please select an import profile.")

        # Create import job
        job = self.env['connector.import.job'].create({
            'profile_id': self.profile_id.id,
            'file_name': self.file_name,
            'file_data': self.file_data,
        })

        # Run import
        job.action_run_import()

        # Return action to view created job
        return {
            'name': 'Import Job',
            'type': 'ir.actions.act_window',
            'res_model': 'connector.import.job',
            'view_mode': 'form',
            'res_id': job.id,
            'target': 'current',
        }

    def action_cancel(self):
        """Cancel wizard"""
        return {'type': 'ir.actions.act_window_close'}
