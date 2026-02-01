# Development Setup

Comprehensive guide for setting up a complete FiniA development environment.

---

## Overview

This guide covers **Option 3: Comprehensive Development Environment** including:

- ✅ **Local Python Setup** - Virtual environment, dependencies
- ✅ **Docker Development** - Container setup with hot reload
- ✅ **IDE Configuration** - VS Code settings, extensions, debugging
- ✅ **Code Quality Tools** - Linting, formatting (planned)
- ✅ **Database Access** - Local and remote MySQL/MariaDB
- ✅ **Debugging** - Backend (Python) and frontend (Browser DevTools)
- ✅ **Git Workflow** - Branching, commits, pull requests

---

## Prerequisites

### Required Software

- **Python 3.10+** (3.11 recommended)
- **Git** for version control
- **MySQL/MariaDB** server (local or remote)
- **Docker** (optional, for containerized development)
- **Docker Compose** (optional)
- **VS Code** (recommended IDE)

### Optional Tools

- **MySQL Workbench** - Database management
- **Postman** - API testing
- **curl** - Command-line API testing

---

## Local Python Setup

### Step 1: Clone Repository

```bash
git clone https://github.com/m2-eng/FiniA.git
cd FiniA
```

---

### Step 2: Create Virtual Environment

**Windows (PowerShell):**
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

**Linux/macOS:**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

**Verify:**
```bash
python --version
# Should show: Python 3.10+ or 3.11+
```

---

### Step 3: Install Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

**Dependencies Installed:**
- `mysql-connector-python>=8.0.0` - MySQL database driver
- `pyyaml>=6.0.0` - YAML config parsing
- `fastapi>=0.109.0` - Web framework
- `uvicorn[standard]>=0.27.0` - ASGI server
- `pydantic>=2.5.0` - Data validation
- `python-multipart>=0.0.6` - File uploads
- `cryptography>=41.0.0` - Fernet encryption
- `pyjwt>=2.8.0` - JWT tokens

---

### Step 4: Configure Database

Edit `cfg/config.yaml`:

```yaml
database:
  host: 192.168.1.10      # Your MySQL server IP
  port: 3306
  name: placeholder       # Will be finiaDB_<username>
  user_table_prefix: finiaDB_  # Database prefix for per-user DBs
```

**Notes:**
- Each user gets their own database: `finiaDB_<username>`
- Database credentials provided at login (memory-only auth)
- No static credentials stored in config

---

### Step 5: Run Application

**Option A: Full Application (API + Web UI)**
```bash
python src/main.py --api --host 0.0.0.0 --port 8000
```

**Option B: API Only**
```bash
python src/main.py --api --host 127.0.0.1 --port 8000
```

**Option C: Setup Database (First Time)**
```bash
python src/main.py --setup --user root --password yourpassword
```

**Access:**
- Web UI: http://localhost:8000
- API Docs: http://localhost:8000/api/docs
- Redoc: http://localhost:8000/api/redoc

---

## Docker Development Setup

### Step 1: Docker Compose Configuration

**Default:** `docker-compose.yml`

```yaml
services:
  api:
    build: .
    ports:
      - "8000:8000"
    volumes:
      - ./src:/app/src              # Hot reload: source code
      - ./cfg:/app/cfg              # Hot reload: config files
      - ./web:/app/web              # Hot reload: frontend files
    environment:
      - PYTHONUNBUFFERED=1
    restart: unless-stopped
```

**Override:** Create `docker-compose.override.yml` for local customization:

```yaml
services:
  api:
    ports:
      - "8080:8000"  # Custom port
    environment:
      - DEBUG=1
      - LOG_LEVEL=DEBUG
```

---

### Step 2: Build and Run

```bash
# Build image
docker-compose build

# Start services
docker-compose up -d

# View logs
docker-compose logs -f api

# Stop services
docker-compose down
```

**Using Makefile:**
```bash
# Build
make build

# Start
make up

# Logs
make logs

# Stop
make down

# Restart
make restart

# Shell access
make shell
```

---

### Step 3: Hot Reload

**Volume Mounts:**
- `./src:/app/src` - Python code changes reload automatically
- `./cfg:/app/cfg` - Config changes require manual restart
- `./web:/app/web` - Frontend changes refresh in browser

