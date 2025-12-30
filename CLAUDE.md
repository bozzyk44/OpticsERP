# Инструкции для Claude

## 📋 Оглавление

### Правила работы (§1-4)
1. [Управление задачами](#1-управление-задачами)
2. [Языки и документация](#2-языки-и-документация)
3. [Управление портами](#3-управление-портами-критично)
4. [Git Workflow](#4-git-workflow-обязательно)

### Архитектура проекта (§5-8)
5. [Обзор проекта](#5-обзор-проекта)
6. [Архитектура компонентов](#6-архитектура-компонентов)
7. [Адаптер ККТ](#7-адаптер-ккт-детальная-имплементация)
8. [План спринтов](#8-план-спринтов)

### Операционные процедуры (§9-13)
9. [Мониторинг и алерты](#9-мониторинг-и-метрики)
10. [Чек-листы развертывания](#10-чек-лист-готовности)
11. [Регламенты эксплуатации](#11-регламенты-эксплуатации)
12. [Следующие шаги](#12-следующие-шаги)
13. [AI Agent Handoff](#13-ai-agent-handoff-protocol)

---

## 1. Управление задачами

- **КРИТИЧНО:** Решать только ОДНУ задачу за запрос
- Если задача требует нескольких шагов → разбить на подзадачи
- После завершения → запросить подтверждение перед следующей

### JIRA Integration (КРИТИЧНО)

**API Credentials:**
- **Файл:** `.env` (root проекта)
- **Переменные:**
  - `JIRA_URL`: https://bozzyk44.atlassian.net
  - `JIRA_EMAIL`: bozzyk44@gmail.com
  - `JIRA_API_TOKEN`: API токен для авторизации
  - `JIRA_PROJECT_KEY`: OpticsERP

**Важно:** `.env` в `.gitignore` - не коммитить!

**Приоритет источников информации:**
1. **ПЕРВИЧНО:** Реальная JIRA (WebFetch от bozzyk44.atlassian.net)
2. **ВТОРИЧНО:** `docs/jira/jira_import.csv` (только если JIRA недоступна)

**Workflow работы с задачами:**

```bash
# 1. Получение задачи
# ❌ НЕПРАВИЛЬНО: Читать jira_import.csv напрямую
grep "OPTERP-31" docs/jira/jira_import.csv

# ✅ ПРАВИЛЬНО: Запросить задачу из JIRA
WebFetch(url: "https://bozzyk44.atlassian.net/browse/OPTERP-31")
```

**После завершения задачи (ОБЯЗАТЕЛЬНО):**

1. **Создать task plan:** `docs/task_plans/YYYYMMDD_OPTERP-XX_description.md`
2. **Commit + Push** (см. §4 Git Workflow)
3. **Обновить комментарий в JIRA:**

```markdown
✅ Задача выполнена

**Выполнено:**
- [x] Пункт 1 из acceptance criteria
- [x] Пункт 2 из acceptance criteria
- [x] Пункт 3 из acceptance criteria

**Файлы:**
- Created: file1.py, file2.py
- Modified: file3.py

**Commit:** [1dfd534](https://github.com/bozzyk44/OpticsERP/commit/1dfd534)
**Task Plan:** docs/task_plans/YYYYMMDD_OPTERP-XX_description.md

**Тесты:** ✅ All tests passed
**Coverage:** 95%+

🤖 Generated with [Claude Code](https://claude.com/claude-code)
```

**Важно:**
- ВСЕГДА обращайся к реальной JIRA при работе с задачей
- `jira_import.csv` - только fallback или для bulk операций
- Комментарий в JIRA = proof of completion (для аудита)
- Ссылка на commit обязательна

## 2. Языки и документация

**Языки:**
- **English:** Код, комментарии, API документация
- **Русский:** Остальная документация, ответы пользователю

**Хранение:**
- **КРИТИЧНО:** ВСЯ документация ТОЛЬКО в `/docs/`
- Диаграммы для сложных концепций обязательны
- Запрещено хранить docs в корне проекта

## 2.1. Ansible и WSL (КРИТИЧНО для Windows)

**КРИТИЧНО:** Ansible НЕ поддерживается нативно на Windows! Используйте WSL.

### Требования для Windows разработчиков:

**WSL (Windows Subsystem for Linux):**
- **ОБЯЗАТЕЛЬНО** для запуска Ansible на Windows
- Установка: `wsl --install -d Ubuntu-20.04`
- После установки: перезагрузка Windows

**Доступ к проекту из WSL:**
```bash
# В WSL терминале
cd /mnt/d/OpticsERP/ansible
```

**Установка Ansible в WSL:**
```bash
# Обновить систему
sudo apt update && sudo apt upgrade -y

# Установить Python и pip
sudo apt install -y python3 python3-pip python3-venv

# Установить Ansible
pip3 install ansible-core==2.16.3 ansible==9.2.0

# Проверить установку
ansible --version
```

**Workflow с WSL:**
```bash
# 1. Открыть WSL терминал (не Git Bash!)
wsl

# 2. Перейти в директорию проекта
cd /mnt/d/OpticsERP/ansible

# 3. Запустить deployment
bash scripts/deploy-wrapper.sh
```

**Альтернативы WSL:**
- **Docker:** Запуск Ansible из Docker контейнера
- **Linux VM:** Использование виртуальной машины
- **Удалённый Linux:** SSH на Linux машину

**Важно:**
- ❌ Git Bash на Windows НЕ поддерживает Ansible
- ❌ PowerShell на Windows НЕ поддерживает Ansible
- ✅ WSL - официально рекомендованный способ
- ✅ Все Ansible команды ТОЛЬКО через WSL

## 3. Управление портами (КРИТИЧНО)

**Правило:** ВСЕГДА использовать стандартные порты. НИКОГДА не менять.

### Стандартные порты

| Сервис | Порт | Назначение |
|--------|------|------------|
| **KKT Adapter** | **8000** | FastAPI REST API |
| Odoo | 8069 | Web server |
| PostgreSQL | 5432 | Database |
| Redis | 6379 | Celery broker |
| Prometheus | 9090 | Metrics |
| Grafana | 3000 | Dashboards |

### Workflow при занятом порте

```bash
# 1. Kill process on port
python scripts/kill_port.py 8000

# 2. Start service on standard port
cd kkt_adapter/app && python main.py

# Kill all project ports
python scripts/kill_port.py 8000 --all
```

## 4. Git Workflow (ОБЯЗАТЕЛЬНО)

**КРИТИЧНО:** Commit + Push после КАЖДОЙ завершенной задачи (OPTERP-X)!

### Workflow
```bash
# 1. Create branch
git checkout -b feature/task-name

# 2. Create task plan
docs/task_plans/YYYYMMDD_task_name.md

# 3. Work → Test → Commit
git add .
git commit -m "<type>(<scope>): description [OPTERP-X]"

# 4. Push (ОБЯЗАТЕЛЬНО!)
git push -u origin feature/task-name
```

### Commit Types
- `feat(scope):` — новая функциональность
- `test(scope):` — тесты
- `fix(scope):` — баг
- `docs(scope):` — документация
- `refactor(scope):` — рефакторинг
- `chore(scope):` — технические задачи

### Pre-Commit Checklist
- [ ] Все тесты пройдены (0 FAILED)
- [ ] Coverage ≥95% (unit tests)
- [ ] Логи тестов сохранены (`tests/logs/`)
- [ ] Task plan создан (`docs/task_plans/`)
- [ ] JIRA ID в commit message

### Когда делать Commit + Push
- ✅ **Завершена задача OPTERP-X**
- ✅ **Все тесты пройдены**
- ✅ **Перед новой задачей**
- ✅ **Завершена сессия работы**
- ❌ Не накапливать задачи перед push!

### Test Logging (КРИТИЧНО)

**Структура:**
```
tests/logs/{test_type}/YYYYMMDD_{TASK_ID}_{desc}.log
```

**Команда:**
```bash
pytest tests/unit/test_hlc.py -v --tb=short 2>&1 | \
  tee tests/logs/unit/$(date +%Y%m%d)_OPTERP-3_hlc_tests.log
```

**При failed test:**
1. Сохранить с суффиксом `_FAILED.log`
2. Записать в `claude_history/`
3. НЕ делать commit до исправления

### Session History
- Компактировать историю чата в `/claude_history`
- Формат: `claude_history/session_YYYYMMDD.md`

---

# План имплементации OpticsERP (Offline-First POS)

> **Версия:** 1.0 • Дата: 2025-10-08 • Разработчик: 1 человек
> **Базовые документы:** docs/1-5 (Постановка, Требования, Архитектура, Дорожная карта, Офлайн-режим)

---

## 🤖 AI Quick Start

### First Time Setup
```bash
make bootstrap  # Create structure, install deps, init DB
make verify-env # Verify Python 3.11+, Docker, SQLite, Git
make smoke-test # Run smoke test
```

### Essential Resources
1. **GLOSSARY.md** — Терминология (ККТ, ОФД, ФН, Circuit Breaker)
2. **docs/5. Офлайн-режим.md** — Offline architecture (§5.2-5.6)
3. **bootstrap/kkt_adapter_skeleton/schema.sql** — SQLite schema

### First Task: SQLite Buffer CRUD
1. Read `bootstrap/kkt_adapter_skeleton/schema.sql`
2. Implement `kkt_adapter/app/buffer.py`:
   - `insert_receipt()`, `get_pending_receipts()`, `mark_synced()`, `move_to_dlq()`
3. Write tests in `tests/unit/test_buffer_db.py`
4. **Checkpoint:** `pytest tests/unit/test_buffer_db.py` → all PASS

---

## 5. Обзор проекта

**Цель:** ERP/POS для сети оптик (Odoo 17) с **offline-first режимом**
- Автономность: 8+ часов без ОФД
- Бизнес-доступность: ≥99.5%
- 54-ФЗ compliance
- 20 точек (40 касс)

**Ключевые принципы:**
1. **Offline-first** — касса автономна, облако вторично
2. **Двухфазная фискализация** — печать → ОФД асинхронно
3. **Гарантированная доставка** — 100% чеков в ОФД
4. **Hybrid Logical Clock** — метки времени не зависят от NTP
5. **Паттерны:** Circuit Breaker, Saga, Bulkhead, Event Sourcing

**Tech Stack:**
- **Backend:** Odoo 17, PostgreSQL 15, Redis, Celery
- **Edge:** FastAPI, SQLite (WAL), APScheduler
- **Monitoring:** Prometheus, Grafana, Jaeger
- **Infra:** Docker Compose, Nginx, NTP

---

## 5.1. Этапы разработки

| Этап | Сроки | Exit Criteria |
|------|-------|---------------|
| **POC** | 06.10-09.11 (5w) | POC-4/5 ✅, метрики |
| **MVP** | 10.11-07.12 (4w) | UAT ≥95%, 0 блокеров |
| **Buffer** | 08.12-14.12 (1w) | Нагрузочные тесты |
| **Пилот** | 15.12-11.01 (4w) | 99.5% uptime, 2 точки |
| **Soft Launch** | 12.01-25.01 (2w) | 5 точек, capacity OK |
| **Прод** | 26.01-22.02 (4w) | 20 точек, RTO≤1ч |

**Итого:** 19 недель

---

## 6. Архитектура компонентов

### Структура проекта

```
OpticsERP/
├── addons/                      # Odoo модули
│   ├── optics_core/             # Рецепты, линзы, заказы на изготовление
│   ├── optics_pos_ru54fz/       # POS + 54-ФЗ + офлайн-режим
│   ├── connector_b/             # Импорт Excel/CSV
│   └── ru_accounting_extras/    # Кассовые счета, отчёт GP
│
├── kkt_adapter/                 # Адаптер ККТ (автономный сервис)
│   ├── app/
│   │   ├── main.py              # FastAPI
│   │   ├── buffer.py            # SQLite буфер + CRUD
│   │   ├── kkt_driver.py        # Драйвер ККТ
│   │   ├── ofd_client.py        # ОФД API + Circuit Breaker
│   │   ├── sync_worker.py       # Фоновая синхронизация
│   │   ├── heartbeat.py         # Heartbeat к Odoo (30s)
│   │   └── hlc.py               # Hybrid Logical Clock
│   ├── data/
│   │   ├── buffer.db            # SQLite офлайн-буфер
│   │   └── cache.json           # Локальный кэш каталога
│   ├── config.toml              # Конфигурация
│   ├── Dockerfile
│   └── docker-compose.yml
│
├── tests/
│   ├── poc/                     # POC-тесты (1-5)
│   ├── uat/                     # UAT-тесты (01-11)
│   ├── load/                    # Нагрузочные тесты (сценарии 1-4)
│   └── integration/             # Интеграционные тесты
│
├── docs/                        # Документация (5 файлов)
├── docker-compose.yml           # Полный стек
├── config.toml                  # Конфигурация проекта
└── CLAUDE.md                    # Этот файл
```

### 3.2 Кастомные модули Odoo

#### optics_core
**Цель:** Доменные сущности оптики

**Модели:**
- `optics.prescription` — рецепт (Sph, Cyl, Axis, PD, Add, Prism)
- `optics.lens` — линза (тип, индекс, покрытие)
- `optics.manufacturing.order` — заказ на изготовление

**Workflow заказа:**
```
Draft → Confirmed → In Production → Ready → Delivered
```

**Файлы:**
- `models/prescription.py`
- `models/lens.py`
- `models/manufacturing_order.py`
- `views/prescription_views.xml`
- `reports/order_label.xml` (штрихкод)

#### optics_pos_ru54fz
**Цель:** POS + 54-ФЗ + офлайн-режим

**Ключевые функции:**
- Интеграция с адаптером ККТ (API вызовы)
- X/Z-отчёты (правильные теги ФФД 1.2)
- Электронный чек (email/SMS)
- UI офлайн-режима (индикация буфера, алерты)

**Новые модели:**
- `pos.offline.buffer.status` — статус буфера для UI
- `pos.session.report` — расширение для X/Z-отчётов

**Файлы:**
- `models/pos_session.py` (расширение)
- `static/src/js/offline_indicator.js` (UI виджет)
- `controllers/kkt_adapter_api.py` (обёртка для вызовов адаптера)

#### connector_b
**Цель:** Импорт прайсов/остатков Excel/CSV

**Функции:**
- Профили маппинга (3+ поставщика)
- Превью импорта с пагинацией
- Upsert (создание/обновление)
- Валидация и отчёт об ошибках
- Блокировка импорта при несинхронизированных буферах

**Модели:**
- `connector.import.profile` — профиль маппинга
- `connector.import.job` — задача импорта
- `connector.import.log` — логи (с пагинацией)

**Файлы:**
- `models/import_profile.py`
- `models/import_job.py`
- `wizards/import_wizard.py` (превью)
- `controllers/import_api.py`

#### ru_accounting_extras
**Цель:** Кассовые счета по точкам, отчёт GP

**Функции:**
- Кассовые счета (`account.account`) по точкам
- Переводы между счетами
- Отчёт валовой прибыли (GP)
- Отчёт прибыли по точкам

**Модели:**
- `account.cash.transfer` — переводы между счетами
- Расширение `sale.order` и `pos.order` для GP

**Файлы:**
- `models/cash_transfer.py`
- `reports/gp_report.py`
- `reports/profit_by_location.py`

---

## 7. Адаптер ККТ (детальная имплементация)

### SQLite Buffer Schema

**Таблицы:** `receipts`, `dlq`, `buffer_events`
- **receipts:** id, pos_id, created_at, hlc_*, fiscal_doc, status, retry_count
- **dlq:** Dead Letter Queue для failed receipts (max_retries=20)
- **buffer_events:** Event Sourcing (receipt_added, synced, failed, circuit_*)

**SQLite Config (КРИТИЧНО):**
```python
PRAGMA journal_mode=WAL
PRAGMA synchronous=FULL  # ⚠️ Power loss protection
PRAGMA wal_autocheckpoint=100
PRAGMA cache_size=-64000  # 64 MB
```

**Full schema:** `bootstrap/kkt_adapter_skeleton/schema.sql`

### Двухфазная фискализация

**Фаза 1 (ВСЕГДА успешна):**
1. Generate HLC timestamp
2. Insert to SQLite (`status='pending'`)
3. Print на ККТ
4. Log event (`receipt_added`)

**Фаза 2 (асинхронная, best-effort):**
1. Check Circuit Breaker state
2. Send to ОФД API (timeout=10s)
3. Update `status='synced'`, set `hlc_server_time`
4. On failure: increment `retry_count` (max=20 → DLQ)

**Circuit Breaker:** `failure_threshold=5`, `recovery_timeout=60s`

**Implementation:** См. `kkt_adapter/app/buffer.py`, `ofd_client.py`

### Hybrid Logical Clock

**Ordering:** `server_time > local_time > logical_counter`

```python
@dataclass
class HybridTimestamp:
    local_time: int        # Unix timestamp
    logical_counter: int   # Monotonic counter
    server_time: Optional[int] = None  # Set on sync
```

**Implementation:** `kkt_adapter/app/hlc.py`

### API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/v1/kkt/receipt` | POST | Create fiscal receipt (2-phase) |
| `/v1/kkt/buffer/status` | GET | Buffer fullness, network status |
| `/v1/kkt/buffer/sync` | POST | Manual sync (Distributed Lock) |
| `/v1/health` | GET | Health check (Circuit Breaker state) |

**Full API:** OpenAPI 3.0 spec в `kkt_adapter/openapi.yaml`

---

## 8. План спринтов

### POC (W1-5): Proof of Concept

**W1-2:** Docker, Odoo skeletons, FastAPI, SQLite CRUD, HLC
**W3:** 2-phase fiscalization, Circuit Breaker, POC-1
**W4:** Heartbeat, offline mode, catalog cache, POC-4 (8h offline)
**W5:** connector_b import, POC-2/5, Go/No-Go

### MVP (W6-9): Полная функциональность

**W6-7:** Odoo modules (optics_core, optics_pos_ru54fz, ru_accounting_extras, connector_b)
**W8:** Offline UI, Distributed Lock, Saga, Bulkhead
**W9:** UAT (01-04, 08-11), fix blockers, MVP sign-off

### Buffer (W10): Стабилизация

Load tests (scenarios 1-4), rollback procedure, docs update, CI/CD gates

### Пилот (W11-14): 2 точки

**W11-12:** Deploy 4 кассы, UPS, training (≥90%)
**W13-14:** Grafana, alerts, stress-test (2 кассы × 8h × 50 receipts), sign-off

### Soft Launch (W15-16): 5 точек

Deploy 10 касс, capacity metrics (PG P95 <50ms, Celery queue <30), optimization

### Прод (W17-20): 20 точек

**W17-18:** 40 кассы, pgbouncer, daily backups, DR test (RTO≤1h)
**W19-20:** Admin manual, runbook (≥20 scenarios), SLA, on-call, sign-off

---

## 8.1. DoD (Definition of Done)

**MVP Exit:**
- ✅ UAT ≥95% (11 scenarios), 0 blockers
- ✅ Дубликаты чеков = 0, P95 печати ≤7s, импорт 10k ≤2min
- ✅ Офлайн: 8h, 50 receipts, sync ≤10min
- ✅ Circuit Breaker, Distributed Lock, Saga работают (автотесты)

**Пилот Exit:**
- ✅ MVP + Uptime ≥99.5% (2w), training ≥90%, 0 P1 incidents

**Прод Exit:**
- ✅ Пилот + 20 точек, RTO≤1h, RPO≤24h, monitoring active

---

## 8.2. Риски

| Риск | Митигация |
|------|-----------|
| **Buffer overflow** | Alert @80%, block @100%, emergency sync |
| **Clock drift** | NTP mandatory, HLC, drift monitoring |
| **ФН full offline** | Alert 3-5d early, replacement procedure |
| **1 dev resource** | MVP focus, test automation, part-time DevOps |

---

## 9. Мониторинг и метрики

**Prometheus Metrics:**
- `kkt_buffer_percent_full` — Buffer fullness %
- `kkt_circuit_breaker_state` — CB state (0/1/2)
- `kkt_sync_duration_seconds` — Sync latency
- `kkt_dlq_size` — DLQ size
- `kkt_hlc_drift_seconds` — HLC drift from NTP

**Critical Alerts:**
- **P1:** Buffer ≥100% (1m), ФН full
- **P2:** Buffer ≥80% (5m), CB OPEN (5m)

**Grafana Panels:**
1. Статус касс (🟢/🟡/🔴 map)
2. Circuit Breaker history (24h)
3. Buffer fullness, top-5 POS
4. Performance (P95 print, sync throughput, DLQ)

---

## 10. Чек-лист готовности

**Pre-flight:**
- [ ] Buffer <10 чеков, NTP active (drift <1s), disk ≥10GB
- [ ] Test sale online/offline OK, alerts work
- [ ] Grafana + Prometheus exporter active

**Post-deployment (30min):**
- [ ] Sale on each POS (100%), buffer stable, heartbeat OK

**Post-deployment (24h):**
- [ ] 0 P1/P2 incidents, buffers stable

---

## 11. Регламенты эксплуатации

**Бэкапы:**
- **PostgreSQL:** Daily full + 6h incremental (retention 90d)
- **SQLite:** Daily snapshot (retention 7d) + `PRAGMA wal_checkpoint(TRUNCATE)`

**SLA:**
| Priority | Response | Resolution | Escalation |
|----------|----------|------------|------------|
| P1 | ≤15m | ≤1h | Owner @30m |
| P2 | ≤1h | ≤4h | Lead @2h |
| P3 | ≤24h | ≤3d | — |

**On-call:** Weekly rotation (Mon 09:00 → Mon 09:00)

---

## 12. Следующие шаги

**W1:** Docker setup, Odoo skeletons, FastAPI, SQLite buffer schema
**W2-3:** HLC, Circuit Breaker, POC tests (1-5)
**W4-9:** MVP (all modules + UAT), load tests, pilot prep

**Ресурсы:**
- **Docs:** docs/1-5 (Постановка, Требования, Архитектура, Дорожная карта, Офлайн)
- **Specs:** 54-ФЗ, ФФД 1.2, Odoo 17 Community
- **Tools:** pybreaker, python-redis-lock, OpenTelemetry

**Summary:**
- ✅ 2-phase fiscalization → business continuity
- ✅ Circuit Breaker → cascade failure protection
- ✅ HLC → correct event ordering
- ✅ 19 weeks (T0 → T0+19) to production

---

## 13. AI Agent Handoff Protocol

### Session Start
```bash
# 1. Read last session
cat claude_history/session_$(date +%Y%m%d).md

# 2. Verify env
make verify-env && git status

# 3. Run last checkpoint
pytest tests/unit/test_lens.py -v  # Expected: all PASS
```

**If checkpoint fails:**
- ❌ **STOP** — do NOT proceed
- Escalate to human with error report (test name, error, last commit, action needed)

### Session End
```bash
# 1. Document progress
cat >> claude_history/session_$(date +%Y%m%d).md << EOF
## Session $(date +%Y-%m-%d\ %H:%M)
### Completed
- ✅ task [file:line]
### Next Tasks
- [ ] next task
### Checkpoints
- W6.1: ✅ PASS
- W6.2: ⏳ Pending
EOF

# 2. Commit + Push
git add . && git commit -m "feat(scope): description [W6.1]" && git push
```

### Error Recovery
1. **Regression?** → `git reset --hard HEAD~1`
2. **Coverage drop >5%?** → ROLLBACK
3. **3 failures?** → Escalate to human with detailed issue report

### Code Freeze (After POC)
**FROZEN (no refactor without approval):**
- SQLite schema, HLC implementation, Circuit Breaker config, ФФД 1.2 structure, Prometheus metrics

**Refactorable (MVP):**
- API endpoints, UI components, internal functions, variable names

### Context Preservation
**Before end:** Session history updated, checkpoint PASS, git clean, next tasks documented
**Before start:** Read history, verify env, re-run checkpoint
