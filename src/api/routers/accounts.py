"""
Account details API router - provides income/expense breakdown per account
"""

from fastapi import APIRouter, Depends, Query, HTTPException, Path
from typing import Optional
from pydantic import BaseModel
from api.dependencies import get_db_cursor, get_db_connection
from api.error_handling import handle_db_errors

router = APIRouter(prefix="/accounts", tags=["accounts"])


@router.get("/income")
@handle_db_errors("fetch account income")
async def get_account_income(
    year: int = Query(..., ge=1900, le=3000, description="Year for income data"),
    account: str = Query(..., description="Account name"),
    cursor = Depends(get_db_cursor)
):
    """
    Get income (Haben) breakdown by category for a specific account and year.
    Returns monthly amounts and total per category.
    """
    query = """
        SELECT
          view_categoryFullname.fullname AS Kategorie,
          SUM(CASE WHEN MONTH(view_balances.dateValue) = 1 THEN view_balances.amountSum ELSE 0 END) AS Januar,
          SUM(CASE WHEN MONTH(view_balances.dateValue) = 2 THEN view_balances.amountSum ELSE 0 END) AS Februar,
          SUM(CASE WHEN MONTH(view_balances.dateValue) = 3 THEN view_balances.amountSum ELSE 0 END) AS März,
          SUM(CASE WHEN MONTH(view_balances.dateValue) = 4 THEN view_balances.amountSum ELSE 0 END) AS April,
          SUM(CASE WHEN MONTH(view_balances.dateValue) = 5 THEN view_balances.amountSum ELSE 0 END) AS Mai,
          SUM(CASE WHEN MONTH(view_balances.dateValue) = 6 THEN view_balances.amountSum ELSE 0 END) AS Juni,
          SUM(CASE WHEN MONTH(view_balances.dateValue) = 7 THEN view_balances.amountSum ELSE 0 END) AS Juli,
          SUM(CASE WHEN MONTH(view_balances.dateValue) = 8 THEN view_balances.amountSum ELSE 0 END) AS August,
          SUM(CASE WHEN MONTH(view_balances.dateValue) = 9 THEN view_balances.amountSum ELSE 0 END) AS September,
          SUM(CASE WHEN MONTH(view_balances.dateValue) = 10 THEN view_balances.amountSum ELSE 0 END) AS Oktober,
          SUM(CASE WHEN MONTH(view_balances.dateValue) = 11 THEN view_balances.amountSum ELSE 0 END) AS November,
          SUM(CASE WHEN MONTH(view_balances.dateValue) = 12 THEN view_balances.amountSum ELSE 0 END) AS Dezember,
          SUM(CASE WHEN YEAR(view_balances.dateValue) = %s THEN amountSum ELSE 0 END) AS Gesamt
        FROM view_balances
          LEFT JOIN tbl_account ON tbl_account.id = view_balances.accountID
          LEFT JOIN view_categoryFullname ON view_categoryFullname.id = view_balances.categoryID
        WHERE YEAR(view_balances.dateValue) = %s AND tbl_account.name = %s AND amountSum >= 0
        GROUP BY view_categoryFullname.fullname
        ORDER BY view_categoryFullname.fullname ASC
    """
    
    cursor.execute(query, (year, year, account))
    rows = cursor.fetchall()
    
    columns = [col[0] for col in cursor.description]
    data = [dict(zip(columns, row)) for row in rows]
    
    return {"year": year, "account": account, "rows": data}


