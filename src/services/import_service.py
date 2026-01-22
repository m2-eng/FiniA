from typing import List, Optional, Any
from services.import_steps.base import ImportStep
from infrastructure.unit_of_work import UnitOfWork
import csv
from pathlib import Path
from decimal import Decimal
from datetime import datetime
import re


class ImportService:
   def __init__(self, connection, steps: List[ImportStep]):
      self.connection = connection
      self.steps = steps

   def run(self, data: dict) -> bool:
      success = True
      for step in self.steps:
         print(f"Running step: {step.name()}")
         with UnitOfWork(self.connection) as uow:
            ok = step.run(data, uow)
            success = success and ok
      return success


def import_csv_with_optional_account(
    db,
    csv_path: Path,
    format_name: str,
    mapping: dict,
    default_account_id: Optional[int],
    cursor
) -> dict:
    """
    Import CSV file with support for optional account column.
    
    If the CSV has an account column, use it to determine the account for each row.
    Otherwise, use the default_account_id for all rows.
    
    Args:
        db: Database instance
        csv_path: Path to CSV file
        format_name: Format name (e.g., 'csv-loan')
        mapping: Format mapping configuration
        default_account_id: Default account ID if not specified in CSV
        cursor: Database cursor for categorization
    
    Returns:
        Dict with import results
    """
    from repositories.transaction_repository import TransactionRepository
    from repositories.accounting_entry_repository import AccountingEntryRepository
    from repositories.account_repository import AccountRepository
    
    delimiter = mapping.get("delimiter", ";")
    encoding = mapping.get("encoding", "utf-8")
    decimal_sep = mapping.get("decimal", ".")
    date_format = mapping.get("date_format")
    columns = mapping.get("columns", {})
    
    has_account_column = columns.get("account") is not None
    
    inserted = 0
    total = 0
    warnings = []
    account_cache = {}  # Cache account lookups by name
    
    # Detect encoding
    encodings_to_try = [encoding]
    if encoding.lower() == "utf-8":
        encodings_to_try.extend(["latin-1", "iso-8859-1", "cp1252"])
    
    detected_encoding = None
    last_error = None
    
    for enc in encodings_to_try:
        try:
            with open(csv_path, "r", encoding=enc, newline="") as test_handle:
                test_handle.read(4096)
            detected_encoding = enc
            break
        except (UnicodeDecodeError, Exception) as e:
            last_error = e
            continue
    
    if detected_encoding is None:
        raise RuntimeError(f"Could not detect encoding for {csv_path.name}. Tried: {encodings_to_try}")
    
    # Read CSV and import
    with open(csv_path, "r", encoding=detected_encoding, newline="") as handle:
        reader = csv.DictReader(handle, delimiter=delimiter)
        
        if reader.fieldnames is None:
            raise ValueError("CSV file has no header row or is empty")
        # Normalize header names by stripping whitespace to avoid mismatches like 'Betrag '
        reader.fieldnames = [fn.strip() if isinstance(fn, str) else fn for fn in reader.fieldnames]
        
        for row in reader:
            total += 1
            try:
                # Determine account ID for this row
                row_account_id = default_account_id
                
                if has_account_column:
                    # Get account name from CSV
                    account_name_raw = _get_field_value(row, columns.get("account"))
                    if account_name_raw:
                        account_name = account_name_raw.strip()
                        
                        # Look up account by name
                        if account_name not in account_cache:
                            # Query account by name using SQL directly
                            cursor_lookup = db.connection.cursor()
                            try:
                                cursor_lookup.execute(
                                    "SELECT id FROM tbl_account WHERE name = %s",
                                    (account_name,)
                                )
                                result = cursor_lookup.fetchone()
                                
                                if result:
                                    account_cache[account_name] = result[0]
                                else:
                                    # Account not found - use default if available, otherwise skip
                                    if default_account_id:
                                        account_cache[account_name] = default_account_id
                                        warnings.append(f"Account '{account_name}' not found, using default account")
                                    else:
                                        warnings.append(f"Account '{account_name}' not found, skipping row {total}")
                                        continue
                            finally:
                                cursor_lookup.close()
                        
                        row_account_id = account_cache.get(account_name)
                
                if not row_account_id:
                    warnings.append(f"No account specified for row {total}, skipping")
                    continue
                
                # Extract transaction fields
                date_value_raw = _get_field_value(row, columns.get("dateValue"))
                amount_raw = _get_field_value(row, columns.get("amount"))
                description = _get_field_value(row, columns.get("description"))
                iban = _get_field_value(row, columns.get("iban"))
                bic = _get_field_value(row, columns.get("bic"))
                recipient = _get_field_value(row, columns.get("recipientApplicant"))
                
                # Parse values
                date_value = _parse_date(date_value_raw, date_format)
                amount = _parse_amount(amount_raw, decimal_sep)
                
                # Insert transaction
                with UnitOfWork(db.connection) as uow:
                    tx_repo = TransactionRepository(uow)
                    ae_repo = AccountingEntryRepository(uow)
                    
                    transaction_id = tx_repo.insert_ignore(
                        account_id=row_account_id,
                        description=description,
                        amount=amount,
                        date_value=date_value,
                        iban=iban or None,
                        bic=bic or None,
                        recipient_applicant=recipient or None,
                    )
                    
                    if isinstance(transaction_id, int) and transaction_id > 0:
                        # Create accounting entry
                        ae_repo.insert(
                            amount=amount,
                            transaction_id=transaction_id,
                            checked=False,
                            accounting_planned_id=None,
                            category_id=None,
                        )
                        inserted += 1
            
            except Exception as exc:
                error_msg = str(exc).lower()
                if "duplicate" not in error_msg and "unique" not in error_msg:
                    warnings.append(f"Row {total}: {str(exc)}")
    
    # Apply auto-categorization
    categorization_result = {"categorized": 0, "total_checked": 0}
    if inserted > 0:
        try:
            from api.routers.transactions import auto_categorize_entries
            categorization_result = auto_categorize_entries(cursor, db.connection)
        except Exception as cat_error:
            warnings.append(f"Auto-categorization failed: {str(cat_error)}")
    
    result = {
        "success": True,
        "message": f"Import abgeschlossen: {inserted} von {total} Transaktionen importiert",
        "inserted": inserted,
        "total": total,
        "format": format_name,
        "filename": csv_path.name,
        "auto_categorized": categorization_result.get("categorized", 0),
        "auto_categorized_total": categorization_result.get("total_checked", 0)
    }
    
    if warnings:
        result["warnings"] = warnings
    
    return result


