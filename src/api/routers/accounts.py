"""
Account details API router - provides income/expense breakdown per account
"""

from fastapi import APIRouter, Depends, Query, HTTPException, Path, UploadFile, File
from api.dependencies import get_db_cursor_with_auth, get_db_connection_with_auth, get_pool_manager
from api.error_handling import handle_db_errors, safe_commit
from api.auth_middleware import get_current_session
from api.models import AccountData
from services.import_service import ImportService
from services.import_steps.accounts import AccountsStep
import yaml

from repositories.account_repository import AccountRepository

router = APIRouter(prefix="/accounts", tags=["accounts"])

@router.post("/import-yaml")
@handle_db_errors("import accounts from YAML")
async def import_accounts_from_yaml(
  file: UploadFile = File(...),
  pool_manager = Depends(get_pool_manager),
  session_id: str = Depends(get_current_session)
):
  """Import accounts from YAML file using account_data syntax."""
  if not file:
    raise HTTPException(status_code=400, detail="Keine Datei übergeben")

  try:
    content = await file.read()
    data = yaml.safe_load(content)
  except Exception as e:
    raise HTTPException(status_code=400, detail=f"Ungültige YAML-Datei: {e}")

  if not isinstance(data, dict) or "account_data" not in data:
    raise HTTPException(status_code=400, detail="YAML-Datei enthält keinen 'account_data'-Abschnitt")

  if not isinstance(data.get("account_data"), list):
    raise HTTPException(status_code=400, detail="'account_data' muss eine Liste sein")

  steps = [AccountsStep()]
  service = ImportService(pool_manager, session_id, steps)
  success = service.run(data)

  count = len(data.get("account_data", []))
  if success:
    return {"status": "success", "imported": count, "message": f"{count} Konten importiert."}
  return {"status": "warning", "imported": count, "message": "Import abgeschlossen mit Warnungen."}


@router.get("/income")
@handle_db_errors("fetch account income")
async def get_account_income(
    year: int = Query(..., ge=1900, le=3000, description="Year for income data"),
    account: str = Query(..., description="Account name"),
    cursor = Depends(get_db_cursor_with_auth)
):
    """
    Get income (Haben) breakdown by category for a specific account and year.
    Blends actual transactions (past/today) with planning entries (future).
    """
    repo = AccountRepository(cursor)
    return repo.get_account_income(year, account)


@router.get("/summary")
@handle_db_errors("fetch account summary")
async def get_account_summary(
    year: int = Query(..., ge=1900, le=3000, description="Year for summary data"),
    account: str = Query(..., description="Account name"),
    cursor = Depends(get_db_cursor_with_auth)
):
    """
    Get monthly summary rows for a specific account and year:
    - Row 1: Haben (sum of positive amounts)
    - Row 2: Soll (sum of negative amounts)
    - Row 3: Gesamt (net sum of all amounts)
    Blends actual transactions (past/today) with planning entries (future).
    """
    repo = AccountRepository(cursor)
    return repo.get_account_summary(year, account)

@router.get("/expenses")
@handle_db_errors("fetch account expenses")
async def get_account_expenses(
    year: int = Query(..., ge=1900, le=3000, description="Year for expense data"),
    account: str = Query(..., description="Account name"),
    cursor = Depends(get_db_cursor_with_auth)
):
    """
    Get expenses (Soll) breakdown by category for a specific account and year.
    Blends actual transactions (past/today) with planning entries (future).
    """
    repo = AccountRepository(cursor)
    return repo.get_account_expenses(year, account)


@router.get("/all-giro/income")
@handle_db_errors("fetch all giro income")
async def get_all_giro_income(
    year: int = Query(..., ge=1900, le=3000, description="Year for income data"),
    cursor = Depends(get_db_cursor_with_auth)
):
    """
    Get aggregated income (Haben) breakdown by category for all Girokonto accounts and year.
    Blends actual transactions (past/today) with planning entries (future).
    """
    repo = AccountRepository(cursor)
    return repo.get_all_giro_income(year)


@router.get("/all-giro/expenses")
@handle_db_errors("fetch all giro expenses")
async def get_all_giro_expenses(
    year: int = Query(..., ge=1900, le=3000, description="Year for expense data"),
    cursor = Depends(get_db_cursor_with_auth)
):
    """
    Get aggregated expenses (Soll) breakdown by category for all Girokonto accounts and year.
    Blends actual transactions (past/today) with planning entries (future).
    """
    repo = AccountRepository(cursor)
    return repo.get_all_giro_expense(year)


