# Task Plan: Generate JIRA Structure from PROJECT_PHASES.md

**Date:** 2025-10-08
**Author:** AI Agent
**Task:** Create JIRA Epics and Tasks based on project phases

---

## Описание задачи

Создать структуру JIRA-задач (Epics + Tasks) на основе детального плана в PROJECT_PHASES.md:
- 6 фаз = 6 Epics
- ~90 задач = ~90 Tasks
- Каждая задача привязана к своему Epic

## Шаги выполнения

### 1. Прочитать PROJECT_PHASES.md
- Извлечь все фазы (Phase 0-6)
- Извлечь все задачи с деталями

### 2. Создать CSV-файл для импорта в JIRA
Формат CSV:
```csv
Issue Type,Summary,Description,Epic Link,Priority,Story Points,Acceptance Criteria,Labels
Epic,Phase 1: POC,...,,,21,,...
Task,Week 1.1: Implement HLC,...,Phase 1: POC,High,3,...,week1,hlc
```

### 3. Создать альтернативный JSON-файл для JIRA REST API
Формат JSON для автоматизации через API

### 4. Создать Markdown-файл с визуализацией структуры
Для ручного reference

## Список файлов для создания

1. `docs/jira/jira_import.csv` — CSV для импорта
2. `docs/jira/jira_structure.json` — JSON для REST API
3. `docs/jira/jira_roadmap.md` — Markdown roadmap
4. `docs/jira/README.md` — Инструкции по импорту

## Acceptance Criteria

- ✅ CSV содержит все 6 Epics
- ✅ CSV содержит все ~90 Tasks
- ✅ Каждый Task привязан к Epic через Epic Link
- ✅ Priority установлен согласно PROJECT_PHASES.md
- ✅ Story Points распределены (Fibonacci: 1,2,3,5,8,13)
- ✅ Acceptance Criteria из PROJECT_PHASES.md перенесены
- ✅ Labels добавлены для фильтрации (week1, hlc, buffer, etc.)

## Команды для тестирования

```bash
# Проверка CSV валидности
python -c "import csv; list(csv.DictReader(open('docs/jira/jira_import.csv')))"

# Проверка JSON валидности
python -c "import json; json.load(open('docs/jira/jira_structure.json'))"

# Подсчёт задач
grep -c "^Task," docs/jira/jira_import.csv
# Expected: ~90

# Подсчёт Epics
grep -c "^Epic," docs/jira/jira_import.csv
# Expected: 6
```

## Приоритеты JIRA

- **Highest:** Блокирующие задачи (например, Bootstrap)
- **High:** Week 1-5 (POC), критичные компоненты
- **Medium:** Week 6-10 (MVP, Stabilization)
- **Low:** Week 11+ (Pilot, Production)

## Story Points (Fibonacci)

- **1 point:** Документация, конфигурация (<2ч)
- **2 points:** Простые функции, unit-тесты (2-4ч)
- **3 points:** Средние функции (4-8ч, 1 день)
- **5 points:** Сложные функции (8-16ч, 2 дня)
- **8 points:** Очень сложные (16-24ч, 3 дня)
- **13 points:** Интеграционные/UAT (3-5 дней)

---

## Примечания

- CSV формат совместим с JIRA Cloud/Server
- JSON можно использовать с JIRA REST API v3
- Для импорта CSV: JIRA → Settings → System → Import → CSV
- Для API нужен токен: https://id.atlassian.com/manage-profile/security/api-tokens
