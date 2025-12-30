"""
Shares and Securities API Router
Endpoints for managing shares, transactions, and price history
"""

from fastapi import APIRouter, Depends, UploadFile, File, Form
from api.dependencies import get_db_cursor, get_db_connection
from api.error_handling import handle_db_errors
import csv
import io
from datetime import datetime, date, timedelta

from repositories.share_repository import ShareRepository
from repositories.share_history_repository import ShareHistoryRepository
from repositories.share_transaction_repository import ShareTransactionRepository

router = APIRouter(tags=["shares"])


def safe_commit(connection):
    """Safely commit changes to database"""
    try:
        if connection:
            connection.commit()
        return True
    except Exception as e:
        print(f"Commit error: {e}")
        return False


def safe_rollback(connection):
    """Safely rollback changes"""
    try:
        if connection:
            connection.rollback()
    except Exception:
        pass


@router.get("/shares/")
@handle_db_errors("Failed to fetch shares")
async def get_shares(
    page: int = 1,
    page_size: int = 20,
    search: str = None,
    filter: str = None,
    sort_by: str = None,
    sort_dir: str = None,
    cursor=Depends(get_db_cursor)
):
    """Get all shares with pagination, optional search, filter, and sorting"""
    repo = ShareRepository(cursor)
    return repo.get_all_shares_paginated(page, page_size, search, filter, sort_by, sort_dir)


@router.post("/shares/")
@handle_db_errors("Failed to create share")
async def create_share(
    name: str = Form(...),
    isin: str = Form(None),
    wkn: str = Form(None),
    cursor=Depends(get_db_cursor),
    connection=Depends(get_db_connection)
):
    """Create a new share"""
    repo = ShareRepository(cursor)
    
    # Check if already exists
    existing = repo.get_share_by_isin_wkn(isin, wkn)
    if existing:
        return {"status": "error", "message": "Share already exists"}
    
    share_id = repo.insert_share(name, isin, wkn)
    safe_commit(connection)
    
    return {"status": "success", "share_id": share_id}


@router.put("/shares/{share_id}")
@handle_db_errors("Failed to update share")
async def update_share(
    share_id: int,
    name: str = Form(...),
    isin: str = Form(None),
    wkn: str = Form(None),
    cursor=Depends(get_db_cursor),
    connection=Depends(get_db_connection)
):
    """Update an existing share"""
    repo = ShareRepository(cursor)
    repo.update_share(share_id, name, isin, wkn)
    safe_commit(connection)
    return {"status": "success"}


@router.delete("/shares/{share_id}")
@handle_db_errors("Failed to delete share")
async def delete_share(
    share_id: int,
    cursor=Depends(get_db_cursor),
    connection=Depends(get_db_connection)
):
    """Delete a share"""
    repo = ShareRepository(cursor)
    repo.delete_share(share_id)
    safe_commit(connection)
    return {"status": "success"}


@router.get("/shares/history")
@handle_db_errors("Failed to fetch share history")
async def get_share_history(
    page: int = 1,
    page_size: int = 20,
    sort_by: str = None,
    sort_dir: str = None,
    search: str = None,
    checked: str = None,
    cursor=Depends(get_db_cursor)
):
    """Get all share history with pagination, sorting, search, and checked filter"""
    repo = ShareHistoryRepository(cursor)
    return repo.get_all_paginated(page, page_size, sort_by, sort_dir, search, checked)


@router.get("/shares/transactions")
@handle_db_errors("Failed to fetch share transactions")
async def get_share_transactions(
    page: int = 1,
    page_size: int = 20,
    search: str = None,
    sort_by: str = None,
    sort_dir: str = None,
    cursor=Depends(get_db_cursor)
):
    """Get all share transactions with pagination, optional search, and sorting"""
    repo = ShareTransactionRepository(cursor)
    return repo.get_all_paginated(page, page_size, search, sort_by, sort_dir)


