#
# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (c) 2026 m2-eng
# Author: m2-eng
# Co-Author: GitHub Copilot
# License: GNU Affero General Public License v3.0 (AGPL-3.0-only)
# Purpose: Authentication and session management module.
#
"""
Authentication and session management module.
"""

from .session_store import SessionStore
from .connection_pool_manager import ConnectionPoolManager
from .rate_limiter import LoginRateLimiter
from .utils import get_database_name

__all__ = [
    'SessionStore',
    'ConnectionPoolManager',
    'LoginRateLimiter',
    'get_database_name'
]
