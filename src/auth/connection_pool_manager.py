"""
MySQL Connection Pool Management pro Session.
"""

import mysql.connector.pooling
from typing import Dict, Optional
from mysql.connector import Error


class PoolNotFoundError(Exception):
    """Connection Pool existiert nicht."""
    pass


class ConnectionPoolManager:
    """
    Verwaltet MySQL Connection Pools pro Session.
    
    Jede Session bekommt einen eigenen Connection Pool
    für bessere Performance und Isolation.
    """
    
    def __init__(self, host: str, port: int, pool_size: int = 5):
        """
        Initialisiert Connection Pool Manager.
        
        Args:
            host: MySQL-Server Host
            port: MySQL-Server Port
            pool_size: Anzahl Connections pro Pool (default: 5)
        """
        self.host = host
        self.port = port
        self.pool_size = pool_size
        self.pools: Dict[str, mysql.connector.pooling.MySQLConnectionPool] = {}
    
    def create_pool(self, session_id: str, username: str, password: str, database: str) -> None:
        """
        Erstellt neuen Connection Pool für Session.
        
        Args:
            session_id: Session-ID
            username: DB-Username
            password: DB-Password
            database: Datenbankname
            
        Raises:
            Error: Bei DB-Connection-Fehler
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
                autocommit=False,
                use_pure=True
            )
        except Error as e:
            raise Error(f"Fehler beim Erstellen des Connection Pools: {e}")
    
    def get_connection(self, session_id: str):
        """
        Holt Connection aus Pool für diese Session.
        
        Args:
            session_id: Session-ID
            
        Returns:
            MySQL Connection
            
        Raises:
            PoolNotFoundError: Pool existiert nicht
        """
        if session_id not in self.pools:
            raise PoolNotFoundError(f"Connection Pool nicht gefunden für Session: {session_id}")
        
        return self.pools[session_id].get_connection()
    
    def close_pool(self, session_id: str) -> None:
        """
        Schließt alle Connections und entfernt Pool.
        
        Args:
            session_id: Session-ID
        """
        if session_id in self.pools:
            # Pool wird automatisch bereinigt bei Deletion
            del self.pools[session_id]
    
    def get_pool_count(self) -> int:
        """Gibt Anzahl aktiver Connection Pools zurück."""
        return len(self.pools)
    
    def has_pool(self, session_id: str) -> bool:
        """
        Prüft ob Pool für Session existiert.
        
        Args:
            session_id: Session-ID
            
        Returns:
            True wenn Pool existiert
        """
        return session_id in self.pools
