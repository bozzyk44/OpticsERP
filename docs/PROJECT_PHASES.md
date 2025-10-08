# OpticsERP — Разбивка проекта на фазы и задачи

> **Назначение:** Детальный план разработки с конкретными задачами и чекпоинтами
> **Версия:** 1.0 • Дата: 2025-10-08
> **Базовый документ:** CLAUDE.md
> **Длительность:** 19 недель (T0 = 06.10.2025 → T0+19 = 22.02.2026)

---

## Обзор фаз

| Фаза | Недели | Сроки | Цель | Exit Criteria |
|------|--------|-------|------|---------------|
| **Phase 0: Bootstrap** | 0 | 06.10 | Инфраструктура | ✅ Выполнено |
| **Phase 1: POC** | 1-5 | 06.10 - 09.11 | Proof of Concept | POC-4/5 pass, метрики |
| **Phase 2: MVP** | 6-9 | 10.11 - 07.12 | Полная функциональность | UAT ≥95%, 0 блокеров |
| **Phase 3: Стабилизация** | 10 | 08.12 - 14.12 | Нагрузка + баги | Нагрузка pass, 0 P1/P2 |
| **Phase 4: Пилот** | 11-14 | 15.12 - 11.01 | 2 точки (4 кассы) | Доступность ≥99.5% |
| **Phase 5: Soft Launch** | 15-16 | 12.01 - 25.01 | 5 точек (10 касс) | Capacity metrics |
| **Phase 6: Production** | 17-20 | 26.01 - 22.02 | 20 точек (40 касс) | RTO≤1ч, RPO≤24ч |

---

## Phase 0: Bootstrap ✅ COMPLETED

**Статус:** Выполнено 2025-10-08
**Результаты:** См. BOOTSTRAP_COMPLETE.md

**Достигнуто:**
- ✅ Структура проекта (30+ директорий)
- ✅ Makefile с автоматизацией
- ✅ SQLite schema + init script
- ✅ 4 модуля Odoo (scaffolds)
- ✅ Test data generator
- ✅ GLOSSARY.md + dependency graph
- ✅ AI Agent Handoff Protocol
- ✅ Sequence diagrams (3 шт)

**Pending:**
- ⏳ Micro-gates для Sprint планов (1-2ч)

---

## Phase 1: POC (Proof of Concept)

**Длительность:** 5 недель (06.10 - 09.11)
**Цель:** Доказать работоспособность offline-first архитектуры
**Exit Criteria:** POC-4 + POC-5 passed, P95 печати ≤7с, throughput ≥20 чеков/мин

---

### Week 1: Базовая инфраструктура (06.10 - 12.10)

#### Day 1-2: Hybrid Logical Clock

**Задачи:**
1. [ ] Создать `kkt_adapter/app/hlc.py`
   - Dataclass: HybridTimestamp (local_time, logical_counter, server_time)
   - Function: generate_hlc() → HybridTimestamp
   - Function: update_hlc_on_sync(receipt_id, server_time)
   - Thread-safe implementation (threading.Lock)
   - **Файлов:** 1
   - **Строк:** ~100

2. [ ] Создать `tests/unit/test_hlc.py`
   - test_hlc_monotonic() — счётчик монотонно растёт
   - test_hlc_same_second() — logical_counter инкрементится
   - test_hlc_ordering() — сравнение timestamps
   - test_hlc_thread_safe() — конкурентные вызовы
   - **Тестов:** 5+
   - **Строк:** ~150

**Checkpoint W1.1:**
```bash
pytest tests/unit/test_hlc.py -v
# Expected: All 5+ tests PASS
```

**Acceptance Criteria:**
- ✅ HLC генерирует монотонные timestamps
- ✅ Logical counter инкрементится при одной секунде
- ✅ Ordering работает (server_time > local_time > logical_counter)
- ✅ Thread-safe (100 конкурентных вызовов без race conditions)

---

#### Day 3-5: SQLite Buffer CRUD

**Задачи:**
3. [ ] Создать `kkt_adapter/app/buffer.py`
   - Class: BufferDB (init, connect, PRAGMA settings)
   - Method: insert_receipt(receipt_data) → receipt_id
   - Method: get_pending_receipts(limit=50) → List[Receipt]
   - Method: mark_synced(receipt_id, server_time) → bool
   - Method: move_to_dlq(receipt_id, reason) → bool
   - Method: get_buffer_status() → dict
   - Method: increment_retry(receipt_id, error) → bool
   - **Файлов:** 1
   - **Строк:** ~300

