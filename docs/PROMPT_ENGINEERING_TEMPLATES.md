# Prompt Engineering Templates — OpticsERP Project

> **Purpose:** Reusable AI prompts for OpticsERP development tasks
> **Version:** 1.0 • Date: 2025-10-08 • Developer: 1 person
> **Base Docs:** CLAUDE.md, docs/1-5 (Architecture, Requirements, Roadmap, Offline-mode)

---

## Содержание

1. [Архитектурные промпты](#1-архитектурные-промпты)
2. [Разработка модулей Odoo](#2-разработка-модулей-odoo)
3. [Адаптер ККТ](#3-адаптер-ккт)
4. [Офлайн-режим и синхронизация](#4-офлайн-режим-и-синхронизация)
5. [Тестирование](#5-тестирование)
6. [Документация](#6-документация)
7. [Код-ревью](#7-код-ревью)
8. [Отладка и диагностика](#8-отладка-и-диагностика)

---

## 1. Архитектурные промпты

### 1.1 Анализ архитектурных решений

```
Контекст: Разрабатываем offline-first POS систему на Odoo 17 для сети оптик.
Критичные требования:
- Автономная работа кассы 8+ часов без интернета
- Двухфазная фискализация (локальная печать → асинхронная отправка в ОФД)
- Гарантированная доставка 100% чеков в ОФД
- Hybrid Logical Clock для временных меток

Задача: Проанализируй архитектурное решение для [КОМПОНЕНТ/ФУНКЦИЯ]:

**Требования:**
1. Соответствие offline-first архитектуре
2. Применение паттернов: Circuit Breaker, Saga, Bulkhead, Event Sourcing
3. Обработка edge cases (сетевые разрывы, power loss, split-brain)
4. Метрики и мониторинг (Prometheus)
5. Graceful degradation

**Формат ответа:**
1. Предложенная архитектура (диаграмма компонентов)
2. Выбранные паттерны и обоснование
3. Edge cases и стратегии обработки
4. Метрики для мониторинга
5. Альтернативные решения с trade-offs
```

### 1.2 Ревью схемы базы данных

```
Контекст: OpticsERP — offline-first POS на Odoo 17.
Специфика: SQLite буфер на кассе (WAL mode, durability), PostgreSQL на сервере.

Задача: Провери схему базы данных для [МОДУЛЬ/КОМПОНЕНТ]:

**Критерии:**
1. Нормализация (3NF, обоснованная денормализация)
2. Индексы (покрытие критичных запросов)
3. Constraints (foreign keys, checks)
4. Миграции (zero-downtime для PostgreSQL)
5. Совместимость SQLite/PostgreSQL (если применимо)

**Проверь:**
- [ ] Поддержка офлайн-режима (локальное хранение)
- [ ] Hybrid Logical Clock поля (local_time, logical_counter, server_time)
- [ ] Event Sourcing таблицы (если нужно)
- [ ] Индексы для запросов синхронизации
- [ ] PRAGMA настройки SQLite (journal_mode, synchronous)

**Схема:**
[ВСТАВИТЬ SQL DDL]
```

---

## 2. Разработка модулей Odoo

### 2.1 Создание модели Odoo

```
Контекст: Odoo 17 модуль для OpticsERP (offline-first POS для оптик).
Документация: CLAUDE.md, docs/3. Архитектура.md

Задача: Создай Odoo модель для [СУЩНОСТЬ]:

**Требования:**
1. Модель наследуется от корректной базовой модели
2. Поля с валидацией и compute methods
3. Constraints (SQL + Python)
4. CRUD methods с обработкой офлайн-кейсов
5. Комментарии на английском

**Спецификация:**
- Модуль: [optics_core / optics_pos_ru54fz / connector_b / ru_accounting_extras]
- Поля: [СПИСОК ПОЛЕЙ С ТИПАМИ]
- Связи: [RELATED MODELS]
- Бизнес-логика: [ОПИСАНИЕ]

**Формат файла:**
```python
# -*- coding: utf-8 -*-
# Author: [YOUR_NAME]
# Date: 2025-10-08
# Purpose: [MODEL_DESCRIPTION]

from odoo import models, fields, api
from odoo.exceptions import ValidationError

class [ModelName](models.Model):
    _name = '[module.model]'
    _description = '[Description]'

    # Fields
    # ...

    # Constraints
    @api.constrains('[field]')
    def _check_[field](self):
        # ...

    # Business logic
    # ...
```
```

### 2.2 Создание view (XML)

```
Задача: Создай Odoo view для модели [MODEL_NAME]:

**Типы views:**
- [ ] Tree view (список)
- [ ] Form view (форма редактирования)
- [ ] Search view (фильтры/группировки)
- [ ] Kanban view (опционально)

**Требования:**
1. Responsive layout (notebook для табов)
2. Группировка логически связанных полей
3. Статусбар для workflow (если применимо)
4. Кнопки действий (smart buttons)
5. Фильтры по статусам и датам

**Специфика OpticsERP:**
- Показывать статус офлайн-синхронизации (если применимо)
- Индикация ошибок фискализации (для pos.order)
- Tooltip для сложных полей (рецепт, линза)

**Формат файла:**
```xml
<?xml version="1.0" encoding="utf-8"?>
<!-- Author: [YOUR_NAME] -->
<!-- Date: 2025-10-08 -->
<!-- Purpose: Views for [model.name] -->
<odoo>
    <record id="view_[model]_tree" model="ir.ui.view">
        <field name="name">[model.name].tree</field>
        <field name="model">[model.name]</field>
        <field name="arch" type="xml">
            <tree>
                <!-- fields -->
            </tree>
        </field>
    </record>

    <!-- form, search views -->
</odoo>
```
```

### 2.3 Создание контроллера (API endpoint)

```
Задача: Создай Odoo HTTP контроллер для [ENDPOINT_PURPOSE]:

**Требования:**
1. Аутентификация (session / token)
2. Валидация входных данных (marshmallow / pydantic style)
3. Обработка ошибок (try/except с логированием)
4. Idempotency (если POST/PUT)
5. JSON response с кодами 200/400/500

**Спецификация:**
- Route: /api/v1/[resource]
- Method: [GET/POST/PUT/DELETE]
- Параметры: [СПИСОК]
- Response: [СХЕМА JSON]

**Пример:**
```python
# -*- coding: utf-8 -*-
# Author: [YOUR_NAME]
# Date: 2025-10-08
# Purpose: API for [resource]

from odoo import http
from odoo.http import request
import logging

_logger = logging.getLogger(__name__)

class [ControllerName](http.Controller):

    @http.route('/api/v1/[resource]', type='json', auth='user', methods=['POST'])
    def create_[resource](self, **kwargs):
        """Create [resource] with validation"""
        try:
            # Validate
            # ...

            # Create
            # ...

            return {'status': 'success', 'id': record.id}
        except Exception as e:
            _logger.error(f"Error creating [resource]: {e}")
            return {'status': 'error', 'message': str(e)}
```
```

---

## 3. Адаптер ККТ

### 3.1 FastAPI endpoint с Circuit Breaker

```
Контекст: Адаптер ККТ (FastAPI) для OpticsERP — автономный сервис на кассе.
Архитектура: SQLite буфер, Circuit Breaker для ОФД, Hybrid Logical Clock.

Задача: Создай FastAPI endpoint для [ОПЕРАЦИЯ_ККТ]:

**Требования:**
1. Idempotency (Idempotency-Key header)
2. Circuit Breaker для внешних вызовов
3. Сохранение в SQLite буфер
4. Hybrid Logical Clock timestamp
5. Валидация (pydantic)
6. Prometheus метрики

**Операции ККТ:**
- Печать чека (sale/refund/correction)
- X-отчёт (текущая смена)
- Z-отчёт (закрытие смены)
- Статус буфера

**Формат:**
```python
# Author: [YOUR_NAME]
# Date: 2025-10-08
# Purpose: [ENDPOINT_DESCRIPTION]

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, validator
from typing import Optional
import uuid

from app.buffer import BufferDB
from app.hlc import generate_hlc
from app.ofd_client import OFDCircuitBreaker
from app.metrics import kkt_buffer_size

router = APIRouter(prefix="/v1/kkt", tags=["kkt"])

class [RequestModel](BaseModel):
    # fields with validation

    @validator('[field]')
    def validate_[field](cls, v):
        # ...

@router.post("/[operation]")
async def [operation](
    data: [RequestModel],
    idempotency_key: str = Header(...)
):
    """[DESCRIPTION]"""
    try:
        # Phase 1: local save
        hlc = generate_hlc()
        receipt_id = str(uuid.uuid4())

        # Save to SQLite
        # ...

        # Update metrics
        kkt_buffer_size.inc()

        return {"status": "buffered", "receipt_id": receipt_id}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```
```

### 3.2 SQLite CRUD операции

```
Задача: Создай CRUD операции для SQLite буфера [ТАБЛИЦА]:

**Требования:**
1. WAL mode, PRAGMA synchronous=FULL
2. Транзакции для атомарности
3. Индексы для запросов синхронизации
4. Event Sourcing (buffer_events)
5. Dead Letter Queue для failed receipts

**Схема:**
[ВСТАВИТЬ DDL]

**Операции:**
- insert_receipt(receipt_data) → receipt_id
- get_pending_receipts(limit=50) → List[Receipt]
- mark_synced(receipt_id, server_time) → bool
- move_to_dlq(receipt_id, reason) → bool
- get_buffer_status() → {total, pending, synced, failed}

**Формат:**
```python
# Author: [YOUR_NAME]
# Date: 2025-10-08
# Purpose: SQLite buffer CRUD for [table]

import sqlite3
import json
from typing import List, Optional
from dataclasses import dataclass
import time

class BufferDB:
    def __init__(self, db_path='/app/data/buffer.db'):
        self.conn = sqlite3.connect(db_path)
        self._init_db()

    def _init_db(self):
        """Initialize DB with PRAGMA settings"""
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA synchronous=FULL")
        # ...

    # CRUD methods
```
```

---

## 4. Офлайн-режим и синхронизация

### 4.1 Двухфазная фискализация

```
Контекст: Двухфазная фискализация для offline-first режима.
Фаза 1: Локальная (печать + SQLite) — всегда успешна.
Фаза 2: Асинхронная отправка в ОФД (Circuit Breaker).

Задача: Имплементируй двухфазную фискализацию для [ТИП_ЧЕКА]:

**Фаза 1 (create_receipt_phase1):**
1. Генерация Hybrid Logical Clock timestamp
2. Сохранение в SQLite (status='pending')
3. Печать чека на ККТ (timeout 10s)
4. Логирование события (buffer_events)
5. Return receipt_id

**Фаза 2 (create_receipt_phase2):**
1. Проверка Circuit Breaker state
2. Отправка в ОФД API (timeout 10s)
3. Update status='synced' + server_time
4. Ретраи (exponential backoff, max 20)
5. Move to DLQ после 20 неудач

**Edge cases:**
- ККТ не отвечает → печать пропущена, алерт P2
- ОФД недоступен → Circuit Breaker OPEN, buffering
- Power loss во время Фазы 1 → WAL восстановит
- Дубликаты → Idempotency-Key защита

**Формат:**
```python
# Author: [YOUR_NAME]
# Date: 2025-10-08
# Purpose: Two-phase fiscalization for [receipt_type]

from app.buffer import BufferDB
from app.hlc import generate_hlc
from app.kkt_driver import KKTDriver
from app.ofd_client import OFDCircuitBreaker
from app.metrics import kkt_receipts_synced
import logging

_logger = logging.getLogger(__name__)

def create_receipt_phase1(receipt_data):
    """Phase 1: Local (always succeeds)"""
    # ...

async def create_receipt_phase2(receipt_id):
    """Phase 2: OFD sync (async, best-effort)"""
    # ...
```
```

### 4.2 Circuit Breaker для ОФД

```
Задача: Настрой Circuit Breaker для ОФД API:

**Параметры:**
- failure_threshold: 5 ошибок подряд → OPEN
- recovery_timeout: 60s в OPEN → HALF_OPEN
- expected_exception: (TimeoutError, ConnectionError, HTTPError 5xx)
- success_threshold: 2 успеха в HALF_OPEN → CLOSED

**Метрики:**
- kkt_circuit_breaker_state (0=CLOSED, 1=OPEN, 2=HALF_OPEN)
- kkt_circuit_breaker_opens_total (counter)

**Библиотека:** pybreaker

**Формат:**
```python
# Author: [YOUR_NAME]
# Date: 2025-10-08
# Purpose: Circuit Breaker for OFD API

from pybreaker import CircuitBreaker
from prometheus_client import Gauge, Counter
import logging

_logger = logging.getLogger(__name__)

# Metrics
cb_state_gauge = Gauge('kkt_circuit_breaker_state', 'CB state', ['pos_id'])
cb_opens_counter = Counter('kkt_circuit_breaker_opens_total', 'CB opens', ['pos_id'])

def on_open(breaker):
    """Callback when CB opens"""
    _logger.warning(f"Circuit Breaker OPEN: {breaker.name}")
    cb_state_gauge.labels(pos_id=breaker.name).set(1)
    cb_opens_counter.labels(pos_id=breaker.name).inc()

def on_close(breaker):
    """Callback when CB closes"""
    _logger.info(f"Circuit Breaker CLOSED: {breaker.name}")
    cb_state_gauge.labels(pos_id=breaker.name).set(0)

ofd_cb = CircuitBreaker(
    failure_threshold=5,
    recovery_timeout=60,
    expected_exception=(TimeoutError, ConnectionError),
    listeners=[on_open, on_close]
)

# Usage
@ofd_cb
async def send_receipt_to_ofd(receipt):
    # ...
```
```

### 4.3 Hybrid Logical Clock

```
Задача: Имплементируй Hybrid Logical Clock для временных меток чеков:

**Требования:**
1. Монотонность (даже при NTP сдвигах)
2. Порядок: server_time > local_time > logical_counter
3. Thread-safe (если многопоточность)
4. Метрики drift от NTP

**Структура:**
```python
@dataclass
class HybridTimestamp:
    local_time: int        # Unix timestamp
    logical_counter: int   # Monotonic counter
    server_time: Optional[int] = None  # Assigned on sync

    def __lt__(self, other):
        # Ordering logic
```

**Функции:**
- generate_hlc() → HybridTimestamp
- update_hlc_on_sync(receipt_id, server_time) → bool
- get_hlc_drift() → float (seconds)

**Формат:**
```python
# Author: [YOUR_NAME]
# Date: 2025-10-08
# Purpose: Hybrid Logical Clock for receipt timestamps

from dataclasses import dataclass
from typing import Optional
import time
import threading

_hlc_lock = threading.Lock()
_hlc_counter = 0
_last_hlc_time = 0

@dataclass
class HybridTimestamp:
    # ...

def generate_hlc() -> HybridTimestamp:
    """Generate HLC timestamp (thread-safe)"""
    # ...
```
```

### 4.4 Синхронизация буфера

```
Задача: Создай worker для синхронизации офлайн-буфера с Odoo:

**Требования:**
1. Периодичность: каждые 60s (APScheduler)
2. Batch size: 50 чеков за раз
3. Distributed Lock (Redis) для предотвращения конкурентной синхронизации
4. Exponential backoff для ретраев
5. Метрики: kkt_sync_duration_seconds, kkt_receipts_synced

**Алгоритм:**
1. Acquire lock (timeout 30s, ttl 5min)
2. SELECT pending receipts LIMIT 50 ORDER BY hlc_local_time
3. For each receipt:
   - send_to_ofd(receipt) via Circuit Breaker
   - UPDATE status='synced', server_time=response.time
4. Release lock
5. Log event: 'sync_completed', count, duration

**Edge cases:**
- Lock не получен → HTTP 409, retry через 60s
- Sync длится >5min → lock expire, алерт P2
- Partial failure → некоторые synced, остальные pending

**Формат:**
```python
# Author: [YOUR_NAME]
# Date: 2025-10-08
# Purpose: Background sync worker for offline buffer

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from redis import Redis
from redis.lock import Lock
import time
import logging

_logger = logging.getLogger(__name__)

redis_client = Redis(host='redis', port=6379, decode_responses=True)
scheduler = AsyncIOScheduler()

async def sync_buffer():
    """Sync pending receipts with Odoo/OFD"""
    lock = Lock(redis_client, 'sync_lock', timeout=300)  # 5min TTL

    if not lock.acquire(blocking=False):
        _logger.warning("Sync already running (lock not acquired)")
        return

    try:
        # Sync logic
        # ...
    finally:
        lock.release()

# Schedule
scheduler.add_job(sync_buffer, 'interval', seconds=60)
scheduler.start()
```
```

---

## 5. Тестирование

### 5.1 POC-тест (офлайн-режим)

```
Задача: Создай POC-тест для проверки [СЦЕНАРИЙ]:

**POC-тесты OpticsERP:**
- POC-1: Эмулятор ККТ + 50 операций
- POC-4: 8ч офлайн, 50 чеков, синхронизация ≤10 мин
- POC-5: Split-brain, flapping, конкурентная синхронизация

**Требования:**
1. Pytest фреймворк
2. Fixtures для инфраструктуры (Docker, tc qdisc для сетевых разрывов)
3. Assertions по критериям успеха
4. Cleanup после теста
5. Метрики и логи для отчёта

**Пример POC-4:**
```python
# Author: [YOUR_NAME]
# Date: 2025-10-08
# Purpose: POC-4 — 8h offline, 50 receipts, sync <10min

import pytest
import time
import subprocess

@pytest.fixture
def offline_env():
    """Setup: simulate network outage with tc qdisc"""
    subprocess.run(["tc", "qdisc", "add", "dev", "eth0", "root", "netem", "loss", "100%"])
    yield
    subprocess.run(["tc", "qdisc", "del", "dev", "eth0", "root"])

def test_poc4_offline_8h(offline_env):
    """Test 8h offline operation"""
    # 1. Create 50 receipts while offline
    receipt_ids = []
    for i in range(50):
        resp = client.post("/v1/kkt/receipt", json={...}, headers={"Idempotency-Key": str(uuid.uuid4())})
        assert resp.status_code == 200
        assert resp.json()['status'] == 'buffered'
        receipt_ids.append(resp.json()['receipt_id'])

    # 2. Check buffer size
    status = client.get("/v1/kkt/buffer/status").json()
    assert status['current_queued'] == 50

    # 3. Simulate 8h (skip for test, just verify buffer persists)
    # ...

    # 4. Restore network (fixture cleanup)
    # ...

    # 5. Trigger sync
    sync_start = time.time()
    client.post("/v1/kkt/buffer/sync", json={"force": True})

    # 6. Wait for sync (poll until buffer empty)
    while True:
        status = client.get("/v1/kkt/buffer/status").json()
        if status['current_queued'] == 0:
            break
        time.sleep(5)

    sync_duration = time.time() - sync_start

    # 7. Assertions
    assert sync_duration <= 600  # 10 min
    assert status['current_queued'] == 0

    # 8. Verify all receipts synced in Odoo
    # ...
```
```

### 5.2 UAT-тест (офлайн-сценарии)

```
Задача: Создай UAT-тест для [СЦЕНАРИЙ]:

**Офлайн UAT-тесты:**
- UAT-08: Продажа в офлайн-режиме
- UAT-09: Возврат несинхронизированного чека (должен быть заблокирован)
- UAT-10b: Переполнение офлайн-буфера
- UAT-10c: Восстановление после power loss
- UAT-11: X/Z-отчёты в офлайн

**Требования:**
1. Ручной UAT с чек-листом
2. Скриншоты критичных шагов
3. Assertion expected vs actual
4. Документирование дефектов (если найдены)

**Формат чек-листа:**
```markdown
# UAT-[XX]: [НАЗВАНИЕ]

**Предусловия:**
- [ ] Касса в online-режиме
- [ ] Офлайн-буфер пуст (<10 чеков)
- [ ] NTP-синхронизация активна

**Шаги:**
1. [ШАГ 1]
   - Expected: [РЕЗУЛЬТАТ]
   - Actual: [ЗАПОЛНИТЬ]
   - Screenshot: [ПУТЬ]
   - ✅ Pass / ❌ Fail

2. [ШАГ 2]
   - ...

**Критерии успеха:**
- [ ] [КРИТЕРИЙ 1]
- [ ] [КРИТЕРИЙ 2]

**Результат:** ✅ Pass / ❌ Fail
**Дефекты:** [ССЫЛКИ НА JIRA]
```
```

### 5.3 Нагрузочный тест (Locust)

```
Задача: Создай нагрузочный тест для [СЦЕНАРИЙ]:

**Нагрузочные сценарии OpticsERP:**
1. Одиночная касса: 100 чеков/час × 10ч (1000 чеков)
2. 5 касс параллельно: 50 чеков/час × 8ч (2000 чеков)
3. Офлайн-синхронизация: 200 чеков, сеть обрыв 30мин → восстановление
4. Упрощённый: 5 касс × 200 чеков/день (1000 total)

**Требования:**
1. Locust framework
2. Метрики: P95, P99, throughput, errors
3. Критерии успеха: P95 печати ≤7с, 0% ошибок
4. Grafana дашборд для real-time monitoring

**Формат:**
```python
# Author: [YOUR_NAME]
# Date: 2025-10-08
# Purpose: Load test — [SCENARIO]

from locust import HttpUser, task, between
import uuid

class KKTUser(HttpUser):
    wait_time = between(30, 60)  # 30-60 sec between receipts

    @task
    def create_receipt(self):
        """Create sale receipt"""
        self.client.post(
            "/v1/kkt/receipt",
            json={
                "pos_id": "POS-001",
                "type": "sale",
                "items": [
                    {"product_id": "LENS-001", "qty": 1, "price": 5000}
                ],
                "payments": [{"method": "card", "amount": 5000}]
            },
            headers={"Idempotency-Key": str(uuid.uuid4())}
        )

# Run: locust -f locustfile.py --host=http://localhost:8000
```

**Критерии успеха (Сценарий 1):**
- P95 времени отклика ≤7с
- P99 времени отклика ≤15с
- Throughput ≥100 чеков/час
- Error rate = 0%
```
```

---

## 6. Документация

### 6.1 API документация (OpenAPI)

```
Задача: Создай OpenAPI 3.0.3 документацию для [API]:

**Требования:**
1. Полная спецификация endpoints (paths, methods, parameters)
2. Request/response schemas (pydantic models → JSON Schema)
3. Authentication (session / token)
4. Error responses (400, 404, 500)
5. Examples для всех endpoints

**Формат:**
```yaml
# Author: [YOUR_NAME]
# Date: 2025-10-08
# Purpose: OpenAPI spec for [API_NAME]

openapi: 3.0.3
info:
  title: OpticsERP KKT Adapter API
  version: 1.0.0
  description: API for offline-first cash register adapter

servers:
  - url: http://localhost:8000/v1
    description: Local development

paths:
  /kkt/receipt:
    post:
      summary: Create fiscal receipt (two-phase)
      operationId: createReceipt
      tags: [KKT]
      parameters:
        - name: Idempotency-Key
          in: header
          required: true
          schema:
            type: string
            format: uuid
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/ReceiptRequest'
      responses:
        '200':
          description: Receipt created
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ReceiptResponse'
        '503':
          description: Buffer overflow
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Error'

components:
  schemas:
    ReceiptRequest:
      type: object
      required: [pos_id, type, items, payments]
      properties:
        pos_id:
          type: string
          example: "POS-001"
        type:
          type: string
          enum: [sale, refund, correction]
        items:
          type: array
          items:
            $ref: '#/components/schemas/ReceiptItem'
        payments:
          type: array
          items:
            $ref: '#/components/schemas/Payment'

    # ... other schemas
```
```

### 6.2 Runbook (процедуры эксплуатации)

```
Задача: Создай Runbook для [ПРОЦЕДУРА]:

**Процедуры OpticsERP:**
1. Проверка офлайн-буфера вручную
2. Экстренная синхронизация при переполнении
3. Восстановление после power loss
4. Замена ФН в офлайн-режиме
5. Rollback к предыдущей версии
6. Диагностика Circuit Breaker OPEN
7. Очистка Dead Letter Queue

**Формат Runbook:**
```markdown
# Runbook: [ПРОЦЕДУРА]

**Назначение:** [ОПИСАНИЕ]
**Приоритет инцидента:** P[1/2/3]
**Время выполнения:** [ОЦЕНКА]

---

## Симптомы
- [СИМПТОМ 1]
- [СИМПТОМ 2]

## Диагностика

### 1. Проверить [КОМПОНЕНТ]
```bash
# Команда
$ [COMMAND]

# Expected output
[OUTPUT]

# Если нет — перейти к шагу [X]
```

### 2. Проверить логи
```bash
$ tail -100 /app/logs/kkt_adapter.log | grep ERROR
```

## Решение

### Вариант А: [НАЗВАНИЕ]
**Когда использовать:** [УСЛОВИЕ]

**Шаги:**
1. [ ] [ШАГ 1]
   ```bash
   $ [COMMAND]
   ```

2. [ ] [ШАГ 2]
   ...

**Критерии успеха:**
- [ ] [КРИТЕРИЙ 1]
- [ ] [КРИТЕРИЙ 2]

### Вариант Б: [НАЗВАНИЕ]
...

## Откат (Rollback)
**Если решение не помогло:**
```bash
$ [ROLLBACK COMMANDS]
```

## Эскалация
**Если проблема не решена за [TIME]:**
- Уведомить L2: [КОНТАКТ]
- JIRA: создать P[X] инцидент с тегом `[TAG]`

## Post-mortem
- [ ] Обновить мониторинг (если новый кейс)
- [ ] Документировать root cause
```
```

---

## 7. Код-ревью

### 7.1 Чек-лист для ревью Odoo модуля

```
Контекст: Код-ревью для модуля Odoo в проекте OpticsERP.

Задача: Провери модуль [MODULE_NAME] по следующему чек-листу:

**Структура модуля:**
- [ ] `__manifest__.py` корректен (зависимости, версия, описание)
- [ ] Структура папок: models/, views/, controllers/, static/, security/
- [ ] `__init__.py` файлы присутствуют

**Код (models):**
- [ ] Наследование от правильных базовых моделей
- [ ] Поля с валидацией (@api.constrains)
- [ ] Compute methods с @api.depends
- [ ] SQL constraints где нужно
- [ ] Комментарии на английском
- [ ] Обработка офлайн-кейсов (если применимо)

**Views (XML):**
- [ ] Tree/Form/Search views присутствуют
- [ ] Группировка полей логична
- [ ] Статусбар для workflow (если нужен)
- [ ] Нет hardcoded strings (используй _())

**Security:**
- [ ] `ir.model.access.csv` для всех моделей
- [ ] Record rules для multi-location (если нужно)
- [ ] Минимальные привилегии (principle of least privilege)

**Тесты:**
- [ ] Unit-тесты для критичной бизнес-логики
- [ ] Coverage ≥80% для models
- [ ] Названия тестов описательны (test_[scenario])

**Performance:**
- [ ] Нет N+1 queries (проверить логи SQL)
- [ ] Используй prefetch/browse для batch operations
- [ ] Индексы для часто запрашиваемых полей

**Специфика OpticsERP:**
- [ ] Поддержка офлайн-режима (если модуль связан с POS)
- [ ] Интеграция с адаптером ККТ (если применимо)
- [ ] Метрики Prometheus (если критичный путь)
- [ ] Graceful degradation (fallback при ошибках)

**Формат замечаний:**
```
[SEVERITY: Critical/Major/Minor]
File: [PATH:LINE]
Issue: [ОПИСАНИЕ]
Suggestion: [КАК ИСПРАВИТЬ]
```
```

### 7.2 Чек-лист для ревью адаптера ККТ

```
Задача: Провери код адаптера ККТ (FastAPI) по чек-листу:

**Архитектура:**
- [ ] Двухфазная фискализация реализована корректно
- [ ] Circuit Breaker для ОФД настроен (параметры из CLAUDE.md)
- [ ] Hybrid Logical Clock генерирует монотонные timestamps
- [ ] Distributed Lock для синхронизации (Redis)
- [ ] Dead Letter Queue для failed receipts

**SQLite буфер:**
- [ ] PRAGMA journal_mode=WAL
- [ ] PRAGMA synchronous=FULL (!!!)
- [ ] Индексы для status, created_at, hlc
- [ ] Транзакции для атомарности
- [ ] Event Sourcing таблица (buffer_events)

**API:**
- [ ] Idempotency через Idempotency-Key header
- [ ] Валидация входных данных (pydantic)
- [ ] Обработка ошибок с логированием
- [ ] HTTP коды корректны (200/400/409/503)
- [ ] OpenAPI документация актуальна

**Метрики:**
- [ ] kkt_buffer_size, kkt_buffer_percent_full
- [ ] kkt_circuit_breaker_state, kkt_circuit_breaker_opens
- [ ] kkt_sync_duration_seconds
- [ ] kkt_dlq_size
- [ ] Labels (pos_id) присутствуют

**Тесты:**
- [ ] Unit-тесты для CRUD операций буфера
- [ ] Integration-тесты для двухфазной фискализации
- [ ] POC-тесты (1, 4, 5) проходят
- [ ] Mock для ККТ драйвера и ОФД API

**Security:**
- [ ] Нет hardcoded credentials
- [ ] Secrets в environment variables
- [ ] TLS для ОФД API (если прод)

**Edge cases:**
- [ ] Power loss во время записи (WAL защищает)
- [ ] Переполнение буфера → HTTP 503
- [ ] Split-brain → Distributed Lock
- [ ] Flapping сети → Circuit Breaker
```

---

## 8. Отладка и диагностика

### 8.1 Диагностика офлайн-буфера

```
Контекст: Касса в офлайн-режиме, буфер растёт, нужна диагностика.

Задача: Проанализируй состояние офлайн-буфера для кассы [POS_ID]:

**Команды диагностики:**

1. **Статус буфера (API):**
```bash
curl http://[POS_IP]:8000/v1/kkt/buffer/status
```

2. **SQLite запросы:**
```sql
-- Размер буфера по статусам
SELECT status, COUNT(*) FROM receipts GROUP BY status;

-- Старейший несинхронизированный чек
SELECT id, created_at, retry_count, last_error
FROM receipts
WHERE status='pending'
ORDER BY created_at ASC
LIMIT 1;

-- Dead Letter Queue
SELECT COUNT(*) FROM dlq WHERE resolved_at IS NULL;
```

3. **Метрики Prometheus:**
```promql
# Заполненность буфера
kkt_buffer_percent_full{pos_id="[POS_ID]"}

# Circuit Breaker state
kkt_circuit_breaker_state{pos_id="[POS_ID]"}
```

4. **Логи:**
```bash
tail -100 /app/logs/kkt_adapter.log | grep -E 'ERROR|Circuit'
```

**Анализ:**
- Если буфер ≥80% → проверить сеть, Circuit Breaker, ОФД
- Если DLQ не пуст → ручная обработка failed receipts
- Если retry_count ≥10 → проверить ОФД API, возможно изменился формат

**Действия:**
1. [ ] Проверить сетевое подключение (ping, traceroute к ОФД)
2. [ ] Проверить статус ОФД (веб-кабинет)
3. [ ] Принудительная синхронизация: POST /v1/kkt/buffer/sync
4. [ ] Если не помогло → эскалация L2 (Runbook)
```

### 8.2 Диагностика Circuit Breaker OPEN

```
Задача: Circuit Breaker в состоянии OPEN, чеки буферизуются. Диагностируй и реши.

**Симптомы:**
- kkt_circuit_breaker_state == 1 (OPEN)
- Офлайн-буфер растёт
- Логи: "Circuit Breaker OPEN"

**Диагностика:**

1. **Проверить состояние ОФД:**
```bash
# Прямой запрос к ОФД API
curl -X POST https://ofd.example.ru/api/receipts \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer [TOKEN]" \
  -d '{"test": true}' \
  --max-time 10
```

2. **Проверить сеть:**
```bash
ping -c 5 ofd.example.ru
traceroute ofd.example.ru
```

3. **Проверить метрики:**
```promql
# Сколько раз открывался за 24ч
increase(kkt_circuit_breaker_opens_total{pos_id="[POS_ID]"}[24h])

# Когда последний раз открылся
kkt_circuit_breaker_state{pos_id="[POS_ID]"} == 1
```

4. **Логи ошибок:**
```bash
grep "Circuit Breaker" /app/logs/kkt_adapter.log | tail -20
```

**Решение:**

**Вариант А: ОФД временно недоступен**
- Ожидать recovery_timeout (60s)
- CB автоматически перейдёт в HALF_OPEN → попытка
- Если успех → CLOSED

**Вариант Б: Постоянная проблема с ОФД (downtime, изменение API)**
1. Проверить статус ОФД (веб-кабинет, поддержка)
2. Если API изменился → обновить ofd_client.py
3. Если длительный downtime → уведомить бизнес, работать в офлайн

**Вариант В: Проблема сети на кассе**
1. Проверить роутер, кабели
2. Перезагрузить сетевое оборудование
3. Если не помогло → вызвать инженера

**Критерии успеха:**
- CB вернулся в CLOSED
- Буфер начал синхронизироваться (уменьшается)
- Нет новых ошибок в логах
```

### 8.3 Анализ performance issues

```
Задача: P95 времени печати чека >7с. Найди узкое место.

**Инструменты:**
1. Jaeger (distributed tracing)
2. Prometheus (метрики)
3. PostgreSQL slow query log
4. Python profiler (cProfile)

**Шаги:**

1. **Jaeger traces:**
```bash
# Найти медленные запросы
# UI: http://jaeger:16686
# Filter: service=kkt_adapter, min_duration=7s
```

2. **Prometheus метрики:**
```promql
# P95 время печати
histogram_quantile(0.95, rate(kkt_receipt_duration_seconds_bucket[5m]))

# Медленные компоненты
topk(5, rate(kkt_receipt_duration_seconds_sum[5m]) / rate(kkt_receipt_duration_seconds_count[5m]))
```

3. **PostgreSQL slow queries:**
```sql
-- Включить логирование медленных запросов
ALTER SYSTEM SET log_min_duration_statement = 1000;  -- 1s
SELECT pg_reload_conf();

-- Проверить логи
SELECT * FROM pg_stat_statements ORDER BY mean_exec_time DESC LIMIT 10;
```

4. **Python profiler:**
```python
import cProfile
import pstats

profiler = cProfile.Profile()
profiler.enable()

# Запустить медленную операцию
create_receipt_phase1(receipt_data)

profiler.disable()
stats = pstats.Stats(profiler).sort_stats('cumtime')
stats.print_stats(20)
```

**Типичные узкие места:**

- **SQLite запись:** PRAGMA synchronous=FULL медленный, но необходим (durability)
  - Решение: batch inserts (если возможно)

- **Печать на ККТ:** timeout 10s, драйвер медленный
  - Решение: оптимизировать драйвер, асинхронная печать

- **Odoo API:** медленный запрос каталога
  - Решение: кэширование (cache.json), индексы

- **Сеть:** высокий latency к ОФД
  - Решение: уже асинхронная отправка, ничего не делать

**Действия:**
1. [ ] Идентифицировать компонент (Jaeger)
2. [ ] Профилировать (cProfile)
3. [ ] Оптимизировать (индексы, кэш, batch)
4. [ ] Проверить метрики (Prometheus)
5. [ ] Повторить нагрузочный тест
```

---

## Использование шаблонов

### Как применять:

1. **Скопируй промпт** из соответствующего раздела
2. **Заполни параметры** в квадратных скобках [ПАРАМЕТР]
3. **Добавь контекст** (файлы, логи, метрики)
4. **Отправь Claude** и получи результат

### Пример:

```
[Копируй промпт 2.1]

Задача: Создай Odoo модель для Prescription (рецепт):

Спецификация:
- Модуль: optics_core
- Поля:
  - patient_id (many2one res.partner)
  - od_sph, od_cyl, od_axis, od_add (float)
  - os_sph, os_cyl, os_axis, os_add (float)
  - pd (float, межзрачковое расстояние)
  - date (date)
  - notes (text)
- Связи: sale.order (one2many)
- Бизнес-логика: валидация диапазонов Sph/Cyl/Axis
```

---

## Обновления шаблонов

При добавлении новых компонентов или изменении архитектуры — обновлять этот файл.

**Версионирование:**
- 1.0 (2025-10-08): Базовые шаблоны для POC/MVP
- 1.1 (планируется): Шаблоны для пилота и продуктива

---

**Контакты:**
- Вопросы: [EMAIL]
- Issue tracker: [JIRA_URL]