@router.get("/summary")
@handle_db_errors("fetch account summary")
async def get_account_summary(
    year: int = Query(..., ge=1900, le=3000, description="Year for summary data"),
    account: str = Query(..., description="Account name"),
    cursor = Depends(get_db_cursor)
):
    """
    Get monthly summary rows for a specific account and year:
    - Row 1: Haben (sum of positive amounts)
    - Row 2: Soll (sum of negative amounts)
    - Row 3: Gesamt (net sum of all amounts)
    Returns rows with columns: Kategorie, Januar..Dezember, Gesamt
    """
    query = """
        SELECT 'Haben' AS Kategorie,
          SUM(CASE WHEN MONTH(view_balances.dateValue) = 1 THEN IF(amountSum >= 0, amountSum, 0) ELSE 0 END) AS Januar,
          SUM(CASE WHEN MONTH(view_balances.dateValue) = 2 THEN IF(amountSum >= 0, amountSum, 0) ELSE 0 END) AS Februar,
          SUM(CASE WHEN MONTH(view_balances.dateValue) = 3 THEN IF(amountSum >= 0, amountSum, 0) ELSE 0 END) AS März,
          SUM(CASE WHEN MONTH(view_balances.dateValue) = 4 THEN IF(amountSum >= 0, amountSum, 0) ELSE 0 END) AS April,
          SUM(CASE WHEN MONTH(view_balances.dateValue) = 5 THEN IF(amountSum >= 0, amountSum, 0) ELSE 0 END) AS Mai,
          SUM(CASE WHEN MONTH(view_balances.dateValue) = 6 THEN IF(amountSum >= 0, amountSum, 0) ELSE 0 END) AS Juni,
          SUM(CASE WHEN MONTH(view_balances.dateValue) = 7 THEN IF(amountSum >= 0, amountSum, 0) ELSE 0 END) AS Juli,
          SUM(CASE WHEN MONTH(view_balances.dateValue) = 8 THEN IF(amountSum >= 0, amountSum, 0) ELSE 0 END) AS August,
          SUM(CASE WHEN MONTH(view_balances.dateValue) = 9 THEN IF(amountSum >= 0, amountSum, 0) ELSE 0 END) AS September,
          SUM(CASE WHEN MONTH(view_balances.dateValue) = 10 THEN IF(amountSum >= 0, amountSum, 0) ELSE 0 END) AS Oktober,
          SUM(CASE WHEN MONTH(view_balances.dateValue) = 11 THEN IF(amountSum >= 0, amountSum, 0) ELSE 0 END) AS November,
          SUM(CASE WHEN MONTH(view_balances.dateValue) = 12 THEN IF(amountSum >= 0, amountSum, 0) ELSE 0 END) AS Dezember,
          SUM(CASE WHEN YEAR(view_balances.dateValue) = %s THEN IF(amountSum >= 0, amountSum, 0) ELSE 0 END) AS Gesamt
        FROM view_balances
          LEFT JOIN tbl_account ON tbl_account.id = view_balances.accountID
        WHERE YEAR(view_balances.dateValue) = %s AND tbl_account.name = %s
        UNION ALL
        SELECT 'Soll' AS Kategorie,
          SUM(CASE WHEN MONTH(view_balances.dateValue) = 1 THEN IF(amountSum < 0, amountSum, 0) ELSE 0 END) AS Januar,
          SUM(CASE WHEN MONTH(view_balances.dateValue) = 2 THEN IF(amountSum < 0, amountSum, 0) ELSE 0 END) AS Februar,
          SUM(CASE WHEN MONTH(view_balances.dateValue) = 3 THEN IF(amountSum < 0, amountSum, 0) ELSE 0 END) AS März,
          SUM(CASE WHEN MONTH(view_balances.dateValue) = 4 THEN IF(amountSum < 0, amountSum, 0) ELSE 0 END) AS April,
          SUM(CASE WHEN MONTH(view_balances.dateValue) = 5 THEN IF(amountSum < 0, amountSum, 0) ELSE 0 END) AS Mai,
          SUM(CASE WHEN MONTH(view_balances.dateValue) = 6 THEN IF(amountSum < 0, amountSum, 0) ELSE 0 END) AS Juni,
          SUM(CASE WHEN MONTH(view_balances.dateValue) = 7 THEN IF(amountSum < 0, amountSum, 0) ELSE 0 END) AS Juli,
          SUM(CASE WHEN MONTH(view_balances.dateValue) = 8 THEN IF(amountSum < 0, amountSum, 0) ELSE 0 END) AS August,
          SUM(CASE WHEN MONTH(view_balances.dateValue) = 9 THEN IF(amountSum < 0, amountSum, 0) ELSE 0 END) AS September,
          SUM(CASE WHEN MONTH(view_balances.dateValue) = 10 THEN IF(amountSum < 0, amountSum, 0) ELSE 0 END) AS Oktober,
          SUM(CASE WHEN MONTH(view_balances.dateValue) = 11 THEN IF(amountSum < 0, amountSum, 0) ELSE 0 END) AS November,
          SUM(CASE WHEN MONTH(view_balances.dateValue) = 12 THEN IF(amountSum < 0, amountSum, 0) ELSE 0 END) AS Dezember,
          SUM(CASE WHEN YEAR(view_balances.dateValue) = %s THEN IF(amountSum < 0, amountSum, 0) ELSE 0 END) AS Gesamt
        FROM view_balances
          LEFT JOIN tbl_account ON tbl_account.id = view_balances.accountID
        WHERE YEAR(view_balances.dateValue) = %s AND tbl_account.name = %s
        UNION ALL
        SELECT 'Gesamt' AS Kategorie,
          SUM(CASE WHEN MONTH(view_balances.dateValue) = 1 THEN amountSum ELSE 0 END) AS Januar,
          SUM(CASE WHEN MONTH(view_balances.dateValue) = 2 THEN amountSum ELSE 0 END) AS Februar,
          SUM(CASE WHEN MONTH(view_balances.dateValue) = 3 THEN amountSum ELSE 0 END) AS März,
          SUM(CASE WHEN MONTH(view_balances.dateValue) = 4 THEN amountSum ELSE 0 END) AS April,
          SUM(CASE WHEN MONTH(view_balances.dateValue) = 5 THEN amountSum ELSE 0 END) AS Mai,
          SUM(CASE WHEN MONTH(view_balances.dateValue) = 6 THEN amountSum ELSE 0 END) AS Juni,
          SUM(CASE WHEN MONTH(view_balances.dateValue) = 7 THEN amountSum ELSE 0 END) AS Juli,
          SUM(CASE WHEN MONTH(view_balances.dateValue) = 8 THEN amountSum ELSE 0 END) AS August,
          SUM(CASE WHEN MONTH(view_balances.dateValue) = 9 THEN amountSum ELSE 0 END) AS September,
          SUM(CASE WHEN MONTH(view_balances.dateValue) = 10 THEN amountSum ELSE 0 END) AS Oktober,
          SUM(CASE WHEN MONTH(view_balances.dateValue) = 11 THEN amountSum ELSE 0 END) AS November,
          SUM(CASE WHEN MONTH(view_balances.dateValue) = 12 THEN amountSum ELSE 0 END) AS Dezember,
          SUM(CASE WHEN YEAR(view_balances.dateValue) = %s THEN amountSum ELSE 0 END) AS Gesamt
        FROM view_balances
          LEFT JOIN tbl_account ON tbl_account.id = view_balances.accountID
        WHERE YEAR(view_balances.dateValue) = %s AND tbl_account.name = %s
    """

    params = (
        year, year, account,  # Haben
        year, year, account,  # Soll
        year, year, account   # Gesamt
    )

    cursor.execute(query, params)
    rows = cursor.fetchall()

    columns = [col[0] for col in cursor.description]
    data = [dict(zip(columns, row)) for row in rows]

    return {"year": year, "account": account, "rows": data}

