# Redis Setup for OpticsERP

## Quick Start

### Prerequisites
- Docker Desktop installed and **running**
- Docker Compose v2.x+

### Start Redis

```bash
# Start Redis service
docker-compose up -d redis

# Check Redis status
docker-compose ps redis

# View Redis logs
docker-compose logs redis

# Test connectivity
docker-compose exec redis redis-cli ping
# Expected output: PONG
```

### Stop Redis

```bash
# Stop Redis (preserves data)
docker-compose stop redis

# Stop and remove container (data in volume persists)
docker-compose down

# Stop and remove everything (including data volume)
docker-compose down -v
```

## Configuration

**Service:** Redis 7-alpine
**Port:** 6379 (standard)
**Persistence:** AOF (append-only file)
**Volume:** `redis_data` (persistent storage)
**Network:** `opticserp_network`

## Testing

### Basic Connectivity

```bash
# Ping test
docker-compose exec redis redis-cli ping
# Expected: PONG

# Set/Get test
docker-compose exec redis redis-cli SET test "Hello Redis"
docker-compose exec redis redis-cli GET test
# Expected: "Hello Redis"
```

### Persistence Test

```bash
# Set a key
docker-compose exec redis redis-cli SET persist_test "data"

# Restart Redis
docker-compose restart redis

# Verify data persisted
docker-compose exec redis redis-cli GET persist_test
# Expected: "data"
```

### Health Check

```bash
# Check health status
docker-compose ps redis
# Expected: healthy

# View health check logs
docker-compose logs redis | grep health
```

## Troubleshooting

### Error: "The system cannot find the file specified"

**Problem:** Docker Desktop is not running

**Solution:**
1. Start Docker Desktop application
2. Wait for Docker to fully start (whale icon in system tray)
3. Run `docker info` to verify connection
4. Retry `docker-compose up -d redis`

### Error: "port 6379 is already allocated"

**Problem:** Another Redis instance is using port 6379

**Solution:**
```bash
# Kill process on port 6379
python scripts/kill_port.py 6379

# Or find and stop the conflicting container
docker ps | grep 6379
docker stop <container_id>
```

### Error: "version is obsolete"

**Warning (can be ignored):** Docker Compose v2 doesn't require version attribute

**Fixed:** Removed `version: '3.8'` from docker-compose.yml

## Usage in Code

### Python Connection

```python
import redis

# Connect to Redis
redis_client = redis.Redis(
    host='localhost',
    port=6379,
    db=0,
    decode_responses=True
)

# Test connection
redis_client.ping()  # Returns True

# Set/Get
redis_client.set('key', 'value')
value = redis_client.get('key')
```

### Distributed Lock (for sync_worker.py)

```python
import redis
from redis_lock import Lock

redis_client = redis.Redis(host='localhost', port=6379, db=0)

# Acquire distributed lock
with Lock(redis_client, "sync_lock", expire=300):
    # Only one worker can execute this code at a time
    sync_pending_receipts()
```

## Data Location

**Docker Volume:**
- Name: `redis_data`
- Location: Docker manages location (typically `/var/lib/docker/volumes/`)
- Persistence: Data survives container restarts and removal

**View volume:**
```bash
docker volume inspect opticserp_redis_data
```

## Monitoring

### Redis CLI

```bash
# Enter Redis CLI
docker-compose exec redis redis-cli

# Inside CLI:
> INFO server
> INFO memory
> DBSIZE
> KEYS *
> GET <key>
> SET <key> <value>
> DEL <key>
> FLUSHALL  # WARNING: Deletes all data
```

### Stats

```bash
# Memory usage
docker-compose exec redis redis-cli INFO memory | grep used_memory_human

# Number of keys
docker-compose exec redis redis-cli DBSIZE

# Connected clients
docker-compose exec redis redis-cli CLIENT LIST
```

## Related Documentation

- **Task Plan:** `docs/task_plans/20251009_OPTERP-20_setup_redis.md`
- **CLAUDE.md §3:** Port management (Redis on 6379)
- **Docker Compose:** Full configuration in `docker-compose.yml`

## Next Steps

- **OPTERP-21:** Implement Sync Worker with Redis distributed locking
- **OPTERP-24:** Setup Celery with Redis as message broker
