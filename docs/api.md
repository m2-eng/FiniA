# API Documentation

FiniA provides a RESTful API built with FastAPI for all financial management operations. The API is fully documented with interactive Swagger UI.

## Base URL

- **Development:** `http://localhost:8000/api`
- **Production:** `https://your-domain.com/api`
- **Interactive Docs:** `http://localhost:8000/api/docs`
- **ReDoc:** `http://localhost:8000/api/redoc`

## Authentication

All API endpoints (except `/api/auth/login`) require JWT token authentication.

### Login

**POST** `/api/auth/login`

Authenticate with MySQL credentials and receive JWT token.

**Request:**
```json
{
  "username": "your_mysql_user",
  "password": "your_mysql_password"
}
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "Bearer",
  "username": "your_mysql_user"
}
```

**Usage:**
Include token in subsequent requests:
```
Authorization: Bearer eyJhbGciOiJIUzI1NiIs...
```

### Logout

**POST** `/api/auth/logout`

Invalidate current session.

**Headers:**
```
Authorization: Bearer <token>
```

**Response:**
```json
{
  "message": "Logged out successfully"
}
```

### Session Info

**GET** `/api/auth/session`

Get current session information (without password).

**Headers:**
```
Authorization: Bearer <token>
```

**Response:**
```json
{
  "session_id": "abc123...",
  "username": "your_mysql_user",
  "created_at": "2025-01-23T10:30:00",
  "last_activity": "2025-01-23T11:45:00"
}
```

## Core Endpoints

### Health Check

**GET** `/api/health`

Check API availability (no authentication required).

**Response:**
```json
{
  "status": "healthy",
  "service": "FiniA API",
  "version": "1.0.0"
}
```

## Transactions

Manage financial transactions and accounting entries.

### List Transactions

**GET** `/api/transactions/`

Get paginated list of transactions with optional filtering.

**Query Parameters:**
- `page` (int, default: 1): Page number
- `page_size` (int, default: 100, max: 1000): Records per page
- `year` (int, optional): Filter by year
- `account` (str, optional): Filter by account name
- `uncategorized_only` (bool, optional): Show only uncategorized entries

**Response:**
```json
{
  "transactions": [
    {
      "id": 1,
      "dateValue": "2025-01-15",
      "description": "Grocery Store",
      "recipientApplicant": "REWE",
      "amount": -45.50,
      "account": "Checking",
      "entries": [
        {
          "id": 1,
          "amount": -45.50,
          "category": "Groceries",
          "category_fullname": "Living Expenses > Groceries"
        }
      ]
    }
  ],
  "page": 1,
  "page_size": 100,
  "total": 250
}
```

### Get Transaction

**GET** `/api/transactions/{transaction_id}`

Fetch single transaction with all accounting entries.

**Response:**
```json
{
  "id": 1,
  "dateValue": "2025-01-15",
  "description": "Grocery Store",
  "recipientApplicant": "REWE",
  "amount": -45.50,
  "account": "Checking",
  "iban": "DE1234567890",
  "checked": true,
  "entries": [...]
}
```

### Update Transaction Entries

**PUT** `/api/transactions/{transaction_id}/entries`

Update accounting entries (categories and split amounts) for a transaction.

**Request:**
```json
{
  "entries": [
    {
      "id": 1,
      "category_id": 5,
      "amount": -30.00
    },
    {
      "id": 2,
      "category_id": 8,
      "amount": -15.50
    }
  ]
}
```

### Mark as Checked

**POST** `/api/transactions/mark-checked`

Mark transactions as reviewed.

**Request:**
```json
{
  "transaction_ids": [1, 2, 3]
}
```

### Import CSV

**POST** `/api/transactions/import-csv`

Upload and import CSV transaction file.

**Form Data:**
- `file` (file): CSV file
- `import_format` (string): Format name from `cfg/import_formats.yaml`
- `account_id` (int): Target account ID

**Response:**
```json
{
  "imported": 25,
  "duplicates": 3,
  "errors": 0
}
```