@router.get("/expenses")
@handle_db_errors("fetch account expenses")
async def get_account_expenses(
    year: int = Query(..., ge=1900, le=3000, description="Year for expense data"),
    account: str = Query(..., description="Account name"),
    cursor = Depends(get_db_cursor)
):
    """
    Get expenses (Soll) breakdown by category for a specific account and year.
    Returns monthly amounts and total per category.
    """
    query = """
        SELECT
          view_categoryFullname.fullname AS Kategorie,
          SUM(CASE WHEN MONTH(view_balances.dateValue) = 1 THEN view_balances.amountSum ELSE 0 END) AS Januar,
          SUM(CASE WHEN MONTH(view_balances.dateValue) = 2 THEN view_balances.amountSum ELSE 0 END) AS Februar,
          SUM(CASE WHEN MONTH(view_balances.dateValue) = 3 THEN view_balances.amountSum ELSE 0 END) AS März,
          SUM(CASE WHEN MONTH(view_balances.dateValue) = 4 THEN view_balances.amountSum ELSE 0 END) AS April,
          SUM(CASE WHEN MONTH(view_balances.dateValue) = 5 THEN view_balances.amountSum ELSE 0 END) AS Mai,
          SUM(CASE WHEN MONTH(view_balances.dateValue) = 6 THEN view_balances.amountSum ELSE 0 END) AS Juni,
          SUM(CASE WHEN MONTH(view_balances.dateValue) = 7 THEN view_balances.amountSum ELSE 0 END) AS Juli,
          SUM(CASE WHEN MONTH(view_balances.dateValue) = 8 THEN view_balances.amountSum ELSE 0 END) AS August,
          SUM(CASE WHEN MONTH(view_balances.dateValue) = 9 THEN view_balances.amountSum ELSE 0 END) AS September,
          SUM(CASE WHEN MONTH(view_balances.dateValue) = 10 THEN view_balances.amountSum ELSE 0 END) AS Oktober,
          SUM(CASE WHEN MONTH(view_balances.dateValue) = 11 THEN view_balances.amountSum ELSE 0 END) AS November,
          SUM(CASE WHEN MONTH(view_balances.dateValue) = 12 THEN view_balances.amountSum ELSE 0 END) AS Dezember,
          SUM(CASE WHEN YEAR(view_balances.dateValue) = %s THEN amountSum ELSE 0 END) AS Gesamt
        FROM view_balances
          LEFT JOIN tbl_account ON tbl_account.id = view_balances.accountID
          LEFT JOIN view_categoryFullname ON view_categoryFullname.id = view_balances.categoryID
        WHERE YEAR(view_balances.dateValue) = %s AND tbl_account.name = %s AND amountSum < 0
        GROUP BY view_categoryFullname.fullname
        ORDER BY view_categoryFullname.fullname ASC
    """
    
    cursor.execute(query, (year, year, account))
    rows = cursor.fetchall()
    
    columns = [col[0] for col in cursor.description]
    data = [dict(zip(columns, row)) for row in rows]
    
    return {"year": year, "account": account, "rows": data}


