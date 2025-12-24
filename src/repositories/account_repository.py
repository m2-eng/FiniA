from repositories.base import BaseRepository
from domain.account import Account


class AccountRepository(BaseRepository):
   def get_type_id(self, type_name: str) -> int:
      self.cursor.execute("SELECT id FROM tbl_accountType WHERE type = %s", (type_name,))
      row = self.cursor.fetchone()
      return row[0] if row else 1

   def get_id_by_name(self, name: str):
      self.cursor.execute("SELECT id FROM tbl_account WHERE name = %s", (name,))
      row = self.cursor.fetchone()
      return row[0] if row else None

   def insert(self, account: Account) -> None:
      acc_id = self.get_id_by_name(account.name)
      if acc_id:
         print(f"  Info: Account '{account.name}' already exists. Skipping insertion.")
         return  # Account already exists
      
      type_id = self.get_type_id(account.type_name)
      sql = (
         """INSERT INTO tbl_account
            (name, iban_accountNumber, bic_market, startAmount, dateStart, dateEnd, type, dateImport)
            VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())"""
      )
      self.cursor.execute(
         sql,
         (
            account.name,
            account.iban_accountNumber,
            account.bic_market,
            account.startAmount,
            account.dateStart,
            account.dateEnd,
            type_id,
         ),
      )

   def update_clearing_account(self, name: str, clearing_name: str) -> None:
      acc_id = self.get_id_by_name(name)
      clear_id = self.get_id_by_name(clearing_name)
      if acc_id and clear_id:
         self.cursor.execute(
            "UPDATE tbl_account SET clearingAccount = %s WHERE id = %s",
            (clear_id, acc_id),
         )
