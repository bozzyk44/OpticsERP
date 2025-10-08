# OpticsERP — Краткий обзор проекта

> **Дата:** 2025-10-08
> **Статус:** Bootstrap Complete, Ready for Phase 1 (POC)
> **Полная детализация:** PROJECT_PHASES.md

---

## 🎯 Цель проекта

Разработать **offline-first POS/ERP систему** для сети оптик на базе Odoo 17 с:
- ✅ Автономная работа кассы 8+ часов без интернета
- ✅ Бизнес-доступность ≥99.5%
- ✅ Соответствие 54-ФЗ (фискализация)
- ✅ Масштабирование до 20 точек (40 касс)

---

## 📊 Обзор фаз (19 недель)

| # | Фаза | Недели | Сроки | Задач | Статус |
|---|------|--------|-------|-------|--------|
| 0 | **Bootstrap** | 0 | 06.10 | 12 | ✅ Complete |
| 1 | **POC** | 1-5 | 06.10 - 09.11 | 30 | ⏳ Next |
| 2 | **MVP** | 6-9 | 10.11 - 07.12 | 32 | Pending |
| 3 | **Стабилизация** | 10 | 08.12 - 14.12 | 6 | Pending |
| 4 | **Пилот** | 11-14 | 15.12 - 11.01 | 10 | Pending |
| 5 | **Soft Launch** | 15-16 | 12.01 - 25.01 | TBD | Pending |
| 6 | **Production** | 17-20 | 26.01 - 22.02 | TBD | Pending |

**Всего:** 90+ задач, 30+ checkpoints, 100+ тестов

---

## 🚀 Phase 1: POC (Следующие 5 недель)

### Week 1: Базовая инфраструктура
- [x] Hybrid Logical Clock (День 1-2)
- [x] SQLite Buffer CRUD (День 3-5)
- **Checkpoints:** W1.1, W1.2

### Week 2: FastAPI Skeleton
- [x] FastAPI app + endpoints (День 1-3)
- [x] Receipt endpoint Phase 1 (День 4-5)
- **Checkpoints:** W2.1, W2.2

### Week 3: Circuit Breaker + Two-Phase
- [x] Circuit Breaker для ОФД (День 1-2)
- [x] Двухфазная фискализация (День 3-5)
- **Checkpoints:** W3.1, W3.2

### Week 4: Sync Worker + Heartbeat
- [x] Sync Worker с Distributed Lock (День 1-3)
- [x] Heartbeat + offline detection (День 4-5)
- **Checkpoints:** W4.1, W4.2

### Week 5: POC Tests
- [x] POC-1: KKT Emulator (День 1-2)
- [x] POC-4: 8h Offline (День 3-4)
- [x] POC-5: Split-Brain (День 5)
- **Checkpoint:** POC Sign-Off

**Exit Criteria:**
- ✅ POC-1, POC-4, POC-5 PASS
- ✅ P95 печати ≤7с
- ✅ Throughput ≥20 чеков/мин

---

## 📁 Ключевые документы

### Для разработчиков
1. **PROJECT_PHASES.md** — Детальный план всех фаз (это файл)
2. **CLAUDE.md** — Архитектура + имплементация
3. **GLOSSARY.md** — Доменные термины
4. **docs/PROMPT_ENGINEERING_TEMPLATES.md** — Шаблоны промптов

### Для AI агентов
5. **CLAUDE.md §0** — Quick Start + Dependency Graph
6. **CLAUDE.md §13** — Handoff Protocol
7. **claude_history/session_YYYYMMDD.md** — История сессий

### Диаграммы
8. **docs/diagrams/two_phase_fiscalization.md**
9. **docs/diagrams/circuit_breaker_states.md**
10. **docs/diagrams/offline_buffer_sync.md**

---

## ✅ Phase 0 Completion Summary

**Выполнено:**
- ✅ Makefile (bootstrap, verify-env, test)
- ✅ Структура проекта (30+ папок)
- ✅ SQLite schema + init script
- ✅ 4 модуля Odoo (scaffolds)
- ✅ Test data generator
- ✅ GLOSSARY.md (50+ терминов)
- ✅ Dependency graph
- ✅ Handoff Protocol
- ✅ 3 sequence diagrams

**Осталось:**
- ⏳ Micro-gates для Sprint планов (1-2ч)

**Статистика:**
- Файлов создано: 25
- Строк кода/docs: ~2,500
- Время: ~3 часа

---

## 🎯 Первая задача (Week 1, Day 1)

**Задача:** Implement Hybrid Logical Clock

**Файлы:**
- `kkt_adapter/app/hlc.py` (~100 строк)
- `tests/unit/test_hlc.py` (~150 строк)

**Checkpoint W1.1:**
```bash
pytest tests/unit/test_hlc.py -v
# Expected: All 5+ tests PASS
```

**Acceptance Criteria:**
- ✅ HLC генерирует монотонные timestamps
- ✅ Logical counter инкрементится
- ✅ Ordering работает корректно
- ✅ Thread-safe

**Референс:**
- CLAUDE.md §4.3 (HLC implementation)
- docs/PROMPT_ENGINEERING_TEMPLATES.md §4.3
- GLOSSARY.md (HLC definition)

---

## 📈 Прогресс-трекер

### Phase 1 (POC)
- Week 1: ⬜⬜⬜⬜⬜ (0/5 дней)
- Week 2: ⬜⬜⬜⬜⬜ (0/5 дней)
- Week 3: ⬜⬜⬜⬜⬜ (0/5 дней)
- Week 4: ⬜⬜⬜⬜⬜ (0/5 дней)
- Week 5: ⬜⬜⬜⬜⬜ (0/5 дней)

**Обновляется в:** claude_history/session_YYYYMMDD.md

---

## 🔑 Критичные метрики

| Метрика | Цель | Измерение |
|---------|------|-----------|
| P95 печати чека | ≤7с | Jaeger traces |
| Throughput | ≥20 чеков/мин | Prometheus |
| Бизнес-доступность | ≥99.5% | Uptime monitoring |
| Sync duration | ≤10 мин (50 чеков) | POC-4 test |
| Buffer capacity | 200 чеков | Config |
| Circuit Breaker threshold | 5 ошибок | Config |

---

## 📞 Контакты & Поддержка

**Для вопросов:**
- Читай: GLOSSARY.md, PROJECT_PHASES.md, CLAUDE.md
- Проверь: claude_history/ (контекст предыдущих сессий)

**Для блокеров:**
- Следуй: CLAUDE.md §13.4 (Error Recovery Protocol)
- После 3 failures → escalate to human

---

## 🎊 Готовность к разработке

**Checklist:**
- [x] Bootstrap complete
- [x] Documentation ready
- [x] Test infrastructure ready
- [x] AI handoff protocol ready
- [ ] Micro-gates added (pending 1-2h)
- [ ] HLC implementation (Week 1 Day 1)

**Статус:** ✅ **READY TO START PHASE 1**

---

**Создано:** 2025-10-08
**Разработчик:** 1 человек + AI assistants
**Длительность проекта:** 19 недель (до 22.02.2026)
