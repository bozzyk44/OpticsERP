# -*- coding: utf-8 -*-
"""
Unit Tests for Manufacturing Order Model

Author: AI Agent
Created: 2025-11-27
Task: OPTERP-37
Reference: CLAUDE.md §3.2, PROJECT_PHASES.md W6.5

Purpose:
Comprehensive unit tests for optics.manufacturing.order model
Test Coverage Target: ≥95%

Test Coverage:
- Model creation and CRUD operations
- Workflow state transitions (6 action methods)
- Date validation (chronological order)
- Expected delivery calculation (3/7/14 days)
- Duration calculation
- Late order detection
- Sequence generation
- Business methods
- Edge cases and error handling
"""

from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError, UserError
from datetime import date, datetime, timedelta
from freezegun import freeze_time


class TestManufacturingOrderModel(TransactionCase):
    """Base test class with common setup for Manufacturing Order tests"""

    def setUp(self):
        super().setUp()
        self.ManufacturingOrder = self.env['optics.manufacturing.order']
        self.Partner = self.env['res.partner']
        self.Prescription = self.env['optics.prescription']
        self.Lens = self.env['optics.lens']

        # Create sample customer
        self.customer = self.Partner.create({
            'name': 'Test Customer',
            'email': 'test@example.com',
        })

        # Create sample prescription
        self.prescription = self.Prescription.create({
            'patient_name': 'Test Patient',
            'date': date.today(),
            'od_sph': -2.50,
            'od_cyl': -0.75,
            'od_axis': 90,
            'os_sph': -2.25,
            'os_cyl': -0.50,
            'os_axis': 85,
            'pd': 63.0,
        })

        # Create sample lenses (different types for lead time testing)
        self.lens_single = self.Lens.create({
            'name': 'Single Vision Lens',
            'type': 'single',
            'index': 1.5,
            'material': 'cr39',
            'cost_price': 500.0,
            'sale_price': 1500.0,
        })

        self.lens_bifocal = self.Lens.create({
            'name': 'Bifocal Lens',
            'type': 'bifocal',
            'index': 1.6,
            'material': 'polycarbonate',
            'cost_price': 1000.0,
            'sale_price': 3000.0,
        })

        self.lens_progressive = self.Lens.create({
            'name': 'Progressive Lens',
            'type': 'progressive',
            'index': 1.67,
            'material': 'high_index',
            'cost_price': 3000.0,
            'sale_price': 9000.0,
        })

        # Sample valid MO data
        self.valid_data = {
            'customer_id': self.customer.id,
            'prescription_id': self.prescription.id,
            'lens_id': self.lens_single.id,
        }


class TestManufacturingOrderCreation(TestManufacturingOrderModel):
    """Test Manufacturing Order creation"""

    def test_create_valid_manufacturing_order(self):
        """Test creating a valid manufacturing order with all required fields"""
        mo = self.ManufacturingOrder.create(self.valid_data)

        self.assertTrue(mo.id)
        self.assertEqual(mo.customer_id, self.customer)
        self.assertEqual(mo.prescription_id, self.prescription)
        self.assertEqual(mo.lens_id, self.lens_single)
        self.assertEqual(mo.state, 'draft')
        self.assertTrue(mo.active)
        self.assertIsNotNone(mo.date_order)

    def test_create_with_notes(self):
        """Test creating MO with notes"""
        mo = self.ManufacturingOrder.create({
            **self.valid_data,
            'notes': 'Customer prefers thin lenses',
            'production_notes': 'Use extra care with coating',
        })

        self.assertEqual(mo.notes, 'Customer prefers thin lenses')
        self.assertEqual(mo.production_notes, 'Use extra care with coating')

    def test_sequence_generation(self):
        """Test automatic sequence generation for order reference"""
        mo1 = self.ManufacturingOrder.create(self.valid_data)
        mo2 = self.ManufacturingOrder.create(self.valid_data)

        self.assertNotEqual(mo1.name, 'New')
        self.assertNotEqual(mo2.name, 'New')
        self.assertNotEqual(mo1.name, mo2.name)

    def test_default_values(self):
        """Test default field values"""
        mo = self.ManufacturingOrder.create(self.valid_data)

        self.assertEqual(mo.state, 'draft')
        self.assertTrue(mo.active)
        self.assertFalse(mo.date_confirmed)
        self.assertFalse(mo.date_production_start)
        self.assertFalse(mo.date_ready)
        self.assertFalse(mo.date_delivered)


