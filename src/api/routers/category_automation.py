"""
Category Automation API router - for automated transaction categorization rules
"""

from fastapi import APIRouter, Depends, Query, HTTPException, Path
from typing import Optional, List
from pydantic import BaseModel
import json
import re
from api.dependencies import get_db_cursor, get_db_connection
from api.error_handling import handle_db_errors

router = APIRouter(prefix="/category-automation", tags=["category-automation"])


class RuleData(BaseModel):
    """Model for category automation rule"""
    type: str  # contains, equals, startsWith, endsWith, regex, amountRange
    columnName: str  # description, recipientApplicant, amount, iban
    value: Optional[str] = None
    caseSensitive: bool = False
    minAmount: Optional[float] = None
    maxAmount: Optional[float] = None
    priority: int = 1
    account: int
    category: int


class RuleTestData(BaseModel):
    """Model for transaction data when testing a rule"""
    description: str
    recipientApplicant: Optional[str] = None
    amount: Optional[str] = None
    iban: Optional[str] = None


class TestRuleRequest(BaseModel):
    """Payload for testing a rule"""
    rule: RuleData
    transaction: RuleTestData


class AutomationRuleResponse(BaseModel):
    """Response model for automation rule"""
    id: int
    type: str
    columnName: str
    value: Optional[str]
    caseSensitive: bool
    minAmount: Optional[float]
    maxAmount: Optional[float]
    priority: int
    account: int
    account_name: str
    category: int
    category_name: str


@router.get("/list")
@handle_db_errors("fetch category automation rules")
async def get_automation_rules(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=1000),
    account: Optional[int] = Query(None, description="Filter by account ID"),
    cursor = Depends(get_db_cursor)
):
    """Get paginated list of category automation rules."""

    # Get total count
    count_query = "SELECT COUNT(*) FROM tbl_categoryAutomation"
    params = []

    if account:
        count_query += " WHERE account = %s"
        params = [account]

    cursor.execute(count_query, params)
    total = cursor.fetchone()[0]

    # Get paginated data
    offset = (page - 1) * page_size
    query = """
        SELECT 
            tbl_categoryAutomation.id,
            tbl_categoryAutomation.columnName,
            tbl_categoryAutomation.rule,
            tbl_categoryAutomation.category,
            tbl_categoryAutomation.account,
            tbl_account.name as account_name,
            tbl_category.name as category_name
        FROM tbl_categoryAutomation
        LEFT JOIN tbl_account ON tbl_account.id = tbl_categoryAutomation.account
        LEFT JOIN tbl_category ON tbl_category.id = tbl_categoryAutomation.category
    """

    if account:
        query += " WHERE tbl_categoryAutomation.account = %s"

    query += " ORDER BY tbl_categoryAutomation.id DESC"
    query += " LIMIT %s OFFSET %s"

    if account:
        cursor.execute(query, [account, page_size, offset])
    else:
        cursor.execute(query, [page_size, offset])

    rows = cursor.fetchall()

    rules = []
    for row in rows:
        rule_data = {}
        try:
            if row[2]:
                rule_data = json.loads(row[2])
        except (json.JSONDecodeError, ValueError):
            # If rule data is invalid JSON, use empty dict
            rule_data = {}

        rules.append({
            "id": row[0],
            "type": rule_data.get("type", "contains"),
            "columnName": row[1],
            "value": rule_data.get("value"),
            "caseSensitive": rule_data.get("caseSensitive", False),
            "minAmount": rule_data.get("minAmount"),
            "maxAmount": rule_data.get("maxAmount"),
            "priority": rule_data.get("priority", 1),
            "account": row[4],
            "account_name": row[5],
            "category": row[3],
            "category_name": row[6]
        })

    return {
        "rules": rules,
        "page": page,
        "page_size": page_size,
        "total": total
    }