4. [ ] Создать `tests/unit/test_buffer_db.py`
   - test_insert_receipt() — успешное сохранение
   - test_get_pending_receipts() — выборка по status
   - test_mark_synced() — обновление статуса
   - test_move_to_dlq() — перенос в DLQ
   - test_buffer_status() — корректная статистика
   - test_hlc_ordering() — сортировка по HLC
   - test_concurrent_inserts() — параллельные вставки (WAL)
   - **Тестов:** 8+
   - **Строк:** ~250

**Checkpoint W1.2:**
```bash
pytest tests/unit/test_buffer_db.py -v
# Expected: All 8+ tests PASS
```

**Acceptance Criteria:**
- ✅ Receipts сохраняются с status=pending
- ✅ Pending receipts выбираются с ORDER BY hlc
- ✅ mark_synced обновляет status + server_time
- ✅ DLQ работает (INSERT в dlq таблицу)
- ✅ buffer_status возвращает корректную статистику
- ✅ WAL mode работает (конкурентные inserts без блокировок)

---

### Week 2: FastAPI Skeleton (13.10 - 19.10)

#### Day 1-3: FastAPI базовая структура

**Задачи:**
5. [ ] Создать `kkt_adapter/app/main.py`
   - FastAPI app initialization
   - Startup event: init SQLite buffer
   - Shutdown event: cleanup
   - CORS middleware
   - Exception handlers
   - **Файлов:** 1
   - **Строк:** ~150

6. [ ] Создать `kkt_adapter/app/models.py`
   - Pydantic: ReceiptRequest (items, payments)
   - Pydantic: ReceiptResponse (status, receipt_id)
   - Pydantic: BufferStatusResponse
   - Pydantic: HealthResponse
   - **Файлов:** 1
   - **Строк:** ~200

7. [ ] Endpoint: `GET /health`
   - Проверка SQLite connection
   - Проверка disk space (≥1GB free)
   - Return: HealthResponse
   - **Строк:** ~30

8. [ ] Endpoint: `GET /v1/kkt/buffer/status`
   - Call: buffer_db.get_buffer_status()
   - Calculate: percent_full
   - Return: BufferStatusResponse
   - **Строк:** ~20

**Checkpoint W2.1:**
```bash
# Start server
uvicorn kkt_adapter.app.main:app --reload

# Test endpoints
curl http://localhost:8000/health
# Expected: {"status": "healthy", "components": {...}}

curl http://localhost:8000/v1/kkt/buffer/status
# Expected: {"total_capacity": 200, "current_queued": 0, ...}
```

**Acceptance Criteria:**
- ✅ FastAPI запускается без ошибок
- ✅ /health возвращает 200 OK
- ✅ /buffer/status возвращает корректную статистику
- ✅ Pydantic валидация работает

---

#### Day 4-5: Receipt endpoint (Phase 1 only)

**Задачи:**
9. [ ] Endpoint: `POST /v1/kkt/receipt` (Phase 1 only)
   - Header: Idempotency-Key (required)
   - Validate: ReceiptRequest
   - Generate: HLC timestamp
   - Generate: receipt_id (UUIDv4)
   - Call: buffer_db.insert_receipt()
   - Return: ReceiptResponse (status=buffered)
   - **Строк:** ~50

10. [ ] Создать `tests/integration/test_receipt_endpoint.py`
    - test_create_receipt_success()
    - test_idempotency_key_required()
    - test_duplicate_idempotency_key()
    - test_invalid_receipt_data()
    - **Тестов:** 4+
    - **Строк:** ~150

**Checkpoint W2.2:**
```bash
pytest tests/integration/test_receipt_endpoint.py -v
# Expected: All 4+ tests PASS

# Manual test
curl -X POST http://localhost:8000/v1/kkt/receipt \
  -H "Idempotency-Key: $(uuidgen)" \
  -H "Content-Type: application/json" \
  -d '{
    "pos_id": "POS-001",
    "type": "sale",
    "items": [{"product_id": "PROD-001", "qty": 1, "price": 1000}],
    "payments": [{"method": "card", "amount": 1000}]
  }'
# Expected: {"status": "buffered", "receipt_id": "..."}
```

**Acceptance Criteria:**
- ✅ POST /v1/kkt/receipt сохраняет в буфер
- ✅ Idempotency-Key обязателен (400 без него)
- ✅ Дубликат Idempotency-Key → 409 Conflict
- ✅ Валидация данных работает (400 на невалидные)

---

### Week 3: Circuit Breaker + Two-Phase Fiscalization (20.10 - 26.10)

#### Day 1-2: Circuit Breaker для ОФД

