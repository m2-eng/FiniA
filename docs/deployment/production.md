# Production Deployment Guide

Comprehensive guide for deploying FiniA in production environments with security, performance, and reliability considerations.

## Overview

This guide covers:
- ✅ Reverse proxy setup (nginx)
- ✅ SSL/TLS configuration
- ✅ Security hardening
- ✅ Resource limits
- ✅ Monitoring & health checks
- ✅ Backup strategies
- ✅ High availability

## Architecture

**Production Stack:**
```
                        Internet
                           │
                           ↓
                    ┌──────────────┐
                    │  Firewall    │
                    │  (443, 80)   │
                    └──────┬───────┘
                           │
                           ↓
                    ┌──────────────┐
                    │    nginx     │
                    │  Reverse     │
                    │   Proxy      │
                    └──────┬───────┘
                           │
                    ┌──────┴───────┐
                    │              │
            ┌───────▼──────┐  ┌───▼────────┐
            │ FiniA API    │  │  Static    │
            │ (FastAPI)    │  │  Files     │
            │ Port 8000    │  │            │
            └──────┬───────┘  └────────────┘
                   │
            ┌──────▼───────────┐
            │ External MySQL   │
            │ (finiaDB_users)  │
            └──────────────────┘
```

## nginx Reverse Proxy

### Basic Configuration

**File:** `nginx.conf` (provided in project root)

**Key Features:**
- SSL/TLS termination
- Rate limiting
- Security headers
- Static file serving
- WebSocket support (if needed)

### Installation

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install nginx
```

**CentOS/RHEL:**
```bash
sudo yum install nginx
```

**Docker Compose (included):**
```yaml
services:
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./ssl:/etc/nginx/ssl:ro
    depends_on:
      - api
```

---

### nginx Configuration Explained

**Rate Limiting Zones:**
```nginx
# General API rate limit: 10 requests/second per IP
limit_req_zone $binary_remote_addr zone=api_limit:10m rate=10r/s;

# Login rate limit: 5 requests/minute per IP
limit_req_zone $binary_remote_addr zone=login_limit:10m rate=5r/m;
```

**Upstream (FiniA API):**
```nginx
upstream finia_api {
    server api:8000;  # Docker service name
    # Or for non-Docker:
    # server 127.0.0.1:8000;
}
```

**Main Server Block:**
```nginx
server {
    listen 80;
    server_name finia.example.com;
    
    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "no-referrer-when-downgrade" always;
    
    # Proxy headers
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    
    # Root path - proxy to API (static files served by FastAPI)
    location / {
        proxy_pass http://finia_api;
        proxy_read_timeout 60s;
        proxy_connect_timeout 60s;
    }
    
    # API endpoints with rate limiting
    location /api/ {
        limit_req zone=api_limit burst=20 nodelay;
        proxy_pass http://finia_api;
    }
    
    # Login endpoint with stricter rate limiting
    location /api/auth/login {
        limit_req zone=login_limit burst=5 nodelay;
        proxy_pass http://finia_api;
    }
}
```

---

## SSL/TLS Configuration

### Obtain SSL Certificate

**Option 1: Let's Encrypt (Free, Automated)**

```bash
# Install Certbot
sudo apt install certbot python3-certbot-nginx

# Generate certificate
sudo certbot --nginx -d finia.example.com

# Auto-renewal (check cron)
sudo certbot renew --dry-run
```

**Option 2: Commercial Certificate**
- Purchase from certificate authority
- Place files in `/etc/nginx/ssl/`

**Option 3: Self-Signed (Testing Only)**
```bash
sudo openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout /etc/nginx/ssl/finia.key \
  -out /etc/nginx/ssl/finia.crt
```

---

### SSL Server Block

**nginx configuration:**

```nginx
# HTTP to HTTPS redirect
server {
    listen 80;
    server_name finia.example.com;
    return 301 https://$host$request_uri;
}

