import mysql.connector
from mysql.connector import Error

class Database:
   """Manages MySQL connections for FiniA."""
   
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
      Establish connection to MySQL server.
      
      Args:
         use_database: If True, connect to specific database; if False, connect to server only.
      
      Returns:
         True on successful connection, False otherwise.
      """
      try:          
         if use_database:
            self.connection = mysql.connector.connect(host=self.host,
                                                      user=self.user,
                                                      password=self.password,
                                                      port=self.port,
                                                      database=self.database_name )
         else:      
            self.connection = mysql.connector.connect(host=self.host,
                                                      user=self.user,
                                                      password=self.password,
                                                      port=self.port )
            
         if self.connection.is_connected():
            db_info = self.connection.get_server_info()
            print(f"Successfully connected to MySQL server version {db_info}")
            return True
         
      except Error as e:
         print(f"Error connecting to MySQL: {e}")
         return False
      
      
   def close(self) -> None:
      """Close database connection."""
      if self.connection and self.connection.is_connected():
         self.connection.close()
         print("Database connection closed")

   def get_cursor(self):
      """Return a live cursor, reconnecting if needed."""
      if not self.connection or not self.connection.is_connected():
         self.connect()
      return self.connection.cursor()

   def commit(self) -> None:
      """Commit current transaction if connection is active."""
      if self.connection and self.connection.is_connected():
         self.connection.commit()