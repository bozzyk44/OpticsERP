# OAuth Setup для Atlassian MCP

**Author:** AI Agent
**Created:** 2025-10-08
**Purpose:** Пошаговая инструкция по OAuth аутентификации Atlassian MCP для доступа к JIRA

---

## Статус

```
MCP Server:  atlassian
Type:        SSE (Server-Sent Events)
URL:         https://mcp.atlassian.com/v1/sse
Status:      ⚠ Needs authentication
Scope:       Local (проект OpticsERP)
```

---

## Метод 1: Автоматическая OAuth (Рекомендуется)

### Шаги

1. **Откройте новый терминал Claude Code в проекте OpticsERP:**
   ```bash
   cd D:\OpticsERP
   claude
   ```

2. **Попросите Claude использовать любой Atlassian MCP инструмент:**
   ```
   Покажи список моих JIRA проектов
   ```

   ИЛИ

   ```
   Создай тестовую задачу в JIRA
   ```

3. **Claude Code автоматически запустит OAuth flow:**
   - Откроется браузер с URL: `https://auth.atlassian.com/authorize?...`
   - Вы увидите страницу авторизации Atlassian

4. **Войдите в ваш Atlassian аккаунт:**
   - Email: [ваш email]
   - Password: [ваш пароль]
   - (опционально) 2FA код

5. **Разрешите доступ для Claude Code MCP:**
   - Нажмите "Accept" / "Allow"
   - Список разрешений (permissions):
     - ✓ Read and write Jira issues
     - ✓ Read Jira projects
     - ✓ Read Jira users
     - ✓ Read Confluence pages (опционально)

6. **Вернитесь в терминал Claude Code:**
   - Увидите сообщение: "✓ Authentication successful"
   - OAuth токен сохранён в `~/.claude/.credentials.json`

7. **Проверьте статус MCP сервера:**
   ```bash
   claude mcp list
   ```

   **Ожидаемый результат:**
   ```
   atlassian: https://mcp.atlassian.com/v1/sse (SSE) - ✓ Ready
   ```

---

## Метод 2: Ручная OAuth через браузер

### Если автоматический flow не сработал

1. **Получите OAuth URL вручную:**
   ```bash
   # В терминале Git Bash (Windows)
   echo "https://auth.atlassian.com/authorize?audience=api.atlassian.com&client_id=YOUR_CLIENT_ID&scope=read:jira-work%20write:jira-work&redirect_uri=http://localhost:45454/oauth/callback&response_type=code&prompt=consent"
   ```

2. **Откройте URL в браузере вручную**

3. **После авторизации скопируйте код из redirect URL:**
   ```
   http://localhost:45454/oauth/callback?code=AUTHORIZATION_CODE
   ```

4. **Обменяйте код на токен (Claude Code делает автоматически)**

---

## Метод 3: API Token (Альтернатива OAuth)

### Если OAuth не работает, используйте API Token

1. **Создайте API Token в Atlassian:**
   - Перейдите: https://id.atlassian.com/manage-profile/security/api-tokens
   - Нажмите "Create API token"
   - Label: `Claude Code MCP`
   - Скопируйте токен (показывается один раз!)

2. **Сохраните токен в переменную окружения:**
   ```bash
   # Windows (PowerShell)
   $env:ATLASSIAN_API_TOKEN = "YOUR_API_TOKEN_HERE"

   # Windows (Git Bash)
   export ATLASSIAN_API_TOKEN="YOUR_API_TOKEN_HERE"

   # Постоянно (добавьте в ~/.bashrc или ~/.bash_profile)
   echo 'export ATLASSIAN_API_TOKEN="YOUR_API_TOKEN_HERE"' >> ~/.bashrc
   ```

3. **Сохраните email в переменную окружения:**
   ```bash
   # Windows (PowerShell)
   $env:ATLASSIAN_EMAIL = "bozzyk44@gmail.com"

   # Windows (Git Bash)
   export ATLASSIAN_EMAIL="bozzyk44@gmail.com"
   ```

4. **Перезапустите Claude Code:**
   ```bash
   exit  # в Claude Code
   claude  # перезапустить
   ```

5. **Проверьте подключение:**
   ```bash
   claude mcp list
   ```

---

## Проверка успешной аутентификации

### После успешной OAuth / API Token настройки

**Команда 1: Проверка статуса MCP сервера**
```bash
claude mcp list
```

**Ожидаемый вывод:**
```
Checking MCP server health...

atlassian: https://mcp.atlassian.com/v1/sse (SSE) - ✓ Ready
```