**Restart on Config Change:**
```bash
docker-compose restart api
```

---

## VS Code Configuration

### Recommended Extensions

**Python Development:**
- `ms-python.python` - Python language support
- `ms-python.vscode-pylance` - Advanced IntelliSense
- `ms-python.debugpy` - Python debugging
- `njpwerner.autodocstring` - Docstring generator

**Web Development:**
- `esbenp.prettier-vscode` - Code formatter (JS/HTML/CSS)
- `dbaeumer.vscode-eslint` - JavaScript linting (if using)
- `ritwickdey.liveserver` - Live reload for HTML

**Docker:**
- `ms-azuretools.vscode-docker` - Docker management
- `ms-vscode-remote.remote-containers` - Dev containers

**Database:**
- `mtxr.sqltools` - SQL client
- `mtxr.sqltools-driver-mysql` - MySQL driver

**General:**
- `eamodio.gitlens` - Git history
- `ms-vsliveshare.vsliveshare` - Pair programming

---

### Workspace Settings

**Create:** `.vscode/settings.json`

```json
{
  "python.defaultInterpreterPath": "${workspaceFolder}/.venv/bin/python",
  "python.analysis.typeCheckingMode": "basic",
  "python.analysis.autoImportCompletions": true,
  "python.analysis.diagnosticMode": "workspace",
  "python.linting.enabled": false,
  "editor.formatOnSave": true,
  "editor.rulers": [120],
  "files.exclude": {
    "**/__pycache__": true,
    "**/*.pyc": true,
    ".venv": true
  },
  "files.watcherExclude": {
    "**/.venv/**": true,
    "**/node_modules/**": true
  }
}
```

---

### Launch Configuration (Debugging)

**Create:** `.vscode/launch.json`

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "FiniA API Server",
      "type": "debugpy",
      "request": "launch",
      "program": "${workspaceFolder}/src/main.py",
      "args": [
        "--api",
        "--host", "0.0.0.0",
        "--port", "8000"
      ],
      "console": "integratedTerminal",
      "justMyCode": false,
      "env": {
        "PYTHONUNBUFFERED": "1"
      }
    },
    {
      "name": "FiniA Setup Database",
      "type": "debugpy",
      "request": "launch",
      "program": "${workspaceFolder}/src/main.py",
      "args": [
        "--setup",
        "--user", "root",
        "--password", "${input:dbPassword}"
      ],
      "console": "integratedTerminal",
      "justMyCode": true
    },
    {
      "name": "Python: Current File",
      "type": "debugpy",
      "request": "launch",
      "program": "${file}",
      "console": "integratedTerminal",
      "justMyCode": true
    }
  ],
  "inputs": [
    {
      "id": "dbPassword",
      "type": "promptString",
      "description": "Enter MySQL root password",
      "password": true
    }
  ]
}
```

---

### Python Path Configuration

**Create:** `.vscode/.env`

```env
PYTHONPATH=${workspaceFolder}/src
```

---

## Debugging

### Backend (Python/FastAPI)

#### Debug API Server

1. Open `src/main.py` in VS Code
2. Press `F5` or Run → Start Debugging
3. Select "FiniA API Server" configuration
4. Set breakpoints by clicking left of line numbers
5. Access API: http://localhost:8000

**Breakpoint Example:**

```python
# src/api/routers/transactions.py
@router.get("/")
async def get_transactions(
    cursor = Depends(get_db_cursor)
):
    # Set breakpoint here ←
    repo = TransactionRepository(cursor)
    transactions = repo.get_all_transactions_paginated(page=1, page_size=50)
    return transactions  # Step through with F10
```

**Debug Actions:**
- `F5` - Continue
- `F10` - Step Over
- `F11` - Step Into
- `Shift+F11` - Step Out
- `Ctrl+Shift+F5` - Restart
- `Shift+F5` - Stop

---

#### Debug Console

**Access:** While debugging, use the Debug Console

```python
# Evaluate expressions
print(transactions)
len(transactions['transactions'])

# Inspect variables
cursor
repo
```

---

#### Logging

Add logging for debugging:

```python
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

@router.get("/")
async def get_transactions(...):
    logger.debug(f"Fetching transactions, page={page}, page_size={page_size}")
    ...
    logger.info(f"Returned {len(result['transactions'])} transactions")
