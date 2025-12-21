#!/usr/bin/env python3
"""
Database creation script for FiniA
Creates the database structure from the SQL dump file on a specified MySQL/MariaDB server.
"""

import mysql.connector
from mysql.connector import Error
import os
import sys
import argparse
from pathlib import Path
import yaml


class DatabaseCreator:
   """Handles database creation from SQL dump file"""
    
   def __init__(self, host, user, password, database_name, port=3306):
      """
      Initialize database creator
        
      Args:
         host: MySQL server host address
         user: Database user
         password: Database password
         database_name: Name of the database to create
         port: MySQL server port (default: 3306)
      """
      self.host = host
      self.user = user
      self.password = password
      self.database_name = database_name
      self.port = port
      self.connection = None
        
   def connect(self, use_database=True):
      """
      Establish connection to MySQL server
        
      Args:
         use_database: If True, connect to specific database; if False, connect to server only
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
            
   def create_database(self):
      """Create the database if it doesn't exist"""
      try:
         cursor = self.connection.cursor()
         cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{self.database_name}` "
                        f"DEFAULT CHARACTER SET utf8mb3 COLLATE utf8mb3_general_ci")
         print(f"Database '{self.database_name}' created or already exists")
         cursor.close()
         return True
      except Error as e:
         print(f"Error creating database: {e}")
         return False
            
   def execute_sql_file(self, sql_file_path):
      """
      Execute SQL commands from file
        
      Args:
         sql_file_path: Path to the SQL dump file
      """
      try:
         # Read SQL file
         with open(sql_file_path, 'r', encoding='utf-8') as file:
            sql_content = file.read()
          
         # Split into individual statements
         # Remove comments and split by semicolons
         statements = []
         current_statement = []
          
         for line in sql_content.split('\n'):
            # Skip empty lines and comments
            stripped = line.strip()
            if not stripped or stripped.startswith('--') or stripped.startswith('/*!'):
               continue
            
            current_statement.append(line)
             
            # Check if line ends with semicolon
            if stripped.endswith(';'):
               statement = '\n'.join(current_statement)
               if statement.strip():
                  statements.append(statement)
               current_statement = []
          
         # Execute statements
         cursor = self.connection.cursor()
         total = len(statements)
         executed = 0
          
         print(f"\nExecuting {total} SQL statements...")
          
         for i, statement in enumerate(statements, 1):
            try:
               # Skip empty statements
               if not statement.strip():
                  continue
                      
               cursor.execute(statement)
               executed += 1
                  
               # Print progress every 10 statements
               if i % 10 == 0 or i == total:
                  print(f"  Progress: {i}/{total} statements executed", end='\r')
                    
            except Error as e:
               # Some statements might fail (e.g., ALGORITHM settings), continue with warnings
               if "ALGORITHM" not in str(e) and "DEFINER" not in str(e):
                  print(f"\nWarning executing statement {i}: {e}")
                  print(f"  Statement: {statement[:100]}...\n")
          
         self.connection.commit()
         cursor.close()
          
         print(f"\nSuccessfully executed {executed} SQL statements")
         return True
          
      except FileNotFoundError:
         print(f"SQL file not found: {sql_file_path}")
         return False
      except Error as e:
         print(f"Error executing SQL file: {e}")
         return False
            
   def close(self):
      """Close database connection"""
      if self.connection and self.connection.is_connected():
         self.connection.close()
         print("Database connection closed")
     
            
   def create_from_file(self, sql_file_path):
      """
      Complete workflow: connect, create database, execute SQL file
        
      Args:
         sql_file_path: Path to the SQL dump file
      """
      print(f"\n{'='*100}")
      print(f"FiniA Database Creation Script")
      print(f"{'='*100}\n")
        
      # Connect to server
      if not self.connect(use_database=False):
         raise RuntimeError("Failed to connect to MySQL server")
            
      # Create database
      if not self.create_database():
         self.close()
         raise RuntimeError("Failed to create database")
            
      # Reconnect with database selected
      self.close()
      if not self.connect(use_database=True):
         raise RuntimeError("Failed to connect to MySQL database")
           
      # Execute SQL file
      success = self.execute_sql_file(sql_file_path)
        
      # Close connection
      self.close()
        
      if success:
         print(f"\n{'='*100}")
         print(f"Database '{self.database_name}' created successfully!")
         print(f"{'='*100}\n")
      else:
         print(f"\n{'='*100}")
         print(f"Database creation failed")
         print(f"{'='*100}\n")
            
      return success


def load_config(config_path='config.yaml'):
   """
   Load configuration from YAML file
   
   Args:
      config_path: Path to config.yaml file
       
   Returns:
      Dictionary with configuration or exception on failure
   """
   try:
      config_file = Path(config_path)
      if not config_file.exists():
         raise FileNotFoundError(f"config.yaml not found at: {config_path}")
      else:
         with open(config_file, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
            return config

   except Exception as e:
      raise RuntimeError(f"Failed to load config.yaml: {e}")


if __name__ == "__main__":
   """Main function with argument parsing"""
   # Argument parser setup
   parser = argparse.ArgumentParser(
      description='Create FiniA database from SQL dump file (uses config.yaml for defaults)',
      formatter_class=argparse.RawDescriptionHelpFormatter,
      epilog="""
Examples:
  python create_database.py --user root --password secret
  python create_database.py -u dbuser -p dbpass
  python create_database.py --user root --password secret --config custom_config.yaml
  
Note: Most parameters are read from config.yaml by default.
      Use command-line arguments to override config values.
      """
   )
   parser.add_argument('-u', '--user',
                       required=True,
                       help='MySQL user')
   parser.add_argument('-p', '--password',
                       required=True,
                       help='MySQL password')
   parser.add_argument('-c', '--config',
                       default='config.yaml',
                       help='Path to config file (default: config.yaml)')
    
   args = parser.parse_args()

   # Load configuration from config.yaml
   config = load_config( args.config )
    
   # Extract defaults from config if available
   if config and 'database' in config:
      db_config = config['database']
      db_host = db_config.get('host', 'localhost')
      db_port = db_config.get('port', 3306)
      db_name = db_config.get('name', 'FiniA')
      sql_path = db_config.get('sql_file', './db/finia_draft.sql')
   else:
      raise KeyError("Database configuration not found in config.yaml")
    
   # Determine SQL file patha
   sql_file = Path(sql_path)
   if not sql_file.exists():
      raise FileNotFoundError(f"SQL file not found at: {sql_file}")
   else:
      print(f"Using SQL file: {sql_file}")
      
      # Create database
      creator = DatabaseCreator(
         host=db_host,
         user=args.user,
         password=args.password,
         database_name=db_name,
         port=db_port
      )
      
      try:
         success = creator.create_from_file(str(sql_file))
      except Exception as e:
         print(f"Error: {e}")
         success = False
      
      sys.exit(0 if success else 1)
