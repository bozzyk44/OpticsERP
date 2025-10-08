# Circuit Breaker State Transitions

> **Purpose:** Visual representation of Circuit Breaker pattern for ОФД connectivity
> **Reference:** CLAUDE.md §4.2, GLOSSARY.md

---

## State Machine Diagram

```mermaid
stateDiagram-v2
    [*] --> CLOSED: Initial state

    CLOSED --> OPEN: failure_threshold reached<br/>(5 consecutive errors)
    CLOSED --> CLOSED: Request succeeds

    OPEN --> HALF_OPEN: recovery_timeout elapsed<br/>(60 seconds)
    OPEN --> OPEN: Requests blocked

    HALF_OPEN --> CLOSED: success_threshold reached<br/>(2 consecutive successes)
    HALF_OPEN --> OPEN: Any request fails

    note right of CLOSED
        Normal operation
        - All requests pass through
        - Track failures
        - Reset counter on success
    end note

    note right of OPEN
        Failure mode
        - Block all requests
        - Buffer receipts locally
        - Wait recovery_timeout
        - Metric: cb_state = 1
    end note

    note right of HALF_OPEN
        Testing recovery
        - Allow limited requests
        - If succeed → CLOSED
        - If fail → OPEN
        - Metric: cb_state = 2
    end note
```

---

## Configuration

**From:** `config.toml` or environment variables

```toml
[buffer.circuit_breaker]
failure_threshold = 5         # Errors to trigger OPEN
recovery_timeout = 60         # Seconds in OPEN before HALF_OPEN
success_threshold = 2         # Successes to return to CLOSED
expected_exceptions = [
    "TimeoutError",
    "ConnectionError",
    "HTTPError[5xx]"
]
```

---

## Sequence: Normal → Failure → Recovery

```mermaid
sequenceDiagram
    participant Adapter as KKT Adapter
    participant CB as Circuit Breaker
    participant OFD as ОФД API
    participant Metrics as Prometheus

    Note over Adapter,Metrics: STATE: CLOSED (Normal)

    loop Normal operations
        Adapter->>CB: send_receipt(receipt)
        CB->>OFD: POST /receipts
        OFD-->>CB: 200 OK
        CB-->>Adapter: Success
        Note right of CB: failure_count = 0
    end

    Note over Adapter,Metrics: ОФД starts failing

    Adapter->>CB: send_receipt(receipt)
    CB->>OFD: POST /receipts
    OFD-->>CB: 503 Service Unavailable
    CB-->>Adapter: Error (retry 1/5)
    Note right of CB: failure_count = 1

    Adapter->>CB: send_receipt(receipt)
    CB->>OFD: POST /receipts
    OFD-->>CB: Timeout
    CB-->>Adapter: Error (retry 2/5)
    Note right of CB: failure_count = 2

    Note over CB: ... 3 more failures ...

    Adapter->>CB: send_receipt(receipt)
    CB->>OFD: POST /receipts
    OFD-->>CB: Timeout
    CB->>CB: failure_count = 5 → OPEN
    CB->>Metrics: cb_state = 1 (OPEN)
    CB-->>Adapter: CircuitBreakerError

    Note over Adapter,Metrics: STATE: OPEN (Blocking)

    Adapter->>CB: send_receipt(receipt)
    CB-->>Adapter: ⛔ CircuitBreakerError<br/>(not sent to ОФД)
    Note right of Adapter: Receipt buffered locally

    Note over CB: Wait recovery_timeout (60s)

    CB->>CB: Timer expired → HALF_OPEN
    CB->>Metrics: cb_state = 2 (HALF_OPEN)

    Note over Adapter,Metrics: STATE: HALF_OPEN (Testing)

    Adapter->>CB: send_receipt(receipt)
    CB->>OFD: POST /receipts (probe)
    OFD-->>CB: 200 OK
    CB->>CB: success_count = 1
    CB-->>Adapter: Success

    Adapter->>CB: send_receipt(receipt)
    CB->>OFD: POST /receipts (probe)
    OFD-->>CB: 200 OK
    CB->>CB: success_count = 2 → CLOSED
    CB->>Metrics: cb_state = 0 (CLOSED)
    CB-->>Adapter: Success

    Note over Adapter,Metrics: STATE: CLOSED (Recovered)
```

---

## Prometheus Metrics & Alerts

### Metrics