class TestWorkflowTransitions(TestManufacturingOrderModel):
    """Test workflow state transitions"""

    def test_workflow_draft_to_confirmed(self):
        """Test transition from draft to confirmed"""
        mo = self.ManufacturingOrder.create(self.valid_data)
        self.assertEqual(mo.state, 'draft')

        mo.action_confirm()

        self.assertEqual(mo.state, 'confirmed')
        self.assertIsNotNone(mo.date_confirmed)

    def test_workflow_confirmed_to_production(self):
        """Test transition from confirmed to production"""
        mo = self.ManufacturingOrder.create(self.valid_data)
        mo.action_confirm()
        self.assertEqual(mo.state, 'confirmed')

        mo.action_start_production()

        self.assertEqual(mo.state, 'production')
        self.assertIsNotNone(mo.date_production_start)

    def test_workflow_production_to_ready(self):
        """Test transition from production to ready"""
        mo = self.ManufacturingOrder.create(self.valid_data)
        mo.action_confirm()
        mo.action_start_production()
        self.assertEqual(mo.state, 'production')

        mo.action_mark_ready()

        self.assertEqual(mo.state, 'ready')
        self.assertIsNotNone(mo.date_ready)

    def test_workflow_ready_to_delivered(self):
        """Test transition from ready to delivered"""
        mo = self.ManufacturingOrder.create(self.valid_data)
        mo.action_confirm()
        mo.action_start_production()
        mo.action_mark_ready()
        self.assertEqual(mo.state, 'ready')

        mo.action_deliver()

        self.assertEqual(mo.state, 'delivered')
        self.assertIsNotNone(mo.date_delivered)

    def test_workflow_complete_cycle(self):
        """Test complete workflow cycle from draft to delivered"""
        mo = self.ManufacturingOrder.create(self.valid_data)

        # Draft → Confirmed
        mo.action_confirm()
        self.assertEqual(mo.state, 'confirmed')
        self.assertIsNotNone(mo.date_confirmed)

        # Confirmed → Production
        mo.action_start_production()
        self.assertEqual(mo.state, 'production')
        self.assertIsNotNone(mo.date_production_start)

        # Production → Ready
        mo.action_mark_ready()
        self.assertEqual(mo.state, 'ready')
        self.assertIsNotNone(mo.date_ready)

        # Ready → Delivered
        mo.action_deliver()
        self.assertEqual(mo.state, 'delivered')
        self.assertIsNotNone(mo.date_delivered)

        # All dates should be set
        self.assertIsNotNone(mo.date_order)
        self.assertIsNotNone(mo.date_confirmed)
        self.assertIsNotNone(mo.date_production_start)
        self.assertIsNotNone(mo.date_ready)
        self.assertIsNotNone(mo.date_delivered)


class TestWorkflowValidation(TestManufacturingOrderModel):
    """Test workflow state transition validation"""

    def test_cannot_confirm_non_draft_order(self):
        """Test that only draft orders can be confirmed"""
        mo = self.ManufacturingOrder.create(self.valid_data)
        mo.action_confirm()

        # Try to confirm again
        with self.assertRaises(UserError) as context:
            mo.action_confirm()

        self.assertIn('draft', str(context.exception).lower())

    def test_cannot_start_production_non_confirmed_order(self):
        """Test that only confirmed orders can start production"""
        mo = self.ManufacturingOrder.create(self.valid_data)

        # Try to start production from draft
        with self.assertRaises(UserError) as context:
            mo.action_start_production()

        self.assertIn('confirmed', str(context.exception).lower())

    def test_cannot_mark_ready_non_production_order(self):
        """Test that only orders in production can be marked ready"""
        mo = self.ManufacturingOrder.create(self.valid_data)
        mo.action_confirm()

        # Try to mark ready from confirmed (skip production)
        with self.assertRaises(UserError) as context:
            mo.action_mark_ready()

        self.assertIn('production', str(context.exception).lower())

    def test_cannot_deliver_non_ready_order(self):
        """Test that only ready orders can be delivered"""
        mo = self.ManufacturingOrder.create(self.valid_data)
        mo.action_confirm()
        mo.action_start_production()

        # Try to deliver from production (skip ready)
        with self.assertRaises(UserError) as context:
            mo.action_deliver()

        self.assertIn('ready', str(context.exception).lower())

    def test_confirm_requires_prescription(self):
        """Test that prescription is required to confirm order"""
        mo = self.ManufacturingOrder.create({
            'customer_id': self.customer.id,
            'prescription_id': False,
            'lens_id': self.lens_single.id,
        })

        with self.assertRaises(ValidationError) as context:
            mo.action_confirm()

        self.assertIn('prescription', str(context.exception).lower())

    def test_confirm_requires_lens(self):
        """Test that lens is required to confirm order"""
        mo = self.ManufacturingOrder.create({
            'customer_id': self.customer.id,
            'prescription_id': self.prescription.id,
            'lens_id': False,
        })

        with self.assertRaises(ValidationError) as context:
            mo.action_confirm()

        self.assertIn('lens', str(context.exception).lower())