@router.post("/test-rule")
@handle_db_errors("test category automation rule")
async def test_rule(
    payload: TestRuleRequest,
    cursor = Depends(get_db_cursor)
):
    """Test a rule against sample transaction data."""

    # Normalize amount from string to float (or None)
    raw_amount = payload.transaction.amount
    amt = None
    if raw_amount is not None and str(raw_amount).strip():
        try:
            amt = float(raw_amount)
        except (ValueError, TypeError):
            amt = None

    transaction = {
        "description": payload.transaction.description,
        "recipientApplicant": payload.transaction.recipientApplicant or None,
        "amount": amt,
        "iban": payload.transaction.iban,
    }

    rule = {
        "columnName": payload.rule.columnName
    }

    rule_json = json.dumps({
        "type": payload.rule.type,
        "value": payload.rule.value,
        "caseSensitive": payload.rule.caseSensitive,
        "minAmount": payload.rule.minAmount,
        "maxAmount": payload.rule.maxAmount,
        "priority": payload.rule.priority
    })

    matches = evaluate_rule(transaction, rule, rule_json)

    return {
        "matches": matches,
        "message": "Regel passt" if matches else "Regel passt nicht"
    }
    
    rows = cursor.fetchall()
    
    rules = []
    for row in rows:
        rule_data = {}
        try:
            if row[2]:
                rule_data = json.loads(row[2])
        except (json.JSONDecodeError, ValueError):
            # If rule data is invalid JSON, use empty dict
            rule_data = {}
        
        rules.append({
            "id": row[0],
            "type": rule_data.get("type", "contains"),
            "columnName": row[1],
            "value": rule_data.get("value"),
            "caseSensitive": rule_data.get("caseSensitive", False),
            "minAmount": rule_data.get("minAmount"),
            "maxAmount": rule_data.get("maxAmount"),
            "priority": rule_data.get("priority", 1),
            "account": row[4],
            "account_name": row[5],
            "category": row[3],
            "category_name": row[6]
        })
    
    return {
        "rules": rules,
        "page": page,
        "page_size": page_size,
        "total": total
    }


@router.post("/")
@handle_db_errors("create category automation rule")
async def create_automation_rule(
    rule_data: RuleData,
    cursor = Depends(get_db_cursor),
    connection = Depends(get_db_connection)
):
    """Create a new category automation rule."""
    
    # Validate rule data
    if not rule_data.type:
        raise HTTPException(status_code=400, detail="Regeltyp erforderlich")
    
    if not rule_data.columnName:
        raise HTTPException(status_code=400, detail="Spaltennamen erforderlich")
    
    # Store rule as JSON
    rule_json = json.dumps({
        "type": rule_data.type,
        "value": rule_data.value,
        "caseSensitive": rule_data.caseSensitive,
        "minAmount": rule_data.minAmount,
        "maxAmount": rule_data.maxAmount,
        "priority": rule_data.priority
    })
    
    insert_query = """
        INSERT INTO tbl_categoryAutomation (dateImport, columnName, rule, category, account)
        VALUES (NOW(), %s, %s, %s, %s)
    """
    
    cursor.execute(insert_query, (
        rule_data.columnName,
        rule_json,
        rule_data.category,
        rule_data.account
    ))
    
    connection.commit()
    rule_id = cursor.lastrowid
    
    return {"id": rule_id, "message": "Regel erfolgreich erstellt"}


@router.get("/{rule_id}")
@handle_db_errors("fetch category automation rule")
async def get_automation_rule(
    rule_id: int = Path(..., gt=0),
    cursor = Depends(get_db_cursor)
):
    """Get details of a specific automation rule."""
    
    query = """
        SELECT 
            tbl_categoryAutomation.id,
            tbl_categoryAutomation.columnName,
            tbl_categoryAutomation.rule,
            tbl_categoryAutomation.category,
            tbl_categoryAutomation.account,
            tbl_account.name as account_name,
            tbl_category.name as category_name
        FROM tbl_categoryAutomation
        LEFT JOIN tbl_account ON tbl_account.id = tbl_categoryAutomation.account
        LEFT JOIN tbl_category ON tbl_category.id = tbl_categoryAutomation.category
        WHERE tbl_categoryAutomation.id = %s
    """
    
    cursor.execute(query, (rule_id,))
    row = cursor.fetchone()
    
    if not row:
        raise HTTPException(status_code=404, detail="Regel nicht gefunden")
    
    rule_data = {}
    try:
        if row[2]:
            rule_data = json.loads(row[2])
    except (json.JSONDecodeError, ValueError):
        rule_data = {}
    
    return {
        "id": row[0],
        "type": rule_data.get("type", "contains"),
        "columnName": row[1],
        "value": rule_data.get("value"),
        "caseSensitive": rule_data.get("caseSensitive", False),
        "minAmount": rule_data.get("minAmount"),
        "maxAmount": rule_data.get("maxAmount"),
        "priority": rule_data.get("priority", 1),
        "account": row[4],
        "account_name": row[5],
        "category": row[3],
        "category_name": row[6]
    }


