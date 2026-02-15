# Database Schema

Complete reference for FiniA's database structure including tables, views, and relationships.

## Overview

FiniA uses a per-user database pattern where each user gets their own isolated database:
- **Pattern:** `finiaDB_<username>`
- **Example:** User "john" → Database "finiaDB_john"
- **Character Set:** UTF-8 (utf8mb3)
- **Collation:** utf8mb3_general_ci

## Database Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        FiniA Database                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Core Financial Data                                             │
│  ├─ tbl_account              (Bank accounts)                     │
│  ├─ tbl_accountType          (Account categories)                │
│  ├─ tbl_transaction          (Financial transactions)            │
│  └─ tbl_accountingEntry      (Split bookings)                    │
│                                                                  │
│  Categories & Classification                                     │
│  ├─ tbl_category             (Hierarchical categories)           │
│  └─ tbl_setting              (JSON-based settings)               │
│                                                                  │
│  Planning & Budgeting                                            │
│  ├─ tbl_planningCycle        (Recurring intervals)               │
│  ├─ tbl_planning             (Budget entries)                    │
│  └─ tbl_planningEntry        (Generated entries)                 │
│                                                                  │
│  Portfolio Management                                            │
│  ├─ tbl_share                (Securities)                        │
│  ├─ tbl_shareHistory         (Price history)                     │
│  └─ tbl_shareTransaction     (Buy/Sell/Dividend)                 │
│                                                                  │
│  Import Configuration                                            │
│  ├─ tbl_accountImportFormat  (CSV format definitions)            │
│  └─ tbl_accountImportPath    (Import paths per account)          │
│                                                                  │
│  Additional Features                                             │
│  ├─ tbl_accountReserve       (Reserve funds tracking)            │
│  └─ tbl_loan                 (Loan accounts)                     │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Core Tables

### tbl_account

Stores all financial accounts (checking, securities, loans, crypto, investments).

**Columns:**
- `id` (BIGINT, PK, AUTO_INCREMENT): Unique account identifier
- `dateImport` (DATETIME): Last import timestamp
- `name` (VARCHAR(128), UNIQUE): Account display name
- `iban_accountNumber` (VARCHAR(32)): IBAN or account number
- `bic_market` (TEXT): BIC code or market identifier
- `startAmount` (DECIMAL(20,10)): Initial balance
- `dateStart` (DATETIME): Account opening date
- `dateEnd` (DATETIME, NULL): Account closing date (NULL = active)
- `type` (BIGINT, FK → tbl_accountType): Account type reference
- `clearingAccount` (BIGINT, FK → tbl_account, NULL): Associated clearing account for transfers

**Indexes:**
- PRIMARY KEY: `id`
- UNIQUE KEY: `name`
- INDEX: `type`
- INDEX: `clearingAccount`

**Usage:**
```sql
-- Get all active checking accounts
SELECT a.*, at.type 
FROM tbl_account a
JOIN tbl_accountType at ON a.type = at.id
WHERE at.type = 'Girokonto' AND a.dateEnd IS NULL;
```

---

### tbl_accountType

Defines account categories (Girokonto, Wertpapierdepot, Darlehen, Krypto, Investment-Plattform).

**Columns:**
- `id` (BIGINT, PK, AUTO_INCREMENT): Type identifier
- `dateImport` (DATETIME): Import timestamp
- `type` (VARCHAR(128)): Type name

**Seed Data (via db/finia_draft.sql):**
```sql
(1, 'Girokonto')              -- Checking account
(2, 'Wertpapierdepot')        -- Securities depot
(3, 'Darlehen')               -- Loan account
(4, 'Krypto')                 -- Cryptocurrency
(5, 'Investment-Plattform')   -- Investment platform
```

---

### tbl_transaction

Financial transactions linked to accounts.

