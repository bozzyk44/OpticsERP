#!/usr/bin/env python3
"""
Script to load Russian translations directly into Odoo database
Uses XML-RPC API to create translation records
"""

import xmlrpc.client
import sys

# Odoo connection parameters
ODOO_URL = "http://localhost:8069"
DB_NAME = "opticserp"
USERNAME = "admin"
PASSWORD = "admin"

# Translation data for optics_core module
TRANSLATIONS_OPTICS_CORE = [
    # Model names
    ("model", "optics.prescription,name", "Optical Prescription", "Рецепт"),
    ("model", "optics.lens,name", "Lens", "Линза"),
    ("model", "optics.lens.coating,name", "Lens Coating", "Покрытие линзы"),
    ("model", "optics.manufacturing.order,name", "Optical Manufacturing Order", "Заказ на изготовление"),

    # Field labels - Prescription
    ("field", "optics.prescription,patient_name", "Patient Name", "Имя пациента"),
    ("field", "optics.prescription,sph_right", "Sphere (Right)", "Сфера (правый)"),
    ("field", "optics.prescription,sph_left", "Sphere (Left)", "Сфера (левый)"),
    ("field", "optics.prescription,cyl_right", "Cylinder (Right)", "Цилиндр (правый)"),
    ("field", "optics.prescription,cyl_left", "Cylinder (Left)", "Цилиндр (левый)"),
    ("field", "optics.prescription,axis_right", "Axis (Right)", "Ось (правый)"),
    ("field", "optics.prescription,axis_left", "Axis (Left)", "Ось (левый)"),
    ("field", "optics.prescription,pd", "Pupillary Distance", "Межзрачковое расстояние"),
    ("field", "optics.prescription,date", "Prescription Date", "Дата рецепта"),
    ("field", "optics.prescription,notes", "Notes", "Примечания"),

    # Field labels - Lens
    ("field", "optics.lens,name", "Lens Name", "Название линзы"),
    ("field", "optics.lens,lens_type", "Lens Type", "Тип линзы"),
    ("field", "optics.lens,index", "Refractive Index", "Показатель преломления"),
    ("field", "optics.lens,material", "Material", "Материал"),
    ("field", "optics.lens,coating_ids", "Coatings", "Покрытия"),

    # Selection values - Lens Type
    ("selection", "optics.lens,lens_type,single", "Single Vision", "Однофокальные"),
    ("selection", "optics.lens,lens_type,bifocal", "Bifocal", "Бифокальные"),
    ("selection", "optics.lens,lens_type,progressive", "Progressive", "Прогрессивные"),

    # Field labels - Manufacturing Order
    ("field", "optics.manufacturing.order,name", "Reference", "Номер"),
    ("field", "optics.manufacturing.order,partner_id", "Customer", "Клиент"),
    ("field", "optics.manufacturing.order,prescription_id", "Prescription", "Рецепт"),
    ("field", "optics.manufacturing.order,lens_id", "Lens", "Линза"),
    ("field", "optics.manufacturing.order,frame_id", "Frame", "Оправа"),
    ("field", "optics.manufacturing.order,state", "State", "Состояние"),
    ("field", "optics.manufacturing.order,date_order", "Order Date", "Дата заказа"),
    ("field", "optics.manufacturing.order,date_expected", "Expected Delivery", "Ожидаемая дата"),
    ("field", "optics.manufacturing.order,notes", "Internal Notes", "Внутренние примечания"),

    # Selection values - State
    ("selection", "optics.manufacturing.order,state,draft", "Draft", "Черновик"),
    ("selection", "optics.manufacturing.order,state,confirmed", "Confirmed", "Подтверждено"),
    ("selection", "optics.manufacturing.order,state,production", "In Production", "В производстве"),
    ("selection", "optics.manufacturing.order,state,ready", "Ready", "Готово"),
    ("selection", "optics.manufacturing.order,state,delivered", "Delivered", "Доставлено"),
    ("selection", "optics.manufacturing.order,state,cancelled", "Cancelled", "Отменено"),
]