@router.post("/shares/transactions")
@handle_db_errors("Failed to create transaction")
async def create_share_transaction(
    isin: str = Form(...),
    dateTransaction: str = Form(...),
    tradingVolume: float = Form(...),
    cursor=Depends(get_db_cursor),
    connection=Depends(get_db_connection)
):
    """Create a new share transaction
    Args:
        isin: ISIN of the share
        dateTransaction: Transaction date (ISO format: YYYY-MM-DD)
        tradingVolume: Number of shares traded (negative for sales)
    """
    share_repo = ShareRepository(cursor)
    transaction_repo = ShareTransactionRepository(cursor)
    
    try:
        # Find share by ISIN
        share = share_repo.get_share_by_isin_wkn(isin, None)
        if not share:
            return {"status": "error", "message": f"Share with ISIN {isin} not found"}
        
        share_id = share['id']
        
        # Insert transaction
        transaction_repo.insert_transaction(share_id, tradingVolume, dateTransaction)
        safe_commit(connection)
        
        return {"status": "success", "message": "Transaction created successfully"}
    except Exception as e:
        safe_rollback(connection)
        return {"status": "error", "message": str(e)}


@router.put("/shares/transactions/{transaction_id}")
@handle_db_errors("Failed to update transaction")
async def update_share_transaction(
    transaction_id: int,
    isin: str = Form(...),
    dateTransaction: str = Form(...),
    tradingVolume: float = Form(...),
    cursor=Depends(get_db_cursor),
    connection=Depends(get_db_connection)
):
    share_repo = ShareRepository(cursor)
    transaction_repo = ShareTransactionRepository(cursor)

    share = share_repo.get_share_by_isin_wkn(isin, None)
    if not share:
        return {"status": "error", "message": f"Share with ISIN {isin} not found"}

    transaction_repo.update_transaction(transaction_id, share['id'], tradingVolume, dateTransaction)
    safe_commit(connection)
    return {"status": "success"}


@router.delete("/shares/transactions/{transaction_id}")
@handle_db_errors("Failed to delete transaction")
async def delete_share_transaction(
    transaction_id: int,
    cursor=Depends(get_db_cursor),
    connection=Depends(get_db_connection)
):
    transaction_repo = ShareTransactionRepository(cursor)
    transaction_repo.delete_transaction(transaction_id)
    safe_commit(connection)
    return {"status": "success"}


@router.post("/shares/history")
@handle_db_errors("Failed to create history")
async def create_share_history(
    isin: str = Form(...),
    date: str = Form(...),
    amount: float = Form(...),
    cursor=Depends(get_db_cursor),
    connection=Depends(get_db_connection)
):
    """Create a new share history entry
    Args:
        isin: ISIN of the share
        date: Date (ISO format: YYYY-MM-DD)
        amount: Price or value amount
    """
    share_repo = ShareRepository(cursor)
    history_repo = ShareHistoryRepository(cursor)
    
    try:
        # Find share by ISIN
        share = share_repo.get_share_by_isin_wkn(isin, None)
        if not share:
            return {"status": "error", "message": f"Share with ISIN {isin} not found"}
        
        share_id = share['id']
        # Prevent duplicates by share/date
        existing_id = history_repo.history_exists_for_share_date(share_id, date)
        if existing_id:
            return {"status": "error", "message": "History entry for this share and date already exists"}

        # Insert history
        history_repo.insert_history(share_id, amount, date)
        safe_commit(connection)
        
        return {"status": "success", "message": "History entry created successfully"}
    except Exception as e:
        safe_rollback(connection)
        return {"status": "error", "message": str(e)}


@router.put("/shares/history/{history_id}")
@handle_db_errors("Failed to update history")
async def update_share_history(
    history_id: int,
    isin: str = Form(...),
    date: str = Form(...),
    amount: float = Form(...),
    checked: bool | None = Form(None),
    cursor=Depends(get_db_cursor),
    connection=Depends(get_db_connection)
):
    share_repo = ShareRepository(cursor)
    history_repo = ShareHistoryRepository(cursor)

    share = share_repo.get_share_by_isin_wkn(isin, None)
    if not share:
        return {"status": "error", "message": f"Share with ISIN {isin} not found"}

    try:
        history_repo.update_history(history_id, share['id'], amount, date, checked)
    except ValueError as ve:
        return {"status": "error", "message": str(ve)}
    safe_commit(connection)
    return {"status": "success"}


