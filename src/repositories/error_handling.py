#
# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (c) 2026 m2-eng
# Author: m2-eng
# Co-Author: GitHub Copilot
# License: GNU Affero General Public License v3.0 (AGPL-3.0-only)
# Purpose: Central error handling for the repository layer.
#
"""
Central error handling for the repository layer.
"""

from __future__ import annotations

from functools import wraps
from typing import Callable, Any, Tuple

from mysql.connector.errors import Error as MySQLError, OperationalError, InterfaceError, DatabaseError


def handle_repository_errors(operation_name: str = "database operation"):
    """Decorator for consistent error handling in repositories."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            try:
                return func(*args, **kwargs)
            except (OperationalError, InterfaceError, DatabaseError) as exc:
                print(f"Database error in repository during {operation_name}: {exc}")
                raise
            except MySQLError as exc:
                print(f"MySQL error in repository during {operation_name}: {exc}")
                raise
        return wrapper
    return decorator


def execute_fetchall_with_retry(
    cursor,
    query: str,
    params: Tuple,
    retries: int = 1,
):
    """Execute query and fetchall with one reconnect+retry on OperationalError 2013."""
    try:
        cursor.execute(query, params)
        rows = cursor.fetchall()
        return rows, cursor.description
    except OperationalError as error:
        errno = getattr(error, "errno", None)
        if errno == 2013 and retries > 0:
            conn = getattr(cursor, "_connection", None) or getattr(cursor, "connection", None)
            try:
                if conn:
                    conn.reconnect(attempts=1, delay=0)
                    new_cursor = conn.cursor(buffered=True)
                    new_cursor.execute(query, params)
                    rows = new_cursor.fetchall()
                    description = new_cursor.description
                    try:
                        new_cursor.close()
                    except Exception:
                        pass
                    return rows, description
            except Exception:
                pass
        raise
