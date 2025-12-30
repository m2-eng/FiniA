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
        
        where_clause = f"WHERE {' AND '.join(where_conditions)}" if where_conditions else ""

        # Sorting (whitelisted columns)
        sort_column_map = {
            'name': 's.name',
            'wkn': 's.wkn',
            'isin': 's.isin',
            'currentVolume': 's.currentVolume',
            'currentPrice': 's.currentPrice',
            'portfolioValue': 's.portfolioValue',
            'dateImport': 's.dateImport'
        }
        sort_column = sort_column_map.get(sort_by, 's.name')
        sort_direction = 'DESC' if (sort_dir or '').lower() == 'desc' else 'ASC'

        count_query = f"""
            SELECT COUNT(*)
            FROM view_sharePortfolioValue s
            {where_clause}
        """

        data_query = f"""
            SELECT s.id, s.name, s.isin, s.wkn, s.currentVolume, s.currentPrice, s.portfolioValue
            FROM view_sharePortfolioValue s
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
        columns = ['id', 'name', 'isin', 'wkn', 'currentVolume', 'currentPrice', 'portfolioValue']
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
        """Get share by ISIN or WKN (for deduplication)"""
        query = "SELECT id, dateImport, name, isin, wkn FROM tbl_share WHERE isin = %s OR wkn = %s LIMIT 1"
        self.cursor.execute(query, (isin, wkn))
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
