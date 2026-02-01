class SettingsRepository:
    """Repository for storing and retrieving application settings (global or user-specific)."""

    def __init__(self, cursor):
        self.cursor = cursor

    def get_settings(self, key: str, user_id: int | None = None):
        """Get all settings entries for a given key (returns list of values)"""
        if user_id is None:
            query = """
                SELECT `value`
                FROM tbl_setting
                WHERE `key` = %s AND user_id IS NULL
            """
            self.cursor.execute(query, (key,))
        else:
            query = """
                SELECT `value`
                FROM tbl_setting
                WHERE `key` = %s AND (user_id = %s OR user_id IS NULL)
                ORDER BY user_id DESC
            """
            self.cursor.execute(query, (key, user_id))
        rows = self.cursor.fetchall()
        return [row[0] for row in rows] if rows else []

    def add_setting(self, key: str, value_json, user_id: int | None = None):
        """Add a new setting entry (allows multiple entries per key)"""
        query = """
            INSERT INTO tbl_setting (user_id, `key`, `value`)
            VALUES (%s, %s, %s)
        """
        self.cursor.execute(query, (user_id, key, value_json))
        return self.cursor.lastrowid

    def delete_setting(self, key: str, value_json, user_id: int | None = None):
        """Delete specific setting entry by key and value"""
        query = """
            DELETE FROM tbl_setting
            WHERE `key` = %s AND `value` = %s AND (user_id IS NULL OR user_id = %s)
        """
        self.cursor.execute(query, (key, value_json, user_id))
        return self.cursor.rowcount

    def delete_setting_by_id(self, setting_id: int):
        """Delete setting by ID"""
        query = "DELETE FROM tbl_setting WHERE id = %s"
        self.cursor.execute(query, (setting_id,))
        return self.cursor.rowcount

    def get_setting_entries(self, key: str, user_id: int | None = None):
        """Get setting entries with ids for a given key."""
        if user_id is None:
            query = """
                SELECT id, `value`, user_id
                FROM tbl_setting
                WHERE `key` = %s AND user_id IS NULL
            """
            self.cursor.execute(query, (key,))
        else:
            query = """
                SELECT id, `value`, user_id
                FROM tbl_setting
                WHERE `key` = %s AND (user_id = %s OR user_id IS NULL)
                ORDER BY user_id DESC
            """
            self.cursor.execute(query, (key, user_id))
        rows = self.cursor.fetchall()
        if not rows:
            return []
        return [
            {
                "id": row[0],
                "value": row[1],
                "user_id": row[2]
            }
            for row in rows
        ]

    def update_setting_value(self, setting_id: int, value_json):
        """Update setting value by ID."""
        query = "UPDATE tbl_setting SET `value` = %s WHERE id = %s"
        self.cursor.execute(query, (value_json, setting_id))
        return self.cursor.rowcount
