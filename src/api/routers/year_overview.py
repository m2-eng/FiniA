"""
Year overview API router - exposes account balances at the start of each month for a given year.
"""

from fastapi import APIRouter, Depends, Query
from mysql.connector import OperationalError
from api.dependencies import get_db_cursor_with_auth as get_db_cursor
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
    """Return monthly starting balances per account for the selected year.
    Includes future planning entries (tbl_planningEntry) only for dates after today.
    Real accounting entries (tbl_accountingEntry) are included only up to today.
    """
    from datetime import date
    today = date.today()
    month_thresholds = [year * 100 + month for month in range(1, 13)]
    year_end_threshold = year * 100 + 12

    # Use correlated subselects to avoid cartesian products when combining real and planned sums
    # finding: Use repository method instead of SQL command here. If no method exists, create one.
    query = """
        SELECT
          a.name AS Konto,
          (
            -- Januar (Stand zu Monatsbeginn): real bis heute + Planung nach heute, jeweils vor Monatsanfang
            COALESCE((SELECT SUM(ae.amount)
                      FROM tbl_transaction t2
                      LEFT JOIN tbl_accountingEntry ae ON ae.transaction = t2.id
                      WHERE t2.account = a.id AND t2.dateValue <= %s
                        AND EXTRACT(YEAR_MONTH FROM t2.dateValue) < %s), 0)
          + COALESCE((SELECT SUM(p.amount)
                      FROM tbl_planning p
                      JOIN tbl_planningEntry pe ON pe.planning = p.id
                      WHERE p.account = a.id AND pe.dateValue > %s
                        AND EXTRACT(YEAR_MONTH FROM pe.dateValue) < %s), 0)
          + a.startAmount
          ) AS Januar,
          (
            COALESCE((SELECT SUM(ae.amount) FROM tbl_transaction t2
                      LEFT JOIN tbl_accountingEntry ae ON ae.transaction = t2.id
                      WHERE t2.account = a.id AND t2.dateValue <= %s AND EXTRACT(YEAR_MONTH FROM t2.dateValue) < %s), 0)
          + COALESCE((SELECT SUM(p.amount) FROM tbl_planning p
                      JOIN tbl_planningEntry pe ON pe.planning = p.id
                      WHERE p.account = a.id AND pe.dateValue > %s AND EXTRACT(YEAR_MONTH FROM pe.dateValue) < %s), 0)
          + a.startAmount) AS Februar,
          (
            COALESCE((SELECT SUM(ae.amount) FROM tbl_transaction t2
                      LEFT JOIN tbl_accountingEntry ae ON ae.transaction = t2.id
                      WHERE t2.account = a.id AND t2.dateValue <= %s AND EXTRACT(YEAR_MONTH FROM t2.dateValue) < %s), 0)
          + COALESCE((SELECT SUM(p.amount) FROM tbl_planning p
                      JOIN tbl_planningEntry pe ON pe.planning = p.id
                      WHERE p.account = a.id AND pe.dateValue > %s AND EXTRACT(YEAR_MONTH FROM pe.dateValue) < %s), 0)
          + a.startAmount) AS März,
          (
            COALESCE((SELECT SUM(ae.amount) FROM tbl_transaction t2
                      LEFT JOIN tbl_accountingEntry ae ON ae.transaction = t2.id
                      WHERE t2.account = a.id AND t2.dateValue <= %s AND EXTRACT(YEAR_MONTH FROM t2.dateValue) < %s), 0)
          + COALESCE((SELECT SUM(p.amount) FROM tbl_planning p
                      JOIN tbl_planningEntry pe ON pe.planning = p.id
                      WHERE p.account = a.id AND pe.dateValue > %s AND EXTRACT(YEAR_MONTH FROM pe.dateValue) < %s), 0)
          + a.startAmount) AS April,
          (
            COALESCE((SELECT SUM(ae.amount) FROM tbl_transaction t2
                      LEFT JOIN tbl_accountingEntry ae ON ae.transaction = t2.id
                      WHERE t2.account = a.id AND t2.dateValue <= %s AND EXTRACT(YEAR_MONTH FROM t2.dateValue) < %s), 0)
          + COALESCE((SELECT SUM(p.amount) FROM tbl_planning p
                      JOIN tbl_planningEntry pe ON pe.planning = p.id
                      WHERE p.account = a.id AND pe.dateValue > %s AND EXTRACT(YEAR_MONTH FROM pe.dateValue) < %s), 0)
          + a.startAmount) AS Mai,
          (
            COALESCE((SELECT SUM(ae.amount) FROM tbl_transaction t2
                      LEFT JOIN tbl_accountingEntry ae ON ae.transaction = t2.id
                      WHERE t2.account = a.id AND t2.dateValue <= %s AND EXTRACT(YEAR_MONTH FROM t2.dateValue) < %s), 0)
          + COALESCE((SELECT SUM(p.amount) FROM tbl_planning p
                      JOIN tbl_planningEntry pe ON pe.planning = p.id
                      WHERE p.account = a.id AND pe.dateValue > %s AND EXTRACT(YEAR_MONTH FROM pe.dateValue) < %s), 0)
          + a.startAmount) AS Juni,
          (
            COALESCE((SELECT SUM(ae.amount) FROM tbl_transaction t2
                      LEFT JOIN tbl_accountingEntry ae ON ae.transaction = t2.id
                      WHERE t2.account = a.id AND t2.dateValue <= %s AND EXTRACT(YEAR_MONTH FROM t2.dateValue) < %s), 0)
          + COALESCE((SELECT SUM(p.amount) FROM tbl_planning p
                      JOIN tbl_planningEntry pe ON pe.planning = p.id
                      WHERE p.account = a.id AND pe.dateValue > %s AND EXTRACT(YEAR_MONTH FROM pe.dateValue) < %s), 0)
          + a.startAmount) AS Juli,
          (
            COALESCE((SELECT SUM(ae.amount) FROM tbl_transaction t2
                      LEFT JOIN tbl_accountingEntry ae ON ae.transaction = t2.id
                      WHERE t2.account = a.id AND t2.dateValue <= %s AND EXTRACT(YEAR_MONTH FROM t2.dateValue) < %s), 0)
          + COALESCE((SELECT SUM(p.amount) FROM tbl_planning p
                      JOIN tbl_planningEntry pe ON pe.planning = p.id
                      WHERE p.account = a.id AND pe.dateValue > %s AND EXTRACT(YEAR_MONTH FROM pe.dateValue) < %s), 0)
          + a.startAmount) AS August,
          (
            COALESCE((SELECT SUM(ae.amount) FROM tbl_transaction t2
                      LEFT JOIN tbl_accountingEntry ae ON ae.transaction = t2.id
                      WHERE t2.account = a.id AND t2.dateValue <= %s AND EXTRACT(YEAR_MONTH FROM t2.dateValue) < %s), 0)
          + COALESCE((SELECT SUM(p.amount) FROM tbl_planning p
                      JOIN tbl_planningEntry pe ON pe.planning = p.id
                      WHERE p.account = a.id AND pe.dateValue > %s AND EXTRACT(YEAR_MONTH FROM pe.dateValue) < %s), 0)
          + a.startAmount) AS September,
          (
            COALESCE((SELECT SUM(ae.amount) FROM tbl_transaction t2
                      LEFT JOIN tbl_accountingEntry ae ON ae.transaction = t2.id
                      WHERE t2.account = a.id AND t2.dateValue <= %s AND EXTRACT(YEAR_MONTH FROM t2.dateValue) < %s), 0)
          + COALESCE((SELECT SUM(p.amount) FROM tbl_planning p
                      JOIN tbl_planningEntry pe ON pe.planning = p.id
                      WHERE p.account = a.id AND pe.dateValue > %s AND EXTRACT(YEAR_MONTH FROM pe.dateValue) < %s), 0)
          + a.startAmount) AS Oktober,
          (
            COALESCE((SELECT SUM(ae.amount) FROM tbl_transaction t2
                      LEFT JOIN tbl_accountingEntry ae ON ae.transaction = t2.id
                      WHERE t2.account = a.id AND t2.dateValue <= %s AND EXTRACT(YEAR_MONTH FROM t2.dateValue) < %s), 0)
          + COALESCE((SELECT SUM(p.amount) FROM tbl_planning p
                      JOIN tbl_planningEntry pe ON pe.planning = p.id
                      WHERE p.account = a.id AND pe.dateValue > %s AND EXTRACT(YEAR_MONTH FROM pe.dateValue) < %s), 0)
          + a.startAmount) AS November,
          (
            COALESCE((SELECT SUM(ae.amount) FROM tbl_transaction t2
                      LEFT JOIN tbl_accountingEntry ae ON ae.transaction = t2.id
                      WHERE t2.account = a.id AND t2.dateValue <= %s AND EXTRACT(YEAR_MONTH FROM t2.dateValue) < %s), 0)
          + COALESCE((SELECT SUM(p.amount) FROM tbl_planning p
                      JOIN tbl_planningEntry pe ON pe.planning = p.id
                      WHERE p.account = a.id AND pe.dateValue > %s AND EXTRACT(YEAR_MONTH FROM pe.dateValue) < %s), 0)
          + a.startAmount) AS Dezember,
          (
            -- Jahresend-Stand: real bis heute (nur bis Jahresende), Planung nach heute (bis Jahresende) + Startbetrag
            COALESCE((SELECT SUM(ae.amount)
                      FROM tbl_transaction t2
                      LEFT JOIN tbl_accountingEntry ae ON ae.transaction = t2.id
                      WHERE t2.account = a.id
                        AND t2.dateValue <= %s
                        AND EXTRACT(YEAR_MONTH FROM t2.dateValue) <= %s), 0)
          + COALESCE((SELECT SUM(p.amount)
                      FROM tbl_planning p
                      JOIN tbl_planningEntry pe ON pe.planning = p.id
                      WHERE p.account = a.id
                        AND pe.dateValue > %s
                        AND EXTRACT(YEAR_MONTH FROM pe.dateValue) <= %s), 0)
          + a.startAmount
          ) AS Jahresabschluss
        FROM tbl_account a
        WHERE YEAR(a.dateStart) <= %s
          AND (YEAR(a.dateEnd) >= %s OR ISNULL(a.dateEnd))
          AND a.type IN (1)
        ORDER BY Konto ASC
    """

    # Build params: for each month we pass (today, month_threshold, today, month_threshold)
    params = []
    for m in month_thresholds:
        params.extend([today, m, today, m])
    # Jahresbilanz params (today, year_end_threshold, today, year_end_threshold)
    params.extend([today, year_end_threshold, today, year_end_threshold])
    # Account filters
    params.extend([year, year])

    params = tuple(params)

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
    """Return monthly delta balances per account for the selected year (Grafana 'Bilanz').
    Real accounting entries are counted only up to today; planning entries only after today.
    """
    from datetime import date
    today = date.today()
    month_equals = [year * 100 + month for month in range(1, 13)]

    query = """
        SELECT
          a.name AS Konto,
          (
            COALESCE((SELECT SUM(ae.amount) FROM tbl_transaction t2
                      LEFT JOIN tbl_accountingEntry ae ON ae.transaction = t2.id
                      WHERE t2.account = a.id AND t2.dateValue <= %s AND EXTRACT(YEAR_MONTH FROM t2.dateValue) = %s), 0)
          + COALESCE((SELECT SUM(p.amount) FROM tbl_planning p
                      JOIN tbl_planningEntry pe ON pe.planning = p.id
                      WHERE p.account = a.id AND pe.dateValue > %s AND EXTRACT(YEAR_MONTH FROM pe.dateValue) = %s), 0)
          ) AS Januar,
          (
            COALESCE((SELECT SUM(ae.amount) FROM tbl_transaction t2
                      LEFT JOIN tbl_accountingEntry ae ON ae.transaction = t2.id
                      WHERE t2.account = a.id AND t2.dateValue <= %s AND EXTRACT(YEAR_MONTH FROM t2.dateValue) = %s), 0)
          + COALESCE((SELECT SUM(p.amount) FROM tbl_planning p
                      JOIN tbl_planningEntry pe ON pe.planning = p.id
                      WHERE p.account = a.id AND pe.dateValue > %s AND EXTRACT(YEAR_MONTH FROM pe.dateValue) = %s), 0)
          ) AS Februar,
          (
            COALESCE((SELECT SUM(ae.amount) FROM tbl_transaction t2
                      LEFT JOIN tbl_accountingEntry ae ON ae.transaction = t2.id
                      WHERE t2.account = a.id AND t2.dateValue <= %s AND EXTRACT(YEAR_MONTH FROM t2.dateValue) = %s), 0)
          + COALESCE((SELECT SUM(p.amount) FROM tbl_planning p
                      JOIN tbl_planningEntry pe ON pe.planning = p.id
                      WHERE p.account = a.id AND pe.dateValue > %s AND EXTRACT(YEAR_MONTH FROM pe.dateValue) = %s), 0)
          ) AS März,
          (
            COALESCE((SELECT SUM(ae.amount) FROM tbl_transaction t2
                      LEFT JOIN tbl_accountingEntry ae ON ae.transaction = t2.id
                      WHERE t2.account = a.id AND t2.dateValue <= %s AND EXTRACT(YEAR_MONTH FROM t2.dateValue) = %s), 0)
          + COALESCE((SELECT SUM(p.amount) FROM tbl_planning p
                      JOIN tbl_planningEntry pe ON pe.planning = p.id
                      WHERE p.account = a.id AND pe.dateValue > %s AND EXTRACT(YEAR_MONTH FROM pe.dateValue) = %s), 0)
          ) AS April,
          (
            COALESCE((SELECT SUM(ae.amount) FROM tbl_transaction t2
                      LEFT JOIN tbl_accountingEntry ae ON ae.transaction = t2.id
                      WHERE t2.account = a.id AND t2.dateValue <= %s AND EXTRACT(YEAR_MONTH FROM t2.dateValue) = %s), 0)
          + COALESCE((SELECT SUM(p.amount) FROM tbl_planning p
                      JOIN tbl_planningEntry pe ON pe.planning = p.id
                      WHERE p.account = a.id AND pe.dateValue > %s AND EXTRACT(YEAR_MONTH FROM pe.dateValue) = %s), 0)
          ) AS Mai,
          (
            COALESCE((SELECT SUM(ae.amount) FROM tbl_transaction t2
                      LEFT JOIN tbl_accountingEntry ae ON ae.transaction = t2.id
                      WHERE t2.account = a.id AND t2.dateValue <= %s AND EXTRACT(YEAR_MONTH FROM t2.dateValue) = %s), 0)
          + COALESCE((SELECT SUM(p.amount) FROM tbl_planning p
                      JOIN tbl_planningEntry pe ON pe.planning = p.id
                      WHERE p.account = a.id AND pe.dateValue > %s AND EXTRACT(YEAR_MONTH FROM pe.dateValue) = %s), 0)
          ) AS Juni,
          (
            COALESCE((SELECT SUM(ae.amount) FROM tbl_transaction t2
                      LEFT JOIN tbl_accountingEntry ae ON ae.transaction = t2.id
                      WHERE t2.account = a.id AND t2.dateValue <= %s AND EXTRACT(YEAR_MONTH FROM t2.dateValue) = %s), 0)
          + COALESCE((SELECT SUM(p.amount) FROM tbl_planning p
                      JOIN tbl_planningEntry pe ON pe.planning = p.id
                      WHERE p.account = a.id AND pe.dateValue > %s AND EXTRACT(YEAR_MONTH FROM pe.dateValue) = %s), 0)
          ) AS Juli,
          (
            COALESCE((SELECT SUM(ae.amount) FROM tbl_transaction t2
                      LEFT JOIN tbl_accountingEntry ae ON ae.transaction = t2.id
                      WHERE t2.account = a.id AND t2.dateValue <= %s AND EXTRACT(YEAR_MONTH FROM t2.dateValue) = %s), 0)
          + COALESCE((SELECT SUM(p.amount) FROM tbl_planning p
                      JOIN tbl_planningEntry pe ON pe.planning = p.id
                      WHERE p.account = a.id AND pe.dateValue > %s AND EXTRACT(YEAR_MONTH FROM pe.dateValue) = %s), 0)
          ) AS August,
          (
            COALESCE((SELECT SUM(ae.amount) FROM tbl_transaction t2
                      LEFT JOIN tbl_accountingEntry ae ON ae.transaction = t2.id
                      WHERE t2.account = a.id AND t2.dateValue <= %s AND EXTRACT(YEAR_MONTH FROM t2.dateValue) = %s), 0)
          + COALESCE((SELECT SUM(p.amount) FROM tbl_planning p
                      JOIN tbl_planningEntry pe ON pe.planning = p.id
                      WHERE p.account = a.id AND pe.dateValue > %s AND EXTRACT(YEAR_MONTH FROM pe.dateValue) = %s), 0)
          ) AS September,
          (
            COALESCE((SELECT SUM(ae.amount) FROM tbl_transaction t2
                      LEFT JOIN tbl_accountingEntry ae ON ae.transaction = t2.id
                      WHERE t2.account = a.id AND t2.dateValue <= %s AND EXTRACT(YEAR_MONTH FROM t2.dateValue) = %s), 0)
          + COALESCE((SELECT SUM(p.amount) FROM tbl_planning p
                      JOIN tbl_planningEntry pe ON pe.planning = p.id
                      WHERE p.account = a.id AND pe.dateValue > %s AND EXTRACT(YEAR_MONTH FROM pe.dateValue) = %s), 0)
          ) AS Oktober,
          (
            COALESCE((SELECT SUM(ae.amount) FROM tbl_transaction t2
                      LEFT JOIN tbl_accountingEntry ae ON ae.transaction = t2.id
                      WHERE t2.account = a.id AND t2.dateValue <= %s AND EXTRACT(YEAR_MONTH FROM t2.dateValue) = %s), 0)
          + COALESCE((SELECT SUM(p.amount) FROM tbl_planning p
                      JOIN tbl_planningEntry pe ON pe.planning = p.id
                      WHERE p.account = a.id AND pe.dateValue > %s AND EXTRACT(YEAR_MONTH FROM pe.dateValue) = %s), 0)
          ) AS November,
          (
            COALESCE((SELECT SUM(ae.amount) FROM tbl_transaction t2
                      LEFT JOIN tbl_accountingEntry ae ON ae.transaction = t2.id
                      WHERE t2.account = a.id AND t2.dateValue <= %s AND EXTRACT(YEAR_MONTH FROM t2.dateValue) = %s), 0)
          + COALESCE((SELECT SUM(p.amount) FROM tbl_planning p
                      JOIN tbl_planningEntry pe ON pe.planning = p.id
                      WHERE p.account = a.id AND pe.dateValue > %s AND EXTRACT(YEAR_MONTH FROM pe.dateValue) = %s), 0)
          ) AS Dezember,
          (
            COALESCE((SELECT SUM(ae.amount) FROM tbl_transaction t2
                      LEFT JOIN tbl_accountingEntry ae ON ae.transaction = t2.id
                      WHERE t2.account = a.id AND t2.dateValue <= %s AND YEAR(t2.dateValue) = %s), 0)
          + COALESCE((SELECT SUM(p.amount) FROM tbl_planning p
                      JOIN tbl_planningEntry pe ON pe.planning = p.id
                      WHERE p.account = a.id AND pe.dateValue > %s AND YEAR(pe.dateValue) = %s), 0)
          ) AS Jahresbilanz
        FROM tbl_account a
        WHERE YEAR(a.dateStart) <= %s
          AND (YEAR(a.dateEnd) >= %s OR ISNULL(a.dateEnd))
          AND a.type IN (1)
        ORDER BY Konto ASC
    """

    params = []
    for m in month_equals:
        params.extend([today, m, today, m])
    params.extend([today, year, today, year])
    params.extend([year, year])
    params = tuple(params)

    rows, description = _execute_fetchall_with_retry(cursor, query, params, retries=1) # finding: Is it the correct function. Single source and desgin!
    columns = [col[0] for col in description]
    data = [dict(zip(columns, row)) for row in rows]

    return {"year": year, "rows": data}


