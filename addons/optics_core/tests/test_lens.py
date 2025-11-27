"""
Unit Tests for Lens Model

Author: AI Agent
Created: 2025-11-27
Task: OPTERP-35
Reference: CLAUDE.md §3.2, PROJECT_PHASES.md W6.2

Purpose:
Comprehensive unit tests for optics.lens and optics.lens.coating models covering:
- Lens types (single/bifocal/progressive)
- Index validation (1.5-1.9)
- Material selection
- Coatings (many2many)
- Pricing validation
- Dimensions validation
- Business logic (display_name, coating_summary, get_full_specification)
- Edge cases

Test Coverage Target: ≥95%
"""

import pytest
from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError
from psycopg2 import IntegrityError


class TestLensModel(TransactionCase):
    """Test optics.lens model"""

    def setUp(self):
        super().setUp()
        self.Lens = self.env['optics.lens']
        self.Coating = self.env['optics.lens.coating']

        # Create sample coatings
        self.coating_ar = self.Coating.create({
            'name': 'Anti-Reflective Coating',
            'code': 'AR',
            'additional_cost': 500.0,
        })

        self.coating_hc = self.Coating.create({
            'name': 'Hard Coating',
            'code': 'HC',
            'additional_cost': 300.0,
        })

        self.coating_uv = self.Coating.create({
            'name': 'UV Protection',
            'code': 'UV',
            'additional_cost': 200.0,
        })

        # Sample valid lens data
        self.valid_data = {
            'name': 'Test Lens',
            'type': 'single',
            'index': 1.5,
            'material': 'cr39',
            'cost_price': 500.0,
            'sale_price': 1500.0,
        }


class TestLensCreation(TestLensModel):
    """Test lens creation"""

    def test_create_valid_lens(self):
        """Test creating a valid lens"""
        lens = self.Lens.create(self.valid_data)

        self.assertEqual(lens.name, 'Test Lens')
        self.assertEqual(lens.type, 'single')
        self.assertEqual(lens.index, 1.5)
        self.assertEqual(lens.material, 'cr39')
        self.assertTrue(lens.active)

    def test_create_minimal_lens(self):
        """Test creating lens with required fields only"""
        lens = self.Lens.create({
            'name': 'Minimal Lens',
            'type': 'single',
            'index': 1.5,
            'material': 'cr39',
        })

        self.assertEqual(lens.name, 'Minimal Lens')
        self.assertEqual(lens.type, 'single')
        self.assertIsNone(lens.cost_price)
        self.assertIsNone(lens.sale_price)

    def test_create_with_coatings(self):
        """Test creating lens with multiple coatings"""
        lens = self.Lens.create({
            **self.valid_data,
            'coating_ids': [(6, 0, [self.coating_ar.id, self.coating_hc.id, self.coating_uv.id])]
        })

        self.assertEqual(len(lens.coating_ids), 3)
        self.assertIn(self.coating_ar, lens.coating_ids)
        self.assertIn(self.coating_hc, lens.coating_ids)
        self.assertIn(self.coating_uv, lens.coating_ids)

    def test_default_values(self):
        """Test default field values"""
        lens = self.Lens.create({
            'name': 'Default Lens',
        })

        self.assertEqual(lens.type, 'single')  # Default type
        self.assertEqual(lens.index, 1.5)      # Default index
        self.assertEqual(lens.material, 'cr39')  # Default material
        self.assertTrue(lens.active)           # Default active


class TestLensTypes(TestLensModel):
    """Test lens type selection"""

    def test_type_single_vision(self):
        """Test single vision lens type"""
        lens = self.Lens.create({
            **self.valid_data,
            'type': 'single'
        })

        self.assertEqual(lens.type, 'single')

    def test_type_bifocal(self):
        """Test bifocal lens type"""
        lens = self.Lens.create({
            **self.valid_data,
            'type': 'bifocal'
        })

        self.assertEqual(lens.type, 'bifocal')

    def test_type_progressive(self):
        """Test progressive lens type"""
        lens = self.Lens.create({
            **self.valid_data,
            'type': 'progressive'
        })

        self.assertEqual(lens.type, 'progressive')


