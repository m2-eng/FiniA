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
from services.category_automation import (
    evaluate_rule,
    load_rules,
    parse_condition_logic
)
from uuid import uuid4
from datetime import datetime

router = APIRouter(prefix="/category-automation", tags=["category-automation"])


class RuleTestData(BaseModel):
    """Model for transaction data when testing a rule"""
    description: str
    recipientApplicant: Optional[str] = None
    amount: Optional[str] = None
    iban: Optional[str] = None

class Condition(BaseModel):
    """Single condition in a rule"""
    id: int
    type: str  # contains, equals, startsWith, endsWith, regex, amountRange
    columnName: str  # description, recipientApplicant, amount, iban
    value: Optional[str] = None
    caseSensitive: bool = False
    minAmount: Optional[float] = None
    maxAmount: Optional[float] = None


class RuleData(BaseModel):
    """Complete rule structure"""
    id: Optional[str] = None  # UUID, auto-generated if not provided
    name: str
    description: Optional[str] = None
    conditions: List[Condition]
    conditionLogic: Optional[str] = None  # e.g., "(1 OR 2) AND 3"
    category: int
    accounts: List[int] = []  # Empty = all accounts
    priority: int = 5
    enabled: bool = True


class RuleResponse(BaseModel):
    """Response model for rule"""
    id: str
    name: str
    description: Optional[str]
    conditions: List[dict]
    conditionLogic: Optional[str]
    category: int
    category_name: Optional[str]
    accounts: List[int]
    priority: int
    enabled: bool
    dateCreated: str
    dateModified: str


class TestRuleRequest(BaseModel):
    """Payload for testing a rule"""
    rule: RuleData
    transaction: RuleTestData


@router.get("/rules")
@handle_db_errors("fetch category automation rules")
async def get_rules(
    account: Optional[int] = Query(None, description="Filter by account ID"),
    enabled_only: bool = Query(True, description="Only return enabled rules"),
    cursor = Depends(get_db_cursor)
):
    """
    Get all automation rules from settings table.
    Returns rules sorted by priority (descending).
    """
    query = """
        SELECT id, value
        FROM tbl_setting
        WHERE `key` = 'category_automation_rule'
    """
    
    cursor.execute(query)
    rows = cursor.fetchall()
    
    rules = []
    for row in rows:
        try:
            rule = json.loads(row[1])
            
            # Filter by enabled status
            if enabled_only and not rule.get('enabled', True):
                continue
            
            # Filter by account
            if account is not None:
                rule_accounts = rule.get('accounts', [])
                if rule_accounts and account not in rule_accounts:
                    continue
            
            # Fetch category name
            category_id = rule.get('category')
            cursor.execute(
                "SELECT name FROM tbl_category WHERE id = %s",
                (category_id,)
            )
            cat_row = cursor.fetchone()
            category_name = cat_row[0] if cat_row else None
            
            rules.append({
                "id": rule.get('id'),
                "name": rule.get('name'),
                "description": rule.get('description'),
                "conditions": rule.get('conditions', []),
                "conditionLogic": rule.get('conditionLogic'),
                "category": category_id,
                "category_name": category_name,
                "accounts": rule.get('accounts', []),
                "priority": rule.get('priority', 5),
                "enabled": rule.get('enabled', True),
                "dateCreated": rule.get('dateCreated'),
                "dateModified": rule.get('dateModified')
            })
            
        except (json.JSONDecodeError, KeyError) as e:
            print(f"Warning: Failed to parse rule {row[0]}: {e}")
            continue
    
    # Sort by priority descending
    rules.sort(key=lambda r: r['priority'], reverse=True)
    
    return {
        "rules": rules,
        "total": len(rules)
    }


@router.get("/rules/{rule_id}")
@handle_db_errors("fetch rule by ID")
async def get_rule_by_id(
    rule_id: str = Path(..., description="Rule UUID"),
    cursor = Depends(get_db_cursor)
):
    """Get a specific rule by ID."""
    query = """
        SELECT id, value
        FROM tbl_setting
        WHERE `key` = 'category_automation_rule'
          AND JSON_EXTRACT(value, '$.id') = %s
    """
    
    cursor.execute(query, (rule_id,))
    row = cursor.fetchone()
    
    if not row:
        raise HTTPException(status_code=404, detail="Regel nicht gefunden")
    
    try:
        rule = json.loads(row[1])
        
        # Fetch category name
        category_id = rule.get('category')
        cursor.execute(
            "SELECT name FROM tbl_category WHERE id = %s",
            (category_id,)
        )
        cat_row = cursor.fetchone()
        category_name = cat_row[0] if cat_row else None
        
        return {
            "id": rule.get('id'),
            "name": rule.get('name'),
            "description": rule.get('description'),
            "conditions": rule.get('conditions', []),
            "conditionLogic": rule.get('conditionLogic'),
            "category": category_id,
            "category_name": category_name,
            "accounts": rule.get('accounts', []),
            "priority": rule.get('priority', 5),
            "enabled": rule.get('enabled', True),
            "dateCreated": rule.get('dateCreated'),
            "dateModified": rule.get('dateModified')
        }
        
    except (json.JSONDecodeError, KeyError) as e:
        raise HTTPException(status_code=500, detail=f"Fehler beim Parsen der Regel: {str(e)}")