```prometheus
# Circuit Breaker state
kkt_circuit_breaker_state{pos_id="POS-001"}
# Values: 0 (CLOSED), 1 (OPEN), 2 (HALF_OPEN)

# Total times opened
kkt_circuit_breaker_opens_total{pos_id="POS-001"}

# Failure count (current)
kkt_circuit_breaker_failures{pos_id="POS-001"}
```

### Alert Rules

```yaml
groups:
  - name: circuit_breaker_alerts
    rules:
      - alert: CircuitBreakerOpen
        expr: kkt_circuit_breaker_state == 1
        for: 5m
        labels:
          severity: P2
        annotations:
          summary: "Circuit Breaker OPEN на {{ $labels.pos_id }}"
          description: "ОФД недоступен, чеки буферизуются локально"

      - alert: CircuitBreakerFlapping
        expr: increase(kkt_circuit_breaker_opens_total[1h]) > 5
        labels:
          severity: P1
        annotations:
          summary: "Circuit Breaker flapping на {{ $labels.pos_id }}"
          description: "CB открывался 5+ раз за час, возможна сетевая проблема"
```

---

## Grafana Dashboard Panel

```json
{
  "title": "Circuit Breaker States",
  "targets": [
    {
      "expr": "kkt_circuit_breaker_state",
      "legendFormat": "{{ pos_id }}"
    }
  ],
  "fieldConfig": {
    "overrides": [
      {
        "matcher": { "id": "byValue", "options": { "value": 0 } },
        "properties": [{ "id": "color", "value": "green" }]
      },
      {
        "matcher": { "id": "byValue", "options": { "value": 1 } },
        "properties": [{ "id": "color", "value": "red" }]
      },
      {
        "matcher": { "id": "byValue", "options": { "value": 2 } },
        "properties": [{ "id": "color", "value": "yellow" }]
      }
    ]
  }
}
```

---

## Python Implementation (pybreaker)

```python
from pybreaker import CircuitBreaker
from prometheus_client import Gauge, Counter

# Metrics
cb_state = Gauge('kkt_circuit_breaker_state', 'CB state', ['pos_id'])
cb_opens = Counter('kkt_circuit_breaker_opens_total', 'CB opens', ['pos_id'])

def on_open(breaker):
    """Callback when CB opens"""
    pos_id = breaker.name
    cb_state.labels(pos_id=pos_id).set(1)
    cb_opens.labels(pos_id=pos_id).inc()
    logger.warning(f"Circuit Breaker OPEN: {pos_id}")

def on_close(breaker):
    """Callback when CB closes"""
    pos_id = breaker.name
    cb_state.labels(pos_id=pos_id).set(0)
    logger.info(f"Circuit Breaker CLOSED: {pos_id}")

def on_half_open(breaker):
    """Callback when CB enters HALF_OPEN"""
    pos_id = breaker.name
    cb_state.labels(pos_id=pos_id).set(2)
    logger.info(f"Circuit Breaker HALF_OPEN: {pos_id}")

# Create Circuit Breaker
ofd_cb = CircuitBreaker(
    fail_max=5,                    # failure_threshold
    reset_timeout=60,              # recovery_timeout
    expected_exception=(TimeoutError, ConnectionError),
    listeners=[on_open, on_close, on_half_open]
)

# Usage
@ofd_cb
async def send_receipt_to_ofd(receipt):
    """Send receipt to ОФД (protected by CB)"""
    response = await ofd_client.post("/receipts", json=receipt, timeout=10)
    return response
```

---

## Decision Tree: When Circuit Opens

```
Circuit Breaker opened
    ├─→ Is this expected? (e.g., scheduled ОФД maintenance)
    │   ├─→ Yes: Monitor, no action needed
    │   └─→ No: Investigate
    │
    ├─→ Check ОФД status (web portal, support)
    │   ├─→ ОФД down: Wait for recovery, monitor buffer
    │   └─→ ОФД up: Check network connectivity
    │
    ├─→ Check network (ping, traceroute)
    │   ├─→ Network issue: Fix network, CB will recover
    │   └─→ Network OK: Check adapter logs
    │
    └─→ Check adapter logs for errors
        ├─→ API changed: Update ofd_client.py
        ├─→ Auth failed: Renew credentials
        └─→ Unknown: Escalate to L2
```

---

**Reference:**
- CLAUDE.md §4.2 for detailed implementation
- GLOSSARY.md for Circuit Breaker definition
- docs/5 Руководство по офлайн-режиму.md §5.6
