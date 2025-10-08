# Glossary — OpticsERP Domain Terms

> **Purpose:** Domain terminology for AI agents and developers
> **Version:** 1.0 • Date: 2025-10-08
> **Audience:** AI agents, new developers, external contractors

---

## 🤖 For AI Agents

When you encounter these terms in documentation or code, use these definitions. This glossary helps you understand the domain context without asking for clarifications.

---

## Fiscal Compliance Terms (54-ФЗ)

### ККТ (KKT)
**Russian:** Контрольно-кассовая техника
**English:** Cash Register / Fiscal Printer
**Definition:** Physical device that prints fiscal receipts and stores fiscal data in the Fiscal Storage (ФН). Required by Russian law 54-ФЗ for all retail transactions.

**Technical details:**
- Connected to POS terminal via USB/Ethernet
- Timeout for print operation: 10 seconds
- Must be certified by Federal Tax Service (ФНС)

**Example:**
```python
kkt_driver.print_receipt(receipt_data)
# Prints receipt on physical ККТ device
```

---

### ОФД (OFD)
**Russian:** Оператор Фискальных Данных
**English:** Fiscal Data Operator
**Definition:** Cloud service that receives and stores all fiscal receipts for tax authorities. Required by 54-ФЗ.

**Technical details:**
- API endpoint: typically HTTPS REST
- Timeout for sync: 10 seconds
- Receipts must be sent within 30 days (law requirement)
- OpticsERP sends in real-time (with offline buffer fallback)

**API example:**
```python
response = await ofd_client.post("/receipts", json=fiscal_doc)
# Send fiscal document to ОФД
```

**Critical:** OpticsERP operates **offline-first**, so ОФД unavailability does NOT block sales.

---

### ФН (FN)
**Russian:** Фискальный Накопитель
**English:** Fiscal Storage / Fiscal Drive
**Definition:** Hardware chip inside ККТ that stores all receipts locally. Has limited capacity (~1,000,000 receipts or 13-36 months).

**Lifecycle:**
1. New ФН installed in ККТ
2. Accumulates receipts over months
3. Capacity warning at ~95% (алерт P2)
4. Must be replaced before 100% (blocks sales)
5. Old ФН submitted to tax authority

**Capacity check:**
```python
fn_capacity = kkt_driver.get_fn_capacity()
if fn_capacity > 95:
    send_alert("ФН близок к заполнению", level='P2')
```

**Important:** When replacing ФН, offline buffer must be synced first (Runbook A.3).

---

### ФФД (FFD)
**Russian:** Формат Фискальных Данных
**English:** Fiscal Data Format
**Definition:** JSON schema for fiscal receipts. Current version: **FFD 1.2** (mandatory since 2021).

**Key fields:**
- `fiscalDocumentNumber` — sequential number from ФН
- `fiscalSign` — cryptographic signature
- `items[]` — receipt line items
- `payments[]` — payment methods
- `taxationType` — tax system code

**Example FFD 1.2 document:**
```json
{
  "fiscalDocumentNumber": 12345,
  "fiscalSign": "3849583049",
  "dateTime": "2025-10-08T14:30:00",
  "items": [
    {
      "name": "Оправа RayBan",
      "price": 5000.00,
      "quantity": 1,
      "sum": 5000.00,
      "tax": "vat20"
    }
  ],
  "payments": [
    {"type": "card", "sum": 5000.00}
  ],
  "taxationType": "osn"
}
```

---

### 54-ФЗ
**Full name:** Федеральный закон № 54-ФЗ «О применении контрольно-кассовой техники»
**English:** Federal Law 54 "On the Use of Cash Register Equipment"
**Definition:** Russian federal law regulating fiscal operations for retail.

**Key requirements for OpticsERP:**
- All cash/card transactions must be fiscalized
- Receipts printed on certified ККТ
- Fiscal data sent to ОФД within 30 days
- Electronic receipts (email/SMS) mandatory if customer provides contact
- X/Z reports with specific FFD tags

**Penalties for non-compliance:** Up to 30,000₽ per violation.

---

## Offline-First Architecture Terms

### Офлайн-буфер (Offline Buffer)
**Definition:** SQLite database on POS terminal storing receipts when ОФД is unreachable.

**Technical details:**
- Location: `kkt_adapter/data/buffer.db`
- Schema: 3 tables (receipts, dlq, buffer_events)
- Capacity: 200 receipts (configurable)
- Durability: WAL mode + synchronous=FULL (survives power loss)

**States:**
- **pending** — not yet sent to ОФД
- **syncing** — currently being sent
- **synced** — successfully sent
- **failed** — moved to DLQ after 20 retries

**Capacity monitoring:**
```prometheus
kkt_buffer_percent_full{pos_id="POS-001"} > 80  # Alert threshold
```

---

### Circuit Breaker
**Definition:** Software pattern protecting from cascading failures. Stops calling failing service (ОФД) until it recovers.

**States:**
- **CLOSED** — normal operation, calls go through
- **OPEN** — service failing, calls blocked (buffered locally)
- **HALF_OPEN** — testing if service recovered

