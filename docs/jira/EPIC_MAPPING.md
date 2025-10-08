# Epic → Stories Mapping

**Author:** AI Agent
**Created:** 2025-10-08
**Purpose:** Маппинг для ручного связывания Stories с Epics в JIRA

---

## 📋 Как использовать этот файл

### Метод 1: Ручное связывание через UI

1. **Откройте Epic в JIRA**
2. **Нажмите кнопку "Add child issue"** (или "+ Add issue to epic")
3. **Выберите Stories из списка ниже**
4. **Повторите для каждого Epic**

### Метод 2: JQL фильтр + массовое редактирование

1. **Скопируйте JQL запрос для Epic** (из секции ниже)
2. **Откройте:** https://bozzyk44.atlassian.net/issues/?jql=YOUR_JQL
3. **Select all issues** → **Bulk change** → **Edit issues** → **Set Epic Link**

---

## 🗂️ Epic Mapping

### OPTERP-79: Phase 0 - Bootstrap Infrastructure

**Epic Link:** `OPTERP-79`
**Stories:** 0 (Bootstrap выполнен вручную)

**JQL:**
```jql
project = OPTERP AND labels = bootstrap AND type = Story
```

---

### OPTERP-80: Phase 1 - POC (Proof of Concept)

**Epic Link:** `OPTERP-80`
**Stories:** 30 задач (OPTERP-2 до OPTERP-31)

| Story Key | Summary |
|-----------|---------|
| OPTERP-2  | Implement Hybrid Logical Clock (HLC) |
| OPTERP-3  | Create HLC Unit Tests |
| OPTERP-4  | Implement SQLite Buffer CRUD |
| OPTERP-5  | Create Buffer DB Unit Tests |
| OPTERP-6  | Create FastAPI Main Application |
| OPTERP-7  | Create Pydantic Models |
| OPTERP-8  | Implement Health Endpoint |
| OPTERP-9  | Implement Buffer Status Endpoint |
| OPTERP-10 | Implement Receipt Endpoint (Phase 1) |
| OPTERP-11 | Create Receipt Endpoint Integration Tests |
| OPTERP-12 | Implement Circuit Breaker for OFD |
| OPTERP-13 | Create Mock OFD Server |
| OPTERP-14 | Create Circuit Breaker Unit Tests |
| OPTERP-15 | Update FastAPI for Phase 2 Fiscalization |
| OPTERP-16 | Create Fiscal Module |
| OPTERP-17 | Create Mock KKT Driver |
| OPTERP-18 | Complete Receipt Endpoint Implementation |
| OPTERP-19 | Create Two-Phase Integration Tests |
| OPTERP-20 | Setup Redis in Docker Compose |
| OPTERP-21 | Implement Sync Worker |
| OPTERP-22 | Integrate APScheduler for Sync |
| OPTERP-23 | Create Sync Worker Unit Tests |
| OPTERP-24 | Implement Heartbeat Module |
| OPTERP-25 | Integrate APScheduler for Heartbeat |
| OPTERP-26 | Create Mock Odoo Server |
| OPTERP-27 | Create Heartbeat Unit Tests |
| OPTERP-28 | Create POC-1 Test (KKT Emulator) |
| OPTERP-29 | Create POC-4 Test (8h Offline) |
| OPTERP-30 | Create POC-5 Test (Split-Brain) |
| OPTERP-31 | Create POC Report and Sign-Off |

**JQL для массового редактирования:**
```jql
project = OPTERP AND key >= OPTERP-2 AND key <= OPTERP-31 AND type = Story
```

**Быстрая команда (скопировать в JIRA Bulk Edit):**
- Select issues: OPTERP-2, OPTERP-3, OPTERP-4, ..., OPTERP-31
- Epic Link: OPTERP-80

---

### OPTERP-81: Phase 2 - MVP (Minimum Viable Product)

**Epic Link:** `OPTERP-81`
**Stories:** 32 задачи (OPTERP-32 до OPTERP-62, исключая 59-62)

