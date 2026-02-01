from typing import List, Optional, Any
from services.import_steps.base import ImportStep
from services.csv_utils import read_csv_rows, parse_amount, parse_date
from infrastructure.unit_of_work import UnitOfWork
from pathlib import Path
from decimal import Decimal
from datetime import datetime


class ImportService:
   def __init__(self, pool_manager, session_id: str, steps: List[ImportStep]):
      """
      Initialisiert den Import-Service mit Connection Pool Manager.
      
      Args:
         pool_manager: ConnectionPoolManager Instanz
         session_id: Session-ID für den Connection Pool
         steps: Liste von ImportStep Instanzen
      """
      self.pool_manager = pool_manager
      self.session_id = session_id
      self.steps = steps

   def run(self, data: dict) -> bool:
      """
      Führt alle Import-Schritte nacheinander aus.
      
      Args:
         data: Daten für den Import
         
      Returns:
         True wenn alle Schritte erfolgreich waren, False sonst
      """
      success = True
      for step in self.steps:
         print(f"Running step: {step.name()}")
         connection = self.pool_manager.get_connection(self.session_id)
         try:
            with UnitOfWork(connection) as uow:
               ok = step.run(data, uow)
               success = success and ok
         finally:
            # Verbindung wird automatisch zum Pool zurückgegeben
            pass
      return success


def import_csv_with_optional_account(
    pool_manager,
    session_id: str,
    csv_path: Path,
    format_name: str,
    mapping: dict,
    default_account_id: Optional[int],
) -> dict:
    """
    Import CSV file with support for optional account column.
    Nutzt Connection Pool Manager für Datenbankzugriff.
    
    If the CSV has an account column, use it to determine the account for each row.
    Otherwise, use the default_account_id for all rows.
    
    Args:
        pool_manager: ConnectionPoolManager Instanz
        session_id: Session-ID für den Connection Pool
        csv_path: Path to CSV file
        format_name: Format name (e.g., 'csv-loan')
        mapping: Format mapping configuration
        default_account_id: Default account ID if not specified in CSV
    
    Returns:
        Dict with import results
    """
    from repositories.transaction_repository import TransactionRepository
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
    
    # Read and process CSV using centralized utilities
    try:
        for row in read_csv_rows(csv_path, delimiter=delimiter, encoding=encoding):
            total += 1
            try:
                # Determine account ID for this row
                row_account_id = default_account_id
                
                if has_account_column:
                    # Get account name from CSV
                    account_name_raw = _get_field_value(row, columns.get("account"))
                    if account_name_raw:
                        account_name = account_name_raw.strip()
                        
                        # Look up account by name using Connection Pool
                        if account_name not in account_cache:
                            try:
                                connection = pool_manager.get_connection(session_id)
                                with UnitOfWork(connection) as uow:
                                    account_repo = AccountRepository(uow)
                                    account = account_repo.find_by_name(account_name)
                                    
                                    if account:
                                        account_cache[account_name] = account.id
                                    else:
                                        # Account not found - use default if available, otherwise skip
                                        if default_account_id:
                                            account_cache[account_name] = default_account_id
                                            warnings.append(f"Account '{account_name}' not found, using default account")
                                        else:
                                            warnings.append(f"Account '{account_name}' not found, skipping row {total}")
                                            continue
                            except Exception as lookup_error:
                                warnings.append(f"Error looking up account '{account_name}': {str(lookup_error)}")
                                continue
                        
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
                
                # Parse values using centralized utilities
                date_value = parse_date(date_value_raw, date_format)
                amount = parse_amount(amount_raw, decimal_sep)
                
                # Insert transaction and accounting entry using Connection Pool
                connection = pool_manager.get_connection(session_id)
                with UnitOfWork(connection) as uow:
                    tx_repo = TransactionRepository(uow)
                    
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
                        # Accounting entry is automatically created by database trigger
                        # trg_transaction_create_accounting_entry - NO manual insert needed
                        inserted += 1
            
            except Exception as exc:
                error_msg = str(exc).lower()
                if "duplicate" not in error_msg and "unique" not in error_msg:
                    warnings.append(f"Row {total}: {str(exc)}")
    
    except (ValueError, RuntimeError) as file_error:
        # CSV reading errors (encoding, no header, etc.)
        raise HTTPException(
            status_code=400,
            detail=f"CSV file error: {str(file_error)}"
        ) from file_error
    
    # Apply auto-categorization
    categorization_result = {"categorized": 0, "total_checked": 0}
    if inserted > 0:
        try:
            from api.routers.transactions import auto_categorize_entries
            connection = pool_manager.get_connection(session_id)
            cursor = None
            try:
                cursor = connection.cursor(buffered=True)
                categorization_result = auto_categorize_entries(cursor, connection)
            finally:
                if cursor:
                    try:
                        cursor.close()
                    except Exception:
                        pass
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
