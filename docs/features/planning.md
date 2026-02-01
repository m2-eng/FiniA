# Planning & Budgeting

Documentation of FiniA's planning and budgeting system for recurring transactions.

---

## Overview

FiniA's planning system enables **recurring budget entries** for:

- ✅ **Income** - Salaries, dividends, side income
- ✅ **Expenses** - Rent, utilities, subscriptions
- ✅ **Savings Goals** - Monthly savings targets
- ✅ **Debt Payments** - Loan installments, credit card payments

**Key Features:**
- Flexible cycles (daily, weekly, monthly, yearly, custom)
- Future entry generation (up to end of next year)
- Category-based budgeting
- Account-specific planning
- Start/end date management

---

## Architecture

### Database Tables

#### tbl_planning

**Purpose:** Store recurring budget entries

| Column | Type | Description |
|--------|------|-------------|
| `id` | INT | Primary key |
| `dateImport` | DATETIME | Creation timestamp |
| `description` | VARCHAR(255) | Planning description (e.g., "Monthly Rent") |
| `amount` | DECIMAL(13,2) | Amount (negative = expense, positive = income) |
| `dateStart` | DATE | Start date |
| `dateEnd` | DATE (nullable) | End date (NULL = ongoing) |
| `account` | INT | Foreign key to tbl_account |
| `category` | INT | Foreign key to tbl_category |
| `cycle` | INT | Foreign key to tbl_planningCycle |

**Example:**
```sql
INSERT INTO tbl_planning (description, amount, dateStart, dateEnd, account, category, cycle)
VALUES ('Monthly Rent', -800.00, '2025-01-01', NULL, 1, 5, 1);
```

---

#### tbl_planningEntry

**Purpose:** Store generated planning occurrences

| Column | Type | Description |
|--------|------|-------------|
| `id` | INT | Primary key |
| `dateImport` | DATETIME | Generation timestamp |
| `dateValue` | DATE | Occurrence date |
| `planning` | INT | Foreign key to tbl_planning |

**Example:**
```sql
-- Generated entries for monthly rent
INSERT INTO tbl_planningEntry (dateValue, planning)
VALUES 
  ('2025-01-01', 1),
  ('2025-02-01', 1),
  ('2025-03-01', 1);
```

---

#### tbl_planningCycle

**Purpose:** Define recurrence patterns

| Column | Type | Description |
|--------|------|-------------|
| `id` | INT | Primary key |
| `dateImport` | DATETIME | Creation timestamp |
| `cycle` | VARCHAR(255) | Cycle name (e.g., "Monthly") |
| `periodValue` | DECIMAL(10,2) (nullable) | Numeric period (e.g., 1, 14) |
| `periodUnit` | VARCHAR(10) (nullable) | Unit: 'd' (days), 'm' (months), 'y' (years) |

**Example:**
```sql
-- Predefined cycles
INSERT INTO tbl_planningCycle (id, cycle, periodValue, periodUnit)
VALUES
  (1, 'Monthly', 1, 'm'),
  (2, 'Yearly', 1, 'y'),
  (3, 'Quarterly', 3, 'm'),
  (4, 'Bi-Weekly', 14, 'd');
```

---

### Views

#### view_balancesPlanning

**Purpose:** Calculate planned balances by account and month

```sql
CREATE VIEW view_balancesPlanning AS
SELECT
    a.id AS account_id,
    a.name AS account_name,
    DATE_FORMAT(pe.dateValue, '%Y-%m') AS month,
    SUM(p.amount) AS planned_balance
FROM tbl_planningEntry pe
JOIN tbl_planning p ON pe.planning = p.id
JOIN tbl_account a ON p.account = a.id
GROUP BY a.id, month;
```

**Usage:**
```sql
-- Get planned balance for account 1 in January 2025
SELECT planned_balance
FROM view_balancesPlanning
WHERE account_id = 1 AND month = '2025-01';
```

---

## Planning Cycles

### Predefined Cycles

