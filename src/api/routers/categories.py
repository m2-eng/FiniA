"""
Categories API Router
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from repositories.category_repository import CategoryRepository
from api.dependencies import get_db_cursor_with_auth as get_db_cursor, get_db_connection_with_auth as get_db_connection
from api.models import CategoryResponse, CategoryCreateRequest, CategoryUpdateRequest
from api.error_handling import handle_db_errors, safe_commit, safe_rollback

router = APIRouter(prefix="/categories", tags=["categories"])


@router.get("/")
@handle_db_errors("fetch categories")
async def get_categories(
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    page_size: int = Query(100, ge=1, le=1000, description="Records per page"),
    cursor=Depends(get_db_cursor)
):
    """
    Get paginated categories with their full hierarchical names.
    
    Args:
        page: Page number (1-based, default 1)
        page_size: Number of records per page (default 100, max 1000)
    
    Returns a paginated list of categories from view_categoryFullname with their fullname.
    """
    repo = CategoryRepository(cursor)
    result = repo.get_all_fullnames_paginated(page=page, page_size=page_size)
    return {"categories": result['categories'], "page": result['page'], "page_size": result['page_size'], "total": result['total']}


@router.get("/hierarchy")
@handle_db_errors("fetch category hierarchy")
async def get_categories_hierarchy( # finding: Add 'paginated' to the function name.
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    page_size: int = Query(100, ge=1, le=1000, description="Records per page"),
    cursor=Depends(get_db_cursor)
):
    """
    Get paginated categories with parent information for building a tree structure.
    
    Args:
        page: Page number (1-based, default 1)
        page_size: Number of records per page (default 100, max 1000)
    
    Returns a paginated list of categories with their parent_id for hierarchical display.
    """
    repo = CategoryRepository(cursor)
    result = repo.get_all_with_parent_paginated(page=page, page_size=page_size)
    return {"categories": result['categories'], "page": result['page'], "page_size": result['page_size'], "total": result['total']}


@router.get("/hierarchy/all")
@handle_db_errors("fetch all categories hierarchy")
async def get_all_categories_hierarchy_unpaginated(cursor=Depends(get_db_cursor)):
    """
    Get ALL categories with parent information in a single efficient query.
    Use this for full category tree loading on category management page.
    
    Returns all categories with their parent_id for hierarchical display.
    """
    repo = CategoryRepository(cursor)
    categories = repo.get_all_with_parent_unpaginated()
    return {"categories": categories}


@router.get("/list")
@handle_db_errors("fetch categories list")
async def list_categories_simple(cursor=Depends(get_db_cursor)):
    """
    Get simple list of all categories with id and fullname for dropdowns.
    """
    query = """
        SELECT id, fullname
        FROM view_categoryFullname
        ORDER BY fullname
    """
    cursor.execute(query)
    rows = cursor.fetchall()
    
    categories = [{"id": row[0], "fullname": row[1]} for row in rows]
    return {"categories": categories}


@router.get("/{category_id}")
@handle_db_errors("fetch category")
async def get_category(category_id: int, cursor=Depends(get_db_cursor)):
    """
    Get a specific category by ID.
    """
    repo = CategoryRepository(cursor)
    category = repo.get_category_by_id(category_id)
    if not category:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")
    return category


@router.post("/")
@handle_db_errors("create category")
async def create_category(request: CategoryCreateRequest, cursor=Depends(get_db_cursor), connection=Depends(get_db_connection)):
    """
    Create a new category.
    
    Args:
        request: CategoryCreateRequest with 'name' and optional 'parent_id'
        
    Returns:
        The created category with its ID
    """
    repo = CategoryRepository(cursor)
    
    # Check if parent exists (if parent_id provided)
    if request.parent_id:
        parent = repo.get_category_by_id(request.parent_id)
        if not parent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Parent category with ID {request.parent_id} not found"
            )
    
    # Get next ID
    next_id = repo.get_max_category_id() + 1
    
    try:
        repo.insert_category(next_id, request.name, request.parent_id)
        safe_commit(connection, "create category")
        return {
            "id": next_id,
            "name": request.name,
            "parent_id": request.parent_id
        }
    except HTTPException:
        safe_rollback(connection, "create category")
        raise
    except Exception as e:
        safe_rollback(connection, "create category")
        raise


@router.put("/{category_id}")
@handle_db_errors("update category")
async def update_category(
    category_id: int,
    request: CategoryUpdateRequest,
    cursor=Depends(get_db_cursor),
    connection=Depends(get_db_connection)
):
    """
    Update a category's name and/or parent.
    
    Args:
        category_id: ID of the category to update
        request: CategoryUpdateRequest with optional 'name' and 'parent_id'
        
    Returns:
        The updated category
    """
    repo = CategoryRepository(cursor)
    
    # Check if category exists
    category = repo.get_category_by_id(category_id)
    if not category:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")
    
    # Use existing values if not provided
    new_name = request.name if request.name is not None else category['name']
    new_parent_id = request.parent_id if request.parent_id is not None else category['parent_id']
    
    # Check if parent exists (if parent_id is being set to something)
    if new_parent_id and new_parent_id != category['parent_id']:
        parent = repo.get_category_by_id(new_parent_id)
        if not parent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Parent category with ID {new_parent_id} not found"
            )
    
    try:
        repo.update_category(category_id, new_name, new_parent_id)
        safe_commit(connection, "update category")
        return {
            "id": category_id,
            "name": new_name,
            "parent_id": new_parent_id
        }
    except HTTPException:
        safe_rollback(connection, "update category")
        raise
    except Exception as e:
        safe_rollback(connection, "update category")
        raise


@router.delete("/{category_id}")
@handle_db_errors("delete category")
async def delete_category(category_id: int, cursor=Depends(get_db_cursor), connection=Depends(get_db_connection)):
    """
    Delete a category and reassign its children to its parent.
    
    Args:
        category_id: ID of the category to delete
        
    Returns:
        Confirmation message
    """
    repo = CategoryRepository(cursor)
    
    # Check if category exists
    category = repo.get_category_by_id(category_id)
    if not category:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")
    
    try:
        repo.delete_category(category_id)
        safe_commit(connection, "delete category")
        return {"message": f"Category {category_id} deleted successfully"}
    except HTTPException:
        safe_rollback(connection, "delete category")
        raise
    except Exception as e:
        safe_rollback(connection, "delete category")
        raise
