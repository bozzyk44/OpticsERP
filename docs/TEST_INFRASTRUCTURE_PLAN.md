# План настройки тестовой инфраструктуры OpticsERP

**Дата:** 2025-10-09
**Статус:** Рекомендации
**Приоритет:** High (перед MVP)

---

## 1. Текущее состояние

### Что работает ✅

**Unit тесты (214 tests total):**
- 23 tests: test_heartbeat.py
- 23 tests: test_circuit_breaker.py
- 29 tests: test_sync_worker.py + test_sync_worker_distributed_lock.py
- 16 tests: test_mock_ofd_server.py
- 19 tests: test_mock_odoo_server.py
- 104+ tests: другие unit тесты (buffer, HLC, fiscal, etc.)

**Integration тесты (28 tests total):**
- 14 tests: test_ofd_sync.py
- 14 tests: test_receipt_workflow.py

**POC тесты (3 tests):**
- POC-1: test_poc_1_emulator.py (1 comprehensive test)
- POC-4: test_poc_4_offline.py (1 comprehensive test)
- POC-5: test_poc_5_splitbrain.py (3 scenario tests)

**Mock servers:**
- MockOFDServer (tests/integration/mock_ofd_server.py)
- MockOdooServer (tests/integration/mock_odoo_server.py)

### Проблемы ❌

1. **Ручной запуск инфраструктуры**
   ```bash
   # Текущий workflow для POC-тестов
   Terminal 1: cd kkt_adapter/app && python main.py  # Manually!
   Terminal 2: pytest tests/poc/test_poc_1_emulator.py -v -s
   ```
   - ❌ Нет автоматического запуска FastAPI
   - ❌ Redis нужен вручную запускать
   - ❌ Mock servers создаются в тестах (не реиспользуются)

2. **Нет централизованных fixtures**
   - Каждый POC-тест дублирует код:
     ```python
     @pytest.fixture
     def fastapi_server():
         try:
             response = requests.get(f"{FASTAPI_BASE_URL}/v1/health", timeout=2)
         except:
             pytest.skip("FastAPI not running")
     ```
   - ❌ Дублирование кода в 3 POC-тестах
   - ❌ Нет общего conftest.py для POC

3. **Нет изоляции данных**
   - SQLite buffer.db: `kkt_adapter/data/buffer.db` (один файл для всех)
   - KKT log: `kkt_adapter/data/kkt_print.log` (перезаписывается)
   - ❌ Тесты могут конфликтовать при параллельном запуске
   - ❌ Cleanup делается в каждом тесте отдельно

4. **Нет pytest.ini конфигурации**
   - ❌ Нет markers (unit, integration, poc, slow)
   - ❌ Нет настроек логирования
   - ❌ Нет coverage конфигурации

5. **Нет CI/CD готовности**
   - ❌ Нет Makefile для запуска тестов
   - ❌ Нет docker-compose.test.yml
   - ❌ Нет GitHub Actions workflow

---

## 2. Рекомендуемые улучшения

### Фаза 1: Базовая автоматизация (1-2 дня)

#### 1.1 Pytest Configuration (pytest.ini)

**Файл:** `pytest.ini`

```ini
[pytest]
# Paths
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*

# Markers
markers =
    unit: Unit tests (fast, no external dependencies)
    integration: Integration tests (require mock servers)
    poc: POC tests (require FastAPI server + Redis)
    slow: Slow tests (>10s)
    redis: Tests requiring Redis
    fastapi: Tests requiring FastAPI server

# Output
addopts =
    --verbose
    --tb=short
    --strict-markers
    --color=yes
    -ra
    --junit-xml=tests/logs/junit.xml
    --html=tests/logs/report.html
    --self-contained-html

# Coverage
[coverage:run]
source = kkt_adapter/app
omit =
    */tests/*
    */migrations/*
    */__pycache__/*

[coverage:report]
precision = 2
show_missing = True
skip_covered = False

[coverage:html]
directory = tests/logs/coverage_html
```

**Использование:**
```bash
# Запуск только unit тестов (быстро)
pytest -m unit

# Запуск integration тестов
pytest -m integration

# Запуск POC тестов
pytest -m poc

# Запуск без slow тестов
pytest -m "not slow"

# Запуск с coverage
pytest --cov --cov-report=html
```

#### 1.2 Centralized Conftest (tests/conftest.py)

**Файл:** `tests/conftest.py`

