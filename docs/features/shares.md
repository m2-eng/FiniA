# Share Portfolio Management

Documentation of FiniA's securities portfolio management system for tracking stocks, ETFs, and other securities.

---

## Overview

FiniA's share portfolio system enables comprehensive **securities tracking**:

- ✅ **Holdings Management** - Track multiple securities (stocks, ETFs, funds)
- ✅ **Transaction History** - Buy, sell, dividend transactions
- ✅ **Price History** - Historical price tracking
- ✅ **Portfolio Valuation** - Automatic portfolio value calculation
- ✅ **Monthly Snapshots** - Historical portfolio values
- ✅ **Performance Analysis** - Investments, proceeds, net cash flow

**Key Features:**
- ISIN/WKN identification (international + German standards)
- Automatic volume calculation (cumulative transactions)
- Current price tracking
- Portfolio value calculation (volume × price)
- Accounting entry integration (cash flow tracking)

---

## Architecture

### Database Tables

#### tbl_share

**Purpose:** Store securities master data

| Column | Type | Description |
|--------|------|-------------|
| `id` | BIGINT | Primary key (auto-increment) |
| `dateImport` | DATETIME | Creation timestamp |
| `name` | VARCHAR(128) | Security name (e.g., "Apple Inc.") |
| `isin` | VARCHAR(12) | International Security ID (e.g., "US0378331005") |
| `wkn` | VARCHAR(6) | German Security ID (e.g., "865985") |

**Example:**
```sql
INSERT INTO tbl_share (name, isin, wkn)
VALUES ('Apple Inc.', 'US0378331005', '865985');
```

**Identification:**
- **ISIN** - International standard (12 alphanumeric chars)
- **WKN** - German standard (6 alphanumeric chars)
- **Priority:** ISIN has priority over WKN in lookups

---

#### tbl_shareTransaction

**Purpose:** Store buy/sell/dividend transactions

| Column | Type | Description |
|--------|------|-------------|
| `id` | BIGINT | Primary key (auto-increment) |
| `dateImport` | DATETIME | Creation timestamp |
| `tradingVolume` | DECIMAL(20,10) | Volume change (+buy, -sell, 0=dividend) |
| `dateTransaction` | DATETIME | Transaction date |
| `checked` | TINYINT | Verification status (0=unchecked, 1=checked) |
| `share` | BIGINT | Foreign key to tbl_share |
| `accountingEntry` | BIGINT (nullable) | Foreign key to tbl_accountingEntry (cash flow) |

**Transaction Types:**
- **Buy:** `tradingVolume > 0` (e.g., +10 shares)
- **Sell:** `tradingVolume < 0` (e.g., -5 shares)
- **Dividend:** `tradingVolume = 0` (no volume change, cash flow only)

**Example:**
```sql
-- Buy 10 shares
INSERT INTO tbl_shareTransaction (tradingVolume, dateTransaction, share, accountingEntry)
VALUES (10, '2025-01-15', 1, 123);

-- Sell 5 shares
INSERT INTO tbl_shareTransaction (tradingVolume, dateTransaction, share, accountingEntry)
VALUES (-5, '2025-06-20', 1, 456);

-- Dividend payment
INSERT INTO tbl_shareTransaction (tradingVolume, dateTransaction, share, accountingEntry)
VALUES (0, '2025-03-31', 1, 789);
```

---

#### tbl_shareHistory

**Purpose:** Store historical price data

| Column | Type | Description |
|--------|------|-------------|
| `id` | BIGINT | Primary key (auto-increment) |
| `dateImport` | DATETIME | Creation timestamp |
| `amount` | DECIMAL(20,10) | Share price |
| `date` | DATE | Price date |
| `checked` | TINYINT | Verification status (0=unchecked, 1=checked) |
| `share` | BIGINT | Foreign key to tbl_share |

**Example:**
```sql
-- Daily prices for Apple Inc.
INSERT INTO tbl_shareHistory (amount, date, share)
VALUES
  (150.00, '2025-01-15', 1),
  (152.50, '2025-01-31', 1),
  (148.75, '2025-02-15', 1);
```

**Constraints:**
- Unique constraint: `(share, date)` - One price per share per day
- Used for portfolio valuation and charts

---

### Views

