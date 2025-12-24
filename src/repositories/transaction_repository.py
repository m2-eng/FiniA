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
