#
# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (c) 2026 m2-eng
# Author: m2-eng
# Co-Author: GitHub Copilot
# License: GNU Affero General Public License v3.0 (AGPL-3.0-only)
# Purpose: Module for import service.
#
from typing import List, Optional, Any
from services.import_steps.base import ImportStep
from services.csv_utils import read_csv_rows, parse_amount, parse_date
from services.field_extractor import extract_field_value
from infrastructure.unit_of_work import UnitOfWork
from pathlib import Path
from decimal import Decimal
from datetime import datetime


class ImportService:
   def __init__(self, pool_manager, session_id: str, steps: List[ImportStep]):
      """
        Initializes the import service with the connection pool manager.
      
      Args:
            pool_manager: ConnectionPoolManager instance
            session_id: Session ID for the connection pool
            steps: List of ImportStep instances
      """
      self.pool_manager = pool_manager
      self.session_id = session_id
      self.steps = steps

   def run(self, data: dict) -> bool:
      """
        Runs all import steps in sequence.
      
      Args:
            data: Data for the import
         
      Returns:
            True if all steps succeeded, False otherwise
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
                # Connection is returned to the pool automatically
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
    Uses the connection pool manager for database access.
    
    If the CSV has an account column, use it to determine the account for each row.
    Otherwise, use the default_account_id for all rows.
    
    Args:
        pool_manager: ConnectionPoolManager instance
        session_id: Session ID for the connection pool
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
    
    # Get a single connection from pool for all operations
    connection = pool_manager.get_connection(session_id)
    
    # Batch settings (opt-in via mapping, default 1000)
    batch_size = mapping.get("batch_size", 1000)
    try:
        batch_size = int(batch_size)
    except Exception:
        batch_size = 1000
    batch_size = max(100, min(batch_size, 5000))

    batch_rows: list[tuple] = []

    def flush_batch() -> None:
        nonlocal inserted
        if not batch_rows:
            return
        with UnitOfWork(connection) as uow:
            tx_repo = TransactionRepository(uow)
            inserted += tx_repo.insert_ignore_many(batch_rows)
        batch_rows.clear()

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
                        
                        # Look up account by name (reuse same connection)
                        if account_name not in account_cache:
                            try:
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
                
                # Batch insert rows for better performance
                batch_rows.append(
                    (
                        iban or None,
                        bic or None,
                        description,
                        amount,
                        date_value,
                        recipient or None,
                        row_account_id,
                    )
                )
                if len(batch_rows) >= batch_size:
                    flush_batch()
            
            except Exception as exc:
                error_msg = str(exc).lower()
                if "duplicate" not in error_msg and "unique" not in error_msg:
                    warnings.append(f"Row {total}: {str(exc)}")
    
        # Flush remaining rows
        flush_batch()

    except (ValueError, RuntimeError) as file_error:
        # CSV reading errors (encoding, no header, etc.)
        raise HTTPException(
            status_code=400,
            detail=f"CSV file error: {str(file_error)}"
        ) from file_error
    finally:
        # Return connection to the pool (important!).
        if connection:
            try:
                connection.close()  # Back to pool
            except Exception:
                pass
    
    # Apply auto-categorization (uses separate connection)
    categorization_result = {"categorized": 0, "total_checked": 0}
    if inserted > 0:
        cat_connection = None
        cursor = None
        try:
            from api.routers.transactions import auto_categorize_entries
            cat_connection = pool_manager.get_connection(session_id)
            cursor = cat_connection.cursor(buffered=True)
            categorization_result = auto_categorize_entries(cursor, cat_connection)
        except Exception as cat_error:
            warnings.append(f"Auto-categorization failed: {str(cat_error)}")
        finally:
            # Return cursor and connection to the pool (important!).
            if cursor:
                try:
                    cursor.close()
                except Exception:
                    pass
            if cat_connection:
                try:
                    cat_connection.close()  # Back to pool
                except Exception:
                    pass
    
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


# Legacy alias for backwards compatibility
_get_field_value = extract_field_value
