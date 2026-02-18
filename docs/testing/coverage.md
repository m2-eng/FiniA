# Code Coverage Setup

This document describes the code coverage integration for FiniA.

## Overview

FiniA uses **pytest-cov** (based on coverage.py) for code coverage measurement - the Python equivalent to gcov. Coverage is automatically measured during test execution and reports are generated in multiple formats.

## Coverage Tools

- **pytest-cov**: Coverage plugin for pytest
- **coverage.py**: Underlying coverage measurement tool
- **Codecov.io**: Cloud-based coverage tracking and visualization

## Configuration

### `.coveragerc`

Coverage configuration is stored in [.coveragerc](.coveragerc):

```ini
[run]
source = src              # Measure coverage for src/ directory
branch = True             # Enable branch coverage
omit = */tests/*, ...     # Exclude test files

[report]
show_missing = True       # Show uncovered lines
fail_under = 75.0         # Minimum coverage threshold: 75%
precision = 2             # Show 2 decimal places

[html]
directory = reports/coverage  # HTML report output

[xml]
output = reports/coverage.xml  # XML for Codecov
```

**Key Settings:**
- ✅ Branch coverage enabled
- ✅ Minimum threshold: 75%
- ✅ Excludes test files, migrations, scripts
- ✅ Excludes pragmas: `# pragma: no cover`

## Running Coverage Locally

### Basic Coverage

```bash
# Run tests with coverage
pytest tests/ --cov=src --cov-report=term

# Output:
# src/main.py                 45      10    22%
# src/api/main.py            123      15    88%
# src/repositories/base.py    89       5    94%
# ...
# TOTAL                      2345     234    90.01%
```

### HTML Report

```bash
# Generate HTML coverage report
pytest tests/ --cov=src --cov-report=html

# Open report in browser
start reports/coverage/index.html  # Windows
# or
xdg-open reports/coverage/index.html  # Linux
```

### XML Report (for CI/CD)

```bash
# Generate XML report for Codecov
pytest tests/ --cov=src --cov-report=xml
```

### All Formats

```bash
# Generate all report formats
pytest tests/ \
    --cov=src \
    --cov-report=term \
    --cov-report=html \
    --cov-report=xml \
    --cov-report=json
```

## Coverage Reports

### Terminal Report

```
---------------------------- coverage: platform win32 ----------------------------
Name                                 Stmts   Miss  Cover   Missing
------------------------------------------------------------------
src/api/main.py                        123     15    88%   45-48, 123-129
src/api/routers/accounts.py            89      5    94%   234-238
src/repositories/account_repository.py 156     12    92%   89-92, 145-151
src/services/import_service.py         234     45    81%   123-156, 234-256
------------------------------------------------------------------
TOTAL                                 2345    234   90.01%
```

### HTML Report

Interactive HTML report with:
- ✅ File-by-file coverage
- ✅ Line-by-line highlighting (green = covered, red = uncovered)
- ✅ Branch coverage visualization
- ✅ Sortable columns
- ✅ Coverage heatmap

**Location:** `reports/coverage/index.html`

### XML Report

Machine-readable XML for CI/CD integration:
- Used by Codecov.io
- Used by SonarQube
- JaCoCo-compatible format

**Location:** `reports/coverage.xml`

## GitHub Actions Integration

Coverage is automatically measured in [.github/workflows/tests.yml](.github/workflows/tests.yml):

```yaml
- name: Run All Tests with Coverage
  run: |
    pytest tests/ \
      --cov=src \
      --cov-report=html:reports/coverage \
      --cov-report=xml:reports/coverage.xml \
      --cov-report=term
```

### Codecov Upload

```yaml
- name: Upload Coverage to Codecov
  uses: codecov/codecov-action@v3
  with:
    file: reports/coverage.xml
    flags: unittests
    fail_ci_if_error: false
  env:
    CODECOV_TOKEN: ${{ secrets.CODECOV_TOKEN }}
```

**Setup:**
1. Sign up at https://codecov.io/
2. Connect GitHub repository
3. Add `CODECOV_TOKEN` to GitHub Secrets
4. Coverage badge appears in README

## Coverage Badges

### GitHub README

```markdown
[![codecov](https://codecov.io/gh/m2-eng/FiniA/branch/main/graph/badge.svg)](https://codecov.io/gh/m2-eng/FiniA)
```

