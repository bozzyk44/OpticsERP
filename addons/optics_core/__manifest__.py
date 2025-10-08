# -*- coding: utf-8 -*-
{
    'name': 'Optics Core',
    'version': '17.0.1.0.0',
    'category': 'Sales',
    'summary': 'Core models for optical network: prescriptions, lenses, manufacturing orders',
    'description': """
        Optics Core Module
        ==================

        Core domain entities for optical retail network:
        * Prescriptions (рецепты): Sph, Cyl, Axis, PD, Add, Prism
        * Lenses (линзы): types, index, coatings
        * Manufacturing Orders (заказы на изготовление): workflow management

        Part of OpticsERP offline-first POS system.
    """,
    'author': 'OpticsERP Team',
    'website': 'https://github.com/opticserp/opticserp',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'product',
        'sale',
        'stock',
    ],
    'data': [
        # Security
        'security/ir.model.access.csv',

        # Views
        'views/prescription_views.xml',
        'views/lens_views.xml',
        'views/manufacturing_order_views.xml',
        'views/menu_views.xml',

        # Reports
        'reports/order_label_template.xml',
    ],
    'demo': [],
    'installable': True,
    'application': True,
    'auto_install': False,
}