**Columns:**
- `id` (BIGINT, PK, AUTO_INCREMENT): Transaction ID
- `dateImport` (DATETIME): Import timestamp
- `dateValue` (DATETIME): Value date (actual transaction date)
- `dateCreation` (DATETIME, NULL): Booking date
- `description` (TEXT): Transaction description
- `recipientApplicant` (TEXT): Recipient or sender name
- `iban` (VARCHAR(34), NULL): Counterparty IBAN
- `bic` (VARCHAR(11), NULL): Counterparty BIC
- `amount` (DECIMAL(20,10)): Total transaction amount (positive = income, negative = expense)
- `account` (BIGINT, FK → tbl_account): Associated account
- `importHash` (VARCHAR(64), UNIQUE): SHA-256 hash for duplicate detection

**Indexes:**
- PRIMARY KEY: `id`
- UNIQUE KEY: `importHash`
- INDEX: `account`
- INDEX: `dateValue`

**Duplicate Detection:**
The `importHash` is computed from:
```
SHA256(account_id + dateValue + amount + description + recipient)
```

**Usage:**
```sql
-- Get all transactions for 2025
SELECT * FROM tbl_transaction
WHERE YEAR(dateValue) = 2025
ORDER BY dateValue DESC;
```

---

### tbl_accountingEntry

Split bookings - each transaction can have multiple entries with different categories.

**Columns:**
- `id` (BIGINT, PK, AUTO_INCREMENT): Entry ID
- `dateImport` (DATETIME): Import timestamp
- `checked` (TINYINT, DEFAULT 0): Review status (0 = unchecked, 1 = verified)
- `amount` (DECIMAL(20,10)): Entry amount
- `transaction` (BIGINT, FK → tbl_transaction): Parent transaction
- `accountingPlanned` (BIGINT, FK → tbl_planningEntry, NULL): Link to budget entry
- `category` (BIGINT, FK → tbl_category, NULL): Assigned category

**Indexes:**
- PRIMARY KEY: `id`
- INDEX: `transaction`
- INDEX: `category`
- INDEX: `accountingPlanned`
- INDEX: `checked`

**Concept:**
- **1 Transaction → N Accounting Entries**
- Allows splitting expenses across multiple categories
- Example: Grocery shopping with food + household items

**Usage:**
```sql
-- Get all uncategorized entries
SELECT ae.*, t.description, t.recipientApplicant
FROM tbl_accountingEntry ae
JOIN tbl_transaction t ON ae.transaction = t.id
WHERE ae.category IS NULL AND ae.checked = 0;
```

---

## Categories & Classification

### tbl_category

Hierarchical category structure (unlimited depth).

**Columns:**
- `id` (BIGINT, PK, AUTO_INCREMENT): Category ID
- `dateImport` (DATETIME): Import timestamp
- `name` (VARCHAR(256)): Category name
- `category` (BIGINT, FK → tbl_category, NULL): Parent category (NULL = root)

**Indexes:**
- PRIMARY KEY: `id`
- INDEX: `category` (parent reference)

**Hierarchy Example:**
```
Living Expenses (id=1, parent=NULL)
├─ Groceries (id=2, parent=1)
├─ Rent (id=3, parent=1)
└─ Utilities (id=4, parent=1)
   ├─ Electricity (id=5, parent=4)
   └─ Water (id=6, parent=4)
```

**Usage:**
```sql
-- Get all root categories
SELECT * FROM tbl_category WHERE category IS NULL;

-- Get children of category 1
SELECT * FROM tbl_category WHERE category = 1;
```

**See also:** `view_categoryFullname` for hierarchical names.

---

### tbl_setting

JSON-based key-value storage for flexible settings.

**Columns:**
- `id` (BIGINT, PK, AUTO_INCREMENT): Setting ID
- `key` (VARCHAR(128)): Setting key
- `value` (TEXT): JSON-encoded value

**Indexes:**
- PRIMARY KEY: `id`
- INDEX: `key`

**Usage Examples:**

**Category Automation Rules:**
```sql
-- Store automation rule
INSERT INTO tbl_setting (key, value) VALUES
('category_automation', '{"category": 5, "field": "recipientApplicant", "pattern": "REWE", "match_type": "contains"}');
```

