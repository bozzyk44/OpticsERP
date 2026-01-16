# Odoo WebSocket Configuration

**Status:** ✅ Configured and Working
**Last Updated:** 2025-12-31
**Issue Resolved:** "Connection Lost" errors in Odoo web interface

---

## Problem Summary

Odoo 17 web interface was experiencing persistent "Connection Lost" errors due to WebSocket connection failures.

**Root Causes Identified:**

1. **Nginx missing WebSocket support** - No proper upgrade headers
2. **Incorrect Connection header** - Hardcoded to "upgrade" instead of using map directive
3. **Missing Origin header** - Odoo requires Origin header for WebSocket validation
4. **Odoo direct connection** - Browser was connecting directly to port 8069 instead of using Nginx proxy
5. **Missing websocket_url** - Odoo config didn't specify WebSocket URL for proxy mode

---

## Solution Architecture

```
Browser (WebSocket Client)
    ↓
Nginx:80/websocket (Reverse Proxy)
    ↓ (proxy_pass to localhost:8072)
Odoo Gevent Service (WebSocket Server)
```

**Key Configuration Points:**

1. **Nginx Main Config** (`/etc/nginx/nginx.conf`):
   ```nginx
   map $http_upgrade $connection_upgrade {
       default upgrade;
       '' close;
   }
   ```

2. **Nginx Site Config** (`/etc/nginx/sites-available/194.87.235.33.conf`):
   ```nginx
   location /websocket {
       proxy_pass http://backend_odoo_longpolling;  # → localhost:8072
       proxy_http_version 1.1;
       proxy_set_header Upgrade $http_upgrade;
       proxy_set_header Connection $connection_upgrade;  # Uses map variable
       proxy_set_header Host $host;
       proxy_set_header Origin $http_origin;         # Required by Odoo
       proxy_buffering off;
       proxy_read_timeout 3600s;
   }
   ```

3. **Odoo Config** (`/etc/opticserp/odoo.conf`):
   ```ini
   proxy_mode = True
   websocket_url = ws://194.87.235.33/websocket
   ```

4. **Docker Port Mapping**:
   ```yaml
   ports:
     - "8069:8069"              # HTTP (public)
     - "127.0.0.1:8072:8072"    # WebSocket (localhost only, via Nginx)
   ```

---

## Deployment

### Master Playbook (Recommended)

Use the unified playbook for complete configuration:

```bash
cd /mnt/d/OpticsERP/ansible
ansible-playbook -i inventories/production/hosts.yml configure-odoo-websocket.yml
```

This playbook performs all steps in correct order:
1. Adds WebSocket map to nginx.conf
2. Configures Nginx site with WebSocket locations
3. Tests and reloads Nginx
4. Adds websocket_url to odoo.conf
5. Restarts Odoo
6. Verifies configuration

### Manual Verification

```bash
# Check Nginx config
sudo nginx -t
sudo systemctl status nginx

# Check Nginx map directive
grep -A 3 "map.*http_upgrade" /etc/nginx/nginx.conf

# Check WebSocket location
grep -A 10 "location /websocket" /etc/nginx/sites-available/194.87.235.33.conf

# Check Odoo config
grep websocket_url /etc/opticserp/odoo.conf

# Check port mappings
docker port opticserp_odoo
# Should show:
# 8069/tcp -> 0.0.0.0:8069
# 8072/tcp -> 127.0.0.1:8072

# Check Odoo logs for WebSocket
docker logs opticserp_odoo 2>&1 | grep -i "evented service"
# Should show: "Evented Service (longpolling) running on 0.0.0.0:8072"
```

---

## Testing

### Browser Testing

1. **Open Odoo:**
   ```
   http://194.87.235.33
   ```

2. **Check Browser Console (F12 → Console):**
   - ✅ Should see: "WebSocket connection established"
   - ❌ Should NOT see: WebSocket errors or 500 status

3. **Check Network Tab (F12 → Network → WS):**
   - ✅ Connection to: `ws://194.87.235.33/websocket`
   - ✅ Status: `101 Switching Protocols`
   - ✅ Connection: Active (green indicator)

4. **Verify No Disconnections:**
   - Use Odoo interface normally
   - ❌ Should NOT see "Connection Lost" popup
   - ✅ Real-time updates work smoothly

### Server-Side Testing

```bash
# Test WebSocket endpoint with curl
curl -i -H "Connection: Upgrade" -H "Upgrade: websocket" \
     -H "Sec-WebSocket-Version: 13" -H "Sec-WebSocket-Key: test" \
     -H "Origin: http://194.87.235.33" \
     http://localhost/websocket?version=17.0-3

# Check Nginx access logs
tail -f /var/log/nginx/194.87.235.33_access.log | grep websocket

# Check Odoo gevent logs
docker logs -f opticserp_odoo 2>&1 | grep -i "longpolling"
```

