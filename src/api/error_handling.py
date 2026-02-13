#
# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (c) 2026 m2-eng
# Author: m2-eng
# Co-Author: GitHub Copilot
# License: GNU Affero General Public License v3.0 (AGPL-3.0-only)
# Purpose: Central error handling for the FiniA API.
#
"""
Central error handling for the FiniA API.
Provides consistent error-handling patterns for all routers.
"""

from functools import wraps
from typing import Callable, Any
from fastapi import HTTPException, status
from mysql.connector.errors import Error as MySQLError, OperationalError, InterfaceError, DatabaseError
import traceback


class DatabaseConnectionError(Exception):
    """Raised when database connection fails."""
    pass


def handle_db_errors(operation_name: str = "database operation"): # finding: Check for exceptions, which can be handled here instead of in individual endpoints.
    """
    Decorator for consistent error handling in API endpoints.
    
    Args:
        operation_name: Operation name for error messages
        
    Usage:
        @router.get("/endpoint")
        @handle_db_errors("fetch data")
        def my_endpoint(cursor = Depends(get_db_cursor_with_auth)):
            # Code here...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs) -> Any:
            try:
                return await func(*args, **kwargs)
            except HTTPException:
                # Re-raise HTTPExceptions directly (404, etc.)
                raise
            except (OperationalError, InterfaceError, DatabaseError) as exc:
                print(f"Database error in {operation_name}: {exc}")
                traceback.print_exc()
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail=f"Database connection error during {operation_name}. Please try again."
                )
            except MySQLError as exc:
                print(f"MySQL error in {operation_name}: {exc}")
                traceback.print_exc()
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Database error during {operation_name}: {str(exc)}"
                )
            except Exception as exc:
                print(f"Unexpected error in {operation_name}: {exc}")
                traceback.print_exc()
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Internal server error during {operation_name}"
                )
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs) -> Any:
            try:
                return func(*args, **kwargs)
            except HTTPException:
                # Re-raise HTTPExceptions directly (404, etc.)
                raise
            except (OperationalError, InterfaceError, DatabaseError) as exc:
                print(f"Database error in {operation_name}: {exc}")
                traceback.print_exc()
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail=f"Database connection error during {operation_name}. Please try again."
                )
            except MySQLError as exc:
                print(f"MySQL error in {operation_name}: {exc}")
                traceback.print_exc()
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Database error during {operation_name}: {str(exc)}"
                )
            except Exception as exc:
                print(f"Unexpected error in {operation_name}: {exc}")
                traceback.print_exc()
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Internal server error during {operation_name}"
                )
        
        # Check if function is async
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    
    return decorator


def safe_commit(connection, operation_name: str = "operation"):
    """
    Safe commit operation with error handling.
    
    Args:
        connection: Database connection
        operation_name: Operation name for error messages
        
    Raises:
        HTTPException: On commit failure
    """
    try:
        if connection and hasattr(connection, 'commit'):
            connection.commit()
    except Exception as exc:
        print(f"Commit failed for {operation_name}: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save changes for {operation_name}"
        )


def safe_rollback(connection, operation_name: str = "operation"):
    """
    Safe rollback operation with error handling.
    
    Args:
        connection: Database connection
        operation_name: Operation name for error messages
    """
    try:
        if connection and hasattr(connection, 'rollback'):
            connection.rollback()
            print(f"Rollback executed for {operation_name}")
    except Exception as exc:
        print(f"Rollback failed for {operation_name}: {exc}")
        # Do not propagate rollback errors
