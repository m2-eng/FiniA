"""
FastAPI dependencies for database access and authentication
"""

from typing import Generator, Optional
from contextvars import ContextVar
from fastapi import Depends, HTTPException, status
from mysql.connector.errors import OperationalError, InterfaceError, DatabaseError, PoolError
from Database import Database
from utils import load_config
import traceback
from api.error_handling import get_cursor_with_retry
from api.auth_middleware import get_current_session


# Global database instance (initialized on startup)
_db_instance: Database | None = None
_request_connection: ContextVar[object] = ContextVar("request_connection", default=None)

# Global credentials storage (set before API startup)
_db_credentials: dict = {}

# Auth-related globals (set when auth is enabled)
_pool_manager = None
_session_store = None


def get_database_config() -> dict:
    """Load database configuration from config file."""
    return load_config('cfg/config.yaml')


def get_database() -> Database:
    """
    Get database instance (singleton pattern).
    
    Returns:
        Database instance
        
    Raises:
        HTTPException: If database not initialized
    """
    if _db_instance is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database not initialized"
        )
    return _db_instance


def set_database_instance(db: Database):
    """Set the global database instance."""
    global _db_instance
    _db_instance = db


def set_database_credentials(user: str, password: str, host: str = None, name: str = None, port: int = None):
    """Set database credentials for API startup."""
    global _db_credentials
    _db_credentials = {
        'user': user,
        'password': password,
        'host': host,
        'name': name,
        'port': port
    }


def set_auth_managers(session_store, pool_manager, rate_limiter):
    """Set auth managers for session-based authentication."""
    global _pool_manager, _session_store
    _session_store = session_store
    _pool_manager = pool_manager
    # rate_limiter wird derzeit nicht in dependencies verwendet


def get_database_credentials() -> dict:
    """Get stored database credentials."""
    return _db_credentials


def get_db_cursor():
    """
    Liefert einen Cursor. Nutzt eine request-lokale Verbindung, falls vorhanden,
    sonst wird kurzlebig eine eigene Verbindung aufgebaut und wieder geschlossen.
    """
    db = get_database()
    cursor = None
    created_conn = None

    try:
        # Verwende vorhandene Request-Verbindung, falls gesetzt
        conn = _request_connection.get()
        if conn is None:
            # Erzeuge kurzlebige Verbindung für Lesezugriffe
            conn = db.create_connection()
            if not conn:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Database connection unavailable"
                )
            created_conn = conn

        cursor = conn.cursor(buffered=True)

        # Session-Timeouts erhöhen (max_execution_time wird möglicherweise nicht unterstützt)
        try:
            cursor.execute("SET SESSION net_read_timeout=120")
            cursor.execute("SET SESSION net_write_timeout=120")
            try:
                cursor.execute("SET SESSION max_execution_time=120000")
            except:
                pass
        except Exception as e:
            print(f"Warning: Could not set session timeouts: {e}")

        yield cursor

    except Exception as e:
        print(f"Database error in get_db_cursor: {e}")
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection error. Please try again."
        )
    finally:
        if cursor:
            try:
                cursor.close()
            except Exception as e:
                print(f"Warning: Error closing cursor: {e}")
        # Schliesse nur die kurzlebig erzeugte Verbindung
        if created_conn:
            try:
                created_conn.close()
            except Exception:
                pass


def get_db_connection():
    """
    Liefert eine request-lokale Verbindung für Transaktionen (commit/rollback).
    Cursor-Abhängigkeiten greifen auf dieselbe Verbindung via ContextVar zu.
    """
    db = get_database()
    conn = None

    try:
        conn = db.create_connection()
        if not conn:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database connection unavailable"
            )

        # Setze Verbindung in Request-Kontext, damit get_db_cursor diese nutzen kann
        _request_connection.set(conn)

        # Optional: Session-Timeouts auf Verbindungs-Ebene setzen
        try:
            cur = conn.cursor()
            cur.execute("SET SESSION net_read_timeout=120")
            cur.execute("SET SESSION net_write_timeout=120")
            try:
                cur.execute("SET SESSION max_execution_time=120000")
            except:
                pass
            cur.close()
        except Exception as e:
            print(f"Warning: Could not set session timeouts on connection: {e}")

        yield conn

    except (OperationalError, InterfaceError, DatabaseError) as e:
        print(f"Database error during transaction: {e}")
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection error during transaction"
        )
    except Exception as e:
        print(f"Unexpected error during transaction: {e}")
        traceback.print_exc()
        raise
    finally:
        # Verbindung aus Context entfernen und schließen
        try:
            _request_connection.set(None)
        except Exception:
            pass
        if conn:
            try:
                conn.close()
            except Exception:
                pass