@router.post("/rules")
@handle_db_errors("create category automation rule")
async def create_rule(
    rule_data: RuleData,
    cursor = Depends(get_db_cursor),
    connection = Depends(get_db_connection)
):
    """Create a new category automation rule."""
    
    # Validate
    if not rule_data.name:
        raise HTTPException(status_code=400, detail="Regelname erforderlich")
    
    if not rule_data.conditions:
        raise HTTPException(status_code=400, detail="Mindestens eine Bedingung erforderlich")
    
    if not rule_data.category:
        raise HTTPException(status_code=400, detail="Kategorie erforderlich")
    
    # Validate condition IDs are unique
    condition_ids = [c.id for c in rule_data.conditions]
    if len(condition_ids) != len(set(condition_ids)):
        raise HTTPException(status_code=400, detail="Bedingung-IDs müssen eindeutig sein")
    
    # Generate UUID if not provided
    rule_id = rule_data.id or str(uuid4())
    
    # Build rule dict
    now = datetime.now().isoformat()
    rule = {
        "id": rule_id,
        "name": rule_data.name,
        "description": rule_data.description,
        "conditions": [c.dict() for c in rule_data.conditions],
        "conditionLogic": rule_data.conditionLogic,
        "category": rule_data.category,
        "accounts": rule_data.accounts,
        "priority": rule_data.priority,
        "enabled": rule_data.enabled,
        "dateCreated": now,
        "dateModified": now
    }
    
    # Insert into settings
    insert_query = """
        INSERT INTO tbl_setting (user_id, `key`, `value`)
        VALUES (NULL, 'category_automation_rule', %s)
    """
    
    cursor.execute(insert_query, (json.dumps(rule),))
    connection.commit()
    
    return {
        "id": rule_id,
        "message": "Regel erfolgreich erstellt",
        "rule": rule
    }


@router.put("/rules/{rule_id}")
@handle_db_errors("update category automation rule")
async def update_rule(
    rule_id: str = Path(..., description="Rule UUID"),
    rule_data: RuleData = None,
    cursor = Depends(get_db_cursor),
    connection = Depends(get_db_connection)
):
    """Update an existing rule."""
    
    # Find existing rule
    find_query = """
        SELECT id
        FROM tbl_setting
        WHERE `key` = 'category_automation_rule'
          AND JSON_EXTRACT(value, '$.id') = %s
    """
    
    cursor.execute(find_query, (rule_id,))
    row = cursor.fetchone()
    
    if not row:
        raise HTTPException(status_code=404, detail="Regel nicht gefunden")
    
    setting_id = row[0]
    
    # Build updated rule
    now = datetime.now().isoformat()
    
    # Keep existing dateCreated if present
    get_created = """
        SELECT JSON_EXTRACT(value, '$.dateCreated')
        FROM tbl_setting
        WHERE id = %s
    """
    cursor.execute(get_created, (setting_id,))
    created_row = cursor.fetchone()
    date_created = created_row[0].strip('"') if created_row and created_row[0] else now
    
    rule = {
        "id": rule_id,
        "name": rule_data.name,
        "description": rule_data.description,
        "conditions": [c.dict() for c in rule_data.conditions],
        "conditionLogic": rule_data.conditionLogic,
        "category": rule_data.category,
        "accounts": rule_data.accounts,
        "priority": rule_data.priority,
        "enabled": rule_data.enabled,
        "dateCreated": date_created,
        "dateModified": now
    }
    
    # Update
    update_query = """
        UPDATE tbl_setting
        SET `value` = %s
        WHERE id = %s
    """
    
    cursor.execute(update_query, (json.dumps(rule), setting_id))
    connection.commit()
    
    return {
        "id": rule_id,
        "message": "Regel erfolgreich aktualisiert",
        "rule": rule
    }


@router.delete("/rules/{rule_id}")
@handle_db_errors("delete category automation rule")
async def delete_rule(
    rule_id: str = Path(..., description="Rule UUID"),
    cursor = Depends(get_db_cursor),
    connection = Depends(get_db_connection)
):
    """Delete a rule."""
    
    delete_query = """
        DELETE FROM tbl_setting
        WHERE `key` = 'category_automation_rule'
          AND JSON_EXTRACT(value, '$.id') = %s
    """
    
    cursor.execute(delete_query, (rule_id,))
    connection.commit()
    
    if cursor.rowcount == 0:
        raise HTTPException(status_code=404, detail="Regel nicht gefunden")
    
    return {
        "message": "Regel erfolgreich gelöscht",
        "id": rule_id
    }


@router.post("/test-rule")
@handle_db_errors("test category automation rule")
async def test_rule(
    payload: TestRuleRequest,
    cursor = Depends(get_db_cursor)
):
    """Test a rule against sample transaction data."""
    
    # Normalize amount
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
    
    # Convert Pydantic model to dict
    rule_dict = {
        "id": payload.rule.id or str(uuid4()),
        "name": payload.rule.name,
        "description": payload.rule.description,
        "conditions": [c.dict() for c in payload.rule.conditions],
        "conditionLogic": payload.rule.conditionLogic,
        "category": payload.rule.category,
        "accounts": payload.rule.accounts,
        "priority": payload.rule.priority,
        "enabled": payload.rule.enabled
    }
    
    # Test rule
    matches = evaluate_rule(transaction, rule_dict)
    
    # Get detailed condition results for debugging
    condition_results = {}
    for condition in payload.rule.conditions:
        from services.category_automation import evaluate_condition
        cond_dict = condition.dict()
        result = evaluate_condition(transaction, cond_dict)
        condition_results[condition.id] = result
    
    # Evaluate logic
    logic_result = None
    if payload.rule.conditionLogic:
        try:
            logic_result = parse_condition_logic(
                payload.rule.conditionLogic,
                condition_results
            )
        except Exception as e:
            logic_result = f"Error: {str(e)}"
    
    return {
        "matches": matches,
        "message": "Regel passt" if matches else "Regel passt nicht",
        "conditionResults": condition_results,
        "logicEvaluation": logic_result,
        "transaction": transaction
    }