```

---

### Frontend (Browser DevTools)

#### Open DevTools

- **Chrome/Edge:** `F12` or `Ctrl+Shift+I`
- **Firefox:** `F12` or `Ctrl+Shift+K`

#### Console Debugging

Add `console.log()` statements:

```javascript
// web/accounts.js
async function loadTransactions() {
    console.log("Loading transactions...");
    const response = await fetch('/api/transactions/');
    const data = await response.json();
    console.log("Transactions:", data);
    // ...
}
```

---

#### Network Tab

Monitor API requests:

1. Open Network tab
2. Filter: XHR/Fetch
3. Reload page or trigger action
4. Click request to see:
   - Request headers
   - Request payload
   - Response headers
   - Response body
   - Timing

---

#### Breakpoints

Set breakpoints in browser:

1. Open Sources tab
2. Find file (e.g., `web/accounts.js`)
3. Click line number to set breakpoint
4. Trigger action
5. Step through code

---

## Database Access

### MySQL Workbench

**Connect:**
1. Open MySQL Workbench
2. Create new connection:
   - Connection Name: FiniA Dev
   - Hostname: 192.168.1.10 (or localhost)
   - Port: 3306
   - Username: root (or your user)
3. Test Connection
4. Connect

**Browse Databases:**
- Per-user databases: `finiaDB_<username>`
- Select database to explore tables

---

### Command Line

```bash
# Connect to MySQL
mysql -h 192.168.1.10 -u root -p

# Use database
USE finiaDB_root;

# List tables
SHOW TABLES;

# Query data
SELECT * FROM tbl_transaction LIMIT 10;

# Exit
EXIT;
```

---

### VS Code SQLTools

**Setup:**
1. Install SQLTools + MySQL driver extensions
2. Create connection:
   - Driver: MySQL
   - Server: 192.168.1.10
   - Port: 3306
   - Database: finiaDB_root
   - Username: root
   - Password: ****
3. Connect
4. Browse tables and run queries

---

## Code Quality (Planned)

### Future Tools

**Linting:**
- `flake8` - PEP 8 style checker
- `pylint` - Comprehensive linter

**Formatting:**
- `black` - Opinionated code formatter
- `isort` - Import sorting

**Type Checking:**
- `mypy` - Static type checker

**Testing:**
- `pytest` - Unit testing framework
- `pytest-cov` - Coverage reporting

**Pre-commit Hooks:**
- `pre-commit` - Git hook framework

---

### Manual Code Review

**Current Best Practices:**

1. **Follow PEP 8:**
   - 4 spaces indentation
   - 120 character line length
   - Snake_case for functions/variables
   - PascalCase for classes

2. **Type Hints:**
```python
def get_transaction(transaction_id: int) -> dict | None:
    """Get transaction by ID."""
    ...
```

3. **Docstrings:**
```python
def insert_transaction(
    account_id: int,
    description: str,
    amount: Decimal,
    date_value: datetime
) -> int | None:
    """
    Insert transaction into database.
    
    Args:
        account_id: Account ID
        description: Transaction description
        amount: Transaction amount
        date_value: Transaction date
        
    Returns:
        Transaction ID if inserted, None otherwise
    """
    ...
```

---

## Git Workflow

### Branch Strategy

**Main Branches:**
- `main` - Production-ready code
- `issue/<number>-<description>` - Feature/bugfix branches

**Example:**
```bash
# Create feature branch
git checkout -b issue/54-improving-the-import-functionalities

# Make changes
git add src/services/account_data_importer.py
git commit -m "feat: add CSV header validation"

