#
# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (c) 2026 m2-eng
# Author: m2-eng
# Co-Author: GitHub Copilot
# License: GNU Affero General Public License v3.0 (AGPL-3.0-only)
# Purpose: Module for account types.
#
from services.import_steps.base import ImportStep
from repositories.account_type_repository import AccountTypeRepository


class AccountTypesStep(ImportStep):
   def name(self) -> str:
      return "account_types"

   def run(self, data: dict, uow) -> bool:
      if not data or "accountType" not in data:
         print("  No accountType data found in YAML")
         return True
      repo = AccountTypeRepository(uow)
      inserted = 0
      for type_name, type_id in data["accountType"].items():
         repo.insert_ignore(type_id, type_name)
         inserted += 1
      print(f"  Inserted {inserted} account types into tbl_accountType") # finding: USe 'logging' instead of 'print' for better log management.
      return True
