#
# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (c) 2026 m2-eng
# Author: m2-eng
# Co-Author: GitHub Copilot
# License: GNU Affero General Public License v3.0 (AGPL-3.0-only)
# Purpose: Module for planning repository.
#
from datetime import datetime, date, timedelta
from decimal import Decimal
import calendar
from repositories.base import BaseRepository


class PlanningRepository(BaseRepository):
    """Repository for managing planning entries and their occurrences."""
    
    def get_all_plannings(self) -> list[dict]:
        """
        Get all planning entries with their details (legacy: returns all, use get_plannings_paginated for large datasets).
        
        Returns:
            List of planning dictionaries with account, category, and cycle info
        """
        return self.get_plannings_paginated(page=1, page_size=1000000)  # Fallback to paginated method

    def get_plannings_paginated(self, page: int = 1, page_size: int = 100) -> dict:
        """
        Get paginated planning entries with their details.
        
        Args:
            page: Page number (1-based)
            page_size: Number of records per page (max 1000)
            
        Returns:
            Dict with 'plannings' list, 'page', 'page_size', and 'total' count
        """
        page = max(1, page)
        page_size = min(max(1, page_size), 1000)
        offset = (page - 1) * page_size
        
        # Get total count
        count_sql = "SELECT COUNT(*) FROM tbl_planning"
        self.cursor.execute(count_sql)
        total = self.cursor.fetchone()[0]
        
        # Get paginated data
        query = """
            SELECT 
                p.id,
                p.dateImport,
                p.description,
                p.amount,
                p.dateStart,
                p.dateEnd,
                p.account as account_id,
                a.name as account_name,
                p.category as category_id,
                vcf.fullname as category_name,
                p.cycle as cycle_id,
                pc.cycle as cycle_name
            FROM tbl_planning p
            JOIN tbl_account a ON p.account = a.id
            LEFT JOIN view_categoryFullname vcf ON p.category = vcf.id
            JOIN tbl_planningCycle pc ON p.cycle = pc.id
            ORDER BY p.dateStart DESC, p.id DESC
            LIMIT %s OFFSET %s
        """
        self.cursor.execute(query, (page_size, offset))
        
        plannings = []
        for row in self.cursor.fetchall():
            planning = {
                "id": row[0],
                "dateImport": row[1],
                "description": row[2],
                "amount": row[3],
                "dateStart": row[4],
                "dateEnd": row[5],
                "account_id": row[6],
                "account_name": row[7],
                "category_id": row[8],
                "category_name": row[9],
                "cycle_id": row[10],
                "cycle_name": row[11]
            }
            plannings.append(planning)
        
        return {
            "plannings": plannings,
            "page": page,
            "page_size": page_size,
            "total": total
        }

    def get_planning_entries(self, planning_id: int) -> list[dict]:
        """Return all planning entries for a planning ordered by date."""
        query = """
            SELECT id, dateImport, dateValue
            FROM tbl_planningEntry
            WHERE planning = %s
            ORDER BY dateValue
        """
        self.cursor.execute(query, (planning_id,))
        entries = []
        for row in self.cursor.fetchall():
            entries.append({
                "id": row[0],
                "dateImport": row[1],
                "dateValue": row[2],
                "planning_id": planning_id
            })
        return entries

    def _get_cycle(self, cycle_id: int) -> dict | None:
        query = "SELECT id, cycle, periodValue, periodUnit FROM tbl_planningCycle WHERE id = %s"
        self.cursor.execute(query, (cycle_id,))
        row = self.cursor.fetchone()
        if not row:
            return None
        return {
            "id": row[0],
            "cycle": row[1],
            "period_value": row[2],
            "period_unit": row[3]
        }

    def _resolve_cycle_interval(self, cycle: dict) -> dict:
        """Map a cycle to an interval definition.

        Prefers structured values from the DB (period_value/period_unit) and
        falls back to name-based heuristics for backward compatibility.
        Returns a dict with either `days`, `months`, or `once`.
        """

        # Try explicit period definition first
        period_value = cycle.get("period_value")
        period_unit = (cycle.get("period_unit") or "").lower()

        if period_value is not None and period_unit:
            try:
                value = float(period_value)
            except (TypeError, ValueError):
                value = None

            if value is not None and value > 0:
                if period_unit == "d":
                    return {"days": value}
                if period_unit == "m":
                    # Months must be integer for calendar-correct jumps; fall back to days if fractional
                    if abs(value - round(value)) < 1e-6:
                        return {"months": int(round(value))}
                    return {"days": value * 30}
                if period_unit == "y":
                    return {"months": int(round(value * 12)) or 12}

        # Fallback: infer from name
        name = (cycle.get("cycle") or "").lower()

        if "einmal" in name or "once" in name or "single" in name:
            return {"once": True}
        if "woche" in name or "week" in name:
            return {"days": 7}
        if "quart" in name:
            return {"months": 3}
        if "halb" in name or "semi" in name:
            return {"months": 6}
        if "jahr" in name or "year" in name:
            return {"months": 12}
        if "tag" in name or "day" in name:
            return {"days": 1}

        # Default: monthly cadence to stay functional even with custom names
        return {"months": 1}

    def _add_months(self, current: date, months: int) -> date:
        month_index = current.month - 1 + months
        year = current.year + month_index // 12
        month = month_index % 12 + 1
        last_day = calendar.monthrange(year, month)[1]
        return current.replace(year=year, month=month, day=min(current.day, last_day))

    def _advance_date(self, current: date, interval: dict) -> date:
        if interval.get("once"):
            return current
        if "months" in interval:
            months = interval["months"]
            # Ensure it's an integer for month-based arithmetic
            return self._add_months(current, int(months))
        if "days" in interval:
            days = interval["days"]
            # Convert to integer for timedelta
            return current + timedelta(days=int(days))
        return current + timedelta(days=30)

    def regenerate_planning_entries(self, planning_id: int, today: date | None = None) -> list[dict] | None:
        """Create planning entries up to min(planning end date, end of next year).

        If the planning has no end date, limit generation to 31.12 of the next
        calendar year (relative to `today`). Existing entries for this planning
        are replaced.
        """
        planning = self.get_planning_by_id(planning_id)
        if not planning:
            return None

        cycle = self._get_cycle(planning["cycle_id"])
        if not cycle:
            return None

        interval = self._resolve_cycle_interval(cycle)

        base_today = today or date.today()
        end_of_next_year = date(base_today.year + 1, 12, 31)
        # Always cap generation at end of next year, even if planning has a later end date
        if planning["dateEnd"]:
            target_end = min(planning["dateEnd"].date(), end_of_next_year)
        else:
            target_end = end_of_next_year

        current_date = planning["dateStart"].date()
        if current_date > target_end:
            target_end = current_date

        entries_to_create: list[datetime] = []
        guard = 0

        while current_date <= target_end:
            entries_to_create.append(datetime.combine(current_date, datetime.min.time()))
            if interval.get("once"):
                break
            current_date = self._advance_date(current_date, interval)
            guard += 1
            if guard > 10000:
                break

        delete_sql = "DELETE FROM tbl_planningEntry WHERE planning = %s"
        self.cursor.execute(delete_sql, (planning_id,))

        if entries_to_create:
            insert_sql = "INSERT INTO tbl_planningEntry (dateImport, dateValue, planning) VALUES (NOW(), %s, %s)"
            self.cursor.executemany(insert_sql, [(dt, planning_id) for dt in entries_to_create])

        return self.get_planning_entries(planning_id)

    def delete_planning_entry(self, planning_id: int, entry_id: int) -> bool:
        """Delete a single planning entry by id for a specific planning."""
        query = "DELETE FROM tbl_planningEntry WHERE id = %s AND planning = %s"
        self.cursor.execute(query, (entry_id, planning_id))
        return self.cursor.rowcount > 0
    
    def get_planning_by_id(self, planning_id: int) -> dict | None:
        """
        Get a single planning entry by ID.
        
        Args:
            planning_id: Planning ID
            
        Returns:
            Planning dictionary or None if not found
        """
        query = """
            SELECT 
                p.id,
                p.dateImport,
                p.description,
                p.amount,
                p.dateStart,
                p.dateEnd,
                p.account as account_id,
                a.name as account_name,
                p.category as category_id,
                vcf.fullname as category_name,
                p.cycle as cycle_id,
                pc.cycle as cycle_name
            FROM tbl_planning p
            JOIN tbl_account a ON p.account = a.id
            LEFT JOIN view_categoryFullname vcf ON p.category = vcf.id
            JOIN tbl_planningCycle pc ON p.cycle = pc.id
            WHERE p.id = %s
        """
        self.cursor.execute(query, (planning_id,))
        row = self.cursor.fetchone()
        
        if not row:
            return None
        
        return {
            "id": row[0],
            "dateImport": row[1],
            "description": row[2],
            "amount": row[3],
            "dateStart": row[4],
            "dateEnd": row[5],
            "account_id": row[6],
            "account_name": row[7],
            "category_id": row[8],
            "category_name": row[9],
            "cycle_id": row[10],
            "cycle_name": row[11]
        }
    
    def create_planning(
        self,
        description: str | None,
        amount: Decimal,
        date_start: datetime,
        date_end: datetime | None,
        account_id: int,
        category_id: int,
        cycle_id: int
    ) -> int:
        """
        Create a new planning entry.
        
        Args:
            description: Optional description
            amount: Planning amount
            date_start: Start date
            date_end: Optional end date
            account_id: Account ID
            category_id: Category ID
            cycle_id: Planning cycle ID
            
        Returns:
            ID of the created planning
        """
        query = """
            INSERT INTO tbl_planning 
            (dateImport, description, amount, dateStart, dateEnd, account, category, cycle)
            VALUES (NOW(), %s, %s, %s, %s, %s, %s, %s)
        """
        self.cursor.execute(
            query,
            (description, amount, date_start, date_end, account_id, category_id, cycle_id)
        )
        return self.cursor.lastrowid
    
    def update_planning(
        self,
        planning_id: int,
        description: str | None,
        amount: Decimal,
        date_start: datetime,
        date_end: datetime | None,
        account_id: int,
        category_id: int,
        cycle_id: int
    ) -> bool:
        """
        Update an existing planning entry.
        
        Args:
            planning_id: Planning ID to update
            description: Optional description
            amount: Planning amount
            date_start: Start date
            date_end: Optional end date
            account_id: Account ID
            category_id: Category ID
            cycle_id: Planning cycle ID
            
        Returns:
            True if statement executed (row may be unchanged)
        """
        query = """
            UPDATE tbl_planning
            SET description = %s,
                amount = %s,
                dateStart = %s,
                dateEnd = %s,
                account = %s,
                category = %s,
                cycle = %s
            WHERE id = %s
        """
        self.cursor.execute(
            query,
            (description, amount, date_start, date_end, account_id, category_id, cycle_id, planning_id)
        )
        # Even if rowcount == 0 (no data change), the update is considered successful because the row exists
        return True
    
    def delete_planning(self, planning_id: int) -> bool:
        """
        Delete a planning entry and its planning entries.
        
        Args:
            planning_id: Planning ID to delete
            
        Returns:
            True if deleted, False if not found
        """
        # First delete all planning entries
        entries_query = "DELETE FROM tbl_planningEntry WHERE planning = %s"
        self.cursor.execute(entries_query, (planning_id,))
        
        # Then delete the planning itself
        query = "DELETE FROM tbl_planning WHERE id = %s"
        self.cursor.execute(query, (planning_id,))
        return self.cursor.rowcount > 0
    
    def get_all_cycles(self) -> list[dict]:
        """
        Get all planning cycles.
        
        Returns:
            List of cycle dictionaries
        """
        query = "SELECT id, cycle FROM tbl_planningCycle ORDER BY id"
        self.cursor.execute(query)
        
        return [{"id": row[0], "cycle": row[1]} for row in self.cursor.fetchall()]
