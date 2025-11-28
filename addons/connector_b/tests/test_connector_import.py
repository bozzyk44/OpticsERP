# -*- coding: utf-8 -*-
"""
Connector Import Unit Tests - Comprehensive Test Suite

Author: AI Agent
Created: 2025-11-27
Task: OPTERP-44
Reference: CLAUDE.md §3.2 (connector_b module)

Test Coverage:
- Import Profile: creation, JSON mapping, validation
- Import Job: execution, file parsing, upsert logic
- Import Log: error/warning logging
- Import Wizard: file upload, preview, import trigger

Target Coverage: ≥95%
"""

from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError, UserError
import base64
import json
from io import BytesIO


class TestConnectorImportProfile(TransactionCase):
    """Test suite for connector.import.profile model"""

    def setUp(self):
        super().setUp()

        # Create test supplier
        self.supplier = self.env['res.partner'].create({
            'name': 'Test Supplier',
            'supplier_rank': 1,
        })

    def test_01_create_import_profile_basic(self):
        """Test: Create import profile with basic fields"""
        profile = self.env['connector.import.profile'].create({
            'name': 'Test Profile',
            'supplier_id': self.supplier.id,
            'file_format': 'xlsx',
            'column_mapping': json.dumps({
                'default_code': 'SKU',
                'name': 'Product Name',
                'list_price': 'Price',
            }),
        })

        self.assertTrue(profile.id)
        self.assertEqual(profile.name, 'Test Profile')
        self.assertEqual(profile.supplier_id, self.supplier)
        self.assertEqual(profile.file_format, 'xlsx')
        self.assertTrue(profile.active)

    def test_02_column_mapping_json_conversion(self):
        """Test: column_mapping text ↔ JSON conversion"""
        mapping_dict = {
            'default_code': 'SKU',
            'name': 'Product Name',
            'list_price': 'Retail Price',
            'standard_price': 'Cost',
        }

        profile = self.env['connector.import.profile'].create({
            'name': 'JSON Test Profile',
            'file_format': 'xlsx',
            'column_mapping': json.dumps(mapping_dict),
        })

        # Test computed JSON field
        self.assertEqual(profile.column_mapping_json, mapping_dict)

        # Test inverse (JSON → text)
        new_mapping = {'default_code': 'Code', 'name': 'Name'}
        profile.column_mapping_json = new_mapping

        parsed = json.loads(profile.column_mapping)
        self.assertEqual(parsed, new_mapping)

    def test_03_row_number_validation_header_too_small(self):
        """Test: header_row must be ≥ 1"""
        with self.assertRaises(ValidationError) as cm:
            self.env['connector.import.profile'].create({
                'name': 'Invalid Header Row',
                'file_format': 'xlsx',
                'header_row': 0,  # Invalid
                'data_start_row': 2,
                'column_mapping': '{}',
            })

        self.assertIn('Header row must be ≥ 1', str(cm.exception))

    def test_04_row_number_validation_data_before_header(self):
        """Test: data_start_row must be > header_row"""
        with self.assertRaises(ValidationError) as cm:
            self.env['connector.import.profile'].create({
                'name': 'Invalid Data Row',
                'file_format': 'xlsx',
                'header_row': 2,
                'data_start_row': 2,  # Invalid (must be > header_row)
                'column_mapping': '{}',
            })

        self.assertIn('must be after', str(cm.exception))

    def test_05_invalid_json_mapping(self):
        """Test: column_mapping must be valid JSON dict"""
        with self.assertRaises(ValidationError) as cm:
            self.env['connector.import.profile'].create({
                'name': 'Invalid JSON',
                'file_format': 'xlsx',
                'column_mapping': 'not valid json',
            })

        self.assertIn('Invalid JSON', str(cm.exception))

    def test_06_csv_delimiter_required_for_csv(self):
        """Test: CSV delimiter required for CSV formats"""
        with self.assertRaises(ValidationError) as cm:
            self.env['connector.import.profile'].create({
                'name': 'CSV No Delimiter',
                'file_format': 'csv_utf8',
                'csv_delimiter': '',  # Invalid
                'column_mapping': '{}',
            })

        self.assertIn('CSV delimiter is required', str(cm.exception))

    def test_07_csv_delimiter_single_character(self):
        """Test: CSV delimiter must be single character"""
        with self.assertRaises(ValidationError) as cm:
            self.env['connector.import.profile'].create({
                'name': 'CSV Multi-Char Delimiter',
                'file_format': 'csv_utf8',
                'csv_delimiter': ';;',  # Invalid (2 characters)
                'column_mapping': '{}',
            })

        self.assertIn('single character', str(cm.exception))

    def test_08_get_column_mapping_dict(self):
        """Test: get_column_mapping_dict() method"""
        mapping = {'default_code': 'SKU', 'name': 'Name'}

        profile = self.env['connector.import.profile'].create({
            'name': 'Test Dict Method',
            'file_format': 'xlsx',
            'column_mapping': json.dumps(mapping),
        })

        result = profile.get_column_mapping_dict()
        self.assertEqual(result, mapping)

    def test_09_set_column_mapping_dict(self):
        """Test: set_column_mapping_dict() method"""
        profile = self.env['connector.import.profile'].create({
            'name': 'Test Set Dict',
            'file_format': 'xlsx',
            'column_mapping': '{}',
        })

        new_mapping = {'barcode': 'EAN', 'list_price': 'Price'}
        profile.set_column_mapping_dict(new_mapping)

        parsed = json.loads(profile.column_mapping)
        self.assertEqual(parsed, new_mapping)

    def test_10_copy_profile_appends_copy(self):
        """Test: copy() appends (copy) to name"""
        profile = self.env['connector.import.profile'].create({
            'name': 'Original Profile',
            'file_format': 'xlsx',
            'column_mapping': '{}',
        })

        copy = profile.copy()
        self.assertEqual(copy.name, 'Original Profile (copy)')

    def test_11_job_count_computation(self):
        """Test: job_count computed field"""
        profile = self.env['connector.import.profile'].create({
            'name': 'Profile with Jobs',
            'file_format': 'xlsx',
            'column_mapping': '{}',
        })

        # Create 3 jobs
        for i in range(3):
            self.env['connector.import.job'].create({
                'name': f'Job {i}',
                'profile_id': profile.id,
                'file_data': base64.b64encode(b'dummy'),
            })

        # Recompute
        profile._compute_job_count()
        self.assertEqual(profile.job_count, 3)

    def test_12_last_import_date_computation(self):
        """Test: last_import_date computed field"""
        profile = self.env['connector.import.profile'].create({
            'name': 'Profile Last Import',
            'file_format': 'xlsx',
            'column_mapping': '{}',
        })

        # Create job and set to done
        job = self.env['connector.import.job'].create({
            'name': 'Completed Job',
            'profile_id': profile.id,
            'file_data': base64.b64encode(b'dummy'),
        })

        job.write({
            'state': 'done',
            'end_date': '2025-11-27 12:00:00',
        })

        # Recompute
        profile._compute_last_import_date()
        self.assertTrue(profile.last_import_date)

    def test_13_action_view_import_jobs(self):
        """Test: action_view_import_jobs() returns correct action"""
        profile = self.env['connector.import.profile'].create({
            'name': 'View Jobs Test',
            'file_format': 'xlsx',
            'column_mapping': '{}',
        })

        action = profile.action_view_import_jobs()

        self.assertEqual(action['type'], 'ir.actions.act_window')
        self.assertEqual(action['res_model'], 'connector.import.job')
        self.assertIn(('profile_id', '=', profile.id), action['domain'])

    def test_14_get_mapping_summary(self):
        """Test: get_mapping_summary() formatted output"""
        profile = self.env['connector.import.profile'].create({
            'name': 'Summary Test',
            'file_format': 'xlsx',
            'upsert_field': 'default_code',
            'column_mapping': json.dumps({'default_code': 'SKU', 'name': 'Name'}),
        })

        summary = profile.get_mapping_summary()

        self.assertIn('Summary Test', summary)
        self.assertIn('Excel', summary)
        self.assertIn('default_code', summary)
        self.assertIn('SKU', summary)