**Команда 2: Проверка доступа к JIRA через Claude**

В интерактивной сессии Claude Code:
```
Покажи список моих JIRA проектов
```

**Ожидаемый результат:**
- Claude вызовет MCP инструмент `atlassian__list_projects`
- Вернёт список проектов из вашей JIRA инстанции

---

## Доступные MCP инструменты после аутентификации

После успешной OAuth у Claude появятся инструменты:

| Инструмент | Описание |
|------------|----------|
| `atlassian__list_projects` | Список JIRA проектов |
| `atlassian__search_issues` | Поиск задач (JQL) |
| `atlassian__get_issue` | Получить детали задачи |
| `atlassian__create_issue` | Создать задачу/эпик |
| `atlassian__update_issue` | Обновить задачу |
| `atlassian__add_comment` | Добавить комментарий |
| `atlassian__transition_issue` | Изменить статус (To Do → In Progress) |
| `atlassian__list_boards` | Список Scrum/Kanban досок |

---

## Использование после аутентификации

### Пример 1: Создание эпика

```bash
cd D:\OpticsERP
claude
```

В Claude Code:
```
Создай эпик в JIRA:
- Summary: Phase 1: POC
- Description: Proof of concept offline-first режима
- Project: OPTICS
- Story Points: 89
```

### Пример 2: Массовый импорт из CSV

```
Импортируй все задачи из docs/jira/jira_import.csv в JIRA проект OPTICS
```

Claude автоматически:
1. Прочитает CSV файл
2. Создаст 7 эпиков
3. Создаст 77 стори
4. Привяжет стори к эпикам
5. Установит приоритеты, лейблы, Story Points

---

## Troubleshooting

### Проблема 1: "⚠ Needs authentication" не исчезает

**Решение:**
```bash
# Удалите кэш OAuth
rm ~/.claude/.credentials.json

# Перезапустите Claude Code
claude
```

### Проблема 2: "OAuth redirect timeout"

**Причина:** Порт 45454 занят другим приложением

**Решение:**
```bash
# Проверьте, что порт свободен
netstat -ano | findstr :45454

# Если занят, убейте процесс:
taskkill /PID <PID> /F

# Перезапустите Claude Code
```

### Проблема 3: "Invalid OAuth token"

**Решение:**
```bash
# Проверьте ~/.claude/.credentials.json
cat ~/.claude/.credentials.json

# Если токен истёк (expired), удалите файл:
rm ~/.claude/.credentials.json

# Повторите OAuth flow
```

### Проблема 4: Browser не открывается автоматически

**Решение:**
1. Скопируйте OAuth URL из терминала вручную
2. Откройте в браузере
3. Завершите авторизацию
4. Скопируйте redirect URL с `code=...` параметром
5. Вставьте обратно в терминал Claude Code (если запрашивается)

---

## Security Notes

### Хранение токенов

- **OAuth токены:** `~/.claude/.credentials.json` (зашифрованы, 60 дней TTL)
- **API Tokens:** Переменные окружения (не коммитить в Git!)

### Permissions (разрешения)

OAuth токен имеет следующие права:
- ✓ `read:jira-work` — чтение задач, проектов
- ✓ `write:jira-work` — создание/обновление задач
- ✗ `admin:jira-work` — НЕТ админских прав
- ✗ `delete:jira-work` — НЕТ прав на удаление

### Revoke (отзыв) токена

Если нужно отозвать доступ:
1. https://id.atlassian.com/manage-profile/security
2. API Tokens → Revoke
3. Удалите `~/.claude/.credentials.json`

---

## Next Steps

После успешной аутентификации:

1. **Импорт задач в JIRA:**
   ```
   Импортируй docs/jira/jira_import.csv в JIRA проект OPTICS
   ```

2. **Настройка Board:**
   - Создать Scrum Board
   - Добавить Epic swimlanes
   - Фильтр по labels: `poc`, `mvp`, `buffer`, `pilot`

3. **Roadmap View:**
   - Включить Roadmap
   - Group by: Epic
   - Color by: Priority

4. **Автоматизация:**
   - Auto-assign по labels
   - Notifications в Telegram/Email
   - Sprint auto-creation (Week 1, Week 2, etc.)

---

**Статус:** ⏳ Требуется OAuth аутентификация
**Следующий шаг:** Выполните Метод 1 (Автоматическая OAuth)
**Ожидаемое время:** 2-3 минуты

