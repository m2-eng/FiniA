# Category Automation - User Guide

Practical guide to automatically categorize transactions using flexible rule-based automation.

## Overview

Category Automation eliminates manual categorization by applying configurable rules to incoming transactions. Each rule matches transaction properties (description, recipient, amount, IBAN) and assigns a category automatically.

**Benefits:**
- ⏱️ **Save time** - No manual categorization for recurring transactions
- ✅ **Consistency** - Same transactions always get same category
- 🎯 **Flexibility** - Multiple conditions, account filters, regex support
- 🔄 **Retroactive** - Apply rules to existing uncategorized transactions

## Quick Start

### Example: Auto-categorize grocery shopping

**Goal:** All transactions from REWE should be categorized as "Groceries"

**Rule:**
```
Field: recipientApplicant
Pattern: REWE
Match Type: contains
Category: Groceries
```

**Result:** Any transaction with "REWE" in recipient → Category "Groceries"

## Rule Structure

Each rule consists of:

| Component | Description | Example |
|-----------|-------------|---------|
| **Category** | Target category | "Groceries" |
| **Conditions** | Match criteria | Recipient contains "REWE" |
| **Logic** | Combine conditions | AND / OR |
| **Accounts** | Scope (optional) | Only "Checking Account" |
| **Priority** | Order of evaluation | 1 (highest) |
| **Status** | Active/Inactive | Active |

## Creating Rules

### Via Web UI

**Location:** `http://localhost:8000/categories.html` → "Automation Rules" tab

**Steps:**
1. Click "Add Rule"
2. Select target category
3. Add condition:
   - Choose field (description, recipient, amount, IBAN)
   - Choose operator (contains, equals, regex, etc.)
   - Enter pattern
4. Optionally: Limit to specific accounts
5. Save

### Via API

**Endpoint:** POST `/api/category-automation/rules`

**Request:**
```json
{
  "category_id": 5,
  "field": "recipientApplicant",
  "pattern": "REWE",
  "match_type": "contains",
  "account_id": null,
  "active": true
}
```

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

## Match Types

### 1. Contains (Case-Insensitive)

Checks if pattern appears anywhere in field.

**Pattern:** `REWE`  
**Matches:**
- "REWE Markt"
- "Einkauf bei REWE"
- "rewe.de Online"

**Use Case:** Most common for recipient/description matching

---

### 2. Equals (Exact Match)

Field must exactly match pattern.

**Pattern:** `Salary`  
**Matches:**
- "Salary" ✓
- "Monthly Salary" ✗
- "salary" ✗ (case-sensitive)

**Use Case:** Specific transaction descriptions

---

### 3. Starts With

Field begins with pattern.

**Pattern:** `Amazon`  
**Matches:**
- "Amazon EU" ✓
- "Amazon Prime" ✓
- "Online Amazon" ✗

**Use Case:** Standardized prefixes

---

### 4. Ends With

Field ends with pattern.

**Pattern:** `.com`  
**Matches:**
- "paypal.com" ✓
- "amazon.com" ✓
- ".com/shop" ✗

**Use Case:** Domain matching

---

### 5. Regex (Regular Expression)

Advanced pattern matching with full regex support.

**Pattern:** `^REWE\s+\d{4}$`  
**Matches:**
- "REWE 1234" ✓
- "REWE 5678" ✓
- "REWE Markt" ✗

**Use Case:** Complex patterns, IBAN validation, structured data

---

## Fields

### recipientApplicant

The person or entity receiving/sending money.

**Examples:**
- "REWE Markt GmbH"
- "Max Mustermann"
- "Amazon EU S.a.r.L"

**Common Rules:**
```
Pattern: "REWE"        → Groceries
Pattern: "Amazon"      → Online Shopping
Pattern: "Stadtwerke"  → Utilities
```

---

### description

Transaction description or purpose.

**Examples:**
- "Lastschrift"
- "Überweisung"
- "SEPA-Lastschrift"

**Common Rules:**
```
Pattern: "Gehalt"      → Salary (Income)
Pattern: "Miete"       → Rent
Pattern: "Dauerauftrag" → Recurring Payment
```

---

### iban

Counterparty IBAN.

**Examples:**
- "DE89370400440532013000"
- "DE12345678901234567890"

**Common Rules:**
```
Pattern: "^DE893704"   → Specific bank
Pattern: "DE12345.*"   → Specific account
```

**Use Case:** Match exact sender (employer IBAN → Salary)

---

### amount

Transaction amount (numeric).

**Operators:**
- `equals`: Exact amount
- `greater_than`: Minimum amount
- `less_than`: Maximum amount
- `between`: Amount range

**Examples:**
```
amount equals -800.00     → Rent (fixed amount)
amount less_than -1000    → Large expenses
amount greater_than 2000  → High income
```

---

## Multiple Conditions

Combine multiple conditions for precise matching.

### AND Logic

**All conditions must match.**

