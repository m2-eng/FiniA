#
# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (c) 2026 m2-eng
# Author: m2-eng
# Co-Author: GitHub Copilot
# License: GNU Affero General Public License v3.0 (AGPL-3.0-only)
# Purpose: Module for account type repository.
#
from repositories.base import BaseRepository
from datetime import datetime


class AccountTypeRepository(BaseRepository):
   """Repository for account type management."""

   def get_all(self):
      """Get all account types ordered by ID."""
      query = """
         SELECT id, type, dateImport
         FROM tbl_accountType
         ORDER BY id ASC
      """
      self.cursor.execute(query)
      rows = self.cursor.fetchall()
      
      if not rows:
         return []
      
      return [
         {
            "id": row[0],
            "type": row[1],
            "dateImport": row[2].isoformat() if row[2] else None
         }
         for row in rows
      ]

   def get_by_id(self, account_type_id: int):
      """Get account type by ID."""
      query = "SELECT id, type, dateImport FROM tbl_accountType WHERE id = %s"
      self.cursor.execute(query, (account_type_id,))
      row = self.cursor.fetchone()
      
      if not row:
         return None
      
      return {
         "id": row[0],
         "type": row[1],
         "dateImport": row[2].isoformat() if row[2] else None
      }

   def get_by_type(self, type_name: str):
      """Get account type by name."""
      query = "SELECT id, type, dateImport FROM tbl_accountType WHERE type = %s"
      self.cursor.execute(query, (type_name,))
      row = self.cursor.fetchone()
      
      if not row:
         return None
      
      return {
         "id": row[0],
         "type": row[1],
         "dateImport": row[2].isoformat() if row[2] else None
      }

   def insert(self, type_name: str):
      """
      Insert new account type.
      
      Args:
         type_name: Name of the account type
         
      Returns:
         ID of the inserted account type
         
      Raises:
         Exception if type already exists (UNIQUE constraint)
      """
      query = """
         INSERT INTO tbl_accountType (type, dateImport)
         VALUES (%s, %s)
      """
      now = datetime.now()
      self.cursor.execute(query, (type_name, now))
      return self.cursor.lastrowid

   def insert_ignore(self, type_id: int, type_name: str) -> None:
      """Insert account type with specific ID, ignoring duplicates."""
      sql = "INSERT IGNORE INTO tbl_accountType (id, type, dateImport) VALUES (%s, %s, NOW())"
      self.cursor.execute(sql, (type_id, type_name))

   def insert_with_id(self, account_type_id: int, type_name: str):
      """
      Insert account type with specific ID (for YAML import).
      
      Args:
         account_type_id: Specific ID to use
         type_name: Name of the account type
         
      Returns:
         ID of the inserted account type
         
      Raises:
         Exception if ID or type already exists
      """
      query = """
         INSERT INTO tbl_accountType (id, type, dateImport)
         VALUES (%s, %s, %s)
      """
      now = datetime.now()
      self.cursor.execute(query, (account_type_id, type_name, now))
      return self.cursor.lastrowid

   def update(self, account_type_id: int, type_name: str):
      """
      Update account type name.
      
      Args:
         account_type_id: ID of the account type to update
         type_name: New name for the account type
         
      Returns:
         Number of affected rows (1 if successful, 0 if not found)
      """
      query = """
         UPDATE tbl_accountType
         SET type = %s
         WHERE id = %s
      """
      self.cursor.execute(query, (type_name, account_type_id))
      return self.cursor.rowcount

   def delete(self, account_type_id: int):
      """
      Delete account type by ID.
      
      Args:
         account_type_id: ID of the account type to delete
         
      Returns:
         Number of affected rows (1 if successful, 0 if not found)
         
      Note:
         Will fail if there are still accounts using this type (FK constraint)
      """
      query = "DELETE FROM tbl_accountType WHERE id = %s"
      self.cursor.execute(query, (account_type_id,))
      return self.cursor.rowcount