def _get_field_value(row: dict[str, Any], mapping: Any) -> str:
    """Extract field value from row using mapping configuration."""
    if mapping is None:
        return ""
    
    if isinstance(mapping, str):
        return (row.get(mapping, "") or "").strip()
    
    if isinstance(mapping, dict):
        if "join" in mapping:
            # Join multiple columns
            separator = mapping.get("separator", " ")
            parts = [
                (row.get(item, "") or "").strip()
                for item in mapping.get("join", [])
                if (row.get(item, "") or "").strip()
            ]
            return separator.join(parts)
        
        if "regex" in mapping:
            # Regex extraction
            import re
            pattern = mapping.get("regex")
            target = mapping.get("source")
            value = row.get(target, "") or ""
            matches = re.findall(pattern, value)
            if not matches:
                return ""
            
            def _flatten(m):
                if isinstance(m, tuple):
                    return "".join(m)
                return m
            
            extracted = [_flatten(m) for m in matches if _flatten(m)]
            return " | ".join(extracted)
        
        if "names" in mapping:
            # Try alternative column names
            names = mapping.get("names", [])
            for name in names:
                if name in row and (row.get(name) or "").strip():
                    return (row.get(name, "") or "").strip()
            return ""
    
    return ""


def _parse_amount(raw: str, decimal_sep: str) -> Decimal:
    """Parse amount string to Decimal.
    Handles various whitespace (including NBSP) and thousands separators.
    """
    if raw is None:
        raw = ""
    # Remove all whitespace characters including non-breaking space and narrow no-break space
    normalized = re.sub(r"[\s\u00A0\u202F]", "", str(raw))
    if decimal_sep == ",":
        # Remove thousands dots and convert comma to dot
        normalized = normalized.replace(".", "").replace(",", ".")
    return Decimal(normalized)


def _parse_date(raw: str, date_format: str) -> datetime:
    """Parse date string to datetime."""
    return datetime.strptime(raw, date_format)