**Share Transaction Categories:**
```sql
-- Store category mappings for share transactions
INSERT INTO tbl_setting (key, value) VALUES
('share_tx_category', '{"category_id": 50, "type": "buy"}'),
('share_tx_category', '{"category_id": 51, "type": "sell"}'),
('share_tx_category', '{"category_id": 52, "type": "dividend"}');
```

---

## Planning & Budgeting

### tbl_planningCycle

Recurring intervals for budget planning.

**Columns:**
- `id` (BIGINT, PK, AUTO_INCREMENT): Cycle ID
- `dateImport` (DATETIME): Import timestamp
- `name` (VARCHAR(128), UNIQUE): Cycle name
- `period_value` (INT): Interval value (e.g., 1, 14, 3)
- `period_unit` (CHAR(1)): Unit ('d' = days, 'm' = months, 'y' = years)

**Seed Data:**
```sql
(1, 'Monthly', 1, 'm')
(2, 'Yearly', 1, 'y')
(3, 'Quarterly', 3, 'm')
(4, 'Weekly', 7, 'd')
(5, 'Biweekly', 14, 'd')
(6, 'Semi-Annually', 6, 'm')
(7, 'Bimonthly', 2, 'm')
(8, 'Daily', 1, 'd')
```

---

### tbl_planning

Budget planning entries (recurring expenses/income).

**Columns:**
- `id` (BIGINT, PK, AUTO_INCREMENT): Planning ID
- `dateImport` (DATETIME): Import timestamp
- `name` (VARCHAR(128)): Planning name (e.g., "Rent")
- `amount` (DECIMAL(20,10)): Planned amount (negative = expense, positive = income)
- `cycle` (BIGINT, FK → tbl_planningCycle): Recurrence cycle
- `category` (BIGINT, FK → tbl_category): Budget category
- `account` (BIGINT, FK → tbl_account): Associated account
- `dateStart` (DATETIME): Start date
- `dateEnd` (DATETIME, NULL): End date (NULL = unlimited)

**Indexes:**
- PRIMARY KEY: `id`
- INDEX: `cycle`, `category`, `account`

**Example:**
```sql
-- Monthly rent planning
INSERT INTO tbl_planning (name, amount, cycle, category, account, dateStart)
VALUES ('Rent', -800.00, 1, 10, 1, '2025-01-01');
```

---

### tbl_planningEntry

Generated entries from planning definitions (future transactions).

**Columns:**
- `id` (BIGINT, PK, AUTO_INCREMENT): Entry ID
- `dateImport` (DATETIME): Import timestamp
- `dateValue` (DATETIME): Planned date
- `planning` (BIGINT, FK → tbl_planning): Source planning

**Indexes:**
- PRIMARY KEY: `id`
- INDEX: `planning`, `dateValue`

**Generation Logic:**
- Automatically created based on `tbl_planning` cycles
- Used for future budgeting in reports
- Endpoint: POST `/api/planning/{id}/entries/generate`

---

## Portfolio Management

### tbl_share

Securities (stocks, ETFs, bonds).

**Columns:**
- `id` (BIGINT, PK, AUTO_INCREMENT): Share ID
- `dateImport` (DATETIME): Import timestamp
- `name` (VARCHAR(128), NULL): Security name
- `isin` (VARCHAR(12), UNIQUE): International Security Identification Number
- `wkn` (VARCHAR(6), UNIQUE, NULL): Wertpapierkennnummer (German identifier)

**Indexes:**
- PRIMARY KEY: `id`
- UNIQUE KEY: `isin`, `wkn`

**Usage:**
```sql
-- Find share by ISIN
SELECT * FROM tbl_share WHERE isin = 'US0378331005';
```

---

### tbl_shareHistory

Price history for securities.

**Columns:**
- `id` (BIGINT, PK, AUTO_INCREMENT): History ID
- `dateImport` (DATETIME): Import timestamp
- `checked` (TINYINT, DEFAULT 0): Verification status
- `share` (BIGINT, FK → tbl_share): Security reference
- `amount` (DECIMAL(20,10)): Price value
- `dateValue` (DATETIME): Price date

**Indexes:**
- PRIMARY KEY: `id`
- INDEX: `share`, `dateValue`
- UNIQUE KEY: `share + dateValue` (prevent duplicates)

