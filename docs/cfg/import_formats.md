# cfg/import_formats.yaml

Purpose: define CSV-to-field mappings for transaction imports with support for **versioned formats**. Used by `AccountDataImporter` and the `/api/transactions/import-formats` endpoint to validate headers, parse values, and map bank/platform exports into FiniA's transaction schema.

## Overview

FiniA supports **versioned import formats**. Each format (e.g., `csv-cb`, `csv-mintos`) can contain multiple versions that are automatically detected based on CSV headers.

### Benefits

- **Stable Account Assignments**: Format name stays the same (e.g., `csv-cb`), only internal versions change
- **Automatic Detection**: System recognizes version based on columns in CSV header
- **Flexible Headers**: Column order doesn't matter, only presence
- **Transparent Logging**: Import displays detected version
- **Backward Compatibility**: Legacy formats without versions are still supported

## Structure

### Nested Versions

```yaml
formats:
  csv-cb:                    # Format name (for account assignment)
    default: v1              # Optional: Default version as fallback
    v1:                      # Version key (any string)
      encoding: utf-8
      delimiter: ';'
      decimal: ','
      date_format: '%d.%m.%Y'
      header_skip: 0         # Number of lines to skip before header
      header:                # Expected columns (for version detection)
        - Valuta
        - Betrag
        - Verwendungszweck
        - "IBAN"
        - "BIC"
        - 'Sender / Empfänger'
      columns:
        dateValue:
          name: Valuta       # Single column
        amount:
          name: Betrag
        description:
          join:              # Merge multiple columns
            - Verwendungszweck
          separator: ' | '
        iban:
          name: "IBAN"
        bic:
          name: "BIC"
        recipientApplicant:
          name: 'Sender / Empfänger'
    
    v2:                      # Second version with different header
      encoding: utf-8
      delimiter: ';'
      decimal: ','
      date_format: '%d.%m.%Y'
      header_skip: 0
      header:
        - Valuta
        - Betrag
        - Verwendungszweck
        - "IBAN / Konto-Nr."  # Different column name!
        - "BIC / BLZ"
        - 'Sender / Empfänger'
      columns:
        dateValue:
          name: Valuta
        amount:
          name: Betrag
        description:
          join:
            - Verwendungszweck
          separator: ' | '
        iban:
          name: "IBAN / Konto-Nr."  # Adjusted
        bic:
          name: "BIC / BLZ"          # Adjusted
        recipientApplicant:
          name: 'Sender / Empfänger'
```

### Version Naming

Flexible string names allowed:

- **Version numbers**: `v1`, `v2`, `v3`
- **Semantic names**: `de`, `en`, `legacy`, `current`
- **Combinations**: `v1-de`, `v1-en`, `v2-de`

**Recommendation**: Use consistent naming within a format.

## New Syntax for Column Mapping

### Single Column (recommended)

```yaml
columns:
  dateValue:
    name: Datum    # Einzelne Spalte
```

### Join Columns

```yaml
columns:
  description:
    join:
      - Details
      - 'Transaction ID:'
    separator: ' | '
```

### Regex Extraction mit Sources

```yaml
columns:
  iban:
    sources:              # Liste von Quellen
      - name: Details     # Spaltenname
        regex: 'ISIN:\s*([A-Z0-9]{10,20})'
      - name: Details
        regex: 'Loan\s*([0-9\-]+)'
```

### Legacy Syntax (still supported)

```yaml
columns:
  dateValue:
    names: [Valuta, Datum]  # List of alternative names
  iban:
    regex: 'ISIN:\s*([A-Z0-9]{10,20})'
    source: Details
```

### Target fields

- `dateValue`: booking/value date (required for validation)
- `amount`: transaction amount (required)
- `description`: human-readable text; often joined from multiple description columns
- `iban`, `bic`: counterparty IBAN/BIC; may be null or regex-extracted
- `recipientApplicant`: counterparty name
- `account`: used in `csv-loan` to specify the loan account reference

## Automatic Version Detection

### How It Works

1. Format is specified (e.g., `csv-cb`)
2. System reads CSV header
3. Compares header with all versions of the format
4. Selects version whose `header` columns are **all** present in CSV
5. If multiple matches: Version with most matching columns wins

### Flexible Matching

- **Order**: Doesn't matter
- **Extra Columns**: Allowed
- **Missing Columns**: Leads to no match for this version

### Fallback Mechanism

1. **Header Match**: Best matching version
2. **Default Version**: If defined in format
3. **First Version**: First available version as last fallback
4. **Error**: If no version found

## Example: Mintos Format

