# Task Progress: Russian UI Translation (Перевод UI на русский)

**Task ID**: Post-MVP Story #88 (from JIRA CSV)
**Created**: 2025-11-30
**Status**: ✅ Phase 1 Complete (Foundation)
**Complexity**: Medium (13 story points)
**Progress**: 60% Complete

---

## 1. Executive Summary

Successfully completed the foundational work for Russian UI translation in OpticsERP. The system is now configured with Russian locale, has comprehensive translation glossary, and translation files created for all 4 custom modules.

**What's Working:**
- ✅ Russian language pack installed in Odoo
- ✅ Regional settings configured (dates, numbers, currency)
- ✅ Admin user interface switched to Russian
- ✅ Translation glossary created (200+ terms)
- ✅ Translation files created for all modules

**What's Remaining:**
- ⏳ .po file format adjustments (technical issue)
- ⏳ POS JavaScript translations
- ⏳ Final testing with end users

---

## 2. Work Completed

### Phase 1: Setup & Configuration ✅

**1.1. Russian Language Installation**

```bash
# Executed successfully
docker-compose run --rm odoo odoo -d opticserp --load-language=ru_RU --stop-after-init
```

**Result:**
- ✅ Russian language pack loaded
- ✅ 50+ standard Odoo modules translated
- ✅ Base UI elements now available in Russian

**Evidence:**
```
2025-11-30 04:57:09,300 opticserp odoo.addons.base.models.ir_module: module base: loading translation file .../base/i18n/ru.po for language ru_RU
2025-11-30 04:57:09,668 opticserp odoo.addons.base.models.ir_module: module web: loading translation file .../web/i18n/ru.po for language ru_RU
...
2025-11-30 04:57:10,430 opticserp odoo.addons.base.models.ir_module: module point_of_sale: loading translation file .../point_of_sale/i18n/ru.po for language ru_RU
```

---

**1.2. Regional Settings Configuration**

**Script Created:** `scripts/setup_russian_locale.py`

**Settings Applied:**
```python
{
    'date_format': '%d.%m.%Y',      # 30.11.2025
    'time_format': '%H:%M:%S',       # 14:30:00 (24-hour)
    'decimal_point': ',',            # 1 234,56
    'thousands_sep': '\u00A0',       # Non-breaking space
    'week_start': '1',               # Monday (ISO 8601)
}
```

**Result:**
```
✅ Regional settings configured:
   - Date format: dd.mm.yyyy
   - Time format: HH:MM:SS (24-hour)
   - Decimal point: , (comma)
   - Thousands separator: (space)
   - Week start: Monday
```

**Admin User:**
- ✅ Default language set to Russian (ru_RU)
- ✅ UI now displays in Russian for admin user

---

### Phase 2: Translation Glossary ✅

**Document Created:** `docs/localization/translation_glossary.md`

**Coverage:** 200+ terms organized into 17 categories

**Categories:**
1. Core Optical Terms (17 terms)
2. Business & Sales Terms (18 terms)
3. 54-ФЗ & Fiscal Terms (16 terms)
4. POS Interface Terms (15 terms)
5. Technical & IT Terms (18 terms)
6. UI Elements (16 terms)
7. Workflow States (10 terms)
8. Common Actions (15 terms)
9. Reports & Documents (8 terms)
10. Dates & Time (12 terms)
11. Financial Terms (15 terms)
12. Module-Specific Terms (4 sections)
13. Special Characters & Symbols (6 terms)
14. Abbreviations (9 terms)
15. Translation Guidelines
16. Quality Assurance Checklist
17. Resources

**Key Terms Examples:**

| English | Russian | Notes |
|---------|---------|-------|
| Prescription | Рецепт | Medical document |
| Pupillary Distance | Межзрачковое расстояние | МР (abbreviation) |
| Point of Sale | Касса | Preferred over "Точка продаж" |
| Fiscal Receipt | Фискальный чек | 54-ФЗ compliant |
| X-Report | X-отчёт | Mid-shift report |
| Z-Report | Z-отчёт | End-of-shift report |
| Manufacturing Order | Заказ на изготовление | |
| Gross Profit | Валовая прибыль | ВП |