```python
"""
Global pytest fixtures for OpticsERP tests

Provides shared fixtures for:
- FastAPI server (automatic startup)
- Mock OFD Server (reusable)
- Mock Odoo Server (reusable)
- Redis connection
- Buffer cleanup
"""

import pytest
import requests
import time
import subprocess
import sys
from pathlib import Path

# Add paths
sys.path.insert(0, str(Path(__file__).parent / 'integration'))
sys.path.insert(0, str(Path(__file__).parent.parent / 'kkt_adapter' / 'app'))

from mock_ofd_server import MockOFDServer
from mock_odoo_server import MockOdooServer
from buffer import init_buffer_db, get_db, close_buffer_db


# ====================
# Configuration
# ====================

FASTAPI_BASE_URL = "http://localhost:8000"
MOCK_OFD_PORT = 8080
MOCK_ODOO_PORT = 8069


# ====================
# FastAPI Server Fixture
# ====================

@pytest.fixture(scope="session")
def fastapi_server_auto():
    """
    Automatically start FastAPI server for session

    Starts server in background process.
    Stops server at end of session.

    Marks: fastapi
    """
    # Check if already running
    try:
        response = requests.get(f"{FASTAPI_BASE_URL}/v1/health", timeout=2)
        if response.status_code == 200:
            print("✅ FastAPI server already running")
            yield FASTAPI_BASE_URL
            return
    except:
        pass

    # Start server in background
    print("🚀 Starting FastAPI server...")

    process = subprocess.Popen(
        [sys.executable, "main.py"],
        cwd=Path(__file__).parent.parent / "kkt_adapter" / "app",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

    # Wait for server to be ready (max 10s)
    start_time = time.time()
    while time.time() - start_time < 10:
        try:
            response = requests.get(f"{FASTAPI_BASE_URL}/v1/health", timeout=1)
            if response.status_code == 200:
                print("✅ FastAPI server started")
                break
        except:
            time.sleep(0.5)
    else:
        process.kill()
        pytest.fail("FastAPI server failed to start within 10s")

    yield FASTAPI_BASE_URL

    # Stop server
    print("🛑 Stopping FastAPI server...")
    process.terminate()
    process.wait(timeout=5)


@pytest.fixture(scope="function")
def fastapi_server_manual():
    """
    Check FastAPI server is running (manual start)

    Use this for quick local testing where you
    start server manually.

    Marks: fastapi
    """
    try:
        response = requests.get(f"{FASTAPI_BASE_URL}/v1/health", timeout=2)
        if response.status_code != 200:
            pytest.skip("FastAPI server not responding")
    except:
        pytest.skip("FastAPI server not running. Start with: cd kkt_adapter/app && python main.py")

    yield FASTAPI_BASE_URL


# ====================
# Mock Server Fixtures
# ====================

@pytest.fixture(scope="session")
def mock_ofd_server_session():
    """
    Session-scoped Mock OFD Server

    Shared across all tests in session.
    Reset state between tests with mock_ofd_server fixture.
    """
    server = MockOFDServer(port=MOCK_OFD_PORT)
    server.start()
    time.sleep(1)

    yield server

    server.stop()


@pytest.fixture
def mock_ofd_server(mock_ofd_server_session):
    """
    Function-scoped Mock OFD Server (reset state)

    Resets server state before each test.
    """
    server = mock_ofd_server_session
    server.reset()
    server.set_success()  # Default: success mode

    yield server

    # Cleanup after test
    server.reset()


@pytest.fixture(scope="session")
def mock_odoo_server_session():
    """
    Session-scoped Mock Odoo Server

    Shared across all tests in session.
    """
    server = MockOdooServer(port=MOCK_ODOO_PORT)
    server.start()
    time.sleep(1)

    yield server

    server.stop()


@pytest.fixture
def mock_odoo_server(mock_odoo_server_session):
    """
    Function-scoped Mock Odoo Server (reset state)
    """
    server = mock_odoo_server_session
    server.reset()
    server.set_success()

    yield server

    server.reset()


# ====================
# Buffer Cleanup Fixture
# ====================

@pytest.fixture
def clean_buffer():
    """
    Clean buffer before test

    Deletes all receipts, DLQ, and events.
    """
    init_buffer_db()

    conn = get_db()
    conn.execute("DELETE FROM receipts")
    conn.execute("DELETE FROM dlq")
    conn.execute("DELETE FROM buffer_events")
    conn.commit()

    yield

    # Optional: cleanup after test
    # (usually not needed, next test will clean)


# ====================
# Redis Fixture
# ====================

@pytest.fixture
def redis_available():
    """
    Check Redis is available

    Marks: redis
    """
    import redis
    try:
        client = redis.Redis(host='localhost', port=6379, db=0)
        client.ping()
        yield client
    except:
        pytest.skip("Redis not running. Start with: docker-compose up -d redis")


# ====================
# Pytest Hooks
# ====================

def pytest_configure(config):
    """
    Configure pytest session
    """
    config.addinivalue_line("markers", "unit: Unit tests")
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "poc: POC tests")
    config.addinivalue_line("markers", "slow: Slow tests")
    config.addinivalue_line("markers", "redis: Tests requiring Redis")
    config.addinivalue_line("markers", "fastapi: Tests requiring FastAPI")
```

