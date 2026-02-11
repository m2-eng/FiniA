# 📋 Review Status (main branch)

## [#71 - Authentication & Sessions](https://github.com/m2-eng/FiniA/issues/71)

### Backend (Python)
- [src/api/auth_middleware.py](../src/api/auth_middleware.py)
- [src/auth/connection_pool_manager.py](../src/auth/connection_pool_manager.py)
- [src/auth/rate_limiter.py](../src/auth/rate_limiter.py)
- [src/auth/session_store.py](../src/auth/session_store.py)
- [src/auth/utils.py](../src/auth/utils.py)

### Frontend (JavaScript)
- none

### HTML Templates
- none

### Others
- none

### New issues
- none

### Updated issues
- [#77 - Improve the handling of the pool manager and the connections](https://github.com/m2-eng/FiniA/issues/77)
- [#89 - Write comments in English](https://github.com/m2-eng/FiniA/issues/89)


## [#70 - API (Backend‑Edge)](https://github.com/m2-eng/FiniA/issues/70)

### Backend (Python)
- [src/api/main.py](../src/api/main.py)
- [src/api/dependencies.py](../src/api/dependencies.py)
- [src/api/error_handling.py](../src/api/error_handling.py)
- [src/api/models.py](../src/api/models.py)
- [src/api/routers](../src/api/routers)
   - [src/api/routers/accounts.py](../src/api/routers/accounts.py)
   - [src/api/routers/categories.py](../src/api/routers/categories.py)
   - [src/api/routers/category_automation.py](../src/api/routers/category_automation.py)
   - [src/api/routers/docs.py](../src/api/routers/docs.py)
   - [src/api/routers/planning.py](../src/api/routers/planning.py)
   - [src/api/routers/settings.py](../src/api/routers/settings.py)
   - [src/api/routers/shares.py](../src/api/routers/shares.py)
   - [src/api/routers/theme.py](../src/api/routers/theme.py)
   - [src/api/routers/transactions.py](../src/api/routers/transactions.py)
   - [src/api/routers/year_overview.py](../src/api/routers/year_overview.py)
   - [src/api/routers/years.py](../src/api/routers/years.py)

### Frontend (JavaScript)
- none

### HTML Templates
- none

### Others
- none

### New issues
- [#77 - Improve the handling of the pool manager and the connections](https://github.com/m2-eng/FiniA/issues/77)
- [#78 - Add VERSION file and used the reference to it](https://github.com/m2-eng/FiniA/issues/78)
- [#79 - Improvement of the configuration](https://github.com/m2-eng/FiniA/issues/79)
- [#80 - Improvement of the log wording and design](https://github.com/m2-eng/FiniA/issues/80)
- [#81 - 'on_event' is deprecated](https://github.com/m2-eng/FiniA/issues/81)
- [#82 - Remove dead code](https://github.com/m2-eng/FiniA/issues/82)
- [#83 - Using the functions provided by connection](https://github.com/m2-eng/FiniA/issues/83)
- [#84 - Single source for the fetch functions](https://github.com/m2-eng/FiniA/issues/84)
- [#85 - Harden against directory traversal attacks](https://github.com/m2-eng/FiniA/issues/85)
- [#86 - Improvement of the SQL command handling](https://github.com/m2-eng/FiniA/issues/86)
- [#87 - Improvement of the exception handling and messages](https://github.com/m2-eng/FiniA/issues/87)
- [#88 - Create the missing base models](https://github.com/m2-eng/FiniA/issues/88)
- [#89 - Write comments in English](https://github.com/m2-eng/FiniA/issues/89)
- [#90 - Renaming of functions and other stuff](https://github.com/m2-eng/FiniA/issues/90)
- [#91 - Check what have to be closed during closing the application](https://github.com/m2-eng/FiniA/issues/91)


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
