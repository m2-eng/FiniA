# CSV Import System

Comprehensive guide to FiniA's CSV transaction import functionality.

## Overview

FiniA provides flexible CSV import with:
- **Multiple format support** via configuration files
- **Duplicate detection** using SHA-256 hashes
- **Flexible column mapping** with three strategies (names, join, regex)
- **API and Web UI** import interfaces
- **Account-specific** or **multi-account** imports

## Architecture

```
┌────────────────────────────────────────────────────────────┐
│                    CSV Import Flow                          │
├────────────────────────────────────────────────────────────┤
│                                                             │
│  1. CSV File Upload (Web UI or API)                        │
│           ↓                                                 │
│  2. AccountDataImporter.import_csv()                        │
│           ↓                                                 │
│  3. Load Format from cfg/import_formats.yaml                │
│           ↓                                                 │
│  4. Parse CSV with Mapping Strategy                         │
│     ├─ names:  Match column headers                         │
│     ├─ join:   Combine multiple columns                     │
│     └─ regex:  Extract via patterns                         │
│           ↓                                                 │
│  5. Compute Import Hash (SHA-256)                           │
│           ↓                                                 │
│  6. Insert Transaction (skip duplicates)                    │
│           ↓                                                 │
│  7. Create Accounting Entry                                 │
│           ↓                                                 │
│  8. Apply Category Automation Rules                         │
│           ↓                                                 │
│  9. Return Statistics (imported/duplicates/errors)          │
│                                                             │
└────────────────────────────────────────────────────────────┘
```

## Components

### AccountDataImporter

**Location:** `src/services/account_data_importer.py`

Main service class for CSV imports.

**Key Methods:**

```python
class AccountDataImporter:
    def __init__(self, db: Database):
        """Initialize with database connection."""
    
    def import_csv(
        self,
        csv_path: Path,
        format_name: str,
        account_id: int,
        apply_automation: bool = True
    ) -> dict:
        """
        Import CSV file with specified format.
        
        Args:
            csv_path: Path to CSV file
            format_name: Format key from import_formats.yaml
            account_id: Target account ID
            apply_automation: Apply category automation rules
        
        Returns:
            {
                "imported": 15,
                "duplicates": 3,
                "errors": 0,
                "messages": []
            }
        """
```

### Import Format Configuration

**Location:** `cfg/import_formats.yaml`

Defines CSV parsing rules for different banks/sources.

**See:** [Import Formats Documentation](../cfg/import_formats.md)

## Mapping Strategies

FiniA supports three column mapping strategies for maximum flexibility:

### 1. Names Strategy (Simple)

Match CSV columns by header names.

**Example: Commerzbank CSV**

```yaml
formats:
  csv-cb:
    description: "Commerzbank CSV format"
    delimiter: ";"
    encoding: "ISO-8859-1"
    skip_rows: 0
    date_format: "%d.%m.%Y"
    columns:
      strategy: names
      mapping:
        dateValue: "Buchungstag"
        dateCreation: "Wertstellung"
        description: "Umsatzart"
        recipientApplicant: "Buchungstext"
        amount: "Betrag"
        iban: "IBAN"
        bic: "BIC"
```

**CSV Structure:**
```
Buchungstag;Wertstellung;Umsatzart;Buchungstext;Betrag;IBAN;BIC
15.01.2025;15.01.2025;Lastschrift;REWE Markt;-45.50;DE12345;ABCDEFGH
```

**Result:**
- `dateValue` = "15.01.2025"
- `recipientApplicant` = "REWE Markt"
- `amount` = -45.50

---

### 2. Join Strategy (Combine Columns)

Concatenate multiple columns into one field.

**Example: Sparkasse CSV**

```yaml
formats:
  csv-spk:
    description: "Sparkasse CSV format"
    delimiter: ";"
    encoding: "ISO-8859-1"
    skip_rows: 1
    date_format: "%d.%m.%y"
    columns:
      strategy: join
      mapping:
        dateValue: "Buchungstag"
        dateCreation: "Valutadatum"
        description:
          join: ["Buchungstext", "Verwendungszweck"]
          separator: " - "
        recipientApplicant: "Beguenstigter/Zahlungspflichtiger"
        amount: "Betrag"
        iban: "Kontonummer"
        bic: "BLZ"
```

**CSV Structure:**
```
Buchungstag;Valutadatum;Buchungstext;Verwendungszweck;Betrag;Beguenstigter/Zahlungspflichtiger;Kontonummer;BLZ
15.01.25;15.01.25;Überweisung;Rechnung 12345;-100.00;Max Mustermann;DE12345;12345678
```

**Result:**
- `description` = "Überweisung - Rechnung 12345"

---

### 3. Regex Strategy (Pattern Extraction)

Extract data using regular expressions with capture groups.

**Example: Mintos CSV**