**Использование в POC-тестах:**
```python
# tests/poc/test_poc_1_emulator.py
import pytest

@pytest.mark.poc
@pytest.mark.fastapi
def test_poc1_create_50_receipts(
    fastapi_server_auto,  # Automatically starts server!
    clean_buffer,
):
    # Server already running, just use it
    response = requests.post(f"{fastapi_server_auto}/v1/kkt/receipt", ...)
```

#### 1.3 Docker Compose для тестирования (docker-compose.test.yml)

**Файл:** `docker-compose.test.yml`

```yaml
# Docker Compose for Testing Environment
# Usage: docker-compose -f docker-compose.test.yml up -d

services:
  # Redis - Required for POC-5 (distributed lock)
  redis:
    image: redis:7-alpine
    container_name: opticserp_test_redis
    ports:
      - "6379:6379"
    command: redis-server --appendonly no  # Faster for tests
    networks:
      - test_network
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 2s
      retries: 3

  # FastAPI KKT Adapter (optional - can run locally)
  kkt_adapter:
    build:
      context: .
      dockerfile: kkt_adapter/Dockerfile
    container_name: opticserp_test_kkt_adapter
    ports:
      - "8000:8000"
    environment:
      - REDIS_HOST=redis
      - REDIS_PORT=6379
      - OFD_API_URL=http://mock_ofd:8080
    depends_on:
      redis:
        condition: service_healthy
    networks:
      - test_network
    volumes:
      - ./kkt_adapter/data:/app/data
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/v1/health"]
      interval: 5s
      timeout: 2s
      retries: 5

networks:
  test_network:
    driver: bridge
```

**Использование:**
```bash
# Запуск тестовой инфраструктуры
docker-compose -f docker-compose.test.yml up -d

# Проверка готовности
docker-compose -f docker-compose.test.yml ps

# Запуск тестов (инфраструктура уже готова)
pytest -m poc -v -s

# Остановка
docker-compose -f docker-compose.test.yml down
```

#### 1.4 Makefile для тестирования

**Файл:** `Makefile`

```makefile
.PHONY: help test test-unit test-integration test-poc test-all test-fast test-coverage clean-test

help:  ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# ====================
# Test Commands
# ====================

test-unit:  ## Run unit tests (fast, no infrastructure)
	pytest -m unit -v

test-integration:  ## Run integration tests (require mock servers)
	pytest -m integration -v

test-poc:  ## Run POC tests (require FastAPI + Redis)
	@echo "Starting test infrastructure..."
	docker-compose -f docker-compose.test.yml up -d
	@echo "Waiting for services..."
	sleep 5
	pytest -m poc -v -s
	docker-compose -f docker-compose.test.yml down

test-fast:  ## Run fast tests only (unit + integration, no POC)
	pytest -m "not slow and not poc" -v

test-all:  ## Run all tests (unit + integration + POC)
	@echo "Starting test infrastructure..."
	docker-compose -f docker-compose.test.yml up -d
	@echo "Waiting for services..."
	sleep 5
	pytest -v
	docker-compose -f docker-compose.test.yml down

test-coverage:  ## Run tests with coverage report
	pytest --cov --cov-report=html --cov-report=term -v
	@echo "Coverage report: tests/logs/coverage_html/index.html"

test-poc-manual:  ## Run POC tests (manual infrastructure start)
	@echo "⚠️  Make sure FastAPI and Redis are running!"
	@echo "   FastAPI: cd kkt_adapter/app && python main.py"
	@echo "   Redis: docker-compose up -d redis"
	pytest -m poc -v -s

# ====================
# Cleanup
# ====================

clean-test:  ## Clean test artifacts
	rm -rf tests/logs/*.log
	rm -rf tests/logs/*.xml
	rm -rf tests/logs/*.html
	rm -rf tests/logs/coverage_html
	rm -rf .pytest_cache
	rm -rf .coverage
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

clean-buffer:  ## Clean SQLite buffer (test data)
	rm -f kkt_adapter/data/buffer.db
	rm -f kkt_adapter/data/kkt_print.log
```