@router.put("/shares/history/{history_id}/checked")
@handle_db_errors("Failed to mark history checked")
async def set_share_history_checked(
    history_id: int,
    checked: bool = Form(True),
    cursor=Depends(get_db_cursor),
    connection=Depends(get_db_connection)
):
    history_repo = ShareHistoryRepository(cursor)
    history_repo.set_checked(history_id, checked)
    safe_commit(connection)
    return {"status": "success"}


@router.post("/shares/history/auto-fill")
@handle_db_errors("Failed to auto-fill share history")
async def auto_fill_share_history(cursor=Depends(get_db_cursor), connection=Depends(get_db_connection)):
    """Create missing month-end history entries with amount=0 for shares in holdings at month end (up to last completed month)."""
    share_repo = ShareRepository(cursor)
    history_repo = ShareHistoryRepository(cursor)
    tx_repo = ShareTransactionRepository(cursor)

    today = date.today()
    last_month_end = (today.replace(day=1) - timedelta(days=1))

    shares = share_repo.get_all_shares()
    created = 0
    skipped = 0

    for share in shares:
        share_id = share['id']
        txs = tx_repo.get_all_for_share_sorted(share_id)
        if not txs:
            continue

        first_tx_date = txs[0]['dateTransaction'].date() if hasattr(txs[0]['dateTransaction'], 'date') else txs[0]['dateTransaction']
        # start from first transaction month
        month_cursor = first_tx_date.replace(day=1)
        if month_cursor > last_month_end:
            continue

        existing_dates = history_repo.get_existing_dates_for_share(share_id)

        # prepare running balance
        balance = 0
        tx_index = 0
        total_txs = len(txs)

        while month_cursor <= last_month_end:
            # month end date
            next_month = (month_cursor.replace(day=28) + timedelta(days=4)).replace(day=1)
            month_end = next_month - timedelta(days=1)

            # apply transactions up to and including month_end
            while tx_index < total_txs:
                tx_date = txs[tx_index]['dateTransaction'].date() if hasattr(txs[tx_index]['dateTransaction'], 'date') else txs[tx_index]['dateTransaction']
                if tx_date <= month_end:
                    balance += float(txs[tx_index]['tradingVolume'])
                    tx_index += 1
                else:
                    break

            if balance != 0:
                month_end_iso = month_end.isoformat()
                if month_end_iso not in existing_dates:
                    inserted_id = history_repo.insert_history(share_id, 0, month_end_iso)
                    if inserted_id:
                        created += 1
                    else:
                        skipped += 1
                else:
                    skipped += 1

            month_cursor = next_month

    safe_commit(connection)
    return {"status": "success", "created": created, "skipped": skipped}


@router.delete("/shares/history/{history_id}")
@handle_db_errors("Failed to delete history")
async def delete_share_history(
    history_id: int,
    cursor=Depends(get_db_cursor),
    connection=Depends(get_db_connection)
):
    history_repo = ShareHistoryRepository(cursor)
    history_repo.delete_history(history_id)
    safe_commit(connection)
    return {"status": "success"}