Shows: [![codecov](https://codecov.io/gh/m2-eng/FiniA/branch/main/graph/badge.svg)](https://codecov.io/gh/m2-eng/FiniA)

### Codecov Dashboard

Visit: https://codecov.io/gh/m2-eng/FiniA

**Features:**
- 📊 Coverage trends over time
- 📈 Pull request coverage changes
- 🔍 File-by-file coverage breakdown
- 🎯 Coverage goals and targets
- 💬 Automated PR comments

## Coverage Thresholds

### Current Targets

| Component | Target | Current |
|-----------|--------|---------|
| API Routers | 95% | ~92% |
| Repositories | 90% | ~88% |
| Services | 85% | ~82% |
| Domain Logic | 95% | ~91% |
| **Overall** | **85%** | **~87%** |

### Minimum Threshold

**75%** - Tests will fail if coverage drops below this threshold (configured in `.coveragerc`).

## Excluding Code from Coverage

### Pragma Comments

```python
def debug_only_function():  # pragma: no cover
    """This function is excluded from coverage."""
    print("Debug info")
```

### Configuration (`.coveragerc`)

```ini
exclude_lines =
    pragma: no cover
    def __repr__
    if __name__ == .__main__.:
    if TYPE_CHECKING:
    raise NotImplementedError
    @abstractmethod
```

## Branch Coverage

Branch coverage measures whether **both branches** of conditional statements are executed:

```python
def process_value(x):
    if x > 0:          # Branch coverage checks:
        return x * 2   # ✅ True branch executed?
    else:
        return 0       # ✅ False branch executed?
```

**Enable in pytest:**
```bash
pytest tests/ --cov=src --cov-branch
```

Already enabled in `.coveragerc`:
```ini
[run]
branch = True
```

## Coverage in Pull Requests

### Automated Checks

For every PR, GitHub Actions:
1. ✅ Runs full test suite with coverage
2. ✅ Uploads coverage to Codecov
3. ✅ Codecov comments on PR with coverage changes
4. ✅ Shows coverage diff (added/removed lines)

### Example PR Comment

```
## Codecov Report
Base: 87.45%  |  Head: 88.12%  |  Δ +0.67%

Files changed coverage:
  src/api/routers/transactions.py: 85.34% → 89.23% (+3.89%)
  src/services/import_service.py: 78.12% → 81.45% (+3.33%)
```

## Local Coverage Development

### Watch Mode with pytest-watch

```bash
# Install pytest-watch
pip install pytest-watch

# Watch for changes and run tests with coverage
ptw -- --cov=src --cov-report=term-missing
```

### Coverage for Specific Module

```bash
# Test only API module
pytest tests/integration/test_api_*.py --cov=src.api --cov-report=term

# Test only repositories
pytest tests/integration/test_db_*.py --cov=src.repositories --cov-report=term
```

### Missing Lines Report

```bash
# Show which lines are NOT covered
pytest tests/ --cov=src --cov-report=term-missing

# Output shows line numbers:
# src/api/main.py    88%   45-48, 123-129
#                          ^^^^^^^^^^^^^^^^ these lines not covered
```

## Troubleshooting

### Coverage Not Measured

**Problem:** Coverage shows 0% for all files

**Solution:**
```bash
# Ensure source path is correct
pytest tests/ --cov=src --cov-report=term

# Check .coveragerc configuration
cat .coveragerc
```

### Inaccurate Branch Coverage

**Problem:** Branch coverage shows unexpected results

**Solution:**
```bash
# Enable detailed branch coverage
pytest tests/ --cov=src --cov-branch --cov-report=html

# Open HTML report to see branch details
start reports/coverage/index.html
```

### Codecov Upload Fails

**Problem:** Codecov upload fails in GitHub Actions

**Solution:**
1. Check `CODECOV_TOKEN` is set in GitHub Secrets
2. Verify repository is connected to Codecov
3. Check `reports/coverage.xml` exists
4. Review workflow logs for errors

## Best Practices

### 1. Write Tests for Uncovered Code

```bash
# Find uncovered lines
pytest tests/ --cov=src --cov-report=term-missing | grep "MISS"

# Write tests for those lines
```

### 2. Review Coverage in PRs

- Check Codecov comment on each PR
- Ensure coverage doesn't decrease
- Aim for 100% coverage of new code

### 3. Use Coverage to Find Dead Code

```bash
# Generate HTML report
pytest tests/ --cov=src --cov-report=html

# Red lines in HTML report may indicate:
# - Untested code (write tests!)
# - Dead code (remove it!)
# - Defensive code (mark with pragma: no cover)
```

### 4. Don't Obsess Over 100%

- **80-90% coverage is excellent**
- Focus on **critical paths**
- Some code is intentionally untested (e.g., `__repr__`, debug functions)

## Integration with IDEs

### VS Code

Install **Coverage Gutters** extension:
1. Install: `code --install-extension ryanluker.vscode-coverage-gutters`
2. Run tests with coverage: `pytest tests/ --cov=src --cov-report=xml`
3. Press `Ctrl+Shift+7` to display coverage in editor
4. Lines will be highlighted: green (covered), red (uncovered)

### PyCharm

Built-in coverage support:
1. Run → Run with Coverage
2. View → Tool Windows → Coverage
3. Coverage report appears in editor gutter

## References

- **pytest-cov Documentation:** https://pytest-cov.readthedocs.io/
- **coverage.py Documentation:** https://coverage.readthedocs.io/
- **Codecov Documentation:** https://docs.codecov.io/
- **Issue #32:** [Implementing a test bench](https://github.com/m2-eng/FiniA/issues/32)

---

**Last Updated:** 2026-02-18 (Issue #32 implementation)
