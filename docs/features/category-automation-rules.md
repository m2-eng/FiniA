---
title: Category Automation Rules - Data Model
version: 2.0
feature: category-automation
type: technical-specification
status: planned
date: 2026-01-22
---

# Category Automation Rules - Data Model

## Overview

Category automation rules allow automatic categorization of transactions based on configurable conditions. Version 2.0 introduces enhanced flexibility with:

- **Multiple conditions per rule** (for handling typos, variations)
- **Reusable rules across multiple accounts**
- **Flexible condition logic** with AND/OR combinations
- **Rule descriptions** for better maintainability
- **Storage in settings table** (JSON-based)

## Migration Path

### Current State (v1.0)
- Dedicated table: `tbl_categoryAutomation`
- One rule = one condition
- One rule = one account
- No rule description

### Target State (v2.0)
- Settings table: `tbl_setting` with key `category_automation_rule`
- One rule = multiple conditions (OR-linked by default)
- One rule = multiple accounts
- Rule description and metadata

## Data Model

### JSON Schema

```json
{
  "id": "string (unique identifier, UUID recommended)",
  "name": "string (rule description, user-defined)",
  "description": "string (optional, detailed explanation)",
  "conditions": [
    {
      "id": "integer (1, 2, 3... for reference in conditionLogic)",
      "type": "string (contains|equals|startsWith|endsWith|regex|amountRange)",
      "columnName": "string (description|recipientApplicant|amount|iban)",
      "value": "string (search value, null for amountRange)",
      "caseSensitive": "boolean (default: false)",
      "minAmount": "number (null if not amountRange)",
      "maxAmount": "number (null if not amountRange)"
    }
  ],
  "conditionLogic": "string (optional, defines how conditions are combined)",
  "category": "integer (category ID)",
  "accounts": "array[integer] (account IDs, empty = all accounts)",
  "priority": "integer (1-10, higher = more priority)",
  "enabled": "boolean (default: true)",
  "dateCreated": "string (ISO timestamp)",
  "dateModified": "string (ISO timestamp)"
}
```

### Field Descriptions

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | Yes | Unique identifier (UUID recommended) |
| `name` | string | Yes | Short, descriptive name (e.g., "Rent Apartment") |
| `description` | string | No | Detailed explanation of rule purpose |
| `conditions` | array | Yes | List of conditions (min. 1) |
| `conditions[].id` | integer | Yes | Numeric ID for referencing in logic (1, 2, 3...) |
| `conditions[].type` | string | Yes | Type of condition (see Condition Types) |
| `conditions[].columnName` | string | Yes | Transaction field to check |
| `conditions[].value` | string | Conditional | Search/match value (required except amountRange) |
| `conditions[].caseSensitive` | boolean | No | Case-sensitive matching (default: false) |
| `conditions[].minAmount` | number | Conditional | Minimum amount (only for amountRange) |
| `conditions[].maxAmount` | number | Conditional | Maximum amount (only for amountRange) |
| `conditionLogic` | string | No | Logic expression (default: all OR-linked) |
| `category` | integer | Yes | Target category ID |
| `accounts` | array[int] | No | Account IDs (empty = applies to all) |
| `priority` | integer | No | Priority 1-10 (default: 5) |
| `enabled` | boolean | No | Rule active status (default: true) |
| `dateCreated` | string | Yes | ISO timestamp of creation |
| `dateModified` | string | Yes | ISO timestamp of last modification |

## Condition Types

### Text Matching

| Type | Description | Example |
|------|-------------|---------|
| `contains` | Field contains value | "REWE" matches "Einkauf REWE Berlin" |
| `equals` | Exact match | "MIETE" matches only "MIETE" |
| `startsWith` | Field starts with value | "Amazon" matches "Amazon.de Order" |
| `endsWith` | Field ends with value | "GmbH" matches "Example GmbH" |
| `regex` | Regular expression | `^[A-Z]{2}\d{2}` matches "AB12..." |

### Amount Matching

| Type | Description | Example |
|------|-------------|---------|
| `amountRange` | Amount within range | min: -1000, max: -800 for rent |

## Condition Logic

