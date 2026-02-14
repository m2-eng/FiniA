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
import logging

from mysql.connector.errors import Error as MySQLError, OperationalError, InterfaceError, DatabaseError

logger = logging.getLogger(__name__)


def handle_repository_errors(
    operation_name: str = "database operation",
    error_message: str | None = None,
    additional_info: str = "",
):
    """Decorator for consistent error handling in repositories."""
    def decorator(func: Callable) -> Callable:
        def build_detail(base_message: str, exc: Exception) -> str:
            detail = f"{base_message} ({operation_name}): {exc}"
            if additional_info:
                detail = f"{detail} | {additional_info}"
            return detail

        def log_exception(exc: Exception, base_message: str) -> None:
            final_message = error_message or base_message
            logger.exception(build_detail(final_message, exc))

        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            try:
                return func(*args, **kwargs)
            except (OperationalError, InterfaceError, DatabaseError) as exc:
                log_exception(exc, "Database connection error")
                raise
            except MySQLError as exc:
                log_exception(exc, "Database error")
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
