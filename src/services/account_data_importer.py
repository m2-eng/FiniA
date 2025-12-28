import csv
import re
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import yaml

from Database import Database
from infrastructure.unit_of_work import UnitOfWork
from repositories.account_import_repository import AccountImportRepository
from repositories.transaction_repository import TransactionRepository
from repositories.accounting_entry_repository import AccountingEntryRepository


@dataclass
class ImportJob:
   account_id: int
   account_name: str
   path: Path
   format: str
   file_ending: str


class AccountDataImporter:
   def __init__(self, db: Database):
      self.db = db
      self._formats_cache = None

   def _load_all_formats(self) -> dict:
      if self._formats_cache is not None:
         return self._formats_cache

      repo_root = Path(__file__).resolve().parents[2]
      formats_file = repo_root / "cfg" / "import_formats.yaml"
      if not formats_file.exists():
         raise FileNotFoundError(f"Import formats file not found: {formats_file}")

      with open(formats_file, "r", encoding="utf-8") as f:
         data = yaml.safe_load(f) or {}

      self._formats_cache = data.get("formats", {})
      return self._formats_cache

   def _get_mapping(self, format_name: str) -> dict:
      formats = self._load_all_formats()
      if format_name not in formats:
         raise ValueError(
            f"Format '{format_name}' not found in import_formats.yaml. Available: {list(formats.keys())}"
         )
      return formats[format_name]

   def _get_field(self, row: dict[str, Any], mapping: dict) -> str:
      if isinstance(mapping, str):
         return (row.get(mapping, "") or "").strip()
      if isinstance(mapping, dict) and "join" in mapping:
         separator = mapping.get("separator", " ")
         parts = [
            (row.get(item, "") or "").strip()
            for item in mapping.get("join", [])
            if (row.get(item, "") or "").strip()
         ]
         return separator.join(parts)
      if isinstance(mapping, dict) and "regex" in mapping:
         pattern = mapping.get("regex")
         target = mapping.get("source")
         value = row.get(target, "") or ""
         matches = re.findall(pattern, value)
         if not matches:
            return ""
         # Join all capture groups or matches into one string
         def _flatten(m):
            if isinstance(m, tuple):
               return "".join(m)
            return m
         extracted = [ _flatten(m) for m in matches if _flatten(m) ]
         return " | ".join(extracted)
      return ""

   def _parse_amount(self, raw: str, decimal_sep: str) -> Decimal:
      normalized = raw.replace(" ", "")
      if decimal_sep == ",":
         normalized = normalized.replace(".", "").replace(",", ".")
      return Decimal(normalized)

   def _parse_date(self, raw: str, date_format: str) -> datetime:
      return datetime.strptime(raw, date_format)

   def _import_file(self, csv_path: Path, mapping: dict, job: ImportJob, tx_repo: TransactionRepository, ae_repo: AccountingEntryRepository) -> tuple[int, int]:
      delimiter = mapping.get("delimiter", ";")
      encoding = mapping.get("encoding", "utf-8")
      decimal_sep = mapping.get("decimal", ".")
      date_format = mapping.get("date_format")
      columns = mapping.get("columns", {})

      inserted = 0
      total = 0

      with open(csv_path, "r", encoding=encoding, newline="") as handle:
         reader = csv.DictReader(handle, delimiter=delimiter)
         for row in reader:
            total += 1
            try:
               date_value_raw = self._get_field(row, columns.get("dateValue"))
               amount_raw = self._get_field(row, columns.get("amount"))
               description = self._get_field(row, columns.get("description"))
               iban = self._get_field(row, columns.get("iban")) or None
               bic = self._get_field(row, columns.get("bic")) or None
               recipient = self._get_field(row, columns.get("recipientApplicant")) or None

               date_value = self._parse_date(date_value_raw, date_format)
               amount = self._parse_amount(amount_raw, decimal_sep)

               transaction_id = tx_repo.insert_ignore(
                  account_id=job.account_id,
                  description=description,
                  amount=amount,
                  date_value=date_value,
                  iban=iban,
                  bic=bic,
                  recipient_applicant=recipient,
               )
               
               if transaction_id:
                  # Automatically create accounting entry for new transaction
                  ae_repo.insert(
                     amount=amount,
                     transaction_id=transaction_id,
                     checked=False,
                     accounting_planned_id=None,
                     category_id=None,
                  )
                  inserted += 1
            except Exception as exc:  # keep importing but report
               print(f"  Warning: skipping row {total} in {csv_path.name}: {exc}")
      return inserted, total

   def _collect_jobs(self) -> list[ImportJob]:
      with UnitOfWork(self.db.connection) as uow:
         repo = AccountImportRepository(uow)
         rows = repo.list_import_paths()
      jobs = []
      
      # Get project root directory (2 levels up from this file: services -> src -> root)
      project_root = Path(__file__).resolve().parents[2]
      
      for row in rows:
         path_str = row["path"]
         path = Path(path_str)
         
         # If path is relative, resolve it from project root
         if not path.is_absolute():
            path = (project_root / path).resolve()
         else:
            path = path.resolve()
         
         jobs.append(
            ImportJob(
               account_id=row["account_id"],
               account_name=row["account_name"],
               path=path,
               format=row["format"],
               file_ending=row["file_ending"],
            )
         )
      return jobs

   def import_account_data(self) -> bool:
      print("\n" + "=" * 100)
      print("FiniA Account CSV Import")
      print("=" * 100 + "\n")

      self.db.close()
      if not self.db.connect(use_database=True):
         raise RuntimeError("Failed to connect to MySQL database")

      jobs = self._collect_jobs()
      if not jobs:
         print("No account import paths configured. Add entries to tbl_accountImportPath first.")
         self.db.close()
         return True

      overall_inserted = 0
      overall_total = 0

      for job in jobs:
         if not job.path.exists():
            print(f"Skipping account '{job.account_name}': folder not found {job.path}")
            continue
         try:
            mapping = self._get_mapping(job.format)
         except Exception as exc:
            print(f"Skipping account '{job.account_name}' ({job.format}): {exc}")
            continue

         files = sorted(job.path.glob(f"*.{job.file_ending}"))
         if not files:
            print(f"No *.{job.file_ending} files found in {job.path} for account '{job.account_name}'")
            continue

         for csv_file in files:
            with UnitOfWork(self.db.connection) as uow:
               tx_repo = TransactionRepository(uow)
               ae_repo = AccountingEntryRepository(uow)
               inserted, total = self._import_file(csv_file, mapping, job, tx_repo, ae_repo)
               overall_inserted += inserted
               overall_total += total
               print(
                  f"Imported {inserted}/{total} rows from {csv_file.name} for account '{job.account_name}'"
               )

      self.db.close()

      print("\n" + "=" * 100)
      print(f"Finished CSV import. Inserted {overall_inserted} of {overall_total} rows")
      print("=" * 100 + "\n")
      return True