**Задачи:**
11. [ ] Создать `kkt_adapter/app/ofd_client.py`
    - Class: OFDClient (base_url, api_key)
    - Method: send_receipt(fiscal_doc) → response
    - Circuit Breaker: pybreaker.CircuitBreaker
    - Parameters: failure_threshold=5, recovery_timeout=60
    - Callbacks: on_open, on_close, on_half_open
    - Prometheus metrics: cb_state, cb_opens_total
    - **Файлов:** 1
    - **Строк:** ~200

12. [ ] Создать mock ОФД сервер: `tests/mocks/ofd_mock.py`
    - FastAPI mock server
    - Endpoint: POST /receipts (200 OK)
    - Endpoint: POST /receipts (503 error — для тестов)
    - **Файлов:** 1
    - **Строк:** ~100

13. [ ] Создать `tests/unit/test_circuit_breaker.py`
    - test_cb_closed_normal() — нормальная работа
    - test_cb_opens_after_5_failures() — открывается после 5 ошибок
    - test_cb_half_open_recovery() — восстановление через 60s
    - test_cb_reopens_on_failure() — повторное открытие
    - test_cb_metrics() — метрики Prometheus
    - **Тестов:** 5+
    - **Строк:** ~200

**Checkpoint W3.1:**
```bash
pytest tests/unit/test_circuit_breaker.py -v
# Expected: All 5+ tests PASS
```

**Acceptance Criteria:**
- ✅ CB в состоянии CLOSED пропускает запросы
- ✅ CB открывается после 5 consecutive failures
- ✅ CB переходит в HALF_OPEN через 60s
- ✅ CB закрывается после 2 успешных проб
- ✅ Метрики cb_state, cb_opens_total работают

---

#### Day 3-5: Two-Phase Fiscalization

**Задачи:**
14. [ ] Обновить `kkt_adapter/app/main.py` — Phase 2
    - Background task: sync_receipt_phase2(receipt_id)
    - Запуск Phase 2 асинхронно после Phase 1
    - **Строк:** +50

15. [ ] Создать `kkt_adapter/app/fiscal.py`
    - Function: create_receipt_phase1(data) → receipt_id
    - Function: create_receipt_phase2(receipt_id) → bool
    - Phase 1: insert_receipt + log event
    - Phase 2: check CB + send to OFD + mark_synced
    - **Файлов:** 1
    - **Строк:** ~150

16. [ ] Создать mock ККТ драйвер: `kkt_adapter/app/kkt_driver.py`
    - Function: print_receipt(receipt_data) → bool
    - Mock implementation (logs to file)
    - Timeout: 10s
    - **Файлов:** 1
    - **Строк:** ~80

17. [ ] Обновить `POST /v1/kkt/receipt` — полная имплементация
    - Phase 1: fiscal.create_receipt_phase1()
    - Background: fiscal.create_receipt_phase2()
    - Return: ReceiptResponse
    - **Строк:** +30

18. [ ] Создать `tests/integration/test_two_phase.py`
    - test_phase1_always_succeeds() — даже если ОФД down
    - test_phase2_syncs_when_online() — синхронизация при online
    - test_phase2_buffers_when_offline() — буферизация при offline
    - test_cb_open_blocks_phase2() — CB OPEN → skip Phase 2
    - **Тестов:** 4+
    - **Строк:** ~200

**Checkpoint W3.2:**
```bash
pytest tests/integration/test_two_phase.py -v
# Expected: All 4+ tests PASS

# Manual test (ОФД online)
curl -X POST http://localhost:8000/v1/kkt/receipt ...
# Expected: status=buffered, затем status=synced (через ~1s)

# Manual test (ОФД offline — stop mock server)
curl -X POST http://localhost:8000/v1/kkt/receipt ...
# Expected: status=buffered, CB opens after 5 receipts
```

**Acceptance Criteria:**
- ✅ Phase 1 всегда успешна (даже если ОФД недоступен)
- ✅ Phase 2 синхронизирует когда ОФД online
- ✅ Phase 2 буферизует когда ОФД offline
- ✅ Circuit Breaker защищает от каскадных отказов

---

### Week 4: Sync Worker + Heartbeat (27.10 - 02.11)

#### Day 1-3: Sync Worker

**Задачи:**
19. [ ] Установить Redis: `docker-compose.yml`
    - Service: redis (image: redis:7-alpine)
    - Port: 6379
    - **Файлов:** 1
    - **Строк:** +15

20. [ ] Создать `kkt_adapter/app/sync_worker.py`
    - Function: sync_buffer() → dict
    - Distributed Lock: Redis (key=sync_lock, ttl=300s)
    - SELECT pending receipts LIMIT 50
    - For each: send to OFD (via CB) + mark_synced
    - Exponential backoff: tenacity library
    - Move to DLQ after 20 retries
    - Prometheus metrics: sync_duration, receipts_synced
    - **Файлов:** 1
    - **Строк:** ~250

