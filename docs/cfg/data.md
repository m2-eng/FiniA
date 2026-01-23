# cfg/data.yaml

Purpose: seed static lookup data and example account/category structures for local imports. The file is consumed by `src/DataImporter.py` (steps: account types, planning cycles, categories, accounts).

## Syntax overview
- Top-level keys are optional; when present they are imported in this order: `accountType`, `planningCycle`, `categories`, `account_data`.
- YAML 1.1 is used; strings are quoted where they contain spaces or special characters.

### accountType
- Map of account type name -> numeric ID.
- These IDs match the primary keys of `tbl_accountType`.
- Values are now also seeded in `db/finia_draft.sql`; YAML is still supported for re-imports.

Example:
```yaml
accountType:
  'Girokonto': 1
  'Wertpapierdepot': 2
```

### planningCycle
- Map of cycle name -> either a numeric ID or an object with `id`, `periodValue`, `periodUnit` (`d`=day, `m`=month, `y`=year).
- Defaults (used when only an ID is provided) match the SQL seed: einmalig 0d, täglich 1d, wöchentlich 7d, 14-tägig 14d, monatlich 1m, vierteljährlich 3m, halbjährlich 6m, jährlich 1y.
- YAML now updates `periodValue/periodUnit` via upsert.

Examples:
```yaml
# Simple (use defaults)
planningCycle:
  'einmalig': 1
  'täglich': 2

# Explicit intervals
planningCycle:
  'monatlich':
    id: 5
    periodValue: 1.0
    periodUnit: m
  '14-tägig':
    id: 4
    periodValue: 14.0
    periodUnit: d
```

### categories
- Hierarchical category tree. Each `name` can contain nested `subcategories`.
- Imported into `tbl_category` with parent-child relations.

Example:
```yaml
categories:
  - name: 'Auto'
    subcategories:
      - name: 'Treibstoff'
      - name: 'Versicherung (Auto)'
```

### account_data
- List of account definitions with metadata and import configuration.
- Important fields:
  - `name`, `iban_accountNumber`, `bic_market`, `type` (must match `accountType` name)
  - `startAmount`, `dateStart`, optional `dateEnd`
  - `clearingAccount` for linked accounts (e.g., depot -> clearing account name)
  - `importFolder`, `importFileEnding`, `importType` (must match an entry in `cfg/import_formats.yaml`)
- Used by `AccountDataImporter` to set up import paths and ingest CSVs.

Example:
```yaml
account_data:
  - account:
      name: 'Consorsbank - Girokonto'
      iban_accountNumber: 'DE89370400440532013000'
      type: 'Girokonto'
      importFolder: ./test/data/CB
      importFileEnding: csv
      importType: csv-cb
```

## Notes
- Static defaults for account types and planning cycles are embedded in `db/finia_draft.sql` to keep IDs stable; YAML re-imports are still allowed and will skip existing rows.
- Keep filenames in `docs/` lowercase (except the top-level README).