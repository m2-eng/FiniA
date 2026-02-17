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

logger = logging.getLogger("uvicorn.error")


def _build_repository_error_detail(
    operation_name: str,
    base_message: str,
    exc: Exception,
    error_message: str | None = None,
    additional_info: str = "",
) -> str:
    final_message = error_message or base_message
    detail = f"{final_message} ({operation_name}): {exc}"
    if additional_info:
        detail = f"{detail} | {additional_info}"
    return detail


def _log_repository_exception(
    operation_name: str,
    base_message: str,
    exc: Exception,
    error_message: str | None = None,
    additional_info: str = "",
) -> None:
    logger.exception(
        _build_repository_error_detail(
            operation_name,
            base_message,
            exc,
            error_message=error_message,
            additional_info=additional_info,
        )
    )


def handle_repository_errors(
    operation_name: str = "database operation",
    error_message: str | None = None,
    additional_info: str = "",
):
    """Decorator for consistent error handling in repositories."""
    def decorator(func: Callable) -> Callable:
        def log_exception(exc: Exception, base_message: str) -> None:
            _log_repository_exception(
                operation_name,
                base_message,
                exc,
                error_message=error_message,
                additional_info=additional_info,
            )

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


class RepositoryCursorProxy:
    def __init__(self, cursor, operation_prefix: str = "repository") -> None:
        self._cursor = cursor
        self._operation_prefix = operation_prefix

    def _call(self, method_name: str, *args, **kwargs):
        operation_name = f"{self._operation_prefix}.{method_name}"
        try:
            method = getattr(self._cursor, method_name)
            return method(*args, **kwargs)
        except (OperationalError, InterfaceError, DatabaseError) as exc:
            _log_repository_exception(operation_name, "Database connection error", exc)
            raise
        except MySQLError as exc:
            _log_repository_exception(operation_name, "Database error", exc)
            raise

    def execute(self, *args, **kwargs):
        return self._call("execute", *args, **kwargs)

    def executemany(self, *args, **kwargs):
        return self._call("executemany", *args, **kwargs)

    def callproc(self, *args, **kwargs):
        return self._call("callproc", *args, **kwargs)

    def fetchone(self, *args, **kwargs):
        return self._call("fetchone", *args, **kwargs)

    def fetchall(self, *args, **kwargs):
        return self._call("fetchall", *args, **kwargs)

    def fetchmany(self, *args, **kwargs):
        return self._call("fetchmany", *args, **kwargs)

    def nextset(self, *args, **kwargs):
        return self._call("nextset", *args, **kwargs)

    def __getattr__(self, name: str):
        return getattr(self._cursor, name)

    def __iter__(self):
        return iter(self._cursor)


def wrap_repository_cursor(cursor, operation_prefix: str = "repository"):
    if isinstance(cursor, RepositoryCursorProxy):
        return cursor
    return RepositoryCursorProxy(cursor, operation_prefix=operation_prefix)


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