### Default Behavior
If `conditionLogic` is `null` or empty, all conditions are OR-linked:
```
Condition 1 OR Condition 2 OR Condition 3
```

### Custom Logic Expressions

The `conditionLogic` field allows flexible combination using:
- **Operators:** `AND`, `OR`, `UND`, `ODER` (German/English)
- **Grouping:** Parentheses `( )` for precedence
- **References:** Condition IDs (1, 2, 3...)

#### Syntax Examples

```
Simple OR:          "1 OR 2"
Simple AND:         "1 AND 2"
Combined:           "(1 OR 2) AND 3"
Complex:            "(1 OR 2 OR 3) AND (4 OR 5)"
German:             "(1 ODER 2) UND 3"
```

#### Evaluation Rules

1. Reference condition IDs with their evaluation result (true/false)
2. Evaluate parentheses first (inner to outer)
3. Apply boolean operators (AND, OR)
4. Return final boolean result

#### Parser Implementation

**Python:**
```python
def parse_condition_logic(logic_str, condition_results):
    """
    Args:
        logic_str: "(1 OR 3) AND 2"
        condition_results: {1: True, 2: False, 3: True}
    Returns:
        bool: Evaluation result
    """
    normalized = logic_str.upper()
    normalized = normalized.replace(' UND ', ' AND ')
    normalized = normalized.replace(' ODER ', ' OR ')
    
    for cond_id, result in condition_results.items():
        normalized = re.sub(rf'\b{cond_id}\b', str(result), normalized)
    
    return eval(normalized.lower())
```

**JavaScript:**
```javascript
function parseConditionLogic(logicStr, conditionResults) {
    let normalized = logicStr.toUpperCase()
        .replace(/\bUND\b/g, 'AND')
        .replace(/\bODER\b/g, 'OR');
    
    for (let [id, result] of Object.entries(conditionResults)) {
        normalized = normalized.replace(
            new RegExp(`\\b${id}\\b`, 'g'), 
            result.toString()
        );
    }
    
    normalized = normalized
        .replace(/\bAND\b/g, '&&')
        .replace(/\bOR\b/g, '||');
    
    return eval(normalized.toLowerCase());
}
```

## Examples

### Example 1: Simple Text Match with Typo Handling

**Scenario:** Match "MIETE" with common typos

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440001",
  "name": "Rent with typo variations",
  "description": "Matches rent transactions including common typos",
  "conditions": [
    {
      "id": 1,
      "type": "contains",
      "columnName": "description",
      "value": "MIETE",
      "caseSensitive": false
    },
    {
      "id": 2,
      "type": "contains",
      "columnName": "description",
      "value": "MITE",
      "caseSensitive": false
    },
    {
      "id": 3,
      "type": "contains",
      "columnName": "description",
      "value": "RENT",
      "caseSensitive": false
    }
  ],
  "conditionLogic": null,
  "category": 123,
  "accounts": [456],
  "priority": 5,
  "enabled": true,
  "dateCreated": "2026-01-22T10:00:00Z",
  "dateModified": "2026-01-22T10:00:00Z"
}
```

**Matches:**
- ✅ "Zahlung MIETE Wohnung"
- ✅ "Überweisung MITE Januar" (typo)
- ✅ "Monthly RENT payment"
- ❌ "Supermarkt REWE"

### Example 2: Amount Range with Text Match

**Scenario:** Salary between €2000-5000 with description variations

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440002",
  "name": "Salary with amount check",
  "description": "Matches salary with typical amount range",
  "conditions": [
    {
      "id": 1,
      "type": "contains",
      "columnName": "description",
      "value": "GEHALT",
      "caseSensitive": false
    },
    {
      "id": 2,
      "type": "contains",
      "columnName": "description",
      "value": "SALARY",
      "caseSensitive": false
    },
    {
      "id": 3,
      "type": "contains",
      "columnName": "description",
      "value": "LOHN",
      "caseSensitive": false
    },
    {
      "id": 4,
      "type": "amountRange",
      "columnName": "amount",
      "minAmount": 2000.0,
      "maxAmount": 5000.0
    }
  ],
  "conditionLogic": "(1 OR 2 OR 3) AND 4",
  "category": 234,
  "accounts": [],
  "priority": 8,
  "enabled": true,
  "dateCreated": "2026-01-22T10:15:00Z",
  "dateModified": "2026-01-22T10:15:00Z"
}
```

