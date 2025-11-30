# Task Plan: Перевод UI Odoo на русский язык (Russian UI Translation)

**Created**: 2025-11-30
**Status**: ⏳ Pending
**Complexity**: Medium
**Estimated Effort**: 2-3 weeks

---

## 1. Task Overview

### Objective
Translate all Odoo UI elements to Russian for better user experience in Russian-speaking optical retail locations.

### Success Criteria
- [x] All custom modules fully translated to Russian
- [x] Standard Odoo modules configured for Russian locale
- [x] Date/time formats match Russian standards
- [x] Currency and number formatting configured for Russia
- [x] User testing confirms 100% Russian UI coverage

### Scope

**In Scope:**
- Custom modules translation (optics_core, optics_pos_ru54fz, connector_b, ru_accounting_extras)
- POS interface translation (critical for cashiers)
- Menu items, field labels, help text
- Error messages and notifications
- Reports and printouts
- Date/time/currency formatting

**Out of Scope:**
- Backend code comments (remain in English)
- Developer documentation (remains in English)
- API endpoint names (remain in English)
- Database field names (technical, remain in English)

---

## 2. Technical Approach

### 2.1. Odoo Translation System

Odoo uses `.po` (Portable Object) files for translations:

```
addons/module_name/i18n/ru_RU.po
```

**Translation workflow:**
1. Extract translatable strings: `odoo -d dbname --i18n-export=ru_RU.po`
2. Translate strings in .po file
3. Import translation: `odoo -d dbname --i18n-import=ru_RU.po --language=ru_RU`
4. Set user language to Russian
5. Test UI

### 2.2. String Categories to Translate

| Category | Examples | Priority |
|----------|----------|----------|
| **Field Labels** | "Prescription", "Sphere", "Cylinder" | P0 (Critical) |
| **Menu Items** | "Sales", "Point of Sale", "Reports" | P0 (Critical) |
| **Help Text** | Field tooltips, wizard instructions | P1 (High) |
| **Error Messages** | Validation errors, warnings | P0 (Critical) |
| **Button Labels** | "Print", "Save", "Cancel" | P0 (Critical) |
| **Report Headers** | Receipt headers, report titles | P0 (Critical) |
| **State Values** | "Draft", "Confirmed", "Done" | P1 (High) |

### 2.3. Russian Standards Configuration

**Regional Settings:**
```python
# res.lang configuration
'decimal_point': ',',        # 1 234,56 (Russian standard)
'thousands_sep': ' ',        # Space separator
'date_format': '%d.%m.%Y',   # 30.11.2025
'time_format': '%H:%M:%S',   # 24-hour format
'week_start': '1',           # Monday (ISO 8601)
```

**Currency:**
- Symbol: ₽ (Ruble)
- Position: After amount (1 234,56 ₽)
- Precision: 2 decimal places

---

## 3. Implementation Plan

### Phase 1: Setup and Base Translation (Week 1)

**Step 1.1: Install Russian Language Pack**
```bash
# In Odoo container
docker-compose exec odoo odoo -d opticserp --load-language=ru_RU --stop-after-init
```

**Step 1.2: Configure System Language**
- Settings → Translations → Languages
- Activate Russian (ru_RU)
- Set as default language

**Step 1.3: Configure Regional Settings**
```python
# Update res.lang for ru_RU
{
    'decimal_point': ',',
    'thousands_sep': ' ',
    'date_format': '%d.%m.%Y',
    'time_format': '%H:%M:%S',
}
```

### Phase 2: Custom Modules Translation (Week 2)

**Step 2.1: optics_core Translation**

File: `addons/optics_core/i18n/ru_RU.po`

Key terms:
- Prescription → Рецепт
- Sphere (Sph) → Сфера (Sph)
- Cylinder (Cyl) → Цилиндр (Cyl)
- Axis → Ось
- Pupillary Distance (PD) → Межзрачковое расстояние (МР)
- Addition (Add) → Аддидация (Add)
- Prism → Призма
- Lens → Линза
- Coating → Покрытие
- Manufacturing Order → Заказ на изготовление