#### view_sharePortfolioValue

**Purpose:** Calculate current portfolio value per share

```sql
CREATE VIEW view_sharePortfolioValue AS
SELECT
  s.id,
  s.name,
  s.isin,
  s.wkn,
  COALESCE(SUM(t.tradingVolume), 0) AS currentVolume,
  COALESCE(latest_history.amount, 0) AS currentPrice,
  COALESCE(SUM(t.tradingVolume), 0) * COALESCE(latest_history.amount, 0) AS portfolioValue
FROM tbl_share s
LEFT JOIN tbl_shareTransaction t ON t.share = s.id
LEFT JOIN (
  SELECT h.share, h.amount, h.date
  FROM tbl_shareHistory h
  INNER JOIN (
    SELECT share, MAX(date) AS latest_date
    FROM tbl_shareHistory
    GROUP BY share
  ) latest ON h.share = latest.share AND h.date = latest.latest_date
) latest_history ON s.id = latest_history.share
GROUP BY s.id, s.name, s.isin, s.wkn, latest_history.amount;
```

**Columns:**
- `id`, `name`, `isin`, `wkn` - Share identification
- `currentVolume` - Sum of all `tradingVolume` (cumulative holdings)
- `currentPrice` - Latest price from `tbl_shareHistory`
- `portfolioValue` - `currentVolume × currentPrice`

**Usage:**
```sql
-- Get current portfolio value for all shares
SELECT name, currentVolume, currentPrice, portfolioValue
FROM view_sharePortfolioValue
WHERE currentVolume != 0;  -- Only shares currently held
```

---

#### view_shareMonthlySnapshot

**Purpose:** Historical portfolio values at month-end

```sql
CREATE VIEW view_shareMonthlySnapshot AS
WITH RECURSIVE months AS (
  -- Generate month-ends from earliest history to 1 year in future
  SELECT LAST_DAY(MIN(date)) AS month_end_date
  FROM tbl_shareHistory
  UNION ALL
  SELECT LAST_DAY(month_end_date + INTERVAL 1 MONTH)
  FROM months
  WHERE month_end_date < LAST_DAY(CURRENT_DATE + INTERVAL 1 YEAR)
),
latest_prices AS (
  -- For each share/month: latest price before/on month-end
  SELECT
    me.share,
    me.month_end_date,
    MAX(sh.date) AS latest_price_date
  FROM month_ends me
  INNER JOIN tbl_shareHistory sh ON sh.share = me.share
    AND DATE(sh.date) <= DATE(me.month_end_date)
  GROUP BY me.share, me.month_end_date
)
SELECT
  h.share AS share_id,
  s.name AS share_name,
  lp.month_end_date,
  h.amount AS price,
  COALESCE(SUM(t.tradingVolume), 0) AS volume,
  h.amount * COALESCE(SUM(t.tradingVolume), 0) AS portfolio_value
FROM latest_prices lp
INNER JOIN tbl_shareHistory h ON h.share = lp.share AND h.date = lp.latest_price_date
INNER JOIN tbl_share s ON s.id = h.share
LEFT JOIN tbl_shareTransaction t ON t.share = h.share AND DATE(t.dateTransaction) <= lp.month_end_date
GROUP BY h.share, s.name, lp.month_end_date, h.amount;
```

**Columns:**
- `share_id`, `share_name` - Share identification
- `month_end_date` - Last day of month
- `price` - Price on/before month-end
- `volume` - Cumulative holdings at month-end
- `portfolio_value` - `volume × price`

**Usage:**
```sql
-- Get portfolio evolution for 2025
SELECT share_name, month_end_date, volume, price, portfolio_value
FROM view_shareMonthlySnapshot
WHERE YEAR(month_end_date) = 2025
ORDER BY month_end_date, share_name;
```

---

## CRUD Operations

### Shares

#### Create Share

**API Endpoint:** `POST /api/shares/`

**Request Body:**
```json
{
  "name": "Apple Inc.",
  "isin": "US0378331005",
  "wkn": "865985"
}
```

**Response:**
```json
{
  "id": 1,
  "dateImport": "2025-01-15T10:30:00",
  "name": "Apple Inc.",
  "isin": "US0378331005",
  "wkn": "865985",
  "currentVolume": 0,
  "currentPrice": 0,
  "portfolioValue": 0
}
```