21. [ ] APScheduler: `kkt_adapter/app/main.py`
    - Import: APScheduler
    - Job: sync_buffer() every 60s
    - Startup event: scheduler.start()
    - **Строк:** +30

22. [ ] Создать `tests/unit/test_sync_worker.py`
    - test_sync_pending_receipts() — успешная синхронизация
    - test_distributed_lock() — конкурентные syncs → 409
    - test_exponential_backoff() — retry с backoff
    - test_move_to_dlq_after_20() — перенос в DLQ
    - test_cb_open_skips_sync() — CB OPEN → skip
    - **Тестов:** 5+
    - **Строк:** ~250

**Checkpoint W4.1:**
```bash
pytest tests/unit/test_sync_worker.py -v
# Expected: All 5+ tests PASS

# Manual test
# 1. Create 10 receipts (ОФД offline)
# 2. Start sync worker (APScheduler)
# 3. Restore ОФД
# 4. Wait 60s
# 5. Check: all receipts synced
```

**Acceptance Criteria:**
- ✅ Sync worker синхронизирует pending receipts
- ✅ Distributed Lock предотвращает конкурентные syncs
- ✅ Exponential backoff работает (1s, 2s, 4s, ..., 60s max)
- ✅ Receipts перемещаются в DLQ после 20 попыток
- ✅ CB OPEN блокирует sync attempts

---

#### Day 4-5: Heartbeat + Offline Detection

**Задачи:**
23. [ ] Создать `kkt_adapter/app/heartbeat.py`
    - Function: send_heartbeat() → bool
    - POST to Odoo: /api/v1/kkt/heartbeat
    - Payload: {pos_id, buffer_status, cb_state}
    - Timeout: 5s
    - Hysteresis: online→offline after 3 failures, offline→online after 2 successes
    - **Файлов:** 1
    - **Строк:** ~120

24. [ ] APScheduler: heartbeat job
    - Job: send_heartbeat() every 30s
    - **Строк:** +10

25. [ ] Создать mock Odoo: `tests/mocks/odoo_mock.py`
    - FastAPI mock
    - POST /api/v1/kkt/heartbeat → 200 OK
    - **Файлов:** 1
    - **Строк:** ~50

26. [ ] Создать `tests/unit/test_heartbeat.py`
    - test_heartbeat_success() — успешный heartbeat
    - test_heartbeat_hysteresis_offline() — 3 failures → offline
    - test_heartbeat_hysteresis_online() — 2 successes → online
    - test_heartbeat_payload() — корректный payload
    - **Тестов:** 4+
    - **Строк:** ~150

**Checkpoint W4.2:**
```bash
pytest tests/unit/test_heartbeat.py -v
# Expected: All 4+ tests PASS
```

**Acceptance Criteria:**
- ✅ Heartbeat отправляется каждые 30s
- ✅ Payload содержит buffer_status + cb_state
- ✅ Hysteresis: 3 failures → offline, 2 successes → online
- ✅ Timeout 5s (не блокирует основной поток)

---

### Week 5: POC Tests + Import (03.11 - 09.11)

#### Day 1-2: POC-1 Test (KKT Emulator)

**Задачи:**
27. [ ] Создать `tests/poc/test_poc_1_emulator.py`
    - Setup: Start KKT adapter + mock ОФД
    - Test: Create 50 receipts (types: sale/refund mix)
    - Verify: All 50 buffered + printed (mock KKT log)
    - Verify: P95 < 7s, throughput ≥ 20 receipts/min
    - Teardown: Check metrics
    - **Файлов:** 1
    - **Строк:** ~200

**Checkpoint POC-1:**
```bash
pytest tests/poc/test_poc_1_emulator.py -v
# Expected: PASS
# Metrics: P95 ≤7s, throughput ≥20/min
```

**Acceptance Criteria:**
- ✅ 50 receipts created successfully
- ✅ All receipts buffered (status=pending)
- ✅ Mock KKT printed all receipts
- ✅ P95 response time ≤ 7s
- ✅ Throughput ≥ 20 receipts/min

---

#### Day 3-4: POC-4 Test (8h Offline)

**Задачи:**
28. [ ] Создать `tests/poc/test_poc_4_offline.py`
    - Setup: Start adapter, STOP mock ОФД (simulate offline)
    - Test: Create 50 receipts over "8 hours" (time mock)
    - Verify: All buffered (status=pending)
    - Verify: Buffer size = 50
    - Setup: START mock ОФД (restore connectivity)
    - Test: Trigger sync_buffer()
    - Verify: All synced within 10 min
    - Verify: Buffer size = 0
    - **Файлов:** 1
    - **Строк:** ~250