**Использование:**
```bash
# Показать справку
make help

# Быстрые unit тесты (без инфраструктуры)
make test-unit

# Все тесты (автоматический запуск инфраструктуры)
make test-all

# POC тесты (с автоматической инфраструктурой)
make test-poc

# Тесты с coverage
make test-coverage

# Очистка
make clean-test
```

---

### Фаза 2: Изоляция данных (1 день)

#### 2.1 Временные SQLite базы для тестов

**Проблема:** Все тесты используют одну БД: `kkt_adapter/data/buffer.db`

**Решение:** Каждый тест использует временную БД

**Файл:** `tests/conftest.py` (дополнение)

```python
import tempfile
import os

@pytest.fixture
def isolated_buffer(monkeypatch):
    """
    Isolated SQLite buffer for each test

    Creates temporary buffer.db in /tmp.
    Cleans up after test.
    """
    # Create temp directory
    temp_dir = tempfile.mkdtemp(prefix="opticserp_test_")
    temp_buffer = Path(temp_dir) / "buffer.db"

    # Monkeypatch buffer path
    monkeypatch.setattr("buffer.BUFFER_DB_PATH", str(temp_buffer))

    # Initialize buffer
    init_buffer_db()

    yield temp_buffer

    # Cleanup
    close_buffer_db()
    try:
        os.remove(temp_buffer)
        os.rmdir(temp_dir)
    except:
        pass
```

#### 2.2 Параллельный запуск тестов (pytest-xdist)

**Установка:**
```bash
pip install pytest-xdist
```

**Конфигурация:** `pytest.ini`
```ini
[pytest]
addopts =
    --numprocesses=auto  # Parallel execution
    --dist=loadscope     # Distribute by scope (session fixtures shared)
```

**Запуск:**
```bash
# Автоматически определяет количество CPU
pytest -n auto

# Явно указать количество процессов
pytest -n 4
```

---

### Фаза 3: CI/CD интеграция (1 день)

#### 3.1 GitHub Actions Workflow

**Файл:** `.github/workflows/test.yml`

```yaml
name: Tests

on:
  push:
    branches: [main, develop, feature/*]
  pull_request:
    branches: [main, develop]

jobs:
  unit-tests:
    name: Unit Tests
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: [3.11]

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python ${{ matrix.python-version }}
        uses: actions/setup-python@v4
        with:
          python-version: ${{ matrix.python-version }}

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-cov pytest-xdist

      - name: Run unit tests
        run: pytest -m unit --cov --cov-report=xml -v

      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          files: ./coverage.xml

  integration-tests:
    name: Integration Tests
    runs-on: ubuntu-latest
    needs: unit-tests

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: 3.11

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest

      - name: Run integration tests
        run: pytest -m integration -v

  poc-tests:
    name: POC Tests
    runs-on: ubuntu-latest
    needs: integration-tests

    services:
      redis:
        image: redis:7-alpine
        ports:
          - 6379:6379
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: 3.11

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest

      - name: Start FastAPI server
        run: |
          cd kkt_adapter/app
          python main.py &
          sleep 10
          curl http://localhost:8000/v1/health

      - name: Run POC tests
        run: pytest -m poc -v -s

      - name: Upload test logs
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: test-logs
          path: tests/logs/
```

---

## 3. Приоритизация

### Критически важно (до MVP)

1. ✅ **pytest.ini** - маркеры и конфигурация (30 мин)
2. ✅ **tests/conftest.py** - централизованные fixtures (2 часа)
3. ✅ **Makefile** - команды для запуска тестов (1 час)

**Итого:** 3.5 часа

**Выгода:**
- Упрощенный запуск тестов (`make test-unit`)
- Автоматический запуск FastAPI для POC-тестов
- Переиспользование mock servers

### Важно (до Pilot)

4. ✅ **docker-compose.test.yml** - контейнеризация тестов (1 час)
5. ✅ **isolated_buffer** - изоляция данных (2 часа)
6. ✅ **pytest-xdist** - параллельные тесты (30 мин)

**Итого:** 3.5 часа

**Выгода:**
- Полная изоляция тестов
- Параллельный запуск (быстрее в 4x)
- Docker-based тестирование

### Желательно (до Production)