# HTTPS server
server {
    listen 443 ssl http2;
    server_name finia.example.com;
    
    # SSL certificates
    ssl_certificate /etc/letsencrypt/live/finia.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/finia.example.com/privkey.pem;
    
    # SSL configuration (Mozilla Modern)
    ssl_protocols TLSv1.3 TLSv1.2;
    ssl_ciphers 'ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384';
    ssl_prefer_server_ciphers off;
    
    # SSL session cache
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;
    
    # OCSP stapling
    ssl_stapling on;
    ssl_stapling_verify on;
    ssl_trusted_certificate /etc/letsencrypt/live/finia.example.com/chain.pem;
    
    # HSTS (HTTP Strict Transport Security)
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    
    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "no-referrer-when-downgrade" always;
    
    # Content Security Policy
    add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data:;" always;
    
    # Proxy configuration
    location / {
        proxy_pass http://finia_api;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 60s;
        proxy_connect_timeout 60s;
    }
    
    # API rate limiting
    location /api/ {
        limit_req zone=api_limit burst=20 nodelay;
        proxy_pass http://finia_api;
    }
    
    # Login rate limiting
    location /api/auth/login {
        limit_req zone=login_limit burst=5 nodelay;
        proxy_pass http://finia_api;
    }
}
```

**Test Configuration:**
```bash
sudo nginx -t
sudo systemctl reload nginx
```

**Verify SSL:**
```bash
curl -I https://finia.example.com
# Check for HTTPS 200 response and security headers
```

---

## Security Hardening

### 1. CORS Configuration

**Development (allow all):**
```python
# src/api/main.py
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # ⚠️ DEVELOPMENT ONLY
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**Production (specific origins):**
```python
# src/api/main.py
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://finia.example.com",
        "https://www.finia.example.com"
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)
```

---

### 2. Secret Management

**DO NOT hardcode secrets in code!**

**Option 1: Environment Variables**

```yaml
# docker-compose.yml
services:
  api:
    environment:
      - DB_HOST=${DB_HOST}
      - DB_PORT=${DB_PORT}
      - JWT_SECRET=${JWT_SECRET}
      - FERNET_KEY=${FERNET_KEY}
```

**Option 2: Docker Secrets**

```yaml
# docker-compose.yml
services:
  api:
    secrets:
      - db_password
      - jwt_secret

secrets:
  db_password:
    external: true
  jwt_secret:
    external: true
```

**Create secrets:**
```bash
echo "your-db-password" | docker secret create db_password -
echo "your-jwt-secret" | docker secret create jwt_secret -
```

**Option 3: External Secret Manager**
- AWS Secrets Manager
- Azure Key Vault
- HashiCorp Vault

---

### 3. Database Security

**Create dedicated database user:**
```sql
-- MySQL/MariaDB
CREATE USER 'finia_app'@'%' IDENTIFIED BY 'strong-password';

-- Grant per-user database pattern
GRANT ALL PRIVILEGES ON `finiaDB_%`.* TO 'finia_app'@'%';

-- Revoke global privileges
REVOKE ALL PRIVILEGES, GRANT OPTION FROM 'finia_app'@'%';

FLUSH PRIVILEGES;
```

**Connection encryption:**
```yaml
# cfg/config.yaml
database:
  host: db.example.com
  port: 3306
  ssl: true
  ssl_ca: /path/to/ca-cert.pem
```

**Firewall rules:**
```bash
# Only allow FiniA API server to access database
sudo ufw allow from 192.168.1.10 to any port 3306
sudo ufw deny 3306
```

---

### 4. File System Permissions

**Docker:**
```dockerfile
# Dockerfile
RUN addgroup --gid 1000 appgroup && \
    adduser --uid 1000 --gid 1000 --disabled-password appuser

USER appuser
```

**Linux Host:**
```bash
# Create dedicated user
sudo useradd -r -s /bin/false finia

# Set ownership
sudo chown -R finia:finia /opt/finia

# Restrict permissions
chmod 750 /opt/finia
chmod 640 /opt/finia/cfg/*.yaml
```

---

### 5. Rate Limiting

**API-Level (FastAPI):**

```python
# src/api/main.py
from fastapi import Request
from fastapi.responses import JSONResponse
import time

# Rate limiting middleware
rate_limit_storage = {}

@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    client_ip = request.client.host
    current_time = time.time()
    
    if client_ip in rate_limit_storage:
        requests, window_start = rate_limit_storage[client_ip]
        
        # Reset window every 60 seconds
        if current_time - window_start > 60:
            rate_limit_storage[client_ip] = (1, current_time)
        else:
            # Max 100 requests per minute
            if requests >= 100:
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Too many requests"}
                )
            rate_limit_storage[client_ip] = (requests + 1, window_start)
    else:
        rate_limit_storage[client_ip] = (1, current_time)
    
    response = await call_next(request)
    return response
```

