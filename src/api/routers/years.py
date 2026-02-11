"""
Years API router - provides available years for dropdown
"""

from fastapi import APIRouter, Depends
from api.dependencies import get_db_cursor_with_auth
from api.error_handling import handle_db_errors

router = APIRouter(prefix="/years", tags=["years"])


@router.get("/")
@handle_db_errors("fetch available years")
async def get_available_years(cursor=Depends(get_db_cursor_with_auth)):
    """
    Get all available years from transactions.
    Returns years in descending order (newest first).
    """
    query = """
        SELECT DISTINCT YEAR(tbl_transaction.dateValue) AS year
        FROM tbl_transaction
        WHERE YEAR(tbl_transaction.dateValue) <= (YEAR(CURDATE())+1)
        ORDER BY YEAR(tbl_transaction.dateValue) DESC
    """
    
    cursor.execute(query)
    rows = cursor.fetchall()
    
    years = [row[0] for row in rows]
    
    return {"years": years}
