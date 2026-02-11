"""
Account details API router - provides income/expense breakdown per account
"""

from fastapi import APIRouter, Depends, Query, HTTPException, Path, UploadFile, File
from api.dependencies import get_db_cursor_with_auth, get_db_connection_with_auth, get_pool_manager
from api.error_handling import handle_db_errors
from api.auth_middleware import get_current_session
from api.models import AccountData
from services.import_service import ImportService
from services.import_steps.accounts import AccountsStep
import yaml

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
    from datetime import date
    today = date.today()

    # finding: The string can be simplified by extracting the substring, e.g. column names. The substring can be reused in other queries.
    query = """
        SELECT
          cat AS Kategorie,
          SUM(Jan) AS Januar,
          SUM(Feb) AS Februar,
          SUM(Mrz) AS März,
          SUM(Apr) AS April,
          SUM(Mai) AS Mai,
          SUM(Jun) AS Juni,
          SUM(Jul) AS Juli,
          SUM(Aug) AS August,
          SUM(Sep) AS September,
          SUM(Okt) AS Oktober,
          SUM(Nov) AS November,
          SUM(Dez) AS Dezember,
          SUM(Jan+Feb+Mrz+Apr+Mai+Jun+Jul+Aug+Sep+Okt+Nov+Dez) AS Gesamt
        FROM (
          -- Actual transactions up to today
          SELECT
            view_categoryFullname.fullname AS cat,
            SUM(CASE WHEN MONTH(t.dateValue) = 1 AND t.dateValue <= %s AND ae.amount > 0 THEN ae.amount ELSE 0 END) AS Jan,
            SUM(CASE WHEN MONTH(t.dateValue) = 2 AND t.dateValue <= %s AND ae.amount > 0 THEN ae.amount ELSE 0 END) AS Feb,
            SUM(CASE WHEN MONTH(t.dateValue) = 3 AND t.dateValue <= %s AND ae.amount > 0 THEN ae.amount ELSE 0 END) AS Mrz,
            SUM(CASE WHEN MONTH(t.dateValue) = 4 AND t.dateValue <= %s AND ae.amount > 0 THEN ae.amount ELSE 0 END) AS Apr,
            SUM(CASE WHEN MONTH(t.dateValue) = 5 AND t.dateValue <= %s AND ae.amount > 0 THEN ae.amount ELSE 0 END) AS Mai,
            SUM(CASE WHEN MONTH(t.dateValue) = 6 AND t.dateValue <= %s AND ae.amount > 0 THEN ae.amount ELSE 0 END) AS Jun,
            SUM(CASE WHEN MONTH(t.dateValue) = 7 AND t.dateValue <= %s AND ae.amount > 0 THEN ae.amount ELSE 0 END) AS Jul,
            SUM(CASE WHEN MONTH(t.dateValue) = 8 AND t.dateValue <= %s AND ae.amount > 0 THEN ae.amount ELSE 0 END) AS Aug,
            SUM(CASE WHEN MONTH(t.dateValue) = 9 AND t.dateValue <= %s AND ae.amount > 0 THEN ae.amount ELSE 0 END) AS Sep,
            SUM(CASE WHEN MONTH(t.dateValue) = 10 AND t.dateValue <= %s AND ae.amount > 0 THEN ae.amount ELSE 0 END) AS Okt,
            SUM(CASE WHEN MONTH(t.dateValue) = 11 AND t.dateValue <= %s AND ae.amount > 0 THEN ae.amount ELSE 0 END) AS Nov,
            SUM(CASE WHEN MONTH(t.dateValue) = 12 AND t.dateValue <= %s AND ae.amount > 0 THEN ae.amount ELSE 0 END) AS Dez
          FROM tbl_accountingEntry ae
            INNER JOIN tbl_transaction t ON ae.transaction = t.id
            INNER JOIN tbl_account ON tbl_account.id = t.account
            LEFT JOIN view_categoryFullname ON view_categoryFullname.id = ae.category
          WHERE YEAR(t.dateValue) = %s AND tbl_account.name = %s
          GROUP BY view_categoryFullname.fullname
          UNION ALL
          -- Planning entries after today
          SELECT
            view_categoryFullname.fullname AS cat,
            SUM(CASE WHEN MONTH(pe.dateValue) = 1 AND pe.dateValue > %s AND p.amount > 0 THEN p.amount ELSE 0 END) AS Jan,
            SUM(CASE WHEN MONTH(pe.dateValue) = 2 AND pe.dateValue > %s AND p.amount > 0 THEN p.amount ELSE 0 END) AS Feb,
            SUM(CASE WHEN MONTH(pe.dateValue) = 3 AND pe.dateValue > %s AND p.amount > 0 THEN p.amount ELSE 0 END) AS Mrz,
            SUM(CASE WHEN MONTH(pe.dateValue) = 4 AND pe.dateValue > %s AND p.amount > 0 THEN p.amount ELSE 0 END) AS Apr,
            SUM(CASE WHEN MONTH(pe.dateValue) = 5 AND pe.dateValue > %s AND p.amount > 0 THEN p.amount ELSE 0 END) AS Mai,
            SUM(CASE WHEN MONTH(pe.dateValue) = 6 AND pe.dateValue > %s AND p.amount > 0 THEN p.amount ELSE 0 END) AS Jun,
            SUM(CASE WHEN MONTH(pe.dateValue) = 7 AND pe.dateValue > %s AND p.amount > 0 THEN p.amount ELSE 0 END) AS Jul,
            SUM(CASE WHEN MONTH(pe.dateValue) = 8 AND pe.dateValue > %s AND p.amount > 0 THEN p.amount ELSE 0 END) AS Aug,
            SUM(CASE WHEN MONTH(pe.dateValue) = 9 AND pe.dateValue > %s AND p.amount > 0 THEN p.amount ELSE 0 END) AS Sep,
            SUM(CASE WHEN MONTH(pe.dateValue) = 10 AND pe.dateValue > %s AND p.amount > 0 THEN p.amount ELSE 0 END) AS Okt,
            SUM(CASE WHEN MONTH(pe.dateValue) = 11 AND pe.dateValue > %s AND p.amount > 0 THEN p.amount ELSE 0 END) AS Nov,
            SUM(CASE WHEN MONTH(pe.dateValue) = 12 AND pe.dateValue > %s AND p.amount > 0 THEN p.amount ELSE 0 END) AS Dez
          FROM tbl_planning p
            JOIN tbl_planningEntry pe ON pe.planning = p.id
            INNER JOIN tbl_account ON tbl_account.id = p.account
            LEFT JOIN view_categoryFullname ON view_categoryFullname.id = p.category
          WHERE YEAR(pe.dateValue) = %s AND tbl_account.name = %s
          GROUP BY view_categoryFullname.fullname
        ) combined
        GROUP BY cat
        HAVING Gesamt > 0
        ORDER BY cat ASC
    """
    
    params = tuple([today]*12 + [year, account] + [today]*12 + [year, account])
    cursor.execute(query, params)
    rows = cursor.fetchall()
    
    columns = [col[0] for col in cursor.description]
    data = [dict(zip(columns, row)) for row in rows]
    
    return {"year": year, "account": account, "rows": data}


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
    from datetime import date
    today = date.today()

    query = """
        SELECT
          'Haben' AS Kategorie,
          SUM(Jan) AS Januar,
          SUM(Feb) AS Februar,
          SUM(Mrz) AS März,
          SUM(Apr) AS April,
          SUM(Mai) AS Mai,
          SUM(Jun) AS Juni,
          SUM(Jul) AS Juli,
          SUM(Aug) AS August,
          SUM(Sep) AS September,
          SUM(Okt) AS Oktober,
          SUM(Nov) AS November,
          SUM(Dez) AS Dezember,
          SUM(Jan+Feb+Mrz+Apr+Mai+Jun+Jul+Aug+Sep+Okt+Nov+Dez) AS Gesamt
        FROM (
          SELECT
            SUM(CASE WHEN MONTH(t.dateValue) = 1 AND t.dateValue <= %s AND ae.amount > 0 THEN ae.amount ELSE 0 END) AS Jan,
            SUM(CASE WHEN MONTH(t.dateValue) = 2 AND t.dateValue <= %s AND ae.amount > 0 THEN ae.amount ELSE 0 END) AS Feb,
            SUM(CASE WHEN MONTH(t.dateValue) = 3 AND t.dateValue <= %s AND ae.amount > 0 THEN ae.amount ELSE 0 END) AS Mrz,
            SUM(CASE WHEN MONTH(t.dateValue) = 4 AND t.dateValue <= %s AND ae.amount > 0 THEN ae.amount ELSE 0 END) AS Apr,
            SUM(CASE WHEN MONTH(t.dateValue) = 5 AND t.dateValue <= %s AND ae.amount > 0 THEN ae.amount ELSE 0 END) AS Mai,
            SUM(CASE WHEN MONTH(t.dateValue) = 6 AND t.dateValue <= %s AND ae.amount > 0 THEN ae.amount ELSE 0 END) AS Jun,
            SUM(CASE WHEN MONTH(t.dateValue) = 7 AND t.dateValue <= %s AND ae.amount > 0 THEN ae.amount ELSE 0 END) AS Jul,
            SUM(CASE WHEN MONTH(t.dateValue) = 8 AND t.dateValue <= %s AND ae.amount > 0 THEN ae.amount ELSE 0 END) AS Aug,
            SUM(CASE WHEN MONTH(t.dateValue) = 9 AND t.dateValue <= %s AND ae.amount > 0 THEN ae.amount ELSE 0 END) AS Sep,
            SUM(CASE WHEN MONTH(t.dateValue) = 10 AND t.dateValue <= %s AND ae.amount > 0 THEN ae.amount ELSE 0 END) AS Okt,
            SUM(CASE WHEN MONTH(t.dateValue) = 11 AND t.dateValue <= %s AND ae.amount > 0 THEN ae.amount ELSE 0 END) AS Nov,
            SUM(CASE WHEN MONTH(t.dateValue) = 12 AND t.dateValue <= %s AND ae.amount > 0 THEN ae.amount ELSE 0 END) AS Dez
          FROM tbl_accountingEntry ae
            INNER JOIN tbl_transaction t ON ae.transaction = t.id
            INNER JOIN tbl_account ON tbl_account.id = t.account
          WHERE YEAR(t.dateValue) = %s AND tbl_account.name = %s
          UNION ALL
          SELECT
            SUM(CASE WHEN MONTH(pe.dateValue) = 1 AND pe.dateValue > %s AND p.amount > 0 THEN p.amount ELSE 0 END) AS Jan,
            SUM(CASE WHEN MONTH(pe.dateValue) = 2 AND pe.dateValue > %s AND p.amount > 0 THEN p.amount ELSE 0 END) AS Feb,
            SUM(CASE WHEN MONTH(pe.dateValue) = 3 AND pe.dateValue > %s AND p.amount > 0 THEN p.amount ELSE 0 END) AS Mrz,
            SUM(CASE WHEN MONTH(pe.dateValue) = 4 AND pe.dateValue > %s AND p.amount > 0 THEN p.amount ELSE 0 END) AS Apr,
            SUM(CASE WHEN MONTH(pe.dateValue) = 5 AND pe.dateValue > %s AND p.amount > 0 THEN p.amount ELSE 0 END) AS Mai,
            SUM(CASE WHEN MONTH(pe.dateValue) = 6 AND pe.dateValue > %s AND p.amount > 0 THEN p.amount ELSE 0 END) AS Jun,
            SUM(CASE WHEN MONTH(pe.dateValue) = 7 AND pe.dateValue > %s AND p.amount > 0 THEN p.amount ELSE 0 END) AS Jul,
            SUM(CASE WHEN MONTH(pe.dateValue) = 8 AND pe.dateValue > %s AND p.amount > 0 THEN p.amount ELSE 0 END) AS Aug,
            SUM(CASE WHEN MONTH(pe.dateValue) = 9 AND pe.dateValue > %s AND p.amount > 0 THEN p.amount ELSE 0 END) AS Sep,
            SUM(CASE WHEN MONTH(pe.dateValue) = 10 AND pe.dateValue > %s AND p.amount > 0 THEN p.amount ELSE 0 END) AS Okt,
            SUM(CASE WHEN MONTH(pe.dateValue) = 11 AND pe.dateValue > %s AND p.amount > 0 THEN p.amount ELSE 0 END) AS Nov,
            SUM(CASE WHEN MONTH(pe.dateValue) = 12 AND pe.dateValue > %s AND p.amount > 0 THEN p.amount ELSE 0 END) AS Dez
          FROM tbl_planning p
            JOIN tbl_planningEntry pe ON pe.planning = p.id
            INNER JOIN tbl_account ON tbl_account.id = p.account
          WHERE YEAR(pe.dateValue) = %s AND tbl_account.name = %s
        ) haben_combined
        UNION ALL
        SELECT
          'Soll' AS Kategorie,
          SUM(Jan) AS Januar,
          SUM(Feb) AS Februar,
          SUM(Mrz) AS März,
          SUM(Apr) AS April,
          SUM(Mai) AS Mai,
          SUM(Jun) AS Juni,
          SUM(Jul) AS Juli,
          SUM(Aug) AS August,
          SUM(Sep) AS September,
          SUM(Okt) AS Oktober,
          SUM(Nov) AS November,
          SUM(Dez) AS Dezember,
          SUM(Jan+Feb+Mrz+Apr+Mai+Jun+Jul+Aug+Sep+Okt+Nov+Dez) AS Gesamt
        FROM (
          SELECT
            SUM(CASE WHEN MONTH(t.dateValue) = 1 AND t.dateValue <= %s AND ae.amount < 0 THEN ae.amount ELSE 0 END) AS Jan,
            SUM(CASE WHEN MONTH(t.dateValue) = 2 AND t.dateValue <= %s AND ae.amount < 0 THEN ae.amount ELSE 0 END) AS Feb,
            SUM(CASE WHEN MONTH(t.dateValue) = 3 AND t.dateValue <= %s AND ae.amount < 0 THEN ae.amount ELSE 0 END) AS Mrz,
            SUM(CASE WHEN MONTH(t.dateValue) = 4 AND t.dateValue <= %s AND ae.amount < 0 THEN ae.amount ELSE 0 END) AS Apr,
            SUM(CASE WHEN MONTH(t.dateValue) = 5 AND t.dateValue <= %s AND ae.amount < 0 THEN ae.amount ELSE 0 END) AS Mai,
            SUM(CASE WHEN MONTH(t.dateValue) = 6 AND t.dateValue <= %s AND ae.amount < 0 THEN ae.amount ELSE 0 END) AS Jun,
            SUM(CASE WHEN MONTH(t.dateValue) = 7 AND t.dateValue <= %s AND ae.amount < 0 THEN ae.amount ELSE 0 END) AS Jul,
            SUM(CASE WHEN MONTH(t.dateValue) = 8 AND t.dateValue <= %s AND ae.amount < 0 THEN ae.amount ELSE 0 END) AS Aug,
            SUM(CASE WHEN MONTH(t.dateValue) = 9 AND t.dateValue <= %s AND ae.amount < 0 THEN ae.amount ELSE 0 END) AS Sep,
            SUM(CASE WHEN MONTH(t.dateValue) = 10 AND t.dateValue <= %s AND ae.amount < 0 THEN ae.amount ELSE 0 END) AS Okt,
            SUM(CASE WHEN MONTH(t.dateValue) = 11 AND t.dateValue <= %s AND ae.amount < 0 THEN ae.amount ELSE 0 END) AS Nov,
            SUM(CASE WHEN MONTH(t.dateValue) = 12 AND t.dateValue <= %s AND ae.amount < 0 THEN ae.amount ELSE 0 END) AS Dez
          FROM tbl_accountingEntry ae
            INNER JOIN tbl_transaction t ON ae.transaction = t.id
            INNER JOIN tbl_account ON tbl_account.id = t.account
          WHERE YEAR(t.dateValue) = %s AND tbl_account.name = %s
          UNION ALL
          SELECT
            SUM(CASE WHEN MONTH(pe.dateValue) = 1 AND pe.dateValue > %s AND p.amount < 0 THEN p.amount ELSE 0 END) AS Jan,
            SUM(CASE WHEN MONTH(pe.dateValue) = 2 AND pe.dateValue > %s AND p.amount < 0 THEN p.amount ELSE 0 END) AS Feb,
            SUM(CASE WHEN MONTH(pe.dateValue) = 3 AND pe.dateValue > %s AND p.amount < 0 THEN p.amount ELSE 0 END) AS Mrz,
            SUM(CASE WHEN MONTH(pe.dateValue) = 4 AND pe.dateValue > %s AND p.amount < 0 THEN p.amount ELSE 0 END) AS Apr,
            SUM(CASE WHEN MONTH(pe.dateValue) = 5 AND pe.dateValue > %s AND p.amount < 0 THEN p.amount ELSE 0 END) AS Mai,
            SUM(CASE WHEN MONTH(pe.dateValue) = 6 AND pe.dateValue > %s AND p.amount < 0 THEN p.amount ELSE 0 END) AS Jun,
            SUM(CASE WHEN MONTH(pe.dateValue) = 7 AND pe.dateValue > %s AND p.amount < 0 THEN p.amount ELSE 0 END) AS Jul,
            SUM(CASE WHEN MONTH(pe.dateValue) = 8 AND pe.dateValue > %s AND p.amount < 0 THEN p.amount ELSE 0 END) AS Aug,
            SUM(CASE WHEN MONTH(pe.dateValue) = 9 AND pe.dateValue > %s AND p.amount < 0 THEN p.amount ELSE 0 END) AS Sep,
            SUM(CASE WHEN MONTH(pe.dateValue) = 10 AND pe.dateValue > %s AND p.amount < 0 THEN p.amount ELSE 0 END) AS Okt,
            SUM(CASE WHEN MONTH(pe.dateValue) = 11 AND pe.dateValue > %s AND p.amount < 0 THEN p.amount ELSE 0 END) AS Nov,
            SUM(CASE WHEN MONTH(pe.dateValue) = 12 AND pe.dateValue > %s AND p.amount < 0 THEN p.amount ELSE 0 END) AS Dez
          FROM tbl_planning p
            JOIN tbl_planningEntry pe ON pe.planning = p.id
            INNER JOIN tbl_account ON tbl_account.id = p.account
          WHERE YEAR(pe.dateValue) = %s AND tbl_account.name = %s
        ) soll_combined
        UNION ALL
        SELECT
          'Gesamt' AS Kategorie,
          SUM(Jan) AS Januar,
          SUM(Feb) AS Februar,
          SUM(Mrz) AS März,
          SUM(Apr) AS April,
          SUM(Mai) AS Mai,
          SUM(Jun) AS Juni,
          SUM(Jul) AS Juli,
          SUM(Aug) AS August,
          SUM(Sep) AS September,
          SUM(Okt) AS Oktober,
          SUM(Nov) AS November,
          SUM(Dez) AS Dezember,
          SUM(Jan+Feb+Mrz+Apr+Mai+Jun+Jul+Aug+Sep+Okt+Nov+Dez) AS Gesamt
        FROM (
          SELECT
            SUM(CASE WHEN MONTH(t.dateValue) = 1 AND t.dateValue <= %s THEN ae.amount ELSE 0 END) AS Jan,
            SUM(CASE WHEN MONTH(t.dateValue) = 2 AND t.dateValue <= %s THEN ae.amount ELSE 0 END) AS Feb,
            SUM(CASE WHEN MONTH(t.dateValue) = 3 AND t.dateValue <= %s THEN ae.amount ELSE 0 END) AS Mrz,
            SUM(CASE WHEN MONTH(t.dateValue) = 4 AND t.dateValue <= %s THEN ae.amount ELSE 0 END) AS Apr,
            SUM(CASE WHEN MONTH(t.dateValue) = 5 AND t.dateValue <= %s THEN ae.amount ELSE 0 END) AS Mai,
            SUM(CASE WHEN MONTH(t.dateValue) = 6 AND t.dateValue <= %s THEN ae.amount ELSE 0 END) AS Jun,
            SUM(CASE WHEN MONTH(t.dateValue) = 7 AND t.dateValue <= %s THEN ae.amount ELSE 0 END) AS Jul,
            SUM(CASE WHEN MONTH(t.dateValue) = 8 AND t.dateValue <= %s THEN ae.amount ELSE 0 END) AS Aug,
            SUM(CASE WHEN MONTH(t.dateValue) = 9 AND t.dateValue <= %s THEN ae.amount ELSE 0 END) AS Sep,
            SUM(CASE WHEN MONTH(t.dateValue) = 10 AND t.dateValue <= %s THEN ae.amount ELSE 0 END) AS Okt,
            SUM(CASE WHEN MONTH(t.dateValue) = 11 AND t.dateValue <= %s THEN ae.amount ELSE 0 END) AS Nov,
            SUM(CASE WHEN MONTH(t.dateValue) = 12 AND t.dateValue <= %s THEN ae.amount ELSE 0 END) AS Dez
          FROM tbl_accountingEntry ae
            INNER JOIN tbl_transaction t ON ae.transaction = t.id
            INNER JOIN tbl_account ON tbl_account.id = t.account
          WHERE YEAR(t.dateValue) = %s AND tbl_account.name = %s
          UNION ALL
          SELECT
            SUM(CASE WHEN MONTH(pe.dateValue) = 1 AND pe.dateValue > %s THEN p.amount ELSE 0 END) AS Jan,
            SUM(CASE WHEN MONTH(pe.dateValue) = 2 AND pe.dateValue > %s THEN p.amount ELSE 0 END) AS Feb,
            SUM(CASE WHEN MONTH(pe.dateValue) = 3 AND pe.dateValue > %s THEN p.amount ELSE 0 END) AS Mrz,
            SUM(CASE WHEN MONTH(pe.dateValue) = 4 AND pe.dateValue > %s THEN p.amount ELSE 0 END) AS Apr,
            SUM(CASE WHEN MONTH(pe.dateValue) = 5 AND pe.dateValue > %s THEN p.amount ELSE 0 END) AS Mai,
            SUM(CASE WHEN MONTH(pe.dateValue) = 6 AND pe.dateValue > %s THEN p.amount ELSE 0 END) AS Jun,
            SUM(CASE WHEN MONTH(pe.dateValue) = 7 AND pe.dateValue > %s THEN p.amount ELSE 0 END) AS Jul,
            SUM(CASE WHEN MONTH(pe.dateValue) = 8 AND pe.dateValue > %s THEN p.amount ELSE 0 END) AS Aug,
            SUM(CASE WHEN MONTH(pe.dateValue) = 9 AND pe.dateValue > %s THEN p.amount ELSE 0 END) AS Sep,
            SUM(CASE WHEN MONTH(pe.dateValue) = 10 AND pe.dateValue > %s THEN p.amount ELSE 0 END) AS Okt,
            SUM(CASE WHEN MONTH(pe.dateValue) = 11 AND pe.dateValue > %s THEN p.amount ELSE 0 END) AS Nov,
            SUM(CASE WHEN MONTH(pe.dateValue) = 12 AND pe.dateValue > %s THEN p.amount ELSE 0 END) AS Dez
          FROM tbl_planning p
            JOIN tbl_planningEntry pe ON pe.planning = p.id
            INNER JOIN tbl_account ON tbl_account.id = p.account
          WHERE YEAR(pe.dateValue) = %s AND tbl_account.name = %s
        ) gesamt_combined
    """

    params = tuple(
        [today]*12 + [year, account] + [today]*12 + [year, account] +  # Haben
        [today]*12 + [year, account] + [today]*12 + [year, account] +  # Soll
        [today]*12 + [year, account] + [today]*12 + [year, account]    # Gesamt
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
    cursor = Depends(get_db_cursor_with_auth)
):
    """
    Get expenses (Soll) breakdown by category for a specific account and year.
    Blends actual transactions (past/today) with planning entries (future).
    """
    from datetime import date
    today = date.today()

    query = """
        SELECT
          cat AS Kategorie,
          SUM(Jan) AS Januar,
          SUM(Feb) AS Februar,
          SUM(Mrz) AS März,
          SUM(Apr) AS April,
          SUM(Mai) AS Mai,
          SUM(Jun) AS Juni,
          SUM(Jul) AS Juli,
          SUM(Aug) AS August,
          SUM(Sep) AS September,
          SUM(Okt) AS Oktober,
          SUM(Nov) AS November,
          SUM(Dez) AS Dezember,
          SUM(Jan+Feb+Mrz+Apr+Mai+Jun+Jul+Aug+Sep+Okt+Nov+Dez) AS Gesamt
        FROM (
          -- Actual transactions up to today
          SELECT
            view_categoryFullname.fullname AS cat,
            SUM(CASE WHEN MONTH(t.dateValue) = 1 AND t.dateValue <= %s AND ae.amount < 0 THEN ae.amount ELSE 0 END) AS Jan,
            SUM(CASE WHEN MONTH(t.dateValue) = 2 AND t.dateValue <= %s AND ae.amount < 0 THEN ae.amount ELSE 0 END) AS Feb,
            SUM(CASE WHEN MONTH(t.dateValue) = 3 AND t.dateValue <= %s AND ae.amount < 0 THEN ae.amount ELSE 0 END) AS Mrz,
            SUM(CASE WHEN MONTH(t.dateValue) = 4 AND t.dateValue <= %s AND ae.amount < 0 THEN ae.amount ELSE 0 END) AS Apr,
            SUM(CASE WHEN MONTH(t.dateValue) = 5 AND t.dateValue <= %s AND ae.amount < 0 THEN ae.amount ELSE 0 END) AS Mai,
            SUM(CASE WHEN MONTH(t.dateValue) = 6 AND t.dateValue <= %s AND ae.amount < 0 THEN ae.amount ELSE 0 END) AS Jun,
            SUM(CASE WHEN MONTH(t.dateValue) = 7 AND t.dateValue <= %s AND ae.amount < 0 THEN ae.amount ELSE 0 END) AS Jul,
            SUM(CASE WHEN MONTH(t.dateValue) = 8 AND t.dateValue <= %s AND ae.amount < 0 THEN ae.amount ELSE 0 END) AS Aug,
            SUM(CASE WHEN MONTH(t.dateValue) = 9 AND t.dateValue <= %s AND ae.amount < 0 THEN ae.amount ELSE 0 END) AS Sep,
            SUM(CASE WHEN MONTH(t.dateValue) = 10 AND t.dateValue <= %s AND ae.amount < 0 THEN ae.amount ELSE 0 END) AS Okt,
            SUM(CASE WHEN MONTH(t.dateValue) = 11 AND t.dateValue <= %s AND ae.amount < 0 THEN ae.amount ELSE 0 END) AS Nov,
            SUM(CASE WHEN MONTH(t.dateValue) = 12 AND t.dateValue <= %s AND ae.amount < 0 THEN ae.amount ELSE 0 END) AS Dez
          FROM tbl_accountingEntry ae
            INNER JOIN tbl_transaction t ON ae.transaction = t.id
            INNER JOIN tbl_account ON tbl_account.id = t.account
            LEFT JOIN view_categoryFullname ON view_categoryFullname.id = ae.category
          WHERE YEAR(t.dateValue) = %s AND tbl_account.name = %s
          GROUP BY view_categoryFullname.fullname
          UNION ALL
          -- Planning entries after today
          SELECT
            view_categoryFullname.fullname AS cat,
            SUM(CASE WHEN MONTH(pe.dateValue) = 1 AND pe.dateValue > %s AND p.amount < 0 THEN p.amount ELSE 0 END) AS Jan,
            SUM(CASE WHEN MONTH(pe.dateValue) = 2 AND pe.dateValue > %s AND p.amount < 0 THEN p.amount ELSE 0 END) AS Feb,
            SUM(CASE WHEN MONTH(pe.dateValue) = 3 AND pe.dateValue > %s AND p.amount < 0 THEN p.amount ELSE 0 END) AS Mrz,
            SUM(CASE WHEN MONTH(pe.dateValue) = 4 AND pe.dateValue > %s AND p.amount < 0 THEN p.amount ELSE 0 END) AS Apr,
            SUM(CASE WHEN MONTH(pe.dateValue) = 5 AND pe.dateValue > %s AND p.amount < 0 THEN p.amount ELSE 0 END) AS Mai,
            SUM(CASE WHEN MONTH(pe.dateValue) = 6 AND pe.dateValue > %s AND p.amount < 0 THEN p.amount ELSE 0 END) AS Jun,
            SUM(CASE WHEN MONTH(pe.dateValue) = 7 AND pe.dateValue > %s AND p.amount < 0 THEN p.amount ELSE 0 END) AS Jul,
            SUM(CASE WHEN MONTH(pe.dateValue) = 8 AND pe.dateValue > %s AND p.amount < 0 THEN p.amount ELSE 0 END) AS Aug,
            SUM(CASE WHEN MONTH(pe.dateValue) = 9 AND pe.dateValue > %s AND p.amount < 0 THEN p.amount ELSE 0 END) AS Sep,
            SUM(CASE WHEN MONTH(pe.dateValue) = 10 AND pe.dateValue > %s AND p.amount < 0 THEN p.amount ELSE 0 END) AS Okt,
            SUM(CASE WHEN MONTH(pe.dateValue) = 11 AND pe.dateValue > %s AND p.amount < 0 THEN p.amount ELSE 0 END) AS Nov,
            SUM(CASE WHEN MONTH(pe.dateValue) = 12 AND pe.dateValue > %s AND p.amount < 0 THEN p.amount ELSE 0 END) AS Dez
          FROM tbl_planning p
            JOIN tbl_planningEntry pe ON pe.planning = p.id
            INNER JOIN tbl_account ON tbl_account.id = p.account
            LEFT JOIN view_categoryFullname ON view_categoryFullname.id = p.category
          WHERE YEAR(pe.dateValue) = %s AND tbl_account.name = %s
          GROUP BY view_categoryFullname.fullname
        ) combined
        GROUP BY cat
        HAVING Gesamt < 0
        ORDER BY cat ASC
    """
    
    params = tuple([today]*12 + [year, account] + [today]*12 + [year, account])
    cursor.execute(query, params)
    rows = cursor.fetchall()
    
    columns = [col[0] for col in cursor.description]
    data = [dict(zip(columns, row)) for row in rows]
    
    return {"year": year, "account": account, "rows": data}


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
    from datetime import date
    today = date.today()

    query = """
        SELECT
          cat AS Kategorie,
          SUM(Jan) AS Januar,
          SUM(Feb) AS Februar,
          SUM(Mrz) AS März,
          SUM(Apr) AS April,
          SUM(Mai) AS Mai,
          SUM(Jun) AS Juni,
          SUM(Jul) AS Juli,
          SUM(Aug) AS August,
          SUM(Sep) AS September,
          SUM(Okt) AS Oktober,
          SUM(Nov) AS November,
          SUM(Dez) AS Dezember,
          SUM(Jan+Feb+Mrz+Apr+Mai+Jun+Jul+Aug+Sep+Okt+Nov+Dez) AS Gesamt
        FROM (
          -- Actual transactions up to today
          SELECT
            view_categoryFullname.fullname AS cat,
            SUM(CASE WHEN MONTH(t.dateValue) = 1 AND t.dateValue <= %s AND ae.amount > 0 THEN ae.amount ELSE 0 END) AS Jan,
            SUM(CASE WHEN MONTH(t.dateValue) = 2 AND t.dateValue <= %s AND ae.amount > 0 THEN ae.amount ELSE 0 END) AS Feb,
            SUM(CASE WHEN MONTH(t.dateValue) = 3 AND t.dateValue <= %s AND ae.amount > 0 THEN ae.amount ELSE 0 END) AS Mrz,
            SUM(CASE WHEN MONTH(t.dateValue) = 4 AND t.dateValue <= %s AND ae.amount > 0 THEN ae.amount ELSE 0 END) AS Apr,
            SUM(CASE WHEN MONTH(t.dateValue) = 5 AND t.dateValue <= %s AND ae.amount > 0 THEN ae.amount ELSE 0 END) AS Mai,
            SUM(CASE WHEN MONTH(t.dateValue) = 6 AND t.dateValue <= %s AND ae.amount > 0 THEN ae.amount ELSE 0 END) AS Jun,
            SUM(CASE WHEN MONTH(t.dateValue) = 7 AND t.dateValue <= %s AND ae.amount > 0 THEN ae.amount ELSE 0 END) AS Jul,
            SUM(CASE WHEN MONTH(t.dateValue) = 8 AND t.dateValue <= %s AND ae.amount > 0 THEN ae.amount ELSE 0 END) AS Aug,
            SUM(CASE WHEN MONTH(t.dateValue) = 9 AND t.dateValue <= %s AND ae.amount > 0 THEN ae.amount ELSE 0 END) AS Sep,
            SUM(CASE WHEN MONTH(t.dateValue) = 10 AND t.dateValue <= %s AND ae.amount > 0 THEN ae.amount ELSE 0 END) AS Okt,
            SUM(CASE WHEN MONTH(t.dateValue) = 11 AND t.dateValue <= %s AND ae.amount > 0 THEN ae.amount ELSE 0 END) AS Nov,
            SUM(CASE WHEN MONTH(t.dateValue) = 12 AND t.dateValue <= %s AND ae.amount > 0 THEN ae.amount ELSE 0 END) AS Dez
          FROM tbl_accountingEntry ae
            INNER JOIN tbl_transaction t ON ae.transaction = t.id
            INNER JOIN tbl_account ON tbl_account.id = t.account
            INNER JOIN tbl_accountType ON tbl_accountType.id = tbl_account.type
            LEFT JOIN view_categoryFullname ON view_categoryFullname.id = ae.category
          WHERE YEAR(t.dateValue) = %s AND tbl_accountType.type = 'Girokonto'
          GROUP BY view_categoryFullname.fullname
          UNION ALL
          -- Planning entries after today
          SELECT
            view_categoryFullname.fullname AS cat,
            SUM(CASE WHEN MONTH(pe.dateValue) = 1 AND pe.dateValue > %s AND p.amount > 0 THEN p.amount ELSE 0 END) AS Jan,
            SUM(CASE WHEN MONTH(pe.dateValue) = 2 AND pe.dateValue > %s AND p.amount > 0 THEN p.amount ELSE 0 END) AS Feb,
            SUM(CASE WHEN MONTH(pe.dateValue) = 3 AND pe.dateValue > %s AND p.amount > 0 THEN p.amount ELSE 0 END) AS Mrz,
            SUM(CASE WHEN MONTH(pe.dateValue) = 4 AND pe.dateValue > %s AND p.amount > 0 THEN p.amount ELSE 0 END) AS Apr,
            SUM(CASE WHEN MONTH(pe.dateValue) = 5 AND pe.dateValue > %s AND p.amount > 0 THEN p.amount ELSE 0 END) AS Mai,
            SUM(CASE WHEN MONTH(pe.dateValue) = 6 AND pe.dateValue > %s AND p.amount > 0 THEN p.amount ELSE 0 END) AS Jun,
            SUM(CASE WHEN MONTH(pe.dateValue) = 7 AND pe.dateValue > %s AND p.amount > 0 THEN p.amount ELSE 0 END) AS Jul,
            SUM(CASE WHEN MONTH(pe.dateValue) = 8 AND pe.dateValue > %s AND p.amount > 0 THEN p.amount ELSE 0 END) AS Aug,
            SUM(CASE WHEN MONTH(pe.dateValue) = 9 AND pe.dateValue > %s AND p.amount > 0 THEN p.amount ELSE 0 END) AS Sep,
            SUM(CASE WHEN MONTH(pe.dateValue) = 10 AND pe.dateValue > %s AND p.amount > 0 THEN p.amount ELSE 0 END) AS Okt,
            SUM(CASE WHEN MONTH(pe.dateValue) = 11 AND pe.dateValue > %s AND p.amount > 0 THEN p.amount ELSE 0 END) AS Nov,
            SUM(CASE WHEN MONTH(pe.dateValue) = 12 AND pe.dateValue > %s AND p.amount > 0 THEN p.amount ELSE 0 END) AS Dez
          FROM tbl_planning p
            JOIN tbl_planningEntry pe ON pe.planning = p.id
            INNER JOIN tbl_account ON tbl_account.id = p.account
            INNER JOIN tbl_accountType ON tbl_accountType.id = tbl_account.type
            LEFT JOIN view_categoryFullname ON view_categoryFullname.id = p.category
          WHERE YEAR(pe.dateValue) = %s AND tbl_accountType.type = 'Girokonto'
          GROUP BY view_categoryFullname.fullname
        ) combined
        GROUP BY cat
        HAVING Gesamt > 0
        ORDER BY cat ASC
    """
    
    params = tuple([today]*12 + [year] + [today]*12 + [year])
    cursor.execute(query, params)
    rows = cursor.fetchall()
    
    columns = [col[0] for col in cursor.description]
    data = [dict(zip(columns, row)) for row in rows]
    
    return {"year": year, "account": "Alle Girokonten", "rows": data}


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
    from datetime import date
    today = date.today()

    query = """
        SELECT
          cat AS Kategorie,
          SUM(Jan) AS Januar,
          SUM(Feb) AS Februar,
          SUM(Mrz) AS März,
          SUM(Apr) AS April,
          SUM(Mai) AS Mai,
          SUM(Jun) AS Juni,
          SUM(Jul) AS Juli,
          SUM(Aug) AS August,
          SUM(Sep) AS September,
          SUM(Okt) AS Oktober,
          SUM(Nov) AS November,
          SUM(Dez) AS Dezember,
          SUM(Jan+Feb+Mrz+Apr+Mai+Jun+Jul+Aug+Sep+Okt+Nov+Dez) AS Gesamt
        FROM (
          -- Actual transactions up to today
          SELECT
            view_categoryFullname.fullname AS cat,
            SUM(CASE WHEN MONTH(t.dateValue) = 1 AND t.dateValue <= %s AND ae.amount < 0 THEN ae.amount ELSE 0 END) AS Jan,
            SUM(CASE WHEN MONTH(t.dateValue) = 2 AND t.dateValue <= %s AND ae.amount < 0 THEN ae.amount ELSE 0 END) AS Feb,
            SUM(CASE WHEN MONTH(t.dateValue) = 3 AND t.dateValue <= %s AND ae.amount < 0 THEN ae.amount ELSE 0 END) AS Mrz,
            SUM(CASE WHEN MONTH(t.dateValue) = 4 AND t.dateValue <= %s AND ae.amount < 0 THEN ae.amount ELSE 0 END) AS Apr,
            SUM(CASE WHEN MONTH(t.dateValue) = 5 AND t.dateValue <= %s AND ae.amount < 0 THEN ae.amount ELSE 0 END) AS Mai,
            SUM(CASE WHEN MONTH(t.dateValue) = 6 AND t.dateValue <= %s AND ae.amount < 0 THEN ae.amount ELSE 0 END) AS Jun,
            SUM(CASE WHEN MONTH(t.dateValue) = 7 AND t.dateValue <= %s AND ae.amount < 0 THEN ae.amount ELSE 0 END) AS Jul,
            SUM(CASE WHEN MONTH(t.dateValue) = 8 AND t.dateValue <= %s AND ae.amount < 0 THEN ae.amount ELSE 0 END) AS Aug,
            SUM(CASE WHEN MONTH(t.dateValue) = 9 AND t.dateValue <= %s AND ae.amount < 0 THEN ae.amount ELSE 0 END) AS Sep,
            SUM(CASE WHEN MONTH(t.dateValue) = 10 AND t.dateValue <= %s AND ae.amount < 0 THEN ae.amount ELSE 0 END) AS Okt,
            SUM(CASE WHEN MONTH(t.dateValue) = 11 AND t.dateValue <= %s AND ae.amount < 0 THEN ae.amount ELSE 0 END) AS Nov,
            SUM(CASE WHEN MONTH(t.dateValue) = 12 AND t.dateValue <= %s AND ae.amount < 0 THEN ae.amount ELSE 0 END) AS Dez
          FROM tbl_accountingEntry ae
            INNER JOIN tbl_transaction t ON ae.transaction = t.id
            INNER JOIN tbl_account ON tbl_account.id = t.account
            INNER JOIN tbl_accountType ON tbl_accountType.id = tbl_account.type
            LEFT JOIN view_categoryFullname ON view_categoryFullname.id = ae.category
          WHERE YEAR(t.dateValue) = %s AND tbl_accountType.type = 'Girokonto'
          GROUP BY view_categoryFullname.fullname
          UNION ALL
          -- Planning entries after today
          SELECT
            view_categoryFullname.fullname AS cat,
            SUM(CASE WHEN MONTH(pe.dateValue) = 1 AND pe.dateValue > %s AND p.amount < 0 THEN p.amount ELSE 0 END) AS Jan,
            SUM(CASE WHEN MONTH(pe.dateValue) = 2 AND pe.dateValue > %s AND p.amount < 0 THEN p.amount ELSE 0 END) AS Feb,
            SUM(CASE WHEN MONTH(pe.dateValue) = 3 AND pe.dateValue > %s AND p.amount < 0 THEN p.amount ELSE 0 END) AS Mrz,
            SUM(CASE WHEN MONTH(pe.dateValue) = 4 AND pe.dateValue > %s AND p.amount < 0 THEN p.amount ELSE 0 END) AS Apr,
            SUM(CASE WHEN MONTH(pe.dateValue) = 5 AND pe.dateValue > %s AND p.amount < 0 THEN p.amount ELSE 0 END) AS Mai,
            SUM(CASE WHEN MONTH(pe.dateValue) = 6 AND pe.dateValue > %s AND p.amount < 0 THEN p.amount ELSE 0 END) AS Jun,
            SUM(CASE WHEN MONTH(pe.dateValue) = 7 AND pe.dateValue > %s AND p.amount < 0 THEN p.amount ELSE 0 END) AS Jul,
            SUM(CASE WHEN MONTH(pe.dateValue) = 8 AND pe.dateValue > %s AND p.amount < 0 THEN p.amount ELSE 0 END) AS Aug,
            SUM(CASE WHEN MONTH(pe.dateValue) = 9 AND pe.dateValue > %s AND p.amount < 0 THEN p.amount ELSE 0 END) AS Sep,
            SUM(CASE WHEN MONTH(pe.dateValue) = 10 AND pe.dateValue > %s AND p.amount < 0 THEN p.amount ELSE 0 END) AS Okt,
            SUM(CASE WHEN MONTH(pe.dateValue) = 11 AND pe.dateValue > %s AND p.amount < 0 THEN p.amount ELSE 0 END) AS Nov,
            SUM(CASE WHEN MONTH(pe.dateValue) = 12 AND pe.dateValue > %s AND p.amount < 0 THEN p.amount ELSE 0 END) AS Dez
          FROM tbl_planning p
            JOIN tbl_planningEntry pe ON pe.planning = p.id
            INNER JOIN tbl_account ON tbl_account.id = p.account
            INNER JOIN tbl_accountType ON tbl_accountType.id = tbl_account.type
            LEFT JOIN view_categoryFullname ON view_categoryFullname.id = p.category
          WHERE YEAR(pe.dateValue) = %s AND tbl_accountType.type = 'Girokonto'
          GROUP BY view_categoryFullname.fullname
        ) combined
        GROUP BY cat
        HAVING Gesamt < 0
        ORDER BY cat ASC
    """
    
    params = tuple([today]*12 + [year] + [today]*12 + [year])
    cursor.execute(query, params)
    rows = cursor.fetchall()
    
    columns = [col[0] for col in cursor.description]
    data = [dict(zip(columns, row)) for row in rows]
    
    return {"year": year, "account": "Alle Girokonten", "rows": data}


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
    from datetime import date
    today = date.today()

    query = """
        -- Haben row (income: positive amounts)
        SELECT 'Haben' AS Kategorie,
          SUM(Jan) AS Januar,
          SUM(Feb) AS Februar,
          SUM(Mrz) AS März,
          SUM(Apr) AS April,
          SUM(Mai) AS Mai,
          SUM(Jun) AS Juni,
          SUM(Jul) AS Juli,
          SUM(Aug) AS August,
          SUM(Sep) AS September,
          SUM(Okt) AS Oktober,
          SUM(Nov) AS November,
          SUM(Dez) AS Dezember,
          SUM(Jan+Feb+Mrz+Apr+Mai+Jun+Jul+Aug+Sep+Okt+Nov+Dez) AS Gesamt
        FROM (
          SELECT
            SUM(CASE WHEN MONTH(t.dateValue) = 1 AND t.dateValue <= %s AND ae.amount > 0 THEN ae.amount ELSE 0 END) AS Jan,
            SUM(CASE WHEN MONTH(t.dateValue) = 2 AND t.dateValue <= %s AND ae.amount > 0 THEN ae.amount ELSE 0 END) AS Feb,
            SUM(CASE WHEN MONTH(t.dateValue) = 3 AND t.dateValue <= %s AND ae.amount > 0 THEN ae.amount ELSE 0 END) AS Mrz,
            SUM(CASE WHEN MONTH(t.dateValue) = 4 AND t.dateValue <= %s AND ae.amount > 0 THEN ae.amount ELSE 0 END) AS Apr,
            SUM(CASE WHEN MONTH(t.dateValue) = 5 AND t.dateValue <= %s AND ae.amount > 0 THEN ae.amount ELSE 0 END) AS Mai,
            SUM(CASE WHEN MONTH(t.dateValue) = 6 AND t.dateValue <= %s AND ae.amount > 0 THEN ae.amount ELSE 0 END) AS Jun,
            SUM(CASE WHEN MONTH(t.dateValue) = 7 AND t.dateValue <= %s AND ae.amount > 0 THEN ae.amount ELSE 0 END) AS Jul,
            SUM(CASE WHEN MONTH(t.dateValue) = 8 AND t.dateValue <= %s AND ae.amount > 0 THEN ae.amount ELSE 0 END) AS Aug,
            SUM(CASE WHEN MONTH(t.dateValue) = 9 AND t.dateValue <= %s AND ae.amount > 0 THEN ae.amount ELSE 0 END) AS Sep,
            SUM(CASE WHEN MONTH(t.dateValue) = 10 AND t.dateValue <= %s AND ae.amount > 0 THEN ae.amount ELSE 0 END) AS Okt,
            SUM(CASE WHEN MONTH(t.dateValue) = 11 AND t.dateValue <= %s AND ae.amount > 0 THEN ae.amount ELSE 0 END) AS Nov,
            SUM(CASE WHEN MONTH(t.dateValue) = 12 AND t.dateValue <= %s AND ae.amount > 0 THEN ae.amount ELSE 0 END) AS Dez
          FROM tbl_accountingEntry ae
            INNER JOIN tbl_transaction t ON ae.transaction = t.id
            INNER JOIN tbl_account ON tbl_account.id = t.account
            INNER JOIN tbl_accountType ON tbl_accountType.id = tbl_account.type
          WHERE YEAR(t.dateValue) = %s AND tbl_accountType.type = 'Girokonto'
          UNION ALL
          SELECT
            SUM(CASE WHEN MONTH(pe.dateValue) = 1 AND pe.dateValue > %s AND p.amount > 0 THEN p.amount ELSE 0 END) AS Jan,
            SUM(CASE WHEN MONTH(pe.dateValue) = 2 AND pe.dateValue > %s AND p.amount > 0 THEN p.amount ELSE 0 END) AS Feb,
            SUM(CASE WHEN MONTH(pe.dateValue) = 3 AND pe.dateValue > %s AND p.amount > 0 THEN p.amount ELSE 0 END) AS Mrz,
            SUM(CASE WHEN MONTH(pe.dateValue) = 4 AND pe.dateValue > %s AND p.amount > 0 THEN p.amount ELSE 0 END) AS Apr,
            SUM(CASE WHEN MONTH(pe.dateValue) = 5 AND pe.dateValue > %s AND p.amount > 0 THEN p.amount ELSE 0 END) AS Mai,
            SUM(CASE WHEN MONTH(pe.dateValue) = 6 AND pe.dateValue > %s AND p.amount > 0 THEN p.amount ELSE 0 END) AS Jun,
            SUM(CASE WHEN MONTH(pe.dateValue) = 7 AND pe.dateValue > %s AND p.amount > 0 THEN p.amount ELSE 0 END) AS Jul,
            SUM(CASE WHEN MONTH(pe.dateValue) = 8 AND pe.dateValue > %s AND p.amount > 0 THEN p.amount ELSE 0 END) AS Aug,
            SUM(CASE WHEN MONTH(pe.dateValue) = 9 AND pe.dateValue > %s AND p.amount > 0 THEN p.amount ELSE 0 END) AS Sep,
            SUM(CASE WHEN MONTH(pe.dateValue) = 10 AND pe.dateValue > %s AND p.amount > 0 THEN p.amount ELSE 0 END) AS Okt,
            SUM(CASE WHEN MONTH(pe.dateValue) = 11 AND pe.dateValue > %s AND p.amount > 0 THEN p.amount ELSE 0 END) AS Nov,
            SUM(CASE WHEN MONTH(pe.dateValue) = 12 AND pe.dateValue > %s AND p.amount > 0 THEN p.amount ELSE 0 END) AS Dez
          FROM tbl_planning p
            JOIN tbl_planningEntry pe ON pe.planning = p.id
            INNER JOIN tbl_account ON tbl_account.id = p.account
            INNER JOIN tbl_accountType ON tbl_accountType.id = tbl_account.type
          WHERE YEAR(pe.dateValue) = %s AND tbl_accountType.type = 'Girokonto'
        ) haben_combined
        UNION ALL
        -- Soll row (expenses: negative amounts)
        SELECT 'Soll' AS Kategorie,
          SUM(Jan) AS Januar,
          SUM(Feb) AS Februar,
          SUM(Mrz) AS März,
          SUM(Apr) AS April,
          SUM(Mai) AS Mai,
          SUM(Jun) AS Juni,
          SUM(Jul) AS Juli,
          SUM(Aug) AS August,
          SUM(Sep) AS September,
          SUM(Okt) AS Oktober,
          SUM(Nov) AS November,
          SUM(Dez) AS Dezember,
          SUM(Jan+Feb+Mrz+Apr+Mai+Jun+Jul+Aug+Sep+Okt+Nov+Dez) AS Gesamt
        FROM (
          SELECT
            SUM(CASE WHEN MONTH(t.dateValue) = 1 AND t.dateValue <= %s AND ae.amount < 0 THEN ae.amount ELSE 0 END) AS Jan,
            SUM(CASE WHEN MONTH(t.dateValue) = 2 AND t.dateValue <= %s AND ae.amount < 0 THEN ae.amount ELSE 0 END) AS Feb,
            SUM(CASE WHEN MONTH(t.dateValue) = 3 AND t.dateValue <= %s AND ae.amount < 0 THEN ae.amount ELSE 0 END) AS Mrz,
            SUM(CASE WHEN MONTH(t.dateValue) = 4 AND t.dateValue <= %s AND ae.amount < 0 THEN ae.amount ELSE 0 END) AS Apr,
            SUM(CASE WHEN MONTH(t.dateValue) = 5 AND t.dateValue <= %s AND ae.amount < 0 THEN ae.amount ELSE 0 END) AS Mai,
            SUM(CASE WHEN MONTH(t.dateValue) = 6 AND t.dateValue <= %s AND ae.amount < 0 THEN ae.amount ELSE 0 END) AS Jun,
            SUM(CASE WHEN MONTH(t.dateValue) = 7 AND t.dateValue <= %s AND ae.amount < 0 THEN ae.amount ELSE 0 END) AS Jul,
            SUM(CASE WHEN MONTH(t.dateValue) = 8 AND t.dateValue <= %s AND ae.amount < 0 THEN ae.amount ELSE 0 END) AS Aug,
            SUM(CASE WHEN MONTH(t.dateValue) = 9 AND t.dateValue <= %s AND ae.amount < 0 THEN ae.amount ELSE 0 END) AS Sep,
            SUM(CASE WHEN MONTH(t.dateValue) = 10 AND t.dateValue <= %s AND ae.amount < 0 THEN ae.amount ELSE 0 END) AS Okt,
            SUM(CASE WHEN MONTH(t.dateValue) = 11 AND t.dateValue <= %s AND ae.amount < 0 THEN ae.amount ELSE 0 END) AS Nov,
            SUM(CASE WHEN MONTH(t.dateValue) = 12 AND t.dateValue <= %s AND ae.amount < 0 THEN ae.amount ELSE 0 END) AS Dez
          FROM tbl_accountingEntry ae
            INNER JOIN tbl_transaction t ON ae.transaction = t.id
            INNER JOIN tbl_account ON tbl_account.id = t.account
            INNER JOIN tbl_accountType ON tbl_accountType.id = tbl_account.type
          WHERE YEAR(t.dateValue) = %s AND tbl_accountType.type = 'Girokonto'
          UNION ALL
          SELECT
            SUM(CASE WHEN MONTH(pe.dateValue) = 1 AND pe.dateValue > %s AND p.amount < 0 THEN p.amount ELSE 0 END) AS Jan,
            SUM(CASE WHEN MONTH(pe.dateValue) = 2 AND pe.dateValue > %s AND p.amount < 0 THEN p.amount ELSE 0 END) AS Feb,
            SUM(CASE WHEN MONTH(pe.dateValue) = 3 AND pe.dateValue > %s AND p.amount < 0 THEN p.amount ELSE 0 END) AS Mrz,
            SUM(CASE WHEN MONTH(pe.dateValue) = 4 AND pe.dateValue > %s AND p.amount < 0 THEN p.amount ELSE 0 END) AS Apr,
            SUM(CASE WHEN MONTH(pe.dateValue) = 5 AND pe.dateValue > %s AND p.amount < 0 THEN p.amount ELSE 0 END) AS Mai,
            SUM(CASE WHEN MONTH(pe.dateValue) = 6 AND pe.dateValue > %s AND p.amount < 0 THEN p.amount ELSE 0 END) AS Jun,
            SUM(CASE WHEN MONTH(pe.dateValue) = 7 AND pe.dateValue > %s AND p.amount < 0 THEN p.amount ELSE 0 END) AS Jul,
            SUM(CASE WHEN MONTH(pe.dateValue) = 8 AND pe.dateValue > %s AND p.amount < 0 THEN p.amount ELSE 0 END) AS Aug,
            SUM(CASE WHEN MONTH(pe.dateValue) = 9 AND pe.dateValue > %s AND p.amount < 0 THEN p.amount ELSE 0 END) AS Sep,
            SUM(CASE WHEN MONTH(pe.dateValue) = 10 AND pe.dateValue > %s AND p.amount < 0 THEN p.amount ELSE 0 END) AS Okt,
            SUM(CASE WHEN MONTH(pe.dateValue) = 11 AND pe.dateValue > %s AND p.amount < 0 THEN p.amount ELSE 0 END) AS Nov,
            SUM(CASE WHEN MONTH(pe.dateValue) = 12 AND pe.dateValue > %s AND p.amount < 0 THEN p.amount ELSE 0 END) AS Dez
          FROM tbl_planning p
            JOIN tbl_planningEntry pe ON pe.planning = p.id
            INNER JOIN tbl_account ON tbl_account.id = p.account
            INNER JOIN tbl_accountType ON tbl_accountType.id = tbl_account.type
          WHERE YEAR(pe.dateValue) = %s AND tbl_accountType.type = 'Girokonto'
        ) soll_combined
        UNION ALL
        -- Gesamt row (net: all amounts)
        SELECT 'Gesamt' AS Kategorie,
          SUM(Jan) AS Januar,
          SUM(Feb) AS Februar,
          SUM(Mrz) AS März,
          SUM(Apr) AS April,
          SUM(Mai) AS Mai,
          SUM(Jun) AS Juni,
          SUM(Jul) AS Juli,
          SUM(Aug) AS August,
          SUM(Sep) AS September,
          SUM(Okt) AS Oktober,
          SUM(Nov) AS November,
          SUM(Dez) AS Dezember,
          SUM(Jan+Feb+Mrz+Apr+Mai+Jun+Jul+Aug+Sep+Okt+Nov+Dez) AS Gesamt
        FROM (
          SELECT
            SUM(CASE WHEN MONTH(t.dateValue) = 1 AND t.dateValue <= %s THEN ae.amount ELSE 0 END) AS Jan,
            SUM(CASE WHEN MONTH(t.dateValue) = 2 AND t.dateValue <= %s THEN ae.amount ELSE 0 END) AS Feb,
            SUM(CASE WHEN MONTH(t.dateValue) = 3 AND t.dateValue <= %s THEN ae.amount ELSE 0 END) AS Mrz,
            SUM(CASE WHEN MONTH(t.dateValue) = 4 AND t.dateValue <= %s THEN ae.amount ELSE 0 END) AS Apr,
            SUM(CASE WHEN MONTH(t.dateValue) = 5 AND t.dateValue <= %s THEN ae.amount ELSE 0 END) AS Mai,
            SUM(CASE WHEN MONTH(t.dateValue) = 6 AND t.dateValue <= %s THEN ae.amount ELSE 0 END) AS Jun,
            SUM(CASE WHEN MONTH(t.dateValue) = 7 AND t.dateValue <= %s THEN ae.amount ELSE 0 END) AS Jul,
            SUM(CASE WHEN MONTH(t.dateValue) = 8 AND t.dateValue <= %s THEN ae.amount ELSE 0 END) AS Aug,
            SUM(CASE WHEN MONTH(t.dateValue) = 9 AND t.dateValue <= %s THEN ae.amount ELSE 0 END) AS Sep,
            SUM(CASE WHEN MONTH(t.dateValue) = 10 AND t.dateValue <= %s THEN ae.amount ELSE 0 END) AS Okt,
            SUM(CASE WHEN MONTH(t.dateValue) = 11 AND t.dateValue <= %s THEN ae.amount ELSE 0 END) AS Nov,
            SUM(CASE WHEN MONTH(t.dateValue) = 12 AND t.dateValue <= %s THEN ae.amount ELSE 0 END) AS Dez
          FROM tbl_accountingEntry ae
            INNER JOIN tbl_transaction t ON ae.transaction = t.id
            INNER JOIN tbl_account ON tbl_account.id = t.account
            INNER JOIN tbl_accountType ON tbl_accountType.id = tbl_account.type
          WHERE YEAR(t.dateValue) = %s AND tbl_accountType.type = 'Girokonto'
          UNION ALL
          SELECT
            SUM(CASE WHEN MONTH(pe.dateValue) = 1 AND pe.dateValue > %s THEN p.amount ELSE 0 END) AS Jan,
            SUM(CASE WHEN MONTH(pe.dateValue) = 2 AND pe.dateValue > %s THEN p.amount ELSE 0 END) AS Feb,
            SUM(CASE WHEN MONTH(pe.dateValue) = 3 AND pe.dateValue > %s THEN p.amount ELSE 0 END) AS Mrz,
            SUM(CASE WHEN MONTH(pe.dateValue) = 4 AND pe.dateValue > %s THEN p.amount ELSE 0 END) AS Apr,
            SUM(CASE WHEN MONTH(pe.dateValue) = 5 AND pe.dateValue > %s THEN p.amount ELSE 0 END) AS Mai,
            SUM(CASE WHEN MONTH(pe.dateValue) = 6 AND pe.dateValue > %s THEN p.amount ELSE 0 END) AS Jun,
            SUM(CASE WHEN MONTH(pe.dateValue) = 7 AND pe.dateValue > %s THEN p.amount ELSE 0 END) AS Jul,
            SUM(CASE WHEN MONTH(pe.dateValue) = 8 AND pe.dateValue > %s THEN p.amount ELSE 0 END) AS Aug,
            SUM(CASE WHEN MONTH(pe.dateValue) = 9 AND pe.dateValue > %s THEN p.amount ELSE 0 END) AS Sep,
            SUM(CASE WHEN MONTH(pe.dateValue) = 10 AND pe.dateValue > %s THEN p.amount ELSE 0 END) AS Okt,
            SUM(CASE WHEN MONTH(pe.dateValue) = 11 AND pe.dateValue > %s THEN p.amount ELSE 0 END) AS Nov,
            SUM(CASE WHEN MONTH(pe.dateValue) = 12 AND pe.dateValue > %s THEN p.amount ELSE 0 END) AS Dez
          FROM tbl_planning p
            JOIN tbl_planningEntry pe ON pe.planning = p.id
            INNER JOIN tbl_account ON tbl_account.id = p.account
            INNER JOIN tbl_accountType ON tbl_accountType.id = tbl_account.type
          WHERE YEAR(pe.dateValue) = %s AND tbl_accountType.type = 'Girokonto'
        ) gesamt_combined
    """

    params = tuple([today]*12 + [year] + [today]*12 + [year] +  # Haben
                   [today]*12 + [year] + [today]*12 + [year] +  # Soll
                   [today]*12 + [year] + [today]*12 + [year])   # Gesamt

    cursor.execute(query, params)
    rows = cursor.fetchall()

    columns = [col[0] for col in cursor.description]
    data = [dict(zip(columns, row)) for row in rows]

    return {"year": year, "account": "Alle Girokonten", "rows": data}


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
    from datetime import date
    today = date.today()

    query = """
        SELECT
          cat AS Kategorie,
          SUM(Jan) AS Januar,
          SUM(Feb) AS Februar,
          SUM(Mrz) AS März,
          SUM(Apr) AS April,
          SUM(Mai) AS Mai,
          SUM(Jun) AS Juni,
          SUM(Jul) AS Juli,
          SUM(Aug) AS August,
          SUM(Sep) AS September,
          SUM(Okt) AS Oktober,
          SUM(Nov) AS November,
          SUM(Dez) AS Dezember,
          SUM(Jan+Feb+Mrz+Apr+Mai+Jun+Jul+Aug+Sep+Okt+Nov+Dez) AS Gesamt
        FROM (
          -- Actual transactions up to today
          SELECT
            view_categoryFullname.fullname AS cat,
            SUM(CASE WHEN MONTH(t.dateValue) = 1 AND t.dateValue <= %s AND ae.amount > 0 THEN ae.amount ELSE 0 END) AS Jan,
            SUM(CASE WHEN MONTH(t.dateValue) = 2 AND t.dateValue <= %s AND ae.amount > 0 THEN ae.amount ELSE 0 END) AS Feb,
            SUM(CASE WHEN MONTH(t.dateValue) = 3 AND t.dateValue <= %s AND ae.amount > 0 THEN ae.amount ELSE 0 END) AS Mrz,
            SUM(CASE WHEN MONTH(t.dateValue) = 4 AND t.dateValue <= %s AND ae.amount > 0 THEN ae.amount ELSE 0 END) AS Apr,
            SUM(CASE WHEN MONTH(t.dateValue) = 5 AND t.dateValue <= %s AND ae.amount > 0 THEN ae.amount ELSE 0 END) AS Mai,
            SUM(CASE WHEN MONTH(t.dateValue) = 6 AND t.dateValue <= %s AND ae.amount > 0 THEN ae.amount ELSE 0 END) AS Jun,
            SUM(CASE WHEN MONTH(t.dateValue) = 7 AND t.dateValue <= %s AND ae.amount > 0 THEN ae.amount ELSE 0 END) AS Jul,
            SUM(CASE WHEN MONTH(t.dateValue) = 8 AND t.dateValue <= %s AND ae.amount > 0 THEN ae.amount ELSE 0 END) AS Aug,
            SUM(CASE WHEN MONTH(t.dateValue) = 9 AND t.dateValue <= %s AND ae.amount > 0 THEN ae.amount ELSE 0 END) AS Sep,
            SUM(CASE WHEN MONTH(t.dateValue) = 10 AND t.dateValue <= %s AND ae.amount > 0 THEN ae.amount ELSE 0 END) AS Okt,
            SUM(CASE WHEN MONTH(t.dateValue) = 11 AND t.dateValue <= %s AND ae.amount > 0 THEN ae.amount ELSE 0 END) AS Nov,
            SUM(CASE WHEN MONTH(t.dateValue) = 12 AND t.dateValue <= %s AND ae.amount > 0 THEN ae.amount ELSE 0 END) AS Dez
          FROM tbl_accountingEntry ae
            INNER JOIN tbl_transaction t ON ae.transaction = t.id
            INNER JOIN tbl_account ON tbl_account.id = t.account
            INNER JOIN tbl_accountType ON tbl_accountType.id = tbl_account.type
            LEFT JOIN view_categoryFullname ON view_categoryFullname.id = ae.category
          WHERE YEAR(t.dateValue) = %s AND tbl_accountType.type = 'Darlehen'
          GROUP BY view_categoryFullname.fullname
          UNION ALL
          -- Planning entries after today
          SELECT
            view_categoryFullname.fullname AS cat,
            SUM(CASE WHEN MONTH(pe.dateValue) = 1 AND pe.dateValue > %s AND p.amount > 0 THEN p.amount ELSE 0 END) AS Jan,
            SUM(CASE WHEN MONTH(pe.dateValue) = 2 AND pe.dateValue > %s AND p.amount > 0 THEN p.amount ELSE 0 END) AS Feb,
            SUM(CASE WHEN MONTH(pe.dateValue) = 3 AND pe.dateValue > %s AND p.amount > 0 THEN p.amount ELSE 0 END) AS Mrz,
            SUM(CASE WHEN MONTH(pe.dateValue) = 4 AND pe.dateValue > %s AND p.amount > 0 THEN p.amount ELSE 0 END) AS Apr,
            SUM(CASE WHEN MONTH(pe.dateValue) = 5 AND pe.dateValue > %s AND p.amount > 0 THEN p.amount ELSE 0 END) AS Mai,
            SUM(CASE WHEN MONTH(pe.dateValue) = 6 AND pe.dateValue > %s AND p.amount > 0 THEN p.amount ELSE 0 END) AS Jun,
            SUM(CASE WHEN MONTH(pe.dateValue) = 7 AND pe.dateValue > %s AND p.amount > 0 THEN p.amount ELSE 0 END) AS Jul,
            SUM(CASE WHEN MONTH(pe.dateValue) = 8 AND pe.dateValue > %s AND p.amount > 0 THEN p.amount ELSE 0 END) AS Aug,
            SUM(CASE WHEN MONTH(pe.dateValue) = 9 AND pe.dateValue > %s AND p.amount > 0 THEN p.amount ELSE 0 END) AS Sep,
            SUM(CASE WHEN MONTH(pe.dateValue) = 10 AND pe.dateValue > %s AND p.amount > 0 THEN p.amount ELSE 0 END) AS Okt,
            SUM(CASE WHEN MONTH(pe.dateValue) = 11 AND pe.dateValue > %s AND p.amount > 0 THEN p.amount ELSE 0 END) AS Nov,
            SUM(CASE WHEN MONTH(pe.dateValue) = 12 AND pe.dateValue > %s AND p.amount > 0 THEN p.amount ELSE 0 END) AS Dez
          FROM tbl_planning p
            JOIN tbl_planningEntry pe ON pe.planning = p.id
            INNER JOIN tbl_account ON tbl_account.id = p.account
            INNER JOIN tbl_accountType ON tbl_accountType.id = tbl_account.type
            LEFT JOIN view_categoryFullname ON view_categoryFullname.id = p.category
          WHERE YEAR(pe.dateValue) = %s AND tbl_accountType.type = 'Darlehen'
          GROUP BY view_categoryFullname.fullname
        ) combined
        GROUP BY cat
        HAVING Gesamt > 0
        ORDER BY cat ASC
    """
    
    params = tuple([today]*12 + [year] + [today]*12 + [year])
    cursor.execute(query, params)
    rows = cursor.fetchall()
    
    columns = [col[0] for col in cursor.description]
    data = [dict(zip(columns, row)) for row in rows]
    
    return {"year": year, "account": "Alle Darlehenskonten", "rows": data}


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
    from datetime import date
    today = date.today()

    query = """
        SELECT
          cat AS Kategorie,
          SUM(Jan) AS Januar,
          SUM(Feb) AS Februar,
          SUM(Mrz) AS März,
          SUM(Apr) AS April,
          SUM(Mai) AS Mai,
          SUM(Jun) AS Juni,
          SUM(Jul) AS Juli,
          SUM(Aug) AS August,
          SUM(Sep) AS September,
          SUM(Okt) AS Oktober,
          SUM(Nov) AS November,
          SUM(Dez) AS Dezember,
          SUM(Jan+Feb+Mrz+Apr+Mai+Jun+Jul+Aug+Sep+Okt+Nov+Dez) AS Gesamt
        FROM (
          -- Actual transactions up to today
          SELECT
            view_categoryFullname.fullname AS cat,
            SUM(CASE WHEN MONTH(t.dateValue) = 1 AND t.dateValue <= %s AND ae.amount < 0 THEN ae.amount ELSE 0 END) AS Jan,
            SUM(CASE WHEN MONTH(t.dateValue) = 2 AND t.dateValue <= %s AND ae.amount < 0 THEN ae.amount ELSE 0 END) AS Feb,
            SUM(CASE WHEN MONTH(t.dateValue) = 3 AND t.dateValue <= %s AND ae.amount < 0 THEN ae.amount ELSE 0 END) AS Mrz,
            SUM(CASE WHEN MONTH(t.dateValue) = 4 AND t.dateValue <= %s AND ae.amount < 0 THEN ae.amount ELSE 0 END) AS Apr,
            SUM(CASE WHEN MONTH(t.dateValue) = 5 AND t.dateValue <= %s AND ae.amount < 0 THEN ae.amount ELSE 0 END) AS Mai,
            SUM(CASE WHEN MONTH(t.dateValue) = 6 AND t.dateValue <= %s AND ae.amount < 0 THEN ae.amount ELSE 0 END) AS Jun,
            SUM(CASE WHEN MONTH(t.dateValue) = 7 AND t.dateValue <= %s AND ae.amount < 0 THEN ae.amount ELSE 0 END) AS Jul,
            SUM(CASE WHEN MONTH(t.dateValue) = 8 AND t.dateValue <= %s AND ae.amount < 0 THEN ae.amount ELSE 0 END) AS Aug,
            SUM(CASE WHEN MONTH(t.dateValue) = 9 AND t.dateValue <= %s AND ae.amount < 0 THEN ae.amount ELSE 0 END) AS Sep,
            SUM(CASE WHEN MONTH(t.dateValue) = 10 AND t.dateValue <= %s AND ae.amount < 0 THEN ae.amount ELSE 0 END) AS Okt,
            SUM(CASE WHEN MONTH(t.dateValue) = 11 AND t.dateValue <= %s AND ae.amount < 0 THEN ae.amount ELSE 0 END) AS Nov,
            SUM(CASE WHEN MONTH(t.dateValue) = 12 AND t.dateValue <= %s AND ae.amount < 0 THEN ae.amount ELSE 0 END) AS Dez
          FROM tbl_accountingEntry ae
            INNER JOIN tbl_transaction t ON ae.transaction = t.id
            INNER JOIN tbl_account ON tbl_account.id = t.account
            INNER JOIN tbl_accountType ON tbl_accountType.id = tbl_account.type
            LEFT JOIN view_categoryFullname ON view_categoryFullname.id = ae.category
          WHERE YEAR(t.dateValue) = %s AND tbl_accountType.type = 'Darlehen'
          GROUP BY view_categoryFullname.fullname
          UNION ALL
          -- Planning entries after today
          SELECT
            view_categoryFullname.fullname AS cat,
            SUM(CASE WHEN MONTH(pe.dateValue) = 1 AND pe.dateValue > %s AND p.amount < 0 THEN p.amount ELSE 0 END) AS Jan,
            SUM(CASE WHEN MONTH(pe.dateValue) = 2 AND pe.dateValue > %s AND p.amount < 0 THEN p.amount ELSE 0 END) AS Feb,
            SUM(CASE WHEN MONTH(pe.dateValue) = 3 AND pe.dateValue > %s AND p.amount < 0 THEN p.amount ELSE 0 END) AS Mrz,
            SUM(CASE WHEN MONTH(pe.dateValue) = 4 AND pe.dateValue > %s AND p.amount < 0 THEN p.amount ELSE 0 END) AS Apr,
            SUM(CASE WHEN MONTH(pe.dateValue) = 5 AND pe.dateValue > %s AND p.amount < 0 THEN p.amount ELSE 0 END) AS Mai,
            SUM(CASE WHEN MONTH(pe.dateValue) = 6 AND pe.dateValue > %s AND p.amount < 0 THEN p.amount ELSE 0 END) AS Jun,
            SUM(CASE WHEN MONTH(pe.dateValue) = 7 AND pe.dateValue > %s AND p.amount < 0 THEN p.amount ELSE 0 END) AS Jul,
            SUM(CASE WHEN MONTH(pe.dateValue) = 8 AND pe.dateValue > %s AND p.amount < 0 THEN p.amount ELSE 0 END) AS Aug,
            SUM(CASE WHEN MONTH(pe.dateValue) = 9 AND pe.dateValue > %s AND p.amount < 0 THEN p.amount ELSE 0 END) AS Sep,
            SUM(CASE WHEN MONTH(pe.dateValue) = 10 AND pe.dateValue > %s AND p.amount < 0 THEN p.amount ELSE 0 END) AS Okt,
            SUM(CASE WHEN MONTH(pe.dateValue) = 11 AND pe.dateValue > %s AND p.amount < 0 THEN p.amount ELSE 0 END) AS Nov,
            SUM(CASE WHEN MONTH(pe.dateValue) = 12 AND pe.dateValue > %s AND p.amount < 0 THEN p.amount ELSE 0 END) AS Dez
          FROM tbl_planning p
            JOIN tbl_planningEntry pe ON pe.planning = p.id
            INNER JOIN tbl_account ON tbl_account.id = p.account
            INNER JOIN tbl_accountType ON tbl_accountType.id = tbl_account.type
            LEFT JOIN view_categoryFullname ON view_categoryFullname.id = p.category
          WHERE YEAR(pe.dateValue) = %s AND tbl_accountType.type = 'Darlehen'
          GROUP BY view_categoryFullname.fullname
        ) combined
        GROUP BY cat
        HAVING Gesamt < 0
        ORDER BY cat ASC
    """
    
    params = tuple([today]*12 + [year] + [today]*12 + [year])
    cursor.execute(query, params)
    rows = cursor.fetchall()
    
    columns = [col[0] for col in cursor.description]
    data = [dict(zip(columns, row)) for row in rows]
    
    return {"year": year, "account": "Alle Darlehenskonten", "rows": data}


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
    from datetime import date
    today = date.today()

    query = """
        -- Haben row (income: positive amounts)
        SELECT 'Haben' AS Kategorie,
          SUM(Jan) AS Januar,
          SUM(Feb) AS Februar,
          SUM(Mrz) AS März,
          SUM(Apr) AS April,
          SUM(Mai) AS Mai,
          SUM(Jun) AS Juni,
          SUM(Jul) AS Juli,
          SUM(Aug) AS August,
          SUM(Sep) AS September,
          SUM(Okt) AS Oktober,
          SUM(Nov) AS November,
          SUM(Dez) AS Dezember,
          SUM(Jan+Feb+Mrz+Apr+Mai+Jun+Jul+Aug+Sep+Okt+Nov+Dez) AS Gesamt
        FROM (
          SELECT
            SUM(CASE WHEN MONTH(t.dateValue) = 1 AND t.dateValue <= %s AND ae.amount > 0 THEN ae.amount ELSE 0 END) AS Jan,
            SUM(CASE WHEN MONTH(t.dateValue) = 2 AND t.dateValue <= %s AND ae.amount > 0 THEN ae.amount ELSE 0 END) AS Feb,
            SUM(CASE WHEN MONTH(t.dateValue) = 3 AND t.dateValue <= %s AND ae.amount > 0 THEN ae.amount ELSE 0 END) AS Mrz,
            SUM(CASE WHEN MONTH(t.dateValue) = 4 AND t.dateValue <= %s AND ae.amount > 0 THEN ae.amount ELSE 0 END) AS Apr,
            SUM(CASE WHEN MONTH(t.dateValue) = 5 AND t.dateValue <= %s AND ae.amount > 0 THEN ae.amount ELSE 0 END) AS Mai,
            SUM(CASE WHEN MONTH(t.dateValue) = 6 AND t.dateValue <= %s AND ae.amount > 0 THEN ae.amount ELSE 0 END) AS Jun,
            SUM(CASE WHEN MONTH(t.dateValue) = 7 AND t.dateValue <= %s AND ae.amount > 0 THEN ae.amount ELSE 0 END) AS Jul,
            SUM(CASE WHEN MONTH(t.dateValue) = 8 AND t.dateValue <= %s AND ae.amount > 0 THEN ae.amount ELSE 0 END) AS Aug,
            SUM(CASE WHEN MONTH(t.dateValue) = 9 AND t.dateValue <= %s AND ae.amount > 0 THEN ae.amount ELSE 0 END) AS Sep,
            SUM(CASE WHEN MONTH(t.dateValue) = 10 AND t.dateValue <= %s AND ae.amount > 0 THEN ae.amount ELSE 0 END) AS Okt,
            SUM(CASE WHEN MONTH(t.dateValue) = 11 AND t.dateValue <= %s AND ae.amount > 0 THEN ae.amount ELSE 0 END) AS Nov,
            SUM(CASE WHEN MONTH(t.dateValue) = 12 AND t.dateValue <= %s AND ae.amount > 0 THEN ae.amount ELSE 0 END) AS Dez
          FROM tbl_accountingEntry ae
            INNER JOIN tbl_transaction t ON ae.transaction = t.id
            INNER JOIN tbl_account ON tbl_account.id = t.account
            INNER JOIN tbl_accountType ON tbl_accountType.id = tbl_account.type
          WHERE YEAR(t.dateValue) = %s AND tbl_accountType.type = 'Darlehen'
          UNION ALL
          SELECT
            SUM(CASE WHEN MONTH(pe.dateValue) = 1 AND pe.dateValue > %s AND p.amount > 0 THEN p.amount ELSE 0 END) AS Jan,
            SUM(CASE WHEN MONTH(pe.dateValue) = 2 AND pe.dateValue > %s AND p.amount > 0 THEN p.amount ELSE 0 END) AS Feb,
            SUM(CASE WHEN MONTH(pe.dateValue) = 3 AND pe.dateValue > %s AND p.amount > 0 THEN p.amount ELSE 0 END) AS Mrz,
            SUM(CASE WHEN MONTH(pe.dateValue) = 4 AND pe.dateValue > %s AND p.amount > 0 THEN p.amount ELSE 0 END) AS Apr,
            SUM(CASE WHEN MONTH(pe.dateValue) = 5 AND pe.dateValue > %s AND p.amount > 0 THEN p.amount ELSE 0 END) AS Mai,
            SUM(CASE WHEN MONTH(pe.dateValue) = 6 AND pe.dateValue > %s AND p.amount > 0 THEN p.amount ELSE 0 END) AS Jun,
            SUM(CASE WHEN MONTH(pe.dateValue) = 7 AND pe.dateValue > %s AND p.amount > 0 THEN p.amount ELSE 0 END) AS Jul,
            SUM(CASE WHEN MONTH(pe.dateValue) = 8 AND pe.dateValue > %s AND p.amount > 0 THEN p.amount ELSE 0 END) AS Aug,
            SUM(CASE WHEN MONTH(pe.dateValue) = 9 AND pe.dateValue > %s AND p.amount > 0 THEN p.amount ELSE 0 END) AS Sep,
            SUM(CASE WHEN MONTH(pe.dateValue) = 10 AND pe.dateValue > %s AND p.amount > 0 THEN p.amount ELSE 0 END) AS Okt,
            SUM(CASE WHEN MONTH(pe.dateValue) = 11 AND pe.dateValue > %s AND p.amount > 0 THEN p.amount ELSE 0 END) AS Nov,
            SUM(CASE WHEN MONTH(pe.dateValue) = 12 AND pe.dateValue > %s AND p.amount > 0 THEN p.amount ELSE 0 END) AS Dez
          FROM tbl_planning p
            JOIN tbl_planningEntry pe ON pe.planning = p.id
            INNER JOIN tbl_account ON tbl_account.id = p.account
            INNER JOIN tbl_accountType ON tbl_accountType.id = tbl_account.type
          WHERE YEAR(pe.dateValue) = %s AND tbl_accountType.type = 'Darlehen'
        ) haben_combined
        UNION ALL
        -- Soll row (expenses: negative amounts)
        SELECT 'Soll' AS Kategorie,
          SUM(Jan) AS Januar,
          SUM(Feb) AS Februar,
          SUM(Mrz) AS März,
          SUM(Apr) AS April,
          SUM(Mai) AS Mai,
          SUM(Jun) AS Juni,
          SUM(Jul) AS Juli,
          SUM(Aug) AS August,
          SUM(Sep) AS September,
          SUM(Okt) AS Oktober,
          SUM(Nov) AS November,
          SUM(Dez) AS Dezember,
          SUM(Jan+Feb+Mrz+Apr+Mai+Jun+Jul+Aug+Sep+Okt+Nov+Dez) AS Gesamt
        FROM (
          SELECT
            SUM(CASE WHEN MONTH(t.dateValue) = 1 AND t.dateValue <= %s AND ae.amount < 0 THEN ae.amount ELSE 0 END) AS Jan,
            SUM(CASE WHEN MONTH(t.dateValue) = 2 AND t.dateValue <= %s AND ae.amount < 0 THEN ae.amount ELSE 0 END) AS Feb,
            SUM(CASE WHEN MONTH(t.dateValue) = 3 AND t.dateValue <= %s AND ae.amount < 0 THEN ae.amount ELSE 0 END) AS Mrz,
            SUM(CASE WHEN MONTH(t.dateValue) = 4 AND t.dateValue <= %s AND ae.amount < 0 THEN ae.amount ELSE 0 END) AS Apr,
            SUM(CASE WHEN MONTH(t.dateValue) = 5 AND t.dateValue <= %s AND ae.amount < 0 THEN ae.amount ELSE 0 END) AS Mai,
            SUM(CASE WHEN MONTH(t.dateValue) = 6 AND t.dateValue <= %s AND ae.amount < 0 THEN ae.amount ELSE 0 END) AS Jun,
            SUM(CASE WHEN MONTH(t.dateValue) = 7 AND t.dateValue <= %s AND ae.amount < 0 THEN ae.amount ELSE 0 END) AS Jul,
            SUM(CASE WHEN MONTH(t.dateValue) = 8 AND t.dateValue <= %s AND ae.amount < 0 THEN ae.amount ELSE 0 END) AS Aug,
            SUM(CASE WHEN MONTH(t.dateValue) = 9 AND t.dateValue <= %s AND ae.amount < 0 THEN ae.amount ELSE 0 END) AS Sep,
            SUM(CASE WHEN MONTH(t.dateValue) = 10 AND t.dateValue <= %s AND ae.amount < 0 THEN ae.amount ELSE 0 END) AS Okt,
            SUM(CASE WHEN MONTH(t.dateValue) = 11 AND t.dateValue <= %s AND ae.amount < 0 THEN ae.amount ELSE 0 END) AS Nov,
            SUM(CASE WHEN MONTH(t.dateValue) = 12 AND t.dateValue <= %s AND ae.amount < 0 THEN ae.amount ELSE 0 END) AS Dez
          FROM tbl_accountingEntry ae
            INNER JOIN tbl_transaction t ON ae.transaction = t.id
            INNER JOIN tbl_account ON tbl_account.id = t.account
            INNER JOIN tbl_accountType ON tbl_accountType.id = tbl_account.type
          WHERE YEAR(t.dateValue) = %s AND tbl_accountType.type = 'Darlehen'
          UNION ALL
          SELECT
            SUM(CASE WHEN MONTH(pe.dateValue) = 1 AND pe.dateValue > %s AND p.amount < 0 THEN p.amount ELSE 0 END) AS Jan,
            SUM(CASE WHEN MONTH(pe.dateValue) = 2 AND pe.dateValue > %s AND p.amount < 0 THEN p.amount ELSE 0 END) AS Feb,
            SUM(CASE WHEN MONTH(pe.dateValue) = 3 AND pe.dateValue > %s AND p.amount < 0 THEN p.amount ELSE 0 END) AS Mrz,
            SUM(CASE WHEN MONTH(pe.dateValue) = 4 AND pe.dateValue > %s AND p.amount < 0 THEN p.amount ELSE 0 END) AS Apr,
            SUM(CASE WHEN MONTH(pe.dateValue) = 5 AND pe.dateValue > %s AND p.amount < 0 THEN p.amount ELSE 0 END) AS Mai,
            SUM(CASE WHEN MONTH(pe.dateValue) = 6 AND pe.dateValue > %s AND p.amount < 0 THEN p.amount ELSE 0 END) AS Jun,
            SUM(CASE WHEN MONTH(pe.dateValue) = 7 AND pe.dateValue > %s AND p.amount < 0 THEN p.amount ELSE 0 END) AS Jul,
            SUM(CASE WHEN MONTH(pe.dateValue) = 8 AND pe.dateValue > %s AND p.amount < 0 THEN p.amount ELSE 0 END) AS Aug,
            SUM(CASE WHEN MONTH(pe.dateValue) = 9 AND pe.dateValue > %s AND p.amount < 0 THEN p.amount ELSE 0 END) AS Sep,
            SUM(CASE WHEN MONTH(pe.dateValue) = 10 AND pe.dateValue > %s AND p.amount < 0 THEN p.amount ELSE 0 END) AS Okt,
            SUM(CASE WHEN MONTH(pe.dateValue) = 11 AND pe.dateValue > %s AND p.amount < 0 THEN p.amount ELSE 0 END) AS Nov,
            SUM(CASE WHEN MONTH(pe.dateValue) = 12 AND pe.dateValue > %s AND p.amount < 0 THEN p.amount ELSE 0 END) AS Dez
          FROM tbl_planning p
            JOIN tbl_planningEntry pe ON pe.planning = p.id
            INNER JOIN tbl_account ON tbl_account.id = p.account
            INNER JOIN tbl_accountType ON tbl_accountType.id = tbl_account.type
          WHERE YEAR(pe.dateValue) = %s AND tbl_accountType.type = 'Darlehen'
        ) soll_combined
        UNION ALL
        -- Gesamt row (net: all amounts)
        SELECT 'Gesamt' AS Kategorie,
          SUM(Jan) AS Januar,
          SUM(Feb) AS Februar,
          SUM(Mrz) AS März,
          SUM(Apr) AS April,
          SUM(Mai) AS Mai,
          SUM(Jun) AS Juni,
          SUM(Jul) AS Juli,
          SUM(Aug) AS August,
          SUM(Sep) AS September,
          SUM(Okt) AS Oktober,
          SUM(Nov) AS November,
          SUM(Dez) AS Dezember,
          SUM(Jan+Feb+Mrz+Apr+Mai+Jun+Jul+Aug+Sep+Okt+Nov+Dez) AS Gesamt
        FROM (
          SELECT
            SUM(CASE WHEN MONTH(t.dateValue) = 1 AND t.dateValue <= %s THEN ae.amount ELSE 0 END) AS Jan,
            SUM(CASE WHEN MONTH(t.dateValue) = 2 AND t.dateValue <= %s THEN ae.amount ELSE 0 END) AS Feb,
            SUM(CASE WHEN MONTH(t.dateValue) = 3 AND t.dateValue <= %s THEN ae.amount ELSE 0 END) AS Mrz,
            SUM(CASE WHEN MONTH(t.dateValue) = 4 AND t.dateValue <= %s THEN ae.amount ELSE 0 END) AS Apr,
            SUM(CASE WHEN MONTH(t.dateValue) = 5 AND t.dateValue <= %s THEN ae.amount ELSE 0 END) AS Mai,
            SUM(CASE WHEN MONTH(t.dateValue) = 6 AND t.dateValue <= %s THEN ae.amount ELSE 0 END) AS Jun,
            SUM(CASE WHEN MONTH(t.dateValue) = 7 AND t.dateValue <= %s THEN ae.amount ELSE 0 END) AS Jul,
            SUM(CASE WHEN MONTH(t.dateValue) = 8 AND t.dateValue <= %s THEN ae.amount ELSE 0 END) AS Aug,
            SUM(CASE WHEN MONTH(t.dateValue) = 9 AND t.dateValue <= %s THEN ae.amount ELSE 0 END) AS Sep,
            SUM(CASE WHEN MONTH(t.dateValue) = 10 AND t.dateValue <= %s THEN ae.amount ELSE 0 END) AS Okt,
            SUM(CASE WHEN MONTH(t.dateValue) = 11 AND t.dateValue <= %s THEN ae.amount ELSE 0 END) AS Nov,
            SUM(CASE WHEN MONTH(t.dateValue) = 12 AND t.dateValue <= %s THEN ae.amount ELSE 0 END) AS Dez
          FROM tbl_accountingEntry ae
            INNER JOIN tbl_transaction t ON ae.transaction = t.id
            INNER JOIN tbl_account ON tbl_account.id = t.account
            INNER JOIN tbl_accountType ON tbl_accountType.id = tbl_account.type
          WHERE YEAR(t.dateValue) = %s AND tbl_accountType.type = 'Darlehen'
          UNION ALL
          SELECT
            SUM(CASE WHEN MONTH(pe.dateValue) = 1 AND pe.dateValue > %s THEN p.amount ELSE 0 END) AS Jan,
            SUM(CASE WHEN MONTH(pe.dateValue) = 2 AND pe.dateValue > %s THEN p.amount ELSE 0 END) AS Feb,
            SUM(CASE WHEN MONTH(pe.dateValue) = 3 AND pe.dateValue > %s THEN p.amount ELSE 0 END) AS Mrz,
            SUM(CASE WHEN MONTH(pe.dateValue) = 4 AND pe.dateValue > %s THEN p.amount ELSE 0 END) AS Apr,
            SUM(CASE WHEN MONTH(pe.dateValue) = 5 AND pe.dateValue > %s THEN p.amount ELSE 0 END) AS Mai,
            SUM(CASE WHEN MONTH(pe.dateValue) = 6 AND pe.dateValue > %s THEN p.amount ELSE 0 END) AS Jun,
            SUM(CASE WHEN MONTH(pe.dateValue) = 7 AND pe.dateValue > %s THEN p.amount ELSE 0 END) AS Jul,
            SUM(CASE WHEN MONTH(pe.dateValue) = 8 AND pe.dateValue > %s THEN p.amount ELSE 0 END) AS Aug,
            SUM(CASE WHEN MONTH(pe.dateValue) = 9 AND pe.dateValue > %s THEN p.amount ELSE 0 END) AS Sep,
            SUM(CASE WHEN MONTH(pe.dateValue) = 10 AND pe.dateValue > %s THEN p.amount ELSE 0 END) AS Okt,
            SUM(CASE WHEN MONTH(pe.dateValue) = 11 AND pe.dateValue > %s THEN p.amount ELSE 0 END) AS Nov,
            SUM(CASE WHEN MONTH(pe.dateValue) = 12 AND pe.dateValue > %s THEN p.amount ELSE 0 END) AS Dez
          FROM tbl_planning p
            JOIN tbl_planningEntry pe ON pe.planning = p.id
            INNER JOIN tbl_account ON tbl_account.id = p.account
            INNER JOIN tbl_accountType ON tbl_accountType.id = tbl_account.type
          WHERE YEAR(pe.dateValue) = %s AND tbl_accountType.type = 'Darlehen'
        ) gesamt_combined
    """

    params = tuple([today]*12 + [year] + [today]*12 + [year] +  # Haben
                   [today]*12 + [year] + [today]*12 + [year] +  # Soll
                   [today]*12 + [year] + [today]*12 + [year])   # Gesamt

    cursor.execute(query, params)
    rows = cursor.fetchall()

    columns = [col[0] for col in cursor.description]
    data = [dict(zip(columns, row)) for row in rows]

    return {"year": year, "account": "Alle Darlehenskonten", "rows": data}


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
    from datetime import date
    today = date.today()

    query = """
        SELECT
          cat AS Kategorie,
          SUM(Jan) AS Januar,
          SUM(Feb) AS Februar,
          SUM(Mrz) AS März,
          SUM(Apr) AS April,
          SUM(Mai) AS Mai,
          SUM(Jun) AS Juni,
          SUM(Jul) AS Juli,
          SUM(Aug) AS August,
          SUM(Sep) AS September,
          SUM(Okt) AS Oktober,
          SUM(Nov) AS November,
          SUM(Dez) AS Dezember,
          SUM(Jan+Feb+Mrz+Apr+Mai+Jun+Jul+Aug+Sep+Okt+Nov+Dez) AS Gesamt
        FROM (
          -- Actual transactions up to today
          SELECT
            view_categoryFullname.fullname AS cat,
            SUM(CASE WHEN MONTH(t.dateValue) = 1 AND t.dateValue <= %s AND ae.amount > 0 THEN ae.amount ELSE 0 END) AS Jan,
            SUM(CASE WHEN MONTH(t.dateValue) = 2 AND t.dateValue <= %s AND ae.amount > 0 THEN ae.amount ELSE 0 END) AS Feb,
            SUM(CASE WHEN MONTH(t.dateValue) = 3 AND t.dateValue <= %s AND ae.amount > 0 THEN ae.amount ELSE 0 END) AS Mrz,
            SUM(CASE WHEN MONTH(t.dateValue) = 4 AND t.dateValue <= %s AND ae.amount > 0 THEN ae.amount ELSE 0 END) AS Apr,
            SUM(CASE WHEN MONTH(t.dateValue) = 5 AND t.dateValue <= %s AND ae.amount > 0 THEN ae.amount ELSE 0 END) AS Mai,
            SUM(CASE WHEN MONTH(t.dateValue) = 6 AND t.dateValue <= %s AND ae.amount > 0 THEN ae.amount ELSE 0 END) AS Jun,
            SUM(CASE WHEN MONTH(t.dateValue) = 7 AND t.dateValue <= %s AND ae.amount > 0 THEN ae.amount ELSE 0 END) AS Jul,
            SUM(CASE WHEN MONTH(t.dateValue) = 8 AND t.dateValue <= %s AND ae.amount > 0 THEN ae.amount ELSE 0 END) AS Aug,
            SUM(CASE WHEN MONTH(t.dateValue) = 9 AND t.dateValue <= %s AND ae.amount > 0 THEN ae.amount ELSE 0 END) AS Sep,
            SUM(CASE WHEN MONTH(t.dateValue) = 10 AND t.dateValue <= %s AND ae.amount > 0 THEN ae.amount ELSE 0 END) AS Okt,
            SUM(CASE WHEN MONTH(t.dateValue) = 11 AND t.dateValue <= %s AND ae.amount > 0 THEN ae.amount ELSE 0 END) AS Nov,
            SUM(CASE WHEN MONTH(t.dateValue) = 12 AND t.dateValue <= %s AND ae.amount > 0 THEN ae.amount ELSE 0 END) AS Dez
          FROM tbl_accountingEntry ae
            INNER JOIN tbl_transaction t ON ae.transaction = t.id
            INNER JOIN tbl_account ON tbl_account.id = t.account
            INNER JOIN tbl_accountType ON tbl_accountType.id = tbl_account.type
            LEFT JOIN view_categoryFullname ON view_categoryFullname.id = ae.category
          WHERE YEAR(t.dateValue) = %s AND tbl_accountType.type IN ('Girokonto', 'Darlehen')
          GROUP BY view_categoryFullname.fullname
          UNION ALL
          -- Planning entries after today
          SELECT
            view_categoryFullname.fullname AS cat,
            SUM(CASE WHEN MONTH(pe.dateValue) = 1 AND pe.dateValue > %s AND p.amount > 0 THEN p.amount ELSE 0 END) AS Jan,
            SUM(CASE WHEN MONTH(pe.dateValue) = 2 AND pe.dateValue > %s AND p.amount > 0 THEN p.amount ELSE 0 END) AS Feb,
            SUM(CASE WHEN MONTH(pe.dateValue) = 3 AND pe.dateValue > %s AND p.amount > 0 THEN p.amount ELSE 0 END) AS Mrz,
            SUM(CASE WHEN MONTH(pe.dateValue) = 4 AND pe.dateValue > %s AND p.amount > 0 THEN p.amount ELSE 0 END) AS Apr,
            SUM(CASE WHEN MONTH(pe.dateValue) = 5 AND pe.dateValue > %s AND p.amount > 0 THEN p.amount ELSE 0 END) AS Mai,
            SUM(CASE WHEN MONTH(pe.dateValue) = 6 AND pe.dateValue > %s AND p.amount > 0 THEN p.amount ELSE 0 END) AS Jun,
            SUM(CASE WHEN MONTH(pe.dateValue) = 7 AND pe.dateValue > %s AND p.amount > 0 THEN p.amount ELSE 0 END) AS Jul,
            SUM(CASE WHEN MONTH(pe.dateValue) = 8 AND pe.dateValue > %s AND p.amount > 0 THEN p.amount ELSE 0 END) AS Aug,
            SUM(CASE WHEN MONTH(pe.dateValue) = 9 AND pe.dateValue > %s AND p.amount > 0 THEN p.amount ELSE 0 END) AS Sep,
            SUM(CASE WHEN MONTH(pe.dateValue) = 10 AND pe.dateValue > %s AND p.amount > 0 THEN p.amount ELSE 0 END) AS Okt,
            SUM(CASE WHEN MONTH(pe.dateValue) = 11 AND pe.dateValue > %s AND p.amount > 0 THEN p.amount ELSE 0 END) AS Nov,
            SUM(CASE WHEN MONTH(pe.dateValue) = 12 AND pe.dateValue > %s AND p.amount > 0 THEN p.amount ELSE 0 END) AS Dez
          FROM tbl_planning p
            JOIN tbl_planningEntry pe ON pe.planning = p.id
            INNER JOIN tbl_account ON tbl_account.id = p.account
            INNER JOIN tbl_accountType ON tbl_accountType.id = tbl_account.type
            LEFT JOIN view_categoryFullname ON view_categoryFullname.id = p.category
          WHERE YEAR(pe.dateValue) = %s AND tbl_accountType.type IN ('Girokonto', 'Darlehen')
          GROUP BY view_categoryFullname.fullname
        ) combined
        GROUP BY cat
        HAVING Gesamt > 0
        ORDER BY cat ASC
    """
    
    params = tuple([today]*12 + [year] + [today]*12 + [year])
    cursor.execute(query, params)
    rows = cursor.fetchall()
    
    columns = [col[0] for col in cursor.description]
    data = [dict(zip(columns, row)) for row in rows]
    
    return {"year": year, "account": "Alle Darlehens- und Girokonten", "rows": data}


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
    from datetime import date
    today = date.today()

    query = """
        SELECT
          cat AS Kategorie,
          SUM(Jan) AS Januar,
          SUM(Feb) AS Februar,
          SUM(Mrz) AS März,
          SUM(Apr) AS April,
          SUM(Mai) AS Mai,
          SUM(Jun) AS Juni,
          SUM(Jul) AS Juli,
          SUM(Aug) AS August,
          SUM(Sep) AS September,
          SUM(Okt) AS Oktober,
          SUM(Nov) AS November,
          SUM(Dez) AS Dezember,
          SUM(Jan+Feb+Mrz+Apr+Mai+Jun+Jul+Aug+Sep+Okt+Nov+Dez) AS Gesamt
        FROM (
          -- Actual transactions up to today
          SELECT
            view_categoryFullname.fullname AS cat,
            SUM(CASE WHEN MONTH(t.dateValue) = 1 AND t.dateValue <= %s AND ae.amount < 0 THEN ae.amount ELSE 0 END) AS Jan,
            SUM(CASE WHEN MONTH(t.dateValue) = 2 AND t.dateValue <= %s AND ae.amount < 0 THEN ae.amount ELSE 0 END) AS Feb,
            SUM(CASE WHEN MONTH(t.dateValue) = 3 AND t.dateValue <= %s AND ae.amount < 0 THEN ae.amount ELSE 0 END) AS Mrz,
            SUM(CASE WHEN MONTH(t.dateValue) = 4 AND t.dateValue <= %s AND ae.amount < 0 THEN ae.amount ELSE 0 END) AS Apr,
            SUM(CASE WHEN MONTH(t.dateValue) = 5 AND t.dateValue <= %s AND ae.amount < 0 THEN ae.amount ELSE 0 END) AS Mai,
            SUM(CASE WHEN MONTH(t.dateValue) = 6 AND t.dateValue <= %s AND ae.amount < 0 THEN ae.amount ELSE 0 END) AS Jun,
            SUM(CASE WHEN MONTH(t.dateValue) = 7 AND t.dateValue <= %s AND ae.amount < 0 THEN ae.amount ELSE 0 END) AS Jul,
            SUM(CASE WHEN MONTH(t.dateValue) = 8 AND t.dateValue <= %s AND ae.amount < 0 THEN ae.amount ELSE 0 END) AS Aug,
            SUM(CASE WHEN MONTH(t.dateValue) = 9 AND t.dateValue <= %s AND ae.amount < 0 THEN ae.amount ELSE 0 END) AS Sep,
            SUM(CASE WHEN MONTH(t.dateValue) = 10 AND t.dateValue <= %s AND ae.amount < 0 THEN ae.amount ELSE 0 END) AS Okt,
            SUM(CASE WHEN MONTH(t.dateValue) = 11 AND t.dateValue <= %s AND ae.amount < 0 THEN ae.amount ELSE 0 END) AS Nov,
            SUM(CASE WHEN MONTH(t.dateValue) = 12 AND t.dateValue <= %s AND ae.amount < 0 THEN ae.amount ELSE 0 END) AS Dez
          FROM tbl_accountingEntry ae
            INNER JOIN tbl_transaction t ON ae.transaction = t.id
            INNER JOIN tbl_account ON tbl_account.id = t.account
            INNER JOIN tbl_accountType ON tbl_accountType.id = tbl_account.type
            LEFT JOIN view_categoryFullname ON view_categoryFullname.id = ae.category
          WHERE YEAR(t.dateValue) = %s AND tbl_accountType.type IN ('Girokonto', 'Darlehen')
          GROUP BY view_categoryFullname.fullname
          UNION ALL
          -- Planning entries after today
          SELECT
            view_categoryFullname.fullname AS cat,
            SUM(CASE WHEN MONTH(pe.dateValue) = 1 AND pe.dateValue > %s AND p.amount < 0 THEN p.amount ELSE 0 END) AS Jan,
            SUM(CASE WHEN MONTH(pe.dateValue) = 2 AND pe.dateValue > %s AND p.amount < 0 THEN p.amount ELSE 0 END) AS Feb,
            SUM(CASE WHEN MONTH(pe.dateValue) = 3 AND pe.dateValue > %s AND p.amount < 0 THEN p.amount ELSE 0 END) AS Mrz,
            SUM(CASE WHEN MONTH(pe.dateValue) = 4 AND pe.dateValue > %s AND p.amount < 0 THEN p.amount ELSE 0 END) AS Apr,
            SUM(CASE WHEN MONTH(pe.dateValue) = 5 AND pe.dateValue > %s AND p.amount < 0 THEN p.amount ELSE 0 END) AS Mai,
            SUM(CASE WHEN MONTH(pe.dateValue) = 6 AND pe.dateValue > %s AND p.amount < 0 THEN p.amount ELSE 0 END) AS Jun,
            SUM(CASE WHEN MONTH(pe.dateValue) = 7 AND pe.dateValue > %s AND p.amount < 0 THEN p.amount ELSE 0 END) AS Jul,
            SUM(CASE WHEN MONTH(pe.dateValue) = 8 AND pe.dateValue > %s AND p.amount < 0 THEN p.amount ELSE 0 END) AS Aug,
            SUM(CASE WHEN MONTH(pe.dateValue) = 9 AND pe.dateValue > %s AND p.amount < 0 THEN p.amount ELSE 0 END) AS Sep,
            SUM(CASE WHEN MONTH(pe.dateValue) = 10 AND pe.dateValue > %s AND p.amount < 0 THEN p.amount ELSE 0 END) AS Okt,
            SUM(CASE WHEN MONTH(pe.dateValue) = 11 AND pe.dateValue > %s AND p.amount < 0 THEN p.amount ELSE 0 END) AS Nov,
            SUM(CASE WHEN MONTH(pe.dateValue) = 12 AND pe.dateValue > %s AND p.amount < 0 THEN p.amount ELSE 0 END) AS Dez
          FROM tbl_planning p
            JOIN tbl_planningEntry pe ON pe.planning = p.id
            INNER JOIN tbl_account ON tbl_account.id = p.account
            INNER JOIN tbl_accountType ON tbl_accountType.id = tbl_account.type
            LEFT JOIN view_categoryFullname ON view_categoryFullname.id = p.category
          WHERE YEAR(pe.dateValue) = %s AND tbl_accountType.type IN ('Girokonto', 'Darlehen')
          GROUP BY view_categoryFullname.fullname
        ) combined
        GROUP BY cat
        HAVING Gesamt < 0
        ORDER BY cat ASC
    """
    
    params = tuple([today]*12 + [year] + [today]*12 + [year])
    cursor.execute(query, params)
    rows = cursor.fetchall()
    
    columns = [col[0] for col in cursor.description]
    data = [dict(zip(columns, row)) for row in rows]
    
    return {"year": year, "account": "Alle Darlehens- und Girokonten", "rows": data}


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
    from datetime import date
    today = date.today()

    query = """
        -- Haben row (income: positive amounts)
        SELECT 'Haben' AS Kategorie,
          SUM(Jan) AS Januar,
          SUM(Feb) AS Februar,
          SUM(Mrz) AS März,
          SUM(Apr) AS April,
          SUM(Mai) AS Mai,
          SUM(Jun) AS Juni,
          SUM(Jul) AS Juli,
          SUM(Aug) AS August,
          SUM(Sep) AS September,
          SUM(Okt) AS Oktober,
          SUM(Nov) AS November,
          SUM(Dez) AS Dezember,
          SUM(Jan+Feb+Mrz+Apr+Mai+Jun+Jul+Aug+Sep+Okt+Nov+Dez) AS Gesamt
        FROM (
          SELECT
            SUM(CASE WHEN MONTH(t.dateValue) = 1 AND t.dateValue <= %s AND ae.amount > 0 THEN ae.amount ELSE 0 END) AS Jan,
            SUM(CASE WHEN MONTH(t.dateValue) = 2 AND t.dateValue <= %s AND ae.amount > 0 THEN ae.amount ELSE 0 END) AS Feb,
            SUM(CASE WHEN MONTH(t.dateValue) = 3 AND t.dateValue <= %s AND ae.amount > 0 THEN ae.amount ELSE 0 END) AS Mrz,
            SUM(CASE WHEN MONTH(t.dateValue) = 4 AND t.dateValue <= %s AND ae.amount > 0 THEN ae.amount ELSE 0 END) AS Apr,
            SUM(CASE WHEN MONTH(t.dateValue) = 5 AND t.dateValue <= %s AND ae.amount > 0 THEN ae.amount ELSE 0 END) AS Mai,
            SUM(CASE WHEN MONTH(t.dateValue) = 6 AND t.dateValue <= %s AND ae.amount > 0 THEN ae.amount ELSE 0 END) AS Jun,
            SUM(CASE WHEN MONTH(t.dateValue) = 7 AND t.dateValue <= %s AND ae.amount > 0 THEN ae.amount ELSE 0 END) AS Jul,
            SUM(CASE WHEN MONTH(t.dateValue) = 8 AND t.dateValue <= %s AND ae.amount > 0 THEN ae.amount ELSE 0 END) AS Aug,
            SUM(CASE WHEN MONTH(t.dateValue) = 9 AND t.dateValue <= %s AND ae.amount > 0 THEN ae.amount ELSE 0 END) AS Sep,
            SUM(CASE WHEN MONTH(t.dateValue) = 10 AND t.dateValue <= %s AND ae.amount > 0 THEN ae.amount ELSE 0 END) AS Okt,
            SUM(CASE WHEN MONTH(t.dateValue) = 11 AND t.dateValue <= %s AND ae.amount > 0 THEN ae.amount ELSE 0 END) AS Nov,
            SUM(CASE WHEN MONTH(t.dateValue) = 12 AND t.dateValue <= %s AND ae.amount > 0 THEN ae.amount ELSE 0 END) AS Dez
          FROM tbl_accountingEntry ae
            INNER JOIN tbl_transaction t ON ae.transaction = t.id
            INNER JOIN tbl_account ON tbl_account.id = t.account
            INNER JOIN tbl_accountType ON tbl_accountType.id = tbl_account.type
          WHERE YEAR(t.dateValue) = %s AND tbl_accountType.type IN ('Girokonto', 'Darlehen')
          UNION ALL
          SELECT
            SUM(CASE WHEN MONTH(pe.dateValue) = 1 AND pe.dateValue > %s AND p.amount > 0 THEN p.amount ELSE 0 END) AS Jan,
            SUM(CASE WHEN MONTH(pe.dateValue) = 2 AND pe.dateValue > %s AND p.amount > 0 THEN p.amount ELSE 0 END) AS Feb,
            SUM(CASE WHEN MONTH(pe.dateValue) = 3 AND pe.dateValue > %s AND p.amount > 0 THEN p.amount ELSE 0 END) AS Mrz,
            SUM(CASE WHEN MONTH(pe.dateValue) = 4 AND pe.dateValue > %s AND p.amount > 0 THEN p.amount ELSE 0 END) AS Apr,
            SUM(CASE WHEN MONTH(pe.dateValue) = 5 AND pe.dateValue > %s AND p.amount > 0 THEN p.amount ELSE 0 END) AS Mai,
            SUM(CASE WHEN MONTH(pe.dateValue) = 6 AND pe.dateValue > %s AND p.amount > 0 THEN p.amount ELSE 0 END) AS Jun,
            SUM(CASE WHEN MONTH(pe.dateValue) = 7 AND pe.dateValue > %s AND p.amount > 0 THEN p.amount ELSE 0 END) AS Jul,
            SUM(CASE WHEN MONTH(pe.dateValue) = 8 AND pe.dateValue > %s AND p.amount > 0 THEN p.amount ELSE 0 END) AS Aug,
            SUM(CASE WHEN MONTH(pe.dateValue) = 9 AND pe.dateValue > %s AND p.amount > 0 THEN p.amount ELSE 0 END) AS Sep,
            SUM(CASE WHEN MONTH(pe.dateValue) = 10 AND pe.dateValue > %s AND p.amount > 0 THEN p.amount ELSE 0 END) AS Okt,
            SUM(CASE WHEN MONTH(pe.dateValue) = 11 AND pe.dateValue > %s AND p.amount > 0 THEN p.amount ELSE 0 END) AS Nov,
            SUM(CASE WHEN MONTH(pe.dateValue) = 12 AND pe.dateValue > %s AND p.amount > 0 THEN p.amount ELSE 0 END) AS Dez
          FROM tbl_planning p
            JOIN tbl_planningEntry pe ON pe.planning = p.id
            INNER JOIN tbl_account ON tbl_account.id = p.account
            INNER JOIN tbl_accountType ON tbl_accountType.id = tbl_account.type
          WHERE YEAR(pe.dateValue) = %s AND tbl_accountType.type IN ('Girokonto', 'Darlehen')
        ) haben_combined
        UNION ALL
        -- Soll row (expenses: negative amounts)
        SELECT 'Soll' AS Kategorie,
          SUM(Jan) AS Januar,
          SUM(Feb) AS Februar,
          SUM(Mrz) AS März,
          SUM(Apr) AS April,
          SUM(Mai) AS Mai,
          SUM(Jun) AS Juni,
          SUM(Jul) AS Juli,
          SUM(Aug) AS August,
          SUM(Sep) AS September,
          SUM(Okt) AS Oktober,
          SUM(Nov) AS November,
          SUM(Dez) AS Dezember,
          SUM(Jan+Feb+Mrz+Apr+Mai+Jun+Jul+Aug+Sep+Okt+Nov+Dez) AS Gesamt
        FROM (
          SELECT
            SUM(CASE WHEN MONTH(t.dateValue) = 1 AND t.dateValue <= %s AND ae.amount < 0 THEN ae.amount ELSE 0 END) AS Jan,
            SUM(CASE WHEN MONTH(t.dateValue) = 2 AND t.dateValue <= %s AND ae.amount < 0 THEN ae.amount ELSE 0 END) AS Feb,
            SUM(CASE WHEN MONTH(t.dateValue) = 3 AND t.dateValue <= %s AND ae.amount < 0 THEN ae.amount ELSE 0 END) AS Mrz,
            SUM(CASE WHEN MONTH(t.dateValue) = 4 AND t.dateValue <= %s AND ae.amount < 0 THEN ae.amount ELSE 0 END) AS Apr,
            SUM(CASE WHEN MONTH(t.dateValue) = 5 AND t.dateValue <= %s AND ae.amount < 0 THEN ae.amount ELSE 0 END) AS Mai,
            SUM(CASE WHEN MONTH(t.dateValue) = 6 AND t.dateValue <= %s AND ae.amount < 0 THEN ae.amount ELSE 0 END) AS Jun,
            SUM(CASE WHEN MONTH(t.dateValue) = 7 AND t.dateValue <= %s AND ae.amount < 0 THEN ae.amount ELSE 0 END) AS Jul,
            SUM(CASE WHEN MONTH(t.dateValue) = 8 AND t.dateValue <= %s AND ae.amount < 0 THEN ae.amount ELSE 0 END) AS Aug,
            SUM(CASE WHEN MONTH(t.dateValue) = 9 AND t.dateValue <= %s AND ae.amount < 0 THEN ae.amount ELSE 0 END) AS Sep,
            SUM(CASE WHEN MONTH(t.dateValue) = 10 AND t.dateValue <= %s AND ae.amount < 0 THEN ae.amount ELSE 0 END) AS Okt,
            SUM(CASE WHEN MONTH(t.dateValue) = 11 AND t.dateValue <= %s AND ae.amount < 0 THEN ae.amount ELSE 0 END) AS Nov,
            SUM(CASE WHEN MONTH(t.dateValue) = 12 AND t.dateValue <= %s AND ae.amount < 0 THEN ae.amount ELSE 0 END) AS Dez
          FROM tbl_accountingEntry ae
            INNER JOIN tbl_transaction t ON ae.transaction = t.id
            INNER JOIN tbl_account ON tbl_account.id = t.account
            INNER JOIN tbl_accountType ON tbl_accountType.id = tbl_account.type
          WHERE YEAR(t.dateValue) = %s AND tbl_accountType.type IN ('Girokonto', 'Darlehen')
          UNION ALL
          SELECT
            SUM(CASE WHEN MONTH(pe.dateValue) = 1 AND pe.dateValue > %s AND p.amount < 0 THEN p.amount ELSE 0 END) AS Jan,
            SUM(CASE WHEN MONTH(pe.dateValue) = 2 AND pe.dateValue > %s AND p.amount < 0 THEN p.amount ELSE 0 END) AS Feb,
            SUM(CASE WHEN MONTH(pe.dateValue) = 3 AND pe.dateValue > %s AND p.amount < 0 THEN p.amount ELSE 0 END) AS Mrz,
            SUM(CASE WHEN MONTH(pe.dateValue) = 4 AND pe.dateValue > %s AND p.amount < 0 THEN p.amount ELSE 0 END) AS Apr,
            SUM(CASE WHEN MONTH(pe.dateValue) = 5 AND pe.dateValue > %s AND p.amount < 0 THEN p.amount ELSE 0 END) AS Mai,
            SUM(CASE WHEN MONTH(pe.dateValue) = 6 AND pe.dateValue > %s AND p.amount < 0 THEN p.amount ELSE 0 END) AS Jun,
            SUM(CASE WHEN MONTH(pe.dateValue) = 7 AND pe.dateValue > %s AND p.amount < 0 THEN p.amount ELSE 0 END) AS Jul,
            SUM(CASE WHEN MONTH(pe.dateValue) = 8 AND pe.dateValue > %s AND p.amount < 0 THEN p.amount ELSE 0 END) AS Aug,
            SUM(CASE WHEN MONTH(pe.dateValue) = 9 AND pe.dateValue > %s AND p.amount < 0 THEN p.amount ELSE 0 END) AS Sep,
            SUM(CASE WHEN MONTH(pe.dateValue) = 10 AND pe.dateValue > %s AND p.amount < 0 THEN p.amount ELSE 0 END) AS Okt,
            SUM(CASE WHEN MONTH(pe.dateValue) = 11 AND pe.dateValue > %s AND p.amount < 0 THEN p.amount ELSE 0 END) AS Nov,
            SUM(CASE WHEN MONTH(pe.dateValue) = 12 AND pe.dateValue > %s AND p.amount < 0 THEN p.amount ELSE 0 END) AS Dez
          FROM tbl_planning p
            JOIN tbl_planningEntry pe ON pe.planning = p.id
            INNER JOIN tbl_account ON tbl_account.id = p.account
            INNER JOIN tbl_accountType ON tbl_accountType.id = tbl_account.type
          WHERE YEAR(pe.dateValue) = %s AND tbl_accountType.type IN ('Girokonto', 'Darlehen')
        ) soll_combined
        UNION ALL
        -- Gesamt row (net: all amounts)
        SELECT 'Gesamt' AS Kategorie,
          SUM(Jan) AS Januar,
          SUM(Feb) AS Februar,
          SUM(Mrz) AS März,
          SUM(Apr) AS April,
          SUM(Mai) AS Mai,
          SUM(Jun) AS Juni,
          SUM(Jul) AS Juli,
          SUM(Aug) AS August,
          SUM(Sep) AS September,
          SUM(Okt) AS Oktober,
          SUM(Nov) AS November,
          SUM(Dez) AS Dezember,
          SUM(Jan+Feb+Mrz+Apr+Mai+Jun+Jul+Aug+Sep+Okt+Nov+Dez) AS Gesamt
        FROM (
          SELECT
            SUM(CASE WHEN MONTH(t.dateValue) = 1 AND t.dateValue <= %s THEN ae.amount ELSE 0 END) AS Jan,
            SUM(CASE WHEN MONTH(t.dateValue) = 2 AND t.dateValue <= %s THEN ae.amount ELSE 0 END) AS Feb,
            SUM(CASE WHEN MONTH(t.dateValue) = 3 AND t.dateValue <= %s THEN ae.amount ELSE 0 END) AS Mrz,
            SUM(CASE WHEN MONTH(t.dateValue) = 4 AND t.dateValue <= %s THEN ae.amount ELSE 0 END) AS Apr,
            SUM(CASE WHEN MONTH(t.dateValue) = 5 AND t.dateValue <= %s THEN ae.amount ELSE 0 END) AS Mai,
            SUM(CASE WHEN MONTH(t.dateValue) = 6 AND t.dateValue <= %s THEN ae.amount ELSE 0 END) AS Jun,
            SUM(CASE WHEN MONTH(t.dateValue) = 7 AND t.dateValue <= %s THEN ae.amount ELSE 0 END) AS Jul,
            SUM(CASE WHEN MONTH(t.dateValue) = 8 AND t.dateValue <= %s THEN ae.amount ELSE 0 END) AS Aug,
            SUM(CASE WHEN MONTH(t.dateValue) = 9 AND t.dateValue <= %s THEN ae.amount ELSE 0 END) AS Sep,
            SUM(CASE WHEN MONTH(t.dateValue) = 10 AND t.dateValue <= %s THEN ae.amount ELSE 0 END) AS Okt,
            SUM(CASE WHEN MONTH(t.dateValue) = 11 AND t.dateValue <= %s THEN ae.amount ELSE 0 END) AS Nov,
            SUM(CASE WHEN MONTH(t.dateValue) = 12 AND t.dateValue <= %s THEN ae.amount ELSE 0 END) AS Dez
          FROM tbl_accountingEntry ae
            INNER JOIN tbl_transaction t ON ae.transaction = t.id
            INNER JOIN tbl_account ON tbl_account.id = t.account
            INNER JOIN tbl_accountType ON tbl_accountType.id = tbl_account.type
          WHERE YEAR(t.dateValue) = %s AND tbl_accountType.type IN ('Girokonto', 'Darlehen')
          UNION ALL
          SELECT
            SUM(CASE WHEN MONTH(pe.dateValue) = 1 AND pe.dateValue > %s THEN p.amount ELSE 0 END) AS Jan,
            SUM(CASE WHEN MONTH(pe.dateValue) = 2 AND pe.dateValue > %s THEN p.amount ELSE 0 END) AS Feb,
            SUM(CASE WHEN MONTH(pe.dateValue) = 3 AND pe.dateValue > %s THEN p.amount ELSE 0 END) AS Mrz,
            SUM(CASE WHEN MONTH(pe.dateValue) = 4 AND pe.dateValue > %s THEN p.amount ELSE 0 END) AS Apr,
            SUM(CASE WHEN MONTH(pe.dateValue) = 5 AND pe.dateValue > %s THEN p.amount ELSE 0 END) AS Mai,
            SUM(CASE WHEN MONTH(pe.dateValue) = 6 AND pe.dateValue > %s THEN p.amount ELSE 0 END) AS Jun,
            SUM(CASE WHEN MONTH(pe.dateValue) = 7 AND pe.dateValue > %s THEN p.amount ELSE 0 END) AS Jul,
            SUM(CASE WHEN MONTH(pe.dateValue) = 8 AND pe.dateValue > %s THEN p.amount ELSE 0 END) AS Aug,
            SUM(CASE WHEN MONTH(pe.dateValue) = 9 AND pe.dateValue > %s THEN p.amount ELSE 0 END) AS Sep,
            SUM(CASE WHEN MONTH(pe.dateValue) = 10 AND pe.dateValue > %s THEN p.amount ELSE 0 END) AS Okt,
            SUM(CASE WHEN MONTH(pe.dateValue) = 11 AND pe.dateValue > %s THEN p.amount ELSE 0 END) AS Nov,
            SUM(CASE WHEN MONTH(pe.dateValue) = 12 AND pe.dateValue > %s THEN p.amount ELSE 0 END) AS Dez
          FROM tbl_planning p
            JOIN tbl_planningEntry pe ON pe.planning = p.id
            INNER JOIN tbl_account ON tbl_account.id = p.account
            INNER JOIN tbl_accountType ON tbl_accountType.id = tbl_account.type
          WHERE YEAR(pe.dateValue) = %s AND tbl_accountType.type IN ('Girokonto', 'Darlehen')
        ) gesamt_combined
    """

    params = tuple([today]*12 + [year] + [today]*12 + [year] +  # Haben
                   [today]*12 + [year] + [today]*12 + [year] +  # Soll
                   [today]*12 + [year] + [today]*12 + [year])   # Gesamt

    cursor.execute(query, params)
    rows = cursor.fetchall()

    columns = [col[0] for col in cursor.description]
    data = [dict(zip(columns, row)) for row in rows]

    return {"year": year, "account": "Alle Darlehens- und Girokonten", "rows": data}


@router.get("/girokonto/list")
@handle_db_errors("fetch account list")
async def get_account_list(cursor = Depends(get_db_cursor_with_auth)):
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
async def get_account_types(cursor = Depends(get_db_cursor_with_auth)):
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
async def get_import_formats(cursor = Depends(get_db_cursor_with_auth)):
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
    cursor = Depends(get_db_cursor_with_auth)
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
    cursor = Depends(get_db_cursor_with_auth),
    connection = Depends(get_db_connection_with_auth)
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
    
    connection.commit() # finding: There is a 'safe_commit' function instead of connection.commit().
    
    # finding: Here should be also 'safe_rollback' in case of errors during commit.

    # Return updated account
    return await get_account_detail(account_id, cursor)


@router.delete("/{account_id}")
@handle_db_errors("delete account")
async def delete_account(
    account_id: int = Path(..., gt=0),
    cursor = Depends(get_db_cursor_with_auth),
    connection = Depends(get_db_connection_with_auth)
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
    
    connection.commit() # finding: There is a 'safe_commit' function instead of connection.commit().
    
    return {"message": "Konto erfolgreich gelöscht"}



