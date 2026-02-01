# FiniA

FiniA is a lightweight personal finance assistant with a FastAPI backend, web UI, and CSV import with duplicate detection.

## Quickstart (local)
- Requirements: Python 3.10+, MySQL/MariaDB.
- Install dependencies (recommended venv):
```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```
- Adjust database and import paths in `cfg/config.yaml` and `cfg/data.yaml`.
- Create schema and seed data:
```bash
python src/main.py --setup --init-database --user <db_user> --password <db_pass> --config cfg/config.yaml
```
- Start API and web UI (login uses DB credentials, in-memory sessions):
```bash
python src/main.py --api --host 127.0.0.1 --port 8000 --config cfg/config.yaml
```
  - Web UI: http://127.0.0.1:8000/
  - API docs: http://127.0.0.1:8000/api/docs
- Trigger CSV import from paths defined in `cfg/data.yaml`:
```bash
python src/main.py --import-account-data --user <db_user> --password <db_pass> --config cfg/config.yaml
```

## Quickstart (Docker)
- Requirements: Docker and Docker Compose; external MySQL/MariaDB.
- Adjust database host in `cfg/config.yaml` (e.g., `host: db.example.com` or host IP).
- For local/non-standard setups, copy `docker-compose.override.yml.example` → `docker-compose.override.yml` to customize port mappings, volumes, or environment variables (especially for Synology or port conflicts).
- Start the API container:
```bash
docker-compose up -d
```
- Access the web UI: http://localhost:8000/
- Check logs: `docker-compose logs -f api`
- Stop: `docker-compose down`

**Note**: The container uses an external database defined in `cfg/config.yaml`; no embedded DB service is included. Override file is typically needed only for non-standard environments (Synology, port conflicts, etc.).

## Documentation

### Getting Started
- [Getting Started Guide](docs/tutorials/getting_started.md) – Your first steps with FiniA, account setup, dashboard overview
- [Quick Reference: Import CSV Data](docs/import/csv_import.md) – CSV format requirements, import process, troubleshooting

### Architecture & Technical Design
- [Repository Pattern & Data Access](docs/architecture/repositories.md) – 13 repositories, BaseRepository, Unit of Work pattern, usage examples, testing strategies
- [Services Layer & Import Pipeline](docs/architecture/services.md) – AccountDataImporter, CategoryAutomation, ImportService, 5 import steps, dependency diagram

### Features & User Guides
- [Planning & Budgeting System](docs/features/planning.md) – Recurring budgets, planning cycles, entry generation, integration with year overview
- [Share Portfolio Management](docs/features/shares.md) – Securities tracking, transactions (buy/sell/dividend), portfolio valuations, performance analysis
- [Category Automation Rules](docs/features/category_automation.md) – Automatic categorization, rule matching types, condition logic, rule testing

### Configuration & Operations
- [Application Configuration](cfg/config.yaml) – Database connection, API settings, logging
- [Data Import Formats](cfg/data.yaml) – CSV source definitions, import paths, field mappings
- [Import Format Definitions](cfg/import_formats.yaml) – Detailed import format specifications

### Production & Deployment
- [Production Deployment Guide](docs/deployment/production.md) – Security hardening, database optimization, backup strategies, monitoring, SSL/TLS setup
- [Docker Deployment](docs/docker/docker.md) – Container configuration, volume management, networking, health checks

### Development
- [Development Setup Guide](docs/development/setup.md) – Local Python environment, Docker development, VS Code configuration, debugging (backend/frontend), code quality, Git workflow, common tasks
- [Database Schema Reference](docs/database/schema.md) – 15 tables, 6 views, ERD, key relationships, data integrity constraints

## Project layout
- `cfg/`: Configuration (DB, data paths, import formats)
- `db/`: SQL dump for schema
- `src/main.py`: CLI entry and API start
- `src/api/`: FastAPI routers and middleware
- `src/services/` and `src/repositories/`: Business logic and data access
- `src/web/`: Static frontend
- `test/data/`: Sample and test data

## Security
- Do not commit passwords or secrets; use local `cfg/` files or environment variables.
- Database operations require explicit `--user` and `--password` for setup/imports.

## License
AGPL-3.0, see `LICENSE`.
