"""
Unit Tests for Prescription Model

Author: AI Agent
Created: 2025-11-27
Task: OPTERP-32, OPTERP-33
Reference: CLAUDE.md §3.2, PROJECT_PHASES.md W6.1

Purpose:
Comprehensive unit tests for optics.prescription model covering:
- Field validation (Sph, Cyl, Axis, PD, Add)
- SQL constraints
- Python constraints (@api.constrains)
- Business logic
- Edge cases

Test Coverage Target: ≥95%
"""

import pytest
from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError
from datetime import date


class TestPrescriptionModel(TransactionCase):
    """Test optics.prescription model"""

    def setUp(self):
        super().setUp()
        self.Prescription = self.env['optics.prescription']

        # Sample valid prescription data
        self.valid_data = {
            'patient_name': 'Test Patient',
            'date': date.today(),
            'od_sph': -2.50,
            'od_cyl': -0.75,
            'od_axis': 90,
            'os_sph': -2.25,
            'os_cyl': -1.00,
            'os_axis': 85,
            'pd': 64.0,
        }


class TestPrescriptionCreation(TestPrescriptionModel):
    """Test prescription creation"""

    def test_create_valid_prescription(self):
        """Test creating prescription with valid data"""
        prescription = self.Prescription.create(self.valid_data)

        assert prescription.id is not None
        assert prescription.patient_name == 'Test Patient'
        assert prescription.od_sph == -2.50
        assert prescription.od_cyl == -0.75
        assert prescription.od_axis == 90
        assert prescription.os_sph == -2.25
        assert prescription.os_cyl == -1.00
        assert prescription.os_axis == 85
        assert prescription.pd == 64.0

    def test_create_minimal_prescription(self):
        """Test creating prescription with minimal data"""
        minimal_data = {
            'patient_name': 'Minimal Patient',
            'date': date.today(),
        }
        prescription = self.Prescription.create(minimal_data)

        assert prescription.id is not None
        assert prescription.patient_name == 'Minimal Patient'

    def test_display_name_computed(self):
        """Test display_name is computed correctly"""
        prescription = self.Prescription.create(self.valid_data)
        expected_name = f"{self.valid_data['patient_name']} - {self.valid_data['date']}"

        assert prescription.display_name == expected_name


class TestSphereValidation(TestPrescriptionModel):
    """Test Sphere (Sph) validation"""

    def test_sph_valid_range(self):
        """Test Sph accepts valid range -20.00 to +20.00"""
        # Test boundary values
        data_min = self.valid_data.copy()
        data_min.update({'od_sph': -20.0, 'os_sph': -20.0})
        prescription_min = self.Prescription.create(data_min)
        assert prescription_min.od_sph == -20.0

        data_max = self.valid_data.copy()
        data_max.update({'od_sph': 20.0, 'os_sph': 20.0})
        prescription_max = self.Prescription.create(data_max)
        assert prescription_max.od_sph == 20.0

    def test_sph_below_range_fails(self):
        """Test Sph < -20.00 raises ValidationError"""
        data = self.valid_data.copy()
        data['od_sph'] = -20.25

        with pytest.raises(ValidationError, match="OD Sphere must be between"):
            self.Prescription.create(data)

    def test_sph_above_range_fails(self):
        """Test Sph > +20.00 raises ValidationError"""
        data = self.valid_data.copy()
        data['os_sph'] = 20.25

        with pytest.raises(ValidationError, match="OS Sphere must be between"):
            self.Prescription.create(data)

    def test_sph_quarter_step_valid(self):
        """Test Sph accepts 0.25 step increments"""
        valid_values = [-2.75, -2.50, -2.25, 0.0, 0.25, 1.50, 3.75]

        for value in valid_values:
            data = self.valid_data.copy()
            data['od_sph'] = value
            prescription = self.Prescription.create(data)
            assert prescription.od_sph == value

    def test_sph_non_quarter_step_fails(self):
        """Test Sph rejects non-0.25 step values"""
        invalid_values = [-2.10, -1.33, 0.11, 1.20]

        for value in invalid_values:
            data = self.valid_data.copy()
            data['od_sph'] = value

            with pytest.raises(ValidationError, match="must be in 0.25 steps"):
                self.Prescription.create(data)


