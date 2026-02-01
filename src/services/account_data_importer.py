import csv
import re
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any
import warnings

import json
from services.csv_utils import read_csv_rows, parse_amount, parse_date
from infrastructure.unit_of_work import UnitOfWork
from repositories.account_import_repository import AccountImportRepository
from repositories.transaction_repository import TransactionRepository
from repositories.settings_repository import SettingsRepository

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
   def __init__(self, pool_manager, session_id: str):
      """
      Initialisiert den Account Data Importer mit Connection Pool Manager.
      
      Args:
         pool_manager: ConnectionPoolManager Instanz
         session_id: Session-ID für den Connection Pool
      """
      self.pool_manager = pool_manager
      self.session_id = session_id
      self._formats_cache = None
      self._settings_key = "import_format"

   def _load_all_formats(self) -> dict:
      if self._formats_cache is not None:
         return self._formats_cache
      # Load import formats from settings table
      formats = self._load_formats_from_settings()
      self._formats_cache = formats
      return self._formats_cache

   def _load_formats_from_settings(self) -> dict:
      connection = self.pool_manager.get_connection(self.session_id)
      cursor = None
      try:
         cursor = connection.cursor(buffered=True)
         repo = SettingsRepository(cursor)
         entries = repo.get_setting_entries(self._settings_key)
         formats: dict = {}
         for entry in entries:
            try:
               data = json.loads(entry.get("value") or "{}")
               name = data.get("name")
               config = data.get("config")
               if name and isinstance(config, dict):
                  formats[name] = config
            except Exception:
               continue
         return formats
      finally:
         if cursor:
            try:
               cursor.close()
            except Exception:
               pass

   def _load_formats_from_yaml(self) -> dict:
      """Deprecated: Import formats are now loaded only from database settings table."""
      raise NotImplementedError(
         "Import formats must be stored in the database settings table. "
         "Use the Settings API to manage formats (POST/PUT/DELETE /settings/import-formats)"
      )

   def _seed_settings_with_formats(self, formats: dict) -> None:
      """Deprecated: Auto-seeding from YAML is no longer supported."""
      pass

   def _get_mapping(self, format_name: str) -> dict:
      formats = self._load_all_formats()
      if format_name not in formats:
         raise ValueError(
            f"Format '{format_name}' not found in settings. Available: {list(formats.keys())}"
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

   def _import_file(self, csv_path: Path, mapping: dict, job: ImportJob) -> tuple[int, int]:
      """
      Import a single CSV file for an account job.
      
      Each row is committed immediately to ensure insert_ignore() duplicate detection works correctly.
      Accounting entries are automatically created by database trigger (trg_transaction_create_accounting_entry).
      
      Args:
         csv_path: Path to the CSV file
         mapping: Format mapping configuration
         job: ImportJob with account and path information
      
      Returns:
         Tuple of (inserted_count, total_rows)
      """
      from repositories.transaction_repository import TransactionRepository
      
      delimiter = mapping.get("delimiter", ";")
      encoding = mapping.get("encoding", "utf-8")
      decimal_sep = mapping.get("decimal", ".")
      date_format = mapping.get("date_format")
      columns = mapping.get("columns", {})

      inserted = 0
      total = 0
      
      # Validate CSV headers before processing
      try:
         # Peek at first row to get fieldnames for validation
         first_pass = True
         for row in read_csv_rows(csv_path, delimiter=delimiter, encoding=encoding):
            if first_pass:
               # Get fieldnames from first iteration
               # (read_csv_rows already normalized them)
               fieldnames = list(row.keys())
               
               # Validate headers
               if not self._validate_csv_headers(fieldnames, columns, csv_path.name):
                  return 0, 0  # Validation failed, abort import
               
               print(f"✓ CSV-Spalten validiert: {csv_path.name}")
               first_pass = False
            
            total += 1
            try:
               # Get field values (headers already validated)
               date_value_raw, _ = self._get_field(row, columns.get("dateValue"), "dateValue")
               amount_raw, _ = self._get_field(row, columns.get("amount"), "amount")
               description, _ = self._get_field(row, columns.get("description"), "description")
               iban, _ = self._get_field(row, columns.get("iban"), "iban")
               bic, _ = self._get_field(row, columns.get("bic"), "bic")
               recipient, _ = self._get_field(row, columns.get("recipientApplicant"), "recipientApplicant")

               # Parse values using centralized utilities
               date_value = parse_date(date_value_raw, date_format)
               amount = parse_amount(amount_raw, decimal_sep)

               # IMPORTANT: Commit each row immediately to ensure insert_ignore() duplicate detection works
               # This prevents duplicate accounting entries from being created
               connection = self.pool_manager.get_connection(self.session_id)
               with UnitOfWork(connection) as uow:
                  tx_repo = TransactionRepository(uow)
                  
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
                     # Accounting entry is automatically created by database trigger
                     # trg_transaction_create_accounting_entry - NO manual insert needed
                     inserted += 1
                  # UnitOfWork.__exit__() commits automatically
            except Exception as exc:  # keep importing but report only relevant errors
               # Silently skip duplicate entries - they are expected and normal
               error_msg = str(exc).lower()
               if "duplicate" in error_msg or "unique" in error_msg:
                  # This is expected when importing duplicate data - don't print
                  pass
               else:
                  # Only print unexpected errors
                  print(f"  Warning: skipping row {total} in {csv_path.name}: {exc}")
      
      except ValueError as e:
         # CSV has no header or is empty
         print(f"\n❌ FEHLER - Datei: {csv_path.name}")
         print(f"   {str(e)}")
         print(f"   Import wird abgebrochen!\n")
         return 0, 0
      except RuntimeError as e:
         # Encoding detection failed
         print(f"\n❌ FEHLER - Datei: {csv_path.name}")
         print(f"   {str(e)}")
         print(f"   Import wird abgebrochen!\n")
         return 0, 0
      
      return inserted, total

   def _collect_jobs(self) -> list[ImportJob]:
      """
      Sammelt alle zu importierenden Jobs aus der Datenbank.
      Nutzt Connection Pool Manager für Datenbankzugriff.
      """
      connection = self.pool_manager.get_connection(self.session_id)
      with UnitOfWork(connection) as uow:
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
      """
      Importiert Account-Daten aus konfigurierten Import-Pfaden.
      Nutzt Connection Pool Manager für Datenbankzugriff.
      """
      print("\n" + "=" * 100)
      print("FiniA Account CSV Import")
      print("=" * 100 + "\n")

      jobs = self._collect_jobs()
      if not jobs:
         print("No account import paths configured. Add entries to tbl_accountImportPath first.")
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
            inserted, total = self._import_file(csv_file, mapping, job)
            overall_inserted += inserted
            overall_total += total
            print(
               f"Imported {inserted}/{total} rows from {csv_file.name} for account '{job.account_name}'"
            )

      print("\n" + "=" * 100)
      print(f"Finished CSV import. Inserted {overall_inserted} of {overall_total} rows")
      print("=" * 100 + "\n")
      return True
