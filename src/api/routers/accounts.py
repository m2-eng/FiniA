"""
Account details API router - provides income/expense breakdown per account
"""

from fastapi import APIRouter, Depends, Query
from api.dependencies import get_db_cursor
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


@router.get("/list")
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