class TestWorkflowCancellation(TestManufacturingOrderModel):
    """Test order cancellation and reset"""

    def test_cancel_draft_order(self):
        """Test cancelling a draft order"""
        mo = self.ManufacturingOrder.create(self.valid_data)

        mo.action_cancel()

        self.assertEqual(mo.state, 'cancelled')

    def test_cancel_confirmed_order(self):
        """Test cancelling a confirmed order"""
        mo = self.ManufacturingOrder.create(self.valid_data)
        mo.action_confirm()

        mo.action_cancel()

        self.assertEqual(mo.state, 'cancelled')

    def test_cancel_production_order(self):
        """Test cancelling an order in production"""
        mo = self.ManufacturingOrder.create(self.valid_data)
        mo.action_confirm()
        mo.action_start_production()

        mo.action_cancel()

        self.assertEqual(mo.state, 'cancelled')

    def test_cancel_ready_order(self):
        """Test cancelling a ready order"""
        mo = self.ManufacturingOrder.create(self.valid_data)
        mo.action_confirm()
        mo.action_start_production()
        mo.action_mark_ready()

        mo.action_cancel()

        self.assertEqual(mo.state, 'cancelled')

    def test_cannot_cancel_delivered_order(self):
        """Test that delivered orders cannot be cancelled"""
        mo = self.ManufacturingOrder.create(self.valid_data)
        mo.action_confirm()
        mo.action_start_production()
        mo.action_mark_ready()
        mo.action_deliver()

        with self.assertRaises(UserError) as context:
            mo.action_cancel()

        self.assertIn('delivered', str(context.exception).lower())

    def test_reset_cancelled_to_draft(self):
        """Test resetting cancelled order to draft"""
        mo = self.ManufacturingOrder.create(self.valid_data)
        mo.action_confirm()
        date_confirmed_before = mo.date_confirmed
        mo.action_cancel()

        mo.action_reset_to_draft()

        self.assertEqual(mo.state, 'draft')
        self.assertFalse(mo.date_confirmed)
        self.assertFalse(mo.date_production_start)
        self.assertFalse(mo.date_ready)
        self.assertFalse(mo.date_delivered)

    def test_cannot_reset_non_cancelled_order(self):
        """Test that only cancelled orders can be reset"""
        mo = self.ManufacturingOrder.create(self.valid_data)

        with self.assertRaises(UserError) as context:
            mo.action_reset_to_draft()

        self.assertIn('cancelled', str(context.exception).lower())


class TestExpectedDeliveryCalculation(TestManufacturingOrderModel):
    """Test expected delivery date calculation"""

    @freeze_time("2025-11-27 10:00:00")
    def test_expected_delivery_single_vision(self):
        """Test expected delivery for single vision lens (3 days)"""
        mo = self.ManufacturingOrder.create({
            **self.valid_data,
            'lens_id': self.lens_single.id,
        })

        mo.action_confirm()

        expected_date = date(2025, 11, 30)  # 3 days from 2025-11-27
        self.assertEqual(mo.expected_delivery_date, expected_date)

    @freeze_time("2025-11-27 10:00:00")
    def test_expected_delivery_bifocal(self):
        """Test expected delivery for bifocal lens (7 days)"""
        mo = self.ManufacturingOrder.create({
            **self.valid_data,
            'lens_id': self.lens_bifocal.id,
        })

        mo.action_confirm()

        expected_date = date(2025, 12, 4)  # 7 days from 2025-11-27
        self.assertEqual(mo.expected_delivery_date, expected_date)

    @freeze_time("2025-11-27 10:00:00")
    def test_expected_delivery_progressive(self):
        """Test expected delivery for progressive lens (14 days)"""
        mo = self.ManufacturingOrder.create({
            **self.valid_data,
            'lens_id': self.lens_progressive.id,
        })

        mo.action_confirm()

        expected_date = date(2025, 12, 11)  # 14 days from 2025-11-27
        self.assertEqual(mo.expected_delivery_date, expected_date)

    def test_expected_delivery_not_set_before_confirmation(self):
        """Test that expected delivery is not set before confirmation"""
        mo = self.ManufacturingOrder.create(self.valid_data)

        self.assertFalse(mo.expected_delivery_date)


