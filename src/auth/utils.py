#
# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (c) 2026 m2-eng
# Author: m2-eng
# Co-Author: GitHub Copilot
# License: GNU Affero General Public License v3.0 (AGPL-3.0-only)
# Purpose: Utility functions for authentication.
#
"""
Utility functions for authentication.
"""


def get_database_name(db_username: str, username_prefix: str = "finia_", database_prefix: str = "finiaDB_") -> str:
    """
    Derives database name from DB username.
    
    Pattern: finia_<name> -> finiaDB_<name>
    
    Args:
        db_username: MySQL username (e.g. "finia_username")
        username_prefix: Expected prefix in the username
        database_prefix: Prefix for database names
        
    Returns:
        Database name (e.g. "finiaDB_username")
        
    Raises:
        ValueError: On invalid username format
        
    Examples:
        >>> get_database_name("finia_username")
        'finiaDB_username'
        >>> get_database_name("finia_alice")
        'finiaDB_alice'
    """
    if not db_username.startswith(username_prefix):
        raise ValueError(f"Username must start with '{username_prefix}'")
    
    if len(db_username) <= len(username_prefix):
        raise ValueError("Username too short")
    
    # Extract suffix (e.g. "username" from "finia_username")
    suffix = db_username[len(username_prefix):]
    
    # Allow only alphanumeric characters and underscores
    if not suffix.replace("_", "").isalnum():
        raise ValueError("Invalid characters in username")
    
    return f"{database_prefix}{suffix}"
