#
# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (c) 2026 m2-eng
# Author: m2-eng
# Co-Author: GitHub Copilot
# License: GNU Affero General Public License v3.0 (AGPL-3.0-only)
# Purpose: Category Automation API router - for automated transaction categorization rules
#
"""
Category Automation API router - for automated transaction categorization rules
"""

import json
import logging
from fastapi import APIRouter, Depends, Query, HTTPException, Path
from typing import Optional
from api.dependencies import get_db_cursor_with_auth, get_db_connection_with_auth
from api.error_handling import handle_db_errors, safe_commit, safe_rollback
from api.models import RuleData, TestRuleRequest
from repositories.settings_repository import SettingsRepository
from repositories.category_repository import CategoryRepository
from services.category_automation import (
    evaluate_rule,
    parse_condition_logic
)
from uuid import uuid4
from datetime import datetime


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/category-automation", tags=["category-automation"])


@router.get("/rules")
@handle_db_errors("fetch category automation rules")
async def get_rules(
    account: Optional[int] = Query(None, description="Filter by account ID"),
    enabled_only: bool = Query(True, description="Only return enabled rules"),
    cursor = Depends(get_db_cursor_with_auth)
):
    """
    Get all automation rules from settings table.
    Returns rules sorted by priority (descending).
    """
    settings_repo = SettingsRepository(cursor)
    category_repo = CategoryRepository(cursor)
    entries = settings_repo.get_setting_entries("category_automation_rule")

    rules = []
    for entry in entries:
        try:
            rule = json.loads(entry["value"])
            
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
            category = category_repo.get_category_by_id(category_id) if category_id else None
            category_name = category['name'] if category else None
            
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
            logger.warning("Failed to parse rule %s: %s", entry.get('id'), e)
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
    cursor = Depends(get_db_cursor_with_auth)
):
    """Get a specific rule by ID."""
    settings_repo = SettingsRepository(cursor)
    category_repo = CategoryRepository(cursor)
    entries = settings_repo.get_setting_entries("category_automation_rule")

    matching = None
    for entry in entries:
        try:
            rule = json.loads(entry["value"])
        except (json.JSONDecodeError, KeyError):
            continue
        if rule.get("id") == rule_id:
            matching = rule
            break

    if not matching:
        raise HTTPException(status_code=404, detail="Rule not found.")

    try:
        category_id = matching.get('category')
        category = category_repo.get_category_by_id(category_id) if category_id else None
        category_name = category['name'] if category else None

        return {
            "id": matching.get('id'),
            "name": matching.get('name'),
            "description": matching.get('description'),
            "conditions": matching.get('conditions', []),
            "conditionLogic": matching.get('conditionLogic'),
            "category": category_id,
            "category_name": category_name,
            "accounts": matching.get('accounts', []),
            "priority": matching.get('priority', 5),
            "enabled": matching.get('enabled', True),
            "dateCreated": matching.get('dateCreated'),
            "dateModified": matching.get('dateModified')
        }

    except (json.JSONDecodeError, KeyError) as e:
        raise HTTPException(status_code=500, detail=f"Failed to parse rule: {str(e)}")


@router.post("/rules")
@handle_db_errors("create category automation rule")
async def create_rule(
    rule_data: RuleData,
    connection = Depends(get_db_connection_with_auth)
):
    """Create a new category automation rule."""
    cursor = connection.cursor(buffered=True)
    try:
        # Validate
        if not rule_data.name:
            raise HTTPException(status_code=400, detail="Rule name is required.")
        
        if not rule_data.conditions:
            raise HTTPException(status_code=400, detail="At least one condition is required.")
        
        if not rule_data.category:
            raise HTTPException(status_code=400, detail="Category is required.")
        
        # Validate condition IDs are unique
        condition_ids = [c.id for c in rule_data.conditions]
        if len(condition_ids) != len(set(condition_ids)):
            raise HTTPException(status_code=400, detail="Condition IDs must be unique.")
        
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
        
        settings_repo = SettingsRepository(cursor)
        settings_repo.add_setting("category_automation_rule", json.dumps(rule))
        safe_commit(connection)
            
        return {
            "id": rule_id,
            "message": "Rule created successfully.",
            "rule": rule
            }
    except Exception:
        safe_rollback(connection, "create category automation rule")
        raise
    finally:
        try:
            cursor.close()
        except Exception:
            pass


