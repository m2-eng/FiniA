# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Documentation

Complete documentation available in `docs/`:
- [Getting Started Guide](docs/tutorials/getting_started.md) – Initial setup and first steps
- [API Documentation](docs/api.md) – REST endpoints and authentication
- [Architecture Guide](docs/architecture/) – System design and patterns
- [Deployment Guide](docs/deployment/production.md) – Production-ready setup
- [Development Setup](docs/development/setup.md) – Local development environment
- [Troubleshooting Guide](docs/troubleshooting.md) – Common issues and solutions

## [Unreleased]

## [0.1.0-beta.3] - 2026-03-01

**Fixed bugs:**
- Missing migration folder in the Docker Container

## [0.1.0-beta.2] - 2026-03-01

**Improvments:**
- Add missing category import

**Fixed bugs:**
- Test errors and warnings due to renaming
- Too many function parameter in insert_ignore of the planning cycle repository
- Loading the categories file/methods


## [0.1.0-beta.1] - 2026-02-18

### ✨ Added

**Core Features:**
- FastAPI REST API backend with JWT-based session authentication
- Responsive Web UI for account management and financial overview
- CSV import with duplicate detection and automatic categorization
- Docker and Docker Compose support for containerized deployment
- Database versioning and migration system (schema_migrations tracking)

**Architecture & Infrastructure:**
- Repository pattern implementation with 13 specialized repositories (BaseRepository)
- Unit of Work pattern for transaction management and consistency
- Service layer with business logic separation (AccountDataImporter, CategoryAutomation, ImportService)
- 5-step import pipeline for robust data processing
- Layered architecture for separation of concerns
- Comprehensive pytest test suite with 125+ integration, unit, and performance tests
- GitHub Actions CI/CD pipeline for Docker builds

**Account & Transaction Management:**
- Multi-account support with customizable account types
- Transaction tracking with detailed categorization
- Accounting entries with automatic category assignment
- Account balance calculations and history tracking
- Reserve/margin management for accounts

**Planning & Budgeting:**
- Recurring budgets with flexible planning cycles
- Automatic entry generation based on planning rules
- Year-over-year budget vs. actual comparison
- Integration with transaction planning

**Portfolio Management:**
- Share/securities tracking with buy/sell/dividend transactions
- Portfolio valuation and performance analysis
- Share history tracking and transaction auditing

**Category Automation:**
- Rule-based automatic transaction categorization
- Multiple condition types: contains, equals, regex, amount ranges, date patterns
- Complex condition logic: AND/OR combinations with nesting
- Support for both English and German operators

**Configuration & Deployment:**
- YAML-based configuration for all settings (database, API, features)
- CORS origins configurable from config.yaml
- Flexible CSV import format definitions
- Docker Compose with MariaDB/MySQL integration
- Environment-based configuration (.env support)

**Database & Schema:**
- 16 normalized tables with 8 views
- Full schema with migrations support
- MySQL 8.0 and MariaDB 11.x compatibility
- Data integrity constraints and referential integrity

**Documentation:**
- Comprehensive API documentation (OpenAPI/Swagger)
- Architecture guides covering repositories and services
- Database schema documentation
- Deployment and setup guides
- Development environment documentation

### 🔧 Changed (Improvements & Refactorings)

**Code Quality:**
- Unified error handling across all APIs and repositories
- Centralized authentication and session management
- Replaced legacy event handlers with modern lifespan pattern
- Translated all comments and documentation to English
- Improved logging throughout application (INFO/DEBUG levels)
- Removed deprecated CLIs in favor of REST APIs
- Improved robustness with proper rollback handling

**User Interface:**
- Redesigned account management interface
- Improved import page with better filters and pagination
- Revised import format settings UI
- Added user theme selection (light/dark modes)
- Better visual organization of navigation

**Performance:**
- Connection pool optimization (configurable pool size)
- Async/await patterns for database operations
- Improved SQL query performance
- Pagination support for large result sets
- Request timeout configuration

**Database:**
- Improved MariaDB compatibility
- Fixed transaction commit handling issues
- Added database migration system for schema evolution
- Proper foreign key constraint handling

### 🐛 Fixed

- Connection pool exhaustion in concurrent scenarios
- Transaction duplication when IBAN is NULL
- Duplicate category creation issues
- Database commit issues with MariaDB
- Navigation menu duplicate items
- Application startup and shutdown sequence
- File name suffix validation for imports

### 📚 Documentation

- Added comprehensive README with feature overview
- Created API documentation with endpoint details
- Added authentication guide
- Created architecture documentation
- Added deployment guide for production setups
- Added troubleshooting guide for common issues
- Added development setup guide
- Created CSV import format documentation

### 🔄 Dependencies

Updated key dependencies to latest stable versions:
- pytest: 7.4.3 → 9.0.2 (test framework)
- faker: 21.0.0 → 40.4.0 (test data generation)
- httpx: 0.25.2 → 0.28.1 (HTTP client)
- mysql-connector-python: 8.2.0 → 9.6.0
- pytest-cov: 4.1.0 → 7.0.0
- pytest-asyncio: 0.23.2 → 1.3.0
- requests: 2.31.0 → 2.32.5
- factory-boy: 3.3.0 → 3.3.3
- pytest-benchmark: 4.0.0 → 5.2.3
- GitHub Actions: checkout@4→6, setup-python@4→6, build-push-action@5→6

### 🐛 Known Issues

- Not fully tested across all edge cases
- Category automation rules may require manual review
- Performance not optimized for large datasets (100k+ transactions)
- Web UI uses in-memory sessions (not persistent across restarts)

### ⚠️ Important Notes

**This is a BETA release** – not recommended for production use without thorough testing.

- Manual testing recommended for:
  - CSV import with your specific data formats
  - Category automation rules in your use case
  - Multi-user concurrent access (in-memory sessions)
  - Docker deployment in non-standard environments

- Backup strategy must be implemented before production deployment
- No embedded database included; external MySQL/MariaDB required

---

## Links

[Unreleased]: https://github.com/m2-eng/FiniA/compare/v0.1.0-beta.3...HEAD
[0.1.0-beta.3]: https://github.com/m2-eng/FiniA/releases/tag/v0.1.0-beta.3
[0.1.0-beta.2]: https://github.com/m2-eng/FiniA/releases/tag/v0.1.0-beta.2
[0.1.0-beta.1]: https://github.com/m2-eng/FiniA/releases/tag/v0.1.0-beta.1
