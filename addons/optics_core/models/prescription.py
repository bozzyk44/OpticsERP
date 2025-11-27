# -*- coding: utf-8 -*-
"""
Prescription Model - Optical Prescription

Author: AI Agent
Created: 2025-10-09
Task: OPTERP-32
Reference: CLAUDE.md §3.2, GLOSSARY.md (Prescription)

Purpose:
Model for storing optical prescriptions with validation for:
- Sphere (Sph): -20 to +20, step 0.25
- Cylinder (Cyl): -4 to 0, step 0.25
- Axis: 1-180° (required if Cyl ≠ 0)
- Add: 0.75-3.0 (for progressive lenses)
- PD (Pupillary Distance): 56-72 mm

Business Rules:
- Cyl must be ≤0 (negative or zero)
- Axis required if Cyl ≠ 0
- Sph/Cyl values must be in 0.25 steps
- PD must be in valid range (56-72mm)
"""

from odoo import models, fields, api
from odoo.exceptions import ValidationError
import re


class OpticsPrescription(models.Model):
    """Optical Prescription model"""

    _name = 'optics.prescription'
    _description = 'Optical Prescription'
    _order = 'date desc, id desc'
    _rec_name = 'display_name'

    # ==================
    # Fields
    # ==================

    # Patient/Customer info
    patient_name = fields.Char(
        string='Patient Name',
        required=True,
        help='Full name of patient'
    )

    patient_id = fields.Many2one(
        comodel_name='res.partner',
        string='Patient',
        help='Link to customer/patient record',
        ondelete='restrict'
    )

    date = fields.Date(
        string='Prescription Date',
        required=True,
        default=fields.Date.context_today,
        help='Date when prescription was issued'
    )

    # Right Eye (OD - Oculus Dexter)
    od_sph = fields.Float(
        string='OD Sphere',
        digits=(3, 2),
        help='Right eye sphere: -20.00 to +20.00'
    )

    od_cyl = fields.Float(
        string='OD Cylinder',
        digits=(3, 2),
        help='Right eye cylinder: -4.00 to 0.00'
    )

    od_axis = fields.Integer(
        string='OD Axis',
        help='Right eye axis: 1-180°'
    )

    od_add = fields.Float(
        string='OD Add',
        digits=(2, 2),
        help='Right eye addition for progressive lenses: 0.75-3.00'
    )

    # Left Eye (OS - Oculus Sinister)
    os_sph = fields.Float(
        string='OS Sphere',
        digits=(3, 2),
        help='Left eye sphere: -20.00 to +20.00'
    )

    os_cyl = fields.Float(
        string='OS Cylinder',
        digits=(3, 2),
        help='Left eye cylinder: -4.00 to 0.00'
    )

    os_axis = fields.Integer(
        string='OS Axis',
        help='Left eye axis: 1-180°'
    )

    os_add = fields.Float(
        string='OS Add',
        digits=(2, 2),
        help='Left eye addition for progressive lenses: 0.75-3.00'
    )

    # Pupillary Distance
    pd = fields.Float(
        string='PD (mm)',
        digits=(4, 1),
        help='Pupillary Distance: 56.0-72.0 mm'
    )

    pd_right = fields.Float(
        string='PD Right (mm)',
        digits=(3, 1),
        help='Right monocular PD'
    )

    pd_left = fields.Float(
        string='PD Left (mm)',
        digits=(3, 1),
        help='Left monocular PD'
    )

    # Additional fields
    prism_od = fields.Char(
        string='OD Prism',
        help='Right eye prism (e.g., "2.0 BI")'
    )

    prism_os = fields.Char(
        string='OS Prism',
        help='Left eye prism (e.g., "1.5 BU")'
    )

    notes = fields.Text(
        string='Notes',
        help='Additional notes or special instructions'
    )

    active = fields.Boolean(
        string='Active',
        default=True,
        help='Set to False to archive prescription'
    )

    # Computed field for display
    display_name = fields.Char(
        string='Display Name',
        compute='_compute_display_name',
        store=True
    )

    # ==================
    # Computed Methods
    # ==================

    @api.depends('patient_name', 'date')
    def _compute_display_name(self):
        """Compute display name: Patient Name - Date"""
        for record in self:
            if record.patient_name and record.date:
                record.display_name = f"{record.patient_name} - {record.date}"
            elif record.patient_name:
                record.display_name = record.patient_name
            else:
                record.display_name = f"Prescription {record.id or 'New'}"

    # ==================
    # Validation Methods
    # ==================

    @api.constrains('od_sph', 'os_sph')
    def _check_sph_range(self):
        """Validate Sphere range: -20.00 to +20.00"""
        for record in self:
            if record.od_sph and not (-20.0 <= record.od_sph <= 20.0):
                raise ValidationError(
                    f"OD Sphere must be between -20.00 and +20.00 (got {record.od_sph})"
                )
            if record.os_sph and not (-20.0 <= record.os_sph <= 20.0):
                raise ValidationError(
                    f"OS Sphere must be between -20.00 and +20.00 (got {record.os_sph})"
                )

    @api.constrains('od_sph', 'os_sph', 'od_cyl', 'os_cyl')
    def _check_quarter_step(self):
        """Validate Sph/Cyl are in 0.25 steps"""
        for record in self:
            # Check OD Sph
            if record.od_sph and (record.od_sph * 4) % 1 != 0:
                raise ValidationError(
                    f"OD Sphere must be in 0.25 steps (got {record.od_sph})"
                )

            # Check OS Sph
            if record.os_sph and (record.os_sph * 4) % 1 != 0:
                raise ValidationError(
                    f"OS Sphere must be in 0.25 steps (got {record.os_sph})"
                )

            # Check OD Cyl
            if record.od_cyl and (record.od_cyl * 4) % 1 != 0:
                raise ValidationError(
                    f"OD Cylinder must be in 0.25 steps (got {record.od_cyl})"
                )

            # Check OS Cyl
            if record.os_cyl and (record.os_cyl * 4) % 1 != 0:
                raise ValidationError(
                    f"OS Cylinder must be in 0.25 steps (got {record.os_cyl})"
                )

    @api.constrains('od_cyl', 'os_cyl')
    def _check_cyl_negative_or_zero(self):
        """Validate Cylinder ≤ 0 (negative or zero)"""
        for record in self:
            if record.od_cyl and record.od_cyl > 0:
                raise ValidationError(
                    f"OD Cylinder must be ≤ 0 (got {record.od_cyl})"
                )
            if record.os_cyl and record.os_cyl > 0:
                raise ValidationError(
                    f"OS Cylinder must be ≤ 0 (got {record.os_cyl})"
                )

    @api.constrains('od_cyl', 'os_cyl')
    def _check_cyl_range(self):
        """Validate Cylinder range: -4.00 to 0.00"""
        for record in self:
            if record.od_cyl and not (-4.0 <= record.od_cyl <= 0.0):
                raise ValidationError(
                    f"OD Cylinder must be between -4.00 and 0.00 (got {record.od_cyl})"
                )
            if record.os_cyl and not (-4.0 <= record.os_cyl <= 0.0):
                raise ValidationError(
                    f"OS Cylinder must be between -4.00 and 0.00 (got {record.os_cyl})"
                )

    @api.constrains('od_cyl', 'od_axis', 'os_cyl', 'os_axis')
    def _check_axis_required_if_cyl(self):
        """Validate Axis is required if Cyl ≠ 0"""
        for record in self:
            # OD: If Cyl exists and ≠ 0, Axis required
            if record.od_cyl and record.od_cyl != 0 and not record.od_axis:
                raise ValidationError(
                    "OD Axis is required when OD Cylinder is not zero"
                )

            # OS: If Cyl exists and ≠ 0, Axis required
            if record.os_cyl and record.os_cyl != 0 and not record.os_axis:
                raise ValidationError(
                    "OS Axis is required when OS Cylinder is not zero"
                )

    @api.constrains('od_axis', 'os_axis')
    def _check_axis_range(self):
        """Validate Axis range: 1-180°"""
        for record in self:
            if record.od_axis and not (1 <= record.od_axis <= 180):
                raise ValidationError(
                    f"OD Axis must be between 1 and 180 (got {record.od_axis})"
                )
            if record.os_axis and not (1 <= record.os_axis <= 180):
                raise ValidationError(
                    f"OS Axis must be between 1 and 180 (got {record.os_axis})"
                )

    @api.constrains('od_add', 'os_add')
    def _check_add_range(self):
        """Validate Add range: 0.75-3.00"""
        for record in self:
            if record.od_add and not (0.75 <= record.od_add <= 3.0):
                raise ValidationError(
                    f"OD Add must be between 0.75 and 3.00 (got {record.od_add})"
                )
            if record.os_add and not (0.75 <= record.os_add <= 3.0):
                raise ValidationError(
                    f"OS Add must be between 0.75 and 3.00 (got {record.os_add})"
                )

    @api.constrains('pd')
    def _check_pd_range(self):
        """Validate PD range: 56.0-72.0 mm"""
        for record in self:
            if record.pd and not (56.0 <= record.pd <= 72.0):
                raise ValidationError(
                    f"PD must be between 56.0 and 72.0 mm (got {record.pd})"
                )

    @api.constrains('pd_right', 'pd_left')
    def _check_monocular_pd_range(self):
        """Validate monocular PD range: 28.0-36.0 mm"""
        for record in self:
            if record.pd_right and not (28.0 <= record.pd_right <= 36.0):
                raise ValidationError(
                    f"Right PD must be between 28.0 and 36.0 mm (got {record.pd_right})"
                )
            if record.pd_left and not (28.0 <= record.pd_left <= 36.0):
                raise ValidationError(
                    f"Left PD must be between 28.0 and 36.0 mm (got {record.pd_left})"
                )

    # ==================
    # SQL Constraints
    # ==================

    _sql_constraints = [
        (
            'check_od_sph_range',
            'CHECK (od_sph IS NULL OR (od_sph >= -20.0 AND od_sph <= 20.0))',
            'OD Sphere must be between -20.00 and +20.00'
        ),
        (
            'check_os_sph_range',
            'CHECK (os_sph IS NULL OR (os_sph >= -20.0 AND os_sph <= 20.0))',
            'OS Sphere must be between -20.00 and +20.00'
        ),
        (
            'check_od_cyl_range',
            'CHECK (od_cyl IS NULL OR (od_cyl >= -4.0 AND od_cyl <= 0.0))',
            'OD Cylinder must be between -4.00 and 0.00'
        ),
        (
            'check_os_cyl_range',
            'CHECK (os_cyl IS NULL OR (os_cyl >= -4.0 AND os_cyl <= 0.0))',
            'OS Cylinder must be between -4.00 and 0.00'
        ),
        (
            'check_od_axis_range',
            'CHECK (od_axis IS NULL OR (od_axis >= 1 AND od_axis <= 180))',
            'OD Axis must be between 1 and 180'
        ),
        (
            'check_os_axis_range',
            'CHECK (os_axis IS NULL OR (os_axis >= 1 AND os_axis <= 180))',
            'OS Axis must be between 1 and 180'
        ),
        (
            'check_od_add_range',
            'CHECK (od_add IS NULL OR (od_add >= 0.75 AND od_add <= 3.0))',
            'OD Add must be between 0.75 and 3.00'
        ),
        (
            'check_os_add_range',
            'CHECK (os_add IS NULL OR (os_add >= 0.75 AND os_add <= 3.0))',
            'OS Add must be between 0.75 and 3.00'
        ),
        (
            'check_pd_range',
            'CHECK (pd IS NULL OR (pd >= 56.0 AND pd <= 72.0))',
            'PD must be between 56.0 and 72.0 mm'
        ),
    ]

    # ==================
    # Business Methods
    # ==================

    def format_prescription(self):
        """Format prescription as readable string"""
        self.ensure_one()

        lines = []

        # Right Eye
        if self.od_sph or self.od_cyl:
            od_str = f"OD: Sph {self.od_sph:+.2f}" if self.od_sph else "OD: Sph 0.00"
            if self.od_cyl:
                od_str += f" Cyl {self.od_cyl:+.2f} Axis {self.od_axis}°"
            if self.od_add:
                od_str += f" Add {self.od_add:.2f}"
            lines.append(od_str)

        # Left Eye
        if self.os_sph or self.os_cyl:
            os_str = f"OS: Sph {self.os_sph:+.2f}" if self.os_sph else "OS: Sph 0.00"
            if self.os_cyl:
                os_str += f" Cyl {self.os_cyl:+.2f} Axis {self.os_axis}°"
            if self.os_add:
                os_str += f" Add {self.os_add:.2f}"
            lines.append(os_str)

        # PD
        if self.pd:
            lines.append(f"PD: {self.pd:.1f} mm")
        elif self.pd_right and self.pd_left:
            lines.append(f"PD: {self.pd_right:.1f}/{self.pd_left:.1f} mm")

        return "\n".join(lines) if lines else "No prescription data"