class TestIndexValidation(TestLensModel):
    """Test refractive index validation"""

    def test_index_valid_range(self):
        """Test valid index values: 1.5, 1.6, 1.67, 1.74"""
        valid_indices = [1.5, 1.6, 1.67, 1.74, 1.9]

        for index_val in valid_indices:
            lens = self.Lens.create({
                **self.valid_data,
                'name': f'Lens Index {index_val}',
                'index': index_val
            })
            self.assertEqual(lens.index, index_val)

    def test_index_minimum_boundary(self):
        """Test minimum index boundary (1.5)"""
        lens = self.Lens.create({
            **self.valid_data,
            'index': 1.5
        })

        self.assertEqual(lens.index, 1.5)

    def test_index_maximum_boundary(self):
        """Test maximum index boundary (1.9)"""
        lens = self.Lens.create({
            **self.valid_data,
            'index': 1.9
        })

        self.assertEqual(lens.index, 1.9)

    def test_index_out_of_range_low(self):
        """Test index below minimum (1.4) raises ValidationError"""
        with self.assertRaises(ValidationError) as context:
            self.Lens.create({
                **self.valid_data,
                'index': 1.4
            })

        self.assertIn('1.5', str(context.exception))
        self.assertIn('1.9', str(context.exception))

    def test_index_out_of_range_high(self):
        """Test index above maximum (2.0) raises ValidationError"""
        with self.assertRaises(ValidationError) as context:
            self.Lens.create({
                **self.valid_data,
                'index': 2.0
            })

        self.assertIn('1.5', str(context.exception))
        self.assertIn('1.9', str(context.exception))


class TestMaterialValidation(TestLensModel):
    """Test material selection"""

    def test_material_cr39(self):
        """Test CR-39 plastic material"""
        lens = self.Lens.create({
            **self.valid_data,
            'material': 'cr39'
        })

        self.assertEqual(lens.material, 'cr39')

    def test_material_polycarbonate(self):
        """Test polycarbonate material"""
        lens = self.Lens.create({
            **self.valid_data,
            'material': 'polycarbonate'
        })

        self.assertEqual(lens.material, 'polycarbonate')

    def test_material_trivex(self):
        """Test trivex material"""
        lens = self.Lens.create({
            **self.valid_data,
            'material': 'trivex'
        })

        self.assertEqual(lens.material, 'trivex')

    def test_material_high_index(self):
        """Test high-index glass material"""
        lens = self.Lens.create({
            **self.valid_data,
            'material': 'high_index'
        })

        self.assertEqual(lens.material, 'high_index')


class TestCoatings(TestLensModel):
    """Test lens coatings (many2many)"""

    def test_lens_without_coatings(self):
        """Test lens without any coatings"""
        lens = self.Lens.create(self.valid_data)

        self.assertEqual(len(lens.coating_ids), 0)
        self.assertEqual(lens.coating_summary, 'No coatings')

    def test_lens_with_single_coating(self):
        """Test lens with single coating"""
        lens = self.Lens.create({
            **self.valid_data,
            'coating_ids': [(6, 0, [self.coating_ar.id])]
        })

        self.assertEqual(len(lens.coating_ids), 1)
        self.assertEqual(lens.coating_summary, 'AR')

    def test_lens_with_multiple_coatings(self):
        """Test lens with multiple coatings"""
        lens = self.Lens.create({
            **self.valid_data,
            'coating_ids': [(6, 0, [self.coating_ar.id, self.coating_hc.id, self.coating_uv.id])]
        })

        self.assertEqual(len(lens.coating_ids), 3)
        # Coating summary format: "AR+HC+UV" (order may vary)
        self.assertIn('AR', lens.coating_summary)
        self.assertIn('HC', lens.coating_summary)
        self.assertIn('UV', lens.coating_summary)

    def test_add_coating_after_creation(self):
        """Test adding coating after lens creation"""
        lens = self.Lens.create(self.valid_data)
        self.assertEqual(len(lens.coating_ids), 0)

        # Add coating
        lens.write({
            'coating_ids': [(4, self.coating_ar.id)]
        })

        self.assertEqual(len(lens.coating_ids), 1)
        self.assertIn(self.coating_ar, lens.coating_ids)

    def test_remove_coating(self):
        """Test removing coating from lens"""
        lens = self.Lens.create({
            **self.valid_data,
            'coating_ids': [(6, 0, [self.coating_ar.id, self.coating_hc.id])]
        })
        self.assertEqual(len(lens.coating_ids), 2)

        # Remove one coating
        lens.write({
            'coating_ids': [(3, self.coating_ar.id)]
        })

        self.assertEqual(len(lens.coating_ids), 1)
        self.assertNotIn(self.coating_ar, lens.coating_ids)
        self.assertIn(self.coating_hc, lens.coating_ids)


