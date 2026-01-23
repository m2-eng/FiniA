# Getting Started with Docker

Step-by-step guide for beginners to deploy FiniA with Docker.

## Prerequisites

- [ ] Docker Desktop installed and running ([download](https://www.docker.com/products/docker-desktop))
- [ ] Project cloned or downloaded
- [ ] External MySQL/MariaDB available (host, port, user credentials)

## Setup checklist

### 1. Prepare configuration

- [ ] Open project directory: `cd C:\...\FiniA` (or your path)
- [ ] Edit database connection in `cfg/config.yaml`:
  ```yaml
  database:
    host: 192.168.x.x  # Your DB server IP
    port: 3306
    name: your_db_name
  ```
- [ ] Save and close

### 2. Build and start

- [ ] Open PowerShell in project directory
- [ ] Run: `docker-compose up -d`
- [ ] Wait 10-15 seconds for startup

### 3. Verify

- [ ] Check container status: `docker-compose ps`
  - Should show `finia-api` running
- [ ] Open browser: http://localhost:8000
  - Should load FiniA web UI
- [ ] Check API docs: http://localhost:8000/api/docs
  - Should show Swagger UI

### 4. First login

- [ ] Use your MySQL credentials:
  - Username: your DB username
  - Password: your DB password
- [ ] System creates database: `finiaDB_<username>` on first login

## Common issues

**"Container won't start"**
```bash
docker-compose logs api
# Check for errors
```

**"Can't connect to web UI"**
- Check firewall settings (allow port 8000)
- Verify Docker Desktop is running
- Wait a bit longer (first start takes ~30 seconds)

**"Login fails"**
- Verify MySQL credentials are correct
- Check if external database is reachable from Docker
- Ensure database server allows connections from Docker host

**"Port 8000 already in use"**
- Create `docker-compose.override.yml`:
  ```yaml
  services:
    api:
      ports:
        - "8001:8000"  # Use port 8001 instead
  ```
- Restart: `docker-compose down && docker-compose up -d`

## Daily usage

**Start:**
```bash
docker-compose up -d
```

**Stop:**
```bash
docker-compose down
```

**View logs:**
```bash
docker-compose logs -f api
```

**Restart after config changes:**
```bash
docker-compose restart api
```

## Next steps

- [ ] Set up CSV import paths in `cfg/data.yaml`
- [ ] Configure import formats in `cfg/import_formats.yaml`
- [ ] Import initial data: `docker exec -it finia-api python3 src/main.py --setup --init-database --user <user> --password <pass>`
- [ ] See full documentation: [docs/docker.md](../docker.md)

## Synology NAS deployment

Step-by-step guide for running FiniA on Synology Container Manager.

### Prerequisites

- [ ] Synology NAS with Container Manager installed
- [ ] SSH access enabled or DSM File Station access
- [ ] External MySQL/MariaDB database accessible from NAS
- [ ] Project files copied to NAS (e.g., `/volume1/docker/FiniA/`)

### Setup steps

**1. Create override file**

Choose one method:

**Option A - DSM File Station (beginner-friendly):**
- [ ] DSM → File Station → navigate to `/docker/FiniA/`
- [ ] Right-click `docker-compose.override.yml.example` → Copy
- [ ] Rename copy to `docker-compose.override.yml`
- [ ] Right-click `docker-compose.override.yml` → Edit with Text Editor

**Option B - SSH:**
```bash
cd /volume1/docker/FiniA
cp docker-compose.override.yml.example docker-compose.override.yml
vi docker-compose.override.yml  # or nano
```

**2. Edit override file**

Adjust Synology paths and ports:
```yaml
services:
  api:
    ports:
      - "8000:8000"  # Change if port conflict (e.g., 8001:8000)
    volumes:
      - /volume1/docker/FiniA/cfg:/app/cfg:ro
```

- [ ] Replace `/volume1/docker/FiniA/cfg` with your actual path
- [ ] Save and close

**3. Configure database**

Edit `cfg/config.yaml` on NAS:
```yaml
database:
  host: 192.168.x.x  # Your DB server IP
  port: 3306
  name: your_db_name
```

**4. Deploy in Container Manager**

- [ ] Open Container Manager → Projects → Create
- [ ] Select project path: `/docker/FiniA` (or your path)
- [ ] Upload both files: `docker-compose.yml` and `docker-compose.override.yml`
- [ ] Click "Deploy" → Container Manager merges files automatically
- [ ] Wait for "Running" status

**5. Verify**

- [ ] Check container logs: Container Manager → Project → View logs
- [ ] Open web UI: `http://<NAS_IP>:8000`
- [ ] Test login with MySQL credentials

### Update workflow

**After git pull:**
- [ ] Only `docker-compose.yml` is updated
- [ ] Your `docker-compose.override.yml` stays unchanged
- [ ] In Container Manager → Redeploy project (or SSH: `docker-compose up -d`)

### Common Synology issues

**"Volume not mounted"**
- Check path exists on NAS: `/volume1/docker/FiniA/cfg`
- Verify override file is uploaded in Container Manager project
- Validate YAML syntax (no tabs, proper indentation)

**"Port conflict"**
- Change host port in override: `"8001:8000"`
- Redeploy project

**"Override not applied"**
- Ensure both files are listed in Container Manager project
- Via SSH: `docker-compose config` to check merged output

## Need help?

- Full Docker documentation: [docker.md](docker.md)
- Configuration guide: [../config.md](../config.md)
- Backup strategy: [../backup.md](../backup.md)
