# -*- coding: utf-8 -*-
{
    'name': 'RU Accounting Extras',
    'version': '17.0.1.0.0',
    'category': 'Accounting',
    'summary': 'Cash accounts per location, GP reporting, profit by store',
    'description': """
        RU Accounting Extras
        ====================

        Features:
        * Cash accounts per location (store cash, collection accounts)
        * Cash transfers between accounts
        * Gross Profit (GP) report by category
        * Profit by location report
        * Integration with POS for GP calculation

        Designed for multi-location retail networks in Russia.

        Part of OpticsERP offline-first POS system.
    """,
    'author': 'OpticsERP Team',
    'website': 'https://github.com/opticserp/opticserp',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'account',
        'point_of_sale',
        'sale',
    ],
    'data': [
        # Data
        'data/sequence.xml',

        # Security
        'security/ir.model.access.csv',

        # Views
        'views/cash_transfer_views.xml',
        'views/account_views.xml',

        # Reports (must be loaded before menu_views.xml because menu references these actions)
        'reports/gp_report_views.xml',
        'reports/profit_by_location_views.xml',

        # Menu (must be last because it references actions from reports)
        'views/menu_views.xml',
    ],
    'demo': [],
    'installable': True,
    'application': False,
    'auto_install': False,
}