**Parameters (from config.toml):**
- `failure_threshold: 5` — 5 errors → OPEN
- `recovery_timeout: 60` — wait 60s in OPEN → try HALF_OPEN
- `success_threshold: 2` — 2 successes in HALF_OPEN → CLOSED

**Metric:**
```prometheus
kkt_circuit_breaker_state{pos_id="POS-001"}
# 0 = CLOSED, 1 = OPEN, 2 = HALF_OPEN
```

**Why it matters:** Prevents OpticsERP from hammering unavailable ОФД, enables graceful offline mode.

---

### Hybrid Logical Clock (HLC)
**Definition:** Timestamp mechanism that doesn't depend on NTP synchronization. Combines local time + logical counter + server time.

**Structure:**
```python
@dataclass
class HybridTimestamp:
    local_time: int        # Unix timestamp from POS clock
    logical_counter: int   # Monotonic counter (increments if same second)
    server_time: int       # Assigned by Odoo during sync (nullable)
```

**Ordering (for conflict resolution):**
1. Compare `server_time` (if both have it)
2. Else compare `local_time`
3. Else compare `logical_counter`

**Why it matters:** Even if POS clock drifts, HLC ensures correct receipt ordering during sync.

---

### Двухфазная фискализация (Two-Phase Fiscalization)
**Definition:** Split fiscal operation into 2 phases to ensure business continuity.

**Phase 1 (Local):**
1. Save receipt to SQLite buffer (status=pending)
2. Print receipt on ККТ
3. Return success to cashier

**Always succeeds** (even if ОФД down).

**Phase 2 (Async):**
1. Check Circuit Breaker state
2. Send to ОФД API
3. Update status=synced (or retry if failed)

**Best-effort** (retries up to 20 times, then DLQ).

**Critical distinction:**
- **Бизнес-доступность (Business Availability):** Can cashier complete sale? → YES (Phase 1)
- **Системная доступность (System Availability):** Is ОФД reachable? → Doesn't matter for sales

---

### DLQ (Dead Letter Queue)
**Definition:** Storage for receipts that failed sync after max retries.

**When receipts go to DLQ:**
- 20 retry attempts exhausted
- ОФД returned 4xx error (client error, not retryable)
- Fiscal document validation failed

**Resolution:**
- Manual review by administrator
- Fix fiscal doc (if malformed)
- Re-send to ОФД
- Mark as resolved

**Table schema:**
```sql
CREATE TABLE dlq (
  id TEXT PRIMARY KEY,
  original_receipt_id TEXT,
  reason TEXT,
  fiscal_doc TEXT,
  retry_attempts INTEGER,
  resolved_at INTEGER  -- NULL if unresolved
);
```

---

### Saga Pattern
**Definition:** Distributed transaction pattern for compensating actions.

**Used in OpticsERP for:** Refunds (возвраты).

**Scenario:** Customer returns item, but original receipt not yet synced to ОФД.

**Saga steps:**
1. Check if original receipt synced (query buffer)
2. If not synced → **block refund** (HTTP 409)
3. If synced → create refund receipt
4. Link refund to original (reference original `fiscalDocumentNumber`)

**Why it matters:** Prevents inconsistent fiscal data in ОФД.

---

### Distributed Lock
**Definition:** Mechanism to prevent concurrent sync workers from running simultaneously.

**Implementation:** Redis lock with TTL.

**Usage:**
```python
lock = Lock(redis_client, 'sync_lock', timeout=300)  # 5 min TTL

if not lock.acquire(blocking=False):
    return HTTP 409  # Another sync in progress

try:
    # Sync receipts
finally:
    lock.release()
```

**Why it matters:** Prevents duplicate ОФД submissions if multiple sync triggers fire.

---

## Business Domain Terms

### Рецепт (Prescription)
**Definition:** Optical prescription from optometrist specifying lens parameters.

**Key fields:**
- **Sph (Sphere):** Дальнозоркость/близорукость (-20 to +20)
- **Cyl (Cylinder):** Астигматизм (-4 to 0)
- **Axis:** Ось астигматизма (1-180°)
- **Add:** Аддидация для прогрессивных линз (0.75-3.0)
- **PD (Pupillary Distance):** Межзрачковое расстояние (56-72 mm)

**Validation rules:**
- Sph step: 0.25
- Cyl ≤ 0 (always negative or zero)
- Axis required if Cyl ≠ 0

---

### Линза (Lens)
**Types:**
- **Одиночные (Single Vision):** Одна оптическая сила
- **Бифокальные (Bifocal):** Две зоны (даль + близь)
- **Прогрессивные (Progressive):** Плавный переход

**Index (Индекс преломления):**
- 1.5 (standard)
- 1.6 (thin)
- 1.67 (ultra-thin)
- 1.74 (super-thin)

**Coatings (Покрытия):**
- AR (Anti-Reflective) — антибликовое
- HC (Hard Coating) — упрочняющее
- UV — УФ-защита
- Photochromic — фотохромное (затемнение)

---

### Заказ на изготовление (Manufacturing Order)
**Definition:** Work order for lens manufacturing based on prescription.

