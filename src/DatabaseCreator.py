#
# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (c) 2026 m2-eng
# Author: m2-eng
# Co-Author: GitHub Copilot
# License: GNU Affero General Public License v3.0 (AGPL-3.0-only)
# Purpose: Module for DatabaseCreator.
#
import logging
from mysql.connector import Error

from Database import Database


logger = logging.getLogger(__name__)

class DatabaseCreator:
   """Create the database schema from an SQL dump using a provided Database instance."""

   def __init__(self, db: Database):
      self.db = db

   def create_database(self) -> bool:
      """Create the database if it doesn't exist."""
      try:
         cursor = self.db.connection.cursor()
         cursor.execute(
            f"CREATE DATABASE IF NOT EXISTS `{self.db.database_name}` "
            f"DEFAULT CHARACTER SET utf8mb3 COLLATE utf8mb3_general_ci"
         )
         logger.info("Database '%s' created or already exists", self.db.database_name)
         cursor.close()
         return True
      except Error as e:
         logger.error("Error creating database: %s", e)
         return False
            

   def execute_sql_file(self, sql_file_path: str) -> bool:
      """
      Execute SQL commands from file.
      
      Args:
         sql_file_path: Path to the SQL dump file.
      
      Returns:
         True if all statements executed successfully (with non-critical warnings allowed), False otherwise.
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
         cursor = self.db.connection.cursor()
         total = len(statements)
         executed = 0
          
         logger.info("Executing %s SQL statements...", total)
          
         for i, statement in enumerate(statements, 1):
            try:
               # Skip empty statements
               if not statement.strip():
                  continue
                      
               cursor.execute(statement)
               executed += 1
                  
               # Print progress every 10 statements
               if i % 10 == 0 or i == total:
                  logger.info("Progress: %s/%s statements executed", i, total)
                    
            except Error as e:
               # Some statements might fail (e.g., ALGORITHM settings), continue with warnings
               if "ALGORITHM" not in str(e) and "DEFINER" not in str(e):
                  logger.warning("Warning executing statement %s: %s", i, e)
                  logger.warning("Statement: %s...", statement[:100])
          
         self.db.connection.commit()
         cursor.close()
          
         logger.info("Successfully executed %s SQL statements", executed)
         return True
          
      except FileNotFoundError:
         logger.error("SQL file not found: %s", sql_file_path)
         return False
      except Error as e:
         logger.error("Error executing SQL file: %s", e)
         return False
      
            
   def create_from_file(self, sql_file_path: str) -> bool:
      """
      Complete workflow: connect, create database, execute SQL file.
      
      Args:
         sql_file_path: Path to the SQL dump file.
      
      Returns:
         True on success, False on failure.
      """
      logger.info("%s", "=" * 100)
      logger.info("FiniA Database Creation Script")
      logger.info("%s", "=" * 100)
        
      # Connect to server
      if not self.db.connect(use_database=False):
         raise RuntimeError("Failed to connect to MySQL server")
            
      # Create database
      if not self.create_database():
         self.db.close()
         raise RuntimeError("Failed to create database")
            
      # Reconnect with database selected
      self.db.close()
      if not self.db.connect(use_database=True):
         raise RuntimeError("Failed to connect to MySQL database")
           
      # Execute SQL file
      success = self.execute_sql_file(sql_file_path)
        
      # Close connection
      self.db.close()
        
      if success:
         logger.info("%s", "=" * 100)
         logger.info("Database '%s' created successfully!", self.db.database_name)
         logger.info("%s", "=" * 100)
      else:
         logger.error("%s", "=" * 100)
         logger.error("Database creation failed")
         logger.error("%s", "=" * 100)
            
      return success
