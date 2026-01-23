# cfg/import_formats.yaml

Purpose: define CSV-to-field mappings for transaction imports. Used by `AccountDataImporter` (CLI) and the `/api/transactions/import-formats` endpoint to validate headers, parse values, and map bank/platform exports into FiniA's transaction schema.

## Structure
- Root key: `formats`
- Each format (e.g., `csv-cb`, `csv-spk`, `csv-mintos`, `csv-loan`) contains:
  - `encoding`: file encoding (e.g., `utf-8`, `latin-1`)
  - `delimiter`: CSV delimiter (e.g., `;`, `,`)
  - `decimal`: decimal separator used in amounts (e.g., `,` or `.`)
  - `date_format`: `datetime.strptime` format string for `dateValue`
  - `columns`: mapping of target fields -> extraction rules

### Column mapping syntax
- `null`: field is optional/unused for this format.
- `names`: list of alternative header names; first present header is used.
- `join`: concatenate multiple columns; `separator` defines the glue string.
- `regex`: extract via regex from a source column (`source`); all matches are joined with ` | `.
- Plain string (legacy): direct column name.

### Target fields typically used
- `dateValue`: booking/value date (required for validation)
- `amount`: transaction amount (required)
- `description`: human-readable text; often joined from multiple description columns
- `iban`, `bic`: counterparty IBAN/BIC; may be null or regex-extracted
- `recipientApplicant`: counterparty name
- `account`: used in `csv-loan` to specify the loan account reference

## Examples
### csv-cb
```yaml
csv-cb:
  encoding: utf-8
  delimiter: ';'
  decimal: ','
  date_format: '%d.%m.%Y'
  columns:
    dateValue:
      names: [Valuta]
    amount:
      names: [Betrag]
    description:
      join: [Verwendungszweck]
      separator: ' | '
    iban:
      names: ['IBAN', 'IBAN / Konto-Nr.']
    bic:
      names: ['BIC', 'BIC / BLZ']
    recipientApplicant:
      names: ['Sender / Empfänger']
```

### csv-mintos (regex extraction example)
```yaml
csv-mintos:
  encoding: utf-8
  delimiter: ','
  decimal: '.'
  date_format: '%Y-%m-%d %H:%M:%S'
  columns:
    dateValue:
      names: [Datum]
    amount:
      names: [Umsatz]
    description:
      join: [Details, 'Transaktions-Nr.:']
      separator: ' | '
    iban:
      regex: 'ISIN:\s*([A-Z0-9]{10,20})|Darlehen\s*([0-9\-]+)'
      source: Details
    bic: null
    recipientApplicant: null
```

### Adding a new format
1. Choose a unique format key under `formats`.
2. Set `encoding`, `delimiter`, `decimal`, `date_format` to match the CSV export.
3. Define `columns` for all required fields (`dateValue`, `amount`, `description`); optional fields can be `null`.
4. Ensure headers in `names` (or `join`/`source`) exactly match the CSV header strings.
5. Test with the importer: `python src/main.py --import-account-data --user <db_user> --password <db_pass> --config cfg/config.yaml`.

## Validation behavior
- Header check: required fields (non-null mappings) must exist in the CSV header; import aborts otherwise.
- Extraction strategies are applied in this order: `join` > `regex` > `names` > direct string mapping.
- Regex matches are concatenated; empty matches yield empty strings.

## Notes
- Keep filenames in `docs/` lowercase (except top-level README).
- When adding formats for new banks, prefer `names` lists for header variants and `join` to keep descriptions readable.