class TestCylinderValidation(TestPrescriptionModel):
    """Test Cylinder (Cyl) validation"""

    def test_cyl_valid_range(self):
        """Test Cyl accepts valid range -4.00 to 0.00"""
        # Test boundary values
        data_min = self.valid_data.copy()
        data_min.update({'od_cyl': -4.0, 'od_axis': 90})
        prescription_min = self.Prescription.create(data_min)
        assert prescription_min.od_cyl == -4.0

        data_zero = self.valid_data.copy()
        data_zero.update({'od_cyl': 0.0, 'od_axis': None})
        prescription_zero = self.Prescription.create(data_zero)
        assert prescription_zero.od_cyl == 0.0

    def test_cyl_positive_fails(self):
        """Test Cyl > 0 raises ValidationError"""
        data = self.valid_data.copy()
        data['od_cyl'] = 0.25

        with pytest.raises(ValidationError, match="Cylinder must be ≤ 0"):
            self.Prescription.create(data)

    def test_cyl_below_range_fails(self):
        """Test Cyl < -4.00 raises ValidationError"""
        data = self.valid_data.copy()
        data['os_cyl'] = -4.25

        with pytest.raises(ValidationError, match="OS Cylinder must be between"):
            self.Prescription.create(data)

    def test_cyl_quarter_step_valid(self):
        """Test Cyl accepts 0.25 step increments"""
        valid_values = [-4.0, -3.75, -2.50, -1.25, -0.50, 0.0]

        for value in valid_values:
            data = self.valid_data.copy()
            data['os_cyl'] = value
            if value != 0.0:
                data['os_axis'] = 90  # Axis required for non-zero Cyl
            prescription = self.Prescription.create(data)
            assert prescription.os_cyl == value

    def test_cyl_non_quarter_step_fails(self):
        """Test Cyl rejects non-0.25 step values"""
        invalid_values = [-2.10, -1.33, -0.11]

        for value in invalid_values:
            data = self.valid_data.copy()
            data['od_cyl'] = value
            data['od_axis'] = 90

            with pytest.raises(ValidationError, match="must be in 0.25 steps"):
                self.Prescription.create(data)


class TestAxisValidation(TestPrescriptionModel):
    """Test Axis validation"""

    def test_axis_valid_range(self):
        """Test Axis accepts valid range 1-180°"""
        # Test boundary values
        data_min = self.valid_data.copy()
        data_min.update({'od_cyl': -0.50, 'od_axis': 1})
        prescription_min = self.Prescription.create(data_min)
        assert prescription_min.od_axis == 1

        data_max = self.valid_data.copy()
        data_max.update({'os_cyl': -0.50, 'os_axis': 180})
        prescription_max = self.Prescription.create(data_max)
        assert prescription_max.os_axis == 180

    def test_axis_below_range_fails(self):
        """Test Axis < 1 raises ValidationError"""
        data = self.valid_data.copy()
        data.update({'od_cyl': -0.50, 'od_axis': 0})

        with pytest.raises(ValidationError, match="Axis must be between 1 and 180"):
            self.Prescription.create(data)

    def test_axis_above_range_fails(self):
        """Test Axis > 180 raises ValidationError"""
        data = self.valid_data.copy()
        data.update({'os_cyl': -0.50, 'os_axis': 181})

        with pytest.raises(ValidationError, match="Axis must be between 1 and 180"):
            self.Prescription.create(data)

    def test_axis_required_if_cyl_nonzero(self):
        """Test Axis is required when Cyl ≠ 0"""
        data = self.valid_data.copy()
        data.update({'od_cyl': -0.75, 'od_axis': None})

        with pytest.raises(ValidationError, match="Axis is required when.*Cylinder is not zero"):
            self.Prescription.create(data)

    def test_axis_not_required_if_cyl_zero(self):
        """Test Axis not required when Cyl = 0"""
        data = self.valid_data.copy()
        data.update({'od_cyl': 0.0, 'od_axis': None})

        prescription = self.Prescription.create(data)
        assert prescription.od_cyl == 0.0
        assert prescription.od_axis is False  # Odoo represents None as False


class TestAddValidation(TestPrescriptionModel):
    """Test Addition (Add) validation"""

    def test_add_valid_range(self):
        """Test Add accepts valid range 0.75-3.00"""
        # Test boundary values
        data_min = self.valid_data.copy()
        data_min['od_add'] = 0.75
        prescription_min = self.Prescription.create(data_min)
        assert prescription_min.od_add == 0.75

        data_max = self.valid_data.copy()
        data_max['os_add'] = 3.0
        prescription_max = self.Prescription.create(data_max)
        assert prescription_max.os_add == 3.0

    def test_add_below_range_fails(self):
        """Test Add < 0.75 raises ValidationError"""
        data = self.valid_data.copy()
        data['od_add'] = 0.50

        with pytest.raises(ValidationError, match="Add must be between 0.75 and 3.00"):
            self.Prescription.create(data)

    def test_add_above_range_fails(self):
        """Test Add > 3.00 raises ValidationError"""
        data = self.valid_data.copy()
        data['os_add'] = 3.25

        with pytest.raises(ValidationError, match="Add must be between 0.75 and 3.00"):
            self.Prescription.create(data)