| Story Key | Summary |
|-----------|---------|
| OPTERP-32 | Create Prescription Model |
| OPTERP-33 | Create Prescription Unit Tests |
| OPTERP-34 | Create Lens Model |
| OPTERP-35 | Create Lens Unit Tests |
| OPTERP-36 | Create Manufacturing Order Model |
| OPTERP-37 | Create Manufacturing Order Unit Tests |
| OPTERP-38 | Create Prescription Views |
| OPTERP-39 | Create Lens Views |
| OPTERP-40 | Create Manufacturing Order Views |
| OPTERP-41 | Create Import Profile Model |
| OPTERP-42 | Create Import Job Model |
| OPTERP-43 | Create Import Wizard |
| OPTERP-44 | Create Connector Import Unit Tests |
| OPTERP-45 | Create Offline Indicator Widget |
| OPTERP-46 | Create POS Config Views for KKT Adapter |
| OPTERP-47 | Implement Saga Pattern (Refund Blocking) |
| OPTERP-48 | Implement Bulkhead Pattern (Celery Queues) |
| OPTERP-49 | Create Saga Pattern Integration Tests |
| OPTERP-50 | Create UAT-01 Sale Test |
| OPTERP-51 | Create UAT-02 Refund Test |
| OPTERP-52 | Create UAT-03 Import Test |
| OPTERP-53 | Create UAT-04 Reports Test |
| OPTERP-54 | Create UAT-08 Offline Sale Test |
| OPTERP-55 | Create UAT-09 Refund Blocked Test |
| OPTERP-56 | Create UAT-10b Buffer Overflow Test |
| OPTERP-57 | Create UAT-10c Power Loss Test |
| OPTERP-58 | Create UAT-11 Offline Reports Test |
| OPTERP-59 | Fix Critical Bugs from UAT |
| OPTERP-60 | Re-run Full UAT Suite |
| OPTERP-61 | Verify MVP DoD Criteria |
| OPTERP-62 | Create MVP Sign-Off Document |

**JQL:**
```jql
project = OPTERP AND key >= OPTERP-32 AND key <= OPTERP-62 AND type = Story
```

---

### OPTERP-82: Phase 3 - Stabilization (Buffer Week)

**Epic Link:** `OPTERP-82`
**Stories:** 6 задач (OPTERP-63 до OPTERP-68)

| Story Key | Summary |
|-----------|---------|
| OPTERP-63 | Create Load Test Suite (Locust) |
| OPTERP-64 | Execute Load Tests and Analyze Results |
| OPTERP-65 | Fix Performance Issues from Load Tests |
| OPTERP-66 | Update Core Documentation (docs 1-5) |
| OPTERP-67 | Create Rollback Procedure Documentation |
| OPTERP-68 | Automate DoD Checks (CI/CD Gate) |

**JQL:**
```jql
project = OPTERP AND key >= OPTERP-63 AND key <= OPTERP-68 AND type = Story
```

---

### OPTERP-83: Phase 4 - Pilot Deployment

**Epic Link:** `OPTERP-83`
**Stories:** 9 задач (OPTERP-69 до OPTERP-77)

| Story Key | Summary |
|-----------|---------|
| OPTERP-69 | Install KKT Adapters on 4 POS Terminals |
| OPTERP-70 | Configure UPS and Graceful Shutdown |
| OPTERP-71 | Train Cashiers (≥90% Pass Rate) |
| OPTERP-72 | Create X/Z Reports and Offline Buffer Procedures |
| OPTERP-73 | Setup Grafana Dashboard (4 Panels) |
| OPTERP-74 | Configure Prometheus Alerts (P1/P2/P3) |
| OPTERP-75 | Integrate Alert Channels (Email/Telegram) |
| OPTERP-76 | Execute Stress Test (2 POS × 8h × 50 Receipts) |
| OPTERP-77 | Create Decision Tree for L1/L2 Support |

**JQL:**
```jql
project = OPTERP AND key >= OPTERP-69 AND key <= OPTERP-77 AND type = Story
```

---

### OPTERP-84: Phase 5 - Soft Launch

**Epic Link:** `OPTERP-84`
**Stories:** 7 задач (OPTERP-86 до OPTERP-92)