@router.get("/investments")
@handle_db_errors("fetch investments overview")
async def get_investments(
  year: int = Query(..., ge=1900, le=3000, description="Year for which investments overview is requested"),
  cursor = Depends(get_db_cursor)
):
    """Return investment platform account balances per month for the selected year (Investment-Plattform - Typ 5).
    
    Shows cumulative balance for each month (sum of all transactions up to and including that month).
    Jahresbilanz shows the change from start of year to end of year.
    Only includes accounts of type 'Investment-Plattform' (type = 5).
    """
    from datetime import date
    today = date.today()

    # Monatsenden des Zieljahres
    month_dates = [f"{year}-{month:02d}-01" for month in range(1, 13)]

    def month_column(label: str, month_date: str) -> str: # finding: Example for simplifying the SQL generation with a helper function.
      return f"""
        (
          CASE
            WHEN LAST_DAY(%s) <= %s THEN
              -- Vergangenheit/Gegenwart: kumulierte Buchungen bis Monatsende
              COALESCE((SELECT SUM(ae.amount)
                        FROM tbl_transaction t2
                        LEFT JOIN tbl_accountingEntry ae ON ae.transaction = t2.id
                        WHERE t2.account = tbl_account.id
                          AND t2.dateValue <= LAST_DAY(%s)), 0)
              + tbl_account.startAmount
            ELSE
              -- Zukunft: Ist-Bestand bis heute + geplante Buchungen ab morgen bis Monatsende
              COALESCE((SELECT SUM(ae.amount)
                        FROM tbl_transaction t2
                        LEFT JOIN tbl_accountingEntry ae ON ae.transaction = t2.id
                        WHERE t2.account = tbl_account.id
                          AND t2.dateValue <= %s), 0)
              + COALESCE((SELECT SUM(p.amount)
                          FROM tbl_planning p
                          JOIN tbl_planningEntry pe ON pe.planning = p.id
                          WHERE p.account = tbl_account.id
                            AND pe.dateValue > %s
                            AND pe.dateValue <= LAST_DAY(%s)), 0)
              + tbl_account.startAmount
          END
        ) AS {label}
      """

    month_sql_parts = [
      month_column('Januar', month_dates[0]),
      month_column('Februar', month_dates[1]),
      month_column('März', month_dates[2]),
      month_column('April', month_dates[3]),
      month_column('Mai', month_dates[4]),
      month_column('Juni', month_dates[5]),
      month_column('Juli', month_dates[6]),
      month_column('August', month_dates[7]),
      month_column('September', month_dates[8]),
      month_column('Oktober', month_dates[9]),
      month_column('November', month_dates[10]),
      month_column('Dezember', month_dates[11]),
    ]

    month_sql = ",\n          ".join(month_sql_parts)

    query = f"""
        SELECT
          tbl_account.name AS Konto,
          {month_sql},
          -- Jahresbilanz: Ist bis heute + Pläne bis Jahresende
          (
            COALESCE((SELECT SUM(ae.amount)
                      FROM tbl_transaction t2
                      LEFT JOIN tbl_accountingEntry ae ON ae.transaction = t2.id
                      WHERE t2.account = tbl_account.id
                        AND t2.dateValue <= %s
                        AND YEAR(t2.dateValue) = %s), 0)
            + COALESCE((SELECT SUM(p.amount)
                        FROM tbl_planning p
                        JOIN tbl_planningEntry pe ON pe.planning = p.id
                        WHERE p.account = tbl_account.id
                          AND pe.dateValue > %s
                          AND YEAR(pe.dateValue) = %s), 0)
          ) AS Jahresbilanz
        FROM tbl_account
        WHERE YEAR(tbl_account.dateStart) <= %s
          AND (YEAR(tbl_account.dateEnd) >= %s OR ISNULL(tbl_account.dateEnd))
          AND tbl_account.type = 5
        ORDER BY Konto ASC
    """

    params = []
    for md in month_dates:
      params.extend([md, today, md, today, today, md])

    params.extend([today, year, today, year, year, year])
    params = tuple(params)

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
    """Return loan account balances per month for the selected year (Darlehen - Typ 3).
    
    Shows cumulative balance for each month (sum of all transactions up to and including that month).
    Jahresbilanz shows the change from start of year to end of year.
    Only includes accounts of type 'Darlehen' (type = 3).
    """
    from datetime import date
    today = date.today()

    # Monatsenden des Zieljahres
    month_dates = [f"{year}-{month:02d}-01" for month in range(1, 13)]

    def month_column(label: str, month_date: str) -> str:
      return f"""
        (
          CASE
            WHEN LAST_DAY(%s) <= %s THEN
              -- Vergangenheit/Gegenwart: kumulierte Buchungen bis Monatsende
              COALESCE((SELECT SUM(ae.amount)
                        FROM tbl_transaction t2
                        LEFT JOIN tbl_accountingEntry ae ON ae.transaction = t2.id
                        WHERE t2.account = tbl_account.id
                          AND t2.dateValue <= LAST_DAY(%s)), 0)
              + tbl_account.startAmount
            ELSE
              -- Zukunft: Ist-Bestand bis heute + geplante Buchungen ab morgen bis Monatsende
              COALESCE((SELECT SUM(ae.amount)
                        FROM tbl_transaction t2
                        LEFT JOIN tbl_accountingEntry ae ON ae.transaction = t2.id
                        WHERE t2.account = tbl_account.id
                          AND t2.dateValue <= %s), 0)
              + COALESCE((SELECT SUM(p.amount)
                          FROM tbl_planning p
                          JOIN tbl_planningEntry pe ON pe.planning = p.id
                          WHERE p.account = tbl_account.id
                            AND pe.dateValue > %s
                            AND pe.dateValue <= LAST_DAY(%s)), 0)
              + tbl_account.startAmount
          END
        ) AS {label}
      """

    month_sql_parts = [
      month_column('Januar', month_dates[0]),
      month_column('Februar', month_dates[1]),
      month_column('März', month_dates[2]),
      month_column('April', month_dates[3]),
      month_column('Mai', month_dates[4]),
      month_column('Juni', month_dates[5]),
      month_column('Juli', month_dates[6]),
      month_column('August', month_dates[7]),
      month_column('September', month_dates[8]),
      month_column('Oktober', month_dates[9]),
      month_column('November', month_dates[10]),
      month_column('Dezember', month_dates[11]),
    ]

    month_sql = ",\n          ".join(month_sql_parts)

    query = f"""
        SELECT
          tbl_account.name AS Konto,
          {month_sql},
          -- Jahresbilanz: Ist bis heute + Pläne bis Jahresende
          (
            COALESCE((SELECT SUM(ae.amount)
                      FROM tbl_transaction t2
                      LEFT JOIN tbl_accountingEntry ae ON ae.transaction = t2.id
                      WHERE t2.account = tbl_account.id
                        AND t2.dateValue <= %s
                        AND YEAR(t2.dateValue) = %s), 0)
            + COALESCE((SELECT SUM(p.amount)
                        FROM tbl_planning p
                        JOIN tbl_planningEntry pe ON pe.planning = p.id
                        WHERE p.account = tbl_account.id
                          AND pe.dateValue > %s
                          AND YEAR(pe.dateValue) = %s), 0)
          ) AS Jahresbilanz
        FROM tbl_account
        WHERE YEAR(tbl_account.dateStart) <= %s
          AND (YEAR(tbl_account.dateEnd) >= %s OR ISNULL(tbl_account.dateEnd))
          AND tbl_account.type = 3
        ORDER BY Konto ASC
    """

    params = []
    for md in month_dates:
      params.extend([md, today, md, today, today, md])

    params.extend([today, year, today, year, year, year])
    params = tuple(params)

    rows, description = _execute_fetchall_with_retry(cursor, query, params, retries=1)
    columns = [col[0] for col in description]
    data = [dict(zip(columns, row)) for row in rows]

    return {"year": year, "rows": data}