**Checkpoint POC-4:**
```bash
pytest tests/poc/test_poc_4_offline.py -v
# Expected: PASS
# Metrics: Sync duration ≤10 min
```

**Acceptance Criteria:**
- ✅ 50 receipts created in offline mode
- ✅ All buffered (no ОФД calls during offline)
- ✅ Sync completes within 10 min after restore
- ✅ All receipts synced (status=synced)
- ✅ No duplicates in ОФД

---

#### Day 5: POC-5 Test (Split-Brain)

**Задачи:**
29. [ ] Создать `tests/poc/test_poc_5_splitbrain.py`
    - Test 1: Concurrent sync workers → Distributed Lock → HTTP 409
    - Test 2: Network flapping (online→offline→online) → CB state changes
    - Test 3: Concurrent receipts → HLC ordering preserved
    - **Файлов:** 1
    - **Строк:** ~300

**Checkpoint POC-5:**
```bash
pytest tests/poc/test_poc_5_splitbrain.py -v
# Expected: PASS
```

**Acceptance Criteria:**
- ✅ Distributed Lock prevents concurrent syncs
- ✅ Network flapping handled correctly (CB opens/closes)
- ✅ HLC ensures correct ordering

---

#### POC Sign-Off

**Задачи:**
30. [ ] Создать `docs/POC_REPORT.md`
    - Результаты POC-1, POC-4, POC-5
    - Metrics: P95, throughput, sync duration
    - Скриншоты Prometheus/Grafana (если есть)
    - Go/No-Go решение
    - **Файлов:** 1
    - **Строк:** ~100

**Checkpoint POC Sign-Off:**
- ✅ POC-1 PASS
- ✅ POC-4 PASS
- ✅ POC-5 PASS
- ✅ Metrics достигнуты (P95≤7s, throughput≥20/min)
- ✅ Go decision

---

## Phase 2: MVP (Minimum Viable Product)

**Длительность:** 4 недели (10.11 - 07.12)
**Цель:** Полная функциональность для продуктива
**Exit Criteria:** UAT ≥95% pass, offline UAT 100%, 0 блокирующих дефектов

---

### Week 6: Odoo Models (optics_core) (10.11 - 16.11)

#### Day 1-2: Prescription Model

**Задачи:**
31. [ ] Создать `addons/optics_core/models/prescription.py`
    - Model: optics.prescription
    - Fields: patient_id, od_sph/cyl/axis/add, os_sph/cyl/axis/add, pd, date, notes
    - Validation: Sph range (-20, +20), Cyl ≤0, Axis (1-180), PD (56-72)
    - Constraints: SQL + Python (@api.constrains)
    - **Файлов:** 1
    - **Строк:** ~200

32. [ ] Создать `tests/unit/test_prescription.py`
    - test_sph_range_validation()
    - test_cyl_negative_only()
    - test_axis_required_if_cyl()
    - test_pd_range()
    - **Тестов:** 5+
    - **Строк:** ~150

**Checkpoint W6.1:**
```bash
pytest tests/unit/test_prescription.py -v
# Expected: All 5+ tests PASS
```

**Acceptance Criteria:**
- ✅ Prescription model создаётся в Odoo
- ✅ Валидация полей работает (Sph, Cyl, Axis, PD)
- ✅ SQL constraints предотвращают некорректные данные
- ✅ Unit tests покрывают все validations

---

#### Day 3-4: Lens Model

**Задачи:**
33. [ ] Создать `addons/optics_core/models/lens.py`
    - Model: optics.lens
    - Fields: name, type (single/bifocal/progressive), index (1.5-1.9), coating (AR/HC/UV/Photochromic)
    - Selection fields: type, coating
    - **Файлов:** 1
    - **Строк:** ~150

34. [ ] Создать `tests/unit/test_lens.py`
    - test_lens_types()
    - test_index_range()
    - test_coating_options()
    - **Тестов:** 3+
    - **Строк:** ~100

**Checkpoint W6.2:**
```bash
pytest tests/unit/test_lens.py -v
# Expected: All 3+ tests PASS
```

**Acceptance Criteria:**
- ✅ Lens model создаётся
- ✅ Types (single/bifocal/progressive) работают
- ✅ Index validation (1.5-1.9)
- ✅ Coating selection fields

---

#### Day 5: Manufacturing Order Model