| ID | Cycle | periodValue | periodUnit | Description |
|----|-------|-------------|------------|-------------|
| 1 | Monthly | 1 | m | Every month |
| 2 | Yearly | 1 | y | Every year |
| 3 | Quarterly | 3 | m | Every 3 months |
| 4 | Bi-Weekly | 14 | d | Every 14 days |
| 5 | Weekly | 7 | d | Every 7 days |
| 6 | Semi-Annually | 6 | m | Every 6 months |
| 7 | Daily | 1 | d | Every day |
| 8 | Once | NULL | NULL | Single occurrence |

---

### Cycle Resolution

FiniA supports **3 cycle formats**:

#### Format 1: Structured (Preferred)

Uses `periodValue` + `periodUnit`:

```python
# Monthly: periodValue=1, periodUnit='m'
# Quarterly: periodValue=3, periodUnit='m'
# Yearly: periodValue=1, periodUnit='y'
# Bi-Weekly: periodValue=14, periodUnit='d'
```

**Units:**
- `d` - Days (integer or decimal)
- `m` - Months (integer, uses calendar logic)
- `y` - Years (converted to months: 1y = 12m)

---

#### Format 2: Name-based (Legacy)

Infers from cycle name:

```python
# Name contains "woche" or "week" → 7 days
# Name contains "quart" → 3 months
# Name contains "jahr" or "year" → 12 months
# Name contains "halb" or "semi" → 6 months
# Name contains "tag" or "day" → 1 day
# Name contains "einmal" or "once" → single occurrence
```

---

#### Format 3: Fallback

Default to monthly if no match:

```python
# Unknown cycle → 1 month
```

---

### Date Advancement Logic

```python
def _advance_date(current: date, interval: dict) -> date:
    if interval.get("once"):
        return current  # No advancement for one-time entries
    
    if "months" in interval:
        # Calendar-aware month addition
        months = int(interval["months"])
        return _add_months(current, months)
    
    if "days" in interval:
        # Simple day addition
        days = int(interval["days"])
        return current + timedelta(days=days)
    
    # Fallback: 30 days
    return current + timedelta(days=30)

def _add_months(current: date, months: int) -> date:
    """Add months with calendar awareness (handles month-end dates)."""
    month_index = current.month - 1 + months
    year = current.year + month_index // 12
    month = month_index % 12 + 1
    last_day = calendar.monthrange(year, month)[1]
    
    # Handle day overflow (e.g., Jan 31 + 1 month = Feb 28)
    return current.replace(
        year=year,
        month=month,
        day=min(current.day, last_day)
    )
```

**Examples:**

```python
# Monthly: Jan 15 → Feb 15 → Mar 15
advance_date(date(2025, 1, 15), {"months": 1})  # → Feb 15

# Monthly (month-end): Jan 31 → Feb 28 → Mar 31
advance_date(date(2025, 1, 31), {"months": 1})  # → Feb 28
advance_date(date(2025, 2, 28), {"months": 1})  # → Mar 28 (preserves day 28)

# Bi-Weekly: Jan 15 → Jan 29 → Feb 12
advance_date(date(2025, 1, 15), {"days": 14})  # → Jan 29

# Yearly: Jan 15, 2025 → Jan 15, 2026
advance_date(date(2025, 1, 15), {"months": 12})  # → Jan 15, 2026
```

---

## CRUD Operations

### Create Planning

**API Endpoint:** `POST /api/planning/`

**Request Body:**

```json
{
  "description": "Monthly Rent",
  "amount": -800.00,
  "dateStart": "2025-01-01",
  "dateEnd": null,
  "account_id": 1,
  "category_id": 5,
  "cycle_id": 1
}
```

**Response:**

```json
{
  "id": 1,
  "dateImport": "2025-01-15T10:30:00",
  "description": "Monthly Rent",
  "amount": -800.00,
  "dateStart": "2025-01-01",
  "dateEnd": null,
  "account_id": 1,
  "account_name": "Personal Checking",
  "category_id": 5,
  "category_name": "Living Expenses - Rent",
  "cycle_id": 1,
  "cycle_name": "Monthly"
}
```

