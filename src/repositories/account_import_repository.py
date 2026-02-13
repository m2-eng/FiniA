#
# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (c) 2026 m2-eng
# Author: m2-eng
# Co-Author: GitHub Copilot
# License: GNU Affero General Public License v3.0 (AGPL-3.0-only)
# Purpose: Module for account import repository.
#
from repositories.base import BaseRepository


class AccountImportRepository(BaseRepository):
   def get_format_id(self, type_name: str) -> int | None:
      self.cursor.execute(
         "SELECT id FROM tbl_accountImportFormat WHERE type = %s",
         (type_name,),
      )
      row = self.cursor.fetchone()
      return row[0] if row else None

   def ensure_format(self, type_name: str, file_ending: str) -> int | None:
      fmt_id = self.get_format_id(type_name)
      if fmt_id:
         return fmt_id
      self.cursor.execute(
         "INSERT IGNORE INTO tbl_accountImportFormat (type, fileEnding, dateImport) VALUES (%s, %s, NOW())",
         (type_name, file_ending),
      )
      return self.get_format_id(type_name)

   def insert_path(self, path: str, account_id: int, format_id: int) -> None:
      self.cursor.execute(
         """
         INSERT IGNORE INTO tbl_accountImportPath (path, account, importFormat, dateImport)
         VALUES (%s, %s, %s, NOW())
         """,
         (path, account_id, format_id),
      )

   def list_import_paths(self) -> list[dict[str, object]]:
      self.cursor.execute(
         """
         SELECT p.path, p.account, f.type, f.fileEnding, a.name
         FROM tbl_accountImportPath p
         JOIN tbl_accountImportFormat f ON p.importFormat = f.id
         JOIN tbl_account a ON p.account = a.id
         """
      )
      return [
         {
            "path": row[0],
            "account_id": row[1],
            "format": row[2],
            "file_ending": row[3],
            "account_name": row[4],
         }
         for row in self.cursor.fetchall()
      ]