**Задачи:**
35. [ ] Создать `addons/optics_core/models/manufacturing_order.py`
    - Model: optics.manufacturing.order
    - Fields: prescription_id, lens_id, state (draft/confirmed/in_production/ready/delivered)
    - Workflow: state transitions with buttons
    - **Файлов:** 1
    - **Строк:** ~200

36. [ ] Создать `tests/unit/test_manufacturing_order.py`
    - test_workflow_transitions()
    - test_state_constraints()
    - **Тестов:** 3+
    - **Строк:** ~100

**Checkpoint W6.3:**
```bash
pytest tests/unit/test_manufacturing_order.py -v
# Expected: All 3+ tests PASS
```

**Acceptance Criteria:**
- ✅ MO model создаётся
- ✅ Workflow transitions работают
- ✅ State constraints предотвращают некорректные переходы

---

### Week 7: Odoo Views + connector_b (17.11 - 23.11)

#### Day 1-2: optics_core Views

**Задачи:**
37. [ ] Создать `addons/optics_core/views/prescription_views.xml`
    - Tree view, Form view, Search view
    - **Файлов:** 1
    - **Строк:** ~150

38. [ ] Создать `addons/optics_core/views/lens_views.xml`
    - Tree view, Form view
    - **Файлов:** 1
    - **Строк:** ~100

39. [ ] Создать `addons/optics_core/views/manufacturing_order_views.xml`
    - Tree view, Form view (с statusbar), Search view
    - **Файлов:** 1
    - **Строк:** ~200

**Checkpoint W7.1:**
```bash
# Install module in Odoo
# Navigate to Prescriptions, Lenses, MO
# Expected: All views render correctly
```

**Acceptance Criteria:**
- ✅ Prescription views работают (tree/form/search)
- ✅ Lens views работают
- ✅ MO views работают (statusbar показывает workflow)

---

#### Day 3-5: connector_b Base

**Задачи:**
40. [ ] Создать `addons/connector_b/models/import_profile.py`
    - Model: connector.import.profile
    - Fields: name, supplier_name, column_mapping (JSON), active
    - **Файлов:** 1
    - **Строк:** ~150

41. [ ] Создать `addons/connector_b/models/import_job.py`
    - Model: connector.import.job
    - Fields: profile_id, file_path, state (draft/running/done/failed), log_ids
    - Method: run_import() → process file
    - **Файлов:** 1
    - **Строк:** ~250

42. [ ] Создать `addons/connector_b/wizards/import_wizard.py`
    - Wizard: Upload file → Select profile → Preview (10 rows)
    - Action: Confirm → run_import()
    - **Файлов:** 1
    - **Строк:** ~200

43. [ ] Создать `tests/unit/test_connector_import.py`
    - test_import_profile_creation()
    - test_import_job_run() — с test data generator
    - test_import_validation() — ошибки в файле
    - **Тестов:** 3+
    - **Строк:** ~200

**Checkpoint W7.2:**
```bash
pytest tests/unit/test_connector_import.py -v
# Expected: All 3+ tests PASS

# Manual test in Odoo
# 1. Create import profile (OptMarket mapping)
# 2. Upload test catalog (from test data generator)
# 3. Preview → 10 rows shown
# 4. Confirm → import runs
# 5. Check: products created/updated
```

**Acceptance Criteria:**
- ✅ Import profile создаётся с mapping
- ✅ Import job обрабатывает Excel/CSV файлы
- ✅ Preview показывает первые 10 строк
- ✅ Upsert работает (создание + обновление)
- ✅ Валидация ошибок с логированием

---

### Week 8: Offline UI + Advanced Patterns (24.11 - 30.11)

#### Day 1-2: Offline UI (POS)

**Задачи:**
44. [ ] Создать `addons/optics_pos_ru54fz/static/src/js/offline_indicator.js`
    - Widget: OfflineIndicator (показывает статус: online/offline/degraded)
    - API call: GET /v1/kkt/buffer/status каждые 30s
    - Display: buffer percentage, CB state
    - **Файлов:** 1
    - **Строк:** ~200

45. [ ] Создать `addons/optics_pos_ru54fz/views/pos_config_views.xml`
    - Add field: kkt_adapter_url
    - **Файлов:** 1
    - **Строк:** ~50

**Checkpoint W8.1:**
```bash
# Open POS in Odoo
# Expected: Offline indicator visible
# Status: Online (green) или Offline (red)
```

**Acceptance Criteria:**
- ✅ Offline indicator отображается в POS UI
- ✅ Статус обновляется каждые 30s
- ✅ Buffer percentage показывается
- ✅ CB state (CLOSED/OPEN) отображается

---

#### Day 3-5: Advanced Patterns