| Story Key | Summary | SP |
|-----------|---------|-----|
| OPTERP-86 | Deploy to 5 Additional Stores (Total 10 POS) | 5 |
| OPTERP-87 | Execute Simplified Load Test (5 POS, 1000 Receipts/Day) | 3 |
| OPTERP-88 | Collect Capacity Metrics (PostgreSQL, Celery, Odoo) | 3 |
| OPTERP-89 | Identify and Document Performance Bottlenecks | 3 |
| OPTERP-90 | Create Store Addition Procedure and Test | 2 |
| OPTERP-91 | Optimize Performance Issues from Capacity Metrics | 5 |
| OPTERP-92 | Create Soft Launch Sign-Off Document | 2 |

**JQL:**
```jql
project = OPTERP AND key >= OPTERP-86 AND key <= OPTERP-92 AND type = Story
```

---

### OPTERP-85: Phase 6 - Production Rollout

**Epic Link:** `OPTERP-85`
**Stories:** 11 задач (OPTERP-78, OPTERP-93 до OPTERP-102)

| Story Key | Summary | SP |
|-----------|---------|-----|
| OPTERP-78 | Document FN Replacement Procedure | 0 |
| OPTERP-93 | Deploy to Remaining 15 Stores (Total 40 POS) | 8 |
| OPTERP-94 | Configure pgbouncer (If Needed) | 3 |
| OPTERP-95 | Setup Daily Backups for Offline Buffers | 3 |
| OPTERP-96 | Execute DR Test (RTO≤1h, RPO≤24h) | 5 |
| OPTERP-97 | Create Administrator Guide (≥50 Pages) | 8 |
| OPTERP-98 | Create Runbook with ≥20 Scenarios | 8 |
| OPTERP-99 | Define SLA and Incident Response Procedures | 5 |
| OPTERP-100 | Setup On-Call Procedures and Contacts | 2 |
| OPTERP-101 | Create Support Maintenance Procedures | 3 |
| OPTERP-102 | Verify Production DoD and Sign-Off | 2 |

**JQL:**
```jql
project = OPTERP AND (key = OPTERP-78 OR (key >= OPTERP-93 AND key <= OPTERP-102)) AND type = Story
```

---

## 📊 Статистика

| Epic | Stories | Story Points |
|------|---------|--------------|
| OPTERP-79 (Phase 0) | 0 | 0 |
| OPTERP-80 (Phase 1) | 30 | 89 |
| OPTERP-81 (Phase 2) | 31 | 118 |
| OPTERP-82 (Phase 3) | 6 | 21 |
| OPTERP-83 (Phase 4) | 9 | 41 |
| OPTERP-84 (Phase 5) | 7 | 23 |
| OPTERP-85 (Phase 6) | 11 | 47 |
| **Всего** | **94** | **339** |

---

## 🚀 Быстрый метод (Bulk Edit)

### Шаги:

1. **Откройте JIRA Issues:**
   ```
   https://bozzyk44.atlassian.net/jira/software/c/projects/OPTERP/issues
   ```

2. **Примените фильтр для Epic 1 (POC):**
   ```jql
   project = OPTERP AND key >= OPTERP-2 AND key <= OPTERP-31
   ```

3. **Select All (30 issues)** → **⋯ (More)** → **Bulk change**

4. **Edit Issues** → **Change Epic Link** → `OPTERP-80`

5. **Confirm** → **Next** → **Confirm**

6. **Повторите для остальных Epics:**
   - Epic 2 (MVP): OPTERP-32 до OPTERP-62
   - Epic 3 (Buffer): OPTERP-63 до OPTERP-68
   - Epic 4 (Pilot): OPTERP-69 до OPTERP-77
   - Epic 5 (Soft Launch): OPTERP-86 до OPTERP-92
   - Epic 6 (Prod): OPTERP-78, OPTERP-93 до OPTERP-102

---

## ✅ Проверка

После связывания проверьте:

```jql
project = OPTERP AND "Epic Link" is EMPTY AND type = Story
```

**Ожидаемый результат:** 0 issues (все Stories привязаны к Epics)

---

## 📌 Альтернатива: Скрипт автоматического связывания

Если хотите автоматизировать, создайте скрипт:

```bash
python scripts/jira_link_epics.py
```

Скрипт использует JIRA REST API для массового связывания Stories с Epics.

---

**Статус:** ✅ Ready for manual linking
**Следующий шаг:** Выполните Bulk Edit для каждого Epic (5-10 минут)

