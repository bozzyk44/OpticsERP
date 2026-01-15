# Archived WebSocket Configuration Playbooks

These playbooks represent the iterative development process for fixing Odoo WebSocket "Connection Lost" errors.

**Status:** 🗄️ Archived - For historical reference only
**Use Instead:** `../configure-odoo-websocket.yml` (Master playbook)

---

## Chronological Development History

### 1. `fix-nginx-websocket.yml` ❌ FAILED
**Date:** 2025-12-31 19:30
**Attempt:** Initial WebSocket configuration with Ansible blockinfile

**Changes:**
- Added map directive using blockinfile
- Updated site config with WebSocket locations

**Result:** ❌ Nginx crashed with SEGFAULT (core dump)
**Issue:** blockinfile syntax error in nginx.conf caused segmentation fault

**Error:**
```
nginx.service: Main process exited, code=dumped, status=11/SEGV
```

---

### 2. `restore-nginx-emergency.yml` ✅ SUCCESS
**Date:** 2025-12-31 19:30 (immediately after crash)
**Purpose:** Emergency rollback from failed configuration

**Actions:**
- Removed broken map directive
- Restored site config from backup
- Restarted Nginx

**Result:** ✅ Nginx restored to working state

---

### 3. `fix-nginx-websocket-v2.yml` ⚠️ PARTIAL SUCCESS
**Date:** 2025-12-31 19:32
**Attempt:** Second try with safer sed-based approach

**Changes:**
- Used `sed` instead of blockinfile for map directive
- Added proper WebSocket locations with $connection_upgrade

**Result:** ⚠️ Configuration applied but WebSocket still failing
**Issue:** Missing Origin header, browser got 400 Bad Request

**Error:**
```
400 Bad Request: Empty or missing header(s): origin
```

---

### 4. `fix-websocket-origin-header.yml` ⚠️ PARTIAL SUCCESS
**Date:** 2025-12-31 19:34
**Attempt:** Added missing Origin header

**Changes:**
- Added `proxy_set_header Origin $http_origin;`
- Added `proxy_set_header Host $host;`

**Result:** ⚠️ Header added but WebSocket still not working
**Issue:** Browser was connecting directly to port 8069 instead of via Nginx

**Problem Identified:**
- Nginx logs showed only curl tests (127.0.0.1)
- Browser WebSocket requests (77.239.98.197) went directly to Odoo
- Missing `websocket_url` in odoo.conf

---

### 5. `fix-odoo-websocket-url.yml` ✅ SUCCESS
**Date:** 2025-12-31 19:35
**Attempt:** Configure Odoo to use Nginx proxy for WebSocket

**Changes:**
- Added `websocket_url = ws://194.87.235.33/websocket` to odoo.conf
- Restarted Odoo container

**Result:** ✅ Configuration complete, WebSocket working
**Breakthrough:** This was the missing piece!

---

### 6. `fix-websocket-port.yml`
**Date:** 2025-12-31 (earlier)
**Purpose:** Expose port 8072 for localhost only

**Changes:**
- Modified docker-compose.yml port mapping
- Changed from `8072:8072` to `127.0.0.1:8072:8072`

**Result:** ✅ Security improvement - WebSocket only accessible via Nginx

---

## Key Lessons Learned

### 1. Nginx Configuration
❌ **Don't use:** Ansible `blockinfile` for complex Nginx configs
✅ **Use instead:** `sed` or direct `copy` with full content

### 2. WebSocket Headers (Critical!)
```nginx
# WRONG - Hardcoded Connection header
proxy_set_header Connection "upgrade";

# CORRECT - Using map variable
map $http_upgrade $connection_upgrade {
    default upgrade;
    '' close;
}
proxy_set_header Connection $connection_upgrade;
```

### 3. Required Headers for Odoo WebSocket
```nginx
proxy_set_header Upgrade $http_upgrade;         # WebSocket upgrade
proxy_set_header Connection $connection_upgrade; # Variable from map
proxy_set_header Host $host;                     # Required!
proxy_set_header Origin $http_origin;            # Required by Odoo!
```

### 4. Odoo Proxy Configuration
```ini
# NOT ENOUGH
proxy_mode = True

# COMPLETE
proxy_mode = True
websocket_url = ws://194.87.235.33/websocket
```

### 5. Port Security
```yaml
# INSECURE - External WebSocket access
ports:
  - "8072:8072"

# SECURE - WebSocket only via Nginx
ports:
  - "127.0.0.1:8072:8072"
```

---

## Problem Resolution Timeline

1. **19:30** - Initial fix attempt → Nginx crash (SEGFAULT)
2. **19:30** - Emergency restore → Nginx working again
3. **19:32** - Second attempt → Config OK but WebSocket errors (400 Bad Request)
4. **19:34** - Add Origin header → Better but still failing (direct connection)
5. **19:35** - Add websocket_url → ✅ **PROBLEM SOLVED!**

**Total time:** ~5 minutes from crash to full resolution

---

## Migration to Master Playbook

All working changes consolidated into:
- `../configure-odoo-websocket.yml`

**Master playbook includes:**
- ✅ Safe map directive installation (sed-based)
- ✅ Complete WebSocket location config
- ✅ All required headers (Upgrade, Connection, Host, Origin)
- ✅ Odoo websocket_url configuration
- ✅ Proper error handling and rollback support
- ✅ Comprehensive testing and verification

---

## Do Not Use These Files

⚠️ **Warning:** These archived playbooks are **incomplete** and may cause issues:

- `fix-nginx-websocket.yml` - Will crash Nginx
- `fix-nginx-websocket-v2.yml` - Missing Origin header
- `fix-websocket-origin-header.yml` - Missing Odoo config
- `fix-odoo-websocket-url.yml` - Only partial fix

**Always use:** `../configure-odoo-websocket.yml` (Complete solution)

---

## Reference Value

These files are kept for:
1. **Historical documentation** - Shows problem-solving process
2. **Learning reference** - Common WebSocket configuration pitfalls
3. **Troubleshooting guide** - What NOT to do
4. **Audit trail** - Complete change history

---

Last Updated: 2025-12-31