@router.get("/girokonto/list")
@handle_db_errors("fetch account list")
async def get_account_list(cursor = Depends(get_db_cursor)):
   """
   Get list of all Girokonto accounts (matching Grafana query).
   """
   query = """
      SELECT
         tbl_account.name AS name
      FROM tbl_account
      LEFT JOIN tbl_accountType ON tbl_accountType.id = tbl_account.type
      WHERE tbl_accountType.type = %s
      ORDER BY name ASC
   """
    
   cursor.execute(query, ("Girokonto",))
   rows = cursor.fetchall()
    
   accounts = [row[0] for row in rows]
    
   return {"accounts": accounts}


# ==================== Account Management Endpoints ====================

class AccountData(BaseModel):
    name: str
    iban_accountNumber: str
    bic_market: str
    type: Optional[int] = None
    startAmount: float
    dateStart: str
    dateEnd: Optional[str] = None
    clearingAccount: Optional[int] = None
    importFormat: Optional[int] = None
    importPath: Optional[str] = None


@router.get("/list")
@handle_db_errors("fetch accounts for management")
async def get_accounts_list(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=1000),
    search: str = Query("", description="Search by name or IBAN"),
    cursor = Depends(get_db_cursor)
):
    """
    Get paginated list of all accounts with their details for management.
    """
    search_pattern = f"%{search}%" if search else "%"
    
    # Get total count
    count_query = """
        SELECT COUNT(DISTINCT tbl_account.id)
        FROM tbl_account
        LEFT JOIN tbl_accountType ON tbl_accountType.id = tbl_account.type
        WHERE tbl_account.name LIKE %s OR tbl_account.iban_accountNumber LIKE %s
    """
    cursor.execute(count_query, (search_pattern, search_pattern))
    total = cursor.fetchone()[0]
    
    # Get paginated data
    offset = (page - 1) * page_size
    query = """
        SELECT 
            tbl_account.id,
            tbl_account.name,
            tbl_account.iban_accountNumber,
            tbl_account.bic_market,
            tbl_account.startAmount,
            tbl_account.dateStart,
            tbl_account.dateEnd,
            tbl_account.type,
            tbl_accountType.type AS type_name,
            tbl_account.clearingAccount
        FROM tbl_account
        LEFT JOIN tbl_accountType ON tbl_accountType.id = tbl_account.type
        WHERE tbl_account.name LIKE %s OR tbl_account.iban_accountNumber LIKE %s
        ORDER BY tbl_account.name ASC
        LIMIT %s OFFSET %s
    """
    
    cursor.execute(query, (search_pattern, search_pattern, page_size, offset))
    rows = cursor.fetchall()
    
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
async def get_account_types(cursor = Depends(get_db_cursor)):
    """
    Get list of all account types.
    """
    query = "SELECT id, type FROM tbl_accountType ORDER BY type ASC"
    cursor.execute(query)
    rows = cursor.fetchall()
    
    types = [{"id": row[0], "type": row[1]} for row in rows]
    return {"types": types}


