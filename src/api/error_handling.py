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


class RetryableError(Exception):
    """Wird geworfen für Fehler, bei denen Retry sinnvoll ist"""
    pass


def handle_db_errors(operation_name: str = "database operation"):
    """
    Decorator für einheitliche Fehlerbehandlung in API-Endpunkten.
    
    Args:
        operation_name: Name der Operation für Fehlermeldungen
        
    Verwendung:
        @router.get("/endpoint")
        @handle_db_errors("fetch data")
        def my_endpoint(cursor = Depends(get_db_cursor)):
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


def get_cursor_with_retry(get_db_func, max_retries: int = 3):
    """
    Erstellt Cursor mit automatischem Reconnect bei Fehlern.
    
    Args:
        get_db_func: Funktion zum Abrufen der Database-Instanz
        max_retries: Maximale Anzahl von Wiederholungsversuchen
        
    Returns:
        Database cursor
        
    Raises:
        DatabaseConnectionError: Wenn Verbindung nach allen Retries fehlschlägt
    """
    for attempt in range(max_retries):
        try:
            db = get_db_func()
            
            # Versuche reconnect
            try:
                db.connection.reconnect(attempts=2, delay=0)
            except (AttributeError, ReferenceError):
                # Connection-Objekt existiert nicht oder ist ungültig
                db.connect()
            except Exception:
                # Reconnect fehlgeschlagen, versuche neu zu verbinden
                if not db.connect():
                    if attempt == max_retries - 1:
                        raise DatabaseConnectionError("Failed to establish database connection")
                    continue
            
            # Hole Cursor
            try:
                cursor = db.get_cursor()
                return cursor
            except Exception:
                # Cursor-Erstellung fehlgeschlagen, versuche Reconnect
                if not db.connect():
                    if attempt == max_retries - 1:
                        raise DatabaseConnectionError("Failed to get database cursor")
                    continue
                cursor = db.get_cursor()
                return cursor
                
        except DatabaseConnectionError:
            raise
        except Exception as exc:
            if attempt == max_retries - 1:
                raise DatabaseConnectionError(f"Failed to get cursor after {max_retries} attempts: {exc}")
            print(f"Retry {attempt + 1}/{max_retries} for cursor creation...")
    
    raise DatabaseConnectionError(f"Failed to get cursor after {max_retries} attempts")


def execute_query_with_retry(cursor, query: str, params: tuple = None, max_retries: int = 2):
    """
    Führt SQL-Query mit automatischem Retry bei Connection-Fehlern aus.
    
    Args:
        cursor: Database cursor
        query: SQL-Query
        params: Query-Parameter
        max_retries: Maximale Anzahl von Wiederholungsversuchen
        
    Returns:
        Tuple (cursor, rows): Cursor und Ergebnis-Rows
        
    Raises:
        DatabaseError: Bei persistenten DB-Fehlern
    """
    for attempt in range(max_retries):
        try:
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            rows = cursor.fetchall()
            return cursor, rows
        except (OperationalError, InterfaceError, ReferenceError) as exc:
            if attempt == max_retries - 1:
                raise DatabaseError(f"Query failed after {max_retries} attempts: {exc}")
            print(f"Query retry {attempt + 1}/{max_retries} due to: {exc}")
            # Bei letztem Versuch Exception durchreichen
    
    raise DatabaseError(f"Query failed after {max_retries} attempts")


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