class TestPricingValidation(TestLensModel):
    """Test pricing validation"""

    def test_prices_positive(self):
        """Test positive prices are valid"""
        lens = self.Lens.create({
            **self.valid_data,
            'cost_price': 1000.0,
            'sale_price': 3000.0,
        })

        self.assertEqual(lens.cost_price, 1000.0)
        self.assertEqual(lens.sale_price, 3000.0)

    def test_prices_zero(self):
        """Test zero prices are valid"""
        lens = self.Lens.create({
            **self.valid_data,
            'cost_price': 0.0,
            'sale_price': 0.0,
        })

        self.assertEqual(lens.cost_price, 0.0)
        self.assertEqual(lens.sale_price, 0.0)

    def test_cost_price_negative(self):
        """Test negative cost price raises ValidationError"""
        with self.assertRaises(ValidationError) as context:
            self.Lens.create({
                **self.valid_data,
                'cost_price': -100.0,
            })

        self.assertIn('positive', str(context.exception).lower())

    def test_sale_price_negative(self):
        """Test negative sale price raises ValidationError"""
        with self.assertRaises(ValidationError) as context:
            self.Lens.create({
                **self.valid_data,
                'sale_price': -500.0,
            })

        self.assertIn('positive', str(context.exception).lower())


class TestDimensionsValidation(TestLensModel):
    """Test dimensions validation"""

    def test_dimensions_positive(self):
        """Test positive dimensions are valid"""
        lens = self.Lens.create({
            **self.valid_data,
            'diameter': 70.0,
            'center_thickness': 2.5,
            'weight': 15.5,
        })

        self.assertEqual(lens.diameter, 70.0)
        self.assertEqual(lens.center_thickness, 2.5)
        self.assertEqual(lens.weight, 15.5)

    def test_diameter_negative(self):
        """Test negative diameter raises ValidationError"""
        with self.assertRaises(ValidationError) as context:
            self.Lens.create({
                **self.valid_data,
                'diameter': -10.0,
            })

        self.assertIn('positive', str(context.exception).lower())

    def test_center_thickness_negative(self):
        """Test negative center thickness raises ValidationError"""
        with self.assertRaises(ValidationError) as context:
            self.Lens.create({
                **self.valid_data,
                'center_thickness': -2.0,
            })

        self.assertIn('positive', str(context.exception).lower())

    def test_weight_negative(self):
        """Test negative weight raises ValidationError"""
        with self.assertRaises(ValidationError) as context:
            self.Lens.create({
                **self.valid_data,
                'weight': -5.0,
            })

        self.assertIn('positive', str(context.exception).lower())


class TestSKUValidation(TestLensModel):
    """Test SKU uniqueness"""

    def test_sku_unique(self):
        """Test SKU must be unique"""
        # Create first lens with SKU
        lens1 = self.Lens.create({
            **self.valid_data,
            'sku': 'TEST-SKU-001',
        })

        self.assertEqual(lens1.sku, 'TEST-SKU-001')

        # Try to create second lens with same SKU
        with self.assertRaises(IntegrityError):
            self.Lens.create({
                **self.valid_data,
                'name': 'Another Lens',
                'sku': 'TEST-SKU-001',  # Duplicate SKU
            })

    def test_sku_optional(self):
        """Test SKU is optional"""
        lens = self.Lens.create({
            **self.valid_data,
            'sku': False,  # No SKU
        })

        self.assertFalse(lens.sku)


class TestBusinessLogic(TestLensModel):
    """Test business methods"""

    def test_display_name_with_all_fields(self):
        """Test display_name: 'Name (Type, Index)'"""
        lens = self.Lens.create({
            'name': 'Varilux Progressive',
            'type': 'progressive',
            'index': 1.67,
            'material': 'high_index',
        })

        self.assertEqual(lens.display_name, 'Varilux Progressive (Progressive, 1.67)')

    def test_display_name_without_type(self):
        """Test display_name fallback to name"""
        lens = self.Lens.create({
            'name': 'Test Lens',
            'type': False,
            'index': 1.5,
            'material': 'cr39',
        })

        # When type is missing, should fallback to name
        self.assertIn('Test Lens', lens.display_name)

    def test_coating_summary_empty(self):
        """Test coating_summary when no coatings"""
        lens = self.Lens.create(self.valid_data)

        self.assertEqual(lens.coating_summary, 'No coatings')

    def test_coating_summary_multiple(self):
        """Test coating_summary with multiple coatings"""
        lens = self.Lens.create({
            **self.valid_data,
            'coating_ids': [(6, 0, [self.coating_ar.id, self.coating_hc.id])]
        })

        # Should contain both codes separated by '+'
        self.assertIn('AR', lens.coating_summary)
        self.assertIn('HC', lens.coating_summary)
        self.assertIn('+', lens.coating_summary)

    def test_get_full_specification(self):
        """Test get_full_specification() method"""
        lens = self.Lens.create({
            'name': 'Complete Lens',
            'type': 'progressive',
            'index': 1.67,
            'material': 'high_index',
            'diameter': 70.0,
            'center_thickness': 2.0,
            'weight': 12.5,
            'manufacturer': 'Zeiss',
            'coating_ids': [(6, 0, [self.coating_ar.id, self.coating_uv.id])]
        })

        spec = lens.get_full_specification()

        # Check that specification contains key information
        self.assertIn('Progressive', spec)
        self.assertIn('1.67', spec)
        self.assertIn('High-Index', spec)
        self.assertIn('70.0', spec)
        self.assertIn('Zeiss', spec)
        self.assertIn('Anti-Reflective', spec)

    def test_archive_lens(self):
        """Test archiving lens (active=False)"""
        lens = self.Lens.create(self.valid_data)
        self.assertTrue(lens.active)

        # Archive
        lens.write({'active': False})

        self.assertFalse(lens.active)