class TestDurationCalculation(TestManufacturingOrderModel):
    """Test duration calculation"""

    def test_duration_days_after_delivery(self):
        """Test duration calculation after delivery"""
        with freeze_time("2025-11-27 10:00:00"):
            mo = self.ManufacturingOrder.create(self.valid_data)
            mo.action_confirm()

        with freeze_time("2025-11-27 11:00:00"):
            mo.action_start_production()

        with freeze_time("2025-11-29 15:00:00"):
            mo.action_mark_ready()

        with freeze_time("2025-11-29 16:00:00"):
            mo.action_deliver()

        # Duration from confirmed (2025-11-27 10:00) to delivered (2025-11-29 16:00) = 2 days
        self.assertEqual(mo.duration_days, 2)

    def test_duration_zero_before_delivery(self):
        """Test that duration is zero before delivery"""
        mo = self.ManufacturingOrder.create(self.valid_data)
        mo.action_confirm()

        self.assertEqual(mo.duration_days, 0)


class TestLateOrderDetection(TestManufacturingOrderModel):
    """Test late order detection"""

    @freeze_time("2025-11-27 10:00:00")
    def test_order_not_late_before_expected_delivery(self):
        """Test order is not late before expected delivery date"""
        mo = self.ManufacturingOrder.create({
            **self.valid_data,
            'lens_id': self.lens_single.id,  # 3 days → expected 2025-11-30
        })
        mo.action_confirm()

        # Today is 2025-11-27, expected is 2025-11-30
        self.assertFalse(mo.is_late)

    @freeze_time("2025-11-27 10:00:00")
    def test_order_not_late_on_expected_delivery(self):
        """Test order is not late on expected delivery date"""
        mo = self.ManufacturingOrder.create({
            **self.valid_data,
            'lens_id': self.lens_single.id,  # 3 days
        })
        mo.action_confirm()

        # Fast forward to expected delivery date
        with freeze_time("2025-11-30 10:00:00"):
            self.assertFalse(mo.is_late)

    @freeze_time("2025-11-27 10:00:00")
    def test_order_late_after_expected_delivery(self):
        """Test order is late after expected delivery date"""
        mo = self.ManufacturingOrder.create({
            **self.valid_data,
            'lens_id': self.lens_single.id,  # 3 days → expected 2025-11-30
        })
        mo.action_confirm()

        # Fast forward to after expected delivery
        with freeze_time("2025-12-01 10:00:00"):  # 1 day late
            self.assertTrue(mo.is_late)

    @freeze_time("2025-11-27 10:00:00")
    def test_delivered_order_not_late(self):
        """Test delivered orders are never marked as late"""
        mo = self.ManufacturingOrder.create({
            **self.valid_data,
            'lens_id': self.lens_single.id,
        })
        mo.action_confirm()
        mo.action_start_production()
        mo.action_mark_ready()
        mo.action_deliver()

        # Fast forward way past expected delivery
        with freeze_time("2025-12-15 10:00:00"):
            self.assertFalse(mo.is_late)


class TestDateValidation(TestManufacturingOrderModel):
    """Test chronological date validation"""

    def test_dates_in_chronological_order(self):
        """Test that dates are validated to be in chronological order"""
        with freeze_time("2025-11-27 10:00:00"):
            mo = self.ManufacturingOrder.create(self.valid_data)
            mo.action_confirm()

        with freeze_time("2025-11-27 11:00:00"):
            mo.action_start_production()

        with freeze_time("2025-11-29 15:00:00"):
            mo.action_mark_ready()

        with freeze_time("2025-11-29 16:00:00"):
            mo.action_deliver()

        # All dates should be in order
        self.assertLessEqual(mo.date_confirmed, mo.date_production_start)
        self.assertLessEqual(mo.date_production_start, mo.date_ready)
        self.assertLessEqual(mo.date_ready, mo.date_delivered)


