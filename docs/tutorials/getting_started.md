# Getting Started with FiniA

Step-by-step tutorial for new users to set up and start using FiniA for personal finance management.

## What is FiniA?

FiniA is a lightweight personal finance assistant that helps you:
- 📊 **Track transactions** across multiple accounts
- 📁 **Categorize expenses** automatically with smart rules
- 💰 **Plan budgets** with recurring entries
- 📈 **Manage portfolios** with securities tracking
- 📥 **Import CSV data** from banks
- 🔍 **Analyze finances** with yearly overviews

## Prerequisites

Before starting, ensure you have:
- ✅ **MySQL/MariaDB** database server (local or remote)
- ✅ **Docker** and **Docker Compose** OR **Python 3.10+**
- ✅ CSV files from your bank (optional, for imports)

## Quick Start (Docker)

### Step 1: Get FiniA

```bash
# Clone repository
git clone https://github.com/m2-eng/FiniA.git
cd FiniA
```

---

### Step 2: Configure Database

Edit `cfg/config.yaml`:

```yaml
database:
  host: 192.168.1.10      # Your MySQL server IP
  port: 3306
  name: placeholder       # Will be finiaDB_<username>
```

**Note:** Each user gets their own database: `finiaDB_<username>`

---

### Step 3: Create Override File (if needed)

For Synology NAS or custom ports:

```bash
cp docker-compose.override.yml.example docker-compose.override.yml
```

Edit `docker-compose.override.yml`:
```yaml
services:
  api:
    ports:
      - "8000:8000"  # Change if port 8000 is in use
```

---

### Step 4: Start FiniA

```bash
docker-compose up -d
```

**Wait ~30 seconds for startup.**

---

### Step 5: Access Web UI

Open browser: **http://localhost:8000**

You should see the login page.

---

## First Login & Setup

### Step 1: Login with Database Credentials

**Username:** Your MySQL username (e.g., `root`)  
**Password:** Your MySQL password

**What happens:**
- FiniA authenticates with MySQL
- Creates database: `finiaDB_<username>`
- Creates initial schema with empty tables

**First-time login may take 10-15 seconds** while database is created.

---

### Step 2: Initialize Seed Data

Seed data includes:
- Default account types (Checking, Securities, Loan, etc.)
- Planning cycles (Monthly, Yearly, Quarterly, etc.)

**Via API:**

```bash
# Get your JWT token from browser (DevTools → Application → Local Storage → auth_token)
TOKEN="your-jwt-token"

# Initialize database with seed data
curl -X POST http://localhost:8000/api/database/init \
  -H "Authorization: Bearer $TOKEN"
```

**Note:** This endpoint creates default data only once.

---

### Step 3: Explore the Interface

