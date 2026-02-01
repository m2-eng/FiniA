"""
CSV Import Utility Functions

Zentrale Funktionen für CSV-Verarbeitung beim Import von Transaktionen.
Vermeidet Code-Duplikation zwischen verschiedenen Import-Implementierungen.
"""

import csv
import re
from pathlib import Path
from decimal import Decimal
from datetime import datetime
from typing import Iterator


def detect_csv_encoding(csv_path: Path, preferred_encoding: str = "utf-8") -> str:
    """
    Erkennt die Encoding der CSV-Datei durch Ausprobieren verschiedener Encodings.
    
    Args:
        csv_path: Pfad zur CSV-Datei
        preferred_encoding: Bevorzugtes Encoding (wird zuerst versucht)
    
    Returns:
        Erkanntes Encoding
    
    Raises:
        RuntimeError: Wenn kein passendes Encoding gefunden wurde
    """
    encodings_to_try = [preferred_encoding]
    if preferred_encoding.lower() == "utf-8":
        # Häufige Fallback-Encodings für deutsche Bank-Exporte
        encodings_to_try.extend(["latin-1", "iso-8859-1", "cp1252"])
    
    last_error = None
    
    for encoding in encodings_to_try:
        try:
            with open(csv_path, "r", encoding=encoding, newline="") as test_handle:
                # Versuche ersten Teil zu lesen um Encoding zu verifizieren
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
    Liest CSV-Datei und gibt normalisierte Zeilen zurück.
    
    - Erkennt automatisch das richtige Encoding
    - Normalisiert Header (entfernt Whitespace)
    - Gibt Iterator über Zeilen-Dictionaries zurück
    
    Args:
        csv_path: Pfad zur CSV-Datei
        delimiter: CSV-Trennzeichen
        encoding: Bevorzugtes Encoding
    
    Yields:
        Dict mit Spaltennamen als Keys und Zellenwerten als Values
    
    Raises:
        ValueError: Wenn CSV keine Header-Zeile hat
        RuntimeError: Wenn Encoding nicht erkannt werden kann
    """
    detected_encoding = detect_csv_encoding(csv_path, encoding)
    
    with open(csv_path, "r", encoding=detected_encoding, newline="") as handle:
        reader = csv.DictReader(handle, delimiter=delimiter)
        
        if reader.fieldnames is None:
            raise ValueError(f"CSV file {csv_path.name} has no header row or is empty")
        
        # Normalisiere Header-Namen: entferne Whitespace
        # Verhindert Probleme wie 'Betrag ' != 'Betrag'
        reader.fieldnames = [
            fieldname.strip() if isinstance(fieldname, str) else fieldname
            for fieldname in reader.fieldnames
        ]
        
        yield from reader


def parse_amount(raw: str, decimal_separator: str = ".") -> Decimal:
    """
    Parst Betrag-String zu Decimal.
    
    Behandelt verschiedene Whitespace-Zeichen und Tausender-Trennzeichen.
    
    Args:
        raw: Betrag als String (z.B. "1.234,56" oder "1234.56")
        decimal_separator: Dezimaltrennzeichen ("," oder ".")
    
    Returns:
        Betrag als Decimal
    
    Examples:
        >>> parse_amount("1.234,56", ",")
        Decimal('1234.56')
        >>> parse_amount("1,234.56", ".")
        Decimal('1234.56')
    """
    if raw is None:
        raw = ""
    
    # Entferne alle Whitespace-Zeichen inkl. non-breaking space und narrow no-break space
    normalized = re.sub(r"[\s\u00A0\u202F]", "", str(raw))
    
    if decimal_separator == ",":
        # Entferne Tausender-Punkte und konvertiere Komma zu Punkt
        normalized = normalized.replace(".", "").replace(",", ".")
    
    return Decimal(normalized)


def parse_date(raw: str, date_format: str) -> datetime:
    """
    Parst Datum-String zu datetime.
    
    Args:
        raw: Datum als String
        date_format: Python strptime Format-String (z.B. "%d.%m.%Y")
    
    Returns:
        Geparster datetime
    
    Examples:
        >>> parse_date("31.12.2023", "%d.%m.%Y")
        datetime.datetime(2023, 12, 31, 0, 0)
    """
    return datetime.strptime(raw, date_format)