class TestBusinessMethods(TestManufacturingOrderModel):
    """Test business methods"""

    def test_get_workflow_info(self):
        """Test get_workflow_info returns formatted string"""
        mo = self.ManufacturingOrder.create(self.valid_data)
        mo.action_confirm()

        info = mo.get_workflow_info()

        self.assertIn(mo.name, info)
        self.assertIn(self.customer.name, info)
        self.assertIn('Confirmed', info)

    def test_get_workflow_info_shows_all_dates(self):
        """Test get_workflow_info shows all workflow dates"""
        mo = self.ManufacturingOrder.create(self.valid_data)
        mo.action_confirm()
        mo.action_start_production()
        mo.action_mark_ready()
        mo.action_deliver()

        info = mo.get_workflow_info()

        self.assertIn('Confirmed:', info)
        self.assertIn('Production Started:', info)
        self.assertIn('Ready:', info)
        self.assertIn('Delivered:', info)


class TestArchiving(TestManufacturingOrderModel):
    """Test order archiving"""

    def test_archive_order(self):
        """Test archiving an order"""
        mo = self.ManufacturingOrder.create(self.valid_data)

        mo.active = False

        self.assertFalse(mo.active)

    def test_unarchive_order(self):
        """Test unarchiving an order"""
        mo = self.ManufacturingOrder.create(self.valid_data)
        mo.active = False

        mo.active = True

        self.assertTrue(mo.active)


class TestEdgeCases(TestManufacturingOrderModel):
    """Test edge cases and boundary conditions"""

    def test_multiple_orders_same_customer(self):
        """Test creating multiple orders for same customer"""
        mo1 = self.ManufacturingOrder.create(self.valid_data)
        mo2 = self.ManufacturingOrder.create(self.valid_data)

        self.assertEqual(mo1.customer_id, mo2.customer_id)
        self.assertNotEqual(mo1.id, mo2.id)
        self.assertNotEqual(mo1.name, mo2.name)

    def test_multiple_orders_different_lens_types(self):
        """Test orders with different lens types have different lead times"""
        with freeze_time("2025-11-27 10:00:00"):
            mo_single = self.ManufacturingOrder.create({
                **self.valid_data,
                'lens_id': self.lens_single.id,
            })
            mo_single.action_confirm()

            mo_bifocal = self.ManufacturingOrder.create({
                **self.valid_data,
                'lens_id': self.lens_bifocal.id,
            })
            mo_bifocal.action_confirm()

            mo_progressive = self.ManufacturingOrder.create({
                **self.valid_data,
                'lens_id': self.lens_progressive.id,
            })
            mo_progressive.action_confirm()

        # Different expected delivery dates
        self.assertEqual(mo_single.expected_delivery_date, date(2025, 11, 30))  # 3 days
        self.assertEqual(mo_bifocal.expected_delivery_date, date(2025, 12, 4))  # 7 days
        self.assertEqual(mo_progressive.expected_delivery_date, date(2025, 12, 11))  # 14 days

    def test_order_without_optional_fields(self):
        """Test creating order with only required fields"""
        mo = self.ManufacturingOrder.create(self.valid_data)

        self.assertFalse(mo.notes)
        self.assertFalse(mo.production_notes)

    def test_order_with_all_fields(self):
        """Test creating order with all fields populated"""
        mo = self.ManufacturingOrder.create({
            **self.valid_data,
            'notes': 'Customer notes',
            'production_notes': 'Production notes',
        })

        self.assertEqual(mo.notes, 'Customer notes')
        self.assertEqual(mo.production_notes, 'Production notes')

    @freeze_time("2025-11-27 10:00:00")
    def test_rapid_state_transitions(self):
        """Test rapid state transitions in same transaction"""
        mo = self.ManufacturingOrder.create(self.valid_data)

        # Execute all transitions rapidly
        mo.action_confirm()
        mo.action_start_production()
        mo.action_mark_ready()
        mo.action_deliver()

        self.assertEqual(mo.state, 'delivered')
        self.assertIsNotNone(mo.date_confirmed)
        self.assertIsNotNone(mo.date_production_start)
        self.assertIsNotNone(mo.date_ready)
        self.assertIsNotNone(mo.date_delivered)
