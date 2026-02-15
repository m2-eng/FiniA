#
# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (c) 2026 m2-eng
# Author: m2-eng
# Co-Author: GitHub Copilot
# License: GNU Affero General Public License v3.0 (AGPL-3.0-only)
# Purpose: Module for accounting entry repository.
#
from decimal import Decimal
from repositories.base import BaseRepository


class AccountingEntryRepository(BaseRepository):
    def insert(
        self,
        amount: Decimal,
        transaction_id: int,
        checked: bool = False,
        accounting_planned_id: int | None = None,
        category_id: int | None = None,
    ) -> int | None:
        """
        Insert an accounting entry for a transaction.

        Args:
            amount: Transaction amount
            transaction_id: Reference to tbl_transaction
            checked: Whether entry is verified (default: False)
            accounting_planned_id: Optional reference to tbl_planning
            category_id: Optional reference to tbl_category

        Returns:
            ID of inserted row or None on failure
        """
        query = """
            INSERT INTO tbl_accountingEntry
            (dateImport, checked, amount, transaction, accountingPlanned, category)
            VALUES (NOW(), %s, %s, %s, %s, %s)
        """
        self.cursor.execute(
            query,
            (checked, amount, transaction_id, accounting_planned_id, category_id),
        )
        return self.cursor.lastrowid if self.cursor.rowcount > 0 else None

    def update(
        self,
        entry_id: int,
        amount: Decimal,
        checked: bool,
        accounting_planned_id: int | None = None,
        category_id: int | None = None,
    ) -> bool:
        """
        Update an existing accounting entry.

        Args:
            entry_id: ID of the entry to update
            amount: New transaction amount
            checked: Whether entry is verified
            accounting_planned_id: Optional reference to tbl_planning
            category_id: Optional reference to tbl_category

        Returns:
            True if update was successful, False otherwise
        """
        query = """
            UPDATE tbl_accountingEntry
            SET amount = %s, checked = %s, accountingPlanned = %s, category = %s
            WHERE id = %s
        """
        self.cursor.execute(
            query,
            (amount, checked, accounting_planned_id, category_id, entry_id),
        )
        return self.cursor.rowcount > 0

    def delete(self, entry_id: int) -> bool:
        """
        Delete an accounting entry.

        Args:
            entry_id: ID of the entry to delete

        Returns:
            True if deletion was successful, False otherwise
        """
        query = "DELETE FROM tbl_accountingEntry WHERE id = %s"
        self.cursor.execute(query, (entry_id,))
        return self.cursor.rowcount > 0

    def set_checked_for_transactions(self, transaction_ids: list[int], checked: bool) -> int:
        """
        Bulk set checked flag for all entries belonging to the given transaction IDs.

        Args:
            transaction_ids: List of transaction IDs
            checked: Desired checked state

        Returns:
            Number of rows updated
        """
        if not transaction_ids:
            return 0

        placeholders = ",".join(["%s"] * len(transaction_ids))
        query = f"UPDATE tbl_accountingEntry SET checked = %s WHERE transaction IN ({placeholders})"
        params = [checked, *transaction_ids]
        self.cursor.execute(query, params)
        return self.cursor.rowcount

    def get_all_by_transaction(self, transaction_id: int) -> list[dict]:
        """
        Get all accounting entries for a transaction.

        Args:
            transaction_id: Transaction ID

        Returns:
            List of accounting entries with category names
        """
        query = """
            SELECT
                ae.id,
                ae.dateImport,
                ae.checked,
                ae.amount,
                ae.accountingPlanned,
                ae.category,
                c.name as category_name
            FROM tbl_accountingEntry ae
            LEFT JOIN tbl_category c ON ae.category = c.id
            WHERE ae.transaction = %s
            ORDER BY ae.dateImport DESC
        """
        self.cursor.execute(query, (transaction_id,))
        columns = [desc[0] for desc in self.cursor.description]
        return [dict(zip(columns, row)) for row in self.cursor.fetchall()]

    def get_uncategorized_entries_with_transaction_details(self) -> list[dict]:
        """
        Get uncategorized accounting entries with transaction details.

        Returns:
            List of dicts with entry and transaction fields.
        """
        query = """
            SELECT DISTINCT
                ae.id as entry_id,
                ae.transaction as transaction_id,
                t.description,
                t.recipientApplicant,
                t.amount,
                t.iban,
                t.account as account_id
            FROM tbl_accountingEntry ae
            INNER JOIN tbl_transaction t ON ae.transaction = t.id
            WHERE ae.category IS NULL
            ORDER BY t.dateValue DESC
        """
        self.cursor.execute(query)
        rows = self.cursor.fetchall()
        columns = [desc[0] for desc in self.cursor.description]
        return [dict(zip(columns, row)) for row in rows]

    def update_category(self, entry_id: int, category_id: int) -> bool:
        """
        Update the category for a single accounting entry.

        Args:
            entry_id: Accounting entry ID
            category_id: Category ID to assign

        Returns:
            True if update was successful, False otherwise
        """
        query = "UPDATE tbl_accountingEntry SET category = %s WHERE id = %s"
        self.cursor.execute(query, (category_id, entry_id))
        return self.cursor.rowcount > 0

    def get_entry_with_transaction_by_id(self, entry_id: int) -> dict | None:
        """
        Get a single accounting entry with transaction details by ID.

        Args:
            entry_id: Accounting entry ID

        Returns:
            Dict with entry fields or None if not found
        """
        query = """
            SELECT ae.id, ae.amount, ae.dateImport, t.description, t.dateValue
            FROM tbl_accountingEntry ae
            JOIN tbl_transaction t ON ae.transaction = t.id
            WHERE ae.id = %s
        """
        self.cursor.execute(query, (entry_id,))
        row = self.cursor.fetchone()
        if not row:
            return None
        columns = [desc[0] for desc in self.cursor.description]
        return dict(zip(columns, row))

    def get_available_for_share_transactions(
        self,
        category_ids: list[int],
        start_date=None,
        end_date=None,
        limit: int = 100,
    ) -> list[dict]:
        """
        Get unlinked accounting entries for share transactions.

        Args:
            category_ids: Category IDs to filter
            start_date: Optional start date for t.dateValue filter
            end_date: Optional end date for t.dateValue filter
            limit: Max number of rows

        Returns:
            List of accounting entry dicts
        """
        if not category_ids:
            return []

        placeholders = ",".join(["%s"] * len(category_ids))
        params = list(category_ids)
        date_clause = ""
        if start_date and end_date:
            date_clause = " AND t.dateValue BETWEEN %s AND %s"
            params.extend([start_date, end_date])

        query = f"""
            SELECT ae.id, ae.amount, ae.dateImport, t.description, t.dateValue
            FROM tbl_accountingEntry ae
            JOIN tbl_transaction t ON ae.transaction = t.id
            WHERE ae.id NOT IN (
                SELECT COALESCE(accountingEntry, 0)
                FROM tbl_shareTransaction
                WHERE accountingEntry IS NOT NULL
            )
              AND ae.category IN ({placeholders}){date_clause}
            ORDER BY t.dateValue DESC
            LIMIT %s
        """
        params.append(limit)
        self.cursor.execute(query, params)
        rows = self.cursor.fetchall()
        columns = [desc[0] for desc in self.cursor.description]
        return [dict(zip(columns, row)) for row in rows]