```yaml
formats:
  csv-mintos:
    default: v2              # Newer version as default
    
    v1:                      # German version (older)
      encoding: utf-8
      delimiter: ','
      decimal: '.'
      date_format: '%Y-%m-%d %H:%M:%S'
      header_skip: 0
      header:
        - Datum
        - 'Transaktions-Nr.:'
        - Einzelheiten
        - Umsatz
        - Saldo
        - Währung
        - Zahlungsart
      columns:
        dateValue:
          name: Datum
        amount:
          name: Umsatz
        description:
          join:
            - Einzelheiten
            - 'Transaktions-Nr.:'
          separator: ' | '
        iban:
          sources:
            - name: Einzelheiten
              regex: 'ISIN:\s*([A-Z0-9]{10,20})'
            - name: Einzelheiten
              regex: 'Darlehen\s*([0-9\-]+)'
        bic: null
        recipientApplicant: null
    
    v2:                      # English version (newer)
      encoding: utf-8
      delimiter: ','
      decimal: '.'
      date_format: '%Y-%m-%d %H:%M:%S'
      header_skip: 0
      header:
        - Date
        - 'Transaction ID:'
        - Details
        - Turnover
        - Balance
        - Currency
        - 'Payment Type'
      columns:
        dateValue:
          name: Date
        amount:
          name: Turnover
        description:
          join:
            - Details
            - 'Transaction ID:'
          separator: ' | '
        iban:
          sources:
            - name: Details
              regex: 'ISIN:\s*([A-Z0-9]{10,20})\s*\(Loan\s*([0-9\-]+)\)'
        bic: null
        recipientApplicant: null
```

## Import Output

```
================================================================================
FiniA Account CSV Import
================================================================================

ℹ️  Format 'csv-mintos' - Detected version: v1 for DokMappe-Mintos_Umsaetze_2018.csv
✓ CSV-Spalten validiert: DokMappe-Mintos_Umsaetze_2018.csv
Imported 5/5 rows from DokMappe-Mintos_Umsaetze_2018.csv for account 'Mintos'

ℹ️  Format 'csv-mintos' - Detected version: v2 for DokMappe-Mintos_Umsaetze_202409.csv
✓ CSV-Spalten validiert: DokMappe-Mintos_Umsaetze_202409.csv
Imported 2/2 rows from DokMappe-Mintos_Umsaetze_202409.csv for account 'Mintos'

================================================================================
Finished CSV import. Inserted 7 of 7 rows
================================================================================
```

## Migration from Old Formats

### Old (without versions)

```yaml
formats:
  csv-cb:
    encoding: utf-8
    delimiter: ';'
    columns:
      dateValue:
        names:              # List of possible names
          - Valuta
      iban:
        names:
          - "IBAN"
          - "IBAN / Konto-Nr."
```

### New (with versions)

```yaml
formats:
  csv-cb:
    default: v1
    v1:
      encoding: utf-8
      delimiter: ';'
      header:
        - Valuta
        - "IBAN"
      columns:
        dateValue:
          name: Valuta      # Single name
        iban:
          name: "IBAN"
    
    v2:                     # Separate version for different header
      encoding: utf-8
      delimiter: ';'
      header:
        - Valuta
        - "IBAN / Konto-Nr."
      columns:
        dateValue:
          name: Valuta
        iban:
          name: "IBAN / Konto-Nr."
```

## Adding a New Format

1. Choose a unique format key under `formats`
2. Create first version (e.g., `v1`) with:
   - `encoding`, `delimiter`, `decimal`, `date_format` matching the CSV export
   - `header`: List of expected column names
   - `columns`: Mapping for all required fields
3. Add additional versions as needed (e.g., `v2` for changed headers)
4. Set `default` to preferred version
5. Test with `POST /api/transactions/import-csv` after login (see [docs/api.md](../api.md)).

## Validation Behavior

- Header check: Version must find all columns defined in `header` in the CSV
- Extraction strategies are applied in this order: `join` > `sources` (regex) > `name` > legacy (`names`, `regex`+`source`)
- Regex matches are concatenated with ` | `; empty matches yield empty strings
- Missing required fields abort import with clear error message

## Database Storage

Formats are stored in `tbl_setting` with `key = 'import_format'`:

```json
{
  "name": "csv-mintos",
  "config": {
    "default": "v2",
    "v1": {
      "encoding": "utf-8",
      "delimiter": ",",
      "header": ["Datum", "Transaktions-Nr.:", "Einzelheiten", ...],
      "columns": {...}
    },
    "v2": {
      "encoding": "utf-8",
      "delimiter": ",",
      "header": ["Date", "Transaction ID:", "Details", ...],
      "columns": {...}
    }
  }
}
```

## Web-UI Usage

1. **Upload YAML**: Upload `import_formats.yaml` via Settings
2. **Select Format**: Choose only format name during import (e.g., `csv-mintos`)
3. **Automatic**: System detects version automatically during import
4. **Logging**: Import log shows detected version

## Error Handling

### No Version Found

```
❌ ERROR loading format for DokMappe-Mintos_Unknown.csv: 
No valid version found for format 'csv-mintos'. Available versions: ['v1', 'v2']
```

**Cause**: CSV header doesn't match any version

**Solution**: 
- Add new version with matching header
- Or adjust CSV header

### Missing Columns

```
❌ ERROR - File: transactions.csv
   Required columns not found:
   - dateValue: Expected column 'Datum'
   - amount: Expected column 'Betrag'
   
   Available columns in CSV file (5):
   - Date
   - Amount
   - Description
   - IBAN
   - BIC
   
   Import for this file will be aborted!
```

## Notes

- Keep filenames in `docs/` lowercase (except top-level README)
- When adding formats for new banks, prefer versioned structure with explicit `header` definitions
- Use `name` for single columns, `sources` for regex extraction, `join` for combining multiple columns
- Test imports thoroughly with real CSV files from the bank/platform

## See Also

- [CSV Import](../import/csv_import.md) - Import system documentation
- [Getting Started](../tutorials/getting_started.md) - Getting started guide