class TestPDValidation(TestPrescriptionModel):
    """Test Pupillary Distance (PD) validation"""

    def test_pd_valid_range(self):
        """Test PD accepts valid range 56.0-72.0 mm"""
        # Test boundary values
        data_min = self.valid_data.copy()
        data_min['pd'] = 56.0
        prescription_min = self.Prescription.create(data_min)
        assert prescription_min.pd == 56.0

        data_max = self.valid_data.copy()
        data_max['pd'] = 72.0
        prescription_max = self.Prescription.create(data_max)
        assert prescription_max.pd == 72.0

    def test_pd_below_range_fails(self):
        """Test PD < 56.0 raises ValidationError"""
        data = self.valid_data.copy()
        data['pd'] = 55.9

        with pytest.raises(ValidationError, match="PD must be between 56.0 and 72.0"):
            self.Prescription.create(data)

    def test_pd_above_range_fails(self):
        """Test PD > 72.0 raises ValidationError"""
        data = self.valid_data.copy()
        data['pd'] = 72.1

        with pytest.raises(ValidationError, match="PD must be between 56.0 and 72.0"):
            self.Prescription.create(data)

    def test_monocular_pd_valid_range(self):
        """Test monocular PD accepts valid range 28.0-36.0 mm"""
        data = self.valid_data.copy()
        data.update({'pd_right': 32.0, 'pd_left': 32.0})

        prescription = self.Prescription.create(data)
        assert prescription.pd_right == 32.0
        assert prescription.pd_left == 32.0

    def test_monocular_pd_below_range_fails(self):
        """Test monocular PD < 28.0 raises ValidationError"""
        data = self.valid_data.copy()
        data['pd_right'] = 27.9

        with pytest.raises(ValidationError, match="Right PD must be between"):
            self.Prescription.create(data)

    def test_monocular_pd_above_range_fails(self):
        """Test monocular PD > 36.0 raises ValidationError"""
        data = self.valid_data.copy()
        data['pd_left'] = 36.1

        with pytest.raises(ValidationError, match="Left PD must be between"):
            self.Prescription.create(data)


class TestBusinessLogic(TestPrescriptionModel):
    """Test business methods"""

    def test_format_prescription_full(self):
        """Test format_prescription() with full data"""
        prescription = self.Prescription.create(self.valid_data)
        formatted = prescription.format_prescription()

        assert 'OD: Sph -2.50' in formatted
        assert 'Cyl -0.75 Axis 90°' in formatted
        assert 'OS: Sph -2.25' in formatted
        assert 'Cyl -1.00 Axis 85°' in formatted
        assert 'PD: 64.0 mm' in formatted

    def test_format_prescription_minimal(self):
        """Test format_prescription() with minimal data"""
        minimal_data = {
            'patient_name': 'Test Patient',
            'date': date.today(),
            'od_sph': -1.00,
        }
        prescription = self.Prescription.create(minimal_data)
        formatted = prescription.format_prescription()

        assert 'OD: Sph -1.00' in formatted
        assert 'OS:' not in formatted

    def test_format_prescription_empty(self):
        """Test format_prescription() with no optical data"""
        minimal_data = {
            'patient_name': 'Test Patient',
            'date': date.today(),
        }
        prescription = self.Prescription.create(minimal_data)
        formatted = prescription.format_prescription()

        assert formatted == "No prescription data"

    def test_archive_prescription(self):
        """Test archiving prescription"""
        prescription = self.Prescription.create(self.valid_data)
        assert prescription.active is True

        prescription.toggle_active()
        assert prescription.active is False


class TestEdgeCases(TestPrescriptionModel):
    """Test edge cases and boundary conditions"""

    def test_zero_values(self):
        """Test prescription with zero values"""
        data = {
            'patient_name': 'Test Patient',
            'date': date.today(),
            'od_sph': 0.0,
            'od_cyl': 0.0,
            'os_sph': 0.0,
            'os_cyl': 0.0,
        }
        prescription = self.Prescription.create(data)
        assert prescription.od_sph == 0.0
        assert prescription.od_cyl == 0.0

    def test_progressive_lens_prescription(self):
        """Test prescription for progressive lenses with Add"""
        data = self.valid_data.copy()
        data.update({
            'od_add': 2.00,
            'os_add': 2.00,
        })
        prescription = self.Prescription.create(data)
        assert prescription.od_add == 2.00
        assert prescription.os_add == 2.00

    def test_prism_values(self):
        """Test prescription with prism values"""
        data = self.valid_data.copy()
        data.update({
            'prism_od': '2.0 BI',
            'prism_os': '1.5 BU',
        })
        prescription = self.Prescription.create(data)
        assert prescription.prism_od == '2.0 BI'
        assert prescription.prism_os == '1.5 BU'

    def test_only_right_eye(self):
        """Test prescription with only right eye data"""
        data = {
            'patient_name': 'Test Patient',
            'date': date.today(),
            'od_sph': -3.00,
            'od_cyl': -1.00,
            'od_axis': 90,
        }
        prescription = self.Prescription.create(data)
        assert prescription.od_sph == -3.00
        assert prescription.os_sph is False  # Odoo represents None as False

    def test_only_left_eye(self):
        """Test prescription with only left eye data"""
        data = {
            'patient_name': 'Test Patient',
            'date': date.today(),
            'os_sph': -2.00,
            'os_cyl': -0.50,
            'os_axis': 85,
        }
        prescription = self.Prescription.create(data)
        assert prescription.os_sph == -2.00
        assert prescription.od_sph is False
