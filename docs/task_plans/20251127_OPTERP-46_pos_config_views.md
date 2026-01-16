# Task Plan: OPTERP-46 - Create POS Config Views for KKT Adapter

**Date:** 2025-11-27
**Status:** ✅ Completed
**Priority:** High
**Assignee:** AI Agent
**Related Tasks:** OPTERP-45 (Offline Indicator Widget), OPTERP-47 (Saga Pattern)
**Phase:** Phase 2 - MVP (Week 8, Day 2)
**Related Commit:** (to be committed)

---

## Objective

Extend pos.config model and views to add KKT adapter configuration fields (URL, enable/disable, connection test).

---

## Context

**Background:**
- Part of Week 8: optics_pos_ru54fz Module Development
- POS config needs KKT adapter URL for integration
- Each POS terminal should have its own KKT adapter instance (local or remote)
- Configuration UI allows cashiers/managers to set up KKT adapter

**Scope:**
- Extend pos.config model with kkt_adapter_url field
- Add boolean toggle for enable/disable
- URL validation (format: http://host:port)
- Connection test button (calls /v1/health endpoint)
- Configuration UI in POS Config form view

---

## Implementation

### 1. Model Extension

#### pos.config Model

**File:** `models/pos_config.py` (175 lines)

**Inheritance:** `_inherit = 'pos.config'`

**New Fields:**

**1. kkt_adapter_url (Char)**
- **Type:** Char
- **String:** 'KKT Adapter URL'
- **Default:** 'http://localhost:8000'
- **Help:** 'URL of KKT adapter service (e.g., http://localhost:8000)'
- **Validation:** URL format (http://host:port or https://host:port)

**2. kkt_adapter_enabled (Boolean)**
- **Type:** Boolean
- **String:** 'Enable KKT Adapter'
- **Default:** True
- **Help:** 'Enable integration with KKT adapter for fiscal printing'

**3. kkt_adapter_status (Char, Computed)**
- **Type:** Char
- **String:** 'Connection Status'
- **Computed:** `_compute_kkt_adapter_status()`
- **Depends:** kkt_adapter_url, kkt_adapter_enabled
- **Values:** 'Disabled', 'Not configured', 'Not tested'

---

#### Validation Methods

**1. _check_kkt_adapter_url() (Constraint)**
- **Decorator:** `@api.constrains('kkt_adapter_url')`
- **Purpose:** Validate URL format
- **Regex:** `^https?://[\w\.\-]+(:\d+)?(/.*)?$`
- **Valid Examples:**
  - http://localhost:8000
  - http://192.168.1.100:8000
  - https://kkt.example.com:8000
- **Invalid Examples:**
  - localhost:8000 (missing protocol)
  - ftp://localhost:8000 (wrong protocol)
  - http://localhost (missing port - allowed but not recommended)

---

#### Business Methods

**1. action_test_kkt_connection()**
- **Purpose:** Test connection to KKT adapter
- **Type:** Button action (object method)
- **Logic:**
  1. Check if kkt_adapter_enabled → Warning if disabled
  2. Check if kkt_adapter_url configured → Error if empty
  3. Call KKT adapter: `GET {url}/v1/health` (timeout 5s)
  4. Display notification (success/error)
- **Returns:** `ir.actions.client` with notification params

**Notification Types:**
- **Success:** Green, 'Connection Successful', shows adapter status
- **Warning:** Yellow, 'KKT Adapter Disabled' or 'URL Not Configured'
- **Danger (Timeout):** Red, sticky, 'Connection Timeout (5s)'
- **Danger (Error):** Red, sticky, 'Connection Failed' + error message

**2. get_kkt_adapter_url()**
- **Purpose:** Get KKT adapter URL (convenience method)
- **Logic:** Return URL if enabled, else None
- **Used by:** kkt_adapter_api.py controller

---

### 2. Views Extension

#### POS Config Form View

**File:** `views/pos_config_views.xml` (115 lines)

**Inheritance:** `point_of_sale.pos_config_view_form`

**XPath:** `<xpath expr="//notebook" position="inside">`

**New Page:** "KKT Adapter (54-ФЗ)"

**Layout:**

**Group 1: KKT Adapter Configuration**
- `kkt_adapter_enabled` (boolean toggle)
- `kkt_adapter_url` (char, placeholder: http://localhost:8000)
  - Invisible if `not kkt_adapter_enabled`
- `kkt_adapter_status` (char, readonly)
  - Invisible if `not kkt_adapter_enabled`
- **Test Connection Button** (btn-primary, icon: fa-plug)
  - Calls: `action_test_kkt_connection()`
  - Invisible if `not kkt_adapter_enabled`

**Group 2: Help**
- **Info Alert (enabled):**
  - Default URL: http://localhost:8000
  - Format: http://host:port or https://host:port
  - Example: http://192.168.1.100:8000
  - Note: Each POS terminal should have its own KKT adapter instance
  - Invisible if `not kkt_adapter_enabled`

- **Warning Alert (disabled):**
  - "Fiscal printing is disabled for this POS"
  - Instruction to enable toggle above
  - Invisible if `kkt_adapter_enabled`

**Group 3: Advanced Settings (Placeholder)**
- Text: "Advanced KKT adapter settings will be added here in future versions"
- Invisible if `not kkt_adapter_enabled`
- **Future fields:**
  - kkt_timeout (integer, default 10s)
  - kkt_retry_count (integer, default 3)
  - kkt_enable_debug_mode (boolean)

**Group 4: Offline Buffer Settings (Placeholder)**
- Text: "Offline buffer settings (max size, alert thresholds) will be configured here"
- Invisible if `not kkt_adapter_enabled`
- **Future fields:**
  - buffer_max_size (integer, default 200)
  - buffer_alert_threshold_yellow (integer, default 50%)
  - buffer_alert_threshold_red (integer, default 80%)

---

### 3. Stub Models

**Created stub files for future implementation:**

#### pos_session.py (40 lines)
- **Purpose:** X/Z reports and fiscal features
- **Status:** Stub (to be implemented in future tasks)
- **Future Features:**
  - X-report generation (shift report without closing)
  - Z-report generation (shift close report)
  - FFD 1.2 compliance (correct tags)
  - Electronic receipt (email/SMS)

#### offline_buffer_status.py (50 lines)
- **Model:** `pos.offline.buffer.status`
- **Purpose:** POS offline buffer monitoring
- **Status:** Stub (to be implemented in future tasks)
- **Future Features:**
  - Real-time buffer status tracking
  - Alert thresholds (yellow: 50%, red: 80%)
  - Historical buffer metrics
  - Integration with Grafana/Prometheus

---

## Files Created/Modified

### Created
1. **`addons/optics_pos_ru54fz/models/pos_config.py`** (175 lines)
   - Extend pos.config model
   - Add kkt_adapter_url, kkt_adapter_enabled fields
   - URL validation (regex pattern)
   - Connection test method
   - Get URL convenience method

2. **`addons/optics_pos_ru54fz/views/pos_config_views.xml`** (115 lines)
   - Extend POS Config form view
   - Add "KKT Adapter (54-ФЗ)" page
   - Configuration UI (URL, toggle, test button)
   - Help text and examples
   - Placeholder sections for future features

3. **`addons/optics_pos_ru54fz/models/pos_session.py`** (40 lines, stub)
   - Stub file for X/Z reports
   - Future implementation

4. **`addons/optics_pos_ru54fz/models/offline_buffer_status.py`** (50 lines, stub)
   - Stub file for buffer status model
   - Future implementation

### Already Prepared (Bootstrap)
5. **`addons/optics_pos_ru54fz/models/__init__.py`**
   - Already imports: pos_config, pos_session, offline_buffer_status ✅

6. **`addons/optics_pos_ru54fz/__manifest__.py`**
   - Already includes: 'views/pos_config_views.xml' ✅

7. **`addons/optics_pos_ru54fz/security/ir.model.access.csv`**
   - Already includes: pos.offline.buffer.status access rules ✅

---

## Acceptance Criteria

- ✅ kkt_adapter_url field added to pos.config
- ✅ kkt_adapter_enabled boolean toggle added
- ✅ URL validation (format: http://host:port)
- ✅ Default URL: http://localhost:8000
- ✅ Connection test button added
- ✅ Test calls /v1/health endpoint (timeout 5s)
- ✅ Success/error notifications displayed
- ✅ Configuration UI in POS Config form view
- ✅ Help text with examples
- ✅ Invisible fields when disabled
- ✅ Stub models created (pos_session, offline_buffer_status)

---

## URL Validation Rules

**Valid URL Format:**
```regex
^https?://[\w\.\-]+(:\d+)?(/.*)?$
```

**Valid Examples:**
```
http://localhost:8000
http://192.168.1.100:8000
https://kkt.example.com:8000
http://kkt-adapter:8000
http://10.0.0.50:8000/api
```

**Invalid Examples:**
```
localhost:8000               → Missing protocol (http://)
ftp://localhost:8000         → Wrong protocol (must be http/https)
http://localhost:80a0        → Invalid port number
http://                      → Missing host
```

**Error Message:**
```
Invalid KKT adapter URL format.
Expected: http://host:port or https://host:port
Example: http://localhost:8000
```

---

## Connection Test Flow

**Test Button Clicked:**

1. **Check Enabled:**
   - If disabled → Warning notification: "KKT Adapter Disabled"

2. **Check URL:**
   - If empty → Danger notification: "URL Not Configured"

3. **Test Connection:**
   - Call: `GET {url}/v1/health` (timeout 5s)
   - Expected response: `{"status": "OK", ...}`

4. **Handle Response:**
   - **Success (200 OK):**
     - Green notification: "Connection Successful"
     - Message: "Connected to KKT adapter at {url}\nStatus: OK"
     - Sticky: No

   - **Timeout (5s):**
     - Red notification: "Connection Timeout"
     - Message: "KKT adapter at {url} is not responding (timeout 5s)."
     - Sticky: Yes

   - **Connection Error:**
     - Red notification: "Connection Failed"
     - Message: "Failed to connect to KKT adapter:\n{error}"
     - Sticky: Yes

   - **Unexpected Error:**
     - Red notification: "Error"
     - Message: "Unexpected error:\n{error}"
     - Sticky: Yes

---

## UI/UX Features

### Configuration Page

**Page Name:** "KKT Adapter (54-ФЗ)"

**Position:** New page in POS Config notebook (after existing pages)

**Layout:**
```
┌─────────────────────────────────────────────────┐
│ KKT Adapter Configuration                       │
│ ┌───────────────────────────────────────────┐   │
│ │ Enable KKT Adapter:  [✓] (toggle)        │   │
│ │ KKT Adapter URL:     [http://localhost...] │   │
│ │ Connection Status:   Not tested           │   │
│ │ [Test Connection]                         │   │
│ └───────────────────────────────────────────┘   │
│                                                   │
│ Help                                             │
│ ┌───────────────────────────────────────────┐   │
│ │ ℹ KKT Adapter Configuration                │   │
│ │ • Default URL: http://localhost:8000       │   │
│ │ • Format: http://host:port                 │   │
│ │ • Example: http://192.168.1.100:8000       │   │
│ │                                             │   │
│ │ The KKT adapter must be running and        │   │
│ │ accessible from this POS terminal.         │   │
│ │ Use the "Test Connection" button to        │   │
│ │ verify connectivity.                       │   │
│ │                                             │   │
│ │ Note: Each POS terminal should have its    │   │
│ │ own KKT adapter instance.                  │   │
│ └───────────────────────────────────────────┘   │
│                                                   │
│ Advanced Settings (placeholder)                  │
│ Offline Buffer Settings (placeholder)            │
└─────────────────────────────────────────────────┘
```

### Notifications

**Success (Green):**
```
✓ Connection Successful
Connected to KKT adapter at http://localhost:8000
Status: OK
```

**Warning (Yellow):**
```
⚠ KKT Adapter Disabled
KKT adapter integration is disabled for this POS.
```

**Error (Red, Sticky):**
```
✗ Connection Timeout
KKT adapter at http://localhost:8000 is not responding (timeout 5s).
```

---

## Integration Points

### With Offline Indicator Widget (OPTERP-45)

**Controller:** `kkt_adapter_api.py`

**Method:** `_get_kkt_adapter_url()`

```python
def _get_kkt_adapter_url(self):
    pos_session = request.env['pos.session'].sudo().search([...], limit=1)
    kkt_adapter_url = pos_session.config_id.kkt_adapter_url
    return kkt_adapter_url.rstrip('/')
```

**Usage:** Offline indicator fetches buffer status via this controller

### With KKT Adapter (External Service)

**Endpoint:** `GET /v1/health`

**Expected Response:**
```json
{
  "status": "OK",
  "version": "1.0.0",
  "uptime": 12345
}
```

**Timeout:** 5 seconds

---

## Testing (Future: OPTERP-XX)

**Note:** Unit tests will be created in a future task.

**Planned Tests:**
- test_pos_config_kkt_url_validation() — Valid/invalid URL formats
- test_pos_config_kkt_enabled_default() — Default enabled = True
- test_pos_config_test_connection_success() — Successful connection test
- test_pos_config_test_connection_timeout() — Timeout handling
- test_pos_config_test_connection_error() — Connection error handling
- test_pos_config_get_kkt_url() — Get URL method
- test_pos_config_disabled_no_url() — Disabled adapter returns None

**Coverage Target:** ≥95%

---

## Known Issues

### Issue 1: Requires requests Library
**Description:** Connection test uses `requests` library.

**Impact:** Test button requires requests library installed.

**Resolution:**
- Add to `requirements.txt`: `requests==2.31.0`
- Already commonly installed in Odoo environments

**Status:** ✅ Acceptable (standard library)

### Issue 2: Health Endpoint Not Implemented Yet
**Description:** KKT adapter /v1/health endpoint not implemented yet.

**Impact:** Connection test will fail until KKT adapter is implemented.

**Resolution:**
- Implement /v1/health endpoint in KKT adapter (POC phase)
- Expected in POC Week 3-4

**Status:** ⏸️ Pending (KKT adapter implementation)

---

## Next Steps

1. **OPTERP-47:** Implement Saga Pattern (Refund Blocking)
   - Refund blocked if original not synced (HTTP 409)
   - POST /v1/pos/refund checks buffer

2. **OPTERP-48:** Implement Bulkhead Pattern (Celery Queues)
   - 4 queues: critical, high, default, low
   - sync_buffer → critical queue

3. **Phase 2 Week 9:** UAT Testing
   - UAT-01 to UAT-11 test scenarios
   - Fix critical bugs
   - MVP sign-off

4. **Future Tasks:**
   - Implement X/Z reports (pos_session.py)
   - Implement offline buffer status model (offline_buffer_status.py)
   - Add advanced settings (timeout, retry count, debug mode)
   - Add offline buffer settings (max size, alert thresholds)

---

## References

### Domain Documentation
- **CLAUDE.md:** §3.2 (optics_pos_ru54fz module overview), §7 (KKT adapter)
- **PROJECT_PHASES.md:** Week 8 Day 2 (POS Config Views)

### Related Tasks
- **OPTERP-44:** Create Connector Import Unit Tests ✅ COMPLETED
- **OPTERP-45:** Create Offline Indicator Widget ✅ COMPLETED
- **OPTERP-46:** Create POS Config Views for KKT Adapter ✅ COMPLETED (this task)
- **OPTERP-47:** Implement Saga Pattern (Refund Blocking) (Next)

### Odoo Documentation
- **Odoo 17 ORM:** Model inheritance (_inherit), fields, constraints
- **Odoo 17 Views:** Form view inheritance, XPath, invisible domains
- **Odoo 17 Actions:** ir.actions.client, display_notification

### Python Libraries
- **requests:** HTTP client for connection testing
- **re:** Regular expressions for URL validation

---

## Timeline

- **Start:** 2025-11-27 21:15
- **End:** 2025-11-27 21:35
- **Duration:** ~20 minutes
- **Lines of Code:** 175 (pos_config.py) + 115 (pos_config_views.xml) + 40 (pos_session.py stub) + 50 (offline_buffer_status.py stub) = **380 lines**

---

**Status:** ✅ CONFIG VIEWS COMPLETE (Pending Odoo Runtime + KKT Adapter for Testing)

**Module Status:** optics_pos_ru54fz (partial) — Offline indicator ✅, POS config ✅

**Next Task:** OPTERP-47 (Implement Saga Pattern - Refund Blocking)

---

🤖 Generated with [Claude Code](https://claude.com/claude-code)
