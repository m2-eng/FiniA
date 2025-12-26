"""
Categories API Router
"""

from fastapi import APIRouter, Depends, HTTPException, status
from repositories.category_repository import CategoryRepository
from api.dependencies import get_db_cursor, get_db_connection
from api.models import CategoryResponse, CategoryCreateRequest, CategoryUpdateRequest

router = APIRouter(prefix="/categories", tags=["categories"])


@router.get("/")
async def get_categories(cursor=Depends(get_db_cursor)):
    """
    Get all categories with their full hierarchical names.
    
    Returns a list of categories from view_categoryFullname with their fullname.
    """
    repo = CategoryRepository(cursor)
    categories = repo.get_all_fullnames()
    return {"categories": categories}


@router.get("/hierarchy")
async def get_categories_hierarchy(cursor=Depends(get_db_cursor)):
    """
    Get all categories with parent information for building a tree structure.
    
    Returns a list of categories with their parent_id for hierarchical display.
    """
    repo = CategoryRepository(cursor)
    categories = repo.get_all_with_parent()
    return {"categories": categories}


@router.get("/{category_id}")
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
        connection.commit()
        return {
            "id": next_id,
            "name": request.name,
            "parent_id": request.parent_id
        }
    except Exception as e:
        connection.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error creating category: {str(e)}"
        )


@router.put("/{category_id}")
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
        connection.commit()
        return {
            "id": category_id,
            "name": new_name,
            "parent_id": new_parent_id
        }
    except Exception as e:
        connection.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error updating category: {str(e)}"
        )


@router.delete("/{category_id}")
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
        connection.commit()
        return {"message": f"Category {category_id} deleted successfully"}
    except Exception as e:
        connection.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error deleting category: {str(e)}"
        )