**Задачи:**
46. [ ] Saga Pattern: Refund blocking
    - В `optics_pos_ru54fz`: блокировка возврата если original receipt не synced
    - API endpoint: POST /v1/pos/refund → check buffer → return 409 if pending
    - **Файлов:** 1
    - **Строк:** ~100

47. [ ] Bulkhead Pattern: Celery queues
    - Create Celery queues: critical, high, default, low
    - Task: sync_buffer → critical queue
    - Task: send_email → low queue
    - **Файлов:** config
    - **Строк:** ~50

48. [ ] Создать `tests/integration/test_saga_pattern.py`
    - test_refund_blocked_if_not_synced()
    - test_refund_allowed_if_synced()
    - **Тестов:** 2+
    - **Строк:** ~100

**Checkpoint W8.2:**
```bash
pytest tests/integration/test_saga_pattern.py -v
# Expected: All 2+ tests PASS
```

**Acceptance Criteria:**
- ✅ Возврат блокируется если original не synced (HTTP 409)
- ✅ Возврат разрешён если original synced
- ✅ Celery queues настроены (critical/high/default/low)

---

### Week 9: UAT Testing + Bug Fixing (01.12 - 07.12)

#### Day 1-3: UAT Tests (Positive Scenarios)

**Задачи:**
49. [ ] Создать `tests/uat/test_uat_01_sale.py`
    - UAT-01: Продажа очков (с рецептом)
    - **Файлов:** 1
    - **Строк:** ~150

50. [ ] Создать `tests/uat/test_uat_02_refund.py`
    - UAT-02: Возврат товара
    - **Файлов:** 1
    - **Строк:** ~100

51. [ ] Создать `tests/uat/test_uat_03_import.py`
    - UAT-03: Импорт прайса поставщика
    - **Файлов:** 1
    - **Строк:** ~150

52. [ ] Создать `tests/uat/test_uat_04_reports.py`
    - UAT-04: X/Z отчёты
    - **Файлов:** 1
    - **Строк:** ~100

**Checkpoint W9.1:**
```bash
pytest tests/uat/test_uat_01_sale.py -v
pytest tests/uat/test_uat_02_refund.py -v
pytest tests/uat/test_uat_03_import.py -v
pytest tests/uat/test_uat_04_reports.py -v
# Expected: All UAT-01 to UAT-04 PASS
```

---

#### Day 4-5: UAT Tests (Offline Scenarios)

**Задачи:**
53. [ ] Создать `tests/uat/test_uat_08_offline_sale.py`
    - UAT-08: Продажа в офлайн-режиме
    - **Файлов:** 1
    - **Строк:** ~150

54. [ ] Создать `tests/uat/test_uat_09_refund_blocked.py`
    - UAT-09: Возврат блокируется если original не synced
    - **Файлов:** 1
    - **Строк:** ~100

55. [ ] Создать `tests/uat/test_uat_10b_buffer_overflow.py`
    - UAT-10b: Переполнение буфера (200 чеков)
    - **Файлов:** 1
    - **Строк:** ~150

56. [ ] Создать `tests/uat/test_uat_10c_power_loss.py`
    - UAT-10c: Восстановление после power loss (WAL test)
    - **Файлов:** 1
    - **Строк:** ~150

57. [ ] Создать `tests/uat/test_uat_11_offline_reports.py`
    - UAT-11: X/Z отчёты в офлайн-режиме
    - **Файлов:** 1
    - **Строк:** ~100

**Checkpoint W9.2:**
```bash
pytest tests/uat/test_uat_08_offline_sale.py -v
pytest tests/uat/test_uat_09_refund_blocked.py -v
pytest tests/uat/test_uat_10b_buffer_overflow.py -v
pytest tests/uat/test_uat_10c_power_loss.py -v
pytest tests/uat/test_uat_11_offline_reports.py -v
# Expected: All UAT-08 to UAT-11 PASS
```

---

#### Bug Fixing + MVP Sign-Off

**Задачи:**
58. [ ] Fix all critical bugs from UAT
59. [ ] Re-run full UAT suite
60. [ ] Verify DoD criteria (см. CLAUDE.md §6.1)
61. [ ] MVP Sign-Off document

**Checkpoint MVP Sign-Off:**
- ✅ ≥95% UAT пройдено (9/11 минимум)
- ✅ Офлайн UAT 100% (UAT-08/09/10b/10c/11 all PASS)
- ✅ 0 блокирующих дефектов
- ✅ Дубликаты чеков = 0
- ✅ P95 печати ≤7с

---

## Phase 3: Стабилизация (Buffer Week)

