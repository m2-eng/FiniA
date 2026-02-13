#
# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (c) 2026 m2-eng
# Author: m2-eng
# Co-Author: GitHub Copilot
# License: GNU Affero General Public License v3.0 (AGPL-3.0-only)
# Purpose: Module for account data importer.
#
import csv
import re
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any
import warnings

import json
from services.csv_utils import read_csv_rows, parse_amount, parse_date, detect_csv_encoding
from services.field_extractor import extract_field_value
from infrastructure.unit_of_work import UnitOfWork
from repositories.account_import_repository import AccountImportRepository
from repositories.settings_repository import SettingsRepository

# Suppress MySQL duplicate entry warnings
warnings.filterwarnings("ignore", message=".*duplicate.*", category=UserWarning)

logger = logging.getLogger(__name__)


@dataclass
class ImportJob:
   account_id: int
   account_name: str
   path: Path
   format: str
   file_ending: str


class AccountDataImporter: # finding: Check design. Is it correct to handover the pool_manager
   def __init__(self, pool_manager, session_id: str):
      """
      Initializes the account data importer with the connection pool manager.
      
      Args:
         pool_manager: ConnectionPoolManager instance
         session_id: Session ID for the connection pool
      """
      self.pool_manager = pool_manager
      self.session_id = session_id
      self._settings_key = "import_format"

   def _load_all_formats(self) -> dict:
      """Load import formats from database settings table.
      
      Formats are always loaded fresh to ensure consistency with database state.
      """
      return self._load_formats_from_settings()

   def _load_formats_from_settings(self) -> dict:
      connection = None
      cursor = None
      try:
         connection = self.pool_manager.get_connection(self.session_id)
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
                  # Repair malformed configs (strings instead of objects)
                  config = self._repair_config(config)
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
         # Return connection to the pool (important!).
         if connection:
            try:
               connection.close()  # Back to pool
            except Exception:
               pass

   def _repair_config(self, config: dict) -> dict:
      """Repair malformed config where nested objects became strings.
      
      This handles backwards compatibility with database entries created by
      the old JavaScript YAML parser that sometimes converted nested objects to strings.
      New uploads use Python's yaml.safe_load() which handles nesting correctly.
      
      Note: This function can be removed once all database entries have been updated
            (estimated 3-6 months after Python parser deployment).
      """
      if not isinstance(config, dict):
         return config
      
      repairs_applied = False
      
      # Recursively repair all nested structures
      if "columns" in config and isinstance(config["columns"], dict):
         for col_name, col_config in config["columns"].items():
            if isinstance(col_config, dict):
               # Repair sources array
               if "sources" in col_config and isinstance(col_config["sources"], list):
                  repaired_sources = []
                  for item in col_config["sources"]:
                     if isinstance(item, str):
                        # Try to parse string as key:value pairs
                        try:
                           # String like "name: Details" -> {name: "Details"}
                           if ':' in item:
                              key, value = item.split(':', 1)
                              repaired_sources.append({key.strip(): value.strip()})
                              repairs_applied = True
                           else:
                              # Can't repair, keep as is
                              repaired_sources.append(item)
                        except Exception:
                           repaired_sources.append(item)
                     elif isinstance(item, dict):
                        repaired_sources.append(item)
                     else:
                        repaired_sources.append(item)
                  col_config["sources"] = repaired_sources
      
      if repairs_applied:
         logger.warning("Applied legacy config repairs (old JavaScript parser format detected)")
      
      return config

   def _get_mapping(self, format_name: str, csv_path: Path = None) -> tuple[dict, str]:
      """Get format mapping, optionally with automatic version detection.
      
      Args:
         format_name: Format name (e.g. 'csv-cb')
         csv_path: Optional path to CSV file for header-based version detection
      
      Returns:
         tuple: (mapping_config, detected_version)
      """
      formats = self._load_all_formats()
      if format_name not in formats:
         raise ValueError(
            f"Format '{format_name}' not found in settings. Available: {list(formats.keys())}"
         )
      
      format_config = formats[format_name]
      
      # Check if format has nested versions
      has_versions = any(k not in ['default'] and isinstance(v, dict) and 'encoding' in v 
                        for k, v in format_config.items())
      
      if not has_versions:
         # Legacy format without versions - return as-is
         return format_config, "legacy"
      
      # Format has versions - try to detect best match
      detected_version = None
      detection_method = None
      
      if csv_path and csv_path.exists():
         # Try automatic header detection
         detected_version = self._detect_format_version(format_name, format_config, csv_path)
         if detected_version:
            detection_method = "header-match"
      
      # Fallback to default version
      if not detected_version:
         detected_version = format_config.get('default', None)
         if detected_version:
            detection_method = "default"
            if csv_path:
               logger.warning(
                  f"No header match for '{format_name}', using default version '{detected_version}'"
               )
      
      # Fallback to first available version
      if not detected_version:
         versions = [k for k in format_config.keys() if k != 'default' and isinstance(format_config[k], dict)]
         if versions:
            detected_version = versions[0]
            detection_method = "first-available"
            logger.warning(
               f"No default for '{format_name}', using first available version '{detected_version}'"
            )
      
      if not detected_version or detected_version not in format_config:
         raise ValueError(
            f"No valid version found for format '{format_name}'. Available versions: {list(format_config.keys())}"
         )
      
      version_config = format_config[detected_version]
      
      # Log the config being used
      if logger.isEnabledFor(logging.DEBUG):
         logger.debug(
            f"Using config for '{format_name}' version '{detected_version}': "
            f"encoding={version_config.get('encoding')}, "
            f"delimiter={version_config.get('delimiter')}, "
            f"date_format={version_config.get('date_format')}, "
            f"header_columns={len(version_config.get('header', []))} cols"
         )
         
         # Detailed field mapping logging
         columns_cfg = version_config.get('columns', {})
         date_col_config = columns_cfg.get('dateValue', {})
         logger.debug(f"dateValue mapping: {date_col_config}")
         
         iban_col_config = columns_cfg.get('iban', {})
         if 'sources' in iban_col_config:
            sources = iban_col_config['sources']
            logger.debug(
               f"iban.sources: type={type(sources).__name__}, "
               f"count={len(sources) if isinstance(sources, list) else 0}"
            )
      
      return version_config, f"{detected_version} ({detection_method})"

   def _detect_format_version(self, format_name: str, format_config: dict, csv_path: Path) -> str | None:
      """Detect best matching format version based on CSV header columns.
      
      Uses flexible matching: all expected columns must be present in CSV header,
      but order and extra columns don't matter.
      
      Tries each version with its own encoding/delimiter to handle different formats.
      
      Args:
         format_name: Format name for logging
         format_config: Format configuration with versions
         csv_path: Path to CSV file
      
      Returns:
         Version key of best match, or None if no match found
      """
      versions = {k: v for k, v in format_config.items() 
                 if k != 'default' and isinstance(v, dict) and 'header' in v}
      
      if not versions:
         return None
      
      best_match = None
      best_score = 0
      
      # Try each version with its specific encoding/delimiter
      for version_key, version_config in versions.items():
         try:
            expected_headers = version_config.get('header', [])
            if not expected_headers:
               continue
            
            preferred_encoding = version_config.get('encoding', 'utf-8')
            delimiter = version_config.get('delimiter', ';')
            header_skip = version_config.get('header_skip', 0)
            
            # Detect actual encoding (with fallback like csv_utils does)
            try:
               actual_encoding = detect_csv_encoding(csv_path, preferred_encoding)
            except RuntimeError as enc_error:
               logger.debug(f"Version '{version_key}': Encoding detection failed - {enc_error}")
               continue
            
            # Read CSV header with detected encoding
            with open(csv_path, 'r', encoding=actual_encoding) as f:
               # Skip header lines if configured
               for _ in range(header_skip):
                  f.readline()
               
               # Read header row
               reader = csv.reader(f, delimiter=delimiter)
               csv_header = next(reader)
               csv_header_set = set(h.strip() for h in csv_header)
            
            expected_set = set(expected_headers)
            
            # Check if all expected columns are present (flexible matching)
            if expected_set.issubset(csv_header_set):
               # Calculate match score (more matching columns = better)
               score = len(expected_set)
               if score > best_score:
                  best_score = score
                  best_match = version_key
                  logger.debug(f"Version '{version_key}': {score}/{len(expected_set)} columns found")
         
         except Exception as e:
            # This version failed to parse - try next one
            logger.debug(f"Version '{version_key}': Error reading - {e}")
            continue
      
      if best_match:
         logger.info(f"Best match for '{format_name}': version '{best_match}' with {best_score} columns")
      else:
         logger.warning(f"No version found matching CSV columns for format '{format_name}'")
      
      return best_match

   def _get_field(self, row: dict[str, Any], mapping: dict, field_name: str = "") -> str:
      """Get field value from row using various extraction strategies.
      
      Note: Header validation happens BEFORE import, so we can safely extract values here.
      Delegates to extract_field_value() from field_extractor module.
      
      Returns:
         Extracted value as string (empty string if not found)
      """
      return extract_field_value(row, mapping)

   def _validate_csv_headers(self, csv_fieldnames: list[str], columns: dict, csv_filename: str) -> bool:
      """Validate that all required columns are present in CSV file.
      
      Required columns are those that are NOT null in the format config.
      Supports both new 'name' syntax and legacy 'names' syntax.
      
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
            # Single column name (new syntax)
            if "name" in field_config:
               name = field_config.get("name")
               field_found = name in csv_fieldnames
            # Legacy: Multiple names
            elif "names" in field_config:
               # Check if any of the alternative names exist
               for name in field_config.get("names", []):
                  if name in csv_fieldnames:
                     field_found = True
                     break
            # Regex extraction - source column(s) must exist
            elif "sources" in field_config:
               sources = field_config.get("sources", [])
               for source_config in sources:
                  if isinstance(source_config, dict):
                     source_name = source_config.get("name")
                     if source_name and source_name in csv_fieldnames:
                        field_found = True
                        break
            # Legacy regex extraction
            elif "regex" in field_config:
               source = field_config.get("source")
               if source and source in csv_fieldnames:
                  field_found = True
            # Join columns - check if source columns exist
            elif "join" in field_config:
               join_fields = field_config.get("join", [])
               if any(f in csv_fieldnames for f in join_fields):
                  field_found = True
         
         if not field_found:
            missing_fields.append(field_name)
      
      if missing_fields:
         # Log for system logs
         logger.error(
            f"Required columns not found in {csv_filename}: {', '.join(missing_fields)}"
         )
         
         # Print for user visibility (imports are often run in terminal)
         print(f"\n❌ FEHLER - Datei: {csv_filename}")
         print(f"   Erforderliche Spalten nicht gefunden:")
         for field in missing_fields:
            config = columns.get(field, {})
            if isinstance(config, dict):
               if "name" in config:
                  print(f"   - {field}: Erwartet Spalte '{config.get('name')}'")
               elif "names" in config:
                  names = config.get("names", [])
                  print(f"   - {field}: Erwartet eine dieser Spalten: {', '.join(names)}")
               elif "sources" in config:
                  sources = config.get("sources", [])
                  source_names = [s.get("name") for s in sources if isinstance(s, dict) and s.get("name")]
                  print(f"   - {field}: Erwartet eine dieser Quellspalten: {', '.join(source_names)}")
               elif "join" in config:
                  join_fields = config.get("join", [])
                  print(f"   - {field}: Erwartet mindestens eine dieser Spalten: {', '.join(join_fields)}")
               else:
                  print(f"   - {field}")
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
      
      # Get one connection for the entire import (not per row!).
      connection = None
      try:
         connection = self.pool_manager.get_connection(self.session_id)
      
         # Batch settings (opt-in via mapping, default 1000)
         batch_size = mapping.get("batch_size", 1000)
         try:
            batch_size = int(batch_size)
         except Exception:
            batch_size = 1000
         batch_size = max(100, min(batch_size, 5000))

         batch_rows: list[tuple] = []

         def flush_batch() -> None:
            nonlocal inserted
            if not batch_rows:
               return
            with UnitOfWork(connection) as uow:
               tx_repo = TransactionRepository(uow)
               inserted += tx_repo.insert_ignore_many(batch_rows)
            batch_rows.clear()

         # Validate CSV headers before processing
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
               date_value_raw = self._get_field(row, columns.get("dateValue"), "dateValue")
               
               # Debug logging for first few rows
               if total <= 3 and logger.isEnabledFor(logging.DEBUG):
                  logger.debug(
                     f"Row {total}: dateValue mapping={columns.get('dateValue')}, "
                     f"raw_value='{date_value_raw}', csv_keys={list(row.keys())[:5]}"
                  )
               
               amount_raw = self._get_field(row, columns.get("amount"), "amount")
               description = self._get_field(row, columns.get("description"), "description")
               iban = self._get_field(row, columns.get("iban"), "iban")
               bic = self._get_field(row, columns.get("bic"), "bic")
               recipient = self._get_field(row, columns.get("recipientApplicant"), "recipientApplicant")

               # Parse values using centralized utilities
               date_value = parse_date(date_value_raw, date_format)
               amount = parse_amount(amount_raw, decimal_sep)

               # Batch insert rows for better performance
               batch_rows.append(
                  (
                     iban,
                     bic,
                     description,
                     amount,
                     date_value,
                     recipient,
                     job.account_id,
                  )
               )
               if len(batch_rows) >= batch_size:
                  flush_batch()
            except Exception as exc:  # keep importing but report only relevant errors
               # Silently skip duplicate entries - they are expected and normal
               error_msg = str(exc).lower()
               if "duplicate" in error_msg or "unique" in error_msg:
                  # This is expected when importing duplicate data - don't print
                  pass
               else:
                  # Only print unexpected errors
                  print(f"  Warning: skipping row {total} in {csv_path.name}: {exc}")
      
         # Flush remaining rows
         flush_batch()

      except ValueError as e:
         # CSV has no header or is empty
         logger.error(f"CSV format error in {csv_path.name}: {str(e)}")
         print(f"\n❌ FEHLER - Datei: {csv_path.name}")
         print(f"   {str(e)}")
         print(f"   Import wird abgebrochen!\n")
         return 0, 0
      except RuntimeError as e:
         # Encoding detection failed
         logger.error(f"Encoding error in {csv_path.name}: {str(e)}")
         print(f"\n❌ FEHLER - Datei: {csv_path.name}")
         print(f"   {str(e)}")
         print(f"   Import wird abgebrochen!\n")
         return 0, 0
      finally:
         # Return connection to the pool (important!).
         if connection:
            try:
               connection.close()  # Back to pool
            except Exception:
               pass
      
      return inserted, total

   def _collect_jobs(self) -> list[ImportJob]:
      """
      Collects all jobs to import from the database.
      Uses the connection pool manager for database access.
      """
      connection = None
      try:
         connection = self.pool_manager.get_connection(self.session_id)
         with UnitOfWork(connection) as uow:
            repo = AccountImportRepository(uow)
            rows = repo.list_import_paths()
      finally:
         # Return connection to the pool (important!).
         if connection:
            try:
               connection.close()  # Back to pool
            except Exception:
               pass
      
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
      Imports account data from configured import paths.
      Uses the connection pool manager for database access.
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

         files = sorted(job.path.glob(f"*.{job.file_ending}"))
         if not files:
            print(f"No *.{job.file_ending} files found in {job.path} for account '{job.account_name}'")
            continue

         for csv_file in files:
            # Get mapping with version detection for this specific file
            try:
               mapping, detected_version = self._get_mapping(job.format, csv_file)
               logger.info(f"Format '{job.format}' - Detected version: {detected_version} for {csv_file.name}")
               print(f"\nℹ️  Format '{job.format}' - Erkannte Version: {detected_version} für {csv_file.name}")
            except Exception as exc:
               logger.error(f"Error loading format for {csv_file.name}: {exc}")
               print(f"\n❌ FEHLER beim Laden des Formats für {csv_file.name}: {exc}")
               continue
            
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
