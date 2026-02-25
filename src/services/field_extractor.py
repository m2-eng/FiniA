#
# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (c) 2026 m2-eng
# Author: m2-eng
# Co-Author: GitHub Copilot
# License: GNU Affero General Public License v3.0 (AGPL-3.0-only)
# Purpose: Field extraction utilities for CSV import.
#
"""
Field extraction utilities for CSV import.

This module provides a unified implementation for extracting field values
from CSV rows using various mapping strategies.
"""

import re
from typing import Any


def extract_field_value(row: dict[str, Any], mapping: Any) -> str:
    """Extract field value from CSV row using mapping configuration.
    
    Supports multiple extraction strategies:
    - Single column: {name: "ColumnName"}
    - Multi-column join: {join: ["Col1", "Col2"], separator: " | "}
    - Regex extraction: {sources: [{name: "Col", regex: "pattern"}]}
    - Legacy names: {names: ["Col1", "Col2"]} (first match wins)
    - Legacy regex: {regex: "pattern", source: "Col"}
    
    Args:
        row: Dictionary mapping column names to values
        mapping: Mapping configuration (string, dict, or None)
    
    Returns:
        Extracted value as string (empty string if not found)
    
    Examples:
        >>> row = {"Date": "2024-01-01", "Amount": "100.00"}
        >>> extract_field_value(row, {"name": "Date"})
        '2024-01-01'
        
        >>> extract_field_value(row, {"join": ["Date", "Amount"], "separator": " | "})
        '2024-01-01 | 100.00'
        
        >>> row = {"Details": "IBAN: DE12345678"}
        >>> extract_field_value(row, {"sources": [{"name": "Details", "regex": r"..."}]})
        'DE12345678'
    """
    if mapping is None:
        return ""
    
    # Strategy 1: Simple string mapping (legacy)
    if isinstance(mapping, str):
        return (row.get(mapping, "") or "").strip()
    
    if not isinstance(mapping, dict):
        return ""
    
    # Strategy 2: Single column name
    if "name" in mapping:
        col_name = mapping.get("name")
        return (row.get(col_name, "") or "").strip()
    
    # Strategy 3: Join multiple columns
    if "join" in mapping:
        separator = mapping.get("separator", " ")
        parts = [
            (row.get(item, "") or "").strip()
            for item in mapping.get("join", [])
            if (row.get(item, "") or "").strip()
        ]
        return separator.join(parts)
    
    # Strategy 4: Extract via regex from source column(s)
    if "sources" in mapping:
        sources = mapping.get("sources", [])
        all_matches = []
        
        for source_config in sources:
            if not isinstance(source_config, dict):
                continue
            
            col_name = source_config.get("name")
            pattern = source_config.get("regex")
            
            if not col_name or not pattern:
                continue
            
            value = row.get(col_name, "") or ""
            try:
                matches = re.findall(pattern, value)
            except re.error:
                # Invalid regex pattern - skip
                continue
            
            if matches:
                # Flatten tuples from capture groups
                for match in matches:
                    if isinstance(match, tuple):
                        # Join all non-empty groups
                        flattened = "".join(g for g in match if g)
                    else:
                        flattened = match
                    
                    if flattened:
                        all_matches.append(flattened)
        
        return " | ".join(all_matches)
    
    # Strategy 5: Legacy regex with single source
    if "regex" in mapping:
        pattern = mapping.get("regex")
        target = mapping.get("source")
        value = row.get(target, "") or ""
        
        try:
            matches = re.findall(pattern, value)
        except re.error:
            return ""
        
        if not matches:
            return ""
        
        # Flatten tuples from capture groups
        extracted = []
        for match in matches:
            if isinstance(match, tuple):
                flattened = "".join(match)
            else:
                flattened = match
            
            if flattened:
                extracted.append(flattened)
        
        return " | ".join(extracted)
    
    # Strategy 6: Legacy names (multiple column names with priority fallbacks)
    if "names" in mapping:
        names = mapping.get("names", [])
        for name in names:
            if name in row and (row.get(name) or "").strip():
                return (row.get(name, "") or "").strip()
        return ""
    
    # No recognized mapping strategy
    return ""