**Step 2.2: optics_pos_ru54fz Translation**

File: `addons/optics_pos_ru54fz/i18n/ru_RU.po`

Key terms:
- Point of Sale → Касса (или Точка продаж)
- Session → Смена
- Receipt → Чек
- Fiscal Receipt → Фискальный чек
- X-Report → X-отчёт
- Z-Report → Z-отчёт
- Cash Register → Касса
- KKT Adapter → Адаптер ККТ
- Offline Mode → Офлайн-режим
- Buffer → Буфер

**Step 2.3: connector_b Translation**

File: `addons/connector_b/i18n/ru_RU.po`

Key terms:
- Import → Импорт
- Supplier Catalog → Каталог поставщика
- Mapping Profile → Профиль маппинга
- Preview → Предпросмотр
- Validation → Валидация
- Upsert → Создание/обновление

**Step 2.4: ru_accounting_extras Translation**

File: `addons/ru_accounting_extras/i18n/ru_RU.po`

Key terms:
- Cash Account → Кассовый счёт
- Cash Transfer → Перевод между счетами
- Gross Profit (GP) → Валовая прибыль (ВП)
- Profit by Location → Прибыль по точкам

### Phase 3: POS Interface Translation (Week 2)

**Critical POS strings** (cashiers must understand):
- Product → Товар
- Price → Цена
- Quantity → Количество
- Discount → Скидка
- Total → Итого
- Payment → Оплата
- Cash → Наличные
- Card → Карта
- Change → Сдача
- Print Receipt → Печать чека
- New Order → Новый заказ
- Customer → Клиент

**POS Buttons:**
```javascript
// static/src/js/pos_translations.js
const POS_TRANSLATIONS = {
    'New Order': 'Новый заказ',
    'Payment': 'Оплата',
    'Print': 'Печать',
    'Discount': 'Скидка',
    'Customer': 'Клиент',
    'Close': 'Закрыть',
    'Cancel': 'Отмена',
};
```

### Phase 4: Reports Translation (Week 3)

**Step 4.1: Receipt Template**
- Header: Company name, address, ИНН, КПП
- Items: Name, Qty, Price, Sum
- Footer: Total, Tax, Payment method
- Fiscal data: ФН number, ФД number, ФП

**Step 4.2: X/Z Reports**
- Header: Report type, date/time, cashier
- Sales summary: Cash, Card, Total
- Tax breakdown: НДС 20%, НДС 10%
- Footer: Signature, stamp

**Step 4.3: Manufacturing Order Label**
- Order number → Номер заказа
- Customer → Клиент
- Prescription → Рецепт
- Due date → Срок изготовления
- Barcode → Штрихкод

### Phase 5: Testing and Validation (Week 3)

**Step 5.1: UI Walkthrough**
- [ ] Login screen (Russian)
- [ ] Main dashboard (all menus in Russian)
- [ ] POS interface (100% Russian)
- [ ] Product catalog (field labels)
- [ ] Manufacturing orders (workflow states)
- [ ] Reports (all templates)

**Step 5.2: Format Validation**
- [ ] Dates: dd.mm.yyyy (30.11.2025)
- [ ] Numbers: 1 234,56 (space thousands, comma decimal)
- [ ] Currency: 1 234,56 ₽ (symbol after amount)
- [ ] Time: 14:30:00 (24-hour)

**Step 5.3: User Acceptance**
- [ ] Cashier can operate POS in Russian
- [ ] Manager can read reports in Russian
- [ ] Admin can configure system in Russian
- [ ] No English strings visible in UI

---

## 4. Files to Create/Modify

### New Files

| File | Purpose |
|------|---------|
| `addons/optics_core/i18n/ru_RU.po` | optics_core translations |
| `addons/optics_pos_ru54fz/i18n/ru_RU.po` | POS + 54-ФЗ translations |
| `addons/connector_b/i18n/ru_RU.po` | Import module translations |
| `addons/ru_accounting_extras/i18n/ru_RU.po` | Accounting translations |
| `docs/localization/translation_glossary.md` | Term consistency guide |

### Modified Files

