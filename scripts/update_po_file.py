#!/usr/bin/env python3
"""
Script to update .po file with Russian translations
Reads template .po file and adds translations from glossary
"""

import re
import sys

# Translation dictionary (from glossary)
TRANSLATIONS = {
    # Core optical terms
    "Patient Name": "Имя пациента",
    "Pupillary Distance": "Межзрачковое расстояние",
    "Prescription Date": "Дата рецепта",
    "Sphere": "Сфера",
    "Cylinder": "Цилиндр",
    "Axis": "Ось",
    "Addition": "Аддидация",
    "Prism": "Призма",

    # Lens terms
    "Lens": "Линза",
    "Lens Type": "Тип линзы",
    "Lens Name": "Название линзы",
    "Single Vision": "Однофокальные",
    "Bifocal": "Бифокальные",
    "Progressive": "Прогрессивные",
    "Refractive Index": "Показатель преломления",
    "Material": "Материал",
    "Coating": "Покрытие",
    "Coatings": "Покрытия",

    # Manufacturing Order
    "Manufacturing Order": "Заказ на изготовление",
    "Customer": "Клиент",
    "Reference": "Номер",
    "Order Date": "Дата заказа",
    "Expected Delivery": "Ожидаемая дата",
    "Internal Notes": "Внутренние примечания",
    "Frame": "Оправа",

    # States
    "State": "Состояние",
    "Draft": "Черновик",
    "Confirmed": "Подтверждено",
    "In Production": "В производстве",
    "Ready": "Готово",
    "Delivered": "Доставлено",
    "Cancelled": "Отменено",

    # Common UI
    "Active": "Активен",
    "Notes": "Примечания",
    "Create": "Создать",
    "Edit": "Редактировать",
    "Delete": "Удалить",
    "Save": "Сохранить",
    "Cancel": "Отменить",
    "Search": "Поиск",
    "Filter": "Фильтр",
    "Actions": "Действия",

    # Optics menu
    "Optics": "Оптика",
    "Prescriptions": "Рецепты",
    "Lenses": "Линзы",
    "Manufacturing Orders": "Заказы на изготовление",
    "Configuration": "Настройки",

    # POS & Fiscal (54-ФЗ)
    "Fiscal Document Number": "Номер фискального документа",
    "Fiscal Sign": "Фискальный признак",
    "Fiscal Drive Number": "Номер фискального накопителя",
    "KKT Registration Number": "Регистрационный номер ККТ",
    "OFD Status": "Статус ОФД",
    "KKT Adapter URL": "URL адаптера ККТ",
    "X-Report Printed": "X-отчёт напечатан",
    "Z-Report Printed": "Z-отчёт напечатан",
    "Z-Report Number": "Номер Z-отчёта",
    "Fiscal Settings": "Фискальные настройки",
    "Fiscal Reports": "Фискальные отчёты",
    "Print X-Report": "Печать X-отчёта",
    "Print Z-Report": "Печать Z-отчёта",
    "Fiscal Information": "Фискальная информация",

    # OFD Status values
    "Pending": "Ожидание",
    "Synced": "Синхронизировано",
    "Failed": "Ошибка",

    # POS UI terms
    "Payment": "Оплата",
    "Cash": "Наличные",
    "Card": "Карта",
    "Total": "Итого",
    "Change": "Сдача",
    "Print Receipt": "Печать чека",
    "Email Receipt": "Отправить чек по email",
    "SMS Receipt": "Отправить чек по SMS",
    "New Order": "Новый заказ",
    "Product": "Товар",
    "Price": "Цена",
    "Quantity": "Количество",
    "Discount": "Скидка",
    "Search Products...": "Поиск товаров...",

    # Offline mode
    "Online": "Онлайн",
    "Offline": "Офлайн",
    "Buffer": "Буфер",
    "Receipts pending sync": "Чеков в очереди",
    "Circuit Breaker": "Circuit Breaker",
    "Status": "Статус",
    "Network Status": "Статус сети",
}

def update_po_file(input_file, output_file):
    """Update .po file with translations"""

    with open(input_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # Process line by line
    lines = content.split('\n')
    result = []
    i = 0

    translated_count = 0

    while i < len(lines):
        line = lines[i]
        result.append(line)

        # Check if this is msgid line
        if line.startswith('msgid "') and not line.startswith('msgid ""'):
            # Extract the msgid value
            msgid_match = re.match(r'msgid "(.+)"', line)
            if msgid_match:
                msgid_text = msgid_match.group(1)

                # Check if we have a translation
                if msgid_text in TRANSLATIONS:
                    # Look ahead to next line
                    if i + 1 < len(lines):
                        next_line = lines[i + 1]

                        # If next line is empty msgstr, replace it
                        if next_line == 'msgstr ""':
                            result.append(f'msgstr "{TRANSLATIONS[msgid_text]}"')
                            i += 2  # Skip the original msgstr line
                            translated_count += 1
                            continue

        i += 1

    # Write output
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(result))

    return translated_count

if __name__ == '__main__':
    if len(sys.argv) != 3:
        print("Usage: update_po_file.py <input.po> <output.po>")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2]

    print(f"📝 Processing {input_file}...")
    count = update_po_file(input_file, output_file)
    print(f"✅ Translated {count} terms")
    print(f"💾 Saved to {output_file}")