@router.get("/securities")
@handle_db_errors("fetch securities overview")
async def get_securities_overview(year: int = Query(...), cursor=Depends(get_db_cursor)):
    """Get securities portfolio values for each month-end of the given year.
    Only includes shares that have at least one month with volume > 0 (were actually held)."""
    query = """
        SELECT 
            vsms.share_name AS Wertpapier,
            COALESCE(MAX(CASE WHEN MONTH(vsms.month_end_date) = 1 THEN vsms.portfolio_value END), 0) AS Januar,
            COALESCE(MAX(CASE WHEN MONTH(vsms.month_end_date) = 2 THEN vsms.portfolio_value END), 0) AS Februar,
            COALESCE(MAX(CASE WHEN MONTH(vsms.month_end_date) = 3 THEN vsms.portfolio_value END), 0) AS März,
            COALESCE(MAX(CASE WHEN MONTH(vsms.month_end_date) = 4 THEN vsms.portfolio_value END), 0) AS April,
            COALESCE(MAX(CASE WHEN MONTH(vsms.month_end_date) = 5 THEN vsms.portfolio_value END), 0) AS Mai,
            COALESCE(MAX(CASE WHEN MONTH(vsms.month_end_date) = 6 THEN vsms.portfolio_value END), 0) AS Juni,
            COALESCE(MAX(CASE WHEN MONTH(vsms.month_end_date) = 7 THEN vsms.portfolio_value END), 0) AS Juli,
            COALESCE(MAX(CASE WHEN MONTH(vsms.month_end_date) = 8 THEN vsms.portfolio_value END), 0) AS August,
            COALESCE(MAX(CASE WHEN MONTH(vsms.month_end_date) = 9 THEN vsms.portfolio_value END), 0) AS September,
            COALESCE(MAX(CASE WHEN MONTH(vsms.month_end_date) = 10 THEN vsms.portfolio_value END), 0) AS Oktober,
            COALESCE(MAX(CASE WHEN MONTH(vsms.month_end_date) = 11 THEN vsms.portfolio_value END), 0) AS November,
            COALESCE(MAX(CASE WHEN MONTH(vsms.month_end_date) = 12 THEN vsms.portfolio_value END), 0) AS Dezember,
            COALESCE(
                (SELECT SUM(ae.amount)
                 FROM tbl_shareTransaction st
                 JOIN tbl_accountingEntry ae ON st.accountingEntry = ae.id
                 JOIN tbl_category cat ON ae.category = cat.id
                 JOIN tbl_transaction t ON ae.transaction = t.id
                 WHERE st.share = vsms.share_id
                   AND cat.name = 'Dividende (Wertpapiere)'
                   AND YEAR(t.dateValue) = %s
                ), 0
            ) AS Dividende
        FROM view_shareMonthlySnapshot vsms
        WHERE YEAR(vsms.month_end_date) = %s
        GROUP BY vsms.share_id, vsms.share_name
        HAVING MAX(vsms.volume) > 0
        ORDER BY vsms.share_name ASC
    """
    
    params = (year, year)
    rows, description = _execute_fetchall_with_retry(cursor, query, params, retries=1)
    columns = [col[0] for col in description]
    data = [dict(zip(columns, row)) for row in rows]

    return {"year": year, "rows": data}


