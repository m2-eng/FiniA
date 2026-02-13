#
# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (c) 2026 m2-eng
# Author: m2-eng
# Co-Author: GitHub Copilot
# License: GNU Affero General Public License v3.0 (AGPL-3.0-only)
# Purpose: Settings API Router
#
"""
Settings API Router
Handles global/user settings storage.
"""

import json
import yaml
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from api.dependencies import get_db_cursor_with_auth, get_db_connection_with_auth
from api.error_handling import handle_db_errors, safe_commit, safe_rollback
from repositories.settings_repository import SettingsRepository
from repositories.account_type_repository import AccountTypeRepository
from repositories.planning_cycle_repository import PlanningCycleRepository

router = APIRouter(prefix="/settings", tags=["settings"])

SETTINGS_KEY_SHARES_TX = "share_tx_category"
SETTINGS_KEY_IMPORT_FORMAT = "import_format"


@router.get("/shares-tx-categories")
@handle_db_errors("fetch shares transaction category settings")
async def get_shares_tx_categories(cursor=Depends(get_db_cursor_with_auth)):
    """Get all category assignments for share transactions"""
    repo = SettingsRepository(cursor)
    entries = repo.get_settings(SETTINGS_KEY_SHARES_TX)
    
    categories = []
    for entry_json in entries:
        try:
            data = json.loads(entry_json)
            categories.append({
                "category_id": int(data.get("category_id")),
                "type": data.get("type")
            })
        except Exception:
            continue
    
    return {"categories": categories}


@router.post("/shares-tx-categories")
@handle_db_errors("add shares transaction category setting")
async def add_shares_tx_category(
    body: dict,
    connection=Depends(get_db_connection_with_auth)
):
    """Add a category assignment for share transactions"""
    category_id = body.get("category_id")
    category_type = body.get("type")
    
    if not category_id or not category_type:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="category_id and type required")
    
    if category_type not in ["buy", "sell", "dividend"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="type must be buy, sell, or dividend")

    cursor = connection.cursor(buffered=True)
    try:
        repo = SettingsRepository(cursor)
        try:
            value = json.dumps({"category_id": int(category_id), "type": category_type})
            repo.add_setting(SETTINGS_KEY_SHARES_TX, value)
            safe_commit(connection)
            return {"status": "success", "category_id": category_id, "type": category_type}
        except Exception as e:
            safe_rollback(connection)
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
    finally:
        try:
            cursor.close()
        except Exception:
            pass


@router.get("/import-formats")
@handle_db_errors("fetch import formats")
async def get_import_formats(
    connection=Depends(get_db_connection_with_auth)
):
    """Get all import formats from database settings table."""
    cursor = connection.cursor(buffered=True)
    try:
        repo = SettingsRepository(cursor)
        entries = repo.get_setting_entries(SETTINGS_KEY_IMPORT_FORMAT)

        formats = []
        for entry in entries:
            try:
                data = json.loads(entry.get("value") or "{}")
                name = data.get("name")
                config = data.get("config")
                if name and isinstance(config, dict):
                    formats.append({
                        "id": entry.get("id"),
                        "name": name,
                        "config": config
                    })
            except Exception:
                continue

        return {"formats": formats}
    finally:
        try:
            cursor.close()
        except Exception:
            pass


@router.post("/import-formats")
@handle_db_errors("add import format")
async def add_import_format(
    body: dict,
    connection=Depends(get_db_connection_with_auth)
):
    """Add a new import format entry."""
    name = body.get("name")
    config = body.get("config")

    if not name or not isinstance(config, dict):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="name and config (object) are required"
        )

    cursor = connection.cursor(buffered=True)
    try:
        repo = SettingsRepository(cursor)
        entries = repo.get_setting_entries(SETTINGS_KEY_IMPORT_FORMAT)
        for entry in entries:
            try:
                data = json.loads(entry.get("value") or "{}")
                if data.get("name") == name:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=f"Format '{name}' already exists"
                    )
            except HTTPException:
                raise
            except Exception:
                continue

        value = json.dumps({"name": name, "config": config})
        try:
            setting_id = repo.add_setting(SETTINGS_KEY_IMPORT_FORMAT, value)
            safe_commit(connection)
            return {"id": setting_id, "name": name, "config": config}
        except Exception as e:
            safe_rollback(connection)
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
    finally:
        try:
            cursor.close()
        except Exception:
            pass


