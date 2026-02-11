"""
Zentrale Fehlerbehandlung für FiniA API
Bietet konsistente Error-Handling-Patterns für alle Router
"""

from functools import wraps
from typing import Callable, Any
from fastapi import HTTPException, status
from mysql.connector.errors import Error as MySQLError, OperationalError, InterfaceError, DatabaseError
import traceback


class DatabaseConnectionError(Exception):
    """Wird geworfen, wenn Datenbankverbindung fehlschlägt"""
    pass


def handle_db_errors(operation_name: str = "database operation"): # finding: Check for exceptions, which can be handled here instead of in individual endpoints.
    """
    Decorator für einheitliche Fehlerbehandlung in API-Endpunkten.
    
    Args:
        operation_name: Name der Operation für Fehlermeldungen
        
    Verwendung:
        @router.get("/endpoint")
        @handle_db_errors("fetch data")
        def my_endpoint(cursor = Depends(get_db_cursor_with_auth)):
            # Code hier...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs) -> Any:
            try:
                return await func(*args, **kwargs)
            except HTTPException:
                # HTTPExceptions direkt durchreichen (404, etc.)
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
                # HTTPExceptions direkt durchreichen (404, etc.)
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
        
        # Prüfe ob Funktion async ist
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    
    return decorator


def safe_commit(connection, operation_name: str = "operation"):
    """
    Sichere Commit-Operation mit Fehlerbehandlung.
    
    Args:
        connection: Database connection
        operation_name: Name der Operation für Fehlermeldungen
        
    Raises:
        HTTPException: Bei Commit-Fehler
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
    Sichere Rollback-Operation mit Fehlerbehandlung.
    
    Args:
        connection: Database connection
        operation_name: Name der Operation für Fehlermeldungen
    """
    try:
        if connection and hasattr(connection, 'rollback'):
            connection.rollback()
            print(f"Rollback executed for {operation_name}")
    except Exception as exc:
        print(f"Rollback failed for {operation_name}: {exc}")
        # Rollback-Fehler nicht durchreichen