**Matches:**
- ✅ "GEHALT Januar", amount: €3000
- ✅ "SALARY PAYMENT", amount: €2500
- ❌ "GEHALT Bonus", amount: €6000 (too high)
- ❌ "Supermarkt", amount: €3000 (description doesn't match)

### Example 3: Complex Nested Logic

**Scenario:** Grocery stores with amount filtering

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440003",
  "name": "Groceries excluding small purchases",
  "description": "Matches grocery stores but filters out very small amounts",
  "conditions": [
    {
      "id": 1,
      "type": "contains",
      "columnName": "description",
      "value": "REWE"
    },
    {
      "id": 2,
      "type": "contains",
      "columnName": "description",
      "value": "EDEKA"
    },
    {
      "id": 3,
      "type": "contains",
      "columnName": "description",
      "value": "ALDI"
    },
    {
      "id": 4,
      "type": "amountRange",
      "columnName": "amount",
      "minAmount": -200.0,
      "maxAmount": -50.0
    },
    {
      "id": 5,
      "type": "amountRange",
      "columnName": "amount",
      "minAmount": -50.0,
      "maxAmount": -20.0
    }
  ],
  "conditionLogic": "(1 OR 2 OR 3) AND (4 OR 5)",
  "category": 345,
  "accounts": [456, 789],
  "priority": 6,
  "enabled": true,
  "dateCreated": "2026-01-22T10:30:00Z",
  "dateModified": "2026-01-22T10:30:00Z"
}
```

**Matches:**
- ✅ "REWE Einkauf", amount: €-75.50
- ✅ "ALDI SÜD", amount: €-120.00
- ❌ "EDEKA", amount: €-15.00 (too small)
- ❌ "REWE", amount: €-250.00 (too large)

### Example 4: Multi-Account Rule

**Scenario:** Reusable rule for multiple accounts

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440004",
  "name": "ATM withdrawals (all accounts)",
  "description": "Matches ATM cash withdrawals across all checking accounts",
  "conditions": [
    {
      "id": 1,
      "type": "contains",
      "columnName": "description",
      "value": "GELDAUTOMAT"
    },
    {
      "id": 2,
      "type": "contains",
      "columnName": "description",
      "value": "ATM"
    },
    {
      "id": 3,
      "type": "contains",
      "columnName": "description",
      "value": "BARGELD"
    }
  ],
  "conditionLogic": "1 OR 2 OR 3",
  "category": 456,
  "accounts": [101, 102, 103],
  "priority": 7,
  "enabled": true,
  "dateCreated": "2026-01-22T10:45:00Z",
  "dateModified": "2026-01-22T10:45:00Z"
}
```

## Migration from v1.0 to

### Step 1: Read Old Rules

```sql
SELECT 
  id,
  columnName,
  rule,
  category,
  account,
  dateImport
FROM tbl_categoryAutomation
ORDER BY id;
```

### Step 2: Convert to New Format

**Old format (v1.0):**
```json
{
  "columnName": "description",
  "rule": {"type": "contains", "value": "MIETE"},
  "category": 123,
  "account": 456
}
```

**New format (v2.0):**
```json
{
  "id": "uuid-from-old-id-123",
  "name": "Migrated: description contains MIETE",
  "description": "Auto-migrated from tbl_categoryAutomation",
  "conditions": [
    {
      "id": 1,
      "type": "contains",
      "columnName": "description",
      "value": "MIETE",
      "caseSensitive": false
    }
  ],
  "conditionLogic": null,
  "category": 123,
  "accounts": [456],
  "priority": 5,
  "enabled": true,
  "dateCreated": "2024-01-01T00:00:00Z",
  "dateModified": "2026-01-22T12:00:00Z"
}
```

### Step 3: Insert into Settings

```sql
INSERT INTO tbl_setting (user_id, `key`, `value`)
VALUES (NULL, 'category_automation_rule', '[json_string]');
```

### Step 4: Verification