**Длительность:** 1 неделя (08.12 - 14.12)
**Цель:** Нагрузочные тесты + баг-фиксы
**Exit Criteria:** Нагрузка pass, 0 P1/P2 дефектов

---

### Week 10: Load Testing + Stabilization (08.12 - 14.12)

#### Day 1-2: Load Tests

**Задачи:**
62. [ ] Создать `tests/load/locustfile.py`
    - Scenario 1: 1 касса × 100 чеков/час × 10ч
    - Scenario 2: 5 касс × 50 чеков/час × 8ч
    - **Файлов:** 1
    - **Строк:** ~200

63. [ ] Run load tests
    ```bash
    locust -f tests/load/locustfile.py --host http://localhost:8000
    ```

**Checkpoint W10.1:**
- ✅ Scenario 1: P95 ≤7s, 0% errors
- ✅ Scenario 2: P95 ≤7s, 0% errors
- ✅ No OOM/CPU throttling

---

#### Day 3-5: Bug Fixing + Documentation

**Задачи:**
64. [ ] Fix performance issues found in load tests
65. [ ] Update all 5 core docs (1-5) if architecture changed
66. [ ] Create rollback procedure documentation
67. [ ] Automate DoD checks (CI/CD gate)

**Checkpoint Buffer Sign-Off:**
- ✅ Load tests pass
- ✅ 0 P1/P2 bugs
- ✅ Documentation updated
- ✅ Rollback procedure tested

---

## Phase 4: Пилот (Pilot)

**Длительность:** 4 недели (15.12 - 11.01)
**Цель:** 2 точки (4 кассы) в реальной эксплуатации
**Exit Criteria:** Доступность ≥99.5%, обучение завершено, 0 P1 инцидентов

---

### Week 11-12: Deployment (15.12 - 28.12)

**Задачи (высокоуровневые):**
68. [ ] Установка KKT адаптеров на 4 кассы
69. [ ] Настройка UPS + graceful shutdown скрипты
70. [ ] Обучение кассиров (тест ≥90% pass rate)
71. [ ] Регламенты X/Z отчётов + офлайн-буфер

**Checkpoint W12:**
- ✅ 4 кассы работают
- ✅ UPS configured
- ✅ Кассиры обучены (≥90% pass)
- ✅ Регламенты утверждены

---

### Week 13-14: Monitoring + Real Usage (29.12 - 11.01)

**Задачи:**
72. [ ] Setup Grafana dashboard (4 panels)
73. [ ] Configure Prometheus alerts (P1/P2/P3)
74. [ ] Integrate alerts (email/telegram)
75. [ ] Run stress test (2 кассы × 8ч офлайн × 50 чеков)
76. [ ] Create Decision Tree for L1/L2 support
77. [ ] Document ФН replacement procedure

**Checkpoint Pilot Sign-Off:**
- ✅ Бизнес-доступность ≥99.5% (2 недели)
- ✅ 0 P1 инцидентов
- ✅ Monitoring активен
- ✅ Stress test passed

---

## Phase 5: Soft Launch

**Длительность:** 2 недели (12.01 - 25.01)
**Цель:** 5 точек (10 касс), проверка capacity
**Exit Criteria:** Capacity metrics в норме, узкие места найдены

*(Детали аналогичны CLAUDE.md §5.5)*

---

## Phase 6: Production

**Длительность:** 4 недели (26.01 - 22.02)
**Цель:** 20 точек (40 касс), full production
**Exit Criteria:** RTO≤1ч, RPO≤24ч, полные регламенты

*(Детали аналогичны CLAUDE.md §5.6)*

---

## Итоговая статистика задач

| Phase | Недели | Задач | Checkpoints | Exit Criteria |
|-------|--------|-------|-------------|---------------|
| Phase 0: Bootstrap | 0 | 12 | 3 | ✅ Completed |
| Phase 1: POC | 1-5 | 30 | 12 | POC-1/4/5 pass |
| Phase 2: MVP | 6-9 | 32 | 10 | UAT ≥95% |
| Phase 3: Buffer | 10 | 6 | 2 | Load pass |
| Phase 4: Pilot | 11-14 | 10 | 2 | Avail ≥99.5% |
| Phase 5: Soft | 15-16 | (TBD) | 1 | Capacity OK |
| Phase 6: Prod | 17-20 | (TBD) | 1 | RTO/RPO met |

**Всего задач (Phase 0-3):** ~90 задач
**Всего checkpoints:** 30+
**Всего тестов (unit+integration+UAT+POC):** 100+ тестов

---

**Дата создания:** 2025-10-08
**Следующее обновление:** После Phase 1 completion