@router.put("/rules/{rule_id}")
@handle_db_errors("update category automation rule")
async def update_rule(
    rule_id: str = Path(..., description="Rule UUID"),
    rule_data: RuleData = None,
    connection = Depends(get_db_connection_with_auth)
):
    """Update an existing rule."""
    cursor = connection.cursor(buffered=True)
    try:

        if rule_data is None:
            raise HTTPException(status_code=400, detail="Rule data is required.")
        
        settings_repo = SettingsRepository(cursor)
        entries = settings_repo.get_setting_entries("category_automation_rule")
        existing_entry = None
        existing_rule = None
        for entry in entries:
            try:
                parsed = json.loads(entry["value"])
            except (json.JSONDecodeError, KeyError):
                continue
            if parsed.get("id") == rule_id:
                existing_entry = entry
                existing_rule = parsed
                break

        if not existing_entry:
            # Frontend sends PUT for new rules with id prefix "new-..."
            if rule_id.startswith("new-"):
                # Validate minimal fields (same as create)
                if not rule_data.name:
                    raise HTTPException(status_code=400, detail="Rule name is required.")
                if not rule_data.conditions:
                    raise HTTPException(status_code=400, detail="At least one condition is required.")
                if not rule_data.category:
                    raise HTTPException(status_code=400, detail="Category is required.")

                condition_ids = [c.id for c in rule_data.conditions]
                if len(condition_ids) != len(set(condition_ids)):
                    raise HTTPException(status_code=400, detail="Condition IDs must be unique.")

                # Generate UUID if not provided or invalid new-id
                new_rule_id = rule_data.id or str(uuid4())
                now = datetime.now().isoformat()
                rule = {
                    "id": new_rule_id,
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

                settings_repo.add_setting("category_automation_rule", json.dumps(rule))
                safe_commit(connection)

                return {
                    "id": new_rule_id,
                    "message": "Rule created successfully.",
                    "rule": rule
                }

            raise HTTPException(status_code=404, detail="Rule not found.")
        
        setting_id = existing_entry["id"]

        # Build updated rule
        now = datetime.now().isoformat()
        date_created = (existing_rule or {}).get("dateCreated", now)
        
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
        
        jsonValue = json.dumps(rule)
        settings_repo.update_setting_value(setting_id, jsonValue)
        safe_commit(connection)
            
        return {
            "id": rule_id,
            "message": "Rule updated successfully.",
            "rule": rule
        }
    except Exception:
        safe_rollback(connection, "update category automation rule")
        raise
    finally:
        try:
            cursor.close()
        except Exception:
            pass


@router.delete("/rules/{rule_id}")
@handle_db_errors("delete category automation rule")
async def delete_rule(
    rule_id: str = Path(..., description="Rule UUID"),
    connection = Depends(get_db_connection_with_auth)
):
    """Delete a rule."""
    cursor = connection.cursor(buffered=True)
    try:
        settings_repo = SettingsRepository(cursor)
        entries = settings_repo.get_setting_entries("category_automation_rule")
        target_id = None
        for entry in entries:
            try:
                rule = json.loads(entry["value"])
            except (json.JSONDecodeError, KeyError):
                continue
            if rule.get("id") == rule_id:
                target_id = entry["id"]
                break

        if target_id is None:
            raise HTTPException(status_code=404, detail="Rule not found.")

        settings_repo.delete_setting_by_id(target_id)
        safe_commit(connection)
        
        return {
            "message": "Rule deleted successfully.",
            "id": rule_id
        }
    except Exception:
        safe_rollback(connection, "delete category automation rule")
        raise
    finally:
        try:
            cursor.close()
        except Exception:
            pass


@router.post("/test-rule")
@handle_db_errors("test category automation rule")
async def test_rule(
    payload: TestRuleRequest,
    cursor = Depends(get_db_cursor_with_auth)
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
        "message": "Rule matches" if matches else "Rule does not match",
        "conditionResults": condition_results,
        "logicEvaluation": logic_result,
        "transaction": transaction
    }