**Repository Method:**

```python
from repositories.planning_repository import PlanningRepository
from decimal import Decimal
from datetime import datetime

repo = PlanningRepository(cursor)

planning_id = repo.create_planning(
    description="Monthly Rent",
    amount=Decimal("-800.00"),
    date_start=datetime(2025, 1, 1),
    date_end=None,  # Ongoing
    account_id=1,
    category_id=5,
    cycle_id=1  # Monthly
)
```

---

### Read Planning

**API Endpoint:** `GET /api/planning/{planning_id}`

**Response:**

```json
{
  "id": 1,
  "dateImport": "2025-01-15T10:30:00",
  "description": "Monthly Rent",
  "amount": -800.00,
  "dateStart": "2025-01-01",
  "dateEnd": null,
  "account_id": 1,
  "account_name": "Personal Checking",
  "category_id": 5,
  "category_name": "Living Expenses - Rent",
  "cycle_id": 1,
  "cycle_name": "Monthly"
}
```

**Repository Method:**

```python
repo = PlanningRepository(cursor)
planning = repo.get_planning_by_id(planning_id=1)
```

---

### List Plannings (Paginated)

**API Endpoint:** `GET /api/planning/?page=1&page_size=50`

**Response:**

```json
{
  "plannings": [
    {
      "id": 1,
      "description": "Monthly Rent",
      "amount": -800.00,
      "dateStart": "2025-01-01",
      "dateEnd": null,
      "account_name": "Personal Checking",
      "category_name": "Living Expenses - Rent",
      "cycle_name": "Monthly"
    },
    {
      "id": 2,
      "description": "Salary",
      "amount": 3000.00,
      "dateStart": "2025-01-01",
      "dateEnd": null,
      "account_name": "Personal Checking",
      "category_name": "Income - Salary",
      "cycle_name": "Monthly"
    }
  ],
  "page": 1,
  "page_size": 50,
  "total": 2
}
```

**Repository Method:**

```python
repo = PlanningRepository(cursor)
result = repo.get_plannings_paginated(page=1, page_size=50)
```

---

### Update Planning

**API Endpoint:** `PUT /api/planning/{planning_id}`

**Request Body:**

```json
{
  "description": "Monthly Rent (Updated)",
  "amount": -850.00,
  "dateStart": "2025-02-01",
  "dateEnd": "2026-01-31",
  "account_id": 1,
  "category_id": 5,
  "cycle_id": 1
}
```

**Repository Method:**

```python
repo = PlanningRepository(cursor)

success = repo.update_planning(
    planning_id=1,
    description="Monthly Rent (Updated)",
    amount=Decimal("-850.00"),
    date_start=datetime(2025, 2, 1),
    date_end=datetime(2026, 1, 31),
    account_id=1,
    category_id=5,
    cycle_id=1
)
```

---

### Delete Planning

**API Endpoint:** `DELETE /api/planning/{planning_id}`

**Response:** `204 No Content`

**Repository Method:**

```python
repo = PlanningRepository(cursor)
deleted = repo.delete_planning(planning_id=1)
# Returns: True if deleted, False if not found
```

**Cascade Behavior:**
- Deletes all `tbl_planningEntry` records for this planning
- Deletes the `tbl_planning` record

---

## Planning Entry Generation

### Generate Entries

**API Endpoint:** `POST /api/planning/{planning_id}/entries/generate`

**Process:**

1. Load planning configuration
2. Load planning cycle
3. Calculate end date: `min(planning.dateEnd, end_of_next_year)`
4. Delete existing entries for this planning
5. Generate new entries from `dateStart` to end date
6. Insert entries into `tbl_planningEntry`

**Response:**