| File | Changes |
|------|---------|
| `addons/optics_core/__manifest__.py` | Add i18n directory to data |
| `addons/optics_pos_ru54fz/__manifest__.py` | Add i18n directory to data |
| Database `res.lang` record | Update Russian regional settings |
| Database `res.users` records | Set default language to ru_RU |

---

## 5. Translation Glossary

### Core Optical Terms

| English | Russian | Notes |
|---------|---------|-------|
| Prescription | Рецепт | Medical document |
| Sphere | Сфера | Keep abbreviation (Sph) |
| Cylinder | Цилиндр | Keep abbreviation (Cyl) |
| Axis | Ось | 0-180 degrees |
| Pupillary Distance | Межзрачковое расстояние | Abbreviate МР |
| Addition | Аддидация | Keep abbreviation (Add) |
| Prism | Призма | |
| Lens | Линза | Single lens |
| Lenses | Линзы | Pair of lenses |
| Frame | Оправа | |
| Coating | Покрытие | Anti-reflective, etc. |
| Refractive Index | Показатель преломления | 1.5, 1.6, 1.67, etc. |

### Business Terms

| English | Russian | Notes |
|---------|---------|-------|
| Manufacturing Order | Заказ на изготовление | |
| Point of Sale | Касса | Or "Точка продаж" |
| Session | Смена | Cash register shift |
| Receipt | Чек | |
| Fiscal Receipt | Фискальный чек | 54-ФЗ compliant |
| X-Report | X-отчёт | Mid-shift report |
| Z-Report | Z-отчёт | End-of-shift report |
| Supplier | Поставщик | |
| Customer | Клиент | |
| Order | Заказ | |

### Technical Terms

| English | Russian | Notes |
|---------|---------|-------|
| Import | Импорт | |
| Export | Экспорт | |
| Mapping | Маппинг | Keep English for technical context |
| Profile | Профиль | |
| Validation | Валидация | |
| Buffer | Буфер | Technical term, keep English in logs |
| Offline Mode | Офлайн-режим | |
| Sync | Синхронизация | |

### UI Elements

| English | Russian | Notes |
|---------|---------|-------|
| Save | Сохранить | |
| Cancel | Отмена | |
| Delete | Удалить | |
| Print | Печать | |
| Close | Закрыть | |
| New | Создать | Context: "Create new" |
| Edit | Изменить | |
| Confirm | Подтвердить | |
| Draft | Черновик | Workflow state |
| Done | Выполнено | Workflow state |
| Cancelled | Отменено | Workflow state |

---

## 6. Quality Assurance

### Translation Quality Checks

**Consistency:**
- [ ] Same term translated identically across all modules
- [ ] Technical terms use glossary definitions
- [ ] Abbreviations preserved where appropriate (Sph, Cyl, Add)

**Accuracy:**
- [ ] Medical terms verified with optical professionals
- [ ] Legal terms (54-ФЗ) match official terminology
- [ ] No machine translation errors

**Usability:**
- [ ] Natural Russian phrasing (not literal translation)
- [ ] Appropriate formality level for business context
- [ ] Button labels short enough to fit UI

### Testing Checklist

**Functional:**
- [ ] All features work with Russian UI
- [ ] No encoding issues (UTF-8)
- [ ] Print templates render correctly
- [ ] Date/number parsing works correctly

**Visual:**
- [ ] No text overflow in buttons/fields
- [ ] Proper text alignment (RTL not needed for Russian)
- [ ] Accented characters (ё, й) display correctly

**User Acceptance:**
- [ ] Cashier completes full POS workflow in Russian
- [ ] Manager generates and reads reports in Russian
- [ ] Admin performs configuration in Russian

---

## 7. Rollout Plan

### Development Environment
1. Export strings from all modules
2. Translate .po files
3. Import translations
4. Test in dev environment

### Staging Environment
1. Deploy translated modules
2. Configure Russian as default language
3. User acceptance testing (1 week)
4. Fix any issues found

### Production Rollout
1. **Pre-deployment:**
   - Backup database
   - Backup existing translations
   - Prepare rollback plan