@router.get("/all-giro/summary")
@handle_db_errors("fetch all giro summary")
async def get_all_giro_summary(
    year: int = Query(..., ge=1900, le=3000, description="Year for summary data"),
    cursor = Depends(get_db_cursor_with_auth)
):
    """
    Get monthly summary rows for all Girokonto accounts and year:
    - Row 1: Haben (sum of positive amounts)
    - Row 2: Soll (sum of negative amounts)
    - Row 3: Gesamt (net sum of all amounts)
    Blends actual transactions (past/today) with planning entries (future).
    """
    repo = AccountRepository(cursor)
    return repo.get_all_giro_summary(year)


@router.get("/all-loans/income")
@handle_db_errors("fetch all loans income")
async def get_all_loans_income(
    year: int = Query(..., ge=1900, le=3000, description="Year for income data"),
    cursor = Depends(get_db_cursor_with_auth)
):
    """
    Get aggregated income (Haben) breakdown by category for all Darlehen accounts and year.
    Blends actual transactions (past/today) with planning entries (future).
    """
    repo = AccountRepository(cursor)
    return repo.get_all_loans_income(year)


@router.get("/all-loans/expenses")
@handle_db_errors("fetch all loans expenses")
async def get_all_loans_expenses(
    year: int = Query(..., ge=1900, le=3000, description="Year for expense data"),
    cursor = Depends(get_db_cursor_with_auth)
):
    """
    Get aggregated expenses (Soll) breakdown by category for all Darlehen accounts and year.
    Blends actual transactions (past/today) with planning entries (future).
    """
    repo = AccountRepository(cursor)
    return repo.get_all_loans_expense(year)


@router.get("/all-loans/summary")
@handle_db_errors("fetch all loans summary")
async def get_all_loans_summary(
    year: int = Query(..., ge=1900, le=3000, description="Year for summary data"),
    cursor = Depends(get_db_cursor_with_auth)
):
    """
    Get aggregated summary (Haben, Soll, Gesamt) for all Darlehen accounts and year.
    Blends actual transactions (past/today) with planning entries (future).
    """
    repo = AccountRepository(cursor)
    return repo.get_all_loans_summary(year)


@router.get("/all-accounts/income")
@handle_db_errors("fetch all accounts income")
async def get_all_accounts_income(
    year: int = Query(..., ge=1900, le=3000, description="Year for income data"),
    cursor = Depends(get_db_cursor_with_auth)
):
    """
    Get aggregated income (Haben) breakdown by category for all Girokonto and Darlehen accounts and year.
    Blends actual transactions (past/today) with planning entries (future).
    """
    repo = AccountRepository(cursor)
    return repo.get_all_accounts_income(year)


@router.get("/all-accounts/expenses")
@handle_db_errors("fetch all accounts expenses")
async def get_all_accounts_expenses(
    year: int = Query(..., ge=1900, le=3000, description="Year for expense data"),
    cursor = Depends(get_db_cursor_with_auth)
):
    """
    Get aggregated expenses (Soll) breakdown by category for all Girokonto and Darlehen accounts and year.
    Blends actual transactions (past/today) with planning entries (future).
    """
    repo = AccountRepository(cursor)
    return repo.get_all_accounts_expense(year)


@router.get("/all-accounts/summary")
@handle_db_errors("fetch all accounts summary")
async def get_all_accounts_summary(
    year: int = Query(..., ge=1900, le=3000, description="Year for summary data"),
    cursor = Depends(get_db_cursor_with_auth)
):
    """
    Get aggregated summary (Haben, Soll, Gesamt) for all Girokonto and Darlehen accounts and year.
    Blends actual transactions (past/today) with planning entries (future).
    """
    repo = AccountRepository(cursor)
    return repo.get_all_accounts_summary(year)


@router.get("/girokonto/list")
@handle_db_errors("fetch account list")
async def get_account_list(
    cursor = Depends(get_db_cursor_with_auth)
):
    """
    Get list of all Girokonto accounts (matching Grafana query).
    """
    repo = AccountRepository(cursor)
    return repo.get_account_list('Girokonto')