**Example: Netflix subscription**
```
Condition 1: recipientApplicant contains "Netflix"
Condition 2: amount equals -15.99
Logic: AND
→ Category: Streaming Services
```

**Use Case:** Avoid false positives (e.g., Netflix gift card purchase vs. subscription)

---

### OR Logic

**Any condition can match.**

**Example: Grocery stores**
```
Condition 1: recipientApplicant contains "REWE"
Condition 2: recipientApplicant contains "EDEKA"
Condition 3: recipientApplicant contains "Lidl"
Logic: OR
→ Category: Groceries
```

**Use Case:** Multiple vendors for same category

---

### Complex Logic (Parentheses)

**Mix AND/OR with grouping.**

**Example: Large grocery shopping**
```
(recipientApplicant contains "REWE" OR recipientApplicant contains "EDEKA")
AND amount less_than -50.00
→ Category: Large Grocery Shopping
```

**Use Case:** Fine-grained categorization

---

## Account Filters

Limit rules to specific accounts.

**Example: Business vs. Personal**

**Rule 1: Personal Groceries**
```
Pattern: "REWE"
Category: Groceries (Personal)
Account: Personal Checking
```

**Rule 2: Business Groceries**
```
Pattern: "REWE"
Category: Office Supplies
Account: Business Checking
```

**Result:** Same recipient, different categories based on account

---

## Regex Examples

### IBAN Matching

**Pattern:** `^DE\d{20}$`  
**Matches:** Valid German IBANs  
**Use Case:** Validate IBAN format

**Pattern:** `^DE893704`  
**Matches:** Specific bank prefix  
**Use Case:** Categorize by sender bank

---

### Amount Extraction

**Pattern:** `-?\d+\.\d{2}`  
**Matches:** Decimal amounts  
**Use Case:** Extract embedded amounts from descriptions

---

### Reference Number

**Pattern:** `#\d{5,10}`  
**Matches:** Transaction references like "#12345"  
**Use Case:** Link transactions to invoices

---

### Date Pattern

**Pattern:** `\d{2}\.\d{2}\.\d{4}`  
**Matches:** Dates in DD.MM.YYYY format  
**Use Case:** Extract transaction dates from descriptions

---

### Email Address

**Pattern:** `[\w\.-]+@[\w\.-]+\.\w+`  
**Matches:** Email addresses  
**Use Case:** Categorize by sender email

---

## Priority & Order

Rules are evaluated in priority order (1 = highest).

**Example:**

**Rule 1 (Priority 1):** REWE + amount < -50 → Bulk Groceries  
**Rule 2 (Priority 2):** REWE → Groceries

**Transaction:** REWE, -75.00  
**Result:** Matched by Rule 1 (checked first)