```json
{
  "planning_id": 1,
  "entries": [
    {
      "id": 1,
      "dateImport": "2025-01-15T10:30:00",
      "dateValue": "2025-01-01",
      "planning_id": 1
    },
    {
      "id": 2,
      "dateImport": "2025-01-15T10:30:00",
      "dateValue": "2025-02-01",
      "planning_id": 1
    },
    ...
  ],
  "total": 12
}
```

**Repository Method:**

```python
from datetime import date

repo = PlanningRepository(cursor)

entries = repo.regenerate_planning_entries(
    planning_id=1,
    today=date.today()  # Optional, defaults to today
)
```

---

### Generation Logic

```python
def regenerate_planning_entries(planning_id: int, today: date = None) -> list[dict]:
    """
    Generate planning entries up to min(planning end date, end of next year).
    
    Args:
        planning_id: Planning to generate entries for
        today: Reference date (default: today)
        
    Returns:
        List of generated entries
    """
    planning = get_planning_by_id(planning_id)
    cycle = get_cycle(planning['cycle_id'])
    interval = resolve_cycle_interval(cycle)
    
    base_today = today or date.today()
    end_of_next_year = date(base_today.year + 1, 12, 31)
    
    # Cap at end of next year
    if planning['dateEnd']:
        target_end = min(planning['dateEnd'].date(), end_of_next_year)
    else:
        target_end = end_of_next_year
    
    current_date = planning['dateStart'].date()
    entries_to_create = []
    
    # Generate dates
    while current_date <= target_end:
        entries_to_create.append(current_date)
        
        if interval.get('once'):
            break  # One-time entry
        
        current_date = advance_date(current_date, interval)
    
    # Delete existing entries
    delete_planning_entries(planning_id)
    
    # Insert new entries
    for entry_date in entries_to_create:
        insert_planning_entry(planning_id, entry_date)
    
    return get_planning_entries(planning_id)
```

**Generation Limits:**
- **Time Horizon:** Up to December 31 of next year
- **Safety Guard:** Max 10,000 iterations (prevents infinite loops)
- **Replacement:** Existing entries are deleted and regenerated

---

### Delete Planning Entry

**API Endpoint:** `DELETE /api/planning/{planning_id}/entries/{entry_id}`

**Response:** `204 No Content`

**Repository Method:**

```python
repo = PlanningRepository(cursor)
deleted = repo.delete_planning_entry(
    planning_id=1,
    entry_id=5
)
# Returns: True if deleted, False if not found
```

**Use Case:** Remove a specific occurrence (e.g., skip a month)

---

## Usage Examples

### Example 1: Monthly Rent

```python
# Create planning
planning_id = repo.create_planning(
    description="Monthly Rent",
    amount=Decimal("-800.00"),
    date_start=datetime(2025, 1, 1),
    date_end=None,  # Ongoing
    account_id=1,
    category_id=5,  # Living Expenses - Rent
    cycle_id=1  # Monthly
)

# Generate entries
entries = repo.regenerate_planning_entries(planning_id)
# Creates 12-24 entries (depending on current month)
```

**Generated Entries:**
- 2025-01-01
- 2025-02-01
- 2025-03-01
- ...
- 2026-12-01

---

### Example 2: Bi-Weekly Salary

```python
# Create planning
planning_id = repo.create_planning(
    description="Salary",
    amount=Decimal("1500.00"),
    date_start=datetime(2025, 1, 15),
    date_end=datetime(2025, 12, 31),
    account_id=1,
    category_id=10,  # Income - Salary
    cycle_id=4  # Bi-Weekly (14 days)
)

# Generate entries
entries = repo.regenerate_planning_entries(planning_id)
```

**Generated Entries:**
- 2025-01-15
- 2025-01-29
- 2025-02-12
- 2025-02-26
- ...
- 2025-12-31 (or earlier)

---

### Example 3: Quarterly Taxes

