#
# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (c) 2026 m2-eng
# Author: m2-eng
# Co-Author: GitHub Copilot
# License: GNU Affero General Public License v3.0 (AGPL-3.0-only)
# Purpose: Module for transaction repository.
#
from datetime import datetime
from decimal import Decimal

from repositories.base import BaseRepository


class TransactionRepository(BaseRepository):
   def __init__(self, cursor):
      """Initialize repository with cursor and category cache."""
      super().__init__(cursor)
      self._category_cache = None
   
   def _build_category_name_map(self) -> dict:
      """
      Build a map of category IDs to their full hierarchical names.
      Uses a single query and builds the hierarchy in Python.
      
      Returns:
         Dictionary mapping category ID to full category name
      """
      if self._category_cache is not None:
         return self._category_cache
      
      # Load all categories
      sql = "SELECT id, name, category FROM tbl_category ORDER BY id"
      self.cursor.execute(sql)
      categories = {row[0]: {"name": row[1], "parent_id": row[2]} for row in self.cursor.fetchall()}
      
      # Build full names
      category_names = {}
      
      def build_full_name(cat_id):
         if cat_id not in categories:
            return None
         if cat_id in category_names:
            return category_names[cat_id]
         
         cat = categories[cat_id]
         name = cat["name"]
         parent_id = cat["parent_id"]
         
         if parent_id and parent_id in categories:
            parent_name = build_full_name(parent_id)
            if parent_name:
               full_name = f"{parent_name} > {name}"
            else:
               full_name = name
         else:
            full_name = name
         
         category_names[cat_id] = full_name
         return full_name
      
      # Build names for all categories
      for cat_id in categories:
         build_full_name(cat_id)
      
      self._category_cache = category_names
      return category_names
   
   def insert_ignore(
      self,
      account_id: int,
      description: str,
      amount: Decimal,
      date_value: datetime,
      iban: str | None = None,
      bic: str | None = None,
      recipient_applicant: str | None = None,
   ) -> int | None:
      """
      Insert transaction with automatic ID generation.
      
      Returns:
         Transaction ID if newly inserted, None if failure.
      """
      sql = (
         """INSERT INTO tbl_transaction
               (dateImport, iban, bic, description, amount, dateValue, recipientApplicant, account)
               VALUES (NOW(), %s, %s, %s, %s, %s, %s, %s)"""
      )
      self.cursor.execute(
         sql,
         (
            iban,
            bic,
            description,
            amount,
            date_value,
            recipient_applicant,
            account_id,
         ),
      )
      if self.cursor.rowcount == 1:
         return self.cursor.lastrowid
      return None

   def insert_ignore_many(self, rows: list[tuple]) -> int:
      """
      Batch insert transactions with INSERT IGNORE.

      Args:
         rows: List of tuples (iban, bic, description, amount, date_value, recipient_applicant, account_id)

      Returns:
         Number of rows inserted (duplicates ignored).
      """
      if not rows:
         return 0

      sql = (
         """INSERT IGNORE INTO tbl_transaction
               (dateImport, iban, bic, description, amount, dateValue, recipientApplicant, account)
               VALUES (NOW(), %s, %s, %s, %s, %s, %s, %s)"""
      )
      self.cursor.executemany(sql, rows)
      return max(self.cursor.rowcount or 0, 0)

   def get_all_transactions(self) -> list[dict]:
      """
      Retrieve all transactions with their accounting entries (legacy: returns all).
      
      Returns:
         List of transaction dictionaries with accounting entries and account info.
      """
      return self.get_all_transactions_paginated(page=1, page_size=1000000)['transactions']

   def get_all_transactions_paginated(
      self,
      page: int = 1,
      page_size: int = 100,
      search: str = None,
      filter_type: str = None,
      account_id: int = None,
      date_from: str = None,
      date_to: str = None,
      sort_by: str = None,
      sort_dir: str = None
   ) -> dict:
      """
      Retrieve paginated transactions with their accounting entries.
      
      Args:
         page: Page number (1-based)
         page_size: Number of records per page (max 1000)
         search: Optional search term for filtering
         filter_type: Optional filter ('unchecked', 'no_entries', 'uncategorized', 'categorized_unchecked')
         account_id: Optional account ID filter
         date_from: Optional date filter (YYYY-MM-DD) from
         date_to: Optional date filter (YYYY-MM-DD) to
         sort_by: Optional sort column ('date', 'description', 'amount', 'account', 'entries')
         sort_dir: Optional sort direction ('asc' or 'desc')

      Returns:
         Dict with 'transactions' list, 'page', 'page_size', and 'total' count
      """
      page = max(1, page)
      page_size = min(max(1, page_size), 100000)  # Increased limit to 100k for get_all_transactions()
      offset = (page - 1) * page_size
      
      # Build WHERE clauses for filtering
      where_clauses = []
      params = []
      
      # Search filter in SQL
      if search:
         search_term = f"%{search}%"
         where_clauses.append("""(
            t.description LIKE %s OR 
            t.recipientApplicant LIKE %s OR 
            t.iban LIKE %s OR 
            t.bic LIKE %s OR 
            a.name LIKE %s OR
            EXISTS (
               SELECT 1 FROM tbl_accountingEntry ae 
               LEFT JOIN tbl_category c ON ae.category = c.id 
               WHERE ae.transaction = t.id AND c.name LIKE %s
            )
         )""")
         params.extend([search_term] * 6)
      
      # Filter type in SQL  
      if filter_type == "unchecked":
         where_clauses.append("""EXISTS (
            SELECT 1 FROM tbl_accountingEntry ae 
            WHERE ae.transaction = t.id AND ae.checked = 0
         )""")
      elif filter_type == "no_entries":
         where_clauses.append("""NOT EXISTS (
            SELECT 1 FROM tbl_accountingEntry ae WHERE ae.transaction = t.id
         )""")
      elif filter_type == "uncategorized":
         where_clauses.append("""EXISTS (
            SELECT 1 FROM tbl_accountingEntry ae 
            WHERE ae.transaction = t.id AND ae.category IS NULL
         )""")
      elif filter_type == "categorized_unchecked":
         where_clauses.append("""EXISTS (
            SELECT 1 FROM tbl_accountingEntry ae 
            WHERE ae.transaction = t.id AND ae.category IS NOT NULL AND ae.checked = 0
         )""")

      if account_id:
         where_clauses.append("t.account = %s")
         params.append(account_id)

      if date_from:
         where_clauses.append("t.dateValue >= %s")
         params.append(date_from)

      if date_to:
         where_clauses.append("t.dateValue <= %s")
         params.append(date_to)
      
      where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"
      
      # Get total count with filters
      count_sql = f"SELECT COUNT(*) FROM tbl_transaction t JOIN tbl_account a ON t.account = a.id WHERE {where_sql}"
      self.cursor.execute(count_sql, params)
      total = self.cursor.fetchone()[0]
      
      sort_map = {
         "date": "t.dateValue",
         "description": "t.description",
         "amount": "t.amount",
         "account": "a.name",
         "entries": "entries_count"
      }
      sort_column = sort_map.get(sort_by)
      sort_direction = "DESC" if (sort_dir or "").lower() != "asc" else "ASC"

      if sort_column:
         if sort_column == "t.dateValue":
            order_by = f"{sort_column} {sort_direction}, t.dateImport {sort_direction}"
         else:
            order_by = f"{sort_column} {sort_direction}, t.dateValue DESC, t.dateImport DESC"
      else:
         order_by = "t.dateValue DESC, t.dateImport DESC"

      # Get paginated data with filters
      sql = f"""
         SELECT 
            t.id,
            t.dateImport,
            t.dateValue,
            t.description,
            t.amount,
            t.iban,
            t.bic,
            t.recipientApplicant,
            a.id as account_id,
            a.name as account_name,
            a.iban_accountNumber,
            COALESCE(ec.entries_count, 0) as entries_count
         FROM tbl_transaction t
         JOIN tbl_account a ON t.account = a.id
         LEFT JOIN (
            SELECT transaction, COUNT(*) AS entries_count
            FROM tbl_accountingEntry
            GROUP BY transaction
         ) ec ON ec.transaction = t.id
         WHERE {where_sql}
         ORDER BY {order_by}
         LIMIT %s OFFSET %s
      """
      self.cursor.execute(sql, params + [page_size, offset])
      
      # Fetch all results first to avoid cursor conflicts
      rows = self.cursor.fetchall()
      
      transactions = []
      for row in rows:
         transaction = {
            "id": row[0],
            "dateImport": row[1],
            "dateValue": row[2],
            "description": row[3],
            "amount": row[4],
            "iban": row[5],
            "bic": row[6],
            "recipientApplicant": row[7],
            "account_id": row[8],
            "account_name": row[9],
            "account_iban": row[10],
            "entries": self._get_accounting_entries(row[0])
         }
         transactions.append(transaction)
      
      return {
         'transactions': transactions,
         'page': page,
         'page_size': page_size,
         'total': total
      }

   def get_transaction_by_id(self, transaction_id: int) -> dict | None:
      """
      Retrieve a single transaction with its accounting entries.
      
      Args:
         transaction_id: ID of the transaction
         
      Returns:
         Transaction dictionary or None if not found.
      """
      sql = """
         SELECT 
            t.id,
            t.dateImport,
            t.dateValue,
            t.description,
            t.amount,
            t.iban,
            t.bic,
            t.recipientApplicant,
            a.id as account_id,
            a.name as account_name,
            a.iban_accountNumber
         FROM tbl_transaction t
         JOIN tbl_account a ON t.account = a.id
         WHERE t.id = %s
      """
      self.cursor.execute(sql, (transaction_id,))
      row = self.cursor.fetchone()
      
      if not row:
         return None
         
      transaction = {
         "id": row[0],
         "dateImport": row[1],
         "dateValue": row[2],
         "description": row[3],
         "amount": row[4],
         "iban": row[5],
         "bic": row[6],
         "recipientApplicant": row[7],
         "account_id": row[8],
         "account_name": row[9],
         "account_iban": row[10],
         "entries": self._get_accounting_entries(row[0])
      }
      
      return transaction

   def _get_accounting_entries(self, transaction_id: int) -> list[dict]:
      """
      Retrieve accounting entries for a transaction.
      
      Args:
         transaction_id: ID of the transaction
         
      Returns:
         List of accounting entry dictionaries.
      """
      sql = """
         SELECT 
            ae.id,
            ae.dateImport,
            ae.checked,
            ae.amount,
            ae.accountingPlanned,
            ae.category,
            vcf.fullname as category_name
         FROM tbl_accountingEntry ae
         LEFT JOIN view_categoryFullname vcf ON ae.category = vcf.id
         WHERE ae.transaction = %s
         ORDER BY ae.dateImport DESC
      """
      self.cursor.execute(sql, (transaction_id,))
      
      # Fetch all results
      rows = self.cursor.fetchall()
      
      entries = []
      for row in rows:
         entry = {
            "id": row[0],
            "dateImport": row[1],
            "checked": row[2],
            "amount": row[3],
            "accountingPlanned": row[4],
            "category": row[5],
            "category_name": row[6]
         }
         entries.append(entry)
      
      return entries
