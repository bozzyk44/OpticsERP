# -*- coding: utf-8 -*-
"""
Lens Model - Optical Lens Catalog

Author: AI Agent
Created: 2025-11-27
Task: OPTERP-34
Reference: CLAUDE.md §3.2, GLOSSARY.md (Lens)

Purpose:
Model for optical lens catalog with specifications:
- Type: Single Vision, Bifocal, Progressive
- Index: 1.5 (standard), 1.6 (thin), 1.67 (ultra-thin), 1.74 (super-thin)
- Material: CR-39, Polycarbonate, Trivex, High-Index
- Coatings: AR (Anti-Reflective), HC (Hard Coating), UV, Photochromic

Business Rules:
- Index range: 1.5-1.9 (step 0.01)
- Material affects weight and durability
- Coatings can be combined (many2many)
- Price varies by type, index, coatings
"""

from odoo import models, fields, api
from odoo.exceptions import ValidationError


class OpticsLens(models.Model):
    """Optical Lens model"""

    _name = 'optics.lens'
    _description = 'Optical Lens'
    _order = 'type, index, name'
    _rec_name = 'name'

    # ==================
    # Fields
    # ==================

    # Basic Information
    name = fields.Char(
        string='Name',
        required=True,
        help='Lens product name (e.g., "Zeiss Progressive 1.67 AR+UV")'
    )

    active = fields.Boolean(
        string='Active',
        default=True,
        help='Set to False to archive lens'
    )

    # Lens Type
    type = fields.Selection(
        selection=[
            ('single', 'Single Vision'),
            ('bifocal', 'Bifocal'),
            ('progressive', 'Progressive')
        ],
        string='Lens Type',
        required=True,
        default='single',
        help='Type of lens: Single Vision (одна зона), Bifocal (2 зоны), Progressive (плавный переход)'
    )

    # Refractive Index
    index = fields.Float(
        string='Refractive Index',
        required=True,
        default=1.5,
        digits=(3, 2),
        help='Index of refraction: 1.5 (standard), 1.6 (thin), 1.67 (ultra-thin), 1.74 (super-thin)'
    )

    # Material
    material = fields.Selection(
        selection=[
            ('cr39', 'CR-39 (Plastic)'),
            ('polycarbonate', 'Polycarbonate'),
            ('trivex', 'Trivex'),
            ('high_index', 'High-Index Glass')
        ],
        string='Material',
        required=True,
        default='cr39',
        help='Lens material affects weight, durability, and optical clarity'
    )

    # Coatings (many2many - multiple coatings can be applied)
    coating_ids = fields.Many2many(
        comodel_name='optics.lens.coating',
        relation='optics_lens_coating_rel',
        column1='lens_id',
        column2='coating_id',
        string='Coatings',
        help='Applied coatings: AR (Anti-Reflective), HC (Hard Coating), UV, Photochromic'
    )

    # Pricing
    cost_price = fields.Float(
        string='Cost Price',
        digits='Product Price',
        help='Purchase cost from supplier'
    )

    sale_price = fields.Float(
        string='Sale Price',
        digits='Product Price',
        help='Retail price for customers'
    )

    # Dimensions and Weight
    diameter = fields.Float(
        string='Diameter (mm)',
        help='Lens diameter in millimeters'
    )

    center_thickness = fields.Float(
        string='Center Thickness (mm)',
        digits=(4, 2),
        help='Center thickness in millimeters'
    )

    weight = fields.Float(
        string='Weight (g)',
        digits=(5, 2),
        help='Lens weight in grams'
    )

    # Manufacturer and SKU
    manufacturer = fields.Char(
        string='Manufacturer',
        help='Lens manufacturer (e.g., Zeiss, Essilor, Hoya)'
    )

    sku = fields.Char(
        string='SKU',
        help='Stock Keeping Unit / Product Code'
    )

    # Additional Information
    description = fields.Text(
        string='Description',
        help='Detailed lens description, features, and specifications'
    )

    notes = fields.Text(
        string='Internal Notes',
        help='Internal notes for staff (not visible to customers)'
    )

    # Computed Fields
    display_name = fields.Char(
        string='Display Name',
        compute='_compute_display_name',
        store=True
    )

    coating_summary = fields.Char(
        string='Coatings',
        compute='_compute_coating_summary',
        store=False,
        help='Summary of applied coatings'
    )

    # ==================
    # Computed Methods
    # ==================

    @api.depends('name', 'type', 'index')
    def _compute_display_name(self):
        """Compute display name: Name (Type, Index)"""
        for record in self:
            type_label = dict(record._fields['type'].selection).get(record.type, '')
            if record.name and record.type and record.index:
                record.display_name = f"{record.name} ({type_label}, {record.index})"
            elif record.name:
                record.display_name = record.name
            else:
                record.display_name = f"Lens {record.id or 'New'}"

    @api.depends('coating_ids')
    def _compute_coating_summary(self):
        """Compute coating summary: AR+HC+UV"""
        for record in self:
            if record.coating_ids:
                coating_codes = record.coating_ids.mapped('code')
                record.coating_summary = '+'.join(coating_codes)
            else:
                record.coating_summary = 'No coatings'

    # ==================
    # Validation Methods
    # ==================

    @api.constrains('index')
    def _check_index_range(self):
        """Validate refractive index range: 1.5-1.9"""
        for record in self:
            if record.index and not (1.5 <= record.index <= 1.9):
                raise ValidationError(
                    f"Refractive index must be between 1.5 and 1.9 (got {record.index})"
                )

    @api.constrains('cost_price', 'sale_price')
    def _check_prices_positive(self):
        """Validate prices are positive"""
        for record in self:
            if record.cost_price and record.cost_price < 0:
                raise ValidationError(
                    f"Cost price must be positive (got {record.cost_price})"
                )
            if record.sale_price and record.sale_price < 0:
                raise ValidationError(
                    f"Sale price must be positive (got {record.sale_price})"
                )

    @api.constrains('diameter', 'center_thickness', 'weight')
    def _check_dimensions_positive(self):
        """Validate dimensions and weight are positive"""
        for record in self:
            if record.diameter and record.diameter <= 0:
                raise ValidationError(
                    f"Diameter must be positive (got {record.diameter})"
                )
            if record.center_thickness and record.center_thickness <= 0:
                raise ValidationError(
                    f"Center thickness must be positive (got {record.center_thickness})"
                )
            if record.weight and record.weight <= 0:
                raise ValidationError(
                    f"Weight must be positive (got {record.weight})"
                )

    # ==================
    # SQL Constraints
    # ==================

    _sql_constraints = [
        (
            'check_index_range',
            'CHECK (index >= 1.5 AND index <= 1.9)',
            'Refractive index must be between 1.5 and 1.9'
        ),
        (
            'check_cost_price_positive',
            'CHECK (cost_price IS NULL OR cost_price >= 0)',
            'Cost price must be positive'
        ),
        (
            'check_sale_price_positive',
            'CHECK (sale_price IS NULL OR sale_price >= 0)',
            'Sale price must be positive'
        ),
        (
            'unique_sku',
            'UNIQUE(sku)',
            'SKU must be unique'
        ),
    ]

    # ==================
    # Business Methods
    # ==================

    def get_full_specification(self):
        """Get full lens specification as formatted string"""
        self.ensure_one()

        lines = []

        # Type and Index
        type_label = dict(self._fields['type'].selection).get(self.type, '')
        lines.append(f"Type: {type_label}")
        lines.append(f"Index: {self.index}")

        # Material
        material_label = dict(self._fields['material'].selection).get(self.material, '')
        lines.append(f"Material: {material_label}")

        # Coatings
        if self.coating_ids:
            coatings = ', '.join(self.coating_ids.mapped('name'))
            lines.append(f"Coatings: {coatings}")

        # Dimensions
        if self.diameter:
            lines.append(f"Diameter: {self.diameter} mm")
        if self.center_thickness:
            lines.append(f"Thickness: {self.center_thickness} mm")
        if self.weight:
            lines.append(f"Weight: {self.weight} g")

        # Manufacturer
        if self.manufacturer:
            lines.append(f"Manufacturer: {self.manufacturer}")

        return "\n".join(lines) if lines else "No specification available"


class OpticsLensCoating(models.Model):
    """Lens Coating model (for many2many relation)"""

    _name = 'optics.lens.coating'
    _description = 'Lens Coating'
    _order = 'sequence, name'

    # ==================
    # Fields
    # ==================

    name = fields.Char(
        string='Coating Name',
        required=True,
        help='Full coating name (e.g., "Anti-Reflective Coating")'
    )

    code = fields.Char(
        string='Code',
        required=True,
        help='Short code (e.g., "AR", "HC", "UV")'
    )

    description = fields.Text(
        string='Description',
        help='Coating benefits and features'
    )

    sequence = fields.Integer(
        string='Sequence',
        default=10,
        help='Display order'
    )

    active = fields.Boolean(
        string='Active',
        default=True
    )

    # Additional cost for this coating
    additional_cost = fields.Float(
        string='Additional Cost',
        digits='Product Price',
        help='Additional cost added to lens price'
    )

    # ==================
    # SQL Constraints
    # ==================

    _sql_constraints = [
        (
            'unique_code',
            'UNIQUE(code)',
            'Coating code must be unique'
        ),
    ]