**Workflow:**
```
Draft → Confirmed → In Production → Ready → Delivered
```

**Timeline:** 3-14 days (зависит от типа линзы).

---

## System Architecture Terms

### Бизнес-доступность (Business Availability)
**Definition:** Can the business operate? (Accept payments, print receipts)

**Target:** ≥99.5% uptime

**Measured by:** Ability to complete sale + print receipt (independent of ОФД).

**Critical:** OpticsERP guarantees business availability even if ОФД/Odoo offline.

---

### Системная доступность (System Availability)
**Definition:** Are backend services (Odoo, ОФД, Redis) reachable?

**NOT a blocker for sales:** Offline buffer ensures business continuity.

---

### POC (Proof of Concept)
**OpticsERP POC tests:**
- **POC-1:** ККТ emulator + 50 operations
- **POC-2:** Import 10k catalog in <2 min
- **POC-4:** 8h offline + 50 receipts → sync <10 min
- **POC-5:** Split-brain, flapping, concurrent sync

**Purpose:** Validate architecture before MVP.

---

### UAT (User Acceptance Testing)
**Definition:** Tests performed by end users to validate functionality.

**OpticsERP offline UATs:**
- **UAT-08:** Sale in offline mode
- **UAT-09:** Refund blocked if original not synced
- **UAT-10b:** Buffer overflow (200 receipts)
- **UAT-10c:** Recovery after power loss
- **UAT-11:** X/Z reports in offline

---

## Metrics & Monitoring

### P95 (95th Percentile)
**Definition:** 95% of requests complete within this time.

**OpticsERP target:** P95 печати чека ≤ 7 секунд.

**Why P95 not P99:** More realistic for business SLA (P99 can have outliers).

---

### RTO (Recovery Time Objective)
**Definition:** Maximum acceptable downtime.

**OpticsERP:** RTO ≤ 1 час для продуктивного окружения.

---

### RPO (Recovery Point Objective)
**Definition:** Maximum acceptable data loss.

**OpticsERP:** RPO ≤ 24 часа (ежедневные бэкапы PostgreSQL + SQLite).

---

## Abbreviations

| Term | Full Name | Russian |
|------|-----------|---------|
| ККТ | Контрольно-кассовая техника | Cash Register |
| ОФД | Оператор Фискальных Данных | Fiscal Data Operator |
| ФН | Фискальный Накопитель | Fiscal Storage |
| ФФД | Формат Фискальных Данных | Fiscal Data Format |
| НДС | Налог на добавленную стоимость | VAT |
| ФНС | Федеральная Налоговая Служба | Federal Tax Service |
| GP | Gross Profit | Валовая прибыль |
| PD | Pupillary Distance | Межзрачковое расстояние |
| Sph | Sphere | Сфера (дальнозоркость/близорукость) |
| Cyl | Cylinder | Цилиндр (астигматизм) |
| Add | Addition | Аддидация (прогрессивные линзы) |
| HLC | Hybrid Logical Clock | Гибридные логические часы |
| DLQ | Dead Letter Queue | Очередь неотправленных |
| WAL | Write-Ahead Logging | Журналирование с опережающей записью |
| CB | Circuit Breaker | Предохранитель |

---

## Usage Examples for AI Agents

### Example 1: Understanding error message
```
ERROR: ФН заполнен на 97%
```

**AI interpretation:**
- ФН = Fiscal Storage (hardware chip in ККТ)
- 97% capacity → warning threshold
- Action: Alert P2, plan ФН replacement (Runbook A.3)

---

### Example 2: Understanding metric
```
kkt_buffer_percent_full{pos_id="POS-001"} = 85
```

**AI interpretation:**
- Offline buffer is 85% full (200 receipts capacity)
- Threshold: 80% warning, 100% critical
- Likely cause: ОФД unreachable or Circuit Breaker OPEN
- Action: Check ОФД connectivity (Runbook B.1)

---

### Example 3: Understanding requirement
```
"UAT-09: Возврат несинхронизированного чека должен быть заблокирован"
```

**AI interpretation:**
- Refund (возврат) for receipt not yet synced to ОФД
- Must return HTTP 409 (Saga Pattern)
- Test: Create receipt → immediately try refund → expect 409

---

## References

- **54-ФЗ:** [consultant.ru/document/cons_doc_LAW_42359](http://www.consultant.ru/document/cons_doc_LAW_42359/)
- **FFD 1.2 Spec:** [nalog.gov.ru](https://www.nalog.gov.ru/rn77/taxation/taxes/kkt/)
- **Circuit Breaker Pattern:** [martinfowler.com/bliki/CircuitBreaker.html](https://martinfowler.com/bliki/CircuitBreaker.html)
- **Saga Pattern:** [microservices.io/patterns/data/saga.html](https://microservices.io/patterns/data/saga.html)

---

**Last updated:** 2025-10-08
**Maintained by:** OpticsERP Team
**For AI agents:** Reference this glossary when encountering unfamiliar terms. If term not found, search in docs/1-5 or ask human.