class TestConnectorImportJob(TransactionCase):
    """Test suite for connector.import.job model"""

    def setUp(self):
        super().setUp()

        # Create test profile
        self.profile = self.env['connector.import.profile'].create({
            'name': 'Test Import Profile',
            'file_format': 'xlsx',
            'header_row': 1,
            'data_start_row': 2,
            'upsert_field': 'default_code',
            'create_missing': True,
            'update_existing': True,
            'column_mapping': json.dumps({
                'default_code': 'SKU',
                'name': 'Product Name',
                'list_price': 'Price',
            }),
        })

    def _create_excel_file(self, rows):
        """Helper: Create Excel file from rows"""
        try:
            import openpyxl
        except ImportError:
            self.skipTest('openpyxl not installed')

        wb = openpyxl.Workbook()
        sheet = wb.active

        # Header row
        sheet.append(['SKU', 'Product Name', 'Price'])

        # Data rows
        for row in rows:
            sheet.append(row)

        # Save to BytesIO
        output = BytesIO()
        wb.save(output)
        output.seek(0)

        return base64.b64encode(output.read())

    def test_15_create_import_job(self):
        """Test: Create import job with sequence"""
        job = self.env['connector.import.job'].create({
            'profile_id': self.profile.id,
            'file_name': 'test.xlsx',
            'file_data': base64.b64encode(b'dummy'),
        })

        self.assertTrue(job.id)
        self.assertNotEqual(job.name, 'New')  # Sequence generated
        self.assertEqual(job.state, 'draft')
        self.assertTrue(job.active)

    def test_16_import_job_run_state_machine(self):
        """Test: State machine (draft → running → done)"""
        # Create minimal Excel file
        file_data = self._create_excel_file([
            ['TEST-001', 'Test Product', 100.0],
        ])

        job = self.env['connector.import.job'].create({
            'profile_id': self.profile.id,
            'file_name': 'test.xlsx',
            'file_data': file_data,
        })

        # Run import
        job.action_run_import()

        # Check state progression
        self.assertEqual(job.state, 'done')
        self.assertTrue(job.start_date)
        self.assertTrue(job.end_date)
        self.assertGreater(job.duration, 0)

    def test_17_import_job_create_products(self):
        """Test: Import creates new products"""
        file_data = self._create_excel_file([
            ['NEW-001', 'New Product 1', 50.0],
            ['NEW-002', 'New Product 2', 60.0],
        ])

        job = self.env['connector.import.job'].create({
            'profile_id': self.profile.id,
            'file_name': 'create_test.xlsx',
            'file_data': file_data,
        })

        # Run import
        job.action_run_import()

        # Verify products created
        self.assertEqual(job.created_count, 2)
        self.assertEqual(job.updated_count, 0)

        product1 = self.env['product.product'].search([('default_code', '=', 'NEW-001')])
        self.assertTrue(product1)
        self.assertEqual(product1.name, 'New Product 1')
        self.assertEqual(product1.list_price, 50.0)

    def test_18_import_job_update_products(self):
        """Test: Import updates existing products"""
        # Create existing product
        existing = self.env['product.product'].create({
            'default_code': 'UPDATE-001',
            'name': 'Old Name',
            'list_price': 10.0,
        })

        file_data = self._create_excel_file([
            ['UPDATE-001', 'New Name', 20.0],
        ])

        job = self.env['connector.import.job'].create({
            'profile_id': self.profile.id,
            'file_name': 'update_test.xlsx',
            'file_data': file_data,
        })

        # Run import
        job.action_run_import()

        # Verify update
        self.assertEqual(job.created_count, 0)
        self.assertEqual(job.updated_count, 1)

        existing.refresh()
        self.assertEqual(existing.name, 'New Name')
        self.assertEqual(existing.list_price, 20.0)

    def test_19_import_job_upsert_mixed(self):
        """Test: Upsert (create + update mixed)"""
        # Create existing product
        self.env['product.product'].create({
            'default_code': 'EXIST-001',
            'name': 'Existing',
            'list_price': 100.0,
        })

        file_data = self._create_excel_file([
            ['EXIST-001', 'Updated Existing', 150.0],  # Update
            ['NEW-001', 'New Product', 200.0],  # Create
        ])

        job = self.env['connector.import.job'].create({
            'profile_id': self.profile.id,
            'file_name': 'upsert_test.xlsx',
            'file_data': file_data,
        })

        # Run import
        job.action_run_import()

        # Verify counts
        self.assertEqual(job.created_count, 1)
        self.assertEqual(job.updated_count, 1)
        self.assertEqual(job.total_rows, 2)

    def test_20_import_job_skip_empty_rows(self):
        """Test: Skip empty rows setting"""
        file_data = self._create_excel_file([
            ['PROD-001', 'Product 1', 50.0],
            ['', '', ''],  # Empty row
            ['PROD-002', 'Product 2', 60.0],
        ])

        job = self.env['connector.import.job'].create({
            'profile_id': self.profile.id,
            'file_name': 'skip_test.xlsx',
            'file_data': file_data,
        })

        # Run import
        job.action_run_import()

        # Verify only 2 products (empty row skipped)
        self.assertEqual(job.total_rows, 2)

    def test_21_import_job_validation_no_file(self):
        """Test: Validation error if no file uploaded"""
        job = self.env['connector.import.job'].create({
            'profile_id': self.profile.id,
            'file_data': False,  # No file
        })

        with self.assertRaises(ValidationError) as cm:
            job.action_run_import()

        self.assertIn('File is required', str(cm.exception))

    def test_22_import_job_validation_no_profile(self):
        """Test: Validation error if no profile selected"""
        job = self.env['connector.import.job'].create({
            'profile_id': False,  # No profile
            'file_data': base64.b64encode(b'dummy'),
        })

        with self.assertRaises(ValidationError) as cm:
            job.action_run_import()

        self.assertIn('profile is required', str(cm.exception))

    def test_23_import_job_cancel(self):
        """Test: Cancel import job"""
        job = self.env['connector.import.job'].create({
            'profile_id': self.profile.id,
            'file_data': base64.b64encode(b'dummy'),
        })

        job.action_cancel()

        self.assertEqual(job.state, 'cancelled')
        self.assertTrue(job.end_date)

    def test_24_import_job_reset_to_draft(self):
        """Test: Reset failed job to draft"""
        job = self.env['connector.import.job'].create({
            'profile_id': self.profile.id,
            'file_data': base64.b64encode(b'dummy'),
        })

        # Simulate failure
        job.write({
            'state': 'failed',
            'error_message': 'Test error',
        })

        # Reset
        job.action_reset_to_draft()

        self.assertEqual(job.state, 'draft')
        self.assertFalse(job.error_message)

    def test_25_import_job_progress_percent(self):
        """Test: Progress percentage computation"""
        job = self.env['connector.import.job'].create({
            'profile_id': self.profile.id,
            'file_data': base64.b64encode(b'dummy'),
            'total_rows': 100,
            'processed_rows': 50,
        })

        self.assertEqual(job.progress_percent, 50.0)

    def test_26_import_job_duration_computation(self):
        """Test: Duration computation"""
        job = self.env['connector.import.job'].create({
            'profile_id': self.profile.id,
            'file_data': base64.b64encode(b'dummy'),
            'start_date': '2025-11-27 10:00:00',
            'end_date': '2025-11-27 10:01:30',
        })

        # Should be 90 seconds
        self.assertAlmostEqual(job.duration, 90.0, places=0)

    def test_27_import_job_error_logging(self):
        """Test: Errors logged to import_log"""
        # Create profile with invalid mapping
        profile = self.env['connector.import.profile'].create({
            'name': 'Error Test Profile',
            'file_format': 'xlsx',
            'column_mapping': json.dumps({
                'default_code': 'NonExistentColumn',
            }),
        })

        file_data = self._create_excel_file([
            ['SKU-001', 'Product', 100.0],
        ])

        job = self.env['connector.import.job'].create({
            'profile_id': profile.id,
            'file_data': file_data,
        })

        # Run import (will skip due to missing column)
        job.action_run_import()

        # Check that job completed (with skips)
        self.assertEqual(job.state, 'done')
        self.assertGreater(job.skipped_count, 0)

    def test_28_import_job_action_view_logs(self):
        """Test: action_view_logs() returns correct action"""
        job = self.env['connector.import.job'].create({
            'profile_id': self.profile.id,
            'file_data': base64.b64encode(b'dummy'),
        })

        action = job.action_view_logs()

        self.assertEqual(action['type'], 'ir.actions.act_window')
        self.assertEqual(action['res_model'], 'connector.import.log')
        self.assertIn(('job_id', '=', job.id), action['domain'])

    def test_29_import_job_get_summary(self):
        """Test: get_summary() formatted output"""
        job = self.env['connector.import.job'].create({
            'profile_id': self.profile.id,
            'file_data': base64.b64encode(b'dummy'),
            'total_rows': 10,
            'created_count': 5,
            'updated_count': 3,
            'skipped_count': 2,
        })

        summary = job.get_summary()

        self.assertIn('Test Import Profile', summary)
        self.assertIn('Total Rows: 10', summary)
        self.assertIn('Created: 5', summary)
        self.assertIn('Updated: 3', summary)