**Repository Method:**
```python
from repositories.share_repository import ShareRepository

repo = ShareRepository(cursor)
share_id = repo.insert_share(
    name="Apple Inc.",
    isin="US0378331005",
    wkn="865985"
)
```

---

#### Read Share

**API Endpoint:** `GET /api/shares/{share_id}`

**Response:**
```json
{
  "id": 1,
  "name": "Apple Inc.",
  "isin": "US0378331005",
  "wkn": "865985",
  "currentVolume": 10,
  "currentPrice": 150.00,
  "portfolioValue": 1500.00
}
```

**Repository Method:**
```python
repo = ShareRepository(cursor)
share = repo.get_share_by_id(share_id=1)
```

---

#### List Shares (Paginated)

**API Endpoint:** `GET /api/shares/?page=1&page_size=50&search=Apple&holdings_filter=in_stock&sort_by=portfolioValue&sort_dir=desc`

**Query Parameters:**
- `page` - Page number (default: 1)
- `page_size` - Records per page (default: 50, max: 1000)
- `search` - Search name/ISIN/WKN (optional)
- `holdings_filter` - Filter options:
  - `in_stock` - Only shares with `currentVolume != 0`
  - `incomplete` - Only shares with missing name or WKN
  - `null` - All shares
- `sort_by` - Sort column: `name`, `wkn`, `isin`, `currentVolume`, `currentPrice`, `portfolioValue`, `investments`, `proceeds`, `net`
- `sort_dir` - Sort direction: `asc`, `desc` (default: `asc`)

**Response:**
```json
{
  "shares": [
    {
      "id": 1,
      "name": "Apple Inc.",
      "isin": "US0378331005",
      "wkn": "865985",
      "currentVolume": 10,
      "currentPrice": 150.00,
      "portfolioValue": 1500.00,
      "investments": 1505.00,
      "proceeds": 0,
      "net": -1505.00,
      "dividends": 25.00
    }
  ],
  "page": 1,
  "page_size": 50,
  "total": 1
}
```

**Aggregated Fields:**
- `investments` - Sum of buy transaction amounts (absolute value)
- `proceeds` - Sum of sell transaction amounts (absolute value)
- `net` - Total cash flow (investments - proceeds + dividends)
- `dividends` - Sum of dividend payments

**Repository Method:**
```python
repo = ShareRepository(cursor)
result = repo.get_all_shares_paginated(
    page=1,
    page_size=50,
    search="Apple",
    holdings_filter="in_stock",
    sort_by="portfolioValue",
    sort_dir="desc"
)
```

---

#### Update Share

**API Endpoint:** `PUT /api/shares/{share_id}`

**Request Body:**
```json
{
  "name": "Apple Inc. (Updated)",
  "isin": "US0378331005",
  "wkn": "865985"
}
```

**Repository Method:**
```python
repo = ShareRepository(cursor)
updated = repo.update_share(
    share_id=1,
    name="Apple Inc. (Updated)",
    isin="US0378331005",
    wkn="865985"
)
```

---

#### Delete Share

**API Endpoint:** `DELETE /api/shares/{share_id}`

**Response:** `204 No Content`

**Repository Method:**
```python
repo = ShareRepository(cursor)
deleted = repo.delete_share(share_id=1)
```

**Cascade Behavior:**
- Deletes all `tbl_shareTransaction` records for this share
- Deletes all `tbl_shareHistory` records for this share

---

### Share Transactions

#### Create Transaction

**API Endpoint:** `POST /api/shares/{share_id}/transactions`

**Request Body (Buy):**
```json
{
  "tradingVolume": 10,
  "dateTransaction": "2025-01-15T10:00:00",
  "accountingEntry": 123
}
```

**Request Body (Sell):**
```json
{
  "tradingVolume": -5,
  "dateTransaction": "2025-06-20T14:00:00",
  "accountingEntry": 456
}
```

**Request Body (Dividend):**
```json
{
  "tradingVolume": 0,
  "dateTransaction": "2025-03-31T09:00:00",
  "accountingEntry": 789
}
```