7. ✅ **GitHub Actions** - CI/CD (2 часа)
8. ✅ **Coverage badges** - визуализация (30 мин)
9. ✅ **Test reporting** - HTML отчеты (1 час)

**Итого:** 3.5 часа

**Выгода:**
- Автоматический запуск тестов на PR
- Coverage tracking
- Красивые отчеты

---

## 4. Roadmap

### Week 10 (Buffer Week)

- ✅ Создать pytest.ini
- ✅ Создать tests/conftest.py с централизованными fixtures
- ✅ Создать Makefile
- ✅ Обновить POC-тесты (использовать новые fixtures)
- ✅ Документация (README_TESTING.md)

**Exit criteria:** `make test-all` работает без ручного запуска инфраструктуры

### Week 11-12 (Pilot Prep)

- ✅ docker-compose.test.yml
- ✅ Изоляция данных (isolated_buffer)
- ✅ pytest-xdist (параллельные тесты)
- ✅ Обновить CI/CD (если используется)

**Exit criteria:** Тесты запускаются параллельно без конфликтов

### Week 13-14 (Pilot)

- ✅ GitHub Actions (если используется GitHub)
- ✅ Coverage badges
- ✅ Test reporting

**Exit criteria:** CI/CD полностью автоматизирован

---

## 5. Примеры использования

### Локальная разработка

```bash
# Быстрая проверка (только unit тесты)
make test-unit

# Полные тесты (POC с автоматическим Docker)
make test-all

# Ручной режим (для отладки)
# Terminal 1
cd kkt_adapter/app && python main.py

# Terminal 2
docker-compose up -d redis

# Terminal 3
pytest -m poc -v -s
```

### CI/CD

```bash
# GitHub Actions автоматически:
1. Запускает unit тесты
2. Запускает integration тесты
3. Запускает POC тесты (с Redis service)
4. Генерирует coverage report
5. Загружает артефакты (logs)
```

---

## 6. Ожидаемые результаты

### До улучшений

- ❌ Ручной запуск FastAPI + Redis для POC-тестов
- ❌ Дублирование fixtures в каждом тесте
- ❌ Нет маркеров (невозможно запустить только unit тесты)
- ❌ Нет coverage tracking
- ⏱️ Последовательный запуск всех тестов: ~5 минут

### После улучшений

- ✅ Автоматический запуск инфраструктуры (`make test-all`)
- ✅ Централизованные fixtures (DRY)
- ✅ Маркеры (`pytest -m unit` - только unit тесты)
- ✅ Coverage tracking (HTML reports)
- ✅ Параллельный запуск (pytest-xdist)
- ⏱️ Параллельный запуск: ~1-2 минуты (4x быстрее)

---

## 7. Дополнительные инструменты

### pytest-timeout

**Установка:**
```bash
pip install pytest-timeout
```

**Использование:**
```python
@pytest.mark.timeout(60)  # Max 60s per test
def test_poc4_8h_offline():
    ...
```

### pytest-html (для красивых отчетов)

**Установка:**
```bash
pip install pytest-html
```

**Использование:**
```bash
pytest --html=tests/logs/report.html --self-contained-html
```

### pytest-repeat (для flaky tests)

**Установка:**
```bash
pip install pytest-repeat
```

**Использование:**
```python
@pytest.mark.repeat(10)  # Run 10 times
def test_distributed_lock():
    ...
```

---

## 8. Метрики успеха

### Целевые метрики (после улучшений)

| Метрика | Текущее | Целевое |
|---------|---------|---------|
| Время запуска всех тестов | ~5 мин | <2 мин |
| Unit test coverage | ~95% | ≥95% |
| Integration test coverage | ~80% | ≥85% |
| Ручные шаги для запуска тестов | 3+ | 1 |
| Время до первого теста (cold start) | ~30s | <10s |
| Процент flaky tests | ? | <1% |

---

## Резюме

**Критичные улучшения (сделать до MVP):**

1. ✅ `pytest.ini` - конфигурация и маркеры
2. ✅ `tests/conftest.py` - централизованные fixtures
3. ✅ `Makefile` - упрощение команд
4. ✅ Обновить POC-тесты (использовать общие fixtures)

**Итого:** ~4 часа работы

**Выгода:**
- Автоматический запуск FastAPI для POC-тестов
- Команда `make test-all` запускает всё
- Нет дублирования кода
- Готовность к CI/CD

**Следующие шаги:**
1. Создать pytest.ini
2. Создать tests/conftest.py
3. Создать Makefile
4. Протестировать `make test-all`
