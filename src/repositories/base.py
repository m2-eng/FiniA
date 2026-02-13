#
# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (c) 2026 m2-eng
# Author: m2-eng
# Co-Author: GitHub Copilot
# License: GNU Affero General Public License v3.0 (AGPL-3.0-only)
# Purpose: Module for base.
#
class BaseRepository:
   def __init__(self, uow_or_cursor):
      """Initialize repository with either UnitOfWork or raw DB cursor.

      Args:
         uow_or_cursor: UnitOfWork instance (with .cursor attribute) or a raw DB cursor
      """
      if hasattr(uow_or_cursor, "cursor"):
         # UnitOfWork or connection wrapper
         self.uow = uow_or_cursor
         self.cursor = uow_or_cursor.cursor
      else:
         # Raw cursor passed directly
         self.uow = None
         self.cursor = uow_or_cursor