@router.put("/{rule_id}")
@handle_db_errors("update category automation rule")
async def update_automation_rule(
    rule_id: int = Path(..., gt=0),
    rule_data: RuleData = None,
    cursor = Depends(get_db_cursor),
    connection = Depends(get_db_connection)
):
    """Update a category automation rule."""
    
    if not rule_data:
        raise HTTPException(status_code=400, detail="Keine Daten übergeben")
    
    # Store rule as JSON
    rule_json = json.dumps({
        "type": rule_data.type,
        "value": rule_data.value,
        "caseSensitive": rule_data.caseSensitive,
        "minAmount": rule_data.minAmount,
        "maxAmount": rule_data.maxAmount,
        "priority": rule_data.priority
    })
    
    update_query = """
        UPDATE tbl_categoryAutomation
        SET columnName = %s, rule = %s, category = %s, account = %s
        WHERE id = %s
    """
    
    cursor.execute(update_query, (
        rule_data.columnName,
        rule_json,
        rule_data.category,
        rule_data.account,
        rule_id
    ))
    
    connection.commit()
    
    return await get_automation_rule(rule_id, cursor)


@router.delete("/{rule_id}")
@handle_db_errors("delete category automation rule")
async def delete_automation_rule(
    rule_id: int = Path(..., gt=0),
    cursor = Depends(get_db_cursor),
    connection = Depends(get_db_connection)
):
    """Delete a category automation rule."""
    
    delete_query = "DELETE FROM tbl_categoryAutomation WHERE id = %s"
    cursor.execute(delete_query, (rule_id,))
    connection.commit()
    
    return {"message": "Regel erfolgreich gelöscht"}


# ==================== Rule Engine ====================

def evaluate_rule(transaction: dict, rule: dict, rule_json: str) -> bool:
    """
    Evaluate if a transaction matches a rule.
    
    Args:
        transaction: Transaction data with columns (description, recipientApplicant, amount, iban)
        rule: Rule metadata (columnName, account)
        rule_json: Rule definition as JSON string
        
    Returns:
        True if rule matches, False otherwise
    """
    try:
        rule_def = json.loads(rule_json)
    except:
        return False
    
    rule_type = rule_def.get("type", "contains")
    column_name = rule.get("columnName")
    value = rule_def.get("value")
    case_sensitive = rule_def.get("caseSensitive", False)
    
    # Get value from transaction
    tx_value = transaction.get(column_name)
    if tx_value is None:
        return False
    
    # Convert to string for comparison (except for amount)
    if column_name != "amount":
        tx_value = str(tx_value)
        if not case_sensitive:
            tx_value = tx_value.lower()
            value = value.lower() if value else ""
    
    # Evaluate based on rule type
    if rule_type == "contains":
        return value in tx_value if value else False
    
    elif rule_type == "equals":
        return tx_value == value
    
    elif rule_type == "startsWith":
        return tx_value.startswith(value) if value else False
    
    elif rule_type == "endsWith":
        return tx_value.endswith(value) if value else False
    
    elif rule_type == "regex":
        try:
            flags = 0 if case_sensitive else re.IGNORECASE
            return bool(re.search(value, tx_value, flags))
        except:
            return False
    
    elif rule_type == "amountRange":
        try:
            tx_amount = float(tx_value)
            min_amount = rule_def.get("minAmount")
            max_amount = rule_def.get("maxAmount")
            
            if min_amount is not None and tx_amount < min_amount:
                return False
            if max_amount is not None and tx_amount > max_amount:
                return False
            return True
        except:
            return False
    
    return False


