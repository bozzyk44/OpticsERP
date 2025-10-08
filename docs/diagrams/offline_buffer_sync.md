# Offline Buffer Synchronization

> **Purpose:** Visual representation of sync worker process
> **Reference:** CLAUDE.md §4.4, docs/5 §5.4

---

## Sync Worker Architecture

```mermaid
graph TB
    A[APScheduler<br/>Every 60s] --> B{Acquire<br/>Distributed Lock?}

    B -->|Lock acquired| C[Sync Worker]
    B -->|Lock busy| D[Skip<br/>Another sync running]

    C --> E[SELECT pending receipts<br/>LIMIT 50<br/>ORDER BY hlc_local_time]

    E --> F{Any pending?}
    F -->|No| G[Release Lock]
    F -->|Yes| H[For each receipt]

    H --> I{Circuit Breaker<br/>CLOSED?}

    I -->|Yes| J[Send to ОФД]
    I -->|No| K[Skip<br/>Will retry next cycle]

    J --> L{ОФД Success?}

    L -->|Yes| M[UPDATE status=synced<br/>server_time=now]
    L -->|No| N{Retry count<br/><20?}

    N -->|Yes| O[UPDATE retry_count+=1<br/>last_error]
    N -->|No| P[Move to DLQ]

    M --> Q[Next receipt]
    O --> Q
    P --> Q
    K --> Q

    Q --> R{More receipts?}
    R -->|Yes| H
    R -->|No| S[Log event<br/>sync_completed]

    S --> G
    G --> T[End]

    style B fill:#FFE6E6
    style I fill:#E6F3FF
    style L fill:#E6FFE6
    style N fill:#FFF9E6
```

---

## Sync Worker Sequence Diagram

```mermaid
sequenceDiagram
    participant Scheduler as APScheduler
    participant Worker as Sync Worker
    participant Redis as Distributed Lock
    participant SQLite as Buffer DB
    participant CB as Circuit Breaker
    participant OFD as ОФД API
    participant Metrics as Prometheus

    Note over Scheduler: Trigger every 60s

    Scheduler->>Worker: sync_buffer()
    activate Worker

    Worker->>Redis: Acquire lock<br/>(key=sync_lock, ttl=300s)

    alt Lock acquired
        Redis-->>Worker: OK

        Worker->>SQLite: SELECT * FROM receipts<br/>WHERE status='pending'<br/>LIMIT 50<br/>ORDER BY hlc_local_time

        SQLite-->>Worker: [50 receipts]

        Worker->>SQLite: INSERT buffer_event<br/>(type=sync_started)

        Worker->>Metrics: sync_start_time = now

        loop For each receipt
            Worker->>CB: Check state

            alt CB CLOSED
                CB-->>Worker: OK

                Worker->>OFD: POST /receipts<br/>{fiscal_doc}

                alt ОФД Success
                    OFD-->>Worker: 200 OK<br/>{fiscalDocumentNumber}

                    Worker->>SQLite: UPDATE receipts<br/>SET status='synced',<br/>server_time=now<br/>WHERE id=?

                    Worker->>Metrics: receipts_synced_total++

                else ОФД Error
                    OFD-->>Worker: 503 / Timeout

                    Worker->>SQLite: UPDATE receipts<br/>SET retry_count += 1,<br/>last_error=?<br/>WHERE id=?

                    alt Retry count >= 20
                        Worker->>SQLite: INSERT INTO dlq<br/>(original_receipt_id, reason)
                        Worker->>SQLite: INSERT buffer_event<br/>(type=receipt_failed)
                        Worker->>Metrics: dlq_size++
                    end
                end

            else CB OPEN
                CB-->>Worker: ⛔ Blocked
                Note right of Worker: Skip, will retry<br/>next cycle
            end
        end

        Worker->>Metrics: sync_duration_seconds = now - start

        Worker->>SQLite: INSERT buffer_event<br/>(type=sync_completed,<br/>metadata={synced: 45, failed: 5})

        Worker->>Redis: Release lock

    else Lock busy
        Redis-->>Worker: ⛔ Conflict (HTTP 409)
        Note right of Worker: Another sync running<br/>Exit gracefully
    end

    deactivate Worker
```

---

## Distributed Lock (Redis)

### Purpose
Prevent concurrent sync workers from duplicating ОФД submissions.

### Implementation

```python
from redis import Redis
from redis.lock import Lock

redis_client = Redis(host='redis', port=6379, decode_responses=True)

async def sync_buffer():
    """Sync pending receipts with ОФД"""
    lock = Lock(
        redis_client,
        'sync_lock',
        timeout=300,     # 5 min TTL (auto-release if worker crashes)
        blocking=False   # Non-blocking (return immediately if busy)
    )

    if not lock.acquire(blocking=False):
        logger.warning("Sync already running (lock not acquired)")
        return {"status": "skipped", "reason": "concurrent_sync"}

    try:
        # Sync logic
        pending = buffer_db.get_pending_receipts(limit=50)
        synced_count = 0
        failed_count = 0

        for receipt in pending:
            if circuit_breaker.current_state == "OPEN":
                break  # Stop if CB opened during sync

            try:
                await ofd_client.send_receipt(receipt)
                buffer_db.mark_synced(receipt['id'], server_time=time.time())
                synced_count += 1
            except Exception as e:
                buffer_db.increment_retry(receipt['id'], error=str(e))
                failed_count += 1

                if receipt['retry_count'] + 1 >= 20:
                    buffer_db.move_to_dlq(receipt['id'], reason="max_retries")

        return {"status": "completed", "synced": synced_count, "failed": failed_count}

    finally:
        lock.release()
```

