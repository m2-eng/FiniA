#
# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (c) 2026 m2-eng
# Author: m2-eng
# Co-Author: GitHub Copilot
# License: GNU Affero General Public License v3.0 (AGPL-3.0-only)
# Purpose: Repository for ShareHistory entities
#
"""
Repository for ShareHistory entities
Handles all database operations for tbl_shareHistory
"""

class ShareHistoryRepository:
    """Repository class for managing share price history in the database"""
    
    def __init__(self, cursor):
        """Initialize with database cursor"""
        self.cursor = cursor
    
    def get_all_paginated(self, page=1, page_size=50, sort_by: str = None, sort_dir: str = None, search: str = None, checked_filter: str = None):
        """Get all share history with pagination, share details, sorting, search, and checked filter"""
        offset = (page - 1) * page_size

        sort_column_map = {
            'date': 'h.date',
            'share_name': 's.name',
            'amount': 'h.amount',
            'wkn': 's.wkn',
            'isin': 's.isin'
        }
        sort_column = sort_column_map.get(sort_by, 'h.date')
        sort_direction = 'ASC' if (sort_dir or '').lower() == 'asc' else 'DESC'

        conditions = []
        params = []

        if search:
            like = f"%{search}%"
            conditions.append("(s.name LIKE %s OR s.isin LIKE %s OR s.wkn LIKE %s)")
            params.extend([like, like, like])

        if checked_filter == 'unchecked':
            conditions.append("h.checked = 0")

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        count_query = f"""
            SELECT COUNT(*)
            FROM tbl_shareHistory h
            JOIN tbl_share s ON h.share = s.id
            {where_clause}
        """

        data_query = f"""
            SELECT 
                h.id, h.dateImport, h.amount, h.date, h.checked, h.share,
                s.name as share_name, s.isin, s.wkn
            FROM tbl_shareHistory h
            JOIN tbl_share s ON h.share = s.id
            {where_clause}
            ORDER BY {sort_column} {sort_direction}
            LIMIT %s OFFSET %s
        """

        # Get total count
        self.cursor.execute(count_query, params)
        total = self.cursor.fetchone()[0]

        # Get paginated data with share info
        self.cursor.execute(data_query, params + [page_size, offset])
        rows = self.cursor.fetchall()
        
        # Convert tuples to dictionaries
        columns = ['id', 'dateImport', 'amount', 'date', 'checked', 'share', 'share_name', 'isin', 'wkn']
        history = [dict(zip(columns, row)) for row in rows] if rows else []
        
        return {
            'history': history,
            'page': page,
            'page_size': page_size,
            'total': total
        }
    
    def get_all_by_share_paginated(self, share_id, page=1, page_size=50):
        """Get history for a specific share with pagination"""
        offset = (page - 1) * page_size
        
        # Get total count
        self.cursor.execute("SELECT COUNT(*) FROM tbl_shareHistory WHERE share = %s", (share_id,))
        total = self.cursor.fetchone()[0]
        
        # Get paginated data
        query = """
            SELECT 
                h.id, h.dateImport, h.amount, h.date, h.checked, h.share,
                s.name as share_name, s.isin, s.wkn
            FROM tbl_shareHistory h
            JOIN tbl_share s ON h.share = s.id
            WHERE h.share = %s
            ORDER BY h.date DESC
            LIMIT %s OFFSET %s
        """
        self.cursor.execute(query, (share_id, page_size, offset))
        rows = self.cursor.fetchall()
        
        # Convert tuples to dictionaries
        columns = ['id', 'dateImport', 'amount', 'date', 'checked', 'share', 'share_name', 'isin', 'wkn']
        history = [dict(zip(columns, row)) for row in rows] if rows else []
        
        return {
            'history': history,
            'page': page,
            'page_size': page_size,
            'total': total
        }
    
    def insert_history(self, share_id, amount, date_str):
        """Insert a new history record (date_str should be ISO format YYYY-MM-DD)"""
        existing_id = self.history_exists_for_share_date(share_id, date_str)
        if existing_id:
            return None
        query = """
            INSERT INTO tbl_shareHistory (dateImport, amount, date, checked, share)
            VALUES (NOW(), %s, %s, 0, %s)
        """
        self.cursor.execute(query, (amount, date_str, share_id))
        return self.cursor.lastrowid

    def update_history(self, history_id, share_id, amount, date_str, checked=None):
        """Update an existing history record"""
        duplicate_id = self.history_exists_for_share_date(share_id, date_str, exclude_id=history_id)
        if duplicate_id:
            raise ValueError("History entry for this share and date already exists")
        if checked is None:
            query = """
                UPDATE tbl_shareHistory
                SET share = %s,
                    amount = %s,
                    date = %s
                WHERE id = %s
            """
            self.cursor.execute(query, (share_id, amount, date_str, history_id))
        else:
            query = """
                UPDATE tbl_shareHistory
                SET share = %s,
                    amount = %s,
                    date = %s,
                    checked = %s
                WHERE id = %s
            """
            self.cursor.execute(query, (share_id, amount, date_str, int(bool(checked)), history_id))
        return self.cursor.rowcount

    def set_checked(self, history_id, checked: bool):
        """Mark a history record as checked/unchecked"""
        query = "UPDATE tbl_shareHistory SET checked = %s WHERE id = %s"
        self.cursor.execute(query, (int(bool(checked)), history_id))
        return self.cursor.rowcount

    def get_existing_dates_for_share(self, share_id):
        """Return a set of dates (YYYY-MM-DD) that already exist for a share history"""
        query = "SELECT DATE(date) as date_only FROM tbl_shareHistory WHERE share = %s"
        self.cursor.execute(query, (share_id,))
        rows = self.cursor.fetchall()
        return set([
            row[0].isoformat() if hasattr(row[0], 'isoformat') else str(row[0]).split('T')[0]
            for row in rows
        ]) if rows else set()

    def delete_history(self, history_id):
        """Delete a history record by ID"""
        query = "DELETE FROM tbl_shareHistory WHERE id = %s"
        self.cursor.execute(query, (history_id,))
        return self.cursor.rowcount

    def history_exists_for_share_date(self, share_id, date_str, exclude_id=None):
        """Return the ID of a history entry for the given share and date (date-only), excluding an optional ID"""
        query = """
            SELECT id
            FROM tbl_shareHistory
            WHERE share = %s
              AND DATE(date) = %s
        """
        params = [share_id, date_str]
        if exclude_id is not None:
            query += " AND id <> %s"
            params.append(exclude_id)
        self.cursor.execute(query, params)
        row = self.cursor.fetchone()
        return row[0] if row else None
