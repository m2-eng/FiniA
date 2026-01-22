"""
Settings API Router
Handles global/user settings storage.
"""

import json
from fastapi import APIRouter, Depends, HTTPException, status
from api.dependencies import get_db_cursor_with_auth as get_db_cursor, get_db_connection_with_auth as get_db_connection
from api.error_handling import handle_db_errors, safe_commit, safe_rollback
from repositories.settings_repository import SettingsRepository

router = APIRouter(prefix="/settings", tags=["settings"])

SETTINGS_KEY_SHARES_TX = "share_tx_category"


@router.get("/shares-tx-categories")
@handle_db_errors("fetch shares transaction category settings")
async def get_shares_tx_categories(cursor=Depends(get_db_cursor)):
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
    cursor=Depends(get_db_cursor),
    connection=Depends(get_db_connection)
):
    """Add a category assignment for share transactions"""
    category_id = body.get("category_id")
    category_type = body.get("type")
    
    if not category_id or not category_type:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="category_id and type required")
    
    if category_type not in ["buy", "sell", "dividend"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="type must be buy, sell, or dividend")
    
    repo = SettingsRepository(cursor)
    try:
        value = json.dumps({"category_id": int(category_id), "type": category_type})
        repo.add_setting(SETTINGS_KEY_SHARES_TX, value)
        safe_commit(connection)
        return {"status": "success", "category_id": category_id, "type": category_type}
    except Exception as e:
        safe_rollback(connection)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.delete("/shares-tx-categories")
@handle_db_errors("delete shares transaction category setting")
async def delete_shares_tx_category(
    body: dict,
    cursor=Depends(get_db_cursor),
    connection=Depends(get_db_connection)
):
    """Delete a category assignment for share transactions"""
    category_id = body.get("category_id")
    category_type = body.get("type")
    
    if not category_id or not category_type:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="category_id and type required")
    
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
