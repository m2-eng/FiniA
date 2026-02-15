#
# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (c) 2026 m2-eng
# Author: m2-eng
# Co-Author: GitHub Copilot
# License: GNU Affero General Public License v3.0 (AGPL-3.0-only)
# Purpose: Repository for ShareTransaction entities
#
"""
Repository for ShareTransaction entities
Handles all database operations for tbl_shareTransaction
"""

from repositories.error_handling import wrap_repository_cursor

class ShareTransactionRepository:
    """Repository class for managing share transactions in the database"""
    
    def __init__(self, cursor):
        """Initialize with database cursor"""
        self.cursor = wrap_repository_cursor(cursor, operation_prefix=type(self).__name__)
    
    def get_all_paginated(self, page=1, page_size=50, search: str = None, sort_by: str = None, sort_dir: str = None):
        """Get all share transactions with pagination, share details, sorting, and optional search"""
        offset = (page - 1) * page_size

        sort_column_map = {
            'dateTransaction': 't.dateTransaction',
            'share_name': 's.name',
            'tradingVolume': 't.tradingVolume',
            'wkn': 's.wkn',
            'isin': 's.isin'
        }
        sort_column = sort_column_map.get(sort_by, 't.dateTransaction')
        sort_direction = 'ASC' if (sort_dir or '').lower() == 'asc' else 'DESC'
        
        # Build WHERE clause for search
        where_conditions = []
        where_params = []
        
        if search:
            like = f"%{search}%"
            where_conditions.append("(s.name LIKE %s OR s.isin LIKE %s OR s.wkn LIKE %s)")
            where_params.extend([like, like, like])
        
        where_clause = f"WHERE {' AND '.join(where_conditions)}" if where_conditions else ""
        
        # Get total count
        count_query = f"""
            SELECT COUNT(*)
            FROM tbl_shareTransaction t
            JOIN tbl_share s ON t.share = s.id
            {where_clause}
        """
        self.cursor.execute(count_query, where_params)
        total = self.cursor.fetchone()[0]
        
        # Get paginated data with share info and accounting entry amount
        query = f"""
            SELECT 
                t.id, t.dateImport, t.tradingVolume, t.dateTransaction, t.checked, t.share, t.accountingEntry,
                s.name as share_name, s.isin, s.wkn,
                ae.amount as accountingEntry_amount
            FROM tbl_shareTransaction t
            JOIN tbl_share s ON t.share = s.id
            LEFT JOIN tbl_accountingEntry ae ON t.accountingEntry = ae.id
            {where_clause}
            ORDER BY {sort_column} {sort_direction}
            LIMIT %s OFFSET %s
        """
        data_params = where_params + [page_size, offset]
        self.cursor.execute(query, data_params)
        rows = self.cursor.fetchall()
        
        # Convert tuples to dictionaries
        columns = ['id', 'dateImport', 'tradingVolume', 'dateTransaction', 'checked', 'share', 'accountingEntry', 'share_name', 'isin', 'wkn', 'accountingEntry_amount']
        transactions = [dict(zip(columns, row)) for row in rows] if rows else []
        
        return {
            'transactions': transactions,
            'page': page,
            'page_size': page_size,
            'total': total
        }
    
    def get_by_share_paginated(self, share_id, page=1, page_size=50):
        """Get transactions for a specific share with pagination"""
        offset = (page - 1) * page_size
        
        # Get total count
        self.cursor.execute("SELECT COUNT(*) FROM tbl_shareTransaction WHERE share = %s", (share_id,))
        total = self.cursor.fetchone()[0]
        
        # Get paginated data with accounting entry amount
        query = """
            SELECT 
                t.id, t.dateImport, t.tradingVolume, t.dateTransaction, t.checked, t.share, t.accountingEntry,
                s.name as share_name, s.isin, s.wkn,
                ae.amount as accountingEntry_amount
            FROM tbl_shareTransaction t
            JOIN tbl_share s ON t.share = s.id
            LEFT JOIN tbl_accountingEntry ae ON t.accountingEntry = ae.id
            WHERE t.share = %s
            ORDER BY t.dateTransaction DESC
            LIMIT %s OFFSET %s
        """
        self.cursor.execute(query, (share_id, page_size, offset))
        rows = self.cursor.fetchall()
        
        # Convert tuples to dictionaries
        columns = ['id', 'dateImport', 'tradingVolume', 'dateTransaction', 'checked', 'share', 'accountingEntry', 'share_name', 'isin', 'wkn', 'accountingEntry_amount']
        transactions = [dict(zip(columns, row)) for row in rows] if rows else []
        
        return {
            'transactions': transactions,
            'page': page,
            'page_size': page_size,
            'total': total
        }
    
    def insert_transaction(self, share_id, trading_volume, date_str, accounting_entry_id=None):
        """Insert a new transaction (date_str should be ISO format YYYY-MM-DDTHH:MM:SS or YYYY-MM-DD)
        Uses INSERT IGNORE to skip duplicate transactions (identified by share, tradingVolume, dateTransaction).
        accounting_entry_id is optional and can be None for standalone stock transactions
        """
        query = """
            INSERT IGNORE INTO tbl_shareTransaction (dateImport, tradingVolume, dateTransaction, checked, share, accountingEntry)
            VALUES (NOW(), %s, %s, 0, %s, %s)
        """
        self.cursor.execute(query, (trading_volume, date_str, share_id, accounting_entry_id))
        return self.cursor.lastrowid if self.cursor.rowcount > 0 else None

    def update_transaction(self, transaction_id, share_id, trading_volume, date_str, accounting_entry_id=None):
        """Update an existing transaction"""
        query = """
            UPDATE tbl_shareTransaction
            SET share = %s,
                tradingVolume = %s,
                dateTransaction = %s,
                accountingEntry = %s
            WHERE id = %s
        """
        self.cursor.execute(query, (share_id, trading_volume, date_str, accounting_entry_id, transaction_id))
        return self.cursor.rowcount

    def delete_transaction(self, transaction_id):
        """Delete a transaction by ID"""
        query = "DELETE FROM tbl_shareTransaction WHERE id = %s"
        self.cursor.execute(query, (transaction_id,))
        return self.cursor.rowcount

    def get_all_for_share_sorted(self, share_id):
        """Get all transactions for a share ordered by dateTransaction"""
        query = """
            SELECT id, dateImport, tradingVolume, dateTransaction, checked, share, accountingEntry
            FROM tbl_shareTransaction
            WHERE share = %s
            ORDER BY dateTransaction ASC
        """
        self.cursor.execute(query, (share_id,))
        rows = self.cursor.fetchall()
        columns = ['id', 'dateImport', 'tradingVolume', 'dateTransaction', 'checked', 'share', 'accountingEntry']
        return [dict(zip(columns, row)) for row in rows] if rows else []
