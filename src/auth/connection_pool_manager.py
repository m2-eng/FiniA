#
# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (c) 2026 m2-eng
# Author: m2-eng
# Co-Author: GitHub Copilot
# License: GNU Affero General Public License v3.0 (AGPL-3.0-only)
# Purpose: MySQL connection pool management per session.
#
"""
MySQL connection pool management per session.
"""

import mysql.connector.pooling
from typing import Dict
from mysql.connector import Error


class PoolNotFoundError(Exception):
    """Connection pool does not exist."""
    pass


class ConnectionPoolManager:
    """
    Manages MySQL connection pools per session.
    
    Each session gets its own connection pool
    for better performance and isolation.
    """
    
    def __init__(self, host: str, port: int, pool_size: int = 5):
        """
        Initializes the connection pool manager.
        
        Args:
            host: MySQL server host
            port: MySQL server port
            pool_size: Connections per pool (default: 5)
        """
        self.host = host
        self.port = port
        self.pool_size = pool_size
        self.pools: Dict[str, mysql.connector.pooling.MySQLConnectionPool] = {}
    
    def create_pool(self, session_id: str, username: str, password: str, database: str) -> None:
        """
        Creates a new connection pool for a session.
        
        Args:
            session_id: Session ID
            username: DB username
            password: DB password
            database: Database name
            
        Raises:
            Error: On DB connection error
        """
        pool_name = f"pool_{session_id[:16]}"
        
        try:
            self.pools[session_id] = mysql.connector.pooling.MySQLConnectionPool(
                pool_name=pool_name,
                pool_size=self.pool_size,
                host=self.host,
                port=self.port,
                user=username,
                password=password,
                database=database,
                autocommit=True, # must be true for proper transaction handling, see issue #55
                use_pure=True
            )
        except Error as e:
            raise Error(f"Error creating connection pool: {e}")
    
    def get_connection(self, session_id: str):
        """
        Gets a connection from the pool for this session.
        
        Args:
            session_id: Session ID
            
        Returns:
            MySQL Connection
            
        Raises:
            PoolNotFoundError: Pool does not exist
        """
        if session_id not in self.pools:
            raise PoolNotFoundError(f"Connection pool not found for session: {session_id}")
        
        return self.pools[session_id].get_connection()
    
    def close_pool(self, session_id: str) -> None:
        """
        Closes all connections and removes the pool.
        
        Args:
            session_id: Session ID
        """
        if session_id in self.pools:
            # Pool is cleaned up on deletion
            del self.pools[session_id]

    def close_all(self) -> int:
        """Closes all pools and returns the number removed."""
        session_ids = list(self.pools.keys())
        for session_id in session_ids:
            self.close_pool(session_id)
        return len(session_ids)
    
    def get_pool_count(self) -> int:
        """Returns the number of active connection pools."""
        return len(self.pools)
    
    def has_pool(self, session_id: str) -> bool:
        """
        Checks whether a pool exists for the session.
        
        Args:
            session_id: Session ID
            
        Returns:
            True if the pool exists
        """
        return session_id in self.pools
