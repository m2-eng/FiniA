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

import logging
import traceback

logger = logging.getLogger("uvicorn.error")

class DatabaseConnectionError(Exception):
    """Raised when database connection fails."""
    pass


def handle_db_errors(
    operation_name: str = "database operation",
    error_message: str | None = None,
):
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
        def log_exception(
            exc: Exception,
            base_message: str,
            status_code: int,
            additional_info: str = "",
        ) -> None:
            final_message = error_message or base_message
            detail = f"{final_message} ({operation_name}): {exc}"
            if additional_info:
                detail = f"{detail}\n\n{additional_info}"
            logger.error(detail)
            traceback.print_exc()
            raise HTTPException(
                status_code=status_code,
                detail=detail
            )

        @wraps(func)
        async def async_wrapper(*args, **kwargs) -> Any:
            try:
                return await func(*args, **kwargs)
            except HTTPException:
                # Re-raise HTTPExceptions directly (404, etc.)
                raise
            except (OperationalError, InterfaceError, DatabaseError) as exc:
                log_exception(
                    exc,
                    "Database connection error",
                    status.HTTP_503_SERVICE_UNAVAILABLE,
                    additional_info="Please try again.",
                )
            except MySQLError as exc:
                log_exception(
                    exc,
                    "Database error",
                    status.HTTP_500_INTERNAL_SERVER_ERROR,
                )
            except Exception as exc:
                log_exception(
                    exc,
                    "Internal server error",
                    status.HTTP_500_INTERNAL_SERVER_ERROR,
                )
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs) -> Any:
            try:
                return func(*args, **kwargs)
            except HTTPException:
                # Re-raise HTTPExceptions directly (404, etc.)
                raise
            except (OperationalError, InterfaceError, DatabaseError) as exc:
                log_exception(
                    exc,
                    "Database connection error",
                    status.HTTP_503_SERVICE_UNAVAILABLE,
                    additional_info="Please try again.",
                )
            except MySQLError as exc:
                log_exception(
                    exc,
                    "Database error",
                    status.HTTP_500_INTERNAL_SERVER_ERROR,
                )
            except Exception as exc:
                log_exception(
                    exc,
                    "Internal server error",
                    status.HTTP_500_INTERNAL_SERVER_ERROR,
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
        logger.error(f"Commit failed for {operation_name}: {exc}")
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
            logger.info(f"Rollback executed for {operation_name}")
    except Exception as exc:
        logger.error(f"Rollback failed for {operation_name}: {exc}")
        # Do not propagate rollback errors