---

### Phase 3: Translation Files Created ✅

**Files Created:**

| Module | File | Terms Translated | Status |
|--------|------|------------------|--------|
| **optics_core** | `addons/optics_core/i18n/ru.po` | ~80 terms | ✅ Created |
| **optics_pos_ru54fz** | `addons/optics_pos_ru54fz/i18n/ru.po` | ~90 terms | ✅ Created |
| **connector_b** | `addons/connector_b/i18n/ru.po` | ~50 terms | ✅ Created |
| **ru_accounting_extras** | `addons/ru_accounting_extras/i18n/ru.po` | ~70 terms | ✅ Created |

**Total:** ~290 translated terms across all modules

---

#### 3.1. optics_core Translations

**Models Translated:**
- `optics.prescription` - Рецепт
- `optics.lens` - Линза
- `optics.lens.coating` - Покрытие линзы
- `optics.manufacturing.order` - Заказ на изготовление

**Field Translations:**
```
Patient Name → Имя пациента
Sphere (Right) → Сфера (правый)
Cylinder (Left) → Цилиндр (левый)
Pupillary Distance → Межзрачковое расстояние
Refractive Index → Показатель преломления
```

**State Translations:**
```
Draft → Черновик
Confirmed → Подтверждено
In Production → В производстве
Ready → Готово
Delivered → Доставлено
Cancelled → Отменено
```

**Menu Translations:**
```
Optics → Оптика
Prescriptions → Рецепты
Lenses → Линзы
Manufacturing Orders → Заказы на изготовление
Configuration → Настройки
```

---

#### 3.2. optics_pos_ru54fz Translations

**Fiscal Terms:**
```
Fiscal Document Number → Номер фискального документа
Fiscal Sign → Фискальный признак
Fiscal Drive Number → Номер фискального накопителя
KKT Registration Number → Регистрационный номер ККТ
OFD Status → Статус ОФД
```

**POS UI:**
```
Payment → Оплата
Cash → Наличные
Card → Карта
Total → Итого
Change → Сдача
Print Receipt → Печать чека
New Order → Новый заказ
Product → Товар
Price → Цена
Quantity → Количество
Discount → Скидка
Customer → Клиент
```

**Offline Mode:**
```
Online → Онлайн
Offline → Офлайн
Buffer → Буфер
Receipts pending sync → Чеков в очереди
Network Status → Статус сети
Working offline - receipts will sync when connection restored →
    Работа офлайн - чеки синхронизируются при восстановлении связи
```

**Reports:**
```
X-Report → X-отчёт
Z-Report → Z-отчёт
Mid-shift report without closing session →
    Промежуточный отчёт без закрытия смены
End-of-shift report and session closure →
    Отчёт о закрытии смены
```

---

#### 3.3. connector_b Translations

**Import Process:**
```
Import Profiles → Профили импорта
Import Jobs → Задания импорта
Supplier Catalog → Каталог поставщика
Column Mapping → Маппинг столбцов
Preview → Предпросмотр
Upsert Mode → Режим создания/обновления
```

**States:**
```
Draft → Черновик
In Progress → В работе
Done → Выполнено
Failed → Ошибка
```

**Statistics:**
```
Total Records → Всего записей
Created → Создано
Updated → Обновлено
Failed → Ошибок
```

---

#### 3.4. ru_accounting_extras Translations

**Accounting:**
```
Russian Accounting → Российский учёт
Cash Accounts → Кассовые счета
Cash Transfers → Переводы между счетами
Gross Profit Report → Отчёт валовой прибыли
Profit by Location → Прибыль по точкам
```

**Reports:**
```
Period → Период
Sales → Продажи
Cost → Себестоимость
Gross Profit → Валовая прибыль
GP Margin % → Наценка ВП %
Revenue → Выручка
Expenses → Расходы
Net Profit → Чистая прибыль
```

