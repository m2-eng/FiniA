"""
Planning API router
"""

from fastapi import APIRouter, Depends, HTTPException, status
from repositories.planning_repository import PlanningRepository
from api.dependencies import get_db_cursor, get_db_connection
from api.models import (
    PlanningResponse,
    PlanningListResponse,
    PlanningCreateRequest,
    PlanningUpdateRequest,
    PlanningCycleResponse,
    PlanningEntryResponse,
    PlanningEntriesResponse
)
from api.error_handling import handle_db_errors, safe_commit


router = APIRouter(prefix="/planning", tags=["planning"])


@router.get("/cycles", response_model=list[PlanningCycleResponse])
@handle_db_errors("fetch planning cycles")
async def get_planning_cycles(cursor = Depends(get_db_cursor)):
    """
    Get all available planning cycles.
    
    Returns list of cycles (e.g., 'Monthly', 'Yearly', etc.)
    """
    repo = PlanningRepository(cursor)
    cycles = repo.get_all_cycles()
    return cycles


@router.get("/", response_model=PlanningListResponse)
@handle_db_errors("fetch plannings")
async def get_plannings(cursor = Depends(get_db_cursor)):
    """
    Get all planning entries.
    
    Returns:
        List of all planning entries with their details
    """
    repo = PlanningRepository(cursor)
    plannings = repo.get_all_plannings()
    
    return {
        "plannings": plannings,
        "total": len(plannings)
    }


@router.get("/{planning_id}", response_model=PlanningResponse)
@handle_db_errors("fetch planning")
async def get_planning(
    planning_id: int,
    cursor = Depends(get_db_cursor)
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
    cursor = Depends(get_db_cursor),
    connection = Depends(get_db_connection)
):
    """
    Create a new planning entry.
    
    Args:
        planning: Planning creation request
        
    Returns:
        Created planning entry
    """
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


@router.put("/{planning_id}", response_model=PlanningResponse)
@handle_db_errors("update planning")
async def update_planning(
    planning_id: int,
    planning: PlanningUpdateRequest,
    cursor = Depends(get_db_cursor),
    connection = Depends(get_db_connection)
):
    """
    Update an existing planning entry.
    
    Args:
        planning_id: Planning ID to update
        planning: Planning update request
        
    Returns:
        Updated planning entry
    """
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


@router.get("/{planning_id}/entries", response_model=PlanningEntriesResponse)
@handle_db_errors("fetch planning entries")
async def get_planning_entries(
    planning_id: int,
    cursor = Depends(get_db_cursor)
):
    """
    Get all planning entries for a planning.
    """
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


@router.post("/{planning_id}/entries/generate", response_model=PlanningEntriesResponse)
@handle_db_errors("generate planning entries")
async def generate_planning_entries(
    planning_id: int,
    cursor = Depends(get_db_cursor),
    connection = Depends(get_db_connection)
):
    """
    Generate planning entries up to the planning end date or the end of next year.
    """
    repo = PlanningRepository(cursor)

    entries = repo.regenerate_planning_entries(planning_id)
    if entries is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Planning with ID {planning_id} not found"
        )

    safe_commit(connection)

    return {
        "planning_id": planning_id,
        "entries": entries,
        "total": len(entries)
    }


@router.delete("/{planning_id}", status_code=status.HTTP_204_NO_CONTENT)
@handle_db_errors("delete planning")
async def delete_planning(
    planning_id: int,
    cursor = Depends(get_db_cursor),
    connection = Depends(get_db_connection)
):
    """
    Delete a planning entry.
    
    Args:
        planning_id: Planning ID to delete
    """
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