2. **Deployment:**
   - Deploy during maintenance window (Sunday night)
   - Import all .po files
   - Update system language settings
   - Restart Odoo services

3. **Post-deployment:**
   - Verify UI displays in Russian
   - Test critical workflows (POS session, receipt printing)
   - Monitor for encoding issues

4. **Rollback Procedure (if needed):**
   - Restore database backup
   - Revert language settings to English
   - Restart services

### Training
- [ ] Create Russian user manual
- [ ] Train cashiers on Russian POS interface (2 hours)
- [ ] Train managers on Russian reports (1 hour)
- [ ] Provide Russian quick reference cards

---

## 8. Maintenance

### Adding New Strings
1. Developer adds translatable string in code:
   ```python
   _("New feature name")
   ```
2. Export updated translations:
   ```bash
   odoo -d opticserp --i18n-export=/tmp/ru_RU.po --modules=optics_core
   ```
3. Translate new strings in .po file
4. Import updated translation

### Translation Updates
- Review translations quarterly
- Collect user feedback on unclear terms
- Update glossary as needed
- Version control all .po files

---

## 9. Dependencies

**Prerequisites:**
- ✅ Odoo 17 installed and running
- ✅ All custom modules installed (optics_core, optics_pos_ru54fz, connector_b, ru_accounting_extras)
- ⏳ Russian language pack installed (to be done)

**Tools Needed:**
- Odoo CLI (`odoo` command)
- Text editor for .po files (or Poedit)
- UTF-8 encoding support

**Skills Required:**
- Russian language proficiency (native level)
- Optical retail terminology knowledge
- Odoo translation system familiarity
- 54-ФЗ legal terminology knowledge

---

## 10. Risks and Mitigations

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| **Inconsistent terminology** | Medium | High | Use glossary, single translator |
| **Text overflow in UI** | Low | Medium | Test all layouts, adjust strings |
| **Date/number parsing errors** | High | Low | Extensive format testing |
| **User confusion during transition** | Medium | High | Training, quick reference cards |
| **Encoding issues (ё, й, etc.)** | Medium | Low | UTF-8 enforcement, testing |

---

## 11. Success Metrics

**Technical Metrics:**
- [ ] 100% of custom module strings translated
- [ ] 0 encoding errors
- [ ] 0 untranslated strings visible in UI
- [ ] All date/number formats match Russian standards

**User Metrics:**
- [ ] ≥90% user satisfaction with Russian UI (survey)
- [ ] ≥95% of users prefer Russian over English
- [ ] 0 workflow errors due to translation issues
- [ ] Training completion rate 100%

**Business Metrics:**
- [ ] No productivity loss during transition
- [ ] Reduced training time for new cashiers (Russian-only speakers)
- [ ] Improved audit compliance (Russian fiscal documents)

---

## 12. Acceptance Criteria

**For MVP → Pilot transition:**
- [x] All POS interface elements in Russian
- [x] All fiscal receipts in Russian (54-ФЗ compliant)
- [x] X/Z reports in Russian
- [x] Date/number formats match Russian standards
- [x] User testing confirms 100% coverage

**For Pilot → Production transition:**
- [x] All modules fully translated
- [x] User manual in Russian
- [x] Training materials in Russian
- [x] No user-reported translation issues (1 week pilot)

---

## 13. Next Steps

### Immediate Actions
1. Install Russian language pack in Odoo
2. Create translation glossary document
3. Export translatable strings from all modules
4. Begin translation of optics_core module

### Week 1 Deliverables
- Russian language activated
- Regional settings configured
- Translation glossary complete
- optics_core translation 50% complete

### Week 2 Deliverables
- All modules translation 100% complete
- POS interface fully translated
- Translations imported and tested
- User acceptance testing started

### Week 3 Deliverables
- All reports translated
- User testing complete
- Training materials prepared
- Production deployment ready

---

**Task Complexity**: Medium
**Estimated Effort**: 2-3 weeks
**Priority**: High (blocks Russian-speaking user adoption)
**Dependencies**: MVP completion (✅ Done)

---

**Created**: 2025-11-30
**Last Updated**: 2025-11-30
**Status**: ⏳ Pending approval
