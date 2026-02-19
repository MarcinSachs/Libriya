# Redis Configuration for Production

## Why Redis?

In-memory rate limiter (`SimpleCache`) doesn't work with multiple Gunicorn workers:

```
Request 1 → Worker 1 (limit: 4 remaining)
Request 2 → Worker 2 (limit: 5 remaining) ← Each worker has own store!
Request 3 → Worker 1 (limit: 3 remaining)
...
```

Result: Attacker can bypass rate limits by distributing requests across workers.

**Solution**: Use shared Redis backend

---

## Installation

### Option 1: Docker (Recommended)

```bash
# Pull Redis image
docker pull redis:7-alpine

# Run Redis container
docker run -d \
  --name libriya-redis \
  -p 6379:6379 \
  -v redis-data:/data \
  redis:7-alpine \
  redis-server --appendonly yes --requirepass "your_secure_password"

# Test connection
redis-cli -h localhost -p 6379 ping
# Output: PONG
```

### Option 2: System Package (Ubuntu/Debian)

```bash
# Install
sudo apt-get update
sudo apt-get install redis-server

# Start service
sudo systemctl start redis-server
sudo systemctl enable redis-server

# Secure with password (edit /etc/redis/redis.conf)
sudo sed -i 's/# requirepass foobared/requirepass your_secure_password/' /etc/redis/redis.conf
sudo systemctl restart redis-server
```

### Option 3: macOS (Homebrew)

```bash
brew install redis
brew services start redis
```

---

## Configuration

### 1. Update requirements.txt

```bash
pip install redis==5.0.1
```

### 2. Update config.py

```python
# config.py

class Config(BaseSettings):
    # ... existing config ...
    
    # Redis Configuration
    REDIS_URL: str = os.getenv('REDIS_URL', 'redis://localhost:6379/1')
    
    # Rate Limiting Storage
    RATELIMIT_STORAGE_URL: str = os.getenv(
        'RATELIMIT_STORAGE_URL',
        os.getenv('REDIS_URL', 'redis://localhost:6379/1')
    )
```

### 3. Update app/__init__.py

```python
# app/__init__.py

from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# Initialize with Redis storage
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri=app.config.get('RATELIMIT_STORAGE_URL')
)
```

### 4. Create .env configuration

```bash
# .env (development)
REDIS_URL=redis://localhost:6379/1

# .env.production
REDIS_URL=redis://:password@redis.example.com:6379/1
RATELIMIT_STORAGE_URL=redis://:password@redis.example.com:6379/1
```

---

## Rate Limiting Strategy

### Login Endpoint
```python
@bp.route("/login/", methods=['POST'])
@limiter.limit("5 per minute")
def login_post():
    # Already implemented
```

### Password Reset
```python
@bp.route('/password-reset', methods=['POST'])
@limiter.limit("3 per hour")
def password_reset():
    # Already implemented
```

### API Endpoints
```python
@bp.route("/api/v1/search", methods=['GET'])
@login_required
@limiter.limit("30 per minute")
def api_search_books():
    # Add this limit
```

### Registration
```python
@bp.route('/register', methods=['POST'])
@limiter.limit("5 per hour")
def register():
    # Add this limit
```

---

## Monitoring

### Check Redis Status

```bash
# Connect to Redis
redis-cli

# Get info
info
DBSIZE
KEYS *

# Monitor live commands
MONITOR

# Exit
EXIT
```

### Monitor Rate Limits

```python
# Debug script
import redis
r = redis.Redis(host='localhost', port=6379, db=1, decode_responses=True)

# See all rate limit keys
for key in r.scan_iter("LIMITER_*"):
    print(f"{key}: {r.ttl(key)}s remaining")
```

---

## High Availability Setup (Optional)

### Redis Sentinel (Failover)

```bash
# Install Sentinel
sudo apt-get install redis-sentinel

# Configure /etc/redis/sentinel.conf
port 26379
sentinel monitor libriya-redis 127.0.0.1 6379 2
sentinel down-after-milliseconds libriya-redis 5000
sentinel failover-timeout libriya-redis 10000
sentinel parallel-syncs libriya-redis 1
```

### Redis Cluster (Sharding)

For very high-traffic applications, consider Redis Cluster:

