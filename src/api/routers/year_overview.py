"""
Year overview API router - exposes account balances at the start of each month for a given year.
"""

from fastapi import APIRouter, Depends, Query
from mysql.connector import OperationalError
from api.dependencies import get_db_cursor
from typing import Tuple, List
from api.error_handling import handle_db_errors

router = APIRouter(prefix="/year-overview", tags=["year-overview"])


def _execute_fetchall_with_retry(cursor, query: str, params: Tuple, retries: int = 1) -> Tuple[List[tuple], list]:
  """Execute query and fetchall with one reconnect+retry on OperationalError 2013."""
  try:
    cursor.execute(query, params)
    rows = cursor.fetchall()
    return rows, cursor.description
  except OperationalError as e:
    errno = getattr(e, 'errno', None)
    if errno == 2013 and retries > 0:
      conn = getattr(cursor, '_connection', None) or getattr(cursor, 'connection', None)
      try:
        if conn:
          conn.reconnect(attempts=1, delay=0)
          new_cursor = conn.cursor(buffered=True)
          try:
            new_cursor.execute("SET SESSION net_read_timeout=120")
            new_cursor.execute("SET SESSION net_write_timeout=120")
            new_cursor.execute("SET SESSION max_execution_time=120000")
          except Exception:
            pass
          new_cursor.execute(query, params)
          rows = new_cursor.fetchall()
          description = new_cursor.description
          try:
            new_cursor.close()
          except Exception:
            pass
          return rows, description
      except Exception:
        # Fallback: Fehler erneut werfen
        pass
    # Andere Fehler oder kein Retry mehr
    raise


@router.get("/account-balances")
@handle_db_errors("fetch account balances")
async def get_account_balances(
  year: int = Query(..., ge=1900, le=3000, description="Year for which balances are requested"),
  cursor = Depends(get_db_cursor)
):
    """Return monthly starting balances per account for the selected year."""
    month_thresholds = [year * 100 + month for month in range(1, 13)]
    year_end_threshold = year * 100 + 12

    query = """
        SELECT
          tbl_account.name AS Konto,
          SUM(CASE WHEN EXTRACT(YEAR_MONTH FROM view_balances.dateValue) < %s THEN view_balances.amountSum ELSE 0 END) + tbl_account.startAmount AS Januar,
          SUM(CASE WHEN EXTRACT(YEAR_MONTH FROM view_balances.dateValue) < %s THEN view_balances.amountSum ELSE 0 END) + tbl_account.startAmount AS Februar,
          SUM(CASE WHEN EXTRACT(YEAR_MONTH FROM view_balances.dateValue) < %s THEN view_balances.amountSum ELSE 0 END) + tbl_account.startAmount AS März,
          SUM(CASE WHEN EXTRACT(YEAR_MONTH FROM view_balances.dateValue) < %s THEN view_balances.amountSum ELSE 0 END) + tbl_account.startAmount AS April,
          SUM(CASE WHEN EXTRACT(YEAR_MONTH FROM view_balances.dateValue) < %s THEN view_balances.amountSum ELSE 0 END) + tbl_account.startAmount AS Mai,
          SUM(CASE WHEN EXTRACT(YEAR_MONTH FROM view_balances.dateValue) < %s THEN view_balances.amountSum ELSE 0 END) + tbl_account.startAmount AS Juni,
          SUM(CASE WHEN EXTRACT(YEAR_MONTH FROM view_balances.dateValue) < %s THEN view_balances.amountSum ELSE 0 END) + tbl_account.startAmount AS Juli,
          SUM(CASE WHEN EXTRACT(YEAR_MONTH FROM view_balances.dateValue) < %s THEN view_balances.amountSum ELSE 0 END) + tbl_account.startAmount AS August,
          SUM(CASE WHEN EXTRACT(YEAR_MONTH FROM view_balances.dateValue) < %s THEN view_balances.amountSum ELSE 0 END) + tbl_account.startAmount AS September,
          SUM(CASE WHEN EXTRACT(YEAR_MONTH FROM view_balances.dateValue) < %s THEN view_balances.amountSum ELSE 0 END) + tbl_account.startAmount AS Oktober,
          SUM(CASE WHEN EXTRACT(YEAR_MONTH FROM view_balances.dateValue) < %s THEN view_balances.amountSum ELSE 0 END) + tbl_account.startAmount AS November,
          SUM(CASE WHEN EXTRACT(YEAR_MONTH FROM view_balances.dateValue) < %s THEN view_balances.amountSum ELSE 0 END) + tbl_account.startAmount AS Dezember,
          SUM(CASE WHEN EXTRACT(YEAR_MONTH FROM view_balances.dateValue) <= %s THEN view_balances.amountSum ELSE 0 END) + tbl_account.startAmount AS Jahresbilanz
        FROM view_balances
          RIGHT JOIN tbl_account ON view_balances.accountID = tbl_account.id
        WHERE YEAR(tbl_account.dateStart) <= %s
          AND (YEAR(tbl_account.dateEnd) >= %s OR ISNULL(tbl_account.dateEnd))
          AND tbl_account.type IN (1)
        GROUP BY Konto
        ORDER BY Konto ASC
    """

    params = (
        *month_thresholds,
        year_end_threshold,
        year,
        year,
    )

    rows, description = _execute_fetchall_with_retry(cursor, query, params, retries=1)
    columns = [col[0] for col in description]
    data = [dict(zip(columns, row)) for row in rows]

    return {"year": year, "rows": data}