class TestLensCoating(TestLensModel):
    """Test optics.lens.coating model"""

    def test_create_coating(self):
        """Test creating coating"""
        coating = self.Coating.create({
            'name': 'Blue Light Filter',
            'code': 'BLF',
            'description': 'Filters blue light from digital screens',
            'additional_cost': 800.0,
        })

        self.assertEqual(coating.name, 'Blue Light Filter')
        self.assertEqual(coating.code, 'BLF')
        self.assertEqual(coating.additional_cost, 800.0)

    def test_coating_code_unique(self):
        """Test coating code must be unique"""
        # First coating
        self.Coating.create({
            'name': 'Coating 1',
            'code': 'C1',
        })

        # Try to create second coating with same code
        with self.assertRaises(IntegrityError):
            self.Coating.create({
                'name': 'Coating 2',
                'code': 'C1',  # Duplicate code
            })

    def test_coating_sequence(self):
        """Test coating sequence for ordering"""
        coating1 = self.Coating.create({
            'name': 'Coating A',
            'code': 'CA',
            'sequence': 10,
        })

        coating2 = self.Coating.create({
            'name': 'Coating B',
            'code': 'CB',
            'sequence': 5,
        })

        # Coating with lower sequence should come first when ordered
        coatings = self.Coating.search([], order='sequence, name')
        self.assertEqual(coatings[0], coating2)  # sequence 5
        self.assertEqual(coatings[1], coating1)  # sequence 10


class TestEdgeCases(TestLensModel):
    """Test edge cases"""

    def test_index_boundary_values(self):
        """Test index at exact boundaries"""
        # Minimum boundary
        lens_min = self.Lens.create({
            **self.valid_data,
            'name': 'Min Index',
            'index': 1.50,
        })
        self.assertEqual(lens_min.index, 1.50)

        # Maximum boundary
        lens_max = self.Lens.create({
            **self.valid_data,
            'name': 'Max Index',
            'index': 1.90,
        })
        self.assertEqual(lens_max.index, 1.90)

    def test_all_lens_types(self):
        """Test creating all lens types"""
        types = ['single', 'bifocal', 'progressive']

        for lens_type in types:
            lens = self.Lens.create({
                **self.valid_data,
                'name': f'{lens_type.title()} Lens',
                'type': lens_type,
            })
            self.assertEqual(lens.type, lens_type)

    def test_all_materials(self):
        """Test creating all material types"""
        materials = ['cr39', 'polycarbonate', 'trivex', 'high_index']

        for material in materials:
            lens = self.Lens.create({
                **self.valid_data,
                'name': f'{material.upper()} Lens',
                'material': material,
            })
            self.assertEqual(lens.material, material)

    def test_lens_without_optional_fields(self):
        """Test lens with only required fields"""
        lens = self.Lens.create({
            'name': 'Minimal Lens',
            'type': 'single',
            'index': 1.5,
            'material': 'cr39',
        })

        self.assertIsNone(lens.cost_price)
        self.assertIsNone(lens.sale_price)
        self.assertIsNone(lens.diameter)
        self.assertIsNone(lens.center_thickness)
        self.assertIsNone(lens.weight)
        self.assertFalse(lens.manufacturer)
        self.assertFalse(lens.sku)

    def test_lens_with_all_fields(self):
        """Test lens with all fields populated"""
        lens = self.Lens.create({
            'name': 'Complete Lens',
            'type': 'progressive',
            'index': 1.74,
            'material': 'high_index',
            'cost_price': 5000.0,
            'sale_price': 15000.0,
            'diameter': 75.0,
            'center_thickness': 1.5,
            'weight': 8.0,
            'manufacturer': 'Zeiss',
            'sku': 'ZEISS-PROG-174',
            'description': 'Premium progressive lens',
            'notes': 'Internal note',
            'coating_ids': [(6, 0, [self.coating_ar.id, self.coating_hc.id, self.coating_uv.id])]
        })

        self.assertTrue(lens.id)
        self.assertEqual(len(lens.coating_ids), 3)
        self.assertEqual(lens.manufacturer, 'Zeiss')