# Push branch
git push -u origin issue/54-improving-the-import-functionalities
```

---

### Commit Conventions

**Format:** `<type>: <subject>`

**Types:**
- `feat` - New feature
- `fix` - Bug fix
- `docs` - Documentation
- `style` - Formatting, missing semicolons
- `refactor` - Code restructuring
- `test` - Adding tests
- `chore` - Maintenance

**Examples:**
```bash
git commit -m "feat: add category automation rules"
git commit -m "fix: correct duplicate detection hash calculation"
git commit -m "docs: update API documentation for planning endpoints"
git commit -m "refactor: extract duplicate detection to service layer"
```

---

### Pull Request Workflow

1. **Create Branch:**
   ```bash
   git checkout -b issue/123-new-feature
   ```

2. **Make Changes:**
   ```bash
   git add .
   git commit -m "feat: implement new feature"
   ```

3. **Push Branch:**
   ```bash
   git push -u origin issue/123-new-feature
   ```

4. **Create Pull Request:**
   - Go to GitHub repository
   - Click "Pull Requests" → "New Pull Request"
   - Select your branch
   - Add description
   - Request review

5. **Address Feedback:**
   ```bash
   # Make changes
   git add .
   git commit -m "fix: address review feedback"
   git push
   ```

6. **Merge:**
   - Reviewer approves
   - Merge to main
   - Delete branch

---

## Project Structure

```
FiniA/
├── cfg/                    # Configuration files
│   ├── config.yaml         # App configuration
│   ├── data.yaml           # Seed data
│   └── import_formats.yaml # CSV import formats
├── db/                     # Database files
│   └── finia_draft.sql     # Database schema
├── docs/                   # Documentation
│   ├── api.md
│   ├── authentication.md
│   ├── backup.md
│   ├── config.md
│   ├── data.md
│   ├── import_formats.md
│   ├── architecture/
│   ├── database/
│   ├── deployment/
│   ├── development/
│   ├── docker/
│   ├── features/
│   ├── import/
│   └── tutorials/
├── src/                    # Source code
│   ├── main.py             # Entry point
│   ├── Database.py         # Database connection
│   ├── DatabaseCreator.py  # Database setup
│   ├── DataImporter.py     # Data import
│   ├── utils.py            # Utilities
│   ├── api/                # FastAPI application
│   │   ├── main.py
│   │   ├── auth_middleware.py
│   │   ├── dependencies.py
│   │   ├── error_handling.py
│   │   ├── models.py
│   │   └── routers/
│   ├── auth/               # Authentication
│   │   ├── connection_pool_manager.py
│   │   ├── rate_limiter.py
│   │   ├── session_store.py
│   │   └── utils.py
│   ├── config/             # Configuration
│   │   └── theme.py
│   ├── domain/             # Domain models
│   │   └── account.py
│   ├── infrastructure/     # Infrastructure
│   │   └── unit_of_work.py
│   ├── repositories/       # Data access
│   │   ├── base.py
│   │   ├── transaction_repository.py
│   │   ├── account_repository.py
│   │   └── ...
│   └── services/           # Business logic
│       ├── account_data_importer.py
│       ├── category_automation.py
│       ├── import_service.py
│       └── import_steps/
├── test/                   # Test data
│   ├── test_category_automation.py
│   └── data/
├── web/                    # Frontend files
│   ├── index.html
│   ├── login.html
│   ├── style.css
│   ├── app.js
│   ├── accounts.js
│   └── ...
├── .gitignore
├── docker-compose.yml
├── Dockerfile
├── LICENSE
├── Makefile
├── README.md
└── requirements.txt
```

---

## Common Development Tasks

### Add New API Endpoint

**1. Create Model:** `src/api/models.py`
```python
class MyNewRequest(BaseModel):
    field1: str
    field2: int

class MyNewResponse(BaseModel):
    result: str
```

**2. Create Repository Method:** `src/repositories/my_repository.py`
```python
class MyRepository(BaseRepository):
    def my_method(self, param: str) -> dict:
        sql = "SELECT * FROM tbl_my_table WHERE field = %s"
        self.cursor.execute(sql, (param,))
        return self.cursor.fetchone()
```

**3. Create Router:** `src/api/routers/my_router.py`
```python
from fastapi import APIRouter, Depends
from api.models import MyNewRequest, MyNewResponse
from repositories.my_repository import MyRepository
from api.dependencies import get_db_cursor

router = APIRouter(prefix="/my-endpoint", tags=["my-endpoint"])

@router.post("/", response_model=MyNewResponse)
async def my_endpoint(
    request: MyNewRequest,
    cursor = Depends(get_db_cursor)
):
    repo = MyRepository(cursor)
    result = repo.my_method(request.field1)
    return {"result": result}
```

**4. Register Router:** `src/api/main.py`
```python
from api.routers import my_router

