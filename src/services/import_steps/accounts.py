#
# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (c) 2026 m2-eng
# Author: m2-eng
# Co-Author: GitHub Copilot
# License: GNU Affero General Public License v3.0 (AGPL-3.0-only)
# Purpose: Module for accounts.
#
from services.import_steps.base import ImportStep
from domain.account import Account
from repositories.account_repository import AccountRepository
from repositories.account_import_repository import AccountImportRepository


class AccountsStep(ImportStep):
   def name(self) -> str:
      return "accounts"

   def run(self, data: dict, uow) -> bool:
      if "account_data" not in data:
         return True

      repo = AccountRepository(uow)
      import_repo = AccountImportRepository(uow)
      inserted = 0
      paths_inserted = 0

      # First pass: create accounts
      accounts = data["account_data"]
      for item in accounts:
         acc = item.get("account", {})
         account = Account(
            name=acc.get("name", ""),
            iban_accountNumber=acc.get("iban_accountNumber", ""),
            bic_market=acc.get("bic_market", ""),
            startAmount=acc.get("startAmount", 0.0),
            dateStart=acc.get("dateStart"),
            dateEnd=acc.get("dateEnd"),
            type_name=acc.get("type", ""),
            clearingAccount=acc.get("clearingAccount"),
         )
         repo.insert(account)
         inserted += 1

         # Persist import format and path if provided
         folder = acc.get("importFolder")
         file_ending = acc.get("importFileEnding")
         import_type = acc.get("importType")
         if file_ending and import_type:
            acc_id = repo.get_id_by_name(account.name)
            fmt_id = import_repo.ensure_format(import_type, file_ending)
            if folder and acc_id and fmt_id:
               import_repo.insert_path(folder, acc_id, fmt_id)
               paths_inserted += 1

      print(f"  Inserted {inserted} accounts into tbl_account")
      if paths_inserted:
         print(f"  Inserted {paths_inserted} import paths/formats")
      # Second pass: set clearing accounts
      updated = 0
      for item in accounts:
         acc = item.get("account", {})
         if acc.get("clearingAccount"):
            repo.update_clearing_account(acc.get("name", ""), acc["clearingAccount"])
            updated += 1

      print(f"  Updated {updated} accounts with clearing account references")
      return True