**Repository Method:**
```python
from repositories.share_transaction_repository import ShareTransactionRepository

repo = ShareTransactionRepository(cursor)

# Buy 10 shares
tx_id = repo.insert_transaction(
    share_id=1,
    trading_volume=10,
    date_str="2025-01-15T10:00:00",
    accounting_entry_id=123  # Link to accounting entry
)
```

---

#### List Transactions

**API Endpoint:** `GET /api/shares/{share_id}/transactions?page=1&page_size=50`

**Response:**
```json
{
  "transactions": [
    {
      "id": 1,
      "dateImport": "2025-01-15T10:30:00",
      "tradingVolume": 10,
      "dateTransaction": "2025-01-15T10:00:00",
      "checked": false,
      "share": 1,
      "share_name": "Apple Inc.",
      "isin": "US0378331005",
      "wkn": "865985",
      "accountingEntry": 123,
      "accountingEntry_amount": -1505.00
    }
  ],
  "page": 1,
  "page_size": 50,
  "total": 1
}
```

**Repository Method:**
```python
repo = ShareTransactionRepository(cursor)
result = repo.get_by_share_paginated(
    share_id=1,
    page=1,
    page_size=50
)
```

---

#### Update Transaction

**API Endpoint:** `PUT /api/shares/transactions/{transaction_id}`

**Request Body:**
```json
{
  "share_id": 1,
  "tradingVolume": 12,
  "dateTransaction": "2025-01-15T10:00:00",
  "accountingEntry": 123
}
```

**Repository Method:**
```python
repo = ShareTransactionRepository(cursor)
updated = repo.update_transaction(
    transaction_id=1,
    share_id=1,
    trading_volume=12,
    date_str="2025-01-15T10:00:00",
    accounting_entry_id=123
)
```

---

#### Delete Transaction

**API Endpoint:** `DELETE /api/shares/transactions/{transaction_id}`

**Response:** `204 No Content`

**Repository Method:**
```python
repo = ShareTransactionRepository(cursor)
deleted = repo.delete_transaction(transaction_id=1)
```

---

### Price History

#### Import Price History (CSV)

**API Endpoint:** `POST /api/shares/import/history`

**CSV Format:**
```csv
ISIN,Date,Price
US0378331005,2025-01-15,150.00
US0378331005,2025-01-31,152.50
US0378331005,2025-02-15,148.75
```

**Request:**
```bash
curl -X POST http://localhost:8000/api/shares/import/history \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@apple_prices.csv"
```

**Response:**
```json
{
  "status": "success",
  "imported": 3,
  "duplicates": 0,
  "errors": 0
}
```

---

#### Create Price Entry

**API Endpoint:** `POST /api/shares/{share_id}/history`

**Request Body:**
```json
{
  "amount": 150.00,
  "date": "2025-01-15"
}
```

**Repository Method:**
```python
from repositories.share_history_repository import ShareHistoryRepository

repo = ShareHistoryRepository(cursor)
history_id = repo.insert_history(
    share_id=1,
    amount=Decimal("150.00"),
    date_str="2025-01-15"
)
```

---

#### List Price History

**API Endpoint:** `GET /api/shares/{share_id}/history?page=1&page_size=50`

**Response:**
```json
{
  "history": [
    {
      "id": 1,
      "dateImport": "2025-01-15T10:30:00",
      "amount": 150.00,
      "date": "2025-01-15",
      "checked": false,
      "share": 1,
      "share_name": "Apple Inc.",
      "isin": "US0378331005",
      "wkn": "865985"
    }
  ],
  "page": 1,
  "page_size": 50,
  "total": 1
}
```

**Repository Method:**
```python
repo = ShareHistoryRepository(cursor)
result = repo.get_all_by_share_paginated(
    share_id=1,
    page=1,
    page_size=50
)
```

---

#### Update Price Entry

**API Endpoint:** `PUT /api/shares/history/{history_id}`

**Request Body:**
```json
{
  "share_id": 1,
  "amount": 152.00,
  "date": "2025-01-15"
}
```

**Repository Method:**
```python
repo = ShareHistoryRepository(cursor)
updated = repo.update_history(
    history_id=1,
    share_id=1,
    amount=Decimal("152.00"),
    date_str="2025-01-15"
)
```

---

#### Delete Price Entry

**API Endpoint:** `DELETE /api/shares/history/{history_id}`