app.include_router(my_router.router)
```

---

### Add New Database Table

**1. Update Schema:** `db/finia_draft.sql`
```sql
CREATE TABLE `tbl_my_new_table` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `dateImport` datetime NOT NULL,
  `name` varchar(128) NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3;
```

**2. Create Repository:** `src/repositories/my_new_table_repository.py`
```python
from repositories.base import BaseRepository

class MyNewTableRepository(BaseRepository):
    def get_all(self) -> list[dict]:
        sql = "SELECT * FROM tbl_my_new_table"
        self.cursor.execute(sql)
        return self.cursor.fetchall()
```

**3. Update Documentation:** `docs/database/schema.md`

---

### Add Frontend Page

**1. Create HTML:** `web/my_page.html`
```html
<!DOCTYPE html>
<html>
<head>
    <title>My Page - FiniA</title>
    <link rel="stylesheet" href="style.css">
</head>
<body>
    <div id="content">
        <h1>My Page</h1>
    </div>
    <script src="my_page.js"></script>
</body>
</html>
```

**2. Create JS:** `web/my_page.js`
```javascript
async function loadData() {
    const response = await fetch('/api/my-endpoint/');
    const data = await response.json();
    console.log(data);
}

document.addEventListener('DOMContentLoaded', loadData);
```

**3. Add Navigation:** Update `web/top_nav.html`

---

## Troubleshooting

### "Module not found" Error

**Symptom:** `ModuleNotFoundError: No module named 'repositories'`

**Solution:**
```bash
# Ensure virtual environment is activated
source .venv/bin/activate  # Linux/macOS
.venv\Scripts\Activate.ps1  # Windows PowerShell

# Verify PYTHONPATH
echo $PYTHONPATH  # Linux/macOS
$env:PYTHONPATH   # Windows PowerShell

# Set PYTHONPATH if needed
export PYTHONPATH="${PYTHONPATH}:${PWD}/src"  # Linux/macOS
$env:PYTHONPATH = "$env:PYTHONPATH;$PWD\src"  # Windows PowerShell
```

---

### Database Connection Fails

**Symptom:** `Can't connect to MySQL server on '192.168.1.10'`

**Check:**
1. MySQL server is running
2. Firewall allows port 3306
3. User has remote access permissions
4. Credentials are correct in `cfg/config.yaml`

**Grant Remote Access:**
```sql
-- On MySQL server
CREATE USER 'root'@'%' IDENTIFIED BY 'password';
GRANT ALL PRIVILEGES ON *.* TO 'root'@'%';
FLUSH PRIVILEGES;
```

---

### Port Already in Use

**Symptom:** `Address already in use: 0.0.0.0:8000`

**Solution:**

**Windows:**
```powershell
# Find process using port 8000
netstat -ano | findstr :8000

# Kill process (replace PID)
taskkill /PID <PID> /F
```

**Linux/macOS:**
```bash
# Find process
lsof -i :8000

# Kill process
kill -9 <PID>
```

**Or use different port:**
```bash
python src/main.py --api --port 8001
```

---

### Hot Reload Not Working (Docker)

**Symptom:** Code changes don't trigger restart

**Check:**
1. Volume mounts are correct in `docker-compose.yml`
2. `PYTHONUNBUFFERED=1` is set
3. Uvicorn is running with `--reload` flag

**Dockerfile:**
```dockerfile
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
```

---

## Related Documentation

- [Getting Started Tutorial](../tutorials/getting_started.md) - User guide
- [Docker Deployment](../docker/docker.md) - Container setup
- [Production Deployment](../deployment/production.md) - Production environment
- [API Documentation](../api.md) - REST API reference
- [Repository Pattern](../architecture/repositories.md) - Data access layer
- [Services Layer](../architecture/services.md) - Business logic

---

## Summary

FiniA development setup includes:

✅ **Local Python Environment** - Virtual environment with dependencies  
✅ **Docker Development** - Containerized setup with hot reload  
✅ **VS Code Integration** - Complete IDE configuration  
✅ **Debugging Tools** - Backend (Python) and frontend (DevTools)  
✅ **Database Access** - Multiple clients and tools  
✅ **Git Workflow** - Branching, commits, pull requests  
✅ **Project Structure** - Clear organization and conventions  

**Ready for productive FiniA development!** 🚀
