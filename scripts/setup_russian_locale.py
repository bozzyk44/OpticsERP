#!/usr/bin/env python3
"""
Script to configure Russian locale settings in Odoo
Sets date/time/currency formats according to Russian standards
"""

import xmlrpc.client
import sys

# Odoo connection parameters
ODOO_URL = "http://localhost:8069"
DB_NAME = "opticserp"
USERNAME = "admin"
PASSWORD = "admin"

def configure_russian_locale():
    """Configure Russian locale settings"""

    print("=== Configuring Russian Locale in Odoo ===\n")

    # Connect to Odoo
    print("1. Connecting to Odoo...")
    common = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/common')

    try:
        uid = common.authenticate(DB_NAME, USERNAME, PASSWORD, {})
        if not uid:
            print("❌ Authentication failed!")
            return False
        print(f"✅ Connected as user ID: {uid}\n")
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False

    # Get models proxy
    models = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/object')

    # 2. Activate Russian language
    print("2. Activating Russian language...")
    try:
        lang_ids = models.execute_kw(
            DB_NAME, uid, PASSWORD,
            'res.lang', 'search',
            [[['code', '=', 'ru_RU']]]
        )

        if lang_ids:
            models.execute_kw(
                DB_NAME, uid, PASSWORD,
                'res.lang', 'write',
                [lang_ids, {'active': True}]
            )
            print("✅ Russian language activated\n")
        else:
            print("⚠️  Russian language not found in database\n")
    except Exception as e:
        print(f"❌ Failed to activate Russian: {e}\n")

    # 3. Configure Russian regional settings
    print("3. Configuring Russian regional settings...")
    try:
        lang_ids = models.execute_kw(
            DB_NAME, uid, PASSWORD,
            'res.lang', 'search',
            [[['code', '=', 'ru_RU']]]
        )

        if lang_ids:
            # Russian standards:
            # - Date: dd.mm.yyyy (30.11.2025)
            # - Time: HH:MM:SS (24-hour)
            # - Numbers: 1 234,56 (space thousands, comma decimal)
            # - Currency: 1 234,56 ₽ (symbol after amount)

            models.execute_kw(
                DB_NAME, uid, PASSWORD,
                'res.lang', 'write',
                [lang_ids, {
                    'date_format': '%d.%m.%Y',           # 30.11.2025
                    'time_format': '%H:%M:%S',           # 14:30:00
                    'decimal_point': ',',                # Comma for decimals
                    'thousands_sep': '\u00A0',           # Non-breaking space (U+00A0)
                    'week_start': '1',                   # Monday (ISO 8601)
                }]
            )
            print("✅ Regional settings configured:")
            print("   - Date format: dd.mm.yyyy")
            print("   - Time format: HH:MM:SS (24-hour)")
            print("   - Decimal point: , (comma)")
            print("   - Thousands separator: (space)")
            print("   - Week start: Monday\n")
        else:
            print("⚠️  Russian language not found\n")
    except Exception as e:
        print(f"❌ Failed to configure regional settings: {e}\n")

    # 4. Set Russian as default language for admin user
    print("4. Setting Russian as default language for admin...")
    try:
        user_ids = models.execute_kw(
            DB_NAME, uid, PASSWORD,
            'res.users', 'search',
            [[['login', '=', 'admin']]]
        )

        if user_ids:
            models.execute_kw(
                DB_NAME, uid, PASSWORD,
                'res.users', 'write',
                [user_ids, {'lang': 'ru_RU'}]
            )
            print("✅ Admin user language set to Russian\n")
    except Exception as e:
        print(f"❌ Failed to set user language: {e}\n")

    # 5. Configure currency (RUB - Russian Ruble)
    print("5. Checking Russian Ruble currency...")
    try:
        currency_ids = models.execute_kw(
            DB_NAME, uid, PASSWORD,
            'res.currency', 'search',
            [[['name', '=', 'RUB']]]
        )

        if currency_ids:
            # Activate RUB currency
            models.execute_kw(
                DB_NAME, uid, PASSWORD,
                'res.currency', 'write',
                [currency_ids, {'active': True}]
            )
            print("✅ Russian Ruble (RUB) currency activated\n")

            # Get currency details
            currency = models.execute_kw(
                DB_NAME, uid, PASSWORD,
                'res.currency', 'read',
                [currency_ids, ['name', 'symbol', 'position', 'rounding']]
            )
            if currency:
                print(f"   Currency: {currency[0]['name']}")
                print(f"   Symbol: {currency[0]['symbol']}")
                print(f"   Position: {currency[0]['position']}")
                print(f"   Rounding: {currency[0]['rounding']}\n")
        else:
            print("⚠️  Russian Ruble currency not found\n")
    except Exception as e:
        print(f"❌ Failed to configure currency: {e}\n")

    print("="*50)
    print("✅ Russian locale configuration complete!\n")
    print("Next steps:")
    print("1. Export translatable strings from custom modules")
    print("2. Translate .po files")
    print("3. Import translations back to Odoo")
    print("4. Test UI in Russian\n")

    return True

if __name__ == '__main__':
    success = configure_russian_locale()
    sys.exit(0 if success else 1)