@router.put("/import-formats/{setting_id}")
@handle_db_errors("update import format")
async def update_import_format(
    setting_id: int,
    body: dict,
    connection=Depends(get_db_connection_with_auth)
):
    """Update an existing import format entry by ID."""
    name = body.get("name")
    config = body.get("config")

    if not name or not isinstance(config, dict):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="name and config (object) are required"
        )

    cursor = connection.cursor(buffered=True)
    try:
        repo = SettingsRepository(cursor)
        entries = repo.get_setting_entries(SETTINGS_KEY_IMPORT_FORMAT)
        for entry in entries:
            if entry.get("id") == setting_id:
                continue
            try:
                data = json.loads(entry.get("value") or "{}")
                if data.get("name") == name:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=f"Format '{name}' already exists"
                    )
            except HTTPException:
                raise
            except Exception:
                continue

        value = json.dumps({"name": name, "config": config})
        try:
            updated = repo.update_setting_value(setting_id, value)
            if updated == 0:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Format not found"
                )
            safe_commit(connection)
            return {"id": setting_id, "name": name, "config": config}
        except HTTPException:
            safe_rollback(connection)
            raise
        except Exception as e:
            safe_rollback(connection)
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
    finally:
        try:
            cursor.close()
        except Exception:
            pass


@router.delete("/import-formats/{setting_id}")
@handle_db_errors("delete import format")
async def delete_import_format(
    setting_id: int,
    connection=Depends(get_db_connection_with_auth)
):
    """Delete an import format entry by ID."""
    cursor = connection.cursor(buffered=True)
    try:
        repo = SettingsRepository(cursor)
        try:
            deleted = repo.delete_setting_by_id(setting_id)
            safe_commit(connection)
            if deleted == 0:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Format not found")
            return {"status": "success"}
        except HTTPException:
            safe_rollback(connection)
            raise
        except Exception as e:
            safe_rollback(connection)
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
    finally:
        try:
            cursor.close()
        except Exception:
            pass


@router.post("/import-formats/upload-yaml")
@handle_db_errors("upload import formats YAML")
async def upload_import_formats_yaml(
    file: UploadFile = File(...),
    connection = Depends(get_db_connection_with_auth)
):
    """Upload and parse import formats from YAML file using Python's yaml parser.
    
    This ensures correct parsing of nested structures including list-of-objects patterns.
    """
    cursor = connection.cursor(buffered=True)
    try:
        try:
            # Read file content
            content = await file.read()
            yaml_text = content.decode('utf-8')
            
            # Parse YAML using Python's yaml library
            parsed = yaml.safe_load(yaml_text)
            
            if not parsed or not isinstance(parsed, dict):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="YAML file must contain a dictionary"
                )
            
            # Extract formats from root key 'formats'
            formats_dict = parsed.get("formats", {})
            if not isinstance(formats_dict, dict):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="YAML root must have 'formats' key containing format definitions"
                )
            
            # Import each format into database
            repo = SettingsRepository(cursor)
            imported_count = 0
            errors = []
            
            for format_name, format_config in formats_dict.items():
                try:
                    if not isinstance(format_config, dict):
                        errors.append(f"Format '{format_name}': config is not an object")
                        continue
                    
                    # Store in database
                    value = json.dumps({"name": format_name, "config": format_config})
                    
                    # Check if exists
                    existing_entries = repo.get_setting_entries("import_format")
                    existing_id = None
                    for entry in existing_entries:
                        data = json.loads(entry.get("value") or "{}")
                        if data.get("name") == format_name:
                            existing_id = entry.get("id")
                            break
                    
                    if existing_id:
                        # Update existing
                        repo.update_setting_value(existing_id, value)
                    else:
                        # Add new
                        repo.add_setting("import_format", value)
                    
                    imported_count += 1
                except Exception as e:
                    errors.append(f"Format '{format_name}': {str(e)}")
            
            safe_commit(connection)
            
            return {
                "status": "success",
                "imported_count": imported_count,
                "total_formats": len(formats_dict),
                "errors": errors if errors else None
            }
        except yaml.YAMLError as e:
            safe_rollback(connection)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"YAML parsing error: {str(e)}"
            )
        except HTTPException:
            raise
        except Exception as e:
            safe_rollback(connection)
            import traceback
            print(f"Traceback: {traceback.format_exc()}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Upload failed: {str(e)}"
            )
    finally:
        try:
            cursor.close()
        except Exception:
            pass