# Translation data for optics_pos_ru54fz module
TRANSLATIONS_POS = [
    # Field labels
    ("field", "pos.order,fiscal_doc_number", "Fiscal Document Number", "Номер фискального документа"),
    ("field", "pos.order,fiscal_sign", "Fiscal Sign", "Фискальный признак"),
    ("field", "pos.order,fn_number", "Fiscal Drive Number", "Номер фискального накопителя"),
    ("field", "pos.order,kkt_reg_number", "KKT Registration Number", "Регистрационный номер ККТ"),
    ("field", "pos.order,ofd_status", "OFD Status", "Статус ОФД"),
    ("field", "pos.config,kkt_adapter_url", "KKT Adapter URL", "URL адаптера ККТ"),
    ("field", "pos.session,x_report_printed", "X-Report Printed", "X-отчёт напечатан"),
    ("field", "pos.session,z_report_printed", "Z-Report Printed", "Z-отчёт напечатан"),

    # Selection values - OFD Status
    ("selection", "pos.order,ofd_status,pending", "Pending", "Ожидание"),
    ("selection", "pos.order,ofd_status,synced", "Synced", "Синхронизировано"),
    ("selection", "pos.order,ofd_status,failed", "Failed", "Ошибка"),

    # Common POS terms
    ("code", "Payment", "Payment", "Оплата"),
    ("code", "Cash", "Cash", "Наличные"),
    ("code", "Card", "Card", "Карта"),
    ("code", "Total", "Total", "Итого"),
    ("code", "Change", "Change", "Сдача"),
    ("code", "Print Receipt", "Print Receipt", "Печать чека"),
    ("code", "New Order", "New Order", "Новый заказ"),
    ("code", "Product", "Product", "Товар"),
    ("code", "Price", "Price", "Цена"),
    ("code", "Quantity", "Quantity", "Количество"),
    ("code", "Discount", "Discount", "Скидка"),
    ("code", "Customer", "Customer", "Клиент"),
]

def load_translations():
    """Load Russian translations into Odoo"""

    print("=== Loading Russian Translations to Odoo ===\n")

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

    # Load translations
    print("2. Loading translations...")

    all_translations = TRANSLATIONS_OPTICS_CORE + TRANSLATIONS_POS

    loaded = 0
    failed = 0

    for trans_type, name, src, value in all_translations:
        try:
            # Create or update translation
            # Search for existing translation
            existing = models.execute_kw(
                DB_NAME, uid, PASSWORD,
                'ir.translation', 'search',
                [[
                    ('lang', '=', 'ru_RU'),
                    ('src', '=', src),
                    ('type', '=', trans_type),
                ]]
            )

            if existing:
                # Update existing
                models.execute_kw(
                    DB_NAME, uid, PASSWORD,
                    'ir.translation', 'write',
                    [existing, {'value': value}]
                )
            else:
                # Create new
                models.execute_kw(
                    DB_NAME, uid, PASSWORD,
                    'ir.translation', 'create',
                    [{
                        'lang': 'ru_RU',
                        'type': trans_type,
                        'name': name,
                        'src': src,
                        'value': value,
                        'state': 'translated',
                        'module': 'optics_core' if trans_type in ['model', 'field', 'selection'] else 'optics_pos_ru54fz',
                    }]
                )

            loaded += 1
            if loaded % 10 == 0:
                print(f"   Loaded {loaded}/{len(all_translations)}...")

        except Exception as e:
            print(f"   ❌ Failed to load: {src} -> {value}: {e}")
            failed += 1

    print(f"\n✅ Translation loading complete!")
    print(f"   Loaded: {loaded}")
    print(f"   Failed: {failed}")
    print(f"   Total: {len(all_translations)}\n")

    # Clear translation cache
    print("3. Clearing translation cache...")
    try:
        models.execute_kw(
            DB_NAME, uid, PASSWORD,
            'ir.translation', 'clear_caches',
            []
        )
        print("✅ Cache cleared\n")
    except:
        print("⚠️  Could not clear cache (may need manual Odoo restart)\n")

    print("="*50)
    print("✅ Russian translations loaded successfully!\n")
    print("Next steps:")
    print("1. Restart Odoo: docker-compose restart odoo")
    print("2. Login to http://localhost:8069")
    print("3. Verify UI is in Russian")
    print("4. Test POS interface\n")

    return True

if __name__ == '__main__':
    success = load_translations()
    sys.exit(0 if success else 1)