@router.get("/account-balances-monthly")
@handle_db_errors("fetch monthly account balances")
async def get_account_balances_monthly(
  year: int = Query(..., ge=1900, le=3000, description="Year for which monthly balances are requested"),
  cursor = Depends(get_db_cursor)
):
    """Return monthly delta balances per account for the selected year (Grafana 'Bilanz')."""
    month_equals = [year * 100 + month for month in range(1, 13)]

    query = """
        SELECT
          tbl_account.name AS Konto,
          SUM(CASE WHEN EXTRACT(YEAR_MONTH FROM view_balances.dateValue) = %s THEN view_balances.amountSum ELSE 0 END) AS Januar,
          SUM(CASE WHEN EXTRACT(YEAR_MONTH FROM view_balances.dateValue) = %s THEN view_balances.amountSum ELSE 0 END) AS Februar,
          SUM(CASE WHEN EXTRACT(YEAR_MONTH FROM view_balances.dateValue) = %s THEN view_balances.amountSum ELSE 0 END) AS März,
          SUM(CASE WHEN EXTRACT(YEAR_MONTH FROM view_balances.dateValue) = %s THEN view_balances.amountSum ELSE 0 END) AS April,
          SUM(CASE WHEN EXTRACT(YEAR_MONTH FROM view_balances.dateValue) = %s THEN view_balances.amountSum ELSE 0 END) AS Mai,
          SUM(CASE WHEN EXTRACT(YEAR_MONTH FROM view_balances.dateValue) = %s THEN view_balances.amountSum ELSE 0 END) AS Juni,
          SUM(CASE WHEN EXTRACT(YEAR_MONTH FROM view_balances.dateValue) = %s THEN view_balances.amountSum ELSE 0 END) AS Juli,
          SUM(CASE WHEN EXTRACT(YEAR_MONTH FROM view_balances.dateValue) = %s THEN view_balances.amountSum ELSE 0 END) AS August,
          SUM(CASE WHEN EXTRACT(YEAR_MONTH FROM view_balances.dateValue) = %s THEN view_balances.amountSum ELSE 0 END) AS September,
          SUM(CASE WHEN EXTRACT(YEAR_MONTH FROM view_balances.dateValue) = %s THEN view_balances.amountSum ELSE 0 END) AS Oktober,
          SUM(CASE WHEN EXTRACT(YEAR_MONTH FROM view_balances.dateValue) = %s THEN view_balances.amountSum ELSE 0 END) AS November,
          SUM(CASE WHEN EXTRACT(YEAR_MONTH FROM view_balances.dateValue) = %s THEN view_balances.amountSum ELSE 0 END) AS Dezember,
          SUM(CASE WHEN YEAR(view_balances.dateValue) = %s THEN view_balances.amountSum ELSE 0 END) AS Jahresbilanz
        FROM view_balances
          RIGHT JOIN tbl_account ON view_balances.accountID = tbl_account.id
        WHERE YEAR(tbl_account.dateStart) <= %s
          AND (YEAR(tbl_account.dateEnd) >= %s OR ISNULL(tbl_account.dateEnd))
          AND tbl_account.type IN (1)
        GROUP BY Konto
        ORDER BY Konto ASC
    """

    params = (
        *month_equals,
        year,
        year,
        year,
    )

    rows, description = _execute_fetchall_with_retry(cursor, query, params, retries=1)
    columns = [col[0] for col in description]
    data = [dict(zip(columns, row)) for row in rows]

    return {"year": year, "rows": data}


