# Developer Setup Guide
# Руководство по настройке среды разработки

**Версия:** 1.0
**Дата:** 2025-11-30
**Статус:** Ready for Use

---

## 📋 Оглавление

1. [Обзор](#1-обзор)
2. [Системные требования](#2-системные-требования)
3. [Быстрый старт](#3-быстрый-старт)
4. [Архитектура среды разработки](#4-архитектура-среды-разработки)
5. [Детальная настройка](#5-детальная-настройка)
6. [Workflow разработки](#6-workflow-разработки)
7. [Тестирование](#7-тестирование)
8. [Отладка](#8-отладка)
9. [Troubleshooting](#9-troubleshooting)
10. [Best Practices](#10-best-practices)

---

## 1. Обзор

### 1.1. Цель

Эта среда разработки позволяет разрабатывать и тестировать OpticsERP **без реального оборудования ККТ и подключения к ОФД**.

### 1.2. Ключевые возможности

✅ **Полная эмуляция фискализации** - Mock ККТ + Mock ОФД
✅ **Быстрая обратная связь** - Синхронизация каждые 5 секунд
✅ **Изолированная среда** - Не влияет на production/staging
✅ **E2E тестирование** - Полный цикл от POS до фискализации
✅ **Hot reload** - Odoo автоматически перезагружается при изменениях
✅ **Мониторинг** - Опциональные Prometheus + Grafana

### 1.3. Что НЕ включено

❌ Реальное оборудование ККТ (Атол, Эвотор и т.д.)
❌ Подключение к реальному ОФД
❌ Production данные
❌ SMS/Email уведомления

---

## 2. Системные требования

### 2.1. Минимальные требования

| Компонент | Требование |
|-----------|------------|
| **OS** | Windows 10/11, Ubuntu 22.04+, macOS 12+ |
| **RAM** | 8 GB (рекомендуется 16 GB) |
| **CPU** | 4 cores (рекомендуется 8 cores) |
| **Диск** | 20 GB свободного места |
| **Docker** | Docker 24.0+, Docker Compose v2.20+ |
| **Git** | Git 2.30+ |
| **Python** | Python 3.11+ (для локальной разработки) |

### 2.2. Проверка окружения

```bash
# Версии инструментов
docker --version          # Docker version 24.0+
docker-compose --version  # Docker Compose version v2.20+
git --version            # git version 2.30+
python --version         # Python 3.11+

# Доступная память
docker system info | grep "Total Memory"  # >= 8 GB

# Доступное место на диске
df -h | grep /var/lib/docker  # >= 20 GB свободного
```

---

## 3. Быстрый старт

### 3.1. Клонирование репозитория

```bash
# Клонировать репозиторий
git clone https://github.com/bozzyk44/OpticsERP.git
cd OpticsERP

# Переключиться на ветку разработки
git checkout feature/phase1-poc
```

### 3.2. Настройка конфигурации

```bash
# Скопировать development конфигурацию
cp .env.dev .env

# Проверить конфигурацию
cat .env | grep -E "^(POSTGRES_|KKT_|ODOO_)"
```

**Ожидаемый вывод:**
```bash
POSTGRES_DB=opticserp_dev
POSTGRES_USER=odoo
POSTGRES_PASSWORD=odoo_dev_password_123
KKT_MODE=mock
KKT_ADAPTER_URL=http://kkt_adapter:8000
ODOO_ADMIN_PASSWORD=admin
```

### 3.3. Запуск среды разработки

```bash
# Запустить все сервисы
docker-compose -f docker-compose.dev.yml up -d

# Проверить статус (все должны быть "Up (healthy)")
docker-compose -f docker-compose.dev.yml ps
```

**Ожидаемый вывод:**
```
NAME                           STATUS
opticserp_kkt_adapter_dev      Up (healthy)
opticserp_mock_ofd_dev         Up (healthy)
opticserp_mock_odoo_api_dev    Up (healthy)
opticserp_odoo_dev             Up (healthy)
opticserp_postgres_dev         Up (healthy)
opticserp_redis_dev            Up (healthy)
```

### 3.4. Проверка доступности

```bash
# Odoo web interface
curl http://localhost:8069/web/health
# Ожидаемый вывод: {"status": "ok"}

# KKT Adapter API
curl http://localhost:8000/v1/health
# Ожидаемый вывод: {"status": "healthy", "circuit_breaker": "CLOSED", ...}

# Mock OFD Server
curl http://localhost:9000/ofd/v1/health
# Ожидаемый вывод: {"status": "healthy", "receipts_received": 0, ...}

# Mock Odoo API
curl http://localhost:8070/api/v1/health
# Ожидаемый вывод: {"status": "healthy", "heartbeats_received": 0}
```

### 3.5. Первый вход в Odoo

1. Открыть браузер: http://localhost:8069
2. Создать базу данных (если первый запуск):
   - **Master Password:** admin
   - **Database Name:** opticserp_dev
   - **Email:** admin@example.com
   - **Password:** admin
   - **Language:** Russian / Русский
   - **Country:** Russia
3. Установить модули:
   - Point of Sale (`optics_pos_ru54fz`)
   - Optics Core (`optics_core`)

### 3.6. Тест фискализации

```bash
# Создать тестовый чек через API
curl -X POST http://localhost:8000/v1/kkt/receipt \
  -H "Content-Type: application/json" \
  -H "X-Idempotency-Key: test-receipt-001" \
  -d '{
    "pos_id": "POS-001",
    "items": [
      {
        "name": "Очки солнцезащитные Ray-Ban",
        "quantity": 1,
        "price": 5000.00,
        "tax_rate": 20
      }
    ],
    "total": 5000.00,
    "payment_method": "card"
  }'

# Проверить статус буфера
curl http://localhost:8000/v1/kkt/buffer/status
# Ожидаемый вывод: {"pending_count": 0, "synced_count": 1, ...}
```

**Готово!** Среда разработки настроена и работает. 🎉

---

## 4. Архитектура среды разработки

### 4.1. Диаграмма сервисов

```
┌─────────────────────────────────────────────────────────┐
│  Development Network (opticserp_dev_network)            │
│                                                         │
│  ┌──────────────┐          ┌──────────────┐            │
│  │  Odoo 17     │◄─────────│  PostgreSQL  │            │
│  │  :8069       │  DB Conn │  :5433       │            │
│  └──────┬───────┘          └──────────────┘            │
│         │                                               │
│         │ API Calls                                     │
│         ▼                                               │
│  ┌──────────────┐          ┌──────────────┐            │
│  │ KKT Adapter  │◄─────────│    Redis     │            │
│  │ (Mock Mode)  │  Lock    │    :6380     │            │
│  │  :8000       │          └──────────────┘            │
│  └──────┬───────┘                                       │
│         │                                               │
│         │ OFD Sync      │ Heartbeat                    │
│         ▼               ▼                               │
│  ┌──────────────┐   ┌──────────────┐                   │
│  │  Mock OFD    │   │ Mock Odoo    │                   │
│  │  Server      │   │ API Server   │                   │
│  │  :9000       │   │  :8070       │                   │
│  └──────────────┘   └──────────────┘                   │
│                                                         │
│  Optional Monitoring:                                  │
│  ┌──────────────┐   ┌──────────────┐                   │
│  │ Prometheus   │◄──│   Grafana    │                   │
│  │  :9091       │   │   :3001      │                   │
│  └──────────────┘   └──────────────┘                   │
└─────────────────────────────────────────────────────────┘
```

### 4.2. Компоненты

| Сервис | Назначение | Порт | Mock? |
|--------|-----------|------|-------|
| **Odoo** | ERP/POS приложение | 8069 | ❌ |
| **PostgreSQL** | База данных Odoo | 5433 | ❌ |
| **Redis** | Distributed Lock, очередь задач | 6380 | ❌ |
| **KKT Adapter** | Адаптер ККТ (mock режим) | 8000 | ✅ |
| **Mock OFD** | Эмулятор ОФД API | 9000 | ✅ |
| **Mock Odoo API** | Эмулятор Odoo API (heartbeat) | 8070 | ✅ |
| **Prometheus** | Сбор метрик | 9091 | ❌ |
| **Grafana** | Визуализация метрик | 3001 | ❌ |

### 4.3. Потоки данных

**Поток фискализации (двухфазный):**

```
1. POS (Odoo) → KKT Adapter API
   POST /v1/kkt/receipt

2. KKT Adapter → Mock KKT Driver (Phase 1)
   - Генерация фискального номера
   - Печать чека (эмуляция 200-500ms)
   - Запись в SQLite буфер

3. KKT Adapter → Mock OFD Server (Phase 2, async)
   POST /ofd/v1/receipts
   - Отправка чека в ОФД (timeout 10s)
   - Обновление статуса в буфере

4. KKT Adapter → Mock Odoo API (Heartbeat)
   POST /api/v1/kkt/heartbeat
   - Отправка статуса каждые 30s
```

### 4.4. Режимы работы

| Режим | KKT_MODE | OFD_MODE | Описание |
|-------|----------|----------|----------|
| **Development** | `mock` | `http` | Mock KKT + HTTP Mock OFD |
| **Unit Test** | `mock` | `mock` | Mock KKT + In-memory Mock OFD |
| **Integration Test** | `mock` | `http` | Mock KKT + HTTP Mock OFD (Docker) |
| **Production** | `real` | `http` | Real KKT + Real OFD |

**Текущий режим:** Development (`mock` + `http`)

---

## 5. Детальная настройка

### 5.1. Конфигурация через .env

**Основные переменные (`.env.dev`):**

```bash
# ===========================================
# Database
# ===========================================
POSTGRES_DB=opticserp_dev
POSTGRES_USER=odoo
POSTGRES_PASSWORD=odoo_dev_password_123

# ===========================================
# KKT Adapter (Mock Mode)
# ===========================================
KKT_MODE=mock                    # Mock KKT driver
OFD_MODE=http                    # HTTP Mock OFD server
BUFFER_MAX_SIZE=100              # Smaller buffer for dev
SYNC_INTERVAL=5                  # Fast sync (5s vs 30s prod)
CIRCUIT_BREAKER_THRESHOLD=3      # Fail after 3 errors

# ===========================================
# Mock Services
# ===========================================
MOCK_OFD_URL=http://mock_ofd:9000
MOCK_ODOO_URL=http://mock_odoo_api:8070

# ===========================================
# Logging
# ===========================================
LOG_LEVEL=DEBUG                  # Verbose logging
PYTHONUNBUFFERED=1              # No buffering

# ===========================================
# Odoo Development Mode
# ===========================================
ODOO_WORKERS=0                   # 0 = dev mode with auto-reload
ODOO_DEV_MODE=all               # Enable all dev features
ODOO_LOG_LEVEL=debug
```

### 5.2. Настройка Odoo config

**Файл:** `odoo.conf`

```ini
[options]
# Development mode
dev_mode = all
workers = 0
max_cron_threads = 0

# Logging
log_level = debug
log_handler = :DEBUG

# Auto-reload on file changes
auto_reload = True

# Database
db_name = opticserp_dev
db_filter = ^opticserp_dev$

# Addons path
addons_path = /mnt/extra-addons,/usr/lib/python3/dist-packages/odoo/addons

# KKT Adapter integration
kkt_adapter_url = http://kkt_adapter:8000
kkt_adapter_timeout = 10

# Session timeout (24h for development)
session_timeout = 86400
```

### 5.3. Настройка Mock OFD поведения

**Scenario 1: Успешная обработка всех запросов (по умолчанию)**

```bash
# В .env.dev
MOCK_OFD_FAILURE_MODE=disabled
```

**Scenario 2: Сбой следующих N запросов (тест Circuit Breaker)**

```bash
# В .env.dev
MOCK_OFD_FAILURE_MODE=count
MOCK_OFD_FAILURE_COUNT=5  # Fail next 5 requests

# Или через API (runtime)
curl -X POST http://localhost:9000/ofd/v1/admin/set-failure \
  -H "Content-Type: application/json" \
  -d '{"failure_count": 5}'
```

**Scenario 3: Постоянные сбои (тест DLQ)**

```bash
# Через API
curl -X POST http://localhost:9000/ofd/v1/admin/set-failure \
  -H "Content-Type: application/json" \
  -d '{"permanent_failure": true}'

# Восстановить
curl -X POST http://localhost:9000/ofd/v1/admin/set-success
```

**Scenario 4: Задержка ответа (тест timeout)**

```bash
# В .env.dev
MOCK_OFD_RESPONSE_DELAY=15  # 15s delay (> timeout)
```

### 5.4. Включение мониторинга

```bash
# Запустить с Prometheus + Grafana
COMPOSE_PROFILES=monitoring docker-compose -f docker-compose.dev.yml up -d

# Проверить доступность
curl http://localhost:9091/targets  # Prometheus targets
curl http://localhost:3001          # Grafana login (admin/admin)
```

**Grafana dashboards:**
- KKT Buffer Status: http://localhost:3001/d/kkt-buffer
- Circuit Breaker: http://localhost:3001/d/circuit-breaker
- Performance: http://localhost:3001/d/performance

---

## 6. Workflow разработки

### 6.1. Типичный рабочий день

**Утро (Start of day):**

```bash
# 1. Pull latest changes
git pull origin feature/phase1-poc

# 2. Start services
docker-compose -f docker-compose.dev.yml up -d

# 3. Check health
docker-compose -f docker-compose.dev.yml ps

# 4. View logs (background terminal)
docker-compose -f docker-compose.dev.yml logs -f
```

**Разработка:**

```bash
# 1. Edit code (Odoo modules, KKT Adapter)
code addons/optics_pos_ru54fz/models/pos_session.py

# 2. Odoo автоматически перезагрузится (ODOO_WORKERS=0)
# Проверить логи:
docker-compose -f docker-compose.dev.yml logs -f odoo

# 3. Если изменения в KKT Adapter:
docker-compose -f docker-compose.dev.yml restart kkt_adapter
```

**Тестирование:**

```bash
# Unit tests
pytest tests/unit/test_buffer_db.py -v

# Integration tests (with Docker stack)
./scripts/run_docker_tests.sh --filter test_two_phase_fiscalization

# Manual testing через Odoo UI
# http://localhost:8069 → Point of Sale → New Session
```

**Вечер (End of day):**

```bash
# 1. Commit changes
git add .
git commit -m "feat(pos): add offline mode indicator [OPTERP-XX]"
git push origin feature/phase1-poc

# 2. Stop services (optional, или оставить запущенными)
docker-compose -f docker-compose.dev.yml down
```

### 6.2. Hot Reload

**Odoo auto-reload (ODOO_WORKERS=0):**
- Изменения в Python модулях → автоматическая перезагрузка
- Изменения в XML/JS → F5 в браузере
- Изменения в `__manifest__.py` → Restart Odoo container

**KKT Adapter manual reload:**

```bash
# Restart KKT Adapter
docker-compose -f docker-compose.dev.yml restart kkt_adapter

# Or rebuild if Dockerfile changed
docker-compose -f docker-compose.dev.yml build kkt_adapter
docker-compose -f docker-compose.dev.yml up -d kkt_adapter
```

### 6.3. Работа с базой данных

**Подключение к PostgreSQL:**

```bash
# Через psql
docker exec -it opticserp_postgres_dev psql -U odoo -d opticserp_dev

# Через DBeaver/pgAdmin
# Host: localhost
# Port: 5433
# Database: opticserp_dev
# User: odoo
# Password: odoo_dev_password_123
```

**Сброс базы данных:**

```bash
# Method 1: Через Odoo UI
# http://localhost:8069/web/database/manager → Drop Database

# Method 2: Через psql
docker exec -it opticserp_postgres_dev psql -U odoo -c "DROP DATABASE opticserp_dev;"
docker exec -it opticserp_postgres_dev psql -U odoo -c "CREATE DATABASE opticserp_dev;"

# Method 3: Удалить volume и пересоздать
docker-compose -f docker-compose.dev.yml down -v
docker-compose -f docker-compose.dev.yml up -d
```

### 6.4. Работа с буфером SQLite

**Инспекция буфера:**

```bash
# Войти в контейнер KKT Adapter
docker exec -it opticserp_kkt_adapter_dev bash

# Открыть SQLite
sqlite3 /app/data/buffer.db

# Запросы
SELECT * FROM receipts ORDER BY created_at DESC LIMIT 10;
SELECT COUNT(*) FROM receipts WHERE status = 'pending';
SELECT * FROM dlq;
```

**Сброс буфера:**

```bash
# Удалить файл буфера (автоматически пересоздастся)
docker exec -it opticserp_kkt_adapter_dev rm /app/data/buffer.db
docker-compose -f docker-compose.dev.yml restart kkt_adapter

# Или удалить volume
docker-compose -f docker-compose.dev.yml down -v
docker volume rm opticserp_kkt_buffer_dev
docker-compose -f docker-compose.dev.yml up -d
```

---

## 7. Тестирование

### 7.1. Unit Tests

```bash
# All unit tests
pytest tests/unit -v

# Specific module
pytest tests/unit/test_buffer_db.py -v
pytest tests/unit/test_hlc.py -v
pytest tests/unit/test_circuit_breaker.py -v

# With coverage
pytest tests/unit --cov=kkt_adapter --cov-report=html
open htmlcov/index.html
```

### 7.2. Integration Tests (Docker)

```bash
# All integration tests
./scripts/run_docker_tests.sh

# Specific test
./scripts/run_docker_tests.sh --filter test_two_phase_fiscalization

# Verbose output
./scripts/run_docker_tests.sh --verbose

# Keep services running for debugging
./scripts/run_docker_tests.sh --keep-up
```

### 7.3. Manual E2E Testing

**Scenario 1: Happy Path (Online mode)**

1. Открыть POS: http://localhost:8069 → Point of Sale
2. Создать сессию: New Session → Open Session
3. Добавить товар: Products → Ray-Ban Sunglasses (5000₽)
4. Оплатить: Payment → Card → Validate
5. Проверить фискализацию:
   ```bash
   curl http://localhost:8000/v1/kkt/buffer/status
   # {"pending_count": 0, "synced_count": 1}
   ```

**Scenario 2: Offline Mode (OFD unavailable)**

1. Отключить Mock OFD:
   ```bash
   docker-compose -f docker-compose.dev.yml stop mock_ofd
   ```
2. Создать продажу в POS (как выше)
3. Проверить буфер:
   ```bash
   curl http://localhost:8000/v1/kkt/buffer/status
   # {"pending_count": 1, "synced_count": 0, "network_status": "OFFLINE"}
   ```
4. Включить Mock OFD:
   ```bash
   docker-compose -f docker-compose.dev.yml start mock_ofd
   ```
5. Дождаться синхронизации (5s):
   ```bash
   curl http://localhost:8000/v1/kkt/buffer/status
   # {"pending_count": 0, "synced_count": 1, "network_status": "ONLINE"}
   ```

**Scenario 3: Circuit Breaker**

1. Настроить Mock OFD на сбои:
   ```bash
   curl -X POST http://localhost:9000/ofd/v1/admin/set-failure \
     -d '{"failure_count": 5}'
   ```
2. Создать 5 продаж в POS
3. Проверить Circuit Breaker:
   ```bash
   curl http://localhost:8000/v1/health
   # {"circuit_breaker": "OPEN", "failures": 5}
   ```
4. Восстановить Mock OFD:
   ```bash
   curl -X POST http://localhost:9000/ofd/v1/admin/set-success
   ```
5. Подождать 30s (recovery timeout)
6. Circuit Breaker вернется в CLOSED

### 7.4. Load Testing

```bash
# Install Apache Bench
sudo apt-get install apache2-utils

# 100 requests, concurrency 10
ab -n 100 -c 10 -p receipt.json -T application/json \
   http://localhost:8000/v1/kkt/receipt

# receipt.json:
{
  "pos_id": "POS-001",
  "items": [{"name": "Test", "quantity": 1, "price": 1000, "tax_rate": 20}],
  "total": 1000,
  "payment_method": "card"
}
```

---

## 8. Отладка

### 8.1. Просмотр логов

**Все сервисы:**

```bash
docker-compose -f docker-compose.dev.yml logs -f
```

**Конкретный сервис:**

```bash
docker-compose -f docker-compose.dev.yml logs -f kkt_adapter
docker-compose -f docker-compose.dev.yml logs -f odoo
docker-compose -f docker-compose.dev.yml logs -f mock_ofd
```

**Последние N строк:**

```bash
docker-compose -f docker-compose.dev.yml logs --tail=100 kkt_adapter
```

**Grep в логах:**

```bash
docker-compose -f docker-compose.dev.yml logs kkt_adapter | grep ERROR
docker-compose -f docker-compose.dev.yml logs odoo | grep "point_of_sale"
```

### 8.2. Отладка KKT Adapter

**Python debugger (pdb):**

1. Добавить breakpoint в код:
   ```python
   import pdb; pdb.set_trace()
   ```

2. Attach к контейнеру:
   ```bash
   docker attach opticserp_kkt_adapter_dev
   ```

**Remote debugging (VS Code):**

1. Установить `debugpy` в Dockerfile:
   ```dockerfile
   RUN pip install debugpy
   ```

2. Запустить с debugpy:
   ```python
   import debugpy
   debugpy.listen(("0.0.0.0", 5678))
   debugpy.wait_for_client()
   ```

3. Настроить VS Code (`launch.json`):
   ```json
   {
     "name": "Attach to KKT Adapter",
     "type": "python",
     "request": "attach",
     "connect": {"host": "localhost", "port": 5678},
     "pathMappings": [{"localRoot": "${workspaceFolder}/kkt_adapter", "remoteRoot": "/app"}]
   }
   ```

### 8.3. Отладка Odoo

**Odoo shell:**

```bash
docker exec -it opticserp_odoo_dev odoo shell -d opticserp_dev

# Python shell с доступом к env
>>> self.env['pos.order'].search([])
>>> self.env['product.product'].browse(1)
```

**Odoo logs (verbose):**

```bash
# Изменить log level в odoo.conf
log_level = debug
log_handler = :DEBUG,werkzeug:DEBUG,odoo.addons.point_of_sale:DEBUG

# Restart Odoo
docker-compose -f docker-compose.dev.yml restart odoo
```

### 8.4. Инспекция сетевых запросов

**Curl с verbose:**

```bash
curl -v http://localhost:8000/v1/kkt/receipt \
  -H "Content-Type: application/json" \
  -H "X-Idempotency-Key: test-001" \
  -d @receipt.json
```

**Tcpdump (packet capture):**

```bash
# Capture traffic между KKT Adapter и Mock OFD
docker exec opticserp_kkt_adapter_dev tcpdump -i any -n host mock_ofd
```

**Network inspection (Docker):**

```bash
# List containers on network
docker network inspect opticserp_dev_network

# Test connectivity
docker exec opticserp_kkt_adapter_dev ping -c 3 mock_ofd
docker exec opticserp_kkt_adapter_dev curl http://mock_ofd:9000/ofd/v1/health
```

---

## 9. Troubleshooting

### 9.1. Сервисы не стартуют

**Симптом:** `docker-compose ps` показывает "Exit 1" или "Restarting"

**Решение:**

```bash
# 1. Проверить логи
docker-compose -f docker-compose.dev.yml logs [service_name]

# 2. Проверить занятые порты
netstat -tuln | grep -E "8000|8069|5433|6380|9000|8070"

# 3. Убить процессы на портах (Windows)
python scripts/kill_port.py 8000 8069 5433 6380 9000 8070

# 4. Перезапустить
docker-compose -f docker-compose.dev.yml down
docker-compose -f docker-compose.dev.yml up -d
```

### 9.2. Health checks failed

**Симптом:** Services в состоянии "Up (unhealthy)"

**Решение:**

```bash
# 1. Проверить health check endpoint вручную
curl http://localhost:8000/v1/health
curl http://localhost:9000/ofd/v1/health

# 2. Увеличить start_period в docker-compose.dev.yml
healthcheck:
  start_period: 60s  # Was 30s

# 3. Проверить зависимости (depends_on)
# Возможно, сервис стартует раньше зависимостей

# 4. Rebuild
docker-compose -f docker-compose.dev.yml build --no-cache
docker-compose -f docker-compose.dev.yml up -d
```

### 9.3. Odoo не видит custom modules

**Симптом:** Apps menu пуст, модули optics_* не отображаются

**Решение:**

```bash
# 1. Проверить volume mount
docker exec opticserp_odoo_dev ls -la /mnt/extra-addons
# Должны быть: optics_core, optics_pos_ru54fz, connector_b, ru_accounting_extras

# 2. Проверить addons_path в odoo.conf
docker exec opticserp_odoo_dev cat /etc/odoo/odoo.conf | grep addons_path

# 3. Update Apps List в Odoo
# Odoo UI → Apps → Update Apps List

# 4. Restart Odoo с --dev all
docker-compose -f docker-compose.dev.yml restart odoo
```

### 9.4. KKT Adapter не синхронизирует буфер

**Симптом:** `pending_count` растет, `synced_count` не меняется

**Решение:**

```bash
# 1. Проверить Circuit Breaker
curl http://localhost:8000/v1/health
# Если "circuit_breaker": "OPEN" → нужно восстановить Mock OFD

# 2. Проверить Mock OFD доступность
curl http://localhost:9000/ofd/v1/health

# 3. Проверить логи sync_worker
docker-compose -f docker-compose.dev.yml logs kkt_adapter | grep sync_worker

# 4. Принудительная синхронизация
curl -X POST http://localhost:8000/v1/kkt/buffer/sync

# 5. Проверить переменные окружения
docker exec opticserp_kkt_adapter_dev env | grep -E "OFD|SYNC"
```

### 9.5. PostgreSQL connection refused

**Симптом:** `psycopg2.OperationalError: could not connect to server`

**Решение:**

```bash
# 1. Проверить PostgreSQL статус
docker-compose -f docker-compose.dev.yml ps postgres

# 2. Проверить health check
docker exec opticserp_postgres_dev pg_isready -U odoo

# 3. Проверить логи PostgreSQL
docker-compose -f docker-compose.dev.yml logs postgres

# 4. Проверить переменные окружения
docker exec opticserp_postgres_dev env | grep POSTGRES

# 5. Recreate volume (ОСТОРОЖНО: потеря данных!)
docker-compose -f docker-compose.dev.yml down -v
docker volume rm opticserp_postgres_dev
docker-compose -f docker-compose.dev.yml up -d
```

### 9.6. "Disk full" error

**Симптом:** `no space left on device`

**Решение:**

```bash
# 1. Проверить место на диске
df -h

# 2. Удалить неиспользуемые Docker объекты
docker system prune -a --volumes
# WARNING: This will remove all unused containers, networks, images, volumes

# 3. Удалить только volumes проекта
docker volume ls | grep opticserp
docker volume rm opticserp_postgres_dev opticserp_odoo_dev opticserp_kkt_buffer_dev

# 4. Очистить Docker builder cache
docker builder prune -a
```

---

## 10. Best Practices

### 10.1. Git Workflow

```bash
# 1. Всегда работать в feature branch
git checkout -b feature/OPTERP-XXX-short-description

# 2. Commit message format
git commit -m "feat(scope): description [OPTERP-XXX]"
# Types: feat, fix, docs, test, refactor, chore

# 3. Push регулярно
git push origin feature/OPTERP-XXX-short-description

# 4. Pull request с описанием
# Title: [OPTERP-XXX] Short description
# Body: Detailed description, acceptance criteria checklist
```

### 10.2. Code Quality

```bash
# 1. Lint перед commit
flake8 kkt_adapter/app
pylint kkt_adapter/app

# 2. Format code
black kkt_adapter/app
isort kkt_adapter/app

# 3. Type checking
mypy kkt_adapter/app

# 4. Tests coverage ≥95%
pytest tests/unit --cov=kkt_adapter --cov-report=term-missing
```

### 10.3. Работа с .env

```bash
# ✅ ПРАВИЛЬНО: Use .env.dev template
cp .env.dev .env
# Edit .env (not tracked by Git)

# ❌ НЕПРАВИЛЬНО: Commit .env
git add .env  # DON'T DO THIS!

# ✅ ПРАВИЛЬНО: Update .env.dev template
# Если добавили новую переменную:
1. Добавить в .env.dev (с комментарием)
2. Commit .env.dev
3. Обновить документацию
```

### 10.4. Работа с secrets

```bash
# ❌ НИКОГДА не коммитить:
# - API tokens
# - Passwords
# - Private keys
# - .env файлы с реальными credentials

# ✅ Использовать:
# - .env (gitignored)
# - Docker secrets (production)
# - Environment variables в CI/CD
```

### 10.5. Тестирование

```bash
# 1. Unit tests первые (TDD)
# Write test → Red → Write code → Green → Refactor

# 2. Integration tests после unit tests

# 3. Manual testing последние

# 4. Load testing перед merge в main
./scripts/run_docker_tests.sh --filter load
```

### 10.6. Логирование

```python
# ✅ ПРАВИЛЬНО: Structured logging
logger.info("Receipt created", extra={
    "receipt_id": receipt.id,
    "pos_id": receipt.pos_id,
    "total": receipt.total
})

# ❌ НЕПРАВИЛЬНО: String concatenation
logger.info(f"Receipt {receipt.id} created for POS {receipt.pos_id}")

# ✅ ПРАВИЛЬНО: Log levels
# DEBUG - detailed diagnostic info
# INFO - general informational messages
# WARNING - something unexpected, but app still works
# ERROR - error occurred, but app can continue
# CRITICAL - serious error, app cannot continue
```

### 10.7. Performance

```bash
# 1. Профилирование перед оптимизацией
python -m cProfile -o profile.stats kkt_adapter/app/main.py

# 2. Мониторинг метрик
# - Response time P95 < 100ms
# - Buffer sync time < 10s
# - PostgreSQL queries < 50ms

# 3. Нагрузочное тестирование
ab -n 1000 -c 50 http://localhost:8000/v1/kkt/receipt
```

---

## Заключение

Эта среда разработки предоставляет:

✅ **Полная эмуляция** фискализации без реального оборудования
✅ **Быстрая обратная связь** - изменения видны сразу
✅ **Изолированность** - не влияет на production
✅ **Воспроизводимость** - одинаковая среда у всех разработчиков
✅ **Тестируемость** - unit + integration + E2E тесты

**Следующие шаги:**
1. Прочитать `docs/testing/KKT_EMULATION_GUIDE.md` - детали эмуляции
2. Прочитать `docs/testing/DOCKER_TESTING_GUIDE.md` - детали Docker тестирования
3. Изучить структуру проекта в `CLAUDE.md` §6
4. Начать с задачи из JIRA (OPTERP-XX)

**Контакты:**
- JIRA: https://bozzyk44.atlassian.net/browse/OPTERP
- Git: https://github.com/bozzyk44/OpticsERP
- Docs: `docs/` directory

---

**Последнее обновление:** 2025-11-30
**Версия:** 1.0
**Автор:** Claude Code