@router.post("/shares/import/history")
@handle_db_errors("Failed to import history")
async def import_share_history(
    file: UploadFile = File(...),
    cursor=Depends(get_db_cursor),
    connection=Depends(get_db_connection)
):
    """Import share history from CSV file
    Expected format: ISIN ; Datum ; Betrag
    Date format: DD.MM.YYYY
    Amount format: German (comma as decimal separator, e.g., "51,31")
    """
    contents = await file.read()
    text_content = contents.decode('utf-8')
    
    share_repo = ShareRepository(cursor)
    history_repo = ShareHistoryRepository(cursor)
    
    imported = 0
    skipped = 0
    errors = []
    
    try:
        csv_reader = csv.DictReader(
            io.StringIO(text_content),
            fieldnames=['isin', 'date_str', 'amount_str'],
            delimiter=';'
        )
        # Skip header
        next(csv_reader, None)
        
        for row_num, row in enumerate(csv_reader, start=2):
            try:
                # Validate required fields
                isin = row.get('isin', '').strip() if row.get('isin') else None
                date_str = row.get('date_str', '').strip() if row.get('date_str') else None
                amount_str = row.get('amount_str', '').strip() if row.get('amount_str') else None
                
                if not all([isin, date_str, amount_str]):
                    errors.append(f"Row {row_num}: Missing required fields")
                    skipped += 1
                    continue
                
                # Parse amount (German format: comma as decimal)
                amount = float(amount_str.replace(',', '.'))
                
                # Parse date (German format: DD.MM.YYYY)
                date_obj = datetime.strptime(date_str, '%d.%m.%Y')
                date_only = date_obj.date().isoformat()
                
                # Look up or create share
                share = share_repo.get_share_by_isin_wkn(isin, None)
                if not share:
                    # Create share with ISIN as name (since WKN is not provided)
                    share_id = share_repo.insert_share(isin, isin, None)
                    share = share_repo.get_share_by_id(share_id)
                else:
                    share_id = share['id']
                
                # Insert history record if not already present
                inserted_id = history_repo.insert_history(share_id, amount, date_only)
                if inserted_id:
                    imported += 1
                else:
                    skipped += 1
                
            except ValueError as ve:
                error_msg = f"Row {row_num}: {str(ve)}"
                errors.append(error_msg)
                skipped += 1
            except Exception as e:
                error_msg = f"Row {row_num}: {str(e)}"
                errors.append(error_msg)
                skipped += 1
        
        # Commit all changes
        safe_commit(connection)
        
        return {
            "status": "success",
            "imported": imported,
            "skipped": skipped,
            "errors": errors[:10],  # Return first 10 errors
            "total_errors": len(errors)
        }
        
    except Exception as e:
        safe_rollback(connection)
        return {
            "status": "error",
            "message": str(e),
            "imported": imported,
            "skipped": skipped
        }


@router.post("/shares/import/transactions")
@handle_db_errors("Failed to import transactions")
async def import_share_transactions(
    file: UploadFile = File(...),
    cursor=Depends(get_db_cursor),
    connection=Depends(get_db_connection)
):
    """Import share transactions from CSV file
    Expected format: ISIN ; Datum ; Anteile
    Date format: DD.MM.YYYY
    Shares format: German (comma as decimal separator, e.g., "7173.91304")
    """
    contents = await file.read()
    text_content = contents.decode('utf-8')
    
    share_repo = ShareRepository(cursor)
    transaction_repo = ShareTransactionRepository(cursor)
    
    imported = 0
    skipped = 0
    errors = []
    
    try:
        csv_reader = csv.DictReader(
            io.StringIO(text_content),
            fieldnames=['isin', 'date_str', 'shares_str'],
            delimiter=';'
        )
        # Skip header
        next(csv_reader, None)
        
        for row_num, row in enumerate(csv_reader, start=2):
            try:
                # Validate required fields
                isin = row.get('isin', '').strip() if row.get('isin') else None
                date_str = row.get('date_str', '').strip() if row.get('date_str') else None
                shares_str = row.get('shares_str', '').strip() if row.get('shares_str') else None
                
                # Skip rows with empty shares field
                if not shares_str:
                    skipped += 1
                    continue
                
                if not all([isin, date_str]):
                    errors.append(f"Row {row_num}: Missing ISIN or Datum")
                    skipped += 1
                    continue
                
                # Parse shares (German format: comma as decimal)
                trading_volume = float(shares_str.replace(',', '.'))
                
                # Parse date (German format: DD.MM.YYYY)
                date_obj = datetime.strptime(date_str, '%d.%m.%Y')
                
                # Look up share by ISIN
                share = share_repo.get_share_by_isin_wkn(isin, None)
                if not share:
                    errors.append(f"Row {row_num}: Share with ISIN {isin} not found")
                    skipped += 1
                    continue
                
                share_id = share['id']
                
                # Insert transaction record
                transaction_repo.insert_transaction(share_id, trading_volume, date_obj.isoformat())
                imported += 1
                
            except ValueError as ve:
                error_msg = f"Row {row_num}: {str(ve)}"
                errors.append(error_msg)
                skipped += 1
            except Exception as e:
                error_msg = f"Row {row_num}: {str(e)}"
                errors.append(error_msg)
                skipped += 1
        
        # Commit all changes
        safe_commit(connection)
        
        return {
            "status": "success",
            "imported": imported,
            "skipped": skipped,
            "errors": errors[:10],  # Return first 10 errors
            "total_errors": len(errors)
        }
        
    except Exception as e:
        safe_rollback(connection)
        return {
            "status": "error",
            "message": str(e),
            "imported": imported,
            "skipped": skipped
        }