# ==================== Account Management Endpoints ====================
@router.get("/list")
@handle_db_errors("fetch accounts for management")
async def get_accounts_list(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=1000),
    search: str = Query("", description="Search by name or IBAN"),
    cursor = Depends(get_db_cursor_with_auth)
):
    """
    Get paginated list of all accounts with their details for management.
    """
    repo = AccountRepository(cursor)

    search_pattern = f"%{search}%" if search else "%"
    
    # Get total count
    total = repo.get_count_accounts(search_pattern)
    
    # Get paginated data
    rows = repo.get_accounts_paginated(page, page_size, search_pattern)
    
    accounts = []
    for row in rows:
        accounts.append({
            "id": row[0],
            "name": row[1],
            "iban_accountNumber": row[2],
            "bic_market": row[3],
            "startAmount": float(row[4]),
            "dateStart": row[5].isoformat() if row[5] else None,
            "dateEnd": row[6].isoformat() if row[6] else None,
            "type": row[7],
            "type_name": row[8],
            "clearingAccount": row[9]
        })
    
    return {
        "accounts": accounts,
        "page": page,
        "page_size": page_size,
        "total": total
    }


@router.get("/types/list")
@handle_db_errors("fetch account types")
async def get_account_types(cursor = Depends(get_db_cursor_with_auth)):
    """
    Get list of all account types.
    """
    repo = AccountRepository(cursor)
    return repo.get_account_types()


@router.get("/formats/list")
@handle_db_errors("fetch import formats")
async def get_import_formats(cursor = Depends(get_db_cursor_with_auth)):
    """
    Get list of all import formats.
    """
    repo = AccountRepository(cursor)
    return repo.get_import_formats()


@router.get("/{account_id}")
@handle_db_errors("fetch account details")
async def get_account_detail(
    account_id: int = Path(..., gt=0),
    cursor = Depends(get_db_cursor_with_auth)
):
    """
    Get full details of a specific account including import settings.
    """
    # Get account info
    repo = AccountRepository(cursor)
    account_row = repo.get_account_by_id(account_id)
    
    if not account_row:
        raise HTTPException(status_code=404, detail="Konto nicht gefunden")
    
    # Get import settings
    repo = AccountRepository(cursor)
    import_row = repo.get_import_settings(account_id)
    
    return {
        "id": account_row[0],
        "name": account_row[1],
        "iban_accountNumber": account_row[2],
        "bic_market": account_row[3],
        "startAmount": float(account_row[4]),
        "dateStart": account_row[5].isoformat() if account_row[5] else None,
        "dateEnd": account_row[6].isoformat() if account_row[6] else None,
        "type": account_row[7],
        "clearingAccount": account_row[8],
        "importFormat": import_row[0] if import_row else None,
        "importPath": import_row[1] if import_row else None
    }


@router.put("/{account_id}")
@handle_db_errors("update account")
async def update_account(
    account_id: int = Path(..., gt=0),
    account_data: AccountData = None,
    connection = Depends(get_db_connection_with_auth)
):
    """
    Update account details and import settings.
    """
    if not account_data:
        raise HTTPException(status_code=400, detail="Keine Daten übergeben")
    
    repo = AccountRepository(connection.cursor(buffered=True))
    cursor = connection.cursor(buffered=True)
    try:
        # Update main account table
        repo.update_account(
            account_data.name,
            account_data.iban_accountNumber,
            account_data.bic_market,
            account_data.type,
            account_data.startAmount,
            account_data.dateStart if account_data.dateStart else None,
            account_data.dateEnd if account_data.dateEnd else None,
            account_data.clearingAccount,
            account_id
        )
            
        # Update or create import path
        if account_data.importPath and account_data.importFormat:
            existing = repo.get_import_path_by_account_id(account_id)
                    
            if existing:
                repo.update_import_path(
                    account_data.importPath,
                    account_data.importFormat,
                    account_id
                )
            else:
                repo.insert_import_path(
                    account_data.importPath,
                    account_data.importFormat,
                    account_id
                )
            
        safe_commit(connection)
            
        # finding: Here should be also 'safe_rollback' in case of errors during commit.

        # Return updated account
        return await get_account_detail(account_id, cursor)
    finally:
        try:
            cursor.close()
        except Exception:
            pass


@router.delete("/{account_id}")
@handle_db_errors("delete account")
async def delete_account(
    account_id: int = Path(..., gt=0),
    connection = Depends(get_db_connection_with_auth)
):
    """
    Delete an account and related import paths.
    """
    repo = AccountRepository(connection.cursor(buffered=True))
    try:
        # Delete import paths first
        repo.delete_import_path_by_account_id(account_id)
            
        # Delete account
        repo.delete_account_by_account_id(account_id)
            
        safe_commit(connection)
            
        return {"message": "Konto erfolgreich gelöscht"}
    finally:
        try:
            repo.cursor.close()
        except Exception:
            pass