@router.delete("/shares-tx-categories")
@handle_db_errors("delete shares transaction category setting")
async def delete_shares_tx_category(
    body: dict,
    connection=Depends(get_db_connection_with_auth)
):
    """Delete a category assignment for share transactions"""
    category_id = body.get("category_id")
    category_type = body.get("type")
    
    if not category_id or not category_type:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="category_id and type required")

    cursor = connection.cursor(buffered=True)
    try:
        repo = SettingsRepository(cursor)
        try:
            value = json.dumps({"category_id": int(category_id), "type": category_type})
            deleted = repo.delete_setting(SETTINGS_KEY_SHARES_TX, value)
            safe_commit(connection)
            
            if deleted == 0:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Setting not found")
            
            return {"status": "success"}
        except HTTPException:
            safe_rollback(connection)
            raise
        except Exception as e:
            safe_rollback(connection)
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
    finally:
        try:
            cursor.close()
        except Exception:
            pass


# ========================================
# Account Types Endpoints
# ========================================

@router.get("/account-types")
@handle_db_errors("fetch account types")
async def get_account_types(cursor=Depends(get_db_cursor_with_auth)):
    """Get all account types from tbl_accountType."""
    repo = AccountTypeRepository(cursor)
    account_types = repo.get_all()
    return {"account_types": account_types}


@router.post("/account-types")
@handle_db_errors("add account type")
async def add_account_type(
    body: dict,
    connection=Depends(get_db_connection_with_auth)
):
    """Add a new account type."""
    type_name = body.get("type")
    
    if not type_name or not isinstance(type_name, str) or not type_name.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="'type' field is required and must be a non-empty string"
        )
    
    type_name = type_name.strip()

    cursor = connection.cursor(buffered=True)
    try:
        repo = AccountTypeRepository(cursor)
        
        # Check for duplicates
        existing = repo.get_by_type(type_name)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Account type '{type_name}' already exists"
            )
        
        try:
            new_id = repo.insert(type_name)
            safe_commit(connection)
            return {
                "status": "success",
                "id": new_id,
                "type": type_name
            }
        except Exception as e:
            safe_rollback(connection)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(e)
            )
    finally:
        try:
            cursor.close()
        except Exception:
            pass


@router.put("/account-types/{account_type_id}")
@handle_db_errors("update account type")
async def update_account_type(
    account_type_id: int,
    body: dict,
    connection=Depends(get_db_connection_with_auth)
):
    """Update an existing account type."""
    type_name = body.get("type")
    
    if not type_name or not isinstance(type_name, str) or not type_name.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="'type' field is required and must be a non-empty string"
        )
    
    type_name = type_name.strip()

    cursor = connection.cursor(buffered=True)
    try:
        repo = AccountTypeRepository(cursor)
        
        # Check if account type exists
        existing = repo.get_by_id(account_type_id)
        if not existing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Account type with ID {account_type_id} not found"
            )
        
        # Check for name conflicts (excluding current record)
        duplicate = repo.get_by_type(type_name)
        if duplicate and duplicate["id"] != account_type_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Account type '{type_name}' already exists"
            )
        
        try:
            rows_affected = repo.update(account_type_id, type_name)
            safe_commit(connection)
            
            if rows_affected == 0:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Account type with ID {account_type_id} not found"
                )
            
            return {
                "status": "success",
                "id": account_type_id,
                "type": type_name
            }
        except HTTPException:
            safe_rollback(connection)
            raise
        except Exception as e:
            safe_rollback(connection)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(e)
            )
    finally:
        try:
            cursor.close()
        except Exception:
            pass


@router.delete("/account-types/{account_type_id}")
@handle_db_errors("delete account type")
async def delete_account_type(
    account_type_id: int,
    connection=Depends(get_db_connection_with_auth)
):
    """Delete an account type by ID."""
    cursor = connection.cursor(buffered=True)
    try:
        repo = AccountTypeRepository(cursor)
        
        # Check if account type exists
        existing = repo.get_by_id(account_type_id)
        if not existing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Account type with ID {account_type_id} not found"
            )
        
        try:
            rows_affected = repo.delete(account_type_id)
            safe_commit(connection)
            
            if rows_affected == 0:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Account type with ID {account_type_id} not found"
                )
            
            return {"status": "success"}
        except HTTPException:
            safe_rollback(connection)
            raise
        except Exception as e:
            safe_rollback(connection)
            # Foreign key constraint violation
            if "foreign key constraint" in str(e).lower() or "cannot delete" in str(e).lower():
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Cannot delete account type: still in use by existing accounts"
                )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(e)
            )
    finally:
        try:
            cursor.close()
        except Exception:
            pass


# ========================================
# Planning Cycles Endpoints
# ========================================

