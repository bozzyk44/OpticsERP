# -*- coding: utf-8 -*-
"""
Create Odoo users with appropriate roles
Run inside Odoo container: python3 /tmp/create_users.py
"""
import odoo
from odoo import api, SUPERUSER_ID

# Initialize Odoo
odoo.tools.config.parse_config(['-c', '/etc/odoo/odoo.conf', '-d', 'odoo_production'])
registry = odoo.registry('odoo_production')

with registry.cursor() as cr:
    env = api.Environment(cr, SUPERUSER_ID, {})

    # Get required groups
    group_user = env.ref('base.group_user')  # Internal User

    # Sales groups
    group_sale_user = env.ref('sales_team.group_sale_salesman', raise_if_not_found=False)
    group_sale_manager = env.ref('sales_team.group_sale_salesman_all_leads', raise_if_not_found=False)

    # POS groups
    group_pos_user = env.ref('point_of_sale.group_pos_user', raise_if_not_found=False)
    group_pos_manager = env.ref('point_of_sale.group_pos_manager', raise_if_not_found=False)

    # Stock groups
    group_stock_user = env.ref('stock.group_stock_user', raise_if_not_found=False)
    group_stock_manager = env.ref('stock.group_stock_manager', raise_if_not_found=False)

    # Accounting groups
    group_account_invoice = env.ref('account.group_account_invoice', raise_if_not_found=False)
    group_account_user = env.ref('account.group_account_user', raise_if_not_found=False)
    group_account_manager = env.ref('account.group_account_manager', raise_if_not_found=False)

    # Admin group
    group_erp_manager = env.ref('base.group_erp_manager', raise_if_not_found=False)

    print('Groups loaded successfully')

    users_data = [
        {
            'name': 'Администратор магазина',
            'login': 'store_admin',
            'password': 'StoreAdmin2026!',
            'groups': [group_user, group_pos_manager, group_sale_manager, group_stock_manager, group_erp_manager],
            'lang': 'ru_RU',
        },
        {
            'name': 'Продавец',
            'login': 'seller',
            'password': 'Seller2026!',
            'groups': [group_user, group_pos_user, group_sale_user],
            'lang': 'ru_RU',
        },
        {
            'name': 'Товаровед',
            'login': 'stock_manager',
            'password': 'Stock2026!',
            'groups': [group_user, group_stock_manager, group_sale_user],
            'lang': 'ru_RU',
        },
        {
            'name': 'Бухгалтер',
            'login': 'accountant',
            'password': 'Account2026!',
            'groups': [group_user, group_account_manager, group_account_invoice],
            'lang': 'ru_RU',
        },
    ]

    ResUsers = env['res.users']

    for ud in users_data:
        existing = ResUsers.search([('login', '=', ud['login'])])
        group_ids = [g.id for g in ud['groups'] if g]

        if existing:
            existing.write({
                'name': ud['name'],
                'password': ud['password'],
                'groups_id': [(6, 0, group_ids)],
                'lang': ud['lang'],
            })
            print(f"Updated: {ud['login']}")
        else:
            ResUsers.create({
                'name': ud['name'],
                'login': ud['login'],
                'password': ud['password'],
                'groups_id': [(6, 0, group_ids)],
                'lang': ud['lang'],
            })
            print(f"Created: {ud['login']}")

    cr.commit()
    print('\n=== All users created successfully ===')