@router.get("/formats/list")
@handle_db_errors("fetch import formats")
async def get_import_formats(cursor = Depends(get_db_cursor)):
    """
    Get list of all import formats.
    """
    query = "SELECT id, type FROM tbl_accountImportFormat ORDER BY type ASC"
    cursor.execute(query)
    rows = cursor.fetchall()
    
    formats = [{"id": row[0], "type": row[1]} for row in rows]
    return {"formats": formats}


@router.get("/{account_id}")
@handle_db_errors("fetch account details")
async def get_account_detail(
    account_id: int = Path(..., gt=0),
    cursor = Depends(get_db_cursor)
):
    """
    Get full details of a specific account including import settings.
    """
    # Get account info
    account_query = """
        SELECT 
            tbl_account.id,
            tbl_account.name,
            tbl_account.iban_accountNumber,
            tbl_account.bic_market,
            tbl_account.startAmount,
            tbl_account.dateStart,
            tbl_account.dateEnd,
            tbl_account.type,
            tbl_account.clearingAccount
        FROM tbl_account
        WHERE tbl_account.id = %s
    """
    
    cursor.execute(account_query, (account_id,))
    account_row = cursor.fetchone()
    
    if not account_row:
        raise HTTPException(status_code=404, detail="Konto nicht gefunden")
    
    # Get import settings
    import_query = """
        SELECT 
            tbl_accountImportFormat.id,
            tbl_accountImportPath.path
        FROM tbl_accountImportPath
        LEFT JOIN tbl_accountImportFormat ON tbl_accountImportFormat.id = tbl_accountImportPath.importFormat
        WHERE tbl_accountImportPath.account = %s
        LIMIT 1
    """
    
    cursor.execute(import_query, (account_id,))
    import_row = cursor.fetchone()
    
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
    cursor = Depends(get_db_cursor),
    connection = Depends(get_db_connection)
):
    """
    Update account details and import settings.
    """
    if not account_data:
        raise HTTPException(status_code=400, detail="Keine Daten übergeben")
    
    # Update main account table
    update_query = """
        UPDATE tbl_account
        SET name = %s,
            iban_accountNumber = %s,
            bic_market = %s,
            type = %s,
            startAmount = %s,
            dateStart = %s,
            dateEnd = %s,
            clearingAccount = %s
        WHERE id = %s
    """
    
    cursor.execute(update_query, (
        account_data.name,
        account_data.iban_accountNumber,
        account_data.bic_market,
        account_data.type,
        account_data.startAmount,
        account_data.dateStart if account_data.dateStart else None,
        account_data.dateEnd if account_data.dateEnd else None,
        account_data.clearingAccount,
        account_id
    ))
    
    # Update or create import path
    if account_data.importPath and account_data.importFormat:
        check_query = "SELECT id FROM tbl_accountImportPath WHERE account = %s"
        cursor.execute(check_query, (account_id,))
        existing = cursor.fetchone()
        
        if existing:
            path_update_query = """
                UPDATE tbl_accountImportPath
                SET path = %s, importFormat = %s
                WHERE account = %s
            """
            cursor.execute(path_update_query, (
                account_data.importPath,
                account_data.importFormat,
                account_id
            ))
        else:
            path_insert_query = """
                INSERT INTO tbl_accountImportPath (dateImport, path, account, importFormat)
                VALUES (NOW(), %s, %s, %s)
            """
            cursor.execute(path_insert_query, (
                account_data.importPath,
                account_id,
                account_data.importFormat
            ))
    
    connection.commit()
    
    # Return updated account
    return await get_account_detail(account_id, cursor)


@router.delete("/{account_id}")
@handle_db_errors("delete account")
async def delete_account(
    account_id: int = Path(..., gt=0),
    cursor = Depends(get_db_cursor),
    connection = Depends(get_db_connection)
):
    """
    Delete an account and related import paths.
    """
    # Delete import paths first
    delete_paths_query = "DELETE FROM tbl_accountImportPath WHERE account = %s"
    cursor.execute(delete_paths_query, (account_id,))
    
    # Delete account
    delete_query = "DELETE FROM tbl_account WHERE id = %s"
    cursor.execute(delete_query, (account_id,))
    
    connection.commit()
    
    return {"message": "Konto erfolgreich gelöscht"}


