# Scripts Directory

Утилиты и вспомогательные скрипты для разработки и тестирования OpticsERP.

## Утилиты управления

### kill_port.py

Убивает процессы на заданном порту. Используется для освобождения стандартных портов сервисов.

**Использование:**

```bash
# Убить процесс на порту 8000
python scripts/kill_port.py 8000

# Принудительное убийство (SIGKILL)
python scripts/kill_port.py 8000 --force

# Убить все стандартные порты (8000, 8069, 5432, 6379)
python scripts/kill_port.py 8000 --all
```

**Стандартные порты:**
- 8000 - KKT Adapter (FastAPI)
- 8069 - Odoo
- 5432 - PostgreSQL
- 6379 - Redis

## Тестовые скрипты

### smoke_test_api.sh

Smoke-тест для KKT Adapter API. Тестирует все основные endpoints с curl.

**Использование:**

```bash
# Запустить FastAPI
cd kkt_adapter/app && python main.py &

# Запустить smoke test
bash scripts/smoke_test_api.sh
```

### test_fastapi.py

Python-скрипт для тестирования FastAPI endpoints с помощью библиотеки requests.

**Использование:**

```bash
# Инициализировать базу данных и запустить тесты
python scripts/test_fastapi.py
```

## Требования

Все скрипты требуют:
- Python 3.11+
- psutil (для kill_port.py)
- requests (для test_fastapi.py)

Установка зависимостей:

```bash
pip install -r scripts/requirements.txt
```

## См. также

- [CLAUDE.md](../CLAUDE.md) - Инструкции для AI-агента
- [Управление портами](../CLAUDE.md#управление-портами-и-процессами-обязательно) - Правила работы с портами
