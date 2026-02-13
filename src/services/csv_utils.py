#
# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (c) 2026 m2-eng
# Author: m2-eng
# Co-Author: GitHub Copilot
# License: GNU Affero General Public License v3.0 (AGPL-3.0-only)
# Purpose: CSV Import Utility Functions
#
"""
CSV Import Utility Functions

Central helpers for CSV processing during transaction imports.
Avoids code duplication across import implementations.
"""

import csv
import re
from pathlib import Path
from decimal import Decimal
from datetime import datetime
from typing import Iterator


def detect_csv_encoding(csv_path: Path, preferred_encoding: str = "utf-8") -> str:
    """
    Detects CSV encoding by trying multiple encodings.
    
    Args:
        csv_path: Path to the CSV file
        preferred_encoding: Preferred encoding (tried first)
    
    Returns:
        Detected encoding
    
    Raises:
        RuntimeError: If no suitable encoding is found
    """
    encodings_to_try = [preferred_encoding]
    if preferred_encoding.lower() == "utf-8":
        # Common fallback encodings for German bank exports
        encodings_to_try.extend(["latin-1", "iso-8859-1", "cp1252"])
    
    last_error = None
    
    for encoding in encodings_to_try:
        try:
            with open(csv_path, "r", encoding=encoding, newline="") as test_handle:
                # Read the first chunk to verify the encoding
                test_handle.read(4096)
            return encoding
        except (UnicodeDecodeError, Exception) as e:
            last_error = e
            continue
    
    raise RuntimeError(
        f"Could not detect encoding for {csv_path.name}. "
        f"Tried: {encodings_to_try}. Last error: {last_error}"
    )


def read_csv_rows(
    csv_path: Path,
    delimiter: str = ";",
    encoding: str = "utf-8"
) -> Iterator[dict]:
    """
    Reads the CSV file and returns normalized rows.
    
    - Automatically detects the correct encoding
    - Normalizes headers (trims whitespace)
    - Yields an iterator of row dictionaries
    
    Args:
        csv_path: Path to the CSV file
        delimiter: CSV delimiter
        encoding: Preferred encoding
    
    Yields:
        Dict with column names as keys and cell values as values
    
    Raises:
        ValueError: If the CSV has no header row
        RuntimeError: If encoding cannot be detected
    """
    detected_encoding = detect_csv_encoding(csv_path, encoding)
    
    with open(csv_path, "r", encoding=detected_encoding, newline="") as handle:
        reader = csv.DictReader(handle, delimiter=delimiter)
        
        if reader.fieldnames is None:
            raise ValueError(f"CSV file {csv_path.name} has no header row or is empty")
        
        # Normalize header names: trim whitespace
        # Prevent issues like 'Amount ' != 'Amount'
        reader.fieldnames = [
            fieldname.strip() if isinstance(fieldname, str) else fieldname
            for fieldname in reader.fieldnames
        ]
        
        yield from reader


def parse_amount(raw: str, decimal_separator: str = ".") -> Decimal:
    """
    Parses an amount string into Decimal.
    
    Handles various whitespace characters and thousands separators.
    
    Args:
        raw: Amount as string (e.g. "1.234,56" or "1234.56")
        decimal_separator: Decimal separator ("," or ".")
    
    Returns:
        Amount as Decimal
    
    Examples:
        >>> parse_amount("1.234,56", ",")
        Decimal('1234.56')
        >>> parse_amount("1,234.56", ".")
        Decimal('1234.56')
    """
    if raw is None:
        raw = ""
    
    # Remove all whitespace characters, including non-breaking and narrow no-break spaces
    normalized = re.sub(r"[\s\u00A0\u202F]", "", str(raw))
    
    if decimal_separator == ",":
        # Remove thousands separators and convert comma to dot
        normalized = normalized.replace(".", "").replace(",", ".")
    
    return Decimal(normalized)


def parse_date(raw: str, date_format: str) -> datetime:
    """
    Parses a date string to datetime.
    
    Args:
        raw: Date as string
        date_format: Python strptime format string (e.g. "%d.%m.%Y")
    
    Returns:
        Parsed datetime
    
    Examples:
        >>> parse_date("31.12.2023", "%d.%m.%Y")
        datetime.datetime(2023, 12, 31, 0, 0)
    """
    return datetime.strptime(raw, date_format)
