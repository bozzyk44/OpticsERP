# Two-Phase Fiscalization — Sequence Diagram

> **Purpose:** Visual representation of двухфазная фискализация process
> **Reference:** CLAUDE.md §4.2, docs/5 §5.3

---

## Process Flow

```mermaid
sequenceDiagram
    participant Cashier
    participant POS as POS UI
    participant Adapter as KKT Adapter (FastAPI)
    participant SQLite as Offline Buffer
    participant KKT as KKT Device
    participant CB as Circuit Breaker
    participant OFD as ОФД Cloud

    Note over Cashier,OFD: PHASE 1: Local (Always Succeeds)

    Cashier->>POS: Complete sale
    POS->>Adapter: POST /v1/kkt/receipt<br/>{items, payments, Idempotency-Key}

    activate Adapter

    Adapter->>Adapter: Generate HLC timestamp<br/>(local_time, logical_counter)
    Adapter->>Adapter: Generate receipt_id (UUIDv4)

    Adapter->>SQLite: INSERT receipt<br/>(id, fiscal_doc, status=pending)
    SQLite-->>Adapter: OK

    Adapter->>KKT: Print receipt
    Note right of KKT: Timeout: 10s

    alt KKT responds
        KKT-->>Adapter: Receipt printed
    else KKT timeout
        Adapter->>Adapter: Log error (P2 alert)
        Note right of Adapter: Print failed but<br/>buffer saved
    end

    Adapter->>SQLite: INSERT buffer_event<br/>(type=receipt_added)
    SQLite-->>Adapter: OK

    Adapter-->>POS: 200 OK<br/>{status: "buffered", receipt_id}
    deactivate Adapter

    POS-->>Cashier: ✅ Sale completed

    Note over Cashier,OFD: PHASE 2: Async (Best-Effort)

    activate Adapter
    Adapter->>CB: Check state

    alt Circuit Breaker CLOSED
        CB-->>Adapter: OK to proceed

        Adapter->>OFD: POST /receipts<br/>{fiscal_doc}
        Note right of OFD: Timeout: 10s

        alt OFD success
            OFD-->>Adapter: 200 OK<br/>{fiscalDocumentNumber, fiscalSign}

            Adapter->>SQLite: UPDATE receipt<br/>(status=synced, server_time=now)
            SQLite-->>Adapter: OK

            Adapter->>SQLite: INSERT buffer_event<br/>(type=receipt_synced)

            Note right of Adapter: ✅ Sync successful

        else OFD error (5xx, timeout)
            OFD-->>Adapter: Error

            Adapter->>SQLite: UPDATE receipt<br/>(retry_count += 1, last_error)

            Note right of Adapter: Will retry later<br/>(exponential backoff)

            alt Retry count >= 20
                Adapter->>SQLite: Move to DLQ<br/>(reason=max_retries)
                Adapter->>SQLite: INSERT buffer_event<br/>(type=receipt_failed)
                Note right of Adapter: ❌ Manual resolution needed
            end

        end

    else Circuit Breaker OPEN
        CB-->>Adapter: ⛔ Blocked
        Note right of Adapter: Receipt stays in buffer<br/>No sync attempt
    end

    deactivate Adapter
```

---

## Key Points

### Phase 1 (Local)
- **Always succeeds** even if ОФД unavailable
- Receipt saved to SQLite with WAL+FULL synchronous
- Printed on KKT (best-effort, 10s timeout)
- Cashier can continue selling immediately

### Phase 2 (Async)
- **Best-effort** delivery to ОФД
- Circuit Breaker prevents hammering failing ОФД
- Exponential backoff for retries (up to 20 attempts)
- After max retries → Dead Letter Queue (manual resolution)

---

## Critical Distinction

| Aspect | Phase 1 | Phase 2 |
|--------|---------|---------|
| **Timing** | Synchronous (blocking) | Asynchronous (background) |
| **Failure handling** | Never fails | Retries + DLQ |
| **Business impact** | Blocks sale if fails | No impact on sales |
| **Бизнес-доступность** | Critical | Non-critical |

---

## Error Scenarios

### Scenario 1: ОФД Unavailable

```
Phase 1: ✅ Receipt saved + printed → Cashier happy
Phase 2: ⛔ Circuit Breaker OPEN → Receipt buffered
Result: Business continues, sync when ОФД returns
```

### Scenario 2: KKT Timeout

```
Phase 1: ✅ Receipt saved, ⚠️ Print timeout → P2 alert
Phase 2: ✅ Synced to ОФД (when back online)
Result: Customer doesn't get paper receipt, but fiscal data preserved
```

### Scenario 3: Power Loss During Phase 1

```
Phase 1: ✅ SQLite WAL ensures durability → Receipt recovered after reboot
Phase 2: ✅ Sync worker picks up on restart
Result: Zero data loss (WAL+FULL synchronous)
```

---

## Prometheus Metrics

```prometheus
# Buffer size
kkt_buffer_size{pos_id="POS-001"} = 15

# Circuit Breaker state (0=CLOSED, 1=OPEN, 2=HALF_OPEN)
kkt_circuit_breaker_state{pos_id="POS-001"} = 1

# Sync duration (histogram)
kkt_sync_duration_seconds{pos_id="POS-001", quantile="0.95"} = 2.3

# DLQ size
kkt_dlq_size{pos_id="POS-001"} = 2
```

---

**Reference:** See CLAUDE.md §4.2 for implementation details.
