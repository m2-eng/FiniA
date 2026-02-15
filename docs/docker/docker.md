# Docker Container Implementation

FiniA provides Docker containers for easy deployment with all dependencies bundled. The implementation uses external MySQL/MariaDB (no embedded database container) and supports both local development and production environments.

## Architecture

```
Docker Host
├── finia-api (FastAPI application)
│   ├── Port: 8000
│   ├── Config: /app/cfg (copied at build time)
│   └── User: appuser (UID 1000, non-root)
└── External MySQL/MariaDB
    ├── Host: configured in cfg/config.yaml
    └── Per-user databases: finiaDB_<username>
```

## Container Image

**Base:** Python 3.11-slim (Debian-based)  
**Build:** Multi-stage for optimized size  
**User:** Non-root (appuser, UID 1000)  
**Health check:** HTTP GET to `/api/docs` every 30s

### Dockerfile highlights

```dockerfile
# System dependencies: gcc, mysql client libraries
# Python dependencies: installed from requirements.txt
# Application code: src/ directory
# Config: cfg/ copied at build time (Windows path issues)
# Exposed port: 8000
# Default command: python3 src/main.py
```

See [Dockerfile](Dockerfile) for full implementation.

## docker-compose.yml

Orchestrates the API service with external database connection:

```yaml
services:
  api:
    build: .
    container_name: finia-api
    ports:
      - "8000:8000"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/docs"]
      interval: 30s
      timeout: 10s
      retries: 3
    restart: unless-stopped
    command: >
      python3 src/main.py
```

**Note:** No embedded database service; uses external MySQL/MariaDB configured in `cfg/config.yaml`.

### Optional setup protection

If you want to protect `/api/setup` in Docker, pass a token via environment
variable (recommended) and set `allow_localhost: false` in `cfg/config.yaml`:

```yaml
services:
  api:
    environment:
      - FINIA_SETUP_TOKEN=changeme
```

## Configuration mounting

**Windows/Docker Desktop:**  
Config is copied into the image at build time (`COPY cfg/ ./cfg/` in Dockerfile) due to path translation issues with volume mounts.

**Linux/Mac/Synology (optional):**  
Can use volume mounts for live config updates via `docker-compose.override.yml`:
```yaml
services:
  api:
    volumes:
      - ./cfg:/app/cfg:ro
```

See [docs/config_and_volumes.md](config_and_volumes.md) for details.

## docker-compose.override.yml

For local/Synology deployments, copy the example:
```bash
cp docker-compose.override.yml.example docker-compose.override.yml
```

Edit to customize:
- Port mappings (e.g., `8001:8000` to avoid conflicts)
- Volume paths (e.g., `/volume1/docker/FiniA/cfg:/app/cfg:ro` for Synology)
- Environment variables (optional)

Override files are merged automatically by docker-compose and stay local (not tracked by Git).

## Deployment automation

### docker-deploy.ps1 (PowerShell)

Automation script for Windows:

| Command | Action |
|---------|--------|
| `.\docker-deploy.ps1 build` | Build image |
| `.\docker-deploy.ps1 up` | Start services |
| `.\docker-deploy.ps1 down` | Stop services |
| `.\docker-deploy.ps1 logs` | Follow logs |
| `.\docker-deploy.ps1 restart` | Restart services |
| `.\docker-deploy.ps1 clean` | Clean up resources |
| `.\docker-deploy.ps1 backup` | Backup database |
| `.\docker-deploy.ps1 restore <file>` | Restore backup |

### Makefile (Linux/Mac)

```bash
make build       # Build image
make up          # Start services
make down        # Stop services
make logs        # Follow logs
make backup      # Backup database
make help        # Show all commands
```

## Security considerations

**Implemented:**
- Non-root user (UID 1000) inside container
- No hardcoded secrets (config uses placeholders)
- Read-only config mounts (where applicable)
- Health checks for auto-recovery
- In-memory authentication (no credential persistence)

**Required for production:**
- SSL/TLS via reverse proxy (see nginx.conf)
- Specific CORS origins (not wildcard)
- Resource limits (CPU/memory)
- Log rotation
- Regular security updates

## Common operations

**Start for first time:**
```bash
# Adjust database host in cfg/config.yaml
docker-compose up -d
# Access: http://localhost:8000
```

**Update after code changes (Windows):**
```bash
docker-compose build
docker-compose up -d
```

**Update config (Linux with volume mount):**
```bash
# Edit cfg/config.yaml or cfg/import_formats.yaml
docker-compose restart api
```

**View logs:**
```bash
docker-compose logs -f api
```

**Check container status:**
```bash
docker-compose ps
docker inspect finia-api
```

**Access container shell:**
```bash
docker exec -it finia-api /bin/sh
```

## Synology Container Manager

For Synology NAS deployments:

1. **Create override file:**
   - **Option A (DSM Text Editor):** DSM → File Station → navigate to `/docker/FiniA/` → right-click `docker-compose.override.yml.example` → Copy → rename to `docker-compose.override.yml` → right-click → Edit → adjust paths/ports
   - **Option B (SSH):** `cd /volume1/docker/FiniA && cp docker-compose.override.yml.example docker-compose.override.yml && vi docker-compose.override.yml`

2. **Edit override to set Synology paths:**
   ```yaml
   services:
     api:
       ports:
         - "8000:8000"  # Change if port conflict
       volumes:
         - /volume1/docker/FiniA/cfg:/app/cfg:ro
   ```

3. Container Manager UI → Projects → Create/Import
4. Upload both `docker-compose.yml` and `docker-compose.override.yml`
5. Deploy; Container Manager merges files automatically

**Update workflow:**
- `git pull` updates only `docker-compose.yml`
- `docker-compose.override.yml` stays unchanged
- Redeploy in Container Manager or via CLI

## Troubleshooting

**"Container won't start"**
```bash
docker-compose logs api
# Check for Python errors or missing config
```

**"Connection refused to database"**
- Verify `cfg/config.yaml` has correct database host/port
- Ensure external database is running and accessible
- Check firewall rules

**"Port 8000 already in use"**
- Change port in `docker-compose.override.yml`: `8001:8000`
- Or stop conflicting service

**"Config changes not reflected"**
- Windows: Rebuild image (`docker-compose build`)
- Linux with volume mount: Restart (`docker-compose restart api`)

## CI/CD integration

See [.github/workflows/docker-build.yml](.github/workflows/docker-build.yml) for automated Docker image builds on git push.
