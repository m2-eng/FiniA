"""
FastAPI dependencies for database access and authentication
"""

from typing import Generator
from fastapi import Depends, HTTPException, status
from Database import Database
from utils import load_config


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
    Get database cursor for repository operations.
    
    Yields:
        Database cursor
    """
    db = get_database()
    cursor = db.get_cursor()
    try:
        yield cursor
    finally:
        # Cursor cleanup handled by Database class
        pass


def get_db_connection():
    """
    Get database connection for transaction management (commit/rollback).
    
    Yields:
        Database connection
    """
    db = get_database()
    connection = db.connection
    try:
        yield connection
    finally:
        pass
