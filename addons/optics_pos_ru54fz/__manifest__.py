# -*- coding: utf-8 -*-
{
    'name': 'Optics POS (54-ФЗ)',
    'version': '17.0.1.0.0',
    'category': 'Point of Sale',
    'summary': 'POS module with 54-ФЗ compliance and offline-first mode',
    'description': """
        Optics POS with 54-ФЗ Compliance
        ================================

        Features:
        * Integration with KKT adapter (fiscal printing)
        * X/Z reports (correct FFD 1.2 tags)
        * Electronic receipts (email/SMS)
        * Offline mode UI (buffer indicator, alerts)
        * Two-phase fiscalization support

        Compliance:
        * 54-ФЗ (Russian fiscal law)
        * FFD 1.2 (Fiscal Data Format)

        Part of OpticsERP offline-first POS system.
    """,
    'author': 'OpticsERP Team',
    'website': 'https://github.com/opticserp/opticserp',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'point_of_sale',
        'optics_core',
    ],
    'data': [
        # Security
        'security/ir.model.access.csv',

        # Views
        'views/pos_session_views.xml',
        'views/pos_config_views.xml',
        'views/offline_buffer_views.xml',

        # Reports
        'reports/x_report_template.xml',
        'reports/z_report_template.xml',
    ],
    'assets': {
        'point_of_sale.assets': [
            # JavaScript
            'optics_pos_ru54fz/static/src/js/offline_indicator.js',
            'optics_pos_ru54fz/static/src/js/kkt_adapter_client.js',
            'optics_pos_ru54fz/static/src/js/refund_saga.js',

            # XML Templates
            'optics_pos_ru54fz/static/src/xml/offline_indicator.xml',

            # Styles
            'optics_pos_ru54fz/static/src/scss/offline_indicator.scss',
        ],
    },
    'demo': [],
    'installable': True,
    'application': False,
    'auto_install': False,
}