**Transaction:** REWE, -20.00  
**Result:** Matched by Rule 2 (Rule 1 doesn't match)

**Best Practice:**
- Specific rules (more conditions) → Higher priority
- General rules → Lower priority

---

## Testing Rules

Before activating, test rules against sample data.

### API Test Endpoint

**Endpoint:** POST `/api/category-automation/rules/test`

**Request:**
```json
{
  "rule": {
    "category": 5,
    "conditions": [
      {
        "field": "recipientApplicant",
        "operator": "contains",
        "value": "REWE"
      }
    ],
    "conditionLogic": "AND"
  },
  "transaction": {
    "description": "Grocery shopping",
    "recipientApplicant": "REWE Markt",
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

---

## Applying Rules

### Auto-Apply on Import

Enabled by default during CSV import:
- Transaction imported
- Rules evaluated immediately
- Category assigned automatically

**Disable:**
- API: `apply_automation=False`
- Web UI: Uncheck "Apply automation"

---

### Manual Application

Apply rules to existing uncategorized transactions.

**Endpoint:** POST `/api/transactions/auto-categorize`

**Request:**
```json
{
  "account_id": 1  // null = all accounts
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

**Use Case:**
- Rules added after import
- Re-categorize after rule changes
- Clean up old uncategorized entries

---

## Common Patterns

### 1. Salary

```
Condition 1: description contains "Gehalt"
Condition 2: iban equals "DE893704..." (employer IBAN)
Condition 3: amount greater_than 2000
Logic: AND
Category: Salary (Income)
```

---

### 2. Rent

```
Condition 1: recipientApplicant equals "Landlord Name"
Condition 2: amount equals -800.00
Logic: AND
Category: Rent
```

---

### 3. Utilities

```
Condition 1: recipientApplicant contains "Stadtwerke"
Condition 2: description contains "Strom|Gas|Wasser" (regex)
Logic: AND
Category: Utilities
```

---

### 4. Online Shopping

```
Condition 1: recipientApplicant matches "Amazon|eBay|Zalando" (regex)
Logic: AND
Category: Online Shopping
```

---

### 5. Cash Withdrawal

```
Condition 1: description contains "Bargeldauszahlung"
Condition 2: amount less_than 0
Logic: AND
Category: Cash Withdrawal
```

---

### 6. Savings Transfer

```
Condition 1: description contains "Dauerauftrag"
Condition 2: recipientApplicant contains "Savings Account"
Condition 3: amount equals -500.00
Logic: AND
Category: Savings
```

---

## Best Practices

### Rule Design
1. **Start specific** - Add general rules later
2. **Test thoroughly** - Use test endpoint before activation
3. **Use priorities** - Order matters for overlapping rules
4. **Document patterns** - Add descriptions to rules
5. **Review regularly** - Check uncategorized entries for new patterns

### Pattern Creation
1. **Case-insensitive** - "contains" handles case automatically
2. **Avoid typos** - Test with actual transaction data
3. **Flexible matching** - Use partial strings (not full text)
4. **Regex validation** - Test patterns with online tools
5. **Escape special chars** - In regex: `\.` for literal dot

### Maintenance
1. **Disable unused rules** - Don't delete (historical data)
2. **Update for changes** - Vendor name changes, amount adjustments
3. **Monitor matches** - Check recently categorized entries
4. **Refine patterns** - Improve accuracy over time
5. **Backup rules** - Export rule configurations

---

## Troubleshooting

### Rule Not Matching

**Check:**
1. Rule is **active**
2. **Account filter** doesn't exclude transaction
3. **Pattern** is case-insensitive for "contains"
4. **Field** has data (not NULL)
5. **Priority** - Higher priority rule matched first

**Debug:**
```sql
-- Check transaction fields
SELECT description, recipientApplicant, amount, iban
FROM tbl_transaction
WHERE id = 123;

-- Check rules
SELECT * FROM tbl_setting
WHERE key = 'category_automation';
```

---

### Multiple Rules Match

**Behavior:** First matching rule (by priority) wins

**Solution:**
1. Adjust priorities
2. Add more specific conditions to higher-priority rules
3. Use account filters to separate overlapping rules

---

### Regex Not Working

**Common Issues:**
- Missing escape characters: `\.` not `.`
- Invalid pattern: Test with https://regex101.com
- Wrong flags: FiniA uses case-insensitive by default

**Example:**
```
Pattern: amazon.com     → Matches "amazonXcom" (dot = any char)
Pattern: amazon\.com    → Matches "amazon.com" (literal dot)
```

---

### Performance Issues

**Symptoms:**
- Slow categorization
- Import takes too long

**Solutions:**
1. Reduce regex complexity
2. Use "contains" instead of regex when possible
3. Limit account filters
4. Review rule priority order (most common rules first)

---

## Advanced Topics

### JSON Storage

Rules are stored in `tbl_setting` as JSON:

```sql
SELECT value FROM tbl_setting
WHERE key = 'category_automation';
```

**Result:**
```json
{
  "id": "rule-uuid",
  "name": "REWE Groceries",
  "description": "Auto-categorize grocery shopping",
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
}
```

---

### Rule Conditions Schema

```typescript
interface Rule {
  id: string;
  name: string;
  description: string;
  conditions: Condition[];
  conditionLogic: "AND" | "OR" | string; // Supports "UND", "ODER"
  category: number;
  accounts: number[];
  priority: number;
  enabled: boolean;
}

interface Condition {
  field: "description" | "recipientApplicant" | "amount" | "iban";
  operator: "contains" | "equals" | "startsWith" | "endsWith" | "regex" | 
            "greater_than" | "less_than" | "between";
  value: string | number;
  value2?: number; // For "between" operator
}
```

---

### Custom Logic Expressions

Beyond simple AND/OR, use complex expressions:

**Example:**
```
(condition_0 OR condition_1) AND condition_2
```

**Usage:**
- Group related conditions
- Implement XOR logic
- Build decision trees

**See:** [Category Automation Rules Technical Spec](category-automation-rules.md)

---

## API Reference

**List Rules:**
- GET `/api/category-automation/rules`
- Returns paginated rule list

**Get Rule:**
- GET `/api/category-automation/rules/{id}`
- Returns single rule details

**Create Rule:**
- POST `/api/category-automation/rules`
- Creates new rule

**Update Rule:**
- PUT `/api/category-automation/rules/{id}`
- Modifies existing rule

**Delete Rule:**
- DELETE `/api/category-automation/rules/{id}`
- Removes rule

**Test Rule:**
- POST `/api/category-automation/rules/test`
- Test rule against sample data

**Apply Rules:**
- POST `/api/transactions/auto-categorize`
- Apply to uncategorized entries

**Full Documentation:** [API Docs](../api.md#category-automation)

---

## See Also

- [Category Automation Technical Spec](category-automation-rules.md) - Implementation details
- [CSV Import](../import/csv_import.md) - Auto-categorization during import
- [API Documentation](../api.md) - REST API endpoints
- [Database Schema](../database/schema.md) - tbl_setting storage