```python
# Create planning
planning_id = repo.create_planning(
    description="Quarterly Taxes",
    amount=Decimal("-1200.00"),
    date_start=datetime(2025, 3, 31),
    date_end=None,
    account_id=2,
    category_id=15,  # Taxes
    cycle_id=3  # Quarterly (3 months)
)

# Generate entries
entries = repo.regenerate_planning_entries(planning_id)
```

**Generated Entries:**
- 2025-03-31
- 2025-06-30
- 2025-09-30
- 2025-12-31
- 2026-03-31
- ...

---

### Example 4: One-Time Bonus

```python
# Create planning
planning_id = repo.create_planning(
    description="Year-End Bonus",
    amount=Decimal("5000.00"),
    date_start=datetime(2025, 12, 20),
    date_end=None,
    account_id=1,
    category_id=11,  # Income - Bonus
    cycle_id=8  # Once
)

# Generate entries
entries = repo.regenerate_planning_entries(planning_id)
# Creates exactly 1 entry: 2025-12-20
```

---

## Integration with Other Features

### Year Overview

**View:** `view_balancesPlanning`

```sql
-- Get planned balance for 2025-01
SELECT account_name, planned_balance
FROM view_balancesPlanning
WHERE month = '2025-01';
```

**Result:**
| account_name | planned_balance |
|--------------|-----------------|
| Personal Checking | -800.00 (rent) + 3000.00 (salary) = 2200.00 |

---

### Budget vs Actual

Compare planned vs actual transactions:

```sql
-- Planned balance for January 2025
SELECT SUM(p.amount) AS planned
FROM tbl_planningEntry pe
JOIN tbl_planning p ON pe.planning = p.id
WHERE pe.dateValue BETWEEN '2025-01-01' AND '2025-01-31';

-- Actual balance for January 2025
SELECT SUM(t.amount) AS actual
FROM tbl_transaction t
WHERE t.dateValue BETWEEN '2025-01-01' AND '2025-01-31';

-- Variance
SELECT planned - actual AS variance;
```

---

### Category Budgets

Get planned spending by category:

```sql
SELECT
    c.name AS category,
    SUM(p.amount) AS planned_amount
FROM tbl_planningEntry pe
JOIN tbl_planning p ON pe.planning = p.id
JOIN tbl_category c ON p.category = c.id
WHERE pe.dateValue BETWEEN '2025-01-01' AND '2025-12-31'
GROUP BY c.id
ORDER BY planned_amount ASC;
```

**Result:**
| category | planned_amount |
|----------|----------------|
| Living Expenses - Rent | -9600.00 |
| Living Expenses - Utilities | -1200.00 |
| Income - Salary | 36000.00 |

---

## API Reference

### Planning Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/planning/` | List plannings (paginated) |
| `POST` | `/api/planning/` | Create planning |
| `GET` | `/api/planning/{id}` | Get planning by ID |
| `PUT` | `/api/planning/{id}` | Update planning |
| `DELETE` | `/api/planning/{id}` | Delete planning |
| `GET` | `/api/planning/{id}/entries` | Get planning entries |
| `POST` | `/api/planning/{id}/entries/generate` | Generate entries |
| `DELETE` | `/api/planning/{id}/entries/{entry_id}` | Delete entry |
| `GET` | `/api/planning/cycles` | List planning cycles |

**See:** [API Documentation](../api.md) for detailed endpoint specs

---

## Best Practices

### ✅ DO

**1. Use Structured Cycles**

```python
# Good: Explicit periodValue + periodUnit
cycle = {
    'cycle': 'Bi-Weekly',
    'periodValue': 14,
    'periodUnit': 'd'
}

# Bad: Rely on name parsing
cycle = {
    'cycle': 'Every Two Weeks',  # Won't parse correctly
    'periodValue': None,
    'periodUnit': None
}
```

**2. Set End Dates for Temporary Planning**

```python
# Good: Limited-term planning
planning = {
    'dateStart': '2025-01-01',
    'dateEnd': '2025-12-31',  # 1-year lease
    ...
}

# Bad: Ongoing for temporary situation
planning = {
    'dateStart': '2025-01-01',
    'dateEnd': None,  # Will generate entries forever
    ...
}
```

