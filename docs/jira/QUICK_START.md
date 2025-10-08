# JIRA Quick Start Guide

**Author:** AI Agent
**Created:** 2025-10-08
**Purpose:** Быстрый старт для работы с JIRA через REST API

---

## ⚡ Quick Start (5 минут)

### Шаг 1: Создайте API Token

1. **Откройте страницу управления API токенами:**
   ```
   https://id.atlassian.com/manage-profile/security/api-tokens
   ```

2. **Нажмите "Create API token"**

3. **Заполните:**
   - Label: `Claude Code MCP`
   - Нажмите: **Create**

4. **Скопируйте токен** (показывается только один раз!)
   ```
   Пример: ATATTxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   ```

### Шаг 2: Настройте окружение

1. **Скопируйте template в рабочий файл:**
   ```bash
   cp .env.template .env
   ```

2. **Откройте `.env` в редакторе:**
   ```bash
   # Windows
   notepad .env

   # VS Code
   code .env
   ```

3. **Замените `YOUR_API_TOKEN_HERE` на ваш токен:**
   ```bash
   export JIRA_URL="https://bozzyk44.atlassian.net"
   export JIRA_EMAIL="bozzyk44@gmail.com"
   export JIRA_API_TOKEN="ATATTxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"  # ← ваш токен
   export JIRA_PROJECT_KEY="OPTICS"
   ```

4. **Сохраните файл** (Ctrl+S)

### Шаг 3: Создайте проект в JIRA (если не существует)

1. **Откройте JIRA:**
   ```
   https://bozzyk44.atlassian.net
   ```

2. **Создайте проект:**
   - Нажмите: **Projects** → **Create project**
   - Template: **Scrum**
   - Name: `OpticsERP`
   - Key: `OPTICS` (важно!)
   - Нажмите: **Create**

### Шаг 4: Запустите тестовый скрипт

```bash
# 1. Загрузите переменные окружения
source .env

# 2. Установите Python зависимости (если нужно)
pip install requests

# 3. Запустите скрипт создания тестовой задачи
python scripts/jira_create_test_issue.py
```

**Ожидаемый вывод:**
```
📡 Connecting to JIRA: https://bozzyk44.atlassian.net
📧 Email: bozzyk44@gmail.com
📁 Project: OPTICS
🔧 Creating test issue...

✅ Success! Test issue created:
   Key: OPTICS-1
   ID: 10001
   URL: https://bozzyk44.atlassian.net/browse/OPTICS-1

🌐 Open in browser: https://bozzyk44.atlassian.net/browse/OPTICS-1
```

### Шаг 5: Проверьте задачу в JIRA

1. **Откройте URL из вывода:**
   ```
   https://bozzyk44.atlassian.net/browse/OPTICS-1
   ```

2. **Проверьте детали задачи:**
   - Summary: 🧪 Test Issue - JIRA Integration Verification
   - Type: Task
   - Priority: Medium
   - Labels: test, api, integration

---

## 🚀 Следующие шаги

### 1. Импортируйте все задачи из CSV

```bash
# Создайте скрипт массового импорта
python scripts/jira_bulk_import.py docs/jira/jira_import.csv
```

### 2. Настройте Scrum Board

1. Откройте: https://bozzyk44.atlassian.net/jira/software/c/projects/OPTICS/boards
2. Создайте **Scrum Board**
3. Настройте:
   - Columns: To Do, In Progress, Done
   - Swimlanes: Epics
   - Filter: `project = OPTICS`

### 3. Включите Roadmap

1. Откройте: https://bozzyk44.atlassian.net/jira/software/c/projects/OPTICS/roadmap
2. Group by: **Epic**
3. Color by: **Priority**

---

## 🔧 Troubleshooting

### Ошибка: "401 Unauthorized"

**Причина:** Неверный API token или email

**Решение:**
1. Проверьте `.env` файл:
   ```bash
   cat .env
   ```
2. Убедитесь, что токен скопирован полностью
3. Проверьте, что email совпадает с вашим Atlassian аккаунтом

### Ошибка: "404 Project not found"

**Причина:** Проект `OPTICS` не существует

**Решение:**
1. Создайте проект в JIRA (см. Шаг 3)
2. ИЛИ измените ключ проекта в `.env`:
   ```bash
   export JIRA_PROJECT_KEY="YOUR_EXISTING_PROJECT_KEY"
   ```

### Ошибка: "403 Forbidden"

**Причина:** У вас нет прав на создание задач

**Решение:**
1. Проверьте роль в проекте (должна быть Member или Admin)
2. Попросите администратора добавить вас в проект

### Ошибка: "Connection timeout"

**Причина:** Не можем достичь JIRA

**Решение:**
1. Проверьте интернет-соединение
2. Проверьте URL в `.env`:
   ```bash
   export JIRA_URL="https://bozzyk44.atlassian.net"  # без слэша в конце!
   ```

---

## 📚 Полезные ссылки

- **JIRA REST API Docs:** https://developer.atlassian.com/cloud/jira/platform/rest/v3/intro/
- **Create API Token:** https://id.atlassian.com/manage-profile/security/api-tokens
- **Your JIRA Instance:** https://bozzyk44.atlassian.net
- **Project Settings:** https://bozzyk44.atlassian.net/jira/software/c/projects/OPTICS/settings

---

## 🔒 Security

### Что НЕ делать:

- ❌ НЕ коммитить `.env` файл в Git
- ❌ НЕ делиться API токеном
- ❌ НЕ хранить токен в открытом виде

### Что делать:

- ✅ Используйте `.env` (уже в `.gitignore`)
- ✅ Revoke токен если утёк: https://id.atlassian.com/manage-profile/security/api-tokens
- ✅ Регулярно ротируйте токены (каждые 90 дней)

---

**Статус:** ✅ Ready to use
**Следующий шаг:** Запустите `python scripts/jira_create_test_issue.py`

