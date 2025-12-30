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
      Insert transaction with INSERT IGNORE for duplicate detection.
      
      Returns:
         Transaction ID if newly inserted, None if duplicate or failure.
      """
      sql = (
         """INSERT IGNORE INTO tbl_transaction
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

   def get_all_transactions(self) -> list[dict]:
      """
      Retrieve all transactions with their accounting entries (legacy: returns all).
      
      Returns:
         List of transaction dictionaries with accounting entries and account info.
      """
      return self.get_all_transactions_paginated(page=1, page_size=1000000)['transactions']

   def get_all_transactions_paginated(self, page: int = 1, page_size: int = 100) -> dict:
      """
      Retrieve paginated transactions with their accounting entries.
      
      Args:
         page: Page number (1-based)
         page_size: Number of records per page (max 1000)

      Returns:
         Dict with 'transactions' list, 'page', 'page_size', and 'total' count
      """
      page = max(1, page)
      page_size = min(max(1, page_size), 1000)
      offset = (page - 1) * page_size
      
      # Get total count
      count_sql = "SELECT COUNT(*) FROM tbl_transaction"
      self.cursor.execute(count_sql)
      total = self.cursor.fetchone()[0]
      
      # Get paginated data
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
         ORDER BY t.dateValue DESC, t.dateImport DESC
         LIMIT %s OFFSET %s
      """
      self.cursor.execute(sql, (page_size, offset))
      
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
