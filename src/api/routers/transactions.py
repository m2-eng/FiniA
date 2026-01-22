"""
Transaction API router
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File, Form
from typing import Optional
from pydantic import BaseModel
from repositories.transaction_repository import TransactionRepository
from repositories.accounting_entry_repository import AccountingEntryRepository
from repositories.category_repository import CategoryRepository
from api.dependencies import get_db_cursor_with_auth as get_db_cursor, get_db_connection_with_auth as get_db_connection
from api.models import TransactionResponse, TransactionListResponse, TransactionEntriesUpdate
from typing import List
from pydantic import BaseModel
from api.error_handling import handle_db_errors, safe_commit, safe_rollback
from decimal import Decimal
from Database import Database
from services.account_data_importer import AccountDataImporter
from infrastructure.unit_of_work import UnitOfWork
from repositories.account_import_repository import AccountImportRepository
from services.category_automation import load_rules, apply_rules_to_transaction
import tempfile
import os
from pathlib import Path
import yaml


class ImportRequest(BaseModel):
    """Request model for import operation"""
    account_id: Optional[int] = None  # None means import all accounts


class AutoCategorizeRequest(BaseModel):
    """Request model for auto-categorization"""
    account_id: Optional[int] = None  # None means all accounts


def auto_categorize_entries(cursor, connection) -> dict:
    """
    Apply automation rules to uncategorized accounting entries.
    
    Returns:
        Dict with categorization statistics
    """
    # Get all automation rules (no account filter = all rules)
    rules = load_rules(cursor)
    if not rules:
        return {"categorized": 0, "total_checked": 0, "message": "Keine Kategorisierungsregeln gefunden"}
    
    # Get all uncategorized entries with their transaction details
    query = """
        SELECT DISTINCT
            ae.id as entry_id,
            ae.transaction as transaction_id,
            t.description,
            t.recipientApplicant,
            t.amount,
            t.iban,
            t.account as account_id
        FROM tbl_accountingEntry ae
        INNER JOIN tbl_transaction t ON ae.transaction = t.id
        WHERE ae.category IS NULL
        ORDER BY t.dateValue DESC
    """
    
    cursor.execute(query)
    entries = cursor.fetchall()
    
    if not entries:
        return {"categorized": 0, "total_checked": 0, "message": "Keine unkategorisierten Einträge gefunden"}
    
    categorized_entry_count = 0
    
    for entry in entries:
        entry_id = entry[0]
        transaction_data = {
            "description": entry[2],
            "recipientApplicant": entry[3],
            "amount": float(entry[4]),
            "iban": entry[5]
        }
        account_id = entry[6]
        
        # Filter rules for this specific account
        account_rules = [
            rule for rule in rules
            if not rule.get('accounts') or account_id in rule.get('accounts', [])
        ]
        
        # Apply rules
        category_id = apply_rules_to_transaction(transaction_data, account_rules)
        
        if category_id:
            # Update entry with category
            update_query = "UPDATE tbl_accountingEntry SET category = %s WHERE id = %s"
            cursor.execute(update_query, (category_id, entry_id))
            categorized_entry_count += 1
    
    connection.commit()
    
    return {
        "categorized": categorized_entry_count,
        "total_checked": len(entries),
        "message": "Transaktionen kategorisiert"
    }


router = APIRouter(prefix="/transactions", tags=["transactions"])


@router.get("/import-formats")
async def get_import_formats():
    """
    Get list of available import formats from configuration.
    """
    try:
        repo_root = Path(__file__).resolve().parents[3]
        formats_file = repo_root / "cfg" / "import_formats.yaml"
        
        if not formats_file.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Import formats configuration file not found"
            )
        
        with open(formats_file, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        
        formats = list(data.get("formats", {}).keys())
        
        return {
            "success": True,
            "formats": formats
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load import formats: {str(e)}"
        )


class BulkCheckRequest(BaseModel):
    """Request body for bulk marking transactions checked/unchecked."""
    transaction_ids: List[int]
    checked: bool = True


@router.get("/", response_model=TransactionListResponse)
@handle_db_errors("fetch transactions")
async def get_transactions(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=1000, description="Items per page (max 1000)"),
    search: Optional[str] = Query(None, description="Search in description, recipient, IBAN"),
    filter: Optional[str] = Query(None, description="Filter: 'unchecked', 'no_entries', 'uncategorized', or 'categorized_unchecked'"),
    cursor = Depends(get_db_cursor)
):
    """
    Get transactions with pagination and optional search.
    
    - **page**: Page number (starting from 1)
    - **page_size**: Number of items per page (max 1000)
    - **search**: Optional search term for filtering
    - **filter**: Optional filter:
        - 'unchecked': transactions with at least one unchecked entry
        - 'no_entries': transactions without any entries
        - 'uncategorized': transactions with at least one entry without category
        - 'categorized_unchecked': transactions with entries that have category but are unchecked
    
    Note: When using search or filter, all matching transactions are loaded into memory for filtering,
    then paginated. For large datasets with complex filters, this may impact performance.
    """
    repo = TransactionRepository(cursor)
    
    # Use optimized SQL-based filtering and pagination
    result = repo.get_all_transactions_paginated(
        page=page, 
        page_size=page_size,
        search=search,
        filter_type=filter
    )
    
    return TransactionListResponse(
        transactions=result['transactions'],
        total=result['total'],
        page=result['page'],
        page_size=result['page_size']
    )


@router.get("/{transaction_id}", response_model=TransactionResponse)
@handle_db_errors("fetch transaction")
async def get_transaction(
    transaction_id: int,
    cursor = Depends(get_db_cursor)
):
    """
    Get a single transaction by ID with all accounting entries.
    
    - **transaction_id**: Transaction ID
    """
    repo = TransactionRepository(cursor)
    transaction = repo.get_transaction_by_id(transaction_id)
    
    if not transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Transaction with ID {transaction_id} not found"
        )
    
    return transaction


@router.put("/{transaction_id}/entries", response_model=TransactionResponse)
@handle_db_errors("update transaction entries")
async def update_transaction_entries(
    transaction_id: int,
    entries_update: TransactionEntriesUpdate,
    cursor = Depends(get_db_cursor),
    connection = Depends(get_db_connection)
):
    """
    Update all accounting entries for a transaction.
    Will delete removed entries, update existing ones, and create new ones.
    
    - **transaction_id**: Transaction ID
    - **entries_update**: List of accounting entries to save
    """
    # Verify transaction exists
    tx_repo = TransactionRepository(cursor)
    transaction = tx_repo.get_transaction_by_id(transaction_id)
    if not transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Transaction with ID {transaction_id} not found"
        )
    
    entry_repo = AccountingEntryRepository(cursor)
    category_repo = CategoryRepository(cursor)
    
    # Get existing entry IDs for this transaction
    existing_entries = entry_repo.get_all_by_transaction(transaction_id)
    existing_ids = {e['id'] for e in existing_entries}
    updated_ids = {e.id for e in entries_update.entries if e.id is not None}
    
    try:
        # Delete entries that are no longer in the list
        for entry_id in existing_ids - updated_ids:
            entry_repo.delete(entry_id)
        
        # Update or insert entries
        for entry in entries_update.entries:
            # Get or create category ID
            category_id = None
            if entry.category_name:
                category_id = category_repo.get_category_by_name(entry.category_name)
                if not category_id:
                    # Create new category
                    max_id = category_repo.get_max_category_id()
                    category_id = max_id + 1
                    category_repo.insert_category(category_id, entry.category_name)
            
            # accountingPlanned: if True, set to 1, otherwise NULL
            accounting_planned_id = 1 if entry.accountingPlanned else None
            
            if entry.id and entry.id in existing_ids:
                # Update existing entry
                entry_repo.update(
                    entry_id=entry.id,
                    amount=entry.amount,
                    checked=entry.checked,
                    accounting_planned_id=accounting_planned_id,
                    category_id=category_id
                )
            else:
                # Insert new entry
                entry_repo.insert(
                    amount=entry.amount,
                    transaction_id=transaction_id,
                    checked=entry.checked,
                    accounting_planned_id=accounting_planned_id,
                    category_id=category_id
                )
        
        # Commit the transaction
        safe_commit(connection, "update transaction entries")
        
        # Return updated transaction
        updated_transaction = tx_repo.get_transaction_by_id(transaction_id)
        return updated_transaction
        
    except HTTPException:
        safe_rollback(connection, "update transaction entries")
        raise


@router.post("/mark-checked")
@handle_db_errors("bulk mark transactions checked")
async def bulk_mark_transactions_checked(
    request: BulkCheckRequest,
    cursor = Depends(get_db_cursor),
    connection = Depends(get_db_connection)
):
    """Mark all accounting entries of the given transactions as checked/unchecked."""
    entry_repo = AccountingEntryRepository(cursor)
    updated = entry_repo.set_checked_for_transactions(request.transaction_ids, request.checked)
    safe_commit(connection, "bulk mark transactions checked")
    return {"updated_entries": updated}


@router.post("/import")
@handle_db_errors("import transactions")
async def import_transactions(
    request: ImportRequest,
    cursor = Depends(get_db_cursor)
):
    """
    Import transactions from configured import paths.
    
    - **account_id**: If provided, imports only for this account. If None, imports all accounts.
    """
    from api.dependencies import get_database_credentials, get_database_config
    
    # Get database credentials that were set on API startup
    credentials = get_database_credentials()
    db_config = get_database_config()
    
    if not credentials or not credentials.get('user') or not credentials.get('password'):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database credentials not configured"
        )
    
    # Create Database instance for importer
    db = Database(
        user=credentials['user'],
        password=credentials['password'],
        host=credentials.get('host') or db_config.get('host', 'localhost'),
        port=credentials.get('port') or db_config.get('port', 3306),
        database_name=credentials.get('name') or db_config.get('name', 'FiniA')
    )
    
    try:
        # Connect to database
        if not db.connect(use_database=True):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to connect to database"
            )
        
        # Create importer instance
        importer = AccountDataImporter(db)
        
        # If account_id is specified, filter jobs
        if request.account_id:
            # Get all jobs
            jobs = importer._collect_jobs()
            
            # Filter for specific account
            jobs = [job for job in jobs if job.account_id == request.account_id]
            
            if not jobs:
                db.close()
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"No import configuration found for account ID {request.account_id}"
                )
            
            # Import only for this account
            overall_inserted = 0
            overall_total = 0
            imported_files = []
            skipped_info = []
            
            for job in jobs:
                if not job.path.exists():
                    skipped_info.append(f"Pfad nicht gefunden: {job.path}")
                    continue
                    
                try:
                    mapping = importer._get_mapping(job.format)
                except Exception as exc:
                    skipped_info.append(f"Mapping-Fehler für {job.account_name}: {exc}")
                    continue
                
                files = sorted(job.path.glob(f"*.{job.file_ending}"))
                if not files:
                    skipped_info.append(f"Keine *.{job.file_ending} Dateien in {job.path}")
                    continue
                
                for csv_file in files:
                    with UnitOfWork(db.connection) as uow:
                        from repositories.transaction_repository import TransactionRepository
                        from repositories.accounting_entry_repository import AccountingEntryRepository
                        tx_repo = TransactionRepository(uow)
                        ae_repo = AccountingEntryRepository(uow)
                        inserted, total = importer._import_file(csv_file, mapping, job, tx_repo, ae_repo)
                        overall_inserted += inserted
                        overall_total += total
                        imported_files.append({
                            "file": csv_file.name,
                            "account": job.account_name,
                            "inserted": inserted,
                            "total": total
                        })
            
            # Apply auto-categorization after import
            categorization_result = {"categorized": 0, "total_checked": 0}
            try:
                if overall_inserted > 0:
                    categorization_result = auto_categorize_entries(cursor, db.connection)
            except Exception as cat_error:
                skipped_info.append(f"Automatische Kategorisierung fehlgeschlagen: {cat_error}")
            
            db.close()
            
            result = {
                "success": True,
                "message": f"Import abgeschlossen: {overall_inserted} von {overall_total} Transaktionen importiert",
                "account_id": request.account_id,
                "inserted": overall_inserted,
                "total": overall_total,
                "files": imported_files,
                "auto_categorized": categorization_result.get("categorized", 0),
                "auto_categorized_total": categorization_result.get("total_checked", 0)
            }
            
            if skipped_info:
                result["warnings"] = skipped_info
            
            return result
        else:
            # Import all accounts
            success = importer.import_account_data()
            db.close()
            
            if success:
                return {
                    "success": True,
                    "message": "Import für alle Konten abgeschlossen"
                }
            else:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Import fehlgeschlagen"
                )
    
    except HTTPException:
        if db:
            db.close()
        raise
    except Exception as e:
        if db:
            db.close()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Import fehlgeschlagen: {str(e)}"
        )


@router.post("/auto-categorize")
@handle_db_errors("auto categorize transactions")
async def auto_categorize_transactions(
    request: AutoCategorizeRequest,
    cursor = Depends(get_db_cursor),
    connection = Depends(get_db_connection)
):
    """
    Apply automation rules to uncategorized accounting entries.
    
    - **account_id**: If provided, only categorizes entries for this account. If None, all accounts.
    """
    try:
        # Apply categorization
        result = auto_categorize_entries(cursor, connection)
        
        return {
            "success": True,
            "categorized": result["categorized"],
            "total_checked": result["total_checked"],
            "message": result["message"]
        }
    
    except Exception as e:
        safe_rollback(connection, "auto categorize transactions")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Kategorisierung fehlgeschlagen: {str(e)}"
        )


@router.post("/import-csv")
@handle_db_errors("import CSV file")
async def import_csv_file(
    file: UploadFile = File(...),
    format: str = Form(...),
    account_id: Optional[int] = Form(None),
    cursor = Depends(get_db_cursor)
):
    """
    Import transactions from a specific CSV file.
    
    - **file**: CSV file to import
    - **format**: Import format name (e.g., 'csv-cb', 'csv-loan')
    - **account_id**: Optional account ID. Required if format doesn't specify account column.
    """
    from api.dependencies import get_database_credentials, get_database_config
    from repositories.account_repository import AccountRepository
    
    # Get database credentials
    credentials = get_database_credentials()
    db_config = get_database_config()
    
    if not credentials or not credentials.get('user') or not credentials.get('password'):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database credentials not configured"
        )
    
    # Create Database instance
    db = Database(
        user=credentials['user'],
        password=credentials['password'],
        host=credentials.get('host') or db_config.get('host', 'localhost'),
        port=credentials.get('port') or db_config.get('port', 3306),
        database_name=credentials.get('name') or db_config.get('name', 'FiniA')
    )
    
    temp_file_path = None
    
    try:
        # Connect to database
        if not db.connect(use_database=True):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to connect to database"
            )
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(mode='wb', delete=False, suffix='.csv') as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_file_path = temp_file.name
        
        # Create importer instance
        importer = AccountDataImporter(db)
        
        # Get format mapping
        try:
            mapping = importer._get_mapping(format)
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid format '{format}': {str(exc)}"
            )
        
        # Check if format has account column
        columns = mapping.get("columns", {})
        has_account_column = columns.get("account") is not None
        
        # If no account column and no account_id provided, error
        if not has_account_column and not account_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Account ID is required for this format (no account column in CSV)"
            )
        
        # Import the file
        from services.import_service import import_csv_with_optional_account
        
        result = import_csv_with_optional_account(
            db=db,
            csv_path=Path(temp_file_path),
            format_name=format,
            mapping=mapping,
            default_account_id=account_id,
            cursor=cursor
        )
        
        db.close()
        
        return result
    
    except HTTPException:
        if db:
            db.close()
        raise
    except Exception as e:
        if db:
            db.close()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Import fehlgeschlagen: {str(e)}"
        )
    finally:
        # Clean up temporary file
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.unlink(temp_file_path)
            except:
                pass