### Auto-Categorize

**POST** `/api/transactions/auto-categorize`

Apply automation rules to uncategorized entries.

**Request:**
```json
{
  "account_id": 1  // Optional: null = all accounts
}
```

**Response:**
```json
{
  "categorized": 15,
  "total_checked": 50,
  "message": "15 entries categorized successfully"
}
```

### Import from YAML

**POST** `/api/transactions/import`

Import transactions from `cfg/data.yaml`.

**Request:**
```json
{
  "account_id": 1  // Optional: null = all accounts
}
```

### Get Import Formats

**GET** `/api/transactions/import-formats`

List available CSV import formats.

**Response:**
```json
{
  "formats": [
    {
      "id": "csv-cb",
      "name": "Commerzbank CSV"
    },
    {
      "id": "csv-spk",
      "name": "Sparkasse CSV"
    }
  ]
}
```

## Categories

Manage hierarchical category structure.

### List Categories

**GET** `/api/categories/`

Get paginated categories with full hierarchical names.

**Query Parameters:**
- `page` (int): Page number
- `page_size` (int): Records per page

**Response:**
```json
{
  "categories": [
    {
      "id": 1,
      "fullname": "Living Expenses > Groceries"
    }
  ],
  "page": 1,
  "page_size": 100,
  "total": 45
}
```

### Get Category Hierarchy

**GET** `/api/categories/hierarchy`

Get categories with parent information for tree building.

**Response:**
```json
{
  "categories": [
    {
      "id": 1,
      "name": "Living Expenses",
      "parent_id": null
    },
    {
      "id": 2,
      "name": "Groceries",
      "parent_id": 1
    }
  ]
}
```

### Get All Categories (Unpaginated)

**GET** `/api/categories/hierarchy/all`

Fetch entire category tree in single request (for category management UI).

### Simple List

**GET** `/api/categories/list`

Get minimal category list for dropdowns (id + fullname only).

### Create Category

**POST** `/api/categories/`

Create new category.

**Request:**
```json
{
  "name": "Netflix",
  "parent_id": 5
}
```

### Update Category

**PUT** `/api/categories/{category_id}`

Update category name or parent.

**Request:**
```json
{
  "name": "Streaming Services",
  "parent_id": 5
}
```

### Get Single Category

**GET** `/api/categories/{category_id}`

Fetch single category details.

**Response:**
```json
{
  "id": 5,
  "name": "Groceries",
  "parent_id": 1,
  "fullname": "Living Expenses > Groceries"
}
```

### Delete Category

**DELETE** `/api/categories/{category_id}`

Remove category (fails if in use).

## Category Automation

Manage automatic categorization rules.

### List Rules

**GET** `/api/category-automation/rules`

Get all automation rules with pagination.

**Query Parameters:**
- `page` (int): Page number
- `page_size` (int): Records per page

**Response:**
```json
{
  "rules": [
    {
      "id": 1,
      "category_id": 5,
      "category_fullname": "Living Expenses > Groceries",
      "field": "recipientApplicant",
      "pattern": "REWE",
      "match_type": "contains",
      "account_id": null,
      "active": true
    }
  ],
  "total": 12
}
```

### Create Rule

**POST** `/api/category-automation/rules`

Add new automation rule.

