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
            use_pure=False,  # C Extension
         )
            
         if self.connection.is_connected():
            db_info = self.connection.get_server_info()
            print(f"Successfully connected to MySQL server version {db_info}")
            return True
            
      except Error as e:
         print(f"Error connecting to MySQL: {e}")
         return False
      
      return False
      
      
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
      Return cursor with global lock - nur EIN Request gleichzeitig.
      Stellt sicher, dass Verbindung aktiv ist.
      """
      Database._global_lock.acquire()  # Lock wird in dependencies.py freigegeben
      
      try:
         # Prüfe und stelle Verbindung wieder her wenn nötig
         if not self.connection or not self.connection.is_connected():
            print("Connection lost, reconnecting...")
            if not self.connect():
               Database._global_lock.release()
               raise RuntimeError("Failed to establish database connection")
         
         # Ping um sicherzustellen, dass Verbindung noch aktiv ist
         try:
            self.connection.ping(reconnect=True)
         except:
            print("Ping failed, reconnecting...")
            if not self.connect():
               Database._global_lock.release()
               raise RuntimeError("Failed to reconnect to database")
         
         # Erstelle Cursor
         cursor = self.connection.cursor(buffered=True)
         return cursor
         
      except Exception as e:
         Database._global_lock.release()
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