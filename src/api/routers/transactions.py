"""
Transaction API router
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import Optional
from repositories.transaction_repository import TransactionRepository
from repositories.accounting_entry_repository import AccountingEntryRepository
from repositories.category_repository import CategoryRepository
from api.dependencies import get_db_cursor, get_db_connection
from api.models import TransactionResponse, TransactionListResponse, TransactionEntriesUpdate
from api.error_handling import handle_db_errors, safe_commit, safe_rollback
from decimal import Decimal

router = APIRouter(prefix="/transactions", tags=["transactions"])


@router.get("/", response_model=TransactionListResponse)
@handle_db_errors("fetch transactions")
async def get_transactions(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(None, description="Search in description, recipient, IBAN"),
    filter: Optional[str] = Query(None, description="Filter: 'unchecked' or 'no_entries'"),
    cursor = Depends(get_db_cursor)
):
    """
    Get all transactions with pagination and optional search.
    
    - **page**: Page number (starting from 1)
    - **page_size**: Number of items per page (max 100)
    - **search**: Optional search term for filtering
    - **filter**: Optional filter ('unchecked' for unchecked entries, 'no_entries' for transactions without entries)
    """
    repo = TransactionRepository(cursor)
    transactions = repo.get_all_transactions()
    
    # Apply filter if provided
    if filter == "unchecked":
        # Filter for transactions with at least one unchecked entry
        transactions = [
            t for t in transactions
            if any(not entry.get("checked", False) for entry in t.get("entries", []))
        ]
    elif filter == "no_entries":
        # Filter for transactions without any entries
        transactions = [
            t for t in transactions
            if len(t.get("entries", [])) == 0
        ]
    
    # Apply search filter if provided
    if search:
        search_lower = search.lower()
        transactions = [
            t for t in transactions
            if (search_lower in t.get("description", "").lower() or
                search_lower in (t.get("recipientApplicant") or "").lower() or
                search_lower in (t.get("iban") or "").lower() or
                search_lower in t.get("account_name", "").lower())
        ]
    
    total = len(transactions)
    
    # Apply pagination
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    paginated_transactions = transactions[start_idx:end_idx]
    
    return TransactionListResponse(
        transactions=paginated_transactions,
        total=total,
        page=page,
        page_size=page_size
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
    except Exception as e:
        safe_rollback(connection, "update transaction entries")
        raise