---

## APScheduler Configuration

```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler

scheduler = AsyncIOScheduler()

# Sync worker: every 60 seconds
scheduler.add_job(
    sync_buffer,
    'interval',
    seconds=60,
    id='sync_worker',
    replace_existing=True,
    max_instances=1  # Prevent concurrent runs (belt-and-suspenders with Redis lock)
)

# Start scheduler
scheduler.start()
```

---

## Metrics & Monitoring

### Prometheus Metrics

```python
from prometheus_client import Counter, Histogram, Gauge

# Sync duration
sync_duration = Histogram(
    'kkt_sync_duration_seconds',
    'Sync worker duration',
    ['pos_id'],
    buckets=[0.1, 0.5, 1, 2, 5, 10, 30, 60]
)

# Receipts synced
receipts_synced = Counter(
    'kkt_receipts_synced_total',
    'Total receipts synced',
    ['pos_id', 'status']  # status: success|failed
)

# Buffer size
buffer_size = Gauge(
    'kkt_buffer_size',
    'Current pending receipts',
    ['pos_id']
)

# DLQ size
dlq_size = Gauge(
    'kkt_dlq_size',
    'Dead Letter Queue size',
    ['pos_id']
)
```

### Alert Rules

```yaml
groups:
  - name: sync_alerts
    rules:
      - alert: SyncWorkerSlow
        expr: kkt_sync_duration_seconds{quantile="0.95"} > 600
        for: 10m
        labels:
          severity: P2
        annotations:
          summary: "Sync worker медленный на {{ $labels.pos_id }}"
          description: "P95 sync duration > 10 мин"

      - alert: BufferGrowing
        expr: increase(kkt_buffer_size[30m]) > 20
        labels:
          severity: P2
        annotations:
          summary: "Буфер растёт на {{ $labels.pos_id }}"
          description: "Буфер вырос на 20+ чеков за 30 мин, проверить ОФД"

      - alert: DLQNotEmpty
        expr: kkt_dlq_size > 0
        for: 1h
        labels:
          severity: P3
        annotations:
          summary: "DLQ не пуст на {{ $labels.pos_id }}"
          description: "{{ $value }} чеков требуют ручной обработки"
```

---

## Exponential Backoff Strategy

```python
import asyncio
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(20),
    wait=wait_exponential(multiplier=1, min=1, max=60),
    reraise=True
)
async def send_receipt_with_backoff(receipt):
    """
    Retry with exponential backoff:
    - Attempt 1: wait 1s
    - Attempt 2: wait 2s
    - Attempt 3: wait 4s
    - ...
    - Attempt 7+: wait 60s (max)
    - Attempt 20: fail → DLQ
    """
    response = await ofd_client.post("/receipts", json=receipt, timeout=10)
    return response
```

**Backoff timeline:**
```
Attempt  Wait (s)  Cumulative (s)
1        0         0
2        1         1
3        2         3
4        4         7
5        8         15
6        16        31
7        32        63
8        60        123  (capped at max=60)
...
20       60        ~18 minutes total
```

---

## Edge Cases Handling

### Case 1: Sync worker crashes mid-sync

```
Problem: Lock held, worker dead
Solution: Redis lock TTL (300s) auto-releases
Result: Next sync cycle acquires lock and continues
```

### Case 2: Circuit Breaker opens during sync

```
Problem: ОФД fails mid-batch (e.g., synced 20/50)
Solution: Worker stops immediately, remaining 30 stay pending
Result: Next cycle retries remaining receipts
```

### Case 3: SQLite locked (rare with WAL)

```
Problem: Long-running read query locks writes
Solution: WAL mode allows concurrent reads/writes
Fallback: Retry INSERT with 100ms timeout
```

### Case 4: Partial sync (some succeed, some fail)

```
Problem: 45/50 synced, 5 failed
Solution: Each receipt tracked independently (status field)
Result: Next cycle retries only 5 failed receipts
```

---

## Grafana Dashboard Query Examples

### Sync throughput (receipts/min)
```promql
rate(kkt_receipts_synced_total{status="success"}[5m]) * 60
```

### Buffer backlog (hours to clear)
```promql
kkt_buffer_size / (rate(kkt_receipts_synced_total{status="success"}[5m]) * 60)
```

### Sync success rate (%)
```promql
sum(rate(kkt_receipts_synced_total{status="success"}[5m]))
  / sum(rate(kkt_receipts_synced_total[5m])) * 100
```

---

**Reference:**
- CLAUDE.md §4.4 for detailed implementation
- docs/5 Руководство по офлайн-режиму.md §5.4
- GLOSSARY.md for Distributed Lock, DLQ definitions