**Dashboard (http://localhost:8000)**
- Year overview
- Account balances
- Quick navigation

**Main Sections:**
- **Accounts** - View transactions by account
- **Categories** - Manage category hierarchy
- **Planning** - Budget recurring expenses/income
- **Shares** - Securities portfolio
- **Import** - CSV transaction import
- **Settings** - Category mappings for share transactions
- **Year Overview** - Financial summary by year

---

## Create Your First Category

Categories organize your transactions hierarchically.

### Via Web UI

**Navigate:** Categories → Click "Add Category"

**Example Hierarchy:**
```
Living Expenses (parent: none)
├─ Groceries (parent: Living Expenses)
├─ Rent (parent: Living Expenses)
└─ Utilities (parent: Living Expenses)
   ├─ Electricity (parent: Utilities)
   └─ Water (parent: Utilities)
```

**Steps:**
1. Name: `Living Expenses`
2. Parent: `(none)` for root category
3. Click "Save"

4. Name: `Groceries`
5. Parent: `Living Expenses`
6. Click "Save"

---

### Via API

```bash
# Create root category
curl -X POST http://localhost:8000/api/categories/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Living Expenses",
    "parent_id": null
  }'

# Response: {"id": 1, "name": "Living Expenses", ...}

# Create child category
curl -X POST http://localhost:8000/api/categories/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Groceries",
    "parent_id": 1
  }'
```

---

## Create Your First Account

Accounts represent bank accounts, credit cards, securities depots, etc.

### Via Web UI

**Navigate:** Account Management → Click "Add Account"

**Example: Checking Account**
- **Name:** Personal Checking
- **IBAN:** DE1234567890123456789012
- **BIC:** ABCDEFGH
- **Type:** Girokonto (Checking)
- **Start Amount:** 1000.00 (initial balance)
- **Start Date:** 2025-01-01
- **End Date:** (leave empty for active accounts)

Click "Save"

---

### Via API

```bash
curl -X POST http://localhost:8000/api/accounts/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Personal Checking",
    "iban_accountNumber": "DE1234567890123456789012",
    "bic_market": "ABCDEFGH",
    "type": 1,
    "startAmount": 1000.00,
    "dateStart": "2025-01-01",
    "dateEnd": null,
    "clearingAccount": null,
    "importFormat": null,
    "importPath": null
  }'
```

**Response:**
```json
{
  "id": 1,
  "name": "Personal Checking",
  "type": "Girokonto",
  ...
}
```

---

## Import Your First Transactions

### Step 1: Prepare CSV File

**Example: bank_transactions.csv**
```csv
Buchungstag;Wertstellung;Umsatzart;Buchungstext;Betrag;IBAN;BIC
15.01.2025;15.01.2025;Lastschrift;REWE Markt;-45.50;DE12345;ABCDEFGH
16.01.2025;16.01.2025;Gutschrift;Gehalt;3000.00;DE98765;XYZDEFGH
```

---

### Step 2: Configure Import Format

If using standard formats (Commerzbank, Sparkasse, etc.), skip to Step 3.

**For custom banks:**

Edit `cfg/import_formats.yaml`:

```yaml
formats:
  csv-mybank:
    description: "My Bank CSV Format"
    delimiter: ";"
    encoding: "ISO-8859-1"
    skip_rows: 0
    date_format: "%d.%m.%Y"
    columns:
      strategy: names
      mapping:
        dateValue: "Buchungstag"
        description: "Umsatzart"
        recipientApplicant: "Buchungstext"
        amount: "Betrag"
        iban: "IBAN"
        bic: "BIC"
```

**See:** [CSV Import Documentation](../import/csv_import.md)

---

### Step 3: Import via Web UI

**Navigate:** Import Transactions

1. Select **Account:** Personal Checking
2. Select **Format:** csv-mybank (or your format)
3. Click **Choose File:** bank_transactions.csv
4. ✅ Check "Apply category automation rules"
5. Click **Import**

**Result:**
```
✅ Import successful!
Imported: 2 transactions
Duplicates: 0
Errors: 0
```

---

### Step 4: Import via API

```bash
curl -X POST http://localhost:8000/api/transactions/import-csv \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@bank_transactions.csv" \
  -F "import_format=csv-mybank" \
  -F "account_id=1"
```

**Response:**
```json
{
  "status": "success",
  "imported": 2,
  "duplicates": 0,
  "errors": 0
}
```

---

### Step 5: View Transactions

**Navigate:** Accounts → Select "Personal Checking"

You should see:
- 15.01.2025 | REWE Markt | -45.50 | (Uncategorized)
- 16.01.2025 | Gehalt | +3000.00 | (Uncategorized)

---

## Categorize Transactions

### Manual Categorization

**Via Web UI:**

1. Click on transaction
2. Select category from dropdown: "Groceries"
3. Click "Save"

**Via API:**

```bash
# Get transaction ID (e.g., 1)
# Get category ID for "Groceries" (e.g., 2)

curl -X PUT http://localhost:8000/api/transactions/1/entries \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "entries": [
      {
        "id": 1,
        "category_id": 2,
        "amount": -45.50
      }
    ]
  }'
```

---

### Automatic Categorization (Recommended)

**Create Automation Rule:**

**Navigate:** Categories → Automation Rules → Add Rule

**Example: Auto-categorize REWE transactions**

- **Category:** Groceries
- **Field:** Recipient/Applicant
- **Pattern:** REWE
- **Match Type:** contains
- **Account:** (leave empty for all accounts)
- **Active:** ✅

Click "Save"

---

**Apply to Existing Transactions:**

```bash
curl -X POST http://localhost:8000/api/transactions/auto-categorize \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "account_id": null
  }'
```

**Result:**
```json
{
  "categorized": 1,
  "total_checked": 2,
  "message": "1 entry categorized successfully"
}
```

**See:** [Category Automation Guide](../features/category_automation.md)

---

## Create Budget Planning

Plan recurring expenses/income.

### Example: Monthly Rent

**Navigate:** Planning → Add Planning

- **Name:** Rent
- **Amount:** -800.00 (negative = expense)
- **Category:** Rent
- **Cycle:** Monthly
- **Account:** Personal Checking
- **Start Date:** 2025-01-01
- **End Date:** (leave empty for ongoing)

Click "Save"

---

**Generate Entries:**

Click "Generate Entries" to create future planned transactions.

**View Entries:**

Planning shows 12 months of upcoming rent payments (-800.00 each).

---

### Via API

```bash
# Create planning
curl -X POST http://localhost:8000/api/planning/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Rent",
    "amount": -800.00,
    "cycle_id": 1,
    "category_id": 3,
    "account_id": 1,
    "dateStart": "2025-01-01",
    "dateEnd": null
  }'

# Generate entries
curl -X POST http://localhost:8000/api/planning/1/entries/generate \
  -H "Authorization: Bearer $TOKEN"
```

---

## View Year Overview

**Navigate:** Year Overview

**Select Year:** 2025

**See:**
- **Account Balances** by type
- **Monthly Balance Progression**
- **Investments Overview**
- **Loans Overview**
- **Securities Portfolio**
- **Assets at Month-End**

---

## Split Transactions

Sometimes one transaction needs multiple categories.

**Example: Grocery + Household Items**

**Original Transaction:**
- REWE Markt | -75.00

**Split into:**
- Groceries: -50.00
- Household Items: -25.00

---

**Via Web UI:**

1. Click transaction
2. Click "Split" button
3. Add entry:
   - Category: Groceries
   - Amount: -50.00
4. Add entry:
   - Category: Household Items
   - Amount: -25.00
5. Save

**Total must equal original amount (-75.00).**

---

**Via API:**

```bash
curl -X PUT http://localhost:8000/api/transactions/1/entries \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "entries": [
      {
        "id": 1,
        "category_id": 2,
        "amount": -50.00
      },
      {
        "category_id": 8,
        "amount": -25.00
      }
    ]
  }'
```

---

## Mark Transactions as Checked

After reviewing transactions:

**Via Web UI:**

1. Select transactions (checkbox)
2. Click "Mark as Checked"

**Via API:**

```bash
curl -X POST http://localhost:8000/api/transactions/mark-checked \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "transaction_ids": [1, 2, 3]
  }'
```

---

## Advanced: Portfolio Management

### Add Share

**Navigate:** Shares → Add Share

- **ISIN:** US0378331005 (Apple Inc.)
- **Name:** Apple Inc.
- **WKN:** 865985

---

### Record Transaction

**Buy 10 shares:**

- **Date:** 2025-01-15
- **Type:** Buy
- **Quantity:** 10
- **Price:** 150.00
- **Fees:** 5.00
- **Account:** Securities Depot

**Total:** -1505.00 (10 × 150.00 + 5.00)

---

### Import Price History

**Prepare CSV:** `apple_prices.csv`
```csv
ISIN,Date,Price
US0378331005,2025-01-15,150.00
US0378331005,2025-01-31,152.50
```

**Import:**

```bash
curl -X POST http://localhost:8000/api/shares/import/history \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@apple_prices.csv"
```

---

## Next Steps

### Explore Features

- ✅ **Set up more automation rules** for common expenses
- ✅ **Import historical data** from past months
- ✅ **Create planning entries** for all recurring transactions
- ✅ **Configure multiple accounts** (checking, savings, credit cards)
- ✅ **Track securities** if you have investments

### Customize

- **Add custom import formats** in `cfg/import_formats.yaml`
- **Configure themes** (Dark/Light mode toggle in UI)
- **Set up category mappings** for share transaction types
- **Create complex automation rules** with regex

### Backup

- **Database backups:** See [Backup Guide](../backup.md)
- **Configuration backups:** Version control `cfg/` folder
- **Export data:** Use API to extract data periodically

---

## Common Tasks Reference

### Check Health Status

```bash
curl http://localhost:8000/api/health
```

### List All Categories

```bash
curl http://localhost:8000/api/categories/list \
  -H "Authorization: Bearer $TOKEN"
```

### Get Transactions for Account

```bash
curl "http://localhost:8000/api/transactions/?account=Personal%20Checking&page=1&page_size=50" \
  -H "Authorization: Bearer $TOKEN"
```

### Get Year Overview

```bash
curl "http://localhost:8000/api/year-overview/account-balances?year=2025" \
  -H "Authorization: Bearer $TOKEN"
```

### Logout

```bash
curl -X POST http://localhost:8000/api/auth/logout \
  -H "Authorization: Bearer $TOKEN"
```

---

## Troubleshooting

### Can't Access Web UI

**Check:**
```bash
docker-compose ps
# Should show "finia-api" running

docker-compose logs api
# Check for errors
```

**Verify port:**
```bash
netstat -tulpn | grep 8000
# Should show Docker listening on port 8000
```

---

### Login Fails

**Check database connection:**
```bash
# From Docker container
docker exec -it finia-api mysql -h <db_host> -u <username> -p
```

**Verify credentials:**
- MySQL username and password are correct
- User has CREATE DATABASE privileges

---

### Import Fails

**Common issues:**
- Wrong delimiter (`;` vs `,`)
- Incorrect encoding (UTF-8 vs ISO-8859-1)
- Date format mismatch
- Missing required columns

**Debug:**
- Check `docker-compose logs api` for errors
- Verify format in `cfg/import_formats.yaml`
- Test with small sample file first

---

### Transactions Not Auto-Categorized

**Check:**
1. Rule is **active** ✅
2. Pattern matches transaction data
3. Account filter doesn't exclude transaction
4. "Apply automation" was enabled during import

**Test rule:**

Use API test endpoint to debug:
```bash
curl -X POST http://localhost:8000/api/category-automation/rules/test \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "rule": { ... },
    "transaction": { ... }
  }'
```

---

## Further Reading

- [Database Schema](../database/schema.md) - Table structure reference
- [CSV Import System](../import/csv_import.md) - Detailed import guide
- [Category Automation](../features/category_automation.md) - Advanced rules
- [API Documentation](../api.md) - Complete REST API reference
- [Docker Deployment](../docker/docker.md) - Container setup
- [Production Deployment](../deployment/production.md) - nginx, SSL, security

---

## Support & Community

- **GitHub Issues:** https://github.com/m2-eng/FiniA/issues
- **Documentation:** https://github.com/m2-eng/FiniA/docs
- **License:** AGPL-3.0 (see [LICENSE](../../LICENSE))

---

**Congratulations! You're now ready to manage your finances with FiniA.** 🎉