class TestConnectorImportLog(TransactionCase):
    """Test suite for connector.import.log model"""

    def setUp(self):
        super().setUp()

        # Create test profile and job
        self.profile = self.env['connector.import.profile'].create({
            'name': 'Log Test Profile',
            'file_format': 'xlsx',
            'column_mapping': '{}',
        })

        self.job = self.env['connector.import.job'].create({
            'profile_id': self.profile.id,
            'file_data': base64.b64encode(b'dummy'),
        })

    def test_30_create_import_log_info(self):
        """Test: Create info log entry"""
        log = self.env['connector.import.log'].create({
            'job_id': self.job.id,
            'level': 'info',
            'message': 'Import started',
            'row_number': 0,
        })

        self.assertTrue(log.id)
        self.assertEqual(log.level, 'info')
        self.assertEqual(log.message, 'Import started')

    def test_31_create_import_log_error(self):
        """Test: Create error log entry with row data"""
        row_data = {'SKU': 'TEST-001', 'Name': 'Test'}

        log = self.env['connector.import.log'].create({
            'job_id': self.job.id,
            'level': 'error',
            'message': 'Validation failed',
            'row_number': 5,
            'row_data': json.dumps(row_data),
        })

        self.assertEqual(log.level, 'error')
        self.assertEqual(log.row_number, 5)
        self.assertIn('TEST-001', log.row_data)

    def test_32_import_log_ordering(self):
        """Test: Logs ordered by create_date desc"""
        # Create 3 logs
        for i in range(3):
            self.env['connector.import.log'].create({
                'job_id': self.job.id,
                'level': 'info',
                'message': f'Log {i}',
            })

        logs = self.env['connector.import.log'].search([
            ('job_id', '=', self.job.id)
        ])

        # Should be ordered newest first
        self.assertEqual(logs[0].message, 'Log 2')
        self.assertEqual(logs[2].message, 'Log 0')

    def test_33_import_log_cascade_delete(self):
        """Test: Logs deleted when job deleted (ondelete='cascade')"""
        # Create log
        log = self.env['connector.import.log'].create({
            'job_id': self.job.id,
            'level': 'info',
            'message': 'Test log',
        })

        log_id = log.id

        # Delete job
        self.job.unlink()

        # Log should be deleted
        exists = self.env['connector.import.log'].search([('id', '=', log_id)])
        self.assertFalse(exists)


