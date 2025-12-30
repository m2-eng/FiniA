"""
Loan management API router
"""

from fastapi import APIRouter, Depends, Query, HTTPException, Path, Body
from typing import Optional
from pydantic import BaseModel
from api.dependencies import get_db_cursor, get_db_connection
from api.error_handling import handle_db_errors
from datetime import datetime

router = APIRouter(prefix="/loans", tags=["loans"])


class LoanBase(BaseModel):
    """Base model for loan data"""
    intrestRate: Optional[float] = None
    account: int
    categoryRebooking: Optional[int] = None
    categoryIntrest: Optional[int] = None


class LoanCreate(LoanBase):
    """Model for creating a new loan"""
    pass


class LoanUpdate(LoanBase):
    """Model for updating an existing loan"""
    pass


@router.get("/list")
@handle_db_errors("fetch loans")
async def list_loans(cursor=Depends(get_db_cursor)):
    """
    Get list of all loans with account and category details
    """
    query = """
        SELECT 
            l.id,
            l.dateImport,
            l.intrestRate,
            l.account,
            a.name AS accountName,
            l.categoryRebooking,
            cr.fullname AS categoryRebookingName,
            l.categoryIntrest,
            ci.fullname AS categoryIntrestName
        FROM tbl_loan l
        LEFT JOIN tbl_account a ON l.account = a.id
        LEFT JOIN view_categoryFullname cr ON l.categoryRebooking = cr.id
        LEFT JOIN view_categoryFullname ci ON l.categoryIntrest = ci.id
        ORDER BY a.name, l.id
    """
    
    cursor.execute(query)
    rows = cursor.fetchall()
    
    columns = [col[0] for col in cursor.description]
    data = [dict(zip(columns, row)) for row in rows]
    
    return {"loans": data}


@router.get("/{loan_id}")
@handle_db_errors("fetch loan details")
async def get_loan(loan_id: int = Path(..., gt=0), cursor=Depends(get_db_cursor)):
    """
    Get details of a specific loan
    """
    query = """
        SELECT 
            l.id,
            l.dateImport,
            l.intrestRate,
            l.account,
            a.name AS accountName,
            l.categoryRebooking,
            cr.fullname AS categoryRebookingName,
            l.categoryIntrest,
            ci.fullname AS categoryIntrestName
        FROM tbl_loan l
        LEFT JOIN tbl_account a ON l.account = a.id
        LEFT JOIN view_categoryFullname cr ON l.categoryRebooking = cr.id
        LEFT JOIN view_categoryFullname ci ON l.categoryIntrest = ci.id
        WHERE l.id = %s
    """
    
    cursor.execute(query, (loan_id,))
    row = cursor.fetchone()
    
    if not row:
        raise HTTPException(status_code=404, detail=f"Loan {loan_id} not found")
    
    columns = [col[0] for col in cursor.description]
    return dict(zip(columns, row))


@router.post("/create")
@handle_db_errors("create loan")
async def create_loan(loan: LoanCreate, cursor=Depends(get_db_cursor), connection=Depends(get_db_connection)):
    """
    Create a new loan
    """
    query = """
        INSERT INTO tbl_loan (dateImport, intrestRate, account, categoryRebooking, categoryIntrest)
        VALUES (%s, %s, %s, %s, %s)
    """
    
    try:
        cursor.execute(query, (
            datetime.now(),
            loan.intrestRate,
            loan.account,
            loan.categoryRebooking,
            loan.categoryIntrest
        ))
        connection.commit()
        loan_id = cursor.lastrowid
        return {"id": loan_id, "message": "Loan created successfully"}
    except Exception as e:
        connection.rollback()
        raise HTTPException(status_code=400, detail=f"Error creating loan: {str(e)}")


@router.put("/{loan_id}")
async def update_loan(
    loan_id: int = Path(..., gt=0),
    loan: LoanUpdate = Body(...),
    cursor=Depends(get_db_cursor),
    connection=Depends(get_db_connection)
):
    """
    Update an existing loan
    """
    # First check if loan exists
    cursor.execute("SELECT id FROM tbl_loan WHERE id = %s", (loan_id,))
    if not cursor.fetchone():
        raise HTTPException(status_code=404, detail=f"Loan {loan_id} not found")
    
    query = """
        UPDATE tbl_loan 
        SET intrestRate = %s, account = %s, categoryRebooking = %s, categoryIntrest = %s
        WHERE id = %s
    """
    
    try:
        cursor.execute(query, (
            loan.intrestRate,
            loan.account,
            loan.categoryRebooking,
            loan.categoryIntrest,
            loan_id
        ))
        
        connection.commit()
        return {"message": "Loan updated successfully"}
    except Exception as e:
        connection.rollback()
        raise HTTPException(status_code=400, detail=f"Error updating loan: {str(e)}")


@router.delete("/{loan_id}")
@handle_db_errors("delete loan")
async def delete_loan(loan_id: int = Path(..., gt=0), cursor=Depends(get_db_cursor), connection=Depends(get_db_connection)):
    """
    Delete a loan
    """
    try:
        # First delete related loanSumExclude entries
        cursor.execute("DELETE FROM tbl_loanSumExclude WHERE loanId = %s", (loan_id,))
        
        # Then delete the loan
        cursor.execute("DELETE FROM tbl_loan WHERE id = %s", (loan_id,))
        
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail=f"Loan {loan_id} not found")
        
        connection.commit()
        return {"message": "Loan deleted successfully"}
    except Exception as e:
        connection.rollback()
        raise HTTPException(status_code=400, detail=f"Error deleting loan: {str(e)}")


@router.get("/accounts/list")
@handle_db_errors("fetch loan accounts")
async def list_accounts(cursor=Depends(get_db_cursor)):
    """
    Get list of all accounts that are configured as loan accounts (have entries in tbl_loan)
    """
    query = """
        SELECT DISTINCT a.id, a.name
        FROM tbl_account a
        INNER JOIN tbl_loan l ON a.id = l.account
        ORDER BY a.name
    """
    
    cursor.execute(query)
    rows = cursor.fetchall()
    
    accounts = [{"id": row[0], "name": row[1]} for row in rows]
    return {"accounts": accounts}