---

## Troubleshooting

### Issue: "Connection Lost" errors persist

**Check:**
1. Nginx map directive present:
   ```bash
   grep "connection_upgrade" /etc/nginx/nginx.conf
   ```

2. Odoo websocket_url configured:
   ```bash
   grep websocket_url /etc/opticserp/odoo.conf
   ```

3. Port 8072 bound to localhost only:
   ```bash
   docker port opticserp_odoo | grep 8072
   # Should show: 127.0.0.1:8072
   ```

### Issue: Nginx fails to reload

**Symptom:** `nginx: [emerg] unknown variable "$connection_upgrade"`

**Fix:**
```bash
# Ensure map directive is in nginx.conf INSIDE http {} block
sudo nano /etc/nginx/nginx.conf
# Add after "http {" line:
    map $http_upgrade $connection_upgrade {
        default upgrade;
        '' close;
    }

sudo nginx -t
sudo systemctl reload nginx
```

### Issue: WebSocket returns 400 Bad Request

**Symptom:** "Empty or missing header(s): origin"

**Fix:**
```bash
# Ensure Origin header is proxied
grep "Origin" /etc/nginx/sites-available/194.87.235.33.conf
# Should show: proxy_set_header Origin $http_origin;
```

### Issue: WebSocket connects to wrong port

**Symptom:** Browser connects to `ws://194.87.235.33:8069/websocket`

**Fix:**
```bash
# Ensure websocket_url is set in odoo.conf
echo "websocket_url = ws://194.87.235.33/websocket" | sudo tee -a /etc/opticserp/odoo.conf
cd /opt/opticserp && sudo -u deploy docker compose restart odoo
```

---

## Rollback Procedure

If WebSocket configuration causes issues:

```bash
# Restore Nginx configs from backup
sudo cp /etc/nginx/nginx.conf.backup-YYYY-MM-DD /etc/nginx/nginx.conf
sudo cp /etc/nginx/sites-available/194.87.235.33.conf.backup-YYYY-MM-DD \
         /etc/nginx/sites-available/194.87.235.33.conf
sudo nginx -t && sudo systemctl reload nginx

# Restore Odoo config
sudo cp /etc/opticserp/odoo.conf.backup-YYYY-MM-DD /etc/opticserp/odoo.conf
cd /opt/opticserp && sudo -u deploy docker compose restart odoo

# Verify rollback
sudo systemctl status nginx
docker ps --filter name=opticserp_odoo
```

---

## Files Modified

### Nginx Configuration
- `/etc/nginx/nginx.conf` - Added WebSocket map directive
- `/etc/nginx/sites-available/194.87.235.33.conf` - Added WebSocket locations

### Odoo Configuration
- `/etc/opticserp/odoo.conf` - Added `websocket_url`

### Backups Created
- `/etc/nginx/nginx.conf.backup-YYYY-MM-DD`
- `/etc/nginx/sites-available/194.87.235.33.conf.backup-YYYY-MM-DD`
- `/etc/opticserp/odoo.conf.backup-YYYY-MM-DD`

---

## Related Ansible Playbooks

**Master Playbook (Use This):**
- `configure-odoo-websocket.yml` - Complete WebSocket configuration

**Archived Playbooks (Historical):**
- `archived/fix-nginx-websocket.yml` - Initial attempt (failed with core dump)
- `archived/fix-nginx-websocket-v2.yml` - Second attempt (missing Origin)
- `archived/fix-websocket-origin-header.yml` - Added Origin header
- `archived/fix-odoo-websocket-url.yml` - Added Odoo websocket_url
- `archived/fix-websocket-port.yml` - Port 8072 localhost binding
- `archived/restore-nginx-emergency.yml` - Emergency rollback playbook

**Utility Playbooks:**
- `check-websocket-logs.yml` - Check logs for WebSocket errors
- `test-websocket-endpoint.yml` - Test WebSocket endpoint functionality

---

## References

- [Odoo 17 Deployment Documentation](https://www.odoo.com/documentation/17.0/administration/on_premise/deploy.html)
- [Nginx WebSocket Proxying](https://nginx.org/en/docs/http/websocket.html)
- [RFC 6455 - The WebSocket Protocol](https://tools.ietf.org/html/rfc6455)

---

## Change Log

**2025-12-31:**
- ✅ Added WebSocket map directive to nginx.conf
- ✅ Configured Nginx WebSocket locations (/websocket, /longpolling)
- ✅ Added Origin header passthrough
- ✅ Added websocket_url to odoo.conf
- ✅ Configured port 8072 as localhost-only
- ✅ Verified WebSocket connections working
- ✅ "Connection Lost" errors resolved