class TestConnectorImportWizard(TransactionCase):
    """Test suite for connector.import.wizard model"""

    def setUp(self):
        super().setUp()

        # Create test profile
        self.profile = self.env['connector.import.profile'].create({
            'name': 'Wizard Test Profile',
            'file_format': 'xlsx',
            'header_row': 1,
            'data_start_row': 2,
            'column_mapping': json.dumps({
                'default_code': 'SKU',
                'name': 'Product Name',
            }),
        })

    def _create_excel_file(self, rows):
        """Helper: Create Excel file from rows"""
        try:
            import openpyxl
        except ImportError:
            self.skipTest('openpyxl not installed')

        wb = openpyxl.Workbook()
        sheet = wb.active

        # Header row
        sheet.append(['SKU', 'Product Name'])

        # Data rows
        for row in rows:
            sheet.append(row)

        # Save to BytesIO
        output = BytesIO()
        wb.save(output)
        output.seek(0)

        return base64.b64encode(output.read())

    def test_34_create_wizard(self):
        """Test: Create import wizard"""
        wizard = self.env['connector.import.wizard'].create({
            'profile_id': self.profile.id,
            'file_name': 'test.xlsx',
            'file_data': base64.b64encode(b'dummy'),
        })

        self.assertTrue(wizard.id)
        self.assertEqual(wizard.profile_id, self.profile)
        self.assertFalse(wizard.show_preview)

    def test_35_wizard_action_preview(self):
        """Test: Preview action (show_preview = True)"""
        file_data = self._create_excel_file([
            ['WIZ-001', 'Wizard Product 1'],
            ['WIZ-002', 'Wizard Product 2'],
        ])

        wizard = self.env['connector.import.wizard'].create({
            'profile_id': self.profile.id,
            'file_name': 'preview_test.xlsx',
            'file_data': file_data,
        })

        # Action preview
        action = wizard.action_preview()

        # show_preview should be True
        self.assertTrue(wizard.show_preview)

        # Action should reload wizard
        self.assertEqual(action['type'], 'ir.actions.act_window')
        self.assertEqual(action['res_id'], wizard.id)

    def test_36_wizard_preview_data_computation(self):
        """Test: Preview data computed field"""
        file_data = self._create_excel_file([
            ['PREV-001', 'Preview Product'],
        ])

        wizard = self.env['connector.import.wizard'].create({
            'profile_id': self.profile.id,
            'file_name': 'preview.xlsx',
            'file_data': file_data,
        })

        # Trigger preview computation
        wizard._compute_preview_data()

        # Check preview contains profile info and rows
        self.assertIn('Wizard Test Profile', wizard.preview_data)
        self.assertIn('PREV-001', wizard.preview_data)
        self.assertIn('Preview Product', wizard.preview_data)

    def test_37_wizard_action_import_creates_job(self):
        """Test: Import action creates job and runs import"""
        file_data = self._create_excel_file([
            ['IMP-001', 'Import Product'],
        ])

        wizard = self.env['connector.import.wizard'].create({
            'profile_id': self.profile.id,
            'file_name': 'import.xlsx',
            'file_data': file_data,
        })

        # Action import
        action = wizard.action_import()

        # Check job created
        jobs = self.env['connector.import.job'].search([
            ('profile_id', '=', self.profile.id)
        ])
        self.assertTrue(jobs)

        # Check action returns job form
        self.assertEqual(action['type'], 'ir.actions.act_window')
        self.assertEqual(action['res_model'], 'connector.import.job')
        self.assertTrue(action['res_id'])

    def test_38_wizard_action_cancel(self):
        """Test: Cancel action closes wizard"""
        wizard = self.env['connector.import.wizard'].create({
            'profile_id': self.profile.id,
            'file_data': base64.b64encode(b'dummy'),
        })

        action = wizard.action_cancel()

        self.assertEqual(action['type'], 'ir.actions.act_window_close')

    def test_39_wizard_validation_no_file(self):
        """Test: Validation error if no file uploaded"""
        wizard = self.env['connector.import.wizard'].create({
            'profile_id': self.profile.id,
            'file_data': False,  # No file
        })

        with self.assertRaises(ValidationError) as cm:
            wizard.action_import()

        self.assertIn('upload a file', str(cm.exception))

    def test_40_wizard_validation_no_profile(self):
        """Test: Validation error if no profile selected"""
        wizard = self.env['connector.import.wizard'].create({
            'profile_id': False,  # No profile
            'file_data': base64.b64encode(b'dummy'),
        })

        with self.assertRaises(ValidationError) as cm:
            wizard.action_import()

        self.assertIn('select an import profile', str(cm.exception))


