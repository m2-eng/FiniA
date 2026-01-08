import csv
import re
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any
import warnings

import yaml

from Database import Database
from infrastructure.unit_of_work import UnitOfWork
from repositories.account_import_repository import AccountImportRepository
from repositories.transaction_repository import TransactionRepository
from repositories.accounting_entry_repository import AccountingEntryRepository

# Suppress MySQL duplicate entry warnings
warnings.filterwarnings("ignore", message=".*duplicate.*", category=UserWarning)


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

   def _get_field(self, row: dict[str, Any], mapping: dict, field_name: str = "") -> tuple[str, bool]:
      """Get field value from row using Strategy 1: Exact column names with priority fallbacks.
      
      Note: Header validation happens BEFORE import, so we can safely extract values here.
      
      Returns:
         tuple: (value, unused_flag) - Returns (value, False) always since headers are pre-validated
      """
      if mapping is None:
         return "", False
      
      if isinstance(mapping, str):
         # Legacy: Simple string mapping (direct column name)
         return (row.get(mapping, "") or "").strip(), False
      
      if isinstance(mapping, dict) and "join" in mapping:
         # Strategy: Join multiple columns
         separator = mapping.get("separator", " ")
         parts = [
            (row.get(item, "") or "").strip()
            for item in mapping.get("join", [])
            if (row.get(item, "") or "").strip()
         ]
         value = separator.join(parts)
         return value, False
      
      if isinstance(mapping, dict) and "regex" in mapping:
         # Strategy: Extract via regex from source column
         pattern = mapping.get("regex")
         target = mapping.get("source")
         value = row.get(target, "") or ""
         matches = re.findall(pattern, value)
         if not matches:
            return "", False
         # Join all capture groups or matches into one string
         def _flatten(m):
            if isinstance(m, tuple):
               return "".join(m)
            return m
         extracted = [ _flatten(m) for m in matches if _flatten(m) ]
         return " | ".join(extracted), False
      
      if isinstance(mapping, dict) and "names" in mapping:
         # Strategy 1: Exact column names with priority fallbacks
         names = mapping.get("names", [])
         for name in names:
            if name in row and (row.get(name) or "").strip():
               return (row.get(name, "") or "").strip(), False
         # Fallback: return empty string if no matching column found
         return "", False
      
      # Fallback for unmapped fields
      return "", False

   def _parse_amount(self, raw: str, decimal_sep: str) -> Decimal:
      normalized = raw.replace(" ", "")
      if decimal_sep == ",":
         normalized = normalized.replace(".", "").replace(",", ".")
      return Decimal(normalized)

   def _parse_date(self, raw: str, date_format: str) -> datetime:
      return datetime.strptime(raw, date_format)

   def _validate_csv_headers(self, csv_fieldnames: list[str], columns: dict, csv_filename: str) -> bool:
      """Validate that all required columns are present in CSV file.
      
      Required columns are those that are NOT null in the format config.
      
      Args:
         csv_fieldnames: List of column names from CSV header
         columns: Column mapping configuration
         csv_filename: Name of CSV file (for error messages)
      
      Returns:
         True if all required columns found, False if validation failed
      """
      csv_fieldnames_lower = [f.lower() for f in csv_fieldnames]
      missing_fields = []
      
      for field_name, field_config in columns.items():
         # Skip null/None fields - they are optional
         if field_config is None:
            continue
         
         # Check if this field can be found in CSV
         field_found = False
         
         if isinstance(field_config, str):
            # Simple string mapping
            field_found = field_config in csv_fieldnames
         elif isinstance(field_config, dict):
            if "names" in field_config:
               # Check if any of the alternative names exist
               for name in field_config.get("names", []):
                  if name in csv_fieldnames:
                     field_found = True
                     break
            elif "regex" in field_config:
               # Regex extraction - source column must exist
               source = field_config.get("source")
               if source and source in csv_fieldnames:
                  field_found = True
            elif "join" in field_config:
               # Join columns - check if source columns exist
               join_fields = field_config.get("join", [])
               if any(f in csv_fieldnames for f in join_fields):
                  field_found = True
         
         if not field_found:
            missing_fields.append(field_name)
      
      if missing_fields:
         print(f"\n❌ FEHLER - Datei: {csv_filename}")
         print(f"   Erforderliche Spalten nicht gefunden:")
         for field in missing_fields:
            config = columns.get(field, {})
            if isinstance(config, dict) and "names" in config:
               names = config.get("names", [])
               print(f"   - {field}: Erwartet eine dieser Spalten: {', '.join(names)}")
            else:
               print(f"   - {field}")
         print(f"\n   Verfügbare Spalten in der CSV-Datei ({len(csv_fieldnames)}):")
         for fname in csv_fieldnames:
            print(f"   - {fname}")
         print(f"\n   Import für diese Datei wird abgebrochen!\n")
         return False
      
      return True

   def _import_file(self, csv_path: Path, mapping: dict, job: ImportJob, tx_repo: TransactionRepository, ae_repo: AccountingEntryRepository) -> tuple[int, int]:
      delimiter = mapping.get("delimiter", ";")
      encoding = mapping.get("encoding", "utf-8")
      decimal_sep = mapping.get("decimal", ".")
      date_format = mapping.get("date_format")
      columns = mapping.get("columns", {})

      inserted = 0
      total = 0

      # Try multiple encodings to handle different CSV formats from banks
      encodings_to_try = [encoding]
      if encoding.lower() == "utf-8":
         # Common fallback encodings for German bank exports
         encodings_to_try.extend(["latin-1", "iso-8859-1", "cp1252"])
      
      detected_encoding = None
      last_error = None
      
      # Detect the correct encoding by trying to read the file
      for enc in encodings_to_try:
         try:
            with open(csv_path, "r", encoding=enc, newline="") as test_handle:
               # Try to read the entire content to verify encoding
               test_handle.read(4096)
            detected_encoding = enc
            break
         except (UnicodeDecodeError, Exception) as e:
            last_error = e
            continue
      
      if detected_encoding is None:
         raise RuntimeError(f"Could not detect encoding for {csv_path.name}. Tried: {encodings_to_try}. Last error: {last_error}")
      
      with open(csv_path, "r", encoding=detected_encoding, newline="") as handle:
         reader = csv.DictReader(handle, delimiter=delimiter)
         
         # Validate CSV headers BEFORE processing
         if reader.fieldnames is None:
            print(f"\n❌ FEHLER - Datei: {csv_path.name}")
            print(f"   CSV-Datei hat keine Header-Zeile oder ist leer!")
            print(f"   Import wird abgebrochen!\n")
            return 0, 0
         
         # Check if all required columns are present
         if not self._validate_csv_headers(reader.fieldnames, columns, csv_path.name):
            return 0, 0  # Validation failed, abort import
         
         print(f"✓ CSV-Spalten validiert: {csv_path.name}")
         
         for row in reader:
            total += 1
            try:
               # Get field values (no need to check for missing required columns anymore)
               date_value_raw, _ = self._get_field(row, columns.get("dateValue"), "dateValue")
               amount_raw, _ = self._get_field(row, columns.get("amount"), "amount")
               description, _ = self._get_field(row, columns.get("description"), "description")
               iban, _ = self._get_field(row, columns.get("iban"), "iban")
               bic, _ = self._get_field(row, columns.get("bic"), "bic")
               recipient, _ = self._get_field(row, columns.get("recipientApplicant"), "recipientApplicant")

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
               
               if isinstance(transaction_id, int) and transaction_id > 0:
                  # Automatically create accounting entry for new transaction
                  # Always create exactly one accounting entry per new transaction
                  ae_repo.insert(
                     amount=amount,
                     transaction_id=transaction_id,
                     checked=False,
                     accounting_planned_id=None,
                     category_id=None,
                  )
                  inserted += 1
            except Exception as exc:  # keep importing but report only relevant errors
               # Silently skip duplicate entries - they are expected and normal
               error_msg = str(exc).lower()
               if "duplicate" in error_msg or "unique" in error_msg:
                  # This is expected when importing duplicate data - don't print
                  pass
               else:
                  # Only print unexpected errors
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
