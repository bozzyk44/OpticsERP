# Task Plan: OPTERP-20 - Setup Redis in Docker Compose

**Date:** 2025-10-09
**Status:** In Progress
**Priority:** High
**Assignee:** AI Agent

---

## Objective

Add Redis service to `docker-compose.yml` for distributed locking and Celery message broker.

---

## Requirements (from JIRA)

From `docs/jira/jira_import.csv`:
> - Redis 7-alpine service defined
> - Port 6379 exposed
> - Redis starts successfully

---

## Current State

**File Status:** `docker-compose.yml` does not exist yet

**Required for:**
- Distributed Lock (sync_worker.py) - prevents concurrent sync operations
- Celery message broker (future task: OPTERP-22)
- APScheduler persistent job store (optional)

---

## Implementation Plan

### Step 1: Create docker-compose.yml

**Location:** `D:\OpticsERP\docker-compose.yml`

**Services to include:**
1. **Redis** - Message broker + distributed locks
2. **KKT Adapter** - FastAPI application (future)
3. **PostgreSQL** - Database (future, for Odoo)

**Initial Implementation (Redis only):**
```yaml
version: '3.8'

services:
  redis:
    image: redis:7-alpine
    container_name: opticserp_redis
    ports:
      - "6379:6379"
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data
    networks:
      - opticserp_network
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

networks:
  opticserp_network:
    driver: bridge

volumes:
  redis_data:
    driver: local
```

### Step 2: Configuration Details

**Redis Settings:**
- **Image:** `redis:7-alpine` (lightweight, latest stable)
- **Port:** `6379` (standard Redis port)
- **Persistence:** AOF (append-only file) mode for durability
- **Volume:** `redis_data` for persistent storage
- **Restart:** `unless-stopped` for high availability
- **Health Check:** `redis-cli ping` every 10s

**Network:**
- **Name:** `opticserp_network` (bridge mode)
- **Purpose:** Isolate OpticsERP services

### Step 3: Test Redis Connectivity

**Commands:**
```bash
# Start Redis
docker-compose up -d redis

# Check Redis logs
docker-compose logs redis

# Test connectivity
docker-compose exec redis redis-cli ping
# Expected output: PONG

# Test set/get
docker-compose exec redis redis-cli SET test "Hello Redis"
docker-compose exec redis redis-cli GET test
# Expected output: "Hello Redis"

# Check health status
docker-compose ps
# Expected: redis (healthy)
```

### Step 4: Update sync_worker.py

**Current:** Sync worker uses in-memory lock (not distributed)

**Future (OPTERP-21):** Integrate `python-redis-lock` for distributed locking

**Required changes (OPTERP-21):**
```python
# sync_worker.py
import redis
from redis_lock import Lock

redis_client = redis.Redis(host='localhost', port=6379, db=0)

def sync_pending_receipts():
    with Lock(redis_client, "sync_lock", expire=300):
        # Sync logic here
        pass
```

---

## Acceptance Criteria

- [x] docker-compose.yml created
- [x] Redis 7-alpine service defined
- [x] Port 6379 exposed
- [x] AOF persistence enabled
- [x] Health check configured
- [x] Volume for data persistence
- [x] Removed obsolete version attribute (Docker Compose v2)
- [ ] Redis starts successfully (requires Docker Desktop to be running)
- [ ] Redis connectivity tested (redis-cli ping)
- [ ] Documentation updated

---

## Files to Create/Modify

**New:**
1. `docker-compose.yml` - Docker Compose configuration

**Modified (future):**
2. `kkt_adapter/app/sync_worker.py` - Add Redis distributed lock (OPTERP-21)
3. `kkt_adapter/app/config.toml` - Add Redis connection settings (optional)

---

## Dependencies

**Required:**
- Docker installed and running
- Docker Compose v2.x+

**Used by:**
- **OPTERP-21:** Implement Sync Worker - will use Redis for distributed locking
- **OPTERP-22:** Integrate APScheduler for Sync - may use Redis for job store
- **OPTERP-24:** Implement Bulkhead Pattern (Celery Queues) - will use Redis as broker

---

## Testing Strategy

### 1. Smoke Test
```bash
# Start Redis
docker-compose up -d redis

# Wait for healthy status
docker-compose ps | grep redis | grep healthy

# Test ping
docker-compose exec redis redis-cli ping
# Expected: PONG
```

### 2. Persistence Test
```bash
# Set key
docker-compose exec redis redis-cli SET persist_test "data"

# Restart Redis
docker-compose restart redis

# Verify persistence
docker-compose exec redis redis-cli GET persist_test
# Expected: "data"
```

### 3. Health Check Test
```bash
# Force Redis crash (stop container)
docker-compose stop redis

# Check health status (should be unhealthy/exited)
docker-compose ps redis

# Restart
docker-compose up -d redis

# Wait for recovery
sleep 15
docker-compose ps redis
# Expected: healthy
```

---

## Timeline

- Docker Compose creation: 10 min
- Redis testing: 5 min
- Documentation: 5 min
- **Total:** ~20 min

---

## Notes

**Why Redis 7-alpine?**
- Alpine: Lightweight (5 MB vs 110 MB for full image)
- Redis 7: Latest stable with ACL, streams, and improved performance
- Official image: Maintained by Redis team

**Why AOF persistence?**
- Durability: Every write operation logged
- Safety: Better than RDB for mission-critical data
- Recovery: Can reconstruct full dataset from log

**Docker Desktop Requirement:**
- Docker Desktop must be running for `docker-compose up` to work
- Error: "open //./pipe/dockerDesktopLinuxEngine: The system cannot find the file specified"
- Solution: Start Docker Desktop application before running docker-compose commands

**Future Extensions:**
- Add Redis Sentinel for HA (Production phase)
- Add Redis password authentication (config.toml)
- Add Redis Cluster for horizontal scaling (if needed)

---

## Related Tasks

- **OPTERP-21:** Implement Sync Worker - uses Redis for distributed locking
- **OPTERP-22:** Integrate APScheduler - may use Redis for job persistence
- **OPTERP-24:** Bulkhead Pattern (Celery) - uses Redis as message broker

---

## References

- Redis Docker Hub: https://hub.docker.com/_/redis
- Docker Compose Spec: https://docs.docker.com/compose/compose-file/
- CLAUDE.md §3: Port management (Redis on 6379)
