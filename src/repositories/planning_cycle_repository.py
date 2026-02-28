#
# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (c) 2026 m2-eng
# Author: m2-eng
# Co-Author: GitHub Copilot
# License: GNU Affero General Public License v3.0 (AGPL-3.0-only)
# Purpose: Module for planning cycle repository.
#
from repositories.base import BaseRepository
from datetime import datetime


class PlanningCycleRepository(BaseRepository):
   """Repository for planning cycle management."""

   def get_all(self):
      """Get all planning cycles ordered by ID."""
      sql = """
         SELECT id, cycle, periodValue, periodUnit, dateImport
         FROM tbl_planningCycle
         ORDER BY id ASC
      """
      self.cursor.execute(sql)
      rows = self.cursor.fetchall()

      if not rows:
         return []

      return [
         {
            "id": row[0],
            "cycle": row[1],
            "periodValue": float(row[2]) if row[2] is not None else None,
            "periodUnit": row[3],
            "dateImport": row[4].isoformat() if row[4] else None
         }
         for row in rows
      ]

   def get_by_id(self, cycle_id: int):
      """Get planning cycle by ID."""
      sql = "SELECT id, cycle, periodValue, periodUnit, dateImport FROM tbl_planningCycle WHERE id = %s"
      self.cursor.execute(sql, (cycle_id,))
      row = self.cursor.fetchone()
      if not row:
         return None
      return {
         "id": row[0],
         "cycle": row[1],
         "periodValue": float(row[2]) if row[2] is not None else None,
         "periodUnit": row[3],
         "dateImport": row[4].isoformat() if row[4] else None
      }

   def get_by_cycle(self, cycle_name: str):
      """Get planning cycle by name."""
      sql = "SELECT id, cycle, periodValue, periodUnit, dateImport FROM tbl_planningCycle WHERE cycle = %s"
      self.cursor.execute(sql, (cycle_name,))
      row = self.cursor.fetchone()
      if not row:
         return None
      return {
         "id": row[0],
         "cycle": row[1],
         "periodValue": float(row[2]) if row[2] is not None else None,
         "periodUnit": row[3],
         "dateImport": row[4].isoformat() if row[4] else None
      }

   def insert(self, cycle_name: str, period_value: float, period_unit: str):
      """Insert new planning cycle."""
      sql = """
         INSERT INTO tbl_planningCycle (cycle, periodValue, periodUnit, dateImport)
         VALUES (%s, %s, %s, %s)
      """
      now = datetime.now()
      self.cursor.execute(sql, (cycle_name, period_value, period_unit, now))
      return self.cursor.lastrowid

   def insert_ignore(self, cycle_name: str, period_value: float = 1.0, period_unit: str = "m") -> None:
      sql = """
         INSERT IGNORE INTO tbl_planningCycle (cycle, periodValue, periodUnit, dateImport)
         VALUES (%s, %s, %s, NOW())
      """
      self.cursor.execute(sql, (cycle_name, period_value, period_unit))

   def update(self, cycle_id: int, cycle_name: str, period_value: float, period_unit: str):
      """Update planning cycle."""
      sql = """
         UPDATE tbl_planningCycle
         SET cycle = %s, periodValue = %s, periodUnit = %s
         WHERE id = %s
      """
      self.cursor.execute(sql, (cycle_name, period_value, period_unit, cycle_id))
      return self.cursor.rowcount

   def delete(self, cycle_id: int):
      """Delete planning cycle by ID."""
      sql = "DELETE FROM tbl_planningCycle WHERE id = %s"
      self.cursor.execute(sql, (cycle_id,))
      return self.cursor.rowcount