**Usage:**
```sql
-- Get latest price for share
SELECT * FROM tbl_shareHistory
WHERE share = 1
ORDER BY dateValue DESC
LIMIT 1;
```

---

### tbl_shareTransaction

Buy/Sell/Dividend transactions for securities.

**Columns:**
- `id` (BIGINT, PK, AUTO_INCREMENT): Transaction ID
- `dateImport` (DATETIME): Import timestamp
- `share` (BIGINT, FK → tbl_share): Security reference
- `type` (ENUM('buy', 'sell', 'dividend')): Transaction type
- `date` (DATETIME): Transaction date
- `quantity` (DECIMAL(20,10)): Number of shares
- `price` (DECIMAL(20,10)): Price per share
- `amount` (DECIMAL(20,10)): Total amount
- `fees` (DECIMAL(20,10), DEFAULT 0): Transaction fees
- `account` (BIGINT, FK → tbl_account): Associated account

**Indexes:**
- PRIMARY KEY: `id`
- INDEX: `share`, `account`, `date`

**Usage:**
```sql
-- Get all buy transactions for 2025
SELECT st.*, s.name, s.isin
FROM tbl_shareTransaction st
JOIN tbl_share s ON st.share = s.id
WHERE st.type = 'buy' AND YEAR(st.date) = 2025;
```

---

## Import Configuration

### tbl_accountImportFormat

CSV import format definitions (links to `cfg/import_formats.yaml`).

**Columns:**
- `id` (BIGINT, PK, AUTO_INCREMENT): Format ID
- `dateImport` (DATETIME): Import timestamp
- `type` (VARCHAR(128)): Format name (e.g., "Commerzbank", "Sparkasse")
- `fileEnding` (TEXT): File extension (e.g., ".csv")

**Indexes:**
- PRIMARY KEY: `id`

---

### tbl_accountImportPath

Maps accounts to import paths and formats.

**Columns:**
- `id` (BIGINT, PK, AUTO_INCREMENT): Mapping ID
- `dateImport` (DATETIME): Import timestamp
- `path` (VARCHAR(256)): Filesystem path to CSV files
- `account` (BIGINT, FK → tbl_account): Target account
- `importFormat` (BIGINT, FK → tbl_accountImportFormat): CSV format

**Indexes:**
- PRIMARY KEY: `id`
- INDEX: `account`, `importFormat`

**Usage:**
```sql
-- Get import configuration for account 1
SELECT aip.path, aif.type, aif.fileEnding
FROM tbl_accountImportPath aip
JOIN tbl_accountImportFormat aif ON aip.importFormat = aif.id
WHERE aip.account = 1;
```

---

## Additional Features

### tbl_accountReserve

Tracks reserve funds over time.

**Columns:**
- `id` (BIGINT, PK, AUTO_INCREMENT): Reserve ID
- `dateImport` (DATETIME): Import timestamp
- `amount` (DECIMAL(20,10)): Reserve amount
- `dateSet` (DATETIME): Date when reserve was set
- `account` (BIGINT, FK → tbl_account): Account reference

---

### tbl_loan

Loan account details.

**Columns:**
- `id` (BIGINT, PK, AUTO_INCREMENT): Loan ID
- `dateImport` (DATETIME): Import timestamp
- `account` (BIGINT, FK → tbl_account): Loan account reference
- `value` (DECIMAL(20,10)): Loan principal
- `interestRate` (DECIMAL(5,2)): Interest rate (percentage)
- `startDate` (DATETIME): Loan start date
- `durationMonths` (INT): Loan duration in months

---

## Database Views

FiniA includes several views for complex queries:

### view_categoryFullname

Recursive CTE building full hierarchical category names.

**Structure:**
- `id` (BIGINT): Category ID
- `fullname` (TEXT): Full path (e.g., "Living Expenses > Groceries")
- `name` (VARCHAR): Category name
- `category` (BIGINT): Parent ID

**Usage:**
```sql
-- Get category with full path
SELECT fullname FROM view_categoryFullname WHERE id = 5;
-- Result: "Living Expenses > Groceries"
```