@router.get("/loans")
@handle_db_errors("fetch loans overview")
async def get_loans(
  year: int = Query(..., ge=1900, le=3000, description="Year for which loans overview is requested"),
  cursor = Depends(get_db_cursor)
):
    """Return loan balances per month for the selected year (Darlehen).
    
    Columns are aligned to the existing tables: Konto, Januar..Dezember, Jahresbilanz.
    Based on Grafana 'Darlehen' query without 'Zinsen' column.
    """
    month_thresholds = [year * 100 + month for month in range(1, 13)]
    year_end_threshold = year * 100 + 12

    query = """
        WITH
          loc_monthlyBalance AS (
            SELECT
              SUM(tbl_accountingEntry.amount) AS amountSum,
              tbl_accountingEntry.category AS categoryID,
              tbl_transaction.account AS accountID,
              tbl_transaction.dateValue AS dateValue
            FROM tbl_accountingEntry
              LEFT JOIN tbl_transaction ON tbl_accountingEntry.transaction = tbl_transaction.id
              INNER JOIN tbl_loan ON tbl_transaction.account = tbl_loan.account
              LEFT JOIN tbl_account ON tbl_transaction.account = tbl_account.id
              LEFT JOIN tbl_loanSumExclude ON tbl_loan.id = tbl_loanSumExclude.loanId AND tbl_loanSumExclude.category = tbl_accountingEntry.category
            WHERE tbl_loanSumExclude.id IS NULL
            GROUP BY categoryID, accountID, YEAR(tbl_transaction.dateValue), MONTH(tbl_transaction.dateValue)
            ORDER BY accountID ASC, dateValue DESC),
          loc_monthlyIntrest AS (
            SELECT
              SUM(tbl_accountingEntry.amount) AS amountSum,
              tbl_accountingEntry.category AS categoryID,
              tbl_transaction.account AS accountID,
              tbl_transaction.dateValue AS dateValue
            FROM tbl_accountingEntry
              LEFT JOIN tbl_transaction ON tbl_accountingEntry.transaction = tbl_transaction.id
              INNER JOIN tbl_loan ON tbl_transaction.account = tbl_loan.account
              LEFT JOIN tbl_account ON tbl_transaction.account = tbl_account.id
              LEFT JOIN tbl_loan loan2 ON tbl_account.id = loan2.account AND loan2.categoryIntrest = tbl_accountingEntry.category
            WHERE loan2.categoryIntrest IS NOT NULL AND YEAR(tbl_transaction.dateValue) = %s
            GROUP BY categoryID, accountID, YEAR(tbl_transaction.dateValue)
            ORDER BY accountID ASC, dateValue DESC)
        SELECT
          tbl_account.name AS Konto,
          SUM(CASE WHEN EXTRACT(YEAR_MONTH FROM loc_monthlyBalance.dateValue) <  %s THEN loc_monthlyBalance.amountSum ELSE 0 END) + tbl_account.startAmount AS Januar,
          SUM(CASE WHEN EXTRACT(YEAR_MONTH FROM loc_monthlyBalance.dateValue) <  %s THEN loc_monthlyBalance.amountSum ELSE 0 END) + tbl_account.startAmount AS Februar,
          SUM(CASE WHEN EXTRACT(YEAR_MONTH FROM loc_monthlyBalance.dateValue) <  %s THEN loc_monthlyBalance.amountSum ELSE 0 END) + tbl_account.startAmount AS März,
          SUM(CASE WHEN EXTRACT(YEAR_MONTH FROM loc_monthlyBalance.dateValue) <  %s THEN loc_monthlyBalance.amountSum ELSE 0 END) + tbl_account.startAmount AS April,
          SUM(CASE WHEN EXTRACT(YEAR_MONTH FROM loc_monthlyBalance.dateValue) <  %s THEN loc_monthlyBalance.amountSum ELSE 0 END) + tbl_account.startAmount AS Mai,
          SUM(CASE WHEN EXTRACT(YEAR_MONTH FROM loc_monthlyBalance.dateValue) <  %s THEN loc_monthlyBalance.amountSum ELSE 0 END) + tbl_account.startAmount AS Juni,
          SUM(CASE WHEN EXTRACT(YEAR_MONTH FROM loc_monthlyBalance.dateValue) <  %s THEN loc_monthlyBalance.amountSum ELSE 0 END) + tbl_account.startAmount AS Juli,
          SUM(CASE WHEN EXTRACT(YEAR_MONTH FROM loc_monthlyBalance.dateValue) <  %s THEN loc_monthlyBalance.amountSum ELSE 0 END) + tbl_account.startAmount AS August,
          SUM(CASE WHEN EXTRACT(YEAR_MONTH FROM loc_monthlyBalance.dateValue) <  %s THEN loc_monthlyBalance.amountSum ELSE 0 END) + tbl_account.startAmount AS September,
          SUM(CASE WHEN EXTRACT(YEAR_MONTH FROM loc_monthlyBalance.dateValue) <  %s THEN loc_monthlyBalance.amountSum ELSE 0 END) + tbl_account.startAmount AS Oktober,
          SUM(CASE WHEN EXTRACT(YEAR_MONTH FROM loc_monthlyBalance.dateValue) <  %s THEN loc_monthlyBalance.amountSum ELSE 0 END) + tbl_account.startAmount AS November,
          SUM(CASE WHEN EXTRACT(YEAR_MONTH FROM loc_monthlyBalance.dateValue) <  %s THEN loc_monthlyBalance.amountSum ELSE 0 END) + tbl_account.startAmount AS Dezember,
          SUM(CASE WHEN EXTRACT(YEAR_MONTH FROM loc_monthlyBalance.dateValue) <= %s THEN loc_monthlyBalance.amountSum ELSE 0 END) + tbl_account.startAmount AS Jahresbilanz
        FROM tbl_loan, ((tbl_account
          LEFT JOIN loc_monthlyBalance ON tbl_account.id = loc_monthlyBalance.accountID)
          LEFT JOIN loc_monthlyIntrest ON loc_monthlyIntrest.accountID = loc_monthlyBalance.accountID)
        WHERE (YEAR(loc_monthlyIntrest.dateValue) = %s OR YEAR(loc_monthlyIntrest.dateValue) IS NULL) AND
          YEAR(tbl_account.dateStart) <= %s AND
          (YEAR(tbl_account.dateEnd) >= %s OR ISNULL(tbl_account.dateEnd)) AND
          tbl_account.id IN(tbl_loan.account)
        GROUP BY Konto
        ORDER BY Konto ASC
    """

    params = (
        year,  # for loc_monthlyIntrest YEAR(...)=year
        *month_thresholds,
        year_end_threshold,
        year,  # WHERE YEAR(loc_monthlyIntrest.dateValue) = year
        year,  # YEAR(tbl_account.dateStart) <= year
        year,  # YEAR(tbl_account.dateEnd) >= year
    )

    rows, description = _execute_fetchall_with_retry(cursor, query, params, retries=1)
    columns = [col[0] for col in description]
    data = [dict(zip(columns, row)) for row in rows]

    return {"year": year, "rows": data}
