#
# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (c) 2026 m2-eng
# Author: m2-eng
# Co-Author: GitHub Copilot
# License: GNU Affero General Public License v3.0 (AGPL-3.0-only)
# Purpose: FastAPI dependencies for database access and authentication
#
"""
FastAPI dependencies for database access and authentication
"""

from contextvars import ContextVar
from fastapi import Depends, HTTPException, status
from mysql.connector.errors import OperationalError, InterfaceError, DatabaseError, PoolError
from Database import Database
from utils import load_config
import traceback
from api.auth_context import AuthContext, get_auth_context
from api.auth_middleware import get_current_session


# Global database instance (initialized on startup)
_db_instance: Database | None = None # finding: Is this the correct database instance? Does the authentication uses the same database instance?
_request_connection: ContextVar[object] = ContextVar("request_connection", default=None)

# Global credentials storage (set before API startup)
_db_credentials: dict = {} # finding: Is this a dupolicate of the configuration loaded elsewhere?


def get_database_config(subconfig: str = None) -> dict:
    """Load database configuration from config file."""
    return load_config(config_path='cfg/config.yaml', subconfig=subconfig)


def get_database() -> Database: # finding: Is this the correct database instance?
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
    return _db_instance # finding: Is this the correct database instance?


def set_database_instance(db: Database): # finding: Is this the correct database instance? [#77]
    """Set the global database instance."""
    global _db_instance
    _db_instance = db


def set_database_credentials(user: str, password: str, host: str = None, name: str = None, port: int = None): # finding: Is this the correct database instance? Is this a duplicate? [#77]
    """Set database credentials for API startup."""
    global _db_credentials
    _db_credentials = {
        'user': user,
        'password': password,
        'host': host,
        'name': name,
        'port': port
    }


def get_database_credentials() -> dict: # finding: Is this a duplicate?
    """Get stored database credentials."""
    return _db_credentials


# ============================================================================
# Session-based Auth Dependencies
# ============================================================================

def get_db_cursor_with_auth(
    session_id: str = Depends(get_current_session),
    auth_context: AuthContext = Depends(get_auth_context),
):
    """
    Returns a cursor based on session auth (connection pool).
    
    Uses the user-session connection pool for better performance.
    
    Args:
        session_id: Session ID from JWT token (via get_current_session dependency)
        
    Yields:
        MySQL Cursor
    """
    if not auth_context.pool_manager:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Session-based authentication not configured"
        )
    
    conn = None
    cursor = None
    db_config = get_database_config('database')
    
    try:
        # Get connection from the session pool
        conn = auth_context.pool_manager.get_connection(session_id)
        
        if not conn:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database connection unavailable"
            )
        
        cursor = conn.cursor(buffered=True)
        
        # Increase session timeouts
        try: # finding: add a parameter to 'config.yaml' to define the timeout values
            cursor.execute(f"SET SESSION net_read_timeout={db_config.get('net_read_timeout', 120)}")
            cursor.execute(f"SET SESSION net_write_timeout={db_config.get('net_write_timeout', 120)}")
            try:
                cursor.execute(f"SET SESSION max_execution_time={db_config.get('max_execution_time', 120000)}")
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
    except HTTPException:
        # Preserve explicit HTTP errors from route handlers
        raise
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
                conn.close()  # Return connection to pool
            except Exception:
                pass


def get_db_connection_with_auth(
    session_id: str = Depends(get_current_session),
    auth_context: AuthContext = Depends(get_auth_context),
):
    """
    Returns a connection based on session auth for transactions.
    
    Args:
        session_id: Session ID from JWT token (via get_current_session dependency)
        
    Yields:
        MySQL Connection
    """
    if not auth_context.pool_manager:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Session-based authentication not configured"
        )

    conn = None
    db_config = get_database_config('database')
    
    try:
        conn = auth_context.pool_manager.get_connection(session_id)
        
        if not conn:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database connection unavailable"
            )
        
        # Store connection in context for cursor access
        _request_connection.set(conn)
        
        # Session timeouts
        try:
            cur = conn.cursor()
            cur.execute(f"SET SESSION net_read_timeout={db_config.get('net_read_timeout', 120)}")
            cur.execute(f"SET SESSION net_write_timeout={db_config.get('net_write_timeout', 120)}")
            try:
                cur.execute(f"SET SESSION max_execution_time={db_config.get('max_execution_time', 120000)}")
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
    except HTTPException:
        # Preserve explicit HTTP errors from route handlers
        raise
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
                conn.close()  # Back to pool
            except Exception:
                pass


def get_pool_manager(auth_context: AuthContext = Depends(get_auth_context)):
    """
    Returns the ConnectionPoolManager for imports.
    
    Returns:
        ConnectionPoolManager instance
        
    Raises:
        HTTPException: If the pool manager is not initialized
    """
    if not auth_context.pool_manager:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Session-based authentication not configured"
        )
    return auth_context.pool_manager