---

### view_accountingEntriesNotChecked

Lists uncategorized/unchecked accounting entries.

**Columns:**
- `account` (BIGINT): Account ID
- `description` (TEXT): Transaction description
- `transactionId` (BIGINT): Transaction ID

---

### view_balancesPlanning

Aggregates planning entries by category and month.

**Columns:**
- `amountSum` (DECIMAL): Sum of planned amounts
- `categoryID` (BIGINT): Category
- `accountID` (BIGINT): Account
- `dateValue` (DATETIME): Month
- `categoryName` (VARCHAR): Category name

---

### view_sharePortfolioValue

Calculates portfolio value with current prices and holdings.

**Columns:**
- `share_id` (BIGINT): Security ID
- `isin` (VARCHAR): ISIN code
- `name` (VARCHAR): Security name
- `total_quantity` (DECIMAL): Current holdings
- `current_price` (DECIMAL): Latest price
- `portfolio_value` (DECIMAL): Total value (quantity × price)

---

### view_shareMonthlySnapshot

Month-end portfolio snapshots for historical tracking.

**Columns:**
- `month_end` (DATETIME): Month-end date
- `share_id` (BIGINT): Security ID
- `quantity` (DECIMAL): Holdings at month-end
- `price` (DECIMAL): Price at month-end
- `value` (DECIMAL): Portfolio value

---

### view_reserveMonthly

Monthly reserve fund tracking with recursive date generation.

**Columns:**
- `account` (BIGINT): Account ID
- `dateSet` (DATETIME): Month
- `amount` (DECIMAL): Reserve amount

---

## Data Relationships

**Key Foreign Key Relationships:**

```
tbl_transaction
  └─ account → tbl_account
  └─ [1:N] → tbl_accountingEntry
                └─ category → tbl_category
                └─ accountingPlanned → tbl_planningEntry

tbl_account
  └─ type → tbl_accountType
  └─ clearingAccount → tbl_account (self-reference)

tbl_category
  └─ category → tbl_category (self-reference, hierarchical)

tbl_planning
  └─ cycle → tbl_planningCycle
  └─ category → tbl_category
  └─ account → tbl_account
  └─ [1:N] → tbl_planningEntry

tbl_shareTransaction
  └─ share → tbl_share
  └─ account → tbl_account

tbl_shareHistory
  └─ share → tbl_share

tbl_accountImportPath
  └─ account → tbl_account
  └─ importFormat → tbl_accountImportFormat
```

## Initialization

**Schema Creation:**
```bash
# Create database and import schema
curl -X POST http://127.0.0.1:8000/api/setup/database \
  -H "Content-Type: application/json" \
  -d '{"username":"<user>","password":"<pass>","database_name":"finiaDB_<username>"}'
```

**Seed Data:**
```bash
# Import account types, planning cycles, categories
curl -X POST http://127.0.0.1:8000/api/setup/init-data \
  -H "Content-Type: application/json" \
  -d '{"username":"<user>","password":"<pass>","database_name":"finiaDB_<username>"}'
```

**SQL File:** [db/finia_draft.sql](../../db/finia_draft.sql)

## Best Practices

### Indexing
- All foreign keys have indexes for join performance
- `dateValue` fields indexed for time-based queries
- Unique constraints on import hashes prevent duplicates

### Data Types
- Use `DECIMAL(20,10)` for financial amounts (no floating-point errors)
- Use `BIGINT` for IDs (supports large datasets)
- Use `DATETIME` for timestamps (timezone-aware via application)

### Constraints
- Use `ON DELETE CASCADE` sparingly (data integrity)
- Nullable foreign keys for optional relationships
- Unique constraints on business keys (ISIN, importHash)

### Performance
- Avoid full table scans with proper indexing
- Use views for complex recurring queries
- Pagination for large result sets (see API docs)

## See Also

- [Data Import (YAML)](../cfg/data.md) - Seed data configuration
- [Import Formats](../cfg/import_formats.md) - CSV import configuration
- [API Documentation](../api.md) - Database access via REST API
- [Backup Strategy](../backup.md) - Database backup procedures