```bash
# Create cluster with 3 masters + 3 replicas
redis-server --port 7000 --cluster
redis-server --port 7001 --cluster
redis-server --port 7002 --cluster
redis-server --port 7003 --cluster-replica-of-port 7000
redis-server --port 7004 --cluster-replica-of-port 7001
redis-server --port 7005 --cluster-replica-of-port 7002
```

---

## Troubleshooting

### Connection Refused

```bash
# Check if Redis is running
sudo systemctl status redis-server

# Check if port is listening
netstat -tulpn | grep 6379

# Restart Redis
sudo systemctl restart redis-server
```

### Authentication Failed

```bash
# Check password in Redis config
sudo grep requirepass /etc/redis/redis.conf

# Or in Docker logs
docker logs libriya-redis
```

### Memory Issues

```bash
# Check Redis memory usage
redis-cli info memory

# Set max memory policy (optional, edit redis.conf)
maxmemory 256mb
maxmemory-policy allkeys-lru  # Evict least recently used keys
```

### Performance Issues

```bash
# Monitor latency
redis-cli --latency

# Check slow queries
redis-cli slowlog get 10
```

---

## Backup & Recovery

### Backup Redis Data

```bash
# Manual backup (creates dump.rdb)
redis-cli BGSAVE

# Copy backup file
cp /var/lib/redis/dump.rdb /backup/redis_$(date +%Y%m%d).rdb
```

### Restore from Backup

```bash
# Stop Redis
sudo systemctl stop redis-server

# Restore backup
cp /backup/redis_20240101.rdb /var/lib/redis/dump.rdb

# Start Redis
sudo systemctl start redis-server
```

---

## Security Best Practices

### 1. Password Protection
```bash
# In redis.conf
requirepass your_very_secure_password_here_min_32_chars
```

### 2. Network Isolation
```bash
# Only allow local connections
bind 127.0.0.1

# Or limit to specific network
bind 10.0.0.5  # Internal network only
```

### 3. Firewall Rules
```bash
sudo ufw allow from 10.0.0.0/8 to any port 6379
```

### 4. Disable Dangerous Commands
```bash
# In redis.conf
rename-command FLUSHDB ""
rename-command FLUSHALL ""
rename-command KEYS ""
```

### 5. ACL (Redis 6+)
```bash
redis-cli
> ACL SETUSER default on >password +@all ~*
> ACL SETUSER app_user on >app_password +@read +@write ~LIMITER_* ~*
> ACL SAVE
```

---

## Docker Compose (Full Stack)

```yaml
version: '3.9'

services:
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    command: redis-server --requirepass libriya_password --appendonly yes
    volumes:
      - redis_data:/data
    networks:
      - libriya_network
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 5

  mysql:
    image: mariadb:11
    environment:
      MYSQL_ROOT_PASSWORD: root_password
      MYSQL_DATABASE: libriya_db
      MYSQL_USER: libriya_user
      MYSQL_PASSWORD: libriya_password
    ports:
      - "3306:3306"
    volumes:
      - mysql_data:/var/lib/mysql
    networks:
      - libriya_network

  libriya:
    build: .
    ports:
      - "5000:5000"
    environment:
      FLASK_ENV: production
      DATABASE_URL: mysql+pymysql://libriya_user:libriya_password@mysql:3306/libriya_db
      REDIS_URL: redis://:libriya_password@redis:6379/1
    depends_on:
      - redis
      - mysql
    networks:
      - libriya_network

volumes:
  redis_data:
  mysql_data:

networks:
  libriya_network:
```

Usage:
```bash
docker-compose up -d
```

---

## Performance Tuning

### Redis Configuration (redis.conf)

```conf
# Memory management
maxmemory 256mb
maxmemory-policy allkeys-lru

# AOF (Append Only File) persistence
appendonly yes
appendfsync everysec

# TCP keepalive
tcp-keepalive 300

# Slowlog
slowlog-log-slower-than 10000
slowlog-max-len 128

# Client timeout
timeout 0
```

---

## Verification Checklist

- [ ] Redis installed and running
- [ ] Redis port accessible (6379)
- [ ] Password configured (if required)
- [ ] redis-py library installed
- [ ] RATELIMIT_STORAGE_URL configured in .env
- [ ] Limiter initialized with Redis backend
- [ ] Rate limiting tested on login endpoint
- [ ] Rate limiting tested on password reset
- [ ] Backup procedure documented
- [ ] Monitoring script created
- [ ] Firewall rules configured
- [ ] Redis secured (password, bind, ACL)

---

**Status**: Ready for Production Redis Setup ✅

