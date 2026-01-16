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
    "Patient": "Пациент",
    "Patient Name": "Имя пациента",
    "Patient Information": "Информация о пациенте",
    "Pupillary Distance": "Межзрачковое расстояние",
    "Prescription Date": "Дата рецепта",
    "Date": "Дата",

    # Eye sections
    "Right Eye (OD)": "Правый глаз (OD)",
    "Left Eye (OS)": "Левый глаз (OS)",
    "Sphere & Cylinder": "Сфера и цилиндр",
    "Addition & Prism": "Аддидация и призма",

    # Right eye fields
    "OD Sphere": "OD Сфера",
    "OD Cylinder": "OD Цилиндр",
    "OD Axis": "OD Ось",
    "OD Sphere must be between -20.00 and +20.00": "OD Сфера должна быть от -20.00 до +20.00",
    "OD Cylinder must be between -4.00 and 0.00": "OD Цилиндр должен быть от -4.00 до 0.00",
    "OD Axis must be between 1 and 180": "OD Ось должна быть от 1 до 180",

    # Left eye fields
    "OS Sphere": "OS Сфера",
    "OS Cylinder": "OS Цилиндр",
    "OS Axis": "OS Ось",
    "OS Sphere must be between -20.00 and +20.00": "OS Сфера должна быть от -20.00 до +20.00",
    "OS Cylinder must be between -4.00 and 0.00": "OS Цилиндр должен быть от -4.00 до 0.00",
    "OS Axis must be between 1 and 180": "OS Ось должна быть от 1 до 180",

    # PD fields
    "PD (mm)": "МР (мм)",
    "Binocular PD": "Бинокулярное МР",
    "Monocular PD": "Монокулярное МР",
    "PD Right (mm)": "МР правый (мм)",
    "PD Left (mm)": "МР левый (мм)",
    "Right monocular PD": "Правое монокулярное МР",
    "Left monocular PD": "Левое монокулярное МР",
    "PD must be between 56.0 and 72.0 mm": "МР должно быть от 56.0 до 72.0 мм",

    # Generic optical terms
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
    "CR-39 (Plastic)": "CR-39 (Пластик)",
    "Polycarbonate": "Поликарбонат",
    "Trivex": "Тривекс",
    "High-Index Glass": "Стекло с высоким показателем преломления",
    "Coating": "Покрытие",
    "Coatings": "Покрытия",
    "Lens Coating": "Покрытие линзы",
    "Lens Coatings": "Покрытия линз",
    "Coating Name": "Название покрытия",
    "Coating benefits and features": "Преимущества и особенности покрытия",
    "Coating benefits and features...": "Преимущества и особенности покрытия...",
    "Coating code must be unique": "Код покрытия должен быть уникальным",
    "Full coating name (e.g., \"Anti-Reflective Coating\")": "Полное название покрытия (напр., \"Антибликовое покрытие\")",
    "Define available coatings: AR, HC, UV, Photochromic, etc.": "Доступные покрытия: AR, HC, UV, фотохромные и т.д.",
    "Create your first coating!": "Создайте первое покрытие!",
    "Create your first lens!": "Создайте первую линзу!",
    "Detailed lens description, features, and specifications": "Подробное описание линзы, характеристики и спецификации",
    "Detailed lens description, features, and specifications...": "Подробное описание линзы, характеристики и спецификации...",
    "Lens material affects weight, durability, and optical clarity": "Материал линзы влияет на вес, прочность и оптическую четкость",
    "Lens manufacturer (e.g., Zeiss, Essilor, Hoya)": "Производитель линз (напр., Zeiss, Essilor, Hoya)",
    "Lens diameter in millimeters": "Диаметр линзы в миллиметрах",
    "Left eye addition for progressive lenses: 0.75-3.00": "Аддидация левого глаза для прогрессивных линз: 0.75-3.00",
    "Center Thickness (mm)": "Толщина по центру (мм)",
    "Center thickness in millimeters": "Толщина по центру в миллиметрах",

    # Manufacturing Order
    "Manufacturing Order": "Заказ на изготовление",
    "Create a new Manufacturing Order": "Создать новый заказ на изготовление",
    "Customer": "Клиент",
    "Customer Information": "Информация о клиенте",
    "Customer who placed the order": "Клиент, разместивший заказ",
    "Reference": "Номер",
    "Order Date": "Дата заказа",
    "Expected Delivery": "Ожидаемая дата",
    "Delivery Date": "Дата доставки",
    "Delivery Information": "Информация о доставке",
    "Expected delivery date (calculated from confirmation date)": "Ожидаемая дата доставки (рассчитывается от даты подтверждения)",
    "Date when order was created": "Дата создания заказа",
    "Date when order was confirmed": "Дата подтверждения заказа",
    "Date when order was delivered": "Дата доставки заказа",
    "Date when order was ready for delivery": "Дата готовности к доставке",
    "Date when production started": "Дата начала производства",
    "Duration from confirmation to delivery in days": "Длительность от подтверждения до доставки в днях",
    "Dates must be in chronological order": "Даты должны быть в хронологическом порядке",
    "Frame": "Оправа",
    "In Production": "В производстве",
    "Late Orders": "Просроченные заказы",
    "Confirmation Date": "Дата подтверждения",
    "Display order": "Порядок отображения",

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
    "Archived": "Архивировано",
    "Notes": "Примечания",
    "Create": "Создать",
    "Edit": "Редактировать",
    "Delete": "Удалить",
    "Save": "Сохранить",
    "Cancel": "Отменить",
    "Confirm": "Подтвердить",
    "Search": "Поиск",
    "Filter": "Фильтр",
    "Actions": "Действия",
    "Created by": "Создано пользователем",
    "Created on": "Дата создания",
    "Last Updated by": "Последнее изменение",
    "Last Updated on": "Дата изменения",

    # Help texts / tooltips
    "Full name of patient": "Полное имя пациента",
    "Date when prescription was issued": "Дата выдачи рецепта",
    "Additional notes or special instructions": "Дополнительные примечания или специальные инструкции",
    "Additional notes or special instructions...": "Дополнительные примечания или специальные инструкции...",
    "Additional notes and special instructions": "Дополнительные примечания и специальные инструкции",
    "Additional notes and special instructions...": "Дополнительные примечания и специальные инструкции...",
    "Internal notes for staff (not visible to customers)": "Внутренние примечания для персонала (не видны клиентам)",
    "Internal notes for staff (not visible to customers)...": "Внутренние примечания для персонала (не видны клиентам)...",
    "Internal notes for production team...": "Внутренние примечания для производства...",
    "Notes for production team": "Примечания для производства",
    "Production Notes": "Производственные примечания",
    "Internal Notes": "Внутренние примечания",
    "Additional cost added to lens price": "Дополнительная стоимость к цене линзы",
    "Additional Cost": "Дополнительная стоимость",

    # Optics menu
    "Optics": "Оптика",
    "Prescriptions": "Рецепты",
    "Lenses": "Линзы",
    "Manufacturing Orders": "Заказы на изготовление",
    "Configuration": "Настройки",
    "Create your first prescription": "Создайте первый рецепт",

    # Pricing fields
    "Sale Price": "Цена продажи",
    "Cost Price": "Себестоимость",
    "Retail price for customers": "Розничная цена для клиентов",
    "Purchase cost from supplier": "Закупочная цена у поставщика",
    "Sale price must be positive": "Цена продажи должна быть положительной",
    "Cost price must be positive": "Себестоимость должна быть положительной",
    "Code": "Код",
    "Short code (e.g., \"AR\", \"HC\", \"UV\")": "Короткий код (напр., \"AR\", \"HC\", \"UV\")",
    "Stock Keeping Unit / Product Code": "Артикул / Код товара",

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
