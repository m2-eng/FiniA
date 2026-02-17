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
import logging
from fastapi import Depends, HTTPException, status
from mysql.connector.errors import OperationalError, InterfaceError, DatabaseError, PoolError
from config import get_config_section
from api.auth_context import AuthContext, get_auth_context
from api.auth_middleware import get_current_session


logger = logging.getLogger("uvicorn.error")


_request_connection: ContextVar[object] = ContextVar("request_connection", default=None)


def get_database_config(subconfig: str = None) -> dict:
    """Load database configuration from config file."""
    return get_config_section(subconfig)


# ============================================================================
# Session-based Auth Dependencies
# ============================================================================

def get_db_cursor(
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
        try:
            cursor.execute(f"SET SESSION net_read_timeout={db_config.get('net_read_timeout', 120)}")
            cursor.execute(f"SET SESSION net_write_timeout={db_config.get('net_write_timeout', 120)}")
            try:
                cursor.execute(f"SET SESSION max_execution_time={db_config.get('max_execution_time', 120000)}")
            except:
                pass
        except Exception as e:
            logger.warning("Could not set session timeouts: %s", e)
        
        yield cursor
        
    except PoolError as e:
        logger.warning("Connection pool exhausted: %s", e)
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
        logger.exception("Database error in get_db_cursor: %s", e)
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
                logger.warning("Error closing cursor: %s", e)
        if conn:
            try:
                conn.close()  # Return connection to pool
            except Exception:
                pass


def get_db_connection(
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
            logger.warning("Could not set session timeouts: %s", e)
        
        yield conn
        
    except (OperationalError, InterfaceError, DatabaseError) as e:
        logger.exception("Database error during transaction: %s", e)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection error during transaction"
        )
    except HTTPException:
        # Preserve explicit HTTP errors from route handlers
        raise
    except Exception as e:
        logger.exception("Unexpected error during transaction: %s", e)
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