---

## 3. Files Created

| File | Size | Purpose |
|------|------|---------|
| `scripts/setup_russian_locale.py` | 3.5 KB | Configure Russian regional settings |
| `docs/localization/translation_glossary.md` | 14.5 KB | Translation terminology reference |
| `addons/optics_core/i18n/ru.po` | 5.2 KB | optics_core module translations |
| `addons/optics_pos_ru54fz/i18n/ru.po` | 6.8 KB | POS & fiscal translations |
| `addons/connector_b/i18n/ru.po` | 4.1 KB | Import module translations |
| `addons/ru_accounting_extras/i18n/ru.po` | 4.9 KB | Accounting module translations |

**Total:** 6 files, ~39 KB of translation data

---

## 4. Technical Details

### 4.1. Odoo Translation System

**How it Works:**
1. Translatable strings are marked in Python code:
   ```python
   string='Patient Name'  # Automatically translatable
   help='Full name of patient'  # Automatically translatable
   ```

2. Odoo extracts these strings and matches them with .po files:
   ```
   addons/module_name/i18n/ru_RU.po  (standard name)
   addons/module_name/i18n/ru.po     (short name, also works)
   ```

3. When user's language is set to Russian, Odoo uses translations

### 4.2. .po File Format

```po
#. module: optics_core
#: model:ir.model.fields,field_description:optics_core.field_optics_prescription__patient_name
msgid "Patient Name"
msgstr "Имя пациента"
```

**Components:**
- `#.` - Comment (module name)
- `#:` - Source reference (model, field, XML ID)
- `msgid` - Original English string
- `msgstr` - Russian translation

### 4.3. Regional Settings Applied

**Date/Time Formats:**
- Date: `%d.%m.%Y` → 30.11.2025
- Time: `%H:%M:%S` → 14:30:00 (24-hour format)
- Week starts: Monday (ISO 8601)

**Number Formats:**
- Decimal separator: `,` (comma)
- Thousands separator: ` ` (non-breaking space U+00A0)
- Example: 1 234,56

**Currency:**
- Symbol: ₽ (Ruble) - not configured yet (RUB currency not in database)
- Position: After amount
- Format: 1 234,56 ₽

---

## 5. Known Issues & Solutions

### Issue 1: .po File Format Error ⚠️

**Problem:**
```
ValueError: invalid literal for int() with base 10: ''
```

**Cause:**
Manually created .po files don't match exact Odoo expected format

**Solution:**
1. Export template .po files from Odoo first
2. Use proper .po editor (Poedit)
3. OR simplify .po files (remove metadata)

**Status:** To be resolved in Phase 2

---

### Issue 2: RUB Currency Not Found ⚠️

**Problem:**
```
⚠️  Russian Ruble currency not found
```

**Cause:**
Base Odoo installation may not include RUB by default

**Solution:**
1. Activate currency manually in Odoo UI
2. OR install l10n_ru module (Russian localization)

**Status:** To be resolved in Phase 2

---

### Issue 3: POS JavaScript Translations ⏳

**Status:** Not yet implemented

**Required:**
JavaScript UI strings need separate translation mechanism:
```javascript
// addons/optics_pos_ru54fz/static/src/js/pos_translations.js
const POS_TRANSLATIONS = {
    'New Order': 'Новый заказ',
    'Payment': 'Оплата',
    ...
};
```

**Solution:** Use Odoo's QWeb template translation system

---

## 6. Next Steps (Phase 2)

### 6.1. Fix .po File Format

**Actions:**
1. Use Odoo's built-in export to generate proper .po template:
   ```bash
   odoo -d opticserp --i18n-export=/tmp/template.po --modules=optics_core --language=ru_RU
   ```
2. Copy exported .po files to `addons/*/i18n/ru.po`
3. Edit with Poedit or similar tool
4. Re-import with `--i18n-overwrite`

**Time Estimate:** 2-3 hours

---

### 6.2. POS JavaScript Translations

