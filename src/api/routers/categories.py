"""
Categories API Router
"""

from fastapi import APIRouter, Depends
from repositories.category_repository import CategoryRepository
from api.dependencies import get_db_cursor

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