@router.get("/planning-cycles")
@handle_db_errors("fetch planning cycles")
async def get_planning_cycles(cursor=Depends(get_db_cursor_with_auth)):
    """Get all planning cycles from tbl_planningCycle."""
    repo = PlanningCycleRepository(cursor)
    cycles = repo.get_all()
    return {"planning_cycles": cycles}


@router.post("/planning-cycles")
@handle_db_errors("add planning cycle")
async def add_planning_cycle(
    body: dict,
    connection=Depends(get_db_connection_with_auth)
):
    """Add a new planning cycle."""
    cycle_name = body.get("cycle")
    period_value = body.get("periodValue")
    period_unit = body.get("periodUnit")

    if not cycle_name or not isinstance(cycle_name, str) or not cycle_name.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="'cycle' field is required and must be a non-empty string"
        )

    if period_value is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="'periodValue' field is required"
        )

    if period_unit not in ["d", "m", "y"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="'periodUnit' must be one of: d, m, y"
        )

    try:
        period_value = float(period_value)
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="'periodValue' must be a number"
        )

    cycle_name = cycle_name.strip()

    cursor = connection.cursor(buffered=True)
    try:
        repo = PlanningCycleRepository(cursor)
        existing = repo.get_by_cycle(cycle_name)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Planning cycle '{cycle_name}' already exists"
            )

        try:
            new_id = repo.insert(cycle_name, period_value, period_unit)
            safe_commit(connection)
            return {
                "status": "success",
                "id": new_id,
                "cycle": cycle_name,
                "periodValue": period_value,
                "periodUnit": period_unit
            }
        except Exception as e:
            safe_rollback(connection)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(e)
            )
    finally:
        try:
            cursor.close()
        except Exception:
            pass


@router.put("/planning-cycles/{cycle_id}")
@handle_db_errors("update planning cycle")
async def update_planning_cycle(
    cycle_id: int,
    body: dict,
    connection=Depends(get_db_connection_with_auth)
):
    """Update an existing planning cycle."""
    cycle_name = body.get("cycle")
    period_value = body.get("periodValue")
    period_unit = body.get("periodUnit")

    if not cycle_name or not isinstance(cycle_name, str) or not cycle_name.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="'cycle' field is required and must be a non-empty string"
        )

    if period_value is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="'periodValue' field is required"
        )

    if period_unit not in ["d", "m", "y"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="'periodUnit' must be one of: d, m, y"
        )

    try:
        period_value = float(period_value)
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="'periodValue' must be a number"
        )

    cycle_name = cycle_name.strip()

    cursor = connection.cursor(buffered=True)
    try:
        repo = PlanningCycleRepository(cursor)
        existing = repo.get_by_id(cycle_id)
        if not existing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Planning cycle with ID {cycle_id} not found"
            )

        duplicate = repo.get_by_cycle(cycle_name)
        if duplicate and duplicate["id"] != cycle_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Planning cycle '{cycle_name}' already exists"
            )

        try:
            rows_affected = repo.update(cycle_id, cycle_name, period_value, period_unit)
            safe_commit(connection)
            if rows_affected == 0:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Planning cycle with ID {cycle_id} not found"
                )
            return {
                "status": "success",
                "id": cycle_id,
                "cycle": cycle_name,
                "periodValue": period_value,
                "periodUnit": period_unit
            }
        except HTTPException:
            safe_rollback(connection)
            raise
        except Exception as e:
            safe_rollback(connection)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(e)
            )
    finally:
        try:
            cursor.close()
        except Exception:
            pass


@router.delete("/planning-cycles/{cycle_id}")
@handle_db_errors("delete planning cycle")
async def delete_planning_cycle(
    cycle_id: int,
    connection=Depends(get_db_connection_with_auth)
):
    """Delete a planning cycle by ID."""
    cursor = connection.cursor(buffered=True)
    try:
        repo = PlanningCycleRepository(cursor)
        existing = repo.get_by_id(cycle_id)
        if not existing:
            raise HTTPException( # finding: Move exceptions and/or messages to a central place for consistency and easier maintenance.
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Planning cycle with ID {cycle_id} not found"
            )

        try:
            rows_affected = repo.delete(cycle_id)
            safe_commit(connection)
            if rows_affected == 0:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Planning cycle with ID {cycle_id} not found"
                )
            return {"status": "success"}
        except HTTPException:
            safe_rollback(connection)
            raise
        except Exception as e:
            safe_rollback(connection)
            if "foreign key constraint" in str(e).lower() or "cannot delete" in str(e).lower():
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Cannot delete planning cycle: still in use by existing planning entries"
                )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(e)
            )
    finally:
        try:
            cursor.close()
        except Exception:
            pass