1. Count rules: Old table vs. new settings
2. Test categorization with both systems
3. Compare results
4. If identical → drop old table

### Step 5: Cleanup (after verification)

```sql
-- Backup first!
CREATE TABLE tbl_categoryAutomation_backup AS 
SELECT * FROM tbl_categoryAutomation;

-- Then drop
DROP TABLE tbl_categoryAutomation;
```

## Rule Matching Algorithm

### Execution Flow

1. **Load all enabled rules** from settings (key: `category_automation_rule`)
2. **Filter by account:** Rules with matching account ID or empty accounts array
3. **Sort by priority:** Higher priority first
4. **For each rule:**
   - Evaluate all conditions against transaction
   - Apply condition logic
   - If match → assign category and stop (unless priority continues)
5. **Return:** Category ID or null

### Priority Handling

- Rules are evaluated in descending priority order (10 → 1)
- First matching rule wins
- Same priority → order by dateCreated (newer first)

### Performance Optimization

- Cache parsed rules in memory
- Index settings by key for fast lookup
- Pre-compile regex patterns
- Batch-process transactions

## Storage in Settings Table

### Key Structure

```
Key: "category_automation_rule"
Value: [JSON object of rule]
```

### Querying Rules

```sql
-- Get all rules
SELECT id, value
FROM tbl_setting
WHERE `key` = 'category_automation_rule'
ORDER BY JSON_EXTRACT(value, '$.priority') DESC;

-- Get rules for specific account
SELECT id, value
FROM tbl_setting
WHERE `key` = 'category_automation_rule'
  AND (
    JSON_CONTAINS(JSON_EXTRACT(value, '$.accounts'), '456')
    OR JSON_LENGTH(JSON_EXTRACT(value, '$.accounts')) = 0
  );
```

### Indexing

For performance, consider adding JSON functional index:

```sql
CREATE INDEX idx_category_rules_priority 
ON tbl_setting ((CAST(JSON_EXTRACT(`value`, '$.priority') AS UNSIGNED)))
WHERE `key` = 'category_automation_rule';
```

## Future Enhancements

### NOT Operator
```json
{
  "conditionLogic": "(1 OR 2) AND NOT 3"
}
```

### Date-based Conditions
```json
{
  "type": "dateRange",
  "columnName": "dateValue",
  "startDate": "2026-01-01",
  "endDate": "2026-12-31"
}
```

### Machine Learning Suggestions
- Analyze uncategorized transactions
- Suggest new rules based on patterns
- Auto-tune condition logic

### Rule Templates
- Predefined rules for common scenarios
- Import/export rule sets
- Sharing between users

## Testing

### Unit Tests Required

1. **Condition evaluation:** Each condition type
2. **Logic parser:** Various logic expressions
3. **Edge cases:** Empty conditions, invalid logic
4. **Migration:** Old format → new format
5. **Performance:** Large rule sets (100+ rules)

### Test Cases

```python
def test_condition_logic_simple_or():
    results = {1: True, 2: False, 3: False}
    assert parse_condition_logic("1 OR 2", results) == True

def test_condition_logic_complex():
    results = {1: False, 2: True, 3: True, 4: False}
    assert parse_condition_logic("(1 OR 2) AND (3 OR 4)", results) == True

def test_german_operators():
    results = {1: True, 2: False}
    assert parse_condition_logic("1 ODER 2", results) == True
```

## API Endpoints (planned)

```
GET    /api/category-automation/rules              - List all rules
GET    /api/category-automation/rules/{id}         - Get specific rule
POST   /api/category-automation/rules              - Create new rule
PUT    /api/category-automation/rules/{id}         - Update rule
DELETE /api/category-automation/rules/{id}         - Delete rule
POST   /api/category-automation/rules/test         - Test rule against transaction
POST   /api/category-automation/migrate            - Migrate from v1.0 to
```

## References

- [Settings Repository](../../src/repositories/settings_repository.py)
- [Category Automation Router](../../src/api/routers/category_automation.py)
- [Category Automation Service](../../src/services/category_automation.py)

---

**Version History:**
- v2.0 (2026-01-22): New data model with multiple conditions, flexible logic
- v1.0 (legacy): Original implementation with dedicated table