```yaml
formats:
  csv-mintos:
    description: "Mintos loan platform CSV"
    delimiter: ","
    encoding: "UTF-8"
    skip_rows: 0
    date_format: "%Y-%m-%d %H:%M:%S"
    columns:
      strategy: regex
      mapping:
        dateValue:
          column: "Date"
          pattern: "^(\\d{4}-\\d{2}-\\d{2})"
          group: 1
        description:
          column: "Details"
          pattern: "^([^\\(]+)"
          group: 1
        amount:
          column: "Turnover"
          pattern: "^([+-]?\\d+\\.\\d+)"
          group: 1
        recipientApplicant:
          column: "Details"
          pattern: "\\((.+?)\\)"
          group: 1
```

**CSV Structure:**
```
Date,Details,Turnover
2025-01-15 10:30:00,Interest Income (Loan #12345),+5.25
```

**Result:**
- `dateValue` = "2025-01-15"
- `description` = "Interest Income"
- `recipientApplicant` = "Loan #12345"
- `amount` = 5.25

**Pattern Explanation:**
- `^(\\d{4}-\\d{2}-\\d{2})`: Capture date at start (YYYY-MM-DD)
- `^([^\\(]+)`: Capture text before first parenthesis
- `\\((.+?)\\)`: Capture text inside parentheses

---

## Duplicate Detection

FiniA prevents duplicate imports using SHA-256 hashes stored in `tbl_transaction.importHash`.

### Hash Computation

**Formula:**
```python
import hashlib

def compute_import_hash(account_id, date_value, amount, description, recipient):
    """
    Generate SHA-256 hash for duplicate detection.
    
    Components:
    - account_id: Ensures same transaction on different accounts
    - date_value: Transaction date
    - amount: Transaction amount
    - description: Transaction description
    - recipient: Recipient/sender name
    """
    data = f"{account_id}{date_value}{amount}{description}{recipient}"
    return hashlib.sha256(data.encode('utf-8')).hexdigest()
```

**Example:**
```python
account_id = 1
date_value = "2025-01-15"
amount = -45.50
description = "Lastschrift"
recipient = "REWE Markt"

hash_input = "12025-01-15-45.5LastschriftREWE Markt"
import_hash = "a3f5d8e7c2b1..."  # SHA-256 result
```

### Database Constraint

```sql
CREATE TABLE tbl_transaction (
  ...
  importHash VARCHAR(64) UNIQUE,
  ...
);
```

**Behavior:**
- **First import:** Transaction inserted successfully
- **Duplicate import:** INSERT fails silently (logged as duplicate)
- **Result:** Statistics include `"duplicates": 3`

---

## Import Workflows

### API Import

**Endpoint:** POST `/api/transactions/import-csv`

**Request:**
```http
POST /api/transactions/import-csv HTTP/1.1
Content-Type: multipart/form-data
Authorization: Bearer <token>

file: [CSV file]
import_format: "csv-cb"
account_id: 1
```

**Response:**
```json
{
  "status": "success",
  "imported": 25,
  "duplicates": 5,
  "errors": 0,
  "messages": [
    "Processed 30 rows",
    "25 new transactions",
    "5 duplicates skipped"
  ]
}
```

**cURL Example:**
```bash
curl -X POST http://localhost:8000/api/transactions/import-csv \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@/path/to/transactions.csv" \
  -F "import_format=csv-cb" \
  -F "account_id=1"
```

---

### Web UI Import

**Location:** `http://localhost:8000/import_transactions.html`

**Steps:**
1. Select account from dropdown
2. Select import format
3. Choose CSV file
4. Click "Import"
5. View statistics (imported/duplicates)

**JavaScript Implementation:**
```javascript
// src/web/import_transactions.js

async function importCSV() {
    const formData = new FormData();
    formData.append('file', fileInput.files[0]);
    formData.append('import_format', formatSelect.value);
    formData.append('account_id', accountSelect.value);
    
    const response = await authenticatedFetch(
        '/api/transactions/import-csv',
        {
            method: 'POST',
            body: formData
        }
    );
    
    const result = await response.json();
    showResult(result);
}
```

---

## Multi-Account CSV Import

Some CSV files include an account column for importing transactions across multiple accounts.

**Format Configuration:**
```yaml
formats:
  csv-loan:
    description: "Loan CSV with account column"
    delimiter: ","
    encoding: "UTF-8"
    columns:
      strategy: names
      mapping:
        account:
          column: "Account Name"
          # Maps to tbl_account.name
        dateValue: "Date"
        amount: "Amount"
        description: "Description"
```

**CSV Structure:**
```
Account Name,Date,Amount,Description
Loan Account 1,2025-01-15,-500.00,Loan payment
Loan Account 2,2025-01-15,-300.00,Loan payment
```

**Import Behavior:**
- If CSV has `account` column: Use it to determine target account
- If no `account` column: Use `account_id` parameter for all rows
- API validates account existence before import

---

## Category Automation

After import, FiniA automatically applies categorization rules.

**Flow:**
1. Transaction imported → Accounting entry created
2. Entry has `category = NULL`
3. Automation rules evaluated (see [Category Automation](../features/category_automation.md))
4. Matching rule found → Category assigned
5. Entry updated with `category_id`

**Disable Automation:**
```python
# API parameter
apply_automation=False

# Web UI checkbox
[ ] Apply category automation rules
```

---

## Error Handling

### Common Errors