@router.get("/assets-month-end")
@handle_db_errors("fetch assets month-end overview")
async def get_assets_month_end(
  year: int = Query(..., ge=1900, le=3000, description="Year for which assets month-end overview is requested"),
  cursor = Depends(get_db_cursor)
):
    """Aggregated assets at month-end, split into categories: Kontostand (Girokonto), Darlehen, Wertpapiere.
    
    For each month of the given year, compute the end-of-month value:
    - Kontostand: sum across accounts of type 'Girokonto' (cash accounts)
    - Darlehen: sum across accounts of type 'Darlehen'
    - Wertpapiere: sum of portfolio values from view_shareMonthlySnapshot

    Past/present months include all real transactions up to month end + startAmount;
    Future months use real up to today + planned entries after today up to month end + startAmount.
    Jahresbilanz reflects the end-of-year value using the same blending logic.
    """
    from datetime import date
    today = date.today()

    # Month first-day dates to feed LAST_DAY()
    month_dates = [f"{year}-{month:02d}-01" for month in range(1, 13)]

    def month_sum_column(label: str, month_date: str, account_type_name: str) -> str:
        # Aggregated month-end value across all accounts of a given type
        # Uses blending logic around 'today'
        return f"""
        (
          CASE
            WHEN LAST_DAY(%s) <= %s THEN
              COALESCE((SELECT SUM(ae.amount)
                        FROM tbl_transaction t2
                        LEFT JOIN tbl_accountingEntry ae ON ae.transaction = t2.id
                        INNER JOIN tbl_account a ON a.id = t2.account
                        INNER JOIN tbl_accountType at ON at.id = a.type
                        WHERE at.type = %s
                          AND t2.dateValue <= LAST_DAY(%s)
                      ), 0)
              + COALESCE((SELECT SUM(a.startAmount)
                          FROM tbl_account a
                          INNER JOIN tbl_accountType at ON at.id = a.type
                          WHERE at.type = %s
                        ), 0)
            ELSE
              COALESCE((SELECT SUM(ae.amount)
                        FROM tbl_transaction t2
                        LEFT JOIN tbl_accountingEntry ae ON ae.transaction = t2.id
                        INNER JOIN tbl_account a ON a.id = t2.account
                        INNER JOIN tbl_accountType at ON at.id = a.type
                        WHERE at.type = %s
                          AND t2.dateValue <= %s
                      ), 0)
              + COALESCE((SELECT SUM(p.amount)
                          FROM tbl_planning p
                          JOIN tbl_planningEntry pe ON pe.planning = p.id
                          INNER JOIN tbl_account a ON a.id = p.account
                          INNER JOIN tbl_accountType at ON at.id = a.type
                          WHERE at.type = %s
                            AND pe.dateValue > %s
                            AND pe.dateValue <= LAST_DAY(%s)
                        ), 0)
              + COALESCE((SELECT SUM(a.startAmount)
                          FROM tbl_account a
                          INNER JOIN tbl_accountType at ON at.id = a.type
                          WHERE at.type = %s
                        ), 0)
          END
        ) AS {label}
        """

    # Build SQL parts for Kontostand (Girokonto) and Darlehen aggregations
    giro_month_sql_parts = [
        month_sum_column('Januar', month_dates[0], 'Girokonto'),
        month_sum_column('Februar', month_dates[1], 'Girokonto'),
        month_sum_column('März', month_dates[2], 'Girokonto'),
        month_sum_column('April', month_dates[3], 'Girokonto'),
        month_sum_column('Mai', month_dates[4], 'Girokonto'),
        month_sum_column('Juni', month_dates[5], 'Girokonto'),
        month_sum_column('Juli', month_dates[6], 'Girokonto'),
        month_sum_column('August', month_dates[7], 'Girokonto'),
        month_sum_column('September', month_dates[8], 'Girokonto'),
        month_sum_column('Oktober', month_dates[9], 'Girokonto'),
        month_sum_column('November', month_dates[10], 'Girokonto'),
        month_sum_column('Dezember', month_dates[11], 'Girokonto'),
    ]

    darlehen_month_sql_parts = [
        month_sum_column('Januar', month_dates[0], 'Darlehen'),
        month_sum_column('Februar', month_dates[1], 'Darlehen'),
        month_sum_column('März', month_dates[2], 'Darlehen'),
        month_sum_column('April', month_dates[3], 'Darlehen'),
        month_sum_column('Mai', month_dates[4], 'Darlehen'),
        month_sum_column('Juni', month_dates[5], 'Darlehen'),
        month_sum_column('Juli', month_dates[6], 'Darlehen'),
        month_sum_column('August', month_dates[7], 'Darlehen'),
        month_sum_column('September', month_dates[8], 'Darlehen'),
        month_sum_column('Oktober', month_dates[9], 'Darlehen'),
        month_sum_column('November', month_dates[10], 'Darlehen'),
        month_sum_column('Dezember', month_dates[11], 'Darlehen'),
    ]

    giro_month_sql = ",\n          ".join(giro_month_sql_parts)
    darlehen_month_sql = ",\n          ".join(darlehen_month_sql_parts)

    # Jahresendwert (Dezember) mit gleicher Logik
    def year_end_sum_column(label: str, account_type_name: str) -> str:
        return f"""
        (
          CASE
            WHEN LAST_DAY(%s) <= %s THEN
              COALESCE((SELECT SUM(ae.amount)
                        FROM tbl_transaction t2
                        LEFT JOIN tbl_accountingEntry ae ON ae.transaction = t2.id
                        INNER JOIN tbl_account a ON a.id = t2.account
                        INNER JOIN tbl_accountType at ON at.id = a.type
                        WHERE at.type = %s
                          AND t2.dateValue <= LAST_DAY(%s)), 0)
              + COALESCE((SELECT SUM(a.startAmount)
                          FROM tbl_account a
                          INNER JOIN tbl_accountType at ON at.id = a.type
                          WHERE at.type = %s), 0)
            ELSE
              COALESCE((SELECT SUM(ae.amount)
                        FROM tbl_transaction t2
                        LEFT JOIN tbl_accountingEntry ae ON ae.transaction = t2.id
                        INNER JOIN tbl_account a ON a.id = t2.account
                        INNER JOIN tbl_accountType at ON at.id = a.type
                        WHERE at.type = %s AND t2.dateValue <= %s), 0)
              + COALESCE((SELECT SUM(p.amount)
                          FROM tbl_planning p
                          JOIN tbl_planningEntry pe ON pe.planning = p.id
                          INNER JOIN tbl_account a ON a.id = p.account
                          INNER JOIN tbl_accountType at ON at.id = a.type
                          WHERE at.type = %s AND pe.dateValue > %s AND YEAR(pe.dateValue) = %s), 0)
              + COALESCE((SELECT SUM(a.startAmount)
                          FROM tbl_account a
                          INNER JOIN tbl_accountType at ON at.id = a.type
                          WHERE at.type = %s), 0)
          END
        ) AS {label}
        """

    # Securities monthly sum per month and end-of-year
    securities_month_sql = """
        COALESCE(MAX(CASE WHEN MONTH(month_end_date) = 1 THEN portfolio_value_sum END), 0) AS Januar,
        COALESCE(MAX(CASE WHEN MONTH(month_end_date) = 2 THEN portfolio_value_sum END), 0) AS Februar,
        COALESCE(MAX(CASE WHEN MONTH(month_end_date) = 3 THEN portfolio_value_sum END), 0) AS März,
        COALESCE(MAX(CASE WHEN MONTH(month_end_date) = 4 THEN portfolio_value_sum END), 0) AS April,
        COALESCE(MAX(CASE WHEN MONTH(month_end_date) = 5 THEN portfolio_value_sum END), 0) AS Mai,
        COALESCE(MAX(CASE WHEN MONTH(month_end_date) = 6 THEN portfolio_value_sum END), 0) AS Juni,
        COALESCE(MAX(CASE WHEN MONTH(month_end_date) = 7 THEN portfolio_value_sum END), 0) AS Juli,
        COALESCE(MAX(CASE WHEN MONTH(month_end_date) = 8 THEN portfolio_value_sum END), 0) AS August,
        COALESCE(MAX(CASE WHEN MONTH(month_end_date) = 9 THEN portfolio_value_sum END), 0) AS September,
        COALESCE(MAX(CASE WHEN MONTH(month_end_date) = 10 THEN portfolio_value_sum END), 0) AS Oktober,
        COALESCE(MAX(CASE WHEN MONTH(month_end_date) = 11 THEN portfolio_value_sum END), 0) AS November,
        COALESCE(MAX(CASE WHEN MONTH(month_end_date) = 12 THEN portfolio_value_sum END), 0) AS Dezember
    """

    # Baseline (Start des Jahres: 1.1.) als Subselect für Differenzbildung
    def year_begin_sum_subselect(account_type_name: str) -> str:
        return f"""
          (SELECT
            COALESCE((SELECT SUM(a.startAmount)
                      FROM tbl_account a
                      INNER JOIN tbl_accountType at ON at.id = a.type
                      WHERE at.type = %s), 0)
            + COALESCE((SELECT SUM(ae.amount)
                        FROM tbl_transaction t2
                        LEFT JOIN tbl_accountingEntry ae ON ae.transaction = t2.id
                        INNER JOIN tbl_account a ON a.id = t2.account
                        INNER JOIN tbl_accountType at ON at.id = a.type
                        WHERE at.type = %s
                          AND t2.dateValue < %s), 0))
        """

    # End-of-year expression (no alias) for subtraction
    def year_end_sum_expr(account_type_name: str) -> str:
        return f"""
        (
          CASE
            WHEN LAST_DAY(%s) <= %s THEN
              COALESCE((SELECT SUM(ae.amount)
                        FROM tbl_transaction t2
                        LEFT JOIN tbl_accountingEntry ae ON ae.transaction = t2.id
                        INNER JOIN tbl_account a ON a.id = t2.account
                        INNER JOIN tbl_accountType at ON at.id = a.type
                        WHERE at.type = %s
                          AND t2.dateValue <= LAST_DAY(%s)), 0)
              + COALESCE((SELECT SUM(a.startAmount)
                          FROM tbl_account a
                          INNER JOIN tbl_accountType at ON at.id = a.type
                          WHERE at.type = %s), 0)
            ELSE
              COALESCE((SELECT SUM(ae.amount)
                        FROM tbl_transaction t2
                        LEFT JOIN tbl_accountingEntry ae ON ae.transaction = t2.id
                        INNER JOIN tbl_account a ON a.id = t2.account
                        INNER JOIN tbl_accountType at ON at.id = a.type
                        WHERE at.type = %s AND t2.dateValue <= %s), 0)
              + COALESCE((SELECT SUM(p.amount)
                          FROM tbl_planning p
                          JOIN tbl_planningEntry pe ON pe.planning = p.id
                          INNER JOIN tbl_account a ON a.id = p.account
                          INNER JOIN tbl_accountType at ON at.id = a.type
                          WHERE at.type = %s AND pe.dateValue > %s AND YEAR(pe.dateValue) = %s), 0)
              + COALESCE((SELECT SUM(a.startAmount)
                          FROM tbl_account a
                          INNER JOIN tbl_accountType at ON at.id = a.type
                          WHERE at.type = %s), 0)
          END
        )
        """

    # Compose the final query with three rows via UNION ALL
    query = f"""
        SELECT 'Kontostand' AS `Vermögen Ende des Monats`,
               {giro_month_sql},
               (
                 {year_end_sum_expr('Girokonto')}
                 - {year_begin_sum_subselect('Girokonto')}
               ) AS Jahresbilanz
        UNION ALL
        SELECT 'Darlehen' AS `Vermögen Ende des Monats`,
               {darlehen_month_sql},
               (
                 {year_end_sum_expr('Darlehen')}
                 - {year_begin_sum_subselect('Darlehen')}
               ) AS Jahresbilanz
        UNION ALL
        SELECT 'Wertpapiere' AS `Vermögen Ende des Monats`,
               {securities_month_sql},
               COALESCE(MAX(CASE WHEN MONTH(month_end_date) = 12 THEN portfolio_value_sum END), 0)
               - COALESCE((SELECT SUM(portfolio_value)
                           FROM view_shareMonthlySnapshot
                           WHERE YEAR(month_end_date) = %s AND MONTH(month_end_date) = 12), 0) AS Jahresbilanz
        FROM (
          SELECT month_end_date, SUM(portfolio_value) AS portfolio_value_sum
          FROM view_shareMonthlySnapshot
          WHERE YEAR(month_end_date) = %s
          GROUP BY month_end_date
        ) s
        """

    # Build params for Girokonto months
    params: list = []
    year_first_day = f"{year}-01-01"
    dec_first = f"{year}-12-01"

    for md in month_dates:
        # Each month_sum_column expects: (month_date, today, typeName, month_date, typeName, typeName, today, typeName, today, month_date, typeName)
        params.extend([md, today, 'Girokonto', md, 'Girokonto', 'Girokonto', today, 'Girokonto', today, md, 'Girokonto'])
     
    params.extend([dec_first, today, 'Girokonto', dec_first, 'Girokonto', 'Girokonto', today, 'Girokonto', today, year, 'Girokonto']) # Jahresendwert (Dez 31) Parameter-Blöcke für year_end_sum_expr
    params.extend(['Girokonto', 'Girokonto', year_first_day]) # Baseline (Start des Jahres 1.1.) für Differenz

    # Darlehen months
    for md in month_dates:
        params.extend([md, today, 'Darlehen', md, 'Darlehen', 'Darlehen', today, 'Darlehen', today, md, 'Darlehen'])
    
    params.extend([dec_first, today, 'Darlehen', dec_first, 'Darlehen', 'Darlehen', today, 'Darlehen', today, year, 'Darlehen']) # Jahresendwert (Dez 31) Parameter-Blöcke für year_end_sum_expr
    params.extend(['Darlehen', 'Darlehen', year_first_day]) # Baseline (Start des Jahres 1.1.) für Differenz

    # Securities: vorheriges Jahr (Dezember) und aktuelles Jahr für Subquery
    previous_year = year - 1
    params.extend([previous_year, year])

    rows, description = _execute_fetchall_with_retry(cursor, query, tuple(params), retries=1)
    columns = [col[0] for col in description]
    data = [dict(zip(columns, row)) for row in rows]

    return {"year": year, "rows": data}
