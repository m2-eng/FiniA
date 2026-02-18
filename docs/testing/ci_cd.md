# Continuous Integration (CI/CD)

This document describes the automated testing and continuous integration setup for FiniA.

## Overview

FiniA uses **GitHub Actions** for automated testing on every push and pull request. The test suite is implemented with **pytest** and includes schema validation, API integration tests, error handling, and performance benchmarks.

**Issue Reference:** [#32 - Implementing a test bench](https://github.com/m2-eng/FiniA/issues/32)

## Workflows

### 1. **Main Test Suite** (`tests.yml`)

**Triggers:**
- Push to `main`, `develop`, or any `issue/**` branch
- Pull requests to `main` or `develop`

**Test Phases:**
1. **Schema & Integrity Tests** - Validates database schema and referential integrity
2. **API Integration Tests** - Tests all API endpoints (accounts, categories, transactions, planning, shares, year-overview)
3. **Error Handling Tests** - Validates HTTP errors, database constraints, business logic errors
4. **Performance Benchmarks** - Measures query performance and API response times
5. **Coverage Report** - Generates code coverage report and uploads to Codecov

**Services:**
- MySQL 8.0 (test database)
- FiniA API Server (started during tests)

**Artifacts:**
- HTML test report
- JUnit XML report
- Coverage report (HTML + XML)
- Uploaded to GitHub Actions (30 days retention)

**Badge:** [![Tests](https://github.com/m2-eng/FiniA/actions/workflows/tests.yml/badge.svg)](https://github.com/m2-eng/FiniA/actions/workflows/tests.yml)

---

### 2. **Quick Tests** (`test-quick.yml`)

**Triggers:**
- Pull requests (opened, synchronized, reopened)

**Purpose:**
Fast feedback for PRs - runs only schema and integrity tests (~2 minutes).

**Use Case:**
Quick validation before full test suite runs.

---

### 3. **Performance Tests** (`performance.yml`)

**Triggers:**
- Daily at 2:00 AM UTC (cron schedule)
- Manual trigger via GitHub UI
- Push to `main` with changes to `src/**` or `tests/performance/**`

**Purpose:**
- Continuous performance monitoring
- Detect performance regressions
- Validate Issue #66 fix (year overview < 2000ms)

**Features:**
- Runs pytest-benchmark suite
- Stores benchmark history
- Alerts on performance degradation >150%
- Uploads performance reports (90 days retention)

**Critical Thresholds:**
- Year Overview API: < 2000ms (Issue #66)
- Account Income API: < 1000ms
- Planning Entries Generation: < 500ms

**Badge:** [![Performance](https://github.com/m2-eng/FiniA/actions/workflows/performance.yml/badge.svg)](https://github.com/m2-eng/FiniA/actions/workflows/performance.yml)

---

## Test Structure

```
tests/
├── conftest.py                          # Shared fixtures and configuration
├── integration/
│   ├── test_db_schema.py               # Schema validation (17 tests)
│   ├── test_data_integrity.py          # Referential integrity (15 tests)
│   ├── test_api_accounts.py            # Account API (10 tests)
│   ├── test_api_categories.py          # Category API (12 tests)
│   ├── test_api_planning.py            # Planning API (8 tests)
│   ├── test_api_shares.py              # Shares API (8 tests)
│   ├── test_api_transactions.py        # Transaction API (15 tests)
│   ├── test_api_year_overview.py       # Year Overview API (7 tests)
│   └── test_error_handling.py          # Error handling (17 tests)
├── performance/
│   └── test_benchmarks.py              # Performance benchmarks (18 tests)
└── fixtures/
    ├── factories.py                     # Test data factories (11 factories)
    └── data_bundles.py                  # Pre-configured test scenarios
```

**Total:** ~127 tests across 12 test files

---

## Code Coverage

FiniA uses **pytest-cov** (Python's equivalent to gcov) for comprehensive code coverage measurement.

**📊 Coverage Badge:** [![codecov](https://codecov.io/gh/m2-eng/FiniA/branch/main/graph/badge.svg)](https://codecov.io/gh/m2-eng/FiniA)

### Coverage Configuration

- **Tool:** pytest-cov (based on coverage.py)
- **Configuration:** [.coveragerc](../../.coveragerc)
- **Minimum Threshold:** 75%
- **Current Target:** 85%
- **Branch Coverage:** Enabled

### Coverage Reports

Generated during test execution:
- **Terminal Report:** Real-time coverage summary
- **HTML Report:** Interactive file-by-file coverage (`reports/coverage/index.html`)
- **XML Report:** For Codecov upload (`reports/coverage.xml`)
- **JSON Report:** Machine-readable data (`reports/coverage.json`)

### Codecov Integration

Coverage is automatically uploaded to [Codecov.io](https://codecov.io/gh/m2-eng/FiniA):
- 📈 Coverage trends over time
- 💬 Automated PR comments with coverage diff
- 🎯 File-by-file coverage breakdown
- 🚨 Alerts on coverage degradation

**Setup Required:**
1. Sign up at https://codecov.io/
2. Connect GitHub repository
3. Add `CODECOV_TOKEN` to GitHub Secrets (optional, works without token for public repos)

### Local Coverage

```bash
# Run tests with coverage
pytest tests/ --cov=src --cov-report=html

# Open HTML report
start reports/coverage/index.html
```

**See:** [Code Coverage Documentation](coverage.md) for detailed information.

---

## Running Tests Locally

### Prerequisites

```bash
# Activate virtual environment
.venv\Scripts\activate

# Install test dependencies
pip install pytest pytest-html pytest-cov pytest-benchmark
```

### Environment Configuration

Create `.env.test` file:

```env
# Database
DB_USER=finia_test
DB_PASSWORD=test_password
DB_HOST=127.0.0.1
DB_PORT=3306
DB_NAME=finia_test

# API
API_HOST=127.0.0.1
API_PORT=8000
API_BASE_URL=http://127.0.0.1:8000

# Test User
TEST_USER_USERNAME=testuser
TEST_USER_PASSWORD=TestPassword123!

# Performance
CRITICAL_TIMEOUT_MS=2000
WARNING_TIMEOUT_MS=1000
```

### Test Commands

```bash
# Run all tests
pytest tests/

# Run only API tests
pytest tests/integration/ -m api -v

# Run only performance tests
pytest tests/performance/ -m performance --benchmark-only

# Run with coverage
pytest tests/ --cov=src --cov-report=html

# Run with HTML report
pytest tests/ --html=reports/test_report.html --self-contained-html

# Run specific test file
pytest tests/integration/test_api_accounts.py -v
```

### Test Markers

```bash
-m schema           # Schema validation tests
-m integrity        # Data integrity tests
-m api              # API integration tests
-m error_handling   # Error handling tests
-m performance      # Performance benchmarks
-m slow             # Slow-running tests
```

---

## Test Data Management

### Fixtures

**Database Fixtures:**
- `db_connection` - Session-scoped database connection
- `db_cursor` - Function-scoped database cursor
- `test_transaction` - Auto-rollback transaction

**API Fixtures:**
- `api_client` - Configured requests.Session
- `test_user` - Test user credentials
- `api_auth_headers` - Authentication headers

### Factories

**11 Test Data Factories:**
1. `account_factory` - Create test accounts
2. `account_type_factory` - Create account types
3. `category_factory` - Create categories (with hierarchy)
4. `transaction_factory` - Create transactions
5. `accounting_entry_factory` - Create accounting entries
6. `planning_cycle_factory` - Create planning cycles
7. `planning_factory` - Create planning entries
8. `share_factory` - Create shares/securities
9. `share_history_factory` - Create price history
10. `share_transaction_factory` - Create share transactions
11. `settings_factory` - Create settings

**Example:**
```python
def test_account_creation(account_factory):
    account_id = account_factory.create(name="Test Account", balance=1000.00)
    assert account_id is not None
```

### Data Bundles

Pre-configured test scenarios via `test_data_bundle` fixture:

```python
def test_full_scenario(test_data_bundle):
    data = test_data_bundle.create_full_test_scenario(
        num_accounts=5,
        categories_per_account=10
    )
    
    assert len(data['accounts']) == 5
    assert len(data['categories']) == 10
```

---

## Performance Monitoring

### Benchmarks

Performance tests use **pytest-benchmark** for accurate timing:

```python
def test_account_list_performance(api_client, benchmark):
    def fetch_accounts():
        return api_client.get("/api/accounts/list")
    
    result = benchmark(fetch_accounts)
    assert result.status_code == 200
```

### Performance Timer

For API response time validation:

```python
def test_year_overview_response_time(api_client, performance_timer):
    with performance_timer as timer:
        response = api_client.get("/api/year-overview/account-balances")
    
    assert timer.elapsed_ms < 2000  # Critical threshold
```

### Regression Detection

Automated checks for performance degradation:
- Year Overview API must remain < 2000ms (Issue #66 fix)
- Alerts triggered if performance degrades >150%
- Daily monitoring via scheduled workflow

---

## GitHub Actions Configuration

### Required Secrets

**Optional:**
- `CODECOV_TOKEN` - For coverage upload (if using Codecov)

**Note:** MySQL credentials are defined in workflow files (test environment only).

### Workflow Files

- [.github/workflows/tests.yml](.github/workflows/tests.yml) - Main test suite
- [.github/workflows/test-quick.yml](.github/workflows/test-quick.yml) - Quick PR validation
- [.github/workflows/performance.yml](.github/workflows/performance.yml) - Performance monitoring

---

## Test Reports

### Artifacts

**Main Test Suite:**
- Test report (HTML)
- JUnit XML (for PR comments)
- Coverage report (HTML + XML)
- Retention: 30 days

**Performance Tests:**
- Benchmark results (JSON)
- Performance report (HTML)
- Retention: 90 days

### Accessing Reports

1. Go to GitHub Actions tab
2. Select workflow run
3. Scroll to "Artifacts" section
4. Download report archive

---

## Pull Request Integration

### Automated Checks

Every PR triggers:
1. ✅ Quick Tests (schema + integrity)
2. ✅ Full Test Suite (all tests)
3. 📊 Test Results Comment (summary in PR)
4. 📈 Coverage Report

### PR Comment Format

```
Test Results

✅ 127 tests passed
❌ 0 tests failed
⏭️ 0 tests skipped

Coverage: 85%

View detailed report in GitHub Actions artifacts.
```

---

## Troubleshooting

### Common Issues

**1. MySQL Connection Failed**
```bash
# Check if MySQL service is running
mysqladmin ping -h 127.0.0.1 -P 3306 -u root -p

# Verify .env.test configuration
cat .env.test
```

**2. API Server Not Starting**
```bash
# Check if port 8000 is available
netstat -an | findstr "8000"

# Start API manually
python src/main.py
```

**3. Test Database Schema Missing**
```bash
# Create schema manually
mysql -u finia_test -p finia_test < db/migrations/001_initial_schema.sql
```

**4. Permission Errors**
```bash
# Verify database user permissions
mysql -u root -p
GRANT ALL PRIVILEGES ON finia_test.* TO 'finia_test'@'localhost';
FLUSH PRIVILEGES;
```

### Debug Mode

Run tests with verbose output:

```bash
pytest tests/ -v --tb=long --log-cli-level=DEBUG
```

---

## Maintenance

### Adding New Tests

1. Create test file in appropriate directory:
   - `tests/integration/` - API and integration tests
   - `tests/performance/` - Performance benchmarks

2. Add pytest markers:
   ```python
   pytestmark = pytest.mark.api
   ```

3. Use existing fixtures/factories for test data

4. Run locally before pushing:
   ```bash
   pytest tests/integration/test_new_feature.py -v
   ```

### Updating Test Configuration

- **pytest configuration:** [pytest.ini](../pytest.ini)
- **Test environment:** [.env.test](.env.test.example)
- **Workflow configuration:** [.github/workflows/](.github/workflows/)

---

## References

- **Issue #32:** [Implementing a test bench](https://github.com/m2-eng/FiniA/issues/32)
- **Issue #66:** [Year Overview Performance Fix](https://github.com/m2-eng/FiniA/issues/66)
- **Pytest Documentation:** https://docs.pytest.org/
- **GitHub Actions:** https://docs.github.com/en/actions

---

## Test Coverage Goals

| Component | Target | Current |
|-----------|--------|---------|
| API Endpoints | 100% | ~95% |
| Repositories | 90% | ~85% |
| Services | 85% | ~80% |
| Domain Logic | 95% | ~90% |
| **Overall** | **85%** | **~85%** |

**Last Updated:** 2026-02-18 (Issue #32 implementation)