# ============================================================================
# Session-based Auth Dependencies
# ============================================================================

def get_db_cursor_with_auth(session_id: str = Depends(get_current_session)):
    """
    Liefert Cursor basierend auf Session-Auth (Connection Pool).
    
    Nutzt Connection Pool der User-Session für bessere Performance.
    
    Args:
        session_id: Session-ID aus JWT-Token (via get_current_session dependency)
        
    Yields:
        MySQL Cursor
    """
    if not _pool_manager:
        # Fallback: Auth nicht aktiviert, nutze alte Methode
        yield from get_db_cursor()
        return
    
    conn = None
    cursor = None
    
    try:
        # Connection aus Session-Pool holen
        conn = _pool_manager.get_connection(session_id)
        
        if not conn:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database connection unavailable"
            )
        
        cursor = conn.cursor(buffered=True)
        
        # Session-Timeouts erhöhen
        try:
            cursor.execute("SET SESSION net_read_timeout=120")
            cursor.execute("SET SESSION net_write_timeout=120")
            try:
                cursor.execute("SET SESSION max_execution_time=120000")
            except:
                pass
        except Exception as e:
            print(f"Warning: Could not set session timeouts: {e}")
        
        yield cursor
        
    except PoolError as e:
        print(f"Connection pool exhausted: {e}")
        if cursor:
            try:
                cursor.close()
            except:
                pass
        if conn:
            try:
                conn.close()
            except:
                pass
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Too many concurrent requests. Please try again in a moment."
        )
    except Exception as e:
        print(f"Database error in get_db_cursor_with_auth: {e}")
        traceback.print_exc()
        if cursor:
            try:
                cursor.close()
            except:
                pass
        if conn:
            try:
                conn.close()
            except:
                pass
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection error. Please try again."
        )
    finally:
        if cursor:
            try:
                cursor.close()
            except Exception as e:
                print(f"Warning: Error closing cursor: {e}")
        if conn:
            try:
                conn.close()  # Gibt Connection zurück an Pool
            except Exception:
                pass


def get_db_connection_with_auth(session_id: str = Depends(get_current_session)):
    """
    Liefert Connection basierend auf Session-Auth für Transaktionen.
    
    Args:
        session_id: Session-ID aus JWT-Token (via get_current_session dependency)
        
    Yields:
        MySQL Connection
    """
    if not _pool_manager:
        # Fallback: Auth nicht aktiviert
        yield from get_db_connection()
        return
    
    conn = None
    
    try:
        conn = _pool_manager.get_connection(session_id)
        
        if not conn:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database connection unavailable"
            )
        
        # Setze Connection in Context für Cursor
        _request_connection.set(conn)
        
        # Session-Timeouts
        try:
            cur = conn.cursor()
            cur.execute("SET SESSION net_read_timeout=120")
            cur.execute("SET SESSION net_write_timeout=120")
            try:
                cur.execute("SET SESSION max_execution_time=120000")
            except:
                pass
            cur.close()
        except Exception as e:
            print(f"Warning: Could not set session timeouts: {e}")
        
        yield conn
        
    except (OperationalError, InterfaceError, DatabaseError) as e:
        print(f"Database error during transaction: {e}")
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection error during transaction"
        )
    except Exception as e:
        print(f"Unexpected error during transaction: {e}")
        traceback.print_exc()
        raise
    finally:
        try:
            _request_connection.set(None)
        except Exception:
            pass
        if conn:
            try:
                conn.close()  # Zurück an Pool
            except Exception:
                pass
