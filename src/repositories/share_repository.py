#
# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (c) 2026 m2-eng
# Author: m2-eng
# Co-Author: GitHub Copilot
# License: GNU Affero General Public License v3.0 (AGPL-3.0-only)
# Purpose: Repository for Share (Wertpapier) entities
#
"""
Repository for Share (Wertpapier) entities
Handles all database operations for tbl_share
"""

class ShareRepository:
    """Repository class for managing shares/stocks in the database"""
    
    def __init__(self, cursor):
        """Initialize with database cursor"""
        self.cursor = cursor
    
    def get_all_shares_paginated(self, page=1, page_size=50, search: str = None, holdings_filter: str = None, sort_by: str = None, sort_dir: str = None):
        """Get all shares with pagination, optional text search, holdings filter, sorting, and portfolio value"""
        offset = (page - 1) * page_size

        # Build WHERE clause for search
        where_conditions = []
        where_params = []
        
        if search:
            like = f"%{search}%"
            where_conditions.append("(s.name LIKE %s OR s.isin LIKE %s OR s.wkn LIKE %s)")
            where_params.extend([like, like, like])
        
        # Filter for only shares with current holdings
        if holdings_filter == "in_stock":
            where_conditions.append("s.currentVolume <> 0")
        
        # Filter for incomplete shares (missing name or wkn)
        if holdings_filter == "incomplete":
            where_conditions.append("(s.name IS NULL OR s.name = '' OR s.wkn IS NULL OR s.wkn = '')")
        
        where_clause = f"WHERE {' AND '.join(where_conditions)}" if where_conditions else ""

        # Sorting (whitelisted columns)
        sort_column_map = {
            'name': 's.name',
            'wkn': 's.wkn',
            'isin': 's.isin',
            'currentVolume': 's.currentVolume',
            'currentPrice': 's.currentPrice',
            'portfolioValue': 's.portfolioValue',
            'dateImport': 's.dateImport',
            # Aggregated sums aliases
            'investments': 'investments',
            'proceeds': 'proceeds',
            'net': 'net'
        }
        sort_column = sort_column_map.get(sort_by, 's.name')
        sort_direction = 'DESC' if (sort_dir or '').lower() == 'desc' else 'ASC'

        count_query = f"""
            SELECT COUNT(*)
            FROM view_sharePortfolioValue s
            {where_clause}
        """

        data_query = f"""
            SELECT 
                s.id, s.name, s.isin, s.wkn, s.currentVolume, s.currentPrice, s.portfolioValue,
                COALESCE(agg.investments, 0) AS investments,
                COALESCE(agg.proceeds, 0) AS proceeds,
                COALESCE(agg.net, 0) AS net,
                COALESCE(agg.dividends, 0) AS dividends
            FROM view_sharePortfolioValue s
            LEFT JOIN (
                SELECT 
                    st.share AS share_id,
                    ABS(SUM(CASE WHEN st.tradingVolume > 0 THEN COALESCE(ae.amount, 0) ELSE 0 END)) AS investments,
                    ABS(SUM(CASE WHEN st.tradingVolume < 0 THEN COALESCE(ae.amount, 0) ELSE 0 END)) AS proceeds,
                    ABS(SUM(CASE WHEN st.tradingVolume = 0 THEN COALESCE(ae.amount, 0) ELSE 0 END)) AS dividends,
                    SUM(COALESCE(ae.amount, 0)) AS net
                FROM tbl_shareTransaction st
                LEFT JOIN tbl_accountingEntry ae ON st.accountingEntry = ae.id
                GROUP BY st.share
            ) agg ON agg.share_id = s.id
            {where_clause}
            ORDER BY {sort_column} {sort_direction}
            LIMIT %s OFFSET %s
        """

        count_params = where_params.copy()
        data_params = where_params + [page_size, offset]

        # Get total count
        self.cursor.execute(count_query, count_params)
        total = self.cursor.fetchone()[0]
        
        # Get paginated data
        self.cursor.execute(data_query, data_params)
        rows = self.cursor.fetchall()
        
        # Convert tuples to dictionaries
        columns = ['id', 'name', 'isin', 'wkn', 'currentVolume', 'currentPrice', 'portfolioValue', 'investments', 'proceeds', 'net', 'dividends']
        shares = [dict(zip(columns, row)) for row in rows] if rows else []
        
        return {
            'shares': shares,
            'page': page,
            'page_size': page_size,
            'total': total
        }
    
    def get_all_shares(self):
        """Get all shares without pagination, including portfolio values"""
        query = """
            SELECT id, name, isin, wkn, currentVolume, currentPrice, portfolioValue
            FROM view_sharePortfolioValue
            ORDER BY name ASC
        """
        self.cursor.execute(query)
        rows = self.cursor.fetchall()
        columns = ['id', 'name', 'isin', 'wkn', 'currentVolume', 'currentPrice', 'portfolioValue']
        return [dict(zip(columns, row)) for row in rows] if rows else []
    
    def get_share_by_id(self, share_id):
        """Get a specific share by ID with portfolio value"""
        query = """
            SELECT id, name, isin, wkn, currentVolume, currentPrice, portfolioValue
            FROM view_sharePortfolioValue
            WHERE id = %s
        """
        self.cursor.execute(query, (share_id,))
        row = self.cursor.fetchone()
        if row:
            columns = ['id', 'name', 'isin', 'wkn', 'currentVolume', 'currentPrice', 'portfolioValue']
            return dict(zip(columns, row))
        return None
    
    def get_share_by_isin_wkn(self, isin, wkn):
        """Get share by ISIN or WKN (ISIN has priority)
        Args:
            isin: ISIN code (international)
            wkn: WKN code (German)
        Returns:
            Share dict if found, None otherwise
        """
        # Try ISIN first (international standard, has priority)
        if isin:
            query = "SELECT id, dateImport, name, isin, wkn FROM tbl_share WHERE isin = %s LIMIT 1"
            self.cursor.execute(query, (isin,))
            row = self.cursor.fetchone()
            if row:
                columns = ['id', 'dateImport', 'name', 'isin', 'wkn']
                return dict(zip(columns, row))
        
        # Fall back to WKN if ISIN not found or not provided
        if wkn:
            query = "SELECT id, dateImport, name, isin, wkn FROM tbl_share WHERE wkn = %s LIMIT 1"
            self.cursor.execute(query, (wkn,))
            row = self.cursor.fetchone()
            if row:
                columns = ['id', 'dateImport', 'name', 'isin', 'wkn']
                return dict(zip(columns, row))
        
        return None
    
    def insert_share(self, name, isin, wkn):
        """Insert a new share"""
        query = """
            INSERT INTO tbl_share (dateImport, name, isin, wkn) 
            VALUES (NOW(), %s, %s, %s)
        """
        self.cursor.execute(query, (name, isin, wkn))
        return self.cursor.lastrowid

    def update_share(self, share_id, name, isin, wkn):
        """Update an existing share"""
        query = """
            UPDATE tbl_share
            SET name = %s, isin = %s, wkn = %s
            WHERE id = %s
        """
        self.cursor.execute(query, (name, isin, wkn, share_id))
        return self.cursor.rowcount

    def delete_share(self, share_id):
        """Delete a share by ID"""
        query = "DELETE FROM tbl_share WHERE id = %s"
        self.cursor.execute(query, (share_id,))
        return self.cursor.rowcount
