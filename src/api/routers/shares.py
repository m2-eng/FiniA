"""
Shares and Securities API Router
Endpoints for managing shares, transactions, and price history
"""

import json
from fastapi import APIRouter, Depends, UploadFile, File, Form, Query
from api.dependencies import get_db_cursor_with_auth as get_db_cursor, get_db_connection_with_auth as get_db_connection
from api.error_handling import handle_db_errors, safe_commit, safe_rollback
import csv
import io
from datetime import datetime, date, timedelta

from repositories.share_repository import ShareRepository
from repositories.share_history_repository import ShareHistoryRepository
from repositories.share_transaction_repository import ShareTransactionRepository
from repositories.settings_repository import SettingsRepository

router = APIRouter(tags=["shares"])


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
    isin: str = Form(...),
    name: str = Form(None),
    wkn: str = Form(None),
    cursor=Depends(get_db_cursor),
    connection=Depends(get_db_connection)
):
    """Create a new share
    Args:
        isin: ISIN code (mandatory)
        name: Share name (optional)
        wkn: WKN code (optional)
    """
    if not isin or isin.strip() == '':
        return {"status": "error", "message": "ISIN is required"}
    
    repo = ShareRepository(cursor)
    
    # Check if already exists by ISIN
    existing = repo.get_share_by_isin_wkn(isin, None)
    if existing:
        return {"status": "error", "message": "Share with this ISIN already exists"}
    
    share_id = repo.insert_share(name, isin, wkn)
    safe_commit(connection)
    
    return {"status": "success", "share_id": share_id}


@router.put("/shares/{share_id}")
@handle_db_errors("Failed to update share")
async def update_share(
    share_id: int,
    isin: str = Form(...),
    name: str = Form(None),
    wkn: str = Form(None),
    cursor=Depends(get_db_cursor),
    connection=Depends(get_db_connection)
):
    """Update an existing share
    Args:
        share_id: ID of the share to update
        isin: ISIN code (mandatory)
        name: Share name (optional)
        wkn: WKN code (optional)
    """
    if not isin or isin.strip() == '':
        return {"status": "error", "message": "ISIN is required"}
    
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
    accountingEntryId: int = Form(None),
    cursor=Depends(get_db_cursor),
    connection=Depends(get_db_connection)
):
    """Create a new share transaction
    Args:
        isin: ISIN of the share
        dateTransaction: Transaction date and time (ISO format: YYYY-MM-DDTHH:MM:SS or YYYY-MM-DD)
        tradingVolume: Number of shares traded (negative for sales)
        accountingEntryId: Optional accounting entry ID to link to this transaction
    """
    share_repo = ShareRepository(cursor)
    transaction_repo = ShareTransactionRepository(cursor)
    
    try:
        # Find share by ISIN
        share = share_repo.get_share_by_isin_wkn(isin, None)
        if not share:
            return {"status": "error", "message": f"Share with ISIN {isin} not found"}
        
        share_id = share['id']
        
        # Insert transaction with optional accounting entry
        transaction_repo.insert_transaction(share_id, tradingVolume, dateTransaction, accountingEntryId)
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
    accountingEntryId: int = Form(None),
    cursor=Depends(get_db_cursor),
    connection=Depends(get_db_connection)
):
    share_repo = ShareRepository(cursor)
    transaction_repo = ShareTransactionRepository(cursor)

    share = share_repo.get_share_by_isin_wkn(isin, None)
    if not share:
        return {"status": "error", "message": f"Share with ISIN {isin} not found"}

    transaction_repo.update_transaction(transaction_id, share['id'], tradingVolume, dateTransaction, accountingEntryId)
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
    Expected format: ISIN/WKN ; Datum ; Betrag
    First column can be ISIN or WKN (ISIN has priority if both exist)
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
            fieldnames=['identifier', 'date_str', 'amount_str'],
            delimiter=';'
        )
        # Skip header
        next(csv_reader, None)
        
        for row_num, row in enumerate(csv_reader, start=2):
            try:
                # Validate required fields
                identifier = row.get('identifier', '').strip() if row.get('identifier') else None
                date_str = row.get('date_str', '').strip() if row.get('date_str') else None
                amount_str = row.get('amount_str', '').strip() if row.get('amount_str') else None
                
                if not all([identifier, date_str, amount_str]):
                    errors.append(f"Row {row_num}: Missing required fields")
                    skipped += 1
                    continue
                
                # Parse amount (German format: comma as decimal)
                amount = float(amount_str.replace(',', '.'))
                
                # Parse date (German format: DD.MM.YYYY)
                date_obj = datetime.strptime(date_str, '%d.%m.%Y')
                date_only = date_obj.date().isoformat()
                
                # Look up share by ISIN or WKN
                # identifier can be ISIN or WKN
                # Determine if it's ISIN (>6 chars) or WKN (<=6 chars)
                is_isin = len(identifier) > 6
                
                if is_isin:
                    share = share_repo.get_share_by_isin_wkn(identifier, None)
                else:
                    share = share_repo.get_share_by_isin_wkn(None, identifier)
                
                if not share:
                    # Create share with only ISIN or WKN, name empty (user fills later)
                    if is_isin:
                        share_id = share_repo.insert_share(None, identifier, None)
                    else:
                        share_id = share_repo.insert_share(None, None, identifier)
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



@router.get("/shares/accounting-entries/{entry_id}")
@handle_db_errors("Failed to fetch accounting entry")
async def get_accounting_entry(
    entry_id: int,
    cursor=Depends(get_db_cursor)
):
    """Get a single accounting entry by ID (including those already assigned to share transactions)"""
    query = """
        SELECT ae.id, ae.amount, ae.dateImport, t.description, t.dateValue
        FROM tbl_accountingEntry ae
        JOIN tbl_transaction t ON ae.transaction = t.id
        WHERE ae.id = %s
    """
    cursor.execute(query, (entry_id,))
    row = cursor.fetchone()
    
    if not row:
        return {'entry': None}
    
    return {
        'entry': {
            'id': row[0],
            'amount': float(row[1]),
            'dateImport': row[2].isoformat() if row[2] else None,
            'description': row[3],
            'dateValue': row[4].isoformat() if row[4] else None,
            'display': f"{row[4]} - {row[3]} ({row[1]}€)" if row[4] and row[3] else f"ID: {row[0]}"
        }
    }


@router.get("/shares/accounting-entries")
@handle_db_errors("Failed to fetch accounting entries")
async def get_accounting_entries(
    type: str = Query(None, description="buy|sell to filter by configured category set"),
    date: str | None = Query(None, description="YYYY-MM-DD; when provided and date filter enabled, limits to date..date+7d"),
    cursor=Depends(get_db_cursor)
):
    """Get list of available accounting entries for linking with transactions.
    Filters by configured categories for buy/sell if available.
    """
    settings_repo = SettingsRepository(cursor)
    entries = settings_repo.get_settings("share_tx_category")
    
    buy_ids = []
    sell_ids = []
    dividend_ids = []
    
    for entry_json in entries:
        try:
            data = json.loads(entry_json)
            cat_id = int(data.get("category_id"))
            cat_type = data.get("type")
            if cat_type == "buy":
                buy_ids.append(cat_id)
            elif cat_type == "sell":
                sell_ids.append(cat_id)
            elif cat_type == "dividend":
                dividend_ids.append(cat_id)
        except Exception:
            continue

    filter_ids = []
    if type == 'buy':
        filter_ids = buy_ids
    elif type == 'sell':
        filter_ids = sell_ids
    elif type == 'dividend':
        filter_ids = dividend_ids
    else:
        # union of all configured categories
        filter_ids = list({*buy_ids, *sell_ids, *dividend_ids}) if (buy_ids or sell_ids or dividend_ids) else []

    # If no categories configured, return empty list to force configuration first
    if not filter_ids:
        return {'entries': []}

    placeholders = ','.join(['%s'] * len(filter_ids))

    params = list(filter_ids)
    date_clause = ""
    if date:
        try:
            start_date = datetime.fromisoformat(date).date()
            start_minus_7 = start_date - timedelta(days=7)
            end_plus_7 = start_date + timedelta(days=7)
            date_clause = " AND t.dateValue BETWEEN %s AND %s"
            params.extend([start_minus_7, end_plus_7])
        except Exception:
            pass

    query = f"""
        SELECT ae.id, ae.amount, ae.dateImport, t.description, t.dateValue
        FROM tbl_accountingEntry ae
        JOIN tbl_transaction t ON ae.transaction = t.id
        WHERE ae.id NOT IN (SELECT COALESCE(accountingEntry, 0) FROM tbl_shareTransaction WHERE accountingEntry IS NOT NULL)
          AND ae.category IN ({placeholders}){date_clause}
        ORDER BY t.dateValue DESC
        LIMIT 100
    """
    cursor.execute(query, params)
    rows = cursor.fetchall()
    
    entries_list = []
    for row in rows:
        entries_list.append({
            'id': row[0],
            'amount': float(row[1]),
            'dateImport': row[2].isoformat() if row[2] else None,
            'description': row[3],
            'dateValue': row[4].isoformat() if row[4] else None,
            'display': f"{row[4]} - {row[3]} ({row[1]}€)" if row[4] and row[3] else f"ID: {row[0]}"
        })
    
    return {'entries': entries_list}


@router.post("/shares/import/transactions")
@handle_db_errors("Failed to import transactions")
async def import_share_transactions(
    file: UploadFile = File(...),
    cursor=Depends(get_db_cursor),
    connection=Depends(get_db_connection)
):
    """Import share transactions from CSV file
    Expected format: ISIN/WKN ; Datum ; Anteile
    First column can be ISIN or WKN (ISIN has priority if both exist)
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
            fieldnames=['identifier', 'date_str', 'shares_str'],
            delimiter=';'
        )
        # Skip header
        next(csv_reader, None)
        
        for row_num, row in enumerate(csv_reader, start=2):
            try:
                # Validate required fields
                identifier = row.get('identifier', '').strip() if row.get('identifier') else None
                date_str = row.get('date_str', '').strip() if row.get('date_str') else None
                shares_str = row.get('shares_str', '').strip() if row.get('shares_str') else None
                
                # Treat empty shares as 0 (dividend/no trading volume)
                if not shares_str or shares_str == '':
                    trading_volume = 0
                else:
                    # Parse shares (German format: comma as decimal)
                    trading_volume = float(shares_str.replace(',', '.'))
                
                if not all([identifier, date_str]):
                    errors.append(f"Row {row_num}: Missing ISIN/WKN or Datum")
                    skipped += 1
                    continue
                
                # Parse date (German format: DD.MM.YYYY)
                date_obj = datetime.strptime(date_str, '%d.%m.%Y')
                
                # Look up share by ISIN or WKN
                # identifier can be ISIN or WKN
                # Determine if it's ISIN (>6 chars) or WKN (<=6 chars)
                is_isin = len(identifier) > 6
                
                if is_isin:
                    share = share_repo.get_share_by_isin_wkn(identifier, None)
                else:
                    share = share_repo.get_share_by_isin_wkn(None, identifier)
                
                if not share:
                    # Auto-create share with only ISIN or WKN (name empty, user fills later)
                    if is_isin:
                        share_id = share_repo.insert_share(None, identifier, None)
                    else:
                        share_id = share_repo.insert_share(None, None, identifier)
                    share = share_repo.get_share_by_id(share_id)
                else:
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