**Response:** `204 No Content`

**Repository Method:**
```python
repo = ShareHistoryRepository(cursor)
deleted = repo.delete_history(history_id=1)
```

---

## Portfolio Calculations

### Current Portfolio Value

```python
from repositories.share_repository import ShareRepository

repo = ShareRepository(cursor)
shares = repo.get_all_shares_paginated(holdings_filter="in_stock")

total_portfolio_value = sum(share['portfolioValue'] for share in shares['shares'])
print(f"Total Portfolio Value: {total_portfolio_value}")
```

**Formula:**
```
portfolioValue = currentVolume × currentPrice
currentVolume = SUM(tradingVolume) for all transactions
currentPrice = latest price from tbl_shareHistory
```

---

### Cash Flow Analysis

```sql
-- Get cash flow breakdown per share
SELECT
    s.name,
    ABS(SUM(CASE WHEN st.tradingVolume > 0 THEN ae.amount ELSE 0 END)) AS investments,
    ABS(SUM(CASE WHEN st.tradingVolume < 0 THEN ae.amount ELSE 0 END)) AS proceeds,
    ABS(SUM(CASE WHEN st.tradingVolume = 0 THEN ae.amount ELSE 0 END)) AS dividends,
    SUM(ae.amount) AS net_cash_flow
FROM tbl_share s
JOIN tbl_shareTransaction st ON st.share = s.id
JOIN tbl_accountingEntry ae ON st.accountingEntry = ae.id
GROUP BY s.id, s.name;
```

**Interpretation:**
- **Investments:** Total money spent buying shares (negative amounts)
- **Proceeds:** Total money received selling shares (negative amounts)
- **Dividends:** Total dividend income (negative amounts)
- **Net Cash Flow:** `investments + proceeds + dividends` (should be negative = money out)

---

### Performance Metrics

```sql
-- Calculate unrealized gain/loss
SELECT
    s.name,
    v.portfolioValue AS current_value,
    ABS(SUM(CASE WHEN st.tradingVolume > 0 THEN ae.amount ELSE 0 END)) AS cost_basis,
    v.portfolioValue + ABS(SUM(CASE WHEN st.tradingVolume > 0 THEN ae.amount ELSE 0 END)) AS unrealized_gain
FROM tbl_share s
JOIN view_sharePortfolioValue v ON v.id = s.id
JOIN tbl_shareTransaction st ON st.share = s.id
JOIN tbl_accountingEntry ae ON st.accountingEntry = ae.id
WHERE v.currentVolume > 0
GROUP BY s.id, s.name, v.portfolioValue;
```

**Metrics:**
- **Current Value:** `portfolioValue` from view
- **Cost Basis:** Total investments (buy transactions)
- **Unrealized Gain:** `current_value - cost_basis`
- **Return %:** `(unrealized_gain / cost_basis) × 100`

---

## Integration with Accounting

### Linking Share Transactions to Accounting Entries

```python
from decimal import Decimal
from repositories.share_transaction_repository import ShareTransactionRepository
from repositories.accounting_entry_repository import AccountingEntryRepository
from infrastructure.unit_of_work import UnitOfWork

# Buy 10 shares of Apple at $150/share + $5 fees = -$1505
with UnitOfWork(connection) as uow:
    # Create accounting entry for cash outflow
    entry_repo = AccountingEntryRepository(uow)
    entry_id = entry_repo.insert(
        transaction_id=123,  # Bank transaction
        category_id=50,  # "Investments - Securities"
        amount=Decimal("-1505.00"),  # Money out
        checked=False
    )
    
    # Create share transaction
    tx_repo = ShareTransactionRepository(uow)
    tx_id = tx_repo.insert_transaction(
        share_id=1,  # Apple Inc.
        trading_volume=10,  # +10 shares
        date_str="2025-01-15T10:00:00",
        accounting_entry_id=entry_id  # Link to accounting entry
    )
```

**Result:**
- **tbl_transaction:** Bank transaction (-$1505)
- **tbl_accountingEntry:** Categorized as "Investments - Securities"
- **tbl_shareTransaction:** +10 shares of Apple, linked to accounting entry

---

### Category Mappings for Share Transactions

Store category mappings in `tbl_setting` with key `share_categories`:

```json
{
  "buy": 50,
  "sell": 51,
  "dividend": 52,
  "fees": 53
}
```

**Usage:**
```python
import json
from repositories.settings_repository import SettingsRepository

repo = SettingsRepository(cursor)
entries = repo.get_setting_entries(key='share_categories')

if entries:
    mappings = json.loads(entries[0]['value'])
    buy_category = mappings['buy']
    sell_category = mappings['sell']
    dividend_category = mappings['dividend']
```

---

## Usage Examples

### Example 1: Track Apple Stock

```python
# 1. Create share
share_repo = ShareRepository(cursor)
share_id = share_repo.insert_share(
    name="Apple Inc.",
    isin="US0378331005",
    wkn="865985"
)

# 2. Import price history
history_repo = ShareHistoryRepository(cursor)
prices = [
    ("2025-01-15", Decimal("150.00")),
    ("2025-01-31", Decimal("152.50")),
    ("2025-02-15", Decimal("148.75"))
]
for date_str, price in prices:
    history_repo.insert_history(share_id, price, date_str)

# 3. Buy 10 shares
with UnitOfWork(connection) as uow:
    # Create accounting entry
    entry_repo = AccountingEntryRepository(uow)
    entry_id = entry_repo.insert(
        transaction_id=123,
        category_id=50,  # Investments
        amount=Decimal("-1505.00")  # 10 × 150 + 5 fees
    )
    
    # Create share transaction
    tx_repo = ShareTransactionRepository(uow)
    tx_repo.insert_transaction(
        share_id=share_id,
        trading_volume=10,
        date_str="2025-01-15T10:00:00",
        accounting_entry_id=entry_id
    )

# 4. Check portfolio value
share = share_repo.get_share_by_id(share_id)
print(f"Portfolio Value: {share['portfolioValue']}")
# Output: 1500.00 (10 shares × 150.00)
```

---

### Example 2: Sell Shares

```python
# Sell 5 shares at $152.50
with UnitOfWork(connection) as uow:
    # Create accounting entry (money in)
    entry_repo = AccountingEntryRepository(uow)
    entry_id = entry_repo.insert(
        transaction_id=456,
        category_id=51,  # Investment Proceeds
        amount=Decimal("757.50")  # 5 × 152.50 - 5 fees
    )
    
    # Create share transaction
    tx_repo = ShareTransactionRepository(uow)
    tx_repo.insert_transaction(
        share_id=1,
        trading_volume=-5,  # Negative = sell
        date_str="2025-06-20T14:00:00",
        accounting_entry_id=entry_id
    )

# Check updated portfolio
share = share_repo.get_share_by_id(1)
print(f"Remaining Volume: {share['currentVolume']}")  # 5 shares
print(f"Portfolio Value: {share['portfolioValue']}")  # 5 × latest price
```

---

### Example 3: Record Dividend

```python
# Dividend payment: $25
with UnitOfWork(connection) as uow:
    # Create accounting entry (income)
    entry_repo = AccountingEntryRepository(uow)
    entry_id = entry_repo.insert(
        transaction_id=789,
        category_id=52,  # Dividend Income
        amount=Decimal("25.00")  # Money in
    )
    
    # Create share transaction (volume = 0)
    tx_repo = ShareTransactionRepository(uow)
    tx_repo.insert_transaction(
        share_id=1,
        trading_volume=0,  # No volume change
        date_str="2025-03-31T09:00:00",
        accounting_entry_id=entry_id
    )
```

---

## API Reference

### Share Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/shares/` | List shares (paginated) |
| `POST` | `/api/shares/` | Create share |
| `GET` | `/api/shares/{id}` | Get share by ID |
| `PUT` | `/api/shares/{id}` | Update share |
| `DELETE` | `/api/shares/{id}` | Delete share |

### Share Transaction Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/shares/{id}/transactions` | List transactions for share |
| `POST` | `/api/shares/{id}/transactions` | Create transaction |
| `PUT` | `/api/shares/transactions/{id}` | Update transaction |
| `DELETE` | `/api/shares/transactions/{id}` | Delete transaction |

