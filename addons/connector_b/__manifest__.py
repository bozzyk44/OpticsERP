# -*- coding: utf-8 -*-
{
    'name': 'Connector B (Excel/CSV Import)',
    'version': '17.0.1.0.0',
    'category': 'Sales',
    'summary': 'Import supplier catalogs from Excel/CSV with validation',
    'description': """
        Connector B — Excel/CSV Import
        ===============================

        Features:
        * Import supplier price lists (Excel/CSV)
        * Mapping profiles for 3+ suppliers
        * Import preview with pagination
        * Upsert mode (create/update products)
        * Validation and error reporting
        * Block import when offline buffers not synced

        Supported formats:
        * XLSX (Excel 2007+)
        * CSV (UTF-8, Windows-1251)

        Part of OpticsERP offline-first POS system.
    """,
    'author': 'OpticsERP Team',
    'website': 'https://github.com/opticserp/opticserp',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'product',
        'stock',
    ],
    'data': [
        # Security
        'security/ir.model.access.csv',

        # Data
        'data/ir_sequence_data.xml',
    ],
    'demo': [],
    'installable': True,
    'application': False,
    'auto_install': False,
}