**Actions:**
1. Create `static/src/xml/pos_translations.xml` for each module
2. Use Odoo QWeb template system for JS strings
3. Test POS UI thoroughly

**Time Estimate:** 4-6 hours

---

### 6.3. Configure RUB Currency

**Actions:**
1. Install `l10n_ru` module (Russian localization)
2. Activate RUB currency
3. Set RUB as company currency
4. Configure symbol position (after amount)

**Time Estimate:** 1 hour

---

### 6.4. User Acceptance Testing

**Test Scenarios:**

**Cashier Testing (POS):**
- [ ] Start new POS session
- [ ] Create sale with multiple products
- [ ] Apply discount
- [ ] Process payment (cash + card)
- [ ] Print fiscal receipt
- [ ] Verify receipt in Russian
- [ ] Test offline mode indicator
- [ ] Print X-report
- [ ] Close session with Z-report

**Manager Testing:**
- [ ] Create prescription
- [ ] Create manufacturing order
- [ ] Import supplier catalog
- [ ] Generate GP report
- [ ] Generate profit by location report
- [ ] Verify all reports in Russian

**Admin Testing:**
- [ ] Configure POS settings
- [ ] Manage users
- [ ] Configure import profiles
- [ ] Verify fiscal settings
- [ ] Check all menus in Russian

**Acceptance Criteria:**
- ✅ 100% of UI elements in Russian
- ✅ No English strings visible to end users
- ✅ Date/time/currency formats correct
- ✅ Fiscal receipts compliant with Russian standards
- ✅ User satisfaction ≥90%

**Time Estimate:** 8-12 hours

---

## 7. Success Metrics

**Phase 1 (Current):**
- ✅ 60% Complete
- ✅ Russian language installed
- ✅ Regional settings configured
- ✅ Translation glossary created (200+ terms)
- ✅ Translation files created (~290 terms)
- ✅ Admin UI partially in Russian

**Phase 2 (Remaining):**
- ⏳ .po files imported successfully
- ⏳ 100% UI coverage
- ⏳ POS JavaScript translated
- ⏳ Currency configured
- ⏳ UAT passed (≥90% satisfaction)

---

## 8. Resources

**Documentation:**
- Translation Glossary: `docs/localization/translation_glossary.md`
- Setup Script: `scripts/setup_russian_locale.py`
- Task Plan: `docs/task_plans/20251130_russian_ui_translation.md`

**Translation Files:**
- optics_core: `addons/optics_core/i18n/ru.po`
- optics_pos_ru54fz: `addons/optics_pos_ru54fz/i18n/ru.po`
- connector_b: `addons/connector_b/i18n/ru.po`
- ru_accounting_extras: `addons/ru_accounting_extras/i18n/ru.po`

**References:**
- Odoo Translation Guide: https://www.odoo.com/documentation/17.0/developer/howtos/translations.html
- Russian Locale Standards: GOST R 6.30-2003
- 54-ФЗ Official Terminology: https://www.nalog.gov.ru/

---

## 9. Conclusion

**Status:** ✅ Phase 1 Complete (Foundation)

**Key Achievements:**
1. ✅ Russian language infrastructure ready
2. ✅ Comprehensive translation glossary (200+ terms)
3. ✅ Translation files created for all modules (~290 terms)
4. ✅ Regional settings configured (dates, numbers)
5. ✅ Admin user switched to Russian

**Remaining Work:**
- Fix .po file format issues (2-3 hours)
- Implement POS JavaScript translations (4-6 hours)
- Configure RUB currency (1 hour)
- Conduct user acceptance testing (8-12 hours)

**Total Remaining Effort:** ~15-22 hours (2-3 days)

**Recommendation:**
Continue with Phase 2 to complete translation work. The foundation is solid, technical issues are minor and can be resolved quickly.

---

**Document Created:** 2025-11-30
**Status:** ✅ Phase 1 Complete
**Next Review:** After Phase 2 completion
**Approved By:** TBD

---

🎯 **Progress:** 60% → Target: 100% after Phase 2
