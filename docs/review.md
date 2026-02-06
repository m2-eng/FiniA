# 📋 Review Status (main branch)

## [#70 - API (Backend‑Edge)](https://github.com/m2-eng/FiniA/issues/70)

### Backend (Python)
- [src/api/main.py](../src/api/main.py)
- [src/api/dependencies.py](../src/api/dependencies.py)

### Frontend (JavaScript)
- none

### HTML Templates
- none

### Others
- none

### New issues
- [#77 - Improve the handling of the pool manager and the connections](https://github.com/m2-eng/FiniA/issues/77)
   - affected files
      - [src/api/dependencies.py](../src/api/dependencies.py)
         - [get_db_cursor_with_auth()](../src/api/dependencies.py)
         - [get_db_connection_with_auth()](../src/api/dependencies.py)
         - [get_pool_manager()](../src/api/dependencies.py)
      - [src/api/auth_middleware.py](../src/api/auth_middleware.py)
      - [src/api/main.py](../src/api/main.py)
   - related findings:
      - Two functions using the same name 'set_auth_managers' is confusing, maybe rename one of them to clarify their purpose.
      - The link to the definition of the function 'get_connection' cannot be resolved.

- Version should be read from a single source of truth. Reference to VERSION file.
   - [src/api/main.py](../src/api/main.py)
- The configuration is loaded into 'config', use single source of truth to avoid confusion.
   - related finding: Maybe move loading 'auth_config' to the section of 'config' loading. Maybe it prevents confusion.
   - see also: [src/api/main.py:shutdown_event()](../src/api/main.py)
- Log design (.e.g indentation) and wording can be improved; maybe also add additional information to the log (e.g. docker module log shall show the 'INFO' messages)
   - [src/api/main.py](../src/api/main.py)
- 'on_event' is deprecated, use 'lifespan' event handler instead.
   - [src/api/main.py](../src/api/main.py)
- Not sure whether everything is closed, what should be closed and what not. Review the content again.
   - [src/api/main.py](../src/api/main.py)
- Not needed imports shall be removed.
   - [src/api/dependencies.py](../src/api/dependencies.py)
- Is this the correct database instance? Does the authentication uses the same database instance?
   - releated finding: Is this a duplicate?
   - [src/api/main.py](../src/api/main.py)
   - [src/api/dependencies.py](../src/api/dependencies.py)
- This is an old function. Only the function 'get_db_cursor_with_auth' shall be used, the old one can be removed.
   - related finding: This is an old function. Only the function 'get_db_connection_with_auth' shall be used, the old one can be removed.
   - [src/api/dependencies.py:get_db_cursor()](../src/api/dependencies.py)
   - [src/api/dependencies.py:get_db_connection()](../src/api/dependencies.py)
- Add a parameter to 'config.yaml' to define the timeout value.
   - [src/api/dependencies.py:get_db_cursor_with_auth()](../src/api/dependencies.py)
- Use Englisch comments
   - [src/api/main.py](../src/api/main.py)
   - [src/api/dependencies.py](../src/api/dependencies.py)

## [#57 - Year Overview](https://github.com/m2-eng/FiniA/issues/57)

### Backend (Python)
- [year_overview.py](../src/api/routers/year_overview.py)
  - only `get_assets_month_end`-function

### Frontend (JavaScript)
- [year_overview.js](../src/web/year_overview.js)

### HTML Templates
- [year_overview.html](../src/web/year_overview.html)

### Others
- none

### New issues
- none


## 👉 📄 TEMPLATE - Reviewed Files

### Backend (Python)
- path/to/file.py
- path/to/module/handler.py

### Frontend (JavaScript)
- static/js/app.js
- static/js/components/Form.js

### HTML Templates
- templates/index.html
- templates/dashboard.html

### Others
- static/css/styles.css

### New issues
(Use this section to list created issues)

- [#57](https://github.com/m2-eng/FiniA/issues/57) - Just a how to


## ✅ Review Strategy (6–8 Issues, thematic/functional)

### Issue 1 – API (Backend Edge)
**Focus:** HTTP API, dependencies, error handling
- [src/api/main.py](../src/api/main.py)
- [src/api/models.py](../src/api/models.py)
- [src/api/dependencies.py](../src/api/dependencies.py)
- [src/api/error_handling.py](../src/api/error_handling.py)
- [src/api/routers/](../src/api/routers/)

### Issue 2 – Authentication & Sessions
**Focus:** Auth middleware, sessions, security‑relevant logic
- [src/api/auth_middleware.py](../src/api/auth_middleware.py)
- [src/auth/](../src/auth/)**

### Issue 3 – Domain & Repositories
**Focus:** Domain models, repositories, persistence abstraction
- [src/domain/](../src/domain/)
- [src/repositories/](../src/repositories/)
- [src/infrastructure/unit_of_work.py](../src/infrastructure/unit_of_work.py)

### Issue 4 – Service Layer (Business Logic)
**Focus:** Business logic, automations
- [src/services/account_data_importer.py](../src/services/account_data_importer.py)
- [src/services/category_automation.py](../src/services/category_automation.py)
- [src/services/field_extractor.py](../src/services/field_extractor.py)
- [src/services/import_service.py](../src/services/import_service.py)

### Issue 5 – Data Access & Import Pipeline
**Focus:** DB setup, import pipeline, CSV utilities
- [src/Database.py](../src/Database.py)
- [src/DatabaseCreator.py](../src/DatabaseCreator.py)
- [src/DataImporter.py](../src/DataImporter.py)
- [src/services/csv_utils.py](../src/services/csv_utils.py)
- [src/services/import_steps/](../src/services/import_steps/)
- [db/finia_draft.sql](../db/finia_draft.sql)

### Issue 6 – Frontend (JS + HTML)
**Focus:** UI logic, screens, client interactions
- [src/web/](../src/web/)

### Issue 7 – Configuration, Operations, Tests & Docs
**Focus:** Runtime, deployment, configs, documentation, tests
- [cfg/](../cfg/)
- [Dockerfile](../Dockerfile)
- [docker-compose.yml](../docker-compose.yml)
- [docker-compose.override.yml.example](../docker-compose.override.yml.example)
- [nginx.conf](../nginx.conf)
- [Makefile](../Makefile)
- [docs/](../docs/)
- [test/](../test/)
