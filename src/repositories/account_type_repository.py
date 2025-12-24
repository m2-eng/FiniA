from repositories.base import BaseRepository


class AccountTypeRepository(BaseRepository):
   def insert_ignore(self, type_id: int, type_name: str) -> None:
      sql = "INSERT IGNORE INTO tbl_accountType (id, type, dateImport) VALUES (%s, %s, NOW())"
      self.cursor.execute(sql, (type_id, type_name))
