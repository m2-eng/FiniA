"""
Planning API router
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from repositories.planning_repository import PlanningRepository
from api.dependencies import get_db_cursor_with_auth, get_db_connection_with_auth
from api.models import (
    PlanningResponse,
    PlanningListResponse,
    PlanningCreateRequest,
    PlanningUpdateRequest,
    PlanningCycleResponse,
    PlanningEntriesResponse
)
from api.error_handling import handle_db_errors, safe_commit


router = APIRouter(prefix="/planning", tags=["planning"])


@router.get("/cycles", response_model=list[PlanningCycleResponse])
@handle_db_errors("fetch planning cycles")
async def get_planning_cycles(cursor = Depends(get_db_cursor_with_auth)):
    """
    Get all available planning cycles.
    
    Returns list of cycles (e.g., 'Monthly', 'Yearly', etc.)
    """
    repo = PlanningRepository(cursor)
    cycles = repo.get_all_cycles()
    return cycles


@router.get("/", response_model=PlanningListResponse)
@handle_db_errors("fetch plannings")
async def get_plannings(
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    page_size: int = Query(100, ge=1, le=1000, description="Records per page"),
    cursor = Depends(get_db_cursor_with_auth)
):
    """
    Get paginated planning entries.
    
    Args:
        page: Page number (1-based, default 1)
        page_size: Number of records per page (default 100, max 1000)
    
    Returns:
        List of planning entries with pagination metadata
    """
    repo = PlanningRepository(cursor)
    result = repo.get_plannings_paginated(page=page, page_size=page_size)
    return result


@router.get("/{planning_id}/entries", response_model=PlanningEntriesResponse)
@handle_db_errors("fetch planning entries")
async def get_planning_entries(
    planning_id: int,
    connection = Depends(get_db_connection_with_auth)
):
    """
    Get all planning entries for a planning.
    """
    cursor = connection.cursor(buffered=True)
    try:
        repo = PlanningRepository(cursor)

        planning = repo.get_planning_by_id(planning_id)
        if not planning:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Planning with ID {planning_id} not found"
            )

        entries = repo.get_planning_entries(planning_id)
        return {
            "planning_id": planning_id,
            "entries": entries,
            "total": len(entries)
        }
    finally:
        try:
            cursor.close()
        except Exception:
            pass


@router.post("/{planning_id}/entries/generate", response_model=PlanningEntriesResponse)
@handle_db_errors("generate planning entries")
async def generate_planning_entries(
    planning_id: int,
    connection = Depends(get_db_connection_with_auth)
):
    """
    Generate planning entries up to the planning end date or the end of next year.
    """
    cursor = connection.cursor(buffered=True)
    try:
        repo = PlanningRepository(cursor)

        entries = repo.regenerate_planning_entries(planning_id)
        if entries is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Planning with ID {planning_id} not found"
            )

        safe_commit(connection)
    finally:
        try:
            cursor.close()
        except Exception:
            pass

    return {
        "planning_id": planning_id,
        "entries": entries,
        "total": len(entries)
    }


@router.delete("/{planning_id}/entries/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
@handle_db_errors("delete planning entry")
async def delete_planning_entry(
    planning_id: int,
    entry_id: int,
    connection = Depends(get_db_connection_with_auth)
):
    """Delete a single planning entry for a planning."""
    cursor = connection.cursor(buffered=True)
    try:
        repo = PlanningRepository(cursor)

        # Ensure the planning exists
        planning = repo.get_planning_by_id(planning_id)
        if not planning:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Planning with ID {planning_id} not found"
            )

        deleted = repo.delete_planning_entry(planning_id, entry_id)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Planning entry with ID {entry_id} not found for planning {planning_id}"
            )

        safe_commit(connection)
    finally:
        try:
            cursor.close()
        except Exception:
            pass


@router.get("/{planning_id}", response_model=PlanningResponse)
@handle_db_errors("fetch planning")
async def get_planning(
    planning_id: int,
    cursor = Depends(get_db_cursor_with_auth)
):
    """
    Get a single planning entry by ID.
    
    Args:
        planning_id: Planning ID
        
    Returns:
        Planning entry details
    """
    repo = PlanningRepository(cursor)
    planning = repo.get_planning_by_id(planning_id)
    
    if not planning:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Planning with ID {planning_id} not found"
        )
    
    return planning


@router.post("/", response_model=PlanningResponse, status_code=status.HTTP_201_CREATED)
@handle_db_errors("create planning")
async def create_planning(
    planning: PlanningCreateRequest,
    connection = Depends(get_db_connection_with_auth)
):
    """
    Create a new planning entry.
    
    Args:
        planning: Planning creation request
        
    Returns:
        Created planning entry
    """
    cursor = connection.cursor(buffered=True)
    try:
        repo = PlanningRepository(cursor)
        
        planning_id = repo.create_planning(
            description=planning.description,
            amount=planning.amount,
            date_start=planning.dateStart,
            date_end=planning.dateEnd,
            account_id=planning.account_id,
            category_id=planning.category_id,
            cycle_id=planning.cycle_id
        )
        
        safe_commit(connection)
        
        # Fetch the created planning
        created_planning = repo.get_planning_by_id(planning_id)
        
        if not created_planning:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve created planning"
            )
        
        return created_planning
    finally:
        try:
            cursor.close()
        except Exception:
            pass


@router.put("/{planning_id}", response_model=PlanningResponse)
@handle_db_errors("update planning")
async def update_planning(
    planning_id: int,
    planning: PlanningUpdateRequest,
    connection = Depends(get_db_connection_with_auth)
):
    """
    Update an existing planning entry.
    
    Args:
        planning_id: Planning ID to update
        planning: Planning update request
        
    Returns:
        Updated planning entry
    """
    cursor = connection.cursor(buffered=True)
    try:
        repo = PlanningRepository(cursor)
        
        # Check if planning exists
        existing = repo.get_planning_by_id(planning_id)
        if not existing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Planning with ID {planning_id} not found"
            )
        
        # Update the planning
        success = repo.update_planning(
            planning_id=planning_id,
            description=planning.description,
            amount=planning.amount,
            date_start=planning.dateStart,
            date_end=planning.dateEnd,
            account_id=planning.account_id,
            category_id=planning.category_id,
            cycle_id=planning.cycle_id
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update planning"
            )
        
        safe_commit(connection)
        
        # Fetch the updated planning
        updated_planning = repo.get_planning_by_id(planning_id)
        return updated_planning
    finally:
        try:
            cursor.close()
        except Exception:
            pass


@router.delete("/{planning_id}", status_code=status.HTTP_204_NO_CONTENT)
@handle_db_errors("delete planning")
async def delete_planning(
    planning_id: int,
    connection = Depends(get_db_connection_with_auth)
):
    """
    Delete a planning entry.
    
    Args:
        planning_id: Planning ID to delete
    """
    cursor = connection.cursor(buffered=True)
    try:
        repo = PlanningRepository(cursor)
        
        # Check if planning exists
        existing = repo.get_planning_by_id(planning_id)
        if not existing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Planning with ID {planning_id} not found"
            )
        
        # Delete the planning
        success = repo.delete_planning(planning_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete planning"
            )
        
        safe_commit(connection)
    finally:
        try:
            cursor.close()
        except Exception:
            pass