**1. Invalid CSV Format**
```json
{
  "status": "error",
  "message": "CSV delimiter mismatch. Expected ';', found ','"
}
```

**Solution:** Check `delimiter` in format configuration.

---

**2. Date Parsing Error**
```json
{
  "status": "error",
  "message": "Unable to parse date '15/01/2025' with format '%d.%m.%Y'"
}
```

**Solution:** Adjust `date_format` in format configuration.

---

**3. Missing Required Columns**
```json
{
  "status": "error",
  "message": "Required column 'Buchungstag' not found in CSV"
}
```

**Solution:** Verify CSV structure matches format definition.

---

**4. Encoding Issues**
```
UnicodeDecodeError: 'utf-8' codec can't decode byte 0xe4
```

**Solution:** Set correct `encoding` (common: `ISO-8859-1`, `UTF-8`, `Windows-1252`).

---

**5. Account Not Found**
```json
{
  "status": "error",
  "message": "Account with name 'Unknown Account' not found"
}
```

**Solution:** Create account first or check account name spelling.

---

### Logging

Import operations log to console:

```
INFO: Starting CSV import for account 1 with format 'csv-cb'
INFO: Processed 30 rows: 25 imported, 5 duplicates, 0 errors
INFO: Applied category automation to 15 entries
```

---

## Performance Considerations

### Batch Inserts

FiniA uses individual inserts with duplicate detection:
- **Pros:** Precise error handling per row
- **Cons:** Slower for large files (>10,000 rows)

**Optimization:**
- Import during off-peak hours
- Split large files into smaller batches

### Database Locks

The `Database` class uses a global lock for serial execution:
```python
# src/Database.py
_global_lock = threading.RLock()
```

**Impact:**
- Only one import at a time
- Prevents race conditions
- May queue multiple concurrent imports

---

## Custom Format Creation

### Step 1: Analyze CSV Structure

**Example CSV:**
```
"Transaction Date","Description","Debit","Credit"
"2025-01-15","Grocery Store","45.50",""
"2025-01-16","Salary","","3000.00"
```

### Step 2: Add to import_formats.yaml

```yaml
formats:
  csv-custom:
    description: "Custom bank CSV format"
    delimiter: ","
    encoding: "UTF-8"
    skip_rows: 0
    date_format: "%Y-%m-%d"
    columns:
      strategy: names
      mapping:
        dateValue: "Transaction Date"
        description: "Description"
        amount:
          # Combine Debit (negative) and Credit (positive)
          join: ["Debit", "Credit"]
          transform: "debit_credit"  # Special handler
```

### Step 3: Register Format in Database

```sql
INSERT INTO tbl_accountImportFormat (dateImport, type, fileEnding)
VALUES (NOW(), 'Custom Bank', '.csv');
```

### Step 4: Test Import

```bash
# Via API
curl -X POST http://localhost:8000/api/transactions/import-csv \
  -H "Authorization: Bearer TOKEN" \
  -F "file=@test.csv" \
  -F "import_format=csv-custom" \
  -F "account_id=1"
```

---

## Best Practices

### CSV Preparation
1. **Remove header rows** if not needed (use `skip_rows`)
2. **Check encoding** (Excel exports often use ISO-8859-1)
3. **Validate date format** consistency
4. **Remove trailing commas** in delimited files

### Format Configuration
1. **Test with sample data** before full import
2. **Use descriptive format names** (e.g., `csv-bank-name-yyyy`)
3. **Document special cases** in `description` field
4. **Validate regex patterns** with online tools

### Import Workflow
1. **Backup database** before large imports
2. **Import in batches** for large files
3. **Review duplicates** manually if count seems high
4. **Check uncategorized** entries after import
5. **Enable automation** for recurring transaction patterns

---

## Troubleshooting

### Debug Mode

Enable verbose logging:

```python
# src/services/account_data_importer.py
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Inspect Import Hash

```sql
-- Check if transaction exists
SELECT * FROM tbl_transaction
WHERE importHash = 'a3f5d8e7c2b1...';
```

### Verify Column Mapping

```python
# Print parsed CSV row
print(f"Parsed row: {row_dict}")
```

### Test Date Parsing

```python
from datetime import datetime

date_str = "15.01.2025"
date_format = "%d.%m.%Y"
parsed = datetime.strptime(date_str, date_format)
print(parsed)  # 2025-01-15 00:00:00
```

---

## API Reference

**Import CSV:**
- Endpoint: POST `/api/transactions/import-csv`
- Documentation: [API Docs](../api.md#import-csv)

**Get Import Formats:**
- Endpoint: GET `/api/transactions/import-formats`
- Returns: List of available format names

**Import from YAML:**
- Endpoint: POST `/api/transactions/import`
- Source: `cfg/data.yaml` account_data section

---

## See Also

- [Import Formats Configuration](../cfg/import_formats.md) - Format syntax reference
- [Category Automation](../features/category_automation.md) - Auto-categorization after import
- [Database Schema](../database/schema.md) - Transaction and entry tables
- [API Documentation](../api.md) - REST API endpoints
- [Web UI](../frontend/architecture.md) - Import interface usage
