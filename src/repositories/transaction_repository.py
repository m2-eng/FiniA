from datetime import datetime
from decimal import Decimal

from repositories.base import BaseRepository


class TransactionRepository(BaseRepository):
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
      Retrieve all transactions with their accounting entries.
      
      Returns:
         List of transaction dictionaries with accounting entries and account info.
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
         ORDER BY t.dateValue DESC, t.dateImport DESC
      """
      self.cursor.execute(sql)
      
      transactions = []
      for row in self.cursor.fetchall():
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
      
      return transactions

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
            c.name as category_name
         FROM tbl_accountingEntry ae
         LEFT JOIN tbl_category c ON ae.category = c.id
         WHERE ae.transaction = %s
         ORDER BY ae.dateImport DESC
      """
      self.cursor.execute(sql, (transaction_id,))
      
      entries = []
      for row in self.cursor.fetchall():
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
