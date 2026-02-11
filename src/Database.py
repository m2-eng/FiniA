import mysql.connector
from mysql.connector import Error
import threading

class Database:
   """Einfache, robuste MySQL-Verbindung mit globalem Lock für serielle Abarbeitung."""
   
   # Globaler Lock - nur EIN Request gleichzeitig auf DB
   _global_lock = threading.RLock()
   
   def __init__(self, host: str, user: str, password: str, database_name: str, port: int = 3306):
      """
      Initialize database connection parameters.
      
      Args:
         host: MySQL server host address
         user: Database user
         password: Database password
         database_name: Name of the database
         port: MySQL server port (default: 3306)
      """
      self.host = host
      self.user = user
      self.password = password
      self.database_name = database_name
      self.port = port
      self.connection = None
    
   def connect(self, use_database: bool = True) -> bool:
      """
      Establish persistent connection to MySQL server.
      
      Args:
         use_database: If True, connect to specific database; if False, connect to server only.
      
      Returns:
         True on successful connection, False otherwise.
      """
      try:
         # Schließe alte Connection falls vorhanden
         if self.connection:
            try:
               if self.connection.is_connected():
                  self.connection.close()
            except:
               pass
            self.connection = None
         
         # Einfache, dauerhafte Connection
         self.connection = mysql.connector.connect(
            host=self.host,
            user=self.user,
            password=self.password,
            database=self.database_name if use_database else None,
            port=self.port,
            autocommit=True,
            use_pure=True,  # pure Python fallback; avoids missing C extension
         )
            
         if self.connection.is_connected():
            db_info = self.connection.get_server_info()
            print(f"Successfully connected to MySQL server version {db_info}")
            return True
            
      except Error as e:
         print(f"Error connecting to MySQL: {e}")
         return False
      
      return False
      
   def create_connection(self, use_database: bool = True):
      """
      Create and return a NEW MySQL connection (independent of the persistent one).
      Useful for per-request isolation to avoid shared-connection contention.
      """
      try:
         conn = mysql.connector.connect(
            host=self.host,
            user=self.user,
            password=self.password,
            database=self.database_name if use_database else None,
            port=self.port,
            autocommit=True,
            use_pure=True,
         )
         return conn
      except Error as e:
         print(f"Error creating new connection: {e}")
         return None

      
   def close(self) -> None:
      """Close database connection safely."""
      try:
         if self.connection and self.connection.is_connected():
            self.connection.close()
            print("Database connection closed")
      except Exception as e:
         print(f"Error closing connection: {e}")
      finally:
         self.connection = None

   def is_connected(self) -> bool:
      """Check if database connection is active."""
      try:
         return self.connection is not None and self.connection.is_connected()
      except:
         return False

   def get_cursor(self):
      """
      Return cursor. Verbindung wird in get_db_cursor_with_auth() gemanagt (dependencies.py).
      Lock wird von get_db_cursor_with_auth() gehalten.
      """
      try:
         # Erstelle Cursor - Verbindung wurde bereits in get_db_cursor() validiert
         if not self.connection:
            raise RuntimeError("Connection not available")
         
         cursor = self.connection.cursor(buffered=True)
         return cursor
         
      except Exception as e:
         raise RuntimeError(f"Failed to get cursor: {e}")

   def commit(self) -> None:
      """Commit current transaction if connection is active."""
      try:
         if self.is_connected():
            self.connection.commit()
      except Exception as e:
         print(f"Commit failed: {e}")
         raise
   
   def rollback(self) -> None:
      """Rollback current transaction if connection is active."""
      try:
         if self.is_connected():
            self.connection.rollback()
      except Exception as e:
         print(f"Rollback failed: {e}")
         # Rollback-Fehler nicht durchreichen