**Request:**
```json
{
  "category_id": 5,
  "field": "description",
  "pattern": "grocery",
  "match_type": "contains",
  "aGet Single Rule

**GET** `/api/category-automation/rules/{rule_id}`

Fetch single automation rule details.

**Response:**
```json
{
  "id": 1,
  "category_id": 5,
  "category_fullname": "Living Expenses > Groceries",
  "field": "recipientApplicant",
  "pattern": "REWE",
  "match_type": "contains",
  "account_id": null,
  "active": true
}
```

### Delete Rule

**DELETE** `/api/category-automation/rules/{rule_id}`

Remove automation rule.

### Test Rule

**POST** `/api/category-automation/rules/test`

Test automation rule against sample transaction data.

**Request:**
```json
{
  "rule": {
    "id": null,
    "name": "Test Rule",
    "description": "Testing",
    "conditions": [
      {
        "field": "recipientApplicant",
        "operator": "contains",
        "value": "REWE"
      }
    ],
    "conditionLogic": "AND",
    "category": 5,
    "accounts": [],
    "priority": 1,
    "enabled": true
  },
  "transaction": {
    "description": "Grocery shopping",
    "recipientApplicant": "REWE Market",
    "amount": -45.50,
    "iban": "DE12345"
  }
}
```

**Response:**
```json
{
  "matches": true,
  "category_id": 5,
  "condition_results": {
    "condition_0": true
  }
}
```
**Match Types:**
- `contains`: Case-insensitive substring match
- `equals`: Exact match
- `regex`: Regular expression

### Update Rule

**PUT** `/api/category-automation/rules/{rule_id}`

Modify existing rule.

### Delete Rule

**DELETE** `/api/category-automation/rules/{rule_id}`

Remove automation rule.

## Planning

Manage recurring budget entries.

### Get Planning Cycles

**GET** `/api/planning/cycles`

List available cycles (Monthly, Yearly, etc.).

**Response:**
```json
[
  {
    "id": 1,
    "name": "Monthly",
    "period_value": 1,
    "period_unit": "m"
  },
  {
    "id": 2,
    "name": "Yearly",
    "period_value": 1,
    "period_unit": "y"
  }
]
```

### List Plannings

**GET** `/api/planning/`

Get paginated planning entries.

**Query Parameters:**
- `page` (int): Page number
- `page_size` (int): Records per page

**Response:**
```json
{
  "plannings": [
    {
      "id": 1,
      "name": "Rent",
      "amount": -800.00,
      "category_id": 10,
    Generate Planning Entries

**POST** `/api/planning/{planning_id}/entries/generate`

Generate/regenerate planning entries up to end date or end of next year.

**Response:**
```json
{
  "planning_id": 1,
  "entries": [
    {
      "date": "2025-02-01",
      "amount": -800.00
    }
  ],
  "total": 12
}
```

### Delete Planning Entry

**DELETE** `/api/planning/{planning_id}/entries/{entry_id}`

Delete single generated planning entry.

**Response:** `204 No Content`

### Delete Planning

**DELETE** `/api/planning/{planning_id}`

Remove planning entry.

**Response:** `204 No Content`
  ],
  "page": 1,
  "page_size": 100,
  "total": 15
}
```

### Get Planning Details

**GET** `/api/planning/{planning_id}`

Fetch single planning with details.
Account Summary

**GET** `/api/accounts/summary`

Get combined income/expense summary for specific account/year.

**Query Parameters:**
- `year` (int): Year
- `account` (string): Account name

**Response:**
```json
{
  "data": [
    {
      "Kategorie": "Salary",
      "Januar": 3000.00,
      "...": "...",
      "Gesamt": 36000.00
    }
  ]
}
```

### All Giro Accounts Aggregated

**GET** `/api/accounts/all-giro/income`  
**GET** `/api/accounts/all-giro/expenses`  
**GET** `/api/accounts/all-giro/summary`

Aggregated data for all "Girokonto" type accounts.

**Query Parameters:**
- `year` (int): Year

### All Loan Accounts Aggregated

**GET** `/api/accounts/all-loans/income`  
**GET** `/api/accounts/all-loans/expenses`  
**GET** `/api/accounts/all-loans/summary`

Aggregated data for all "Darlehen" type accounts.

### All Accounts Combined

**GET** `/api/accounts/all-accounts/income`  
**GET** `/api/accounts/all-accounts/expenses`  
**GET** `/api/accounts/all-accounts/summary`

Combined data across all account types.

### List Girokonto Accounts

**GET** `/api/accounts/girokonto/list`

Get list of checking accounts only.

**Response:**
```json
{
  "accounts": ["Checking", "Savings"]
}
```

### List All Accounts

**GET** `/api/accounts/list`

Get paginated accounts with search.

**Query Parameters:**
- `page` (int): Page number
- `page_size` (int): Records per page
- `search` (string): Search by name or IBAN

**Response:**
```json
{
  "accounts": [
    {
      "id": 1,
      "name": "Checking",
      "iban_accountNumber": "DE1234567890",
      "bic_market": "ABCDEFGH",
      "startAmount": 1000.00,
      "dateStart": "2020-01-01",
      "dateEnd": null,
      "type": 1,
      "type_name": "Girokonto",
      "clearingAccount": null
    }
  ],
  "page": 1,
  "page_size": 50,
  "total": 15
}
```

### List Account Types

**GET** `/api/accounts/types/list`

Get all available account types.

**Response:**
```json
{
  "types": [
    {"id": 1, "type": "Girokonto"},
    {"id": 2, "type": "Wertpapierdepot"}
  ]
}
```

### List Import Formats

**GET** `/api/accounts/formats/list`

Get all configured import formats.

**Response:**
```json
{
  "formats": [
    {"id": 1, "type": "Commerzbank"},
    {"id": 2, "type": "Sparkasse"}
  ]
}
```

### Get Account Details

**GET** `/api/accounts/{account_id}`

Fetch single account with full details.

**Response:**
```json
{
  "id": 1,
  "name": "Checking",
  "iban_accountNumber": "DE1234567890",
  "bic_market": "ABCDEFGH",
  "type": 1,
  "startAmount": 1000.00,
  "dateStart": "2020-01-01",
  "dateEnd": null,
  "clearingAccount": null,
  "importFormat": 1,
  "importPath": "/data/bank_statements/"
}
```
Price History

**GET** `/api/shares/history`

Get price history for all shares with pagination.

**Query Parameters:**
- `page` (int): Page number
- `page_size` (int): Records per page
- `isin` (string, optional): Filter by ISIN
- `from_date` (string, optional): Start date filter
- `to_date` (string, optional): End date filter

### Create Share Price History

**POST** `/api/shares/history`

Add single price history entry.

**Form Data:**
- `isin` (string): ISIN code
- `date` (string): ISO date (YYYY-MM-DD)
- `amount` (float): Price value

**Response:**
```json
{
  "status": "success",
  "message": "History entry created successfully"
}
```

### Update History Checked Status

**PUT** `/api/shares/history/{history_id}/checked`

Mark price history entry as checked/verified.

**Form Data:**
- `checked` (bool): True or false

### Delete Price History

**DELETE** `/api/shares/history/{history_id}`

Remove single price history entry.

### Auto-Fill Share History

**POST** `/api/shares/history/auto-fill`

Automatically create missing month-end price entries (amount=0) for all shares held at month-end.

**Response:**
```json
{
  "status": "success",
  "created": 15
}
```

### Import Price History CSV

**POST** `/api/shares/import/history`

Bulk import price history from CSV file.

**Form Data:**
- `file` (file): CSV with columns: ISIN, Date, Amount

**Response:**
```json
{
  "imported": 120,
  "duplicates": 5,
  "errors": 0
}
```

### Share Transactions

**GET** `/api/shares/transactions`

Get all share transactions with pagination.

**Query Parameters:**
- `page` (int): Page number
- `page_size` (int): Records per page
- `isin` (string, optional): Filter by ISIN
- `from_date` (string, optional): Start date filter
- `to_date` (string, optional): End date filter

### Create Share Transaction

**POST** `/api/shares/transactions`

Record new buy/sell/dividend transaction.

**Form Data:**
- `isin` (string): ISIN code
- `date` (string): Transaction date
- `type` (string): `buy`, `sell`, or `dividend`
- `amount` (float): Transaction amount
- `quantity` (float): Number of shares
- `price` (float): Price per share
- `fees` (float, optional): Transaction fees
- `account_id` (int): Associated account

**Response:**
```json
{
  "status": "success",
  "transaction_id": 123
}
```

### Update Share Transaction

**PUT** `/api/shares/transactions/{transaction_id}`

Modify existing share transaction.

### Delete Share Transaction

**DELETE** `/api/shares/transactions/{transaction_id}`

Remove share transaction.

### Import Share Transactions CSV

**POST** `/api/shares/import/transactions`

Bulk import share transactions from CSV.

**Form Data:**
- `file` (file): CSV with transaction data
- `account_id` (int): Target account

### Share Accounting Entries

**GET** `/api/shares/accounting-entries`

Get accounting entries related to share transactions.

**Query Parameters:**
- `page` (int): Page number
- `page_size` (int): Records per page
- `transaction_id` (int, optional): Filter by transaction

**GET** `/api/shares/accounting-entries/{entry_id}`

Get single accounting entry details.
Add new recurring budget entry.

**Request:**
```json
{
  "name": "Internet",
  "amount": -50.00,
  "category_id": 12,
  "cycle_id": 1,
  "account_id": 1,
  "start_date": "2025-01-01"
}
```

### Update Planning

**PUT** `/api/planning/{planning_id}`

Modify planning entry.

### Delete Planning

**DELETE** `/api/planning/{planning_id}`

Remove planning entry.

## Accounts

Account-specific income/expense breakdowns.

### Get Account Income

**GET** `/api/accounts/income`

Monthly income breakdown by category for specific account/year.

**Query Parameters:**
- `year` (int, required): Year
- `account` (string, required): Account name

**Response:**
```json
{
  "data": [
    {
      "Kategorie": "Salary",
      "Januar": 3000.00,
      "Februar": 3000.00,
      "...": "...",
      "Gesamt": 36000.00
    }
  ]
}
```

### Get Account Expenses

**GET** `/api/accounts/expenses`

Monthly expense breakdown by category for specific account/year.

**Query Parameters:**
- `year` (int): Year
- `account` (string): Account name

**Response:** Same structure as income.

### List Accounts

**GET** `/api/accounts/list`

Get all available accounts for dropdowns.

**Response:**
```json
{
  "accounts": [
    {
      "id": 1,
      "name": "Checking",
      "type": "Girokonto"
    }
  ]
}
```

### Account Management

Additional endpoints for CRUD operations:
- **POST** `/api/accounts/` - Create account
- **PUT** `/api/accounts/{account_id}` - Update account
- **DELETE** `/api/accounts/{account_id}` - Delete account

## Shares

Manage securities portfolio.

### List Shares

**GET** `/api/shares/`

Get paginated shares list with optional filtering.

**Query Parameters:**
- `page` (int): Page number
- `page_size` (int): Records per page
- `search` (string): Search by name/ISIN/WKN
- `filter` (string): Filter criteria
- `sort_by` (string): Sort field
- `sort_dir` (string): `asc` or `desc`

**Response:**
```json
{
  "shares": [
    {
      "id": 1,
      "name": "Apple Inc.",
      "isin": "US0378331005",
      "wkn": "865985",
      "current_price": 150.25,
      "currency": "USD"
    }
  ],
  "page": 1,
  "page_size": 20,
  "total": 50
}
```

### Create Share

**POST** `/api/shares/`

Add new security.

**Form Data:**
- `isin` (string, required): ISIN code
- `name` (string, optional): Security name
- `wkn` (string, optional): WKN code

### Update Share

**PUT** `/api/shares/{share_id}`

Modify security information.

### Delete Share

**DELETE** `/api/shares/{share_id}`

Remove security (fails if transactions exist).

### Share Transactions

**GET** `/api/shares/{share_id}/transactions`

Get all buy/sell/dividend transactions for a security.

**POST** `/api/shares/{share_id}/transactions`

Record new share transaction.

**Request:**
```json
{
  "date": "2025-01-15",
  "type": "buy",
  "quantity": 10,
  "price": 150.00,
  "fees": 5.00,
  "account_id": 2
}
```

### Price History

**GET** `/api/shares/{share_id}/history`

Get historical price data.

**POST** `/api/shares/{share_id}/history/upload`

Import price history from CSV.

**Form Data:**
- `file` (file): CSV with date,price columns

## Year Overview

High-level financial summaries.

### Account Balances

**GET** `/api/year-overview/account-balances`

Get account balances by type for a year.

**Query Parameters:**
- `year` (int, required): Year

**Response:**
```json
{
  "Girokonto": 5000.00,
  "Wertpapierdepot": 25000.00,
  "Krypto": 1000.00
}
```

### Monthly Balances

**GET** `/api/year-overview/account-balances-monthly`

Monthly progression of account balances.

**Query Parameters:**
- `year` (int): Year

**Response:**
```json
{
  "months": ["Jan", "Feb", "..."],
  "Girokonto": [4500, 4800, "..."],
  "Wertpapierdepot": [24000, 24500, "..."]
}
```

### Investments Overview

**GET** `/api/year-overview/investments`

Summary of investment accounts.

**Query Parameters:**
- `year` (int): Year

### Loans Overview

**GET** `/api/year-overview/loans`

Summary of loan accounts.

### Securities Overview

**GET** `/api/year-overview/securities`

Portfolio performance summary.

### Assets Month-End

**GET** `/api/year-overview/assets-month-end`

Total assets at end of each month.

## Years

**GET** `/api/years/`

Get available years from transaction data (for dropdowns).

**Response:**
```json
{
  "years": [2025, 2024, 2023]
}
```

## Settings

Manage application settings.

### Get Share Transaction Categories

**GET** `/api/settings/shares-tx-categories`

Get category assignments for share transaction types.

**Response:**
```json
{
  "categories": [
    {
      "category_id": 50,
      "type": "buy"
    },
    {
      "category_id": 51,
      "type": "sell"
    }
  ]
}
```

### Add Share Transaction Category

**POST** `/api/settings/shares-tx-categories`

Assign category to share transaction type.

**Request:**
```json
{
  "category_id": 50,
  "type": "buy"  // Options: buy, sell, dividend
}
```

### Delete Share Transaction Category

**DELETE** `/api/settings/shares-tx-categories`

Remove category assignment.

## Theme

Dynamic CSS theme management.

### Get Color Palette

**GET** `/api/theme/colors`

Fetch current color scheme.

**Response:**
```json
{
  "primary": "#007bff",
  "secondary": "#6c757d",
  "success": "#28a745",
  "...": "..."
}
```

### Get CSS

**GET** `/api/theme/css`

Generate dynamic CSS with current theme colors.

**Response:** CSS text content

## Error Handling

All endpoints return consistent error format:

```json
{
  "detail": "Error message",
  "status_code": 400
}
```

**Common Status Codes:**
- `200` - Success
- `201` - Created
- `400` - Bad Request (validation error)
- `401` - Unauthorized (missing/invalid token)
- `404` - Not Found
- `500` - Internal Server Error

## Rate Limiting

Login endpoint has rate limiting:
- **5 failed attempts** → 15-minute lockout
- Lockout resets after timeout or successful login

## CORS

API allows cross-origin requests. Configure `allow_origins` in production for specific domains.

## Data Formats

**Dates:** ISO 8601 format (`YYYY-MM-DD`)  
**Amounts:** Decimal with 2 decimal places  
**Negative values:** Expenses  
**Positive values:** Income  

## Pagination

Paginated endpoints accept:
- `page` (int, default: 1): Page number (1-based)
- `page_size` (int, default: varies, max: 1000): Records per page

Response includes:
```json
{
  "data": [...],
  "page": 1,
  "page_size": 100,
  "total": 250
}
```

## Next Steps

- Explore interactive docs: http://localhost:8000/api/docs
- See [authentication.md](authentication.md) for auth architecture
- See [config.md](config.md) for API configuration
- See [docker.md](docker/docker.md) for container deployment