**Note:** Built-in login rate limiting exists in `auth/rate_limiter.py` (5 failed attempts → 15-minute lockout).

---

## Resource Limits

### Docker Resource Constraints

```yaml
# docker-compose.yml
services:
  api:
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 2G
        reservations:
          cpus: '0.5'
          memory: 512M
    restart: unless-stopped
    ulimits:
      nofile:
        soft: 65536
        hard: 65536
```

---

### System Limits (systemd)

```ini
# /etc/systemd/system/finia.service
[Unit]
Description=FiniA API
After=network.target

[Service]
Type=simple
User=finia
Group=finia
WorkingDirectory=/opt/finia
ExecStart=/opt/finia/.venv/bin/python src/main.py
Restart=on-failure

# Resource limits
LimitNOFILE=65536
MemoryLimit=2G
CPUQuota=200%

[Install]
WantedBy=multi-user.target
```

**Enable service:**
```bash
sudo systemctl daemon-reload
sudo systemctl enable finia
sudo systemctl start finia
```

---

## Monitoring & Health Checks

### Health Check Endpoint

**Built-in:** GET `/api/health`

**Response:**
```json
{
  "status": "healthy",
  "service": "FiniA API",
  "version": "1.0.0"
}
```

---

### Docker Health Check

```yaml
# docker-compose.yml
services:
  api:
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
```

**Check status:**
```bash
docker inspect --format='{{.State.Health.Status}}' finia-api
```

---

### Monitoring Script

**File:** `scripts/health_check.py`

```python
#!/usr/bin/env python3
import requests
import sys

def check_health():
    try:
        response = requests.get('http://localhost:8000/api/health', timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data.get('status') == 'healthy':
                print("✅ FiniA API is healthy")
                return 0
        print("❌ FiniA API unhealthy")
        return 1
    except Exception as e:
        print(f"❌ Health check failed: {e}")
        return 1

if __name__ == '__main__':
    sys.exit(check_health())
```

**Cron job:**
```bash
# /etc/cron.d/finia-health
*/5 * * * * finia /opt/finia/scripts/health_check.py
```

---

### Log Monitoring

**Docker logs:**
```bash
docker-compose logs -f api
```

**systemd logs:**
```bash
journalctl -u finia -f
```

**Log rotation:**
```bash
# /etc/logrotate.d/finia
/var/log/finia/*.log {
    daily
    rotate 14
    compress
    delaycompress
    notifempty
    create 0640 finia finia
    sharedscripts
    postrotate
        systemctl reload finia
    endscript
}
```

---

### Performance Metrics

**Track:**
- Request latency
- Error rates (4xx, 5xx)
- Database query times
- Import processing times
- Memory/CPU usage

**Tools:**
- **Prometheus + Grafana** - Metrics visualization
- **ELK Stack** - Log aggregation
- **Sentry** - Error tracking
- **New Relic / DataDog** - APM

---

## Backup Strategy

### Database Backups

**See:** [Backup Documentation](../backup.md)

**Automated daily backup:**
```bash
#!/bin/bash
# /opt/finia/scripts/backup.sh

DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/backups/finia"
DB_HOST="db.example.com"
DB_USER="backup_user"
DB_PASS="backup_password"

# Backup all finiaDB_* databases
for db in $(mysql -h $DB_HOST -u $DB_USER -p$DB_PASS -N -e "SHOW DATABASES LIKE 'finiaDB_%'"); do
    echo "Backing up $db..."
    mysqldump -h $DB_HOST -u $DB_USER -p$DB_PASS $db | gzip > "$BACKUP_DIR/${db}_${DATE}.sql.gz"
done

# Cleanup old backups (keep 30 days)
find $BACKUP_DIR -name "*.sql.gz" -mtime +30 -delete

echo "Backup completed: $DATE"
```

**Cron:**
```bash
# Daily at 2 AM
0 2 * * * /opt/finia/scripts/backup.sh
```

---

### Configuration Backups