**3. Regenerate After Changes**

```python
# Good: Regenerate after update
repo.update_planning(planning_id=1, amount=-850.00, ...)
repo.regenerate_planning_entries(planning_id=1)

# Bad: Update without regenerating
repo.update_planning(planning_id=1, amount=-850.00, ...)
# Old entries still have -800.00!
```

---

### ❌ DON'T

**1. Create Entries Manually**

```python
# Bad: Manual entry creation
for i in range(12):
    repo.insert_planning_entry(planning_id, date + timedelta(days=30*i))

# Good: Use generation
repo.regenerate_planning_entries(planning_id)
```

**2. Mix Amounts in One Planning**

```python
# Bad: Variable amounts in one planning
planning = {
    'amount': -800.00,  # Amount changes per month?
    ...
}

# Good: Create separate plannings
planning_rent_1 = {'amount': -800.00, 'dateEnd': '2025-06-30', ...}
planning_rent_2 = {'amount': -850.00, 'dateStart': '2025-07-01', ...}
```

---

## Troubleshooting

### Entries Not Generated

**Symptom:** No entries after calling `regenerate_planning_entries()`

**Causes:**
1. `dateStart` is in the future beyond next year
2. `dateEnd` is before `dateStart`
3. Cycle configuration is invalid

**Solution:**

```python
# Check planning configuration
planning = repo.get_planning_by_id(planning_id)
print(f"Start: {planning['dateStart']}")
print(f"End: {planning['dateEnd']}")
print(f"Cycle: {planning['cycle_id']}")

# Check cycle configuration
cycle = repo.get_cycle_by_id(planning['cycle_id'])
print(f"Cycle: {cycle}")
```

---

### Wrong Number of Entries

**Symptom:** Too many or too few entries generated

**Causes:**
1. End date extends beyond next year
2. Cycle interval is too small (e.g., daily for 2 years)
3. Safety guard triggered (10,000 iterations)

**Solution:**

```python
# Check generation range
planning = repo.get_planning_by_id(planning_id)
today = date.today()
end_of_next_year = date(today.year + 1, 12, 31)

print(f"Start: {planning['dateStart']}")
print(f"Target End: {min(planning['dateEnd'] or end_of_next_year, end_of_next_year)}")

# Verify cycle interval
cycle = repo.get_cycle_by_id(planning['cycle_id'])
interval = repo._resolve_cycle_interval(cycle)
print(f"Interval: {interval}")
```

---

### Month-End Date Issues

**Symptom:** Dates shift on months with fewer days

**Example:**
- Start: Jan 31
- Expected: Feb 28, Mar 31, Apr 30
- Actual: Feb 28, Mar 28, Apr 28

**Cause:** Day preservation after month-end adjustment

**Solution:**

Use first day of month for monthly planning:

```python
# Good: Start on first day
planning = {
    'dateStart': '2025-01-01',  # Avoids day overflow
    ...
}

# Bad: Start on last day
planning = {
    'dateStart': '2025-01-31',  # Will shift to 28th/30th
    ...
}
```

---

## Related Documentation

- [Database Schema](../database/schema.md) - Planning tables structure
- [API Documentation](../api.md) - Planning endpoints
- [Repository Pattern](../architecture/repositories.md) - PlanningRepository details
- [Getting Started Tutorial](../tutorials/getting_started.md) - Planning examples

---

## Summary

FiniA's planning system provides:

✅ **Flexible Cycles** - Daily, weekly, monthly, yearly, custom intervals  
✅ **Future Planning** - Generate up to end of next year  
✅ **Budget Tracking** - Compare planned vs actual  
✅ **Category-based** - Budget by expense/income category  
✅ **Account-specific** - Plan per account  
✅ **Easy Management** - CRUD operations via API  

**Perfect for recurring income/expenses and budget planning.**
