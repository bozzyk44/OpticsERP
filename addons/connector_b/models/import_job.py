# -*- coding: utf-8 -*-
"""
Import Job Model - Supplier Catalog Import Execution

Author: AI Agent
Created: 2025-11-27
Task: OPTERP-39
Reference: CLAUDE.md §3.2 (connector_b module)

Purpose:
Model for executing supplier catalog imports from Excel/CSV files.
Implements state machine (draft → running → done/failed) with logging.

Business Rules:
- File upload (binary field)
- State machine workflow with validation
- Logging with pagination (one2many to import_log)
- Upsert mode (create/update products)
- Blocking when offline buffers not synced
"""

from odoo import models, fields, api
from odoo.exceptions import ValidationError, UserError
import base64
import json
import logging
from datetime import datetime

_logger = logging.getLogger(__name__)


class ConnectorImportJob(models.Model):
    """Import Job for Supplier Catalog Import"""

    _name = 'connector.import.job'
    _description = 'Import Job'
    _order = 'start_date desc, id desc'
    _rec_name = 'name'

    # ==================
    # Fields
    # ==================

    # Basic Information
    name = fields.Char(
        string='Job Reference',
        required=True,
        copy=False,
        readonly=True,
        default='New',
        help='Import job reference number'
    )

    active = fields.Boolean(
        string='Active',
        default=True,
        help='Set to False to archive job'
    )

    # Import Profile
    profile_id = fields.Many2one(
        comodel_name='connector.import.profile',
        string='Import Profile',
        required=True,
        readonly=True,
        states={'draft': [('readonly', False)]},
        help='Import profile to use for this job'
    )

    # File Upload
    file_name = fields.Char(
        string='File Name',
        help='Name of uploaded file'
    )

    file_data = fields.Binary(
        string='File',
        required=True,
        readonly=True,
        states={'draft': [('readonly', False)]},
        help='Excel or CSV file to import'
    )

    # State
    state = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('running', 'Running'),
            ('done', 'Done'),
            ('failed', 'Failed'),
            ('cancelled', 'Cancelled'),
        ],
        string='Status',
        required=True,
        default='draft',
        tracking=True,
        help='Import job status'
    )

    # Dates
    start_date = fields.Datetime(
        string='Start Date',
        readonly=True,
        help='Date when import started'
    )

    end_date = fields.Datetime(
        string='End Date',
        readonly=True,
        help='Date when import finished'
    )

    duration = fields.Float(
        string='Duration (seconds)',
        compute='_compute_duration',
        store=False,
        help='Import duration in seconds'
    )

    # Statistics
    total_rows = fields.Integer(
        string='Total Rows',
        readonly=True,
        help='Total number of rows in file (excluding header)'
    )

    processed_rows = fields.Integer(
        string='Processed Rows',
        readonly=True,
        help='Number of rows processed'
    )

    created_count = fields.Integer(
        string='Created',
        readonly=True,
        help='Number of products created'
    )

    updated_count = fields.Integer(
        string='Updated',
        readonly=True,
        help='Number of products updated'
    )

    skipped_count = fields.Integer(
        string='Skipped',
        readonly=True,
        help='Number of rows skipped'
    )

    error_count = fields.Integer(
        string='Errors',
        readonly=True,
        help='Number of rows with errors'
    )

    # Progress
    progress_percent = fields.Float(
        string='Progress (%)',
        compute='_compute_progress_percent',
        store=False,
        help='Import progress percentage'
    )

    # Logs
    log_ids = fields.One2many(
        comodel_name='connector.import.log',
        inverse_name='job_id',
        string='Logs',
        help='Import logs with pagination'
    )

    log_count = fields.Integer(
        string='Log Count',
        compute='_compute_log_count',
        help='Number of log entries'
    )

    # Error Summary
    error_message = fields.Text(
        string='Error Message',
        readonly=True,
        help='Error message if import failed'
    )

    # Additional Information
    notes = fields.Text(
        string='Notes',
        help='Additional notes about this import'
    )

    # ==================
    # Computed Methods
    # ==================

    @api.depends('start_date', 'end_date')
    def _compute_duration(self):
        """Compute import duration in seconds"""
        for record in self:
            if record.start_date and record.end_date:
                delta = record.end_date - record.start_date
                record.duration = delta.total_seconds()
            else:
                record.duration = 0.0

    @api.depends('total_rows', 'processed_rows')
    def _compute_progress_percent(self):
        """Compute progress percentage"""
        for record in self:
            if record.total_rows > 0:
                record.progress_percent = (record.processed_rows / record.total_rows) * 100
            else:
                record.progress_percent = 0.0

    def _compute_log_count(self):
        """Count log entries"""
        for record in self:
            record.log_count = len(record.log_ids)

    # ==================
    # CRUD Methods
    # ==================

    @api.model
    def create(self, vals):
        """Generate sequence for job reference"""
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('connector.import.job') or 'New'
        return super().create(vals)

    # ==================
    # Workflow Methods
    # ==================

    def action_run_import(self):
        """Run import (draft → running → done/failed)"""
        for record in self:
            if record.state != 'draft':
                raise UserError("Only draft jobs can be run.")

            # Check if offline buffers are synced (CLAUDE.md requirement)
            # TODO: Implement buffer sync check when KKT adapter integrated
            # if not self._check_buffer_synced():
            #     raise UserError("Cannot import: offline buffers not synced.")

            try:
                # Set to running
                record.write({
                    'state': 'running',
                    'start_date': fields.Datetime.now(),
                })

                # Run import
                record._do_import()

                # Set to done
                record.write({
                    'state': 'done',
                    'end_date': fields.Datetime.now(),
                })

            except Exception as e:
                # Set to failed
                _logger.exception(f"Import job {record.name} failed: {e}")
                record.write({
                    'state': 'failed',
                    'end_date': fields.Datetime.now(),
                    'error_message': str(e),
                })
                raise

        return True

    def action_cancel(self):
        """Cancel import job"""
        for record in self:
            if record.state in ('done', 'failed'):
                raise UserError("Cannot cancel completed jobs.")

            record.write({
                'state': 'cancelled',
                'end_date': fields.Datetime.now(),
            })

        return True

    def action_reset_to_draft(self):
        """Reset to draft (only from failed/cancelled)"""
        for record in self:
            if record.state not in ('failed', 'cancelled'):
                raise UserError("Only failed or cancelled jobs can be reset.")

            record.write({
                'state': 'draft',
                'start_date': False,
                'end_date': False,
                'total_rows': 0,
                'processed_rows': 0,
                'created_count': 0,
                'updated_count': 0,
                'skipped_count': 0,
                'error_count': 0,
                'error_message': False,
            })

            # Delete logs
            record.log_ids.unlink()

        return True

    # ==================
    # Business Methods
    # ==================

    def _do_import(self):
        """Execute import (main logic)"""
        self.ensure_one()

        if not self.file_data:
            raise ValidationError("File is required for import.")

        if not self.profile_id:
            raise ValidationError("Import profile is required.")

        # Decode file
        file_content = base64.b64decode(self.file_data)

        # Parse file based on format
        rows = self._parse_file(file_content)

        # Update total rows
        self.total_rows = len(rows)

        # Get column mapping
        mapping = self.profile_id.get_column_mapping_dict()

        if not mapping:
            raise ValidationError("Column mapping is empty in import profile.")

        # Import rows
        created = 0
        updated = 0
        skipped = 0
        errors = 0

        for idx, row in enumerate(rows, start=1):
            try:
                result = self._import_row(row, mapping)

                if result == 'created':
                    created += 1
                elif result == 'updated':
                    updated += 1
                elif result == 'skipped':
                    skipped += 1

                # Update progress every 10 rows
                if idx % 10 == 0:
                    self.processed_rows = idx
                    self.env.cr.commit()  # Commit progress

            except Exception as e:
                errors += 1
                self._log_error(idx, row, str(e))

        # Final stats
        self.write({
            'processed_rows': len(rows),
            'created_count': created,
            'updated_count': updated,
            'skipped_count': skipped,
            'error_count': errors,
        })

        _logger.info(
            f"Import {self.name} completed: "
            f"{created} created, {updated} updated, "
            f"{skipped} skipped, {errors} errors"
        )

    def _parse_file(self, file_content):
        """Parse file content based on format"""
        self.ensure_one()

        profile = self.profile_id
        file_format = profile.file_format

        rows = []

        if file_format == 'xlsx':
            rows = self._parse_xlsx(file_content)
        elif file_format in ('csv_utf8', 'csv_cp1251'):
            encoding = 'utf-8' if file_format == 'csv_utf8' else 'cp1251'
            rows = self._parse_csv(file_content, encoding)
        else:
            raise ValidationError(f"Unsupported file format: {file_format}")

        return rows

    def _parse_xlsx(self, file_content):
        """Parse Excel file"""
        import openpyxl
        from io import BytesIO

        profile = self.profile_id
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

    def _parse_csv(self, file_content, encoding):
        """Parse CSV file"""
        import csv
        from io import StringIO

        profile = self.profile_id
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

    def _import_row(self, row, mapping):
        """Import single row (create or update product)"""
        self.ensure_one()

        Product = self.env['product.product']
        profile = self.profile_id

        # Map row to Odoo fields
        vals = {}
        for odoo_field, file_column in mapping.items():
            if file_column in row:
                vals[odoo_field] = row[file_column]

        if not vals:
            return 'skipped'

        # Find existing product
        upsert_field = profile.upsert_field
        upsert_value = vals.get(upsert_field)

        if not upsert_value:
            self._log_warning(0, row, f"Missing upsert field: {upsert_field}")
            return 'skipped'

        existing_product = Product.search([
            (upsert_field, '=', upsert_value)
        ], limit=1)

        if existing_product:
            # Update existing
            if profile.update_existing:
                existing_product.write(vals)
                return 'updated'
            else:
                return 'skipped'
        else:
            # Create new
            if profile.create_missing:
                Product.create(vals)
                return 'created'
            else:
                return 'skipped'

    def _log_error(self, row_number, row, message):
        """Log error"""
        self.env['connector.import.log'].create({
            'job_id': self.id,
            'row_number': row_number,
            'level': 'error',
            'message': message,
            'row_data': json.dumps(row, ensure_ascii=False),
        })

    def _log_warning(self, row_number, row, message):
        """Log warning"""
        self.env['connector.import.log'].create({
            'job_id': self.id,
            'row_number': row_number,
            'level': 'warning',
            'message': message,
            'row_data': json.dumps(row, ensure_ascii=False),
        })

    def action_view_logs(self):
        """Open logs for this job"""
        self.ensure_one()
        return {
            'name': f'Import Logs - {self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'connector.import.log',
            'view_mode': 'tree,form',
            'domain': [('job_id', '=', self.id)],
            'context': {'default_job_id': self.id},
        }

    def get_summary(self):
        """Get formatted import summary"""
        self.ensure_one()

        lines = []
        lines.append(f"Job: {self.name}")
        lines.append(f"Profile: {self.profile_id.name}")
        lines.append(f"Status: {dict(self._fields['state'].selection)[self.state]}")
        lines.append("")

        if self.start_date:
            lines.append(f"Started: {self.start_date.strftime('%Y-%m-%d %H:%M:%S')}")
        if self.end_date:
            lines.append(f"Finished: {self.end_date.strftime('%Y-%m-%d %H:%M:%S')}")
        if self.duration > 0:
            lines.append(f"Duration: {self.duration:.2f}s")

        lines.append("")
        lines.append(f"Total Rows: {self.total_rows}")
        lines.append(f"Processed: {self.processed_rows}")
        lines.append(f"Created: {self.created_count}")
        lines.append(f"Updated: {self.updated_count}")
        lines.append(f"Skipped: {self.skipped_count}")
        lines.append(f"Errors: {self.error_count}")

        if self.error_message:
            lines.append("")
            lines.append(f"Error: {self.error_message}")

        return "\n".join(lines)
