"""
FastAPI dependencies for database access and authentication
"""

from typing import Generator
from fastapi import Depends, HTTPException, status
from mysql.connector.errors import OperationalError, InterfaceError, DatabaseError
from Database import Database
from utils import load_config
import traceback


# Global database instance (initialized on startup)
_db_instance: Database | None = None

# Global credentials storage (set before API startup)
_db_credentials: dict = {}


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


def get_database_credentials() -> dict:
    """Get stored database credentials."""
    return _db_credentials


def get_db_cursor():
    """
    Get database cursor - serieller Zugriff durch globalen Lock.
    
    Yields:
        Database cursor
        
    Raises:
        HTTPException: Bei Verbindungsfehlern
    """
    from Database import Database
    
    db = get_database()
    cursor = None
    
    try:
        # Hole Cursor (Lock wird in get_cursor() gesetzt)
        cursor = db.get_cursor()
        # Session-Timeouts erhöhen, um Abbrüche während großer Abfragen zu vermeiden
        try:
            cursor.execute("SET SESSION net_read_timeout=120")
            cursor.execute("SET SESSION net_write_timeout=120")
            cursor.execute("SET SESSION max_execution_time=120000")  # 120s
        except Exception:
            # Falls der Server einzelne Variablen nicht unterstützt, ignorieren
            pass
        yield cursor
    except Exception as e:
        print(f"Database error: {e}")
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection error"
        )
    finally:
        # Cursor schließen und Lock freigeben
        if cursor:
            try:
                cursor.close()
            except:
                pass
        # Lock IMMER freigeben
        try:
            Database._global_lock.release()
        except:
            pass  # Falls Lock nicht gehalten wurde


def get_db_connection():
    """
    Get database connection for transaction management (commit/rollback).
    
    Yields:
        Database connection
        
    Raises:
        HTTPException: Bei Verbindungsfehlern
    """
    db = get_database()
    
    # Stelle sicher dass Connection aktiv ist
    if not db.is_connected():
        if not db.connect():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database connection unavailable"
            )
    
    try:
        yield db.connection
    except (OperationalError, InterfaceError, DatabaseError) as e:
        print(f"Database error during transaction: {e}")
        traceback.print_exc()
        # Versuche Rollback
        try:
            db.rollback()
        except:
            pass
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection error during transaction"
        )
    except Exception as e:
        print(f"Unexpected error during transaction: {e}")
        traceback.print_exc()
        # Versuche Rollback
        try:
            db.rollback()
        except:
            pass
        raise