### Share History Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/shares/{id}/history` | List price history for share |
| `POST` | `/api/shares/{id}/history` | Create price entry |
| `PUT` | `/api/shares/history/{id}` | Update price entry |
| `DELETE` | `/api/shares/history/{id}` | Delete price entry |
| `POST` | `/api/shares/import/history` | Import price history (CSV) |

**See:** [API Documentation](../api.md) for detailed endpoint specs

---

## Best Practices

### ✅ DO

**1. Use ISIN for International Securities**

```python
# Good: ISIN standard
share = {
    'name': 'Apple Inc.',
    'isin': 'US0378331005',
    'wkn': '865985'
}

# Bad: Only WKN (limited to German market)
share = {
    'name': 'Apple Inc.',
    'isin': None,
    'wkn': '865985'
}
```

**2. Link Share Transactions to Accounting Entries**

```python
# Good: Complete cash flow tracking
with UnitOfWork(connection) as uow:
    entry_id = entry_repo.insert(...)
    tx_repo.insert_transaction(..., accounting_entry_id=entry_id)

# Bad: No accounting link
tx_repo.insert_transaction(..., accounting_entry_id=None)
# Can't track cash flow!
```

**3. Import Price History Regularly**

```python
# Good: Automated daily price updates
schedule.every().day.at("18:00").do(import_price_history)

# Bad: Manual price entry
# Tedious and error-prone
```

---

### ❌ DON'T

**1. Create Duplicate Shares**

```python
# Bad: Check for existing share first
existing = repo.get_share_by_isin_wkn(isin, wkn)
if not existing:
    repo.insert_share(name, isin, wkn)

# Good: Use get_or_create pattern
share = repo.get_share_by_isin_wkn(isin, wkn)
if not share:
    share_id = repo.insert_share(name, isin, wkn)
else:
    share_id = share['id']
```

**2. Mix Transaction Types**

```python
# Bad: Confusing volume semantics
tx_repo.insert_transaction(
    share_id=1,
    trading_volume=10,  # Buy?
    ...
)
tx_repo.insert_transaction(
    share_id=1,
    trading_volume=0,  # Dividend?
    ...
)

# Good: Clear transaction types
# Buy: trading_volume > 0
# Sell: trading_volume < 0
# Dividend: trading_volume = 0
```

---

## Troubleshooting

### Portfolio Value is Zero

**Symptom:** `portfolioValue` is 0 despite having transactions

**Causes:**
1. No price history entries
2. Latest price is 0
3. Volume is 0 (all shares sold)

**Solution:**
```python
# Check volume
share = repo.get_share_by_id(share_id)
print(f"Volume: {share['currentVolume']}")

# Check latest price
history_repo = ShareHistoryRepository(cursor)
latest = history_repo.get_latest_price(share_id)
print(f"Latest Price: {latest}")

# Import price if missing
if not latest:
    history_repo.insert_history(share_id, Decimal("150.00"), "2025-01-15")
```

---

### Transaction Volume Mismatch

**Symptom:** `currentVolume` doesn't match expected holdings

**Cause:** Missing or incorrect transactions

**Solution:**
```python
# Audit transactions
tx_repo = ShareTransactionRepository(cursor)
transactions = tx_repo.get_all_for_share_sorted(share_id)

cumulative_volume = 0
for tx in transactions:
    cumulative_volume += tx['tradingVolume']
    print(f"{tx['dateTransaction']}: {tx['tradingVolume']:+} → Total: {cumulative_volume}")

print(f"Expected: {cumulative_volume}")
print(f"Actual: {share['currentVolume']}")
```

---

## Related Documentation

- [Database Schema](../database/schema.md) - Share tables structure
- [API Documentation](../api.md) - Share endpoints
- [Repository Pattern](../architecture/repositories.md) - ShareRepository details
- [Year Overview](../api.md#year-overview) - Portfolio visualization

---

## Summary

FiniA's share portfolio system provides:

✅ **Complete Tracking** - Holdings, transactions, price history  
✅ **Automatic Valuation** - Portfolio value calculation  
✅ **Cash Flow Integration** - Link to accounting entries  
✅ **Performance Analysis** - Investments, proceeds, gains  
✅ **Historical Data** - Monthly snapshots and charts  
✅ **International Support** - ISIN/WKN identification  

**Perfect for tracking stock/ETF portfolios with integrated accounting.**
