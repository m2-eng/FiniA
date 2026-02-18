# FiniA Test Suite Documentation

**Issue #32: Implementing a test bench**

Comprehensive automated testing framework for FiniA financial application.

## 📋 Table of Contents

- [Overview](#overview)
- [Quick Start](#quick-start)
- [Test Structure](#test-structure)
- [Configuration](#configuration)
- [Running Tests](#running-tests)
- [Test Data](#test-data)
- [CI/CD Integration](#cicd-integration)
- [Writing Tests](#writing-tests)
- [Troubleshooting](#troubleshooting)

---

## Overview

Das FiniA Test-Framework bietet:

✅ **Schema Validation** - Datenbankstruktur und Constraints  
✅ **Data Integrity** - Referenzielle Integrität und Constraints  
✅ **API Testing** - REST API Functional Tests  
✅ **Error Handling** - Fehlerbehandlung und Edge Cases  
✅ **Performance Benchmarks** - Execution Time Tracking  
✅ **Smart Dependencies** - Automatisches Skipping bei Dependency-Failures  
✅ **Factory Pattern** - Einfache Test-Daten-Erstellung  
✅ **Multiple Test Users** - Lokale, CI/CD, Performance User  

---

## Quick Start

### 1. Installation

```powershell
# Test-Dependencies installieren
pip install -r requirements-test.txt

# Test-Datenbank vorbereiten (optional - wird automatisch gemacht)
# cp .env.test.example .env.test
# Credentials anpassen in .env.test
```

### 2. Test-Konfiguration prüfen

```powershell
# Test-User-Konfiguration
cat cfg/test_users.yaml

# Environment-Variablen
cat .env.test
```

### 3. Tests ausführen

```powershell
# Alle Tests
pytest

# Nur Schema-Validation
pytest -m schema

# Nur API-Tests
pytest -m api

# Spezifische Test-Datei
pytest tests/integration/test_schema_validation.py

# Mit detailliertem Output
pytest -v -s

# Mit HTML-Report
pytest --html=tests/reports/report.html
```

---

## Test Structure

```
tests/
├── conftest.py              # Zentrale Fixture-Konfiguration
├── pytest.ini               # Pytest-Konfiguration
├── requirements-test.txt    # Test-Dependencies
│
├── data/                    # Test-Daten-Generatoren
│   ├── factories.py         # Factory Pattern (11 Factories)
│   └── fake_data.py         # Faker-basierte Generatoren
│
├── fixtures/                # Custom Fixtures
│   └── assertions.py        # 50+ Assertion Helpers
│
├── integration/             # Integration Tests
│   ├── test_schema_validation.py    # Schema Tests
│   ├── test_data_integrity.py       # Integrity Tests
│   ├── test_api_accounts.py         # Account API Tests
│   ├── test_api_categories.py       # Category API Tests
│   ├── test_api_transactions.py     # Transaction API Tests
│   └── ...
│
├── unit/                    # Unit Tests (future)
│
├── performance/             # Performance Benchmarks
│   └── test_benchmarks.py
│
└── reports/                 # Test-Reports (auto-generated)
    ├── report.html
    └── junit.xml
```

---

## Configuration

### Environment Variables (.env.test)

```env
# Database
DB_TEST_HOST=127.0.0.1
DB_TEST_PORT=3306
DB_TEST_USER=root
DB_TEST_PASSWORD=yourpassword
DB_TEST_NAME=finia_test

# API
TEST_API_BASE_URL=http://localhost:8000
TEST_API_TIMEOUT=30

# Test User (siehe test_users.yaml)
FINIA_TEST_USER=local_test

# Performance
PERF_BASELINE_TOLERANCE=10
PERF_CRITICAL_TIMEOUT=2000

# Parallel Execution
PYTEST_PARALLELIZABLE=true
PYTEST_WORKER_COUNT=4
```

### Test Users (cfg/test_users.yaml)

```yaml
test_users:
  local_test:
    username: "test_local"
    password: "test123"
    description: "Local development user"
    type: "local"
    permissions: [read, write, delete]
    skip_teardown: false
  
  ci_runner:
    username: "test_ci"
    password: "ci_token_secure"
    description: "GitHub Actions CI user"
    type: "ci"
    permissions: [read, write, delete]
    skip_teardown: false
  
  performance_test:
    username: "perf_test"
    password: "perf123"
    description: "Performance benchmarking"
    type: "performance"
    permissions: [read, write]
    skip_teardown: true  # Keep data for benchmarks
```

---

## Running Tests

### Marker-basiert

```powershell
# Schema Tests
pytest -m schema

# Data Integrity Tests
pytest -m integrity

# API Tests
pytest -m api

# Performance Tests
pytest -m performance

# Error Handling Tests
pytest -m error_handling

# Slow Tests (>1s)
pytest -m "not slow"
```

### Coverage-Report

```powershell
# Mit Coverage
pytest --cov=src --cov-report=html

# Coverage für spezifisches Modul
pytest --cov=src/repositories --cov-report=term
```

### Parallel Execution

```powershell
# 4 Worker (auto-detected CPUs)
pytest -n auto

# Spezifische Anzahl Worker
pytest -n 4

# Mit Load-Balancing
pytest -n auto --dist loadscope
```

### Performance Benchmarks

```powershell
# Benchmarks ausführen
pytest -m performance --benchmark-only

# Benchmark-Vergleich speichern
pytest -m performance --benchmark-save=baseline

# Mit Baseline vergleichen
pytest -m performance --benchmark-compare=baseline
```

---

## Test Data

### Factory Pattern

```python
def test_with_factories(account_factory, category_factory, transaction_factory):
    """Example: Using factories for test data."""
    
    # Create single account
    account_id = account_factory.create(
        name="Test Account",
        type=1,
        startAmount=1000.0
    )
    
    # Create batch of categories
    category_ids = category_factory.create_batch(count=5)
    
    # Create transactions for account
    transaction_ids = transaction_factory.create_batch(
        account_id=account_id,
        count=10
    )
```

### Faker-basierte Generatoren

```python
def test_with_faker(test_data_generator):
    """Example: Using Faker for realistic data."""
    
    # Generate realistic account data
    account_data = test_data_generator.generate_account_data(
        account_type=1,
        start_amount=5000.0
    )
    
    # Generate transaction batch
    transactions = test_data_generator.generate_transaction_batch(
        account_id=123,
        count=20,
        spread_days=180
    )
    
    # Generate boundary values
    edge_trans = test_data_generator.generate_boundary_transaction(
        account_id=123,
        boundary_type='max_positive'
    )
```

### Test Data Bundle (Convenience)

```python
def test_with_bundle(test_data_bundle):
    """Example: Using convenience bundle."""
    
    # Create complete test scenario
    data = test_data_bundle.create_full_test_scenario(
        num_accounts=3,
        categories_per_account=5
    )
    
    # Access created IDs
    account_ids = data['accounts']
    category_ids = data['categories']
    transaction_ids = data['transactions']
```

---

## CI/CD Integration

### GitHub Actions Workflow

```yaml
# .github/workflows/test.yml
name: Test Suite

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      mysql:
        image: mysql:8.0
        env:
          MYSQL_ROOT_PASSWORD: test_password
          MYSQL_DATABASE: finia_test
        ports:
          - 3306:3306
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install -r requirements-test.txt
      
      - name: Run tests
        env:
          FINIA_TEST_USER: ci_runner
          DB_TEST_HOST: 127.0.0.1
          DB_TEST_PASSWORD: test_password
        run: |
          pytest -v --junitxml=junit.xml --html=report.html
      
      - name: Upload test results
        uses: actions/upload-artifact@v3
        if: always()
        with:
          name: test-results
          path: |
            junit.xml
            report.html
```

---

## Writing Tests

### Test Template

```python
import pytest
from decimal import Decimal

@pytest.mark.api
class TestMyFeature:
    """Test suite for MyFeature."""
    
    def test_basic_functionality(self, db_cursor, account_factory):
        """Test basic feature behavior."""
        # Arrange
        account_id = account_factory.create()
        
        # Act
        db_cursor.execute("SELECT * FROM tbl_account WHERE id=%s", (account_id,))
        result = db_cursor.fetchone()
        
        # Assert
        assert result is not None
        assert result[0] == account_id
    
    def test_edge_case(self, test_data_generator):
        """Test edge case handling."""
        # Generate boundary data
        data = test_data_generator.generate_boundary_transaction(
            account_id=1,
            boundary_type='zero'
        )
        
        # Test handling
        assert data['amount'] == Decimal('0.00')
    
    def test_api_endpoint(self, api_client, test_config):
        """Test API endpoint."""
        response = api_client.get(
            f"{test_config['api_base_url']}/api/accounts/list"
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
```

### Assertion Helpers

```python
def test_with_assertions(db_cursor, assertions):
    """Example: Using assertion helpers."""
    from fixtures.assertions import APIAssertions, DatabaseAssertions
    
    api = APIAssertions()
    db = DatabaseAssertions()
    
    # API assertions
    response = api_client.get("/api/accounts/1")
    data = api.assert_response_success(response, expected_code=200)
    api.assert_contains_fields(data, ['id', 'name', 'iban_accountNumber'])
    
    # Database assertions
    db.assert_record_exists(
        db_cursor,
        'tbl_account',
        {'id': 1, 'type': 1}
    )
    
    db.assert_record_count(
        db_cursor,
        'tbl_transaction',
        expected_count=10,
        where_clause="account=%s",
        params=(1,)
    )
```

---

## Troubleshooting

### Common Issues

**1. Database connection failed**

```
ERROR: Failed to connect to test database
```

**Solution**: Check .env.test credentials and ensure MySQL is running:

```powershell
# Check MySQL service
Get-Service MySQL*

# Test connection
mysql -h 127.0.0.1 -u root -p finia_test
```

**2. Migration errors**

```
ERROR: Database initialization failed
```

**Solution**: Reset test database:

```powershell
# Drop and recreate
mysql -u root -p -e "DROP DATABASE IF EXISTS finia_test; CREATE DATABASE finia_test;"

# Re-run tests (will apply migrations)
pytest
```

**3. Import errors**

```
ModuleNotFoundError: No module named 'factories'
```

**Solution**: Ensure Python path includes test directories:

```python
# conftest.py already handles this
sys.path.insert(0, str(Path(__file__).parent / 'data'))
```

**4. Parallel execution conflicts**

```
ERROR: Duplicate entry violation in parallel tests
```

**Solution**: Use sequential execution for integrity tests:

```powershell
pytest -m integrity -n 0  # No parallelization
```

### Debug Mode

```powershell
# Run with full debug output
pytest -vvs --log-cli-level=DEBUG

# Run single test with debugger
pytest tests/integration/test_schema_validation.py::TestDatabaseSchema::test_all_required_tables_exist -vvs --pdb

# Show fixture setup
pytest --setup-show
```

---

## Test Metrics

### Current Coverage

| Module | Coverage | Tests |
|--------|----------|-------|
| Schema Validation | ✅ 100% | 15 tests |
| Data Integrity | ✅ 100% | 12 tests |
| Account API | ✅ 85% | 18 tests |
| Category API | 🚧 Pending | - |
| Transaction API | 🚧 Pending | - |
| Planning API | 🚧 Pending | - |
| Performance | 🚧 Pending | - |

### Test Execution Times

- **Schema Validation**: ~2s
- **Data Integrity**: ~5s
- **Account API**: ~8s
- **Full Suite** (when complete): ~30s (estimated)

---

## Contributing

### Adding New Tests

1. **Create test file** in appropriate directory
2. **Use markers** (@pytest.mark.schema, @pytest.mark.api, etc.)
3. **Use factories** for test data
4. **Add assertions** for validation
5. **Document** test purpose in docstring

### Test Naming Conventions

- Test files: `test_<feature>.py`
- Test classes: `Test<Feature><Aspect>`
- Test methods: `test_<specific_behavior>`

### Example

```python
# tests/integration/test_api_my_feature.py

@pytest.mark.api
class TestMyFeatureAPI:
    """Test MyFeature API endpoints."""
    
    def test_create_my_feature(self, api_client, test_config):
        """Test POST /api/my-feature creates new feature."""
        pass
    
    def test_get_my_feature_list(self, api_client, test_config):
        """Test GET /api/my-feature returns feature list."""
        pass
```

---

## Resources

- **pytest Docs**: https://docs.pytest.org/
- **factory-boy Docs**: https://factoryboy.readthedocs.io/
- **Faker Docs**: https://faker.readthedocs.io/
- **FastAPI Testing**: https://fastapi.tiangolo.com/tutorial/testing/

---

## Contact

For questions or issues related to the test suite:

- **Issue Tracker**: GitHub Issues
- **Pull Requests**: Welcome!
- **Documentation**: See docs/ directory

---

**Last Updated**: February 18, 2026  
**Issue**: #32 - Implementing a test bench  
**Status**: ✅ Phase 1-2 Complete, 🚧 Phase 3-5 In Progress