**Include in version control (without secrets):**
```bash
# Backup cfg/ folder (sanitized)
cp cfg/config.yaml.example cfg/config.yaml.backup
cp cfg/data.yaml cfg/data.yaml.backup
cp cfg/import_formats.yaml cfg/import_formats.yaml.backup

# Store in Git
git add cfg/*.backup
git commit -m "Backup configuration templates"
```

**Offsite backups:**
- S3 / Cloud Storage
- SFTP server
- Network-attached storage (NAS)

---

## High Availability

### Load Balancing

**nginx upstream with multiple API instances:**

```nginx
upstream finia_api {
    least_conn;  # Load balancing method
    server api1:8000 max_fails=3 fail_timeout=30s;
    server api2:8000 max_fails=3 fail_timeout=30s;
    server api3:8000 max_fails=3 fail_timeout=30s;
}
```

**Docker Swarm:**
```bash
docker service create \
  --name finia-api \
  --replicas 3 \
  --publish 8000:8000 \
  finia:latest
```

**Kubernetes:**
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: finia-api
spec:
  replicas: 3
  selector:
    matchLabels:
      app: finia-api
  template:
    metadata:
      labels:
        app: finia-api
    spec:
      containers:
      - name: api
        image: finia:latest
        ports:
        - containerPort: 8000
```

---

### Database Replication

**Master-Slave setup:**

```sql
-- Master (write)
CREATE USER 'repl'@'%' IDENTIFIED BY 'replication-password';
GRANT REPLICATION SLAVE ON *.* TO 'repl'@'%';

-- Slave (read)
CHANGE MASTER TO
  MASTER_HOST='master-db.example.com',
  MASTER_USER='repl',
  MASTER_PASSWORD='replication-password',
  MASTER_LOG_FILE='mysql-bin.000001',
  MASTER_LOG_POS=107;

START SLAVE;
```

**Connection pooling:**
- Read operations → Slave
- Write operations → Master
- FiniA uses single database class (extend for master/slave routing)

---

## Deployment Workflows

### Docker Compose Production

**1. Prepare configuration:**
```bash
cp docker-compose.override.yml.example docker-compose.override.yml
# Edit override with production values
```

**2. Build and start:**
```bash
docker-compose -f docker-compose.yml -f docker-compose.override.yml up -d --build
```

**3. Verify:**
```bash
docker-compose ps
docker-compose logs -f api
curl http://localhost:8000/api/health
```

---

### Zero-Downtime Updates

**Rolling update:**

```bash
# Build new image
docker-compose build api

# Update service (one container at a time)
docker-compose up -d --no-deps --build api

# Verify health
docker-compose exec api curl http://localhost:8000/api/health
```

---

### Blue-Green Deployment

**Setup:**
```bash
# Blue (current)
docker-compose -p finia-blue up -d

# Green (new version)
docker-compose -p finia-green up -d

# Switch nginx upstream
# Update nginx.conf: server blue:8000 → server green:8000
sudo nginx -s reload

# Cleanup old version
docker-compose -p finia-blue down
```

---

## Troubleshooting Production Issues

### High CPU Usage

**Check:**
```bash
docker stats finia-api
top
htop
```

**Solutions:**
- Increase resource limits
- Optimize database queries
- Add caching (Redis)
- Scale horizontally

---

### Memory Leaks

**Monitor:**
```bash
docker stats --no-stream finia-api
```

**Solutions:**
- Restart service regularly (systemd timer)
- Review connection pooling
- Check for unclosed database cursors

---

### Database Connection Issues

**Check:**
```bash
# Test connection from container
docker exec -it finia-api mysql -h db.example.com -u finia_app -p

# Check firewall
sudo ufw status
```

**Solutions:**
- Verify database credentials
- Check network connectivity
- Review connection pool settings
- Increase MySQL max_connections

---

### SSL Certificate Expiration

**Check expiration:**
```bash
sudo certbot certificates
```

**Manual renewal:**
```bash
sudo certbot renew --force-renewal
sudo systemctl reload nginx
```

---

## See Also

- [Docker Documentation](../docker/docker.md) - Container deployment
- [nginx Configuration](../../nginx.conf) - Full reverse proxy config
- [Backup Strategy](../backup.md) - Database backup procedures
- [API Documentation](../api.md) - REST API endpoints
- [Authentication](../authentication.md) - Security architecture
