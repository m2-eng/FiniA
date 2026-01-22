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

   def update(
      self,
      entry_id: int,
      amount: Decimal,
      checked: bool,
      accounting_planned_id: int | None = None,
      category_id: int | None = None,
   ) -> bool:
      """
      Update an existing accounting entry.
      
      Args:
         entry_id: ID of the entry to update
         amount: New transaction amount
         checked: Whether entry is verified
         accounting_planned_id: Optional reference to tbl_planning
         category_id: Optional reference to tbl_category
      
      Returns:
         True if update was successful, False otherwise
      """
      sql = """
         UPDATE tbl_accountingEntry
         SET amount = %s, checked = %s, accountingPlanned = %s, category = %s
         WHERE id = %s
      """
      self.cursor.execute(
         sql,
         (amount, checked, accounting_planned_id, category_id, entry_id)
      )
      return self.cursor.rowcount > 0

   def delete(self, entry_id: int) -> bool:
      """
      Delete an accounting entry.
      
      Args:
         entry_id: ID of the entry to delete
      
      Returns:
         True if deletion was successful, False otherwise
      """
      sql = "DELETE FROM tbl_accountingEntry WHERE id = %s"
      self.cursor.execute(sql, (entry_id,))
      return self.cursor.rowcount > 0

   def set_checked_for_transactions(self, transaction_ids: list[int], checked: bool) -> int:
      """
      Bulk set checked flag for all entries belonging to the given transaction IDs.

      Args:
         transaction_ids: List of transaction IDs
         checked: Desired checked state

      Returns:
         Number of rows updated
      """
      if not transaction_ids:
         return 0

      placeholders = ",".join(["%s"] * len(transaction_ids))
      sql = f"UPDATE tbl_accountingEntry SET checked = %s WHERE transaction IN ({placeholders})"
      params = [checked, *transaction_ids]
      self.cursor.execute(sql, params)
      return self.cursor.rowcount

   def get_all_by_transaction(self, transaction_id: int) -> list[dict]:
      """
      Get all accounting entries for a transaction.
      
      Args:
         transaction_id: Transaction ID
      
      Returns:
         List of accounting entries with category names
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
      columns = [desc[0] for desc in self.cursor.description]
      return [dict(zip(columns, row)) for row in self.cursor.fetchall()]
