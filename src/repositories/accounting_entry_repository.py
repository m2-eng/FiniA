from decimal import Decimal
from repositories.base import BaseRepository


class AccountingEntryRepository(BaseRepository):
   def insert(
      self,
      amount: Decimal,
      transaction_id: int,
      checked: bool = False,
      accounting_planned_id: int | None = None,
      category_id: int | None = None,
   ) -> int | None:
      """
      Insert an accounting entry for a transaction.
      
      Args:
         amount: Transaction amount
         transaction_id: Reference to tbl_transaction
         checked: Whether entry is verified (default: False)
         accounting_planned_id: Optional reference to tbl_planning
         category_id: Optional reference to tbl_category
      
      Returns:
         ID of inserted row or None on failure
      """
      sql = """
         INSERT INTO tbl_accountingEntry
         (dateImport, checked, amount, transaction, accountingPlanned, category)
         VALUES (NOW(), %s, %s, %s, %s, %s)
      """
      self.cursor.execute(
         sql,
         (checked, amount, transaction_id, accounting_planned_id, category_id)
      )
      return self.cursor.lastrowid if self.cursor.rowcount > 0 else None