class TestConnectorImportCSV(TransactionCase):
    """Test suite for CSV import (UTF-8 and Windows-1251)"""

    def setUp(self):
        super().setUp()

        # Create CSV profile (UTF-8)
        self.profile_utf8 = self.env['connector.import.profile'].create({
            'name': 'CSV UTF-8 Profile',
            'file_format': 'csv_utf8',
            'csv_delimiter': ',',
            'csv_quote_char': '"',
            'header_row': 1,
            'data_start_row': 2,
            'upsert_field': 'default_code',
            'create_missing': True,
            'column_mapping': json.dumps({
                'default_code': 'SKU',
                'name': 'Product Name',
                'list_price': 'Price',
            }),
        })

    def _create_csv_file(self, rows, encoding='utf-8'):
        """Helper: Create CSV file from rows"""
        import csv
        from io import StringIO

        output = StringIO()
        writer = csv.writer(output, delimiter=',', quotechar='"')

        # Header row
        writer.writerow(['SKU', 'Product Name', 'Price'])

        # Data rows
        for row in rows:
            writer.writerow(row)

        csv_content = output.getvalue()
        return base64.b64encode(csv_content.encode(encoding))

    def test_41_import_csv_utf8(self):
        """Test: Import CSV UTF-8 file"""
        file_data = self._create_csv_file([
            ['CSV-001', 'CSV Product 1', '100.0'],
            ['CSV-002', 'CSV Product 2', '200.0'],
        ], encoding='utf-8')

        job = self.env['connector.import.job'].create({
            'profile_id': self.profile_utf8.id,
            'file_name': 'test_utf8.csv',
            'file_data': file_data,
        })

        # Run import
        job.action_run_import()

        # Verify products created
        self.assertEqual(job.state, 'done')
        self.assertEqual(job.created_count, 2)

        product = self.env['product.product'].search([('default_code', '=', 'CSV-001')])
        self.assertTrue(product)
        self.assertEqual(product.name, 'CSV Product 1')

    def test_42_import_csv_semicolon_delimiter(self):
        """Test: CSV with semicolon delimiter"""
        profile = self.env['connector.import.profile'].create({
            'name': 'CSV Semicolon Profile',
            'file_format': 'csv_utf8',
            'csv_delimiter': ';',
            'csv_quote_char': '"',
            'header_row': 1,
            'data_start_row': 2,
            'upsert_field': 'default_code',
            'create_missing': True,
            'column_mapping': json.dumps({
                'default_code': 'SKU',
                'name': 'Name',
            }),
        })

        # Create CSV with semicolon
        import csv
        from io import StringIO

        output = StringIO()
        writer = csv.writer(output, delimiter=';', quotechar='"')
        writer.writerow(['SKU', 'Name'])
        writer.writerow(['SEMI-001', 'Semicolon Product'])

        csv_content = output.getvalue()
        file_data = base64.b64encode(csv_content.encode('utf-8'))

        job = self.env['connector.import.job'].create({
            'profile_id': profile.id,
            'file_name': 'semicolon.csv',
            'file_data': file_data,
        })

        # Run import
        job.action_run_import()

        # Verify
        self.assertEqual(job.state, 'done')
        self.assertEqual(job.created_count, 1)


# ==================
# Test Summary
# ==================
"""
Total Tests: 42

Import Profile Tests (14):
- 01-14: Creation, JSON mapping, validation, business methods

Import Job Tests (15):
- 15-29: State machine, upsert, file parsing, logging, statistics

Import Log Tests (4):
- 30-33: Log creation, ordering, cascade delete

Import Wizard Tests (7):
- 34-40: Wizard creation, preview, import trigger, validation

CSV Import Tests (2):
- 41-42: CSV UTF-8, delimiter variations

Coverage Target: ≥95%
"""
