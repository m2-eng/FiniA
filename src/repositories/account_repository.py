from domain.account import Account


SQL_COLUMN_HEADER = (
  "SUM(Jan) AS Januar, "
  "SUM(Feb) AS Februar, "
  "SUM(Mrz) AS März, "
  "SUM(Apr) AS April, "
  "SUM(Mai) AS Mai, "
  "SUM(Jun) AS Juni, "
  "SUM(Jul) AS Juli, "
  "SUM(Aug) AS August, "
  "SUM(Sep) AS September, "
  "SUM(Okt) AS Oktober, "
  "SUM(Nov) AS November, "
  "SUM(Dez) AS Dezember, "
  "SUM(Jan+Feb+Mrz+Apr+Mai+Jun+Jul+Aug+Sep+Okt+Nov+Dez) AS Gesamt"
)

MONTH_ABBR = [
    ("Jan", 1),
    ("Feb", 2),
    ("Mrz", 3),
    ("Apr", 4),
    ("Mai", 5),
    ("Jun", 6),
    ("Jul", 7),
    ("Aug", 8),
    ("Sep", 9),
    ("Okt", 10),
    ("Nov", 11),
    ("Dez", 12),
]


def _build_monthly_values(
    date_col: str,
    amount_col: str,
    date_compare: str,
    amount_compare: str | None = None,
) -> str:
    parts = []
    for label, month in MONTH_ABBR:
        amount_clause = f" AND {amount_col} {amount_compare}" if amount_compare else ""
        parts.append(
            "SUM(CASE WHEN MONTH({date_col}) = {month} AND {date_col} {date_compare}{amount_clause} "
            "THEN {amount_col} ELSE 0 END) AS {label}"
            .format(
                date_col=date_col,
                month=month,
                date_compare=date_compare,
                amount_clause=amount_clause,
                amount_col=amount_col,
                label=label,
            )
        )
    return ",".join(parts)

SQL_VALUES_INCOME = _build_monthly_values("t.dateValue", "ae.amount", "<= %s", "> 0")

SQL_VALUES_INCOME_PLANNING = _build_monthly_values("pe.dateValue", "p.amount", "> %s", "> 0")

SQL_VALUES_EXPENSE = _build_monthly_values("t.dateValue", "ae.amount", "<= %s", "< 0")

SQL_VALUES_EXPENSE_PLANNING = _build_monthly_values("pe.dateValue", "p.amount", "> %s", "< 0")

SQL_VALUES_SUMMARY = _build_monthly_values("t.dateValue", "ae.amount", "<= %s")

SQL_VALUES_SUMMARY_PLANNING = _build_monthly_values("pe.dateValue", "p.amount", "> %s")


class AccountRepository:

    def __init__(self, cursor):
        """Initialize with database cursor"""
        self.cursor = cursor

    def _month_params(self, today, count: int = 12) -> list:
        return [today] * count

    def _fetch_report(self, query: str, params: tuple, year: int, account_label: str) -> dict:
        self.cursor.execute(query, params)
        rows = self.cursor.fetchall()
        columns = [col[0] for col in self.cursor.description]
        data = [dict(zip(columns, row)) for row in rows]
        return {"year": year, "account": account_label, "rows": data}

    def get_type_id(self, type_name: str) -> int:
        self.cursor.execute("SELECT id FROM tbl_accountType WHERE type = %s", (type_name,))
        row = self.cursor.fetchone()
        return row[0] if row else 1

    def get_id_by_name(self, name: str):
        self.cursor.execute("SELECT id FROM tbl_account WHERE name = %s", (name,))
        row = self.cursor.fetchone()
        return row[0] if row else None

    def insert(self, account: Account) -> None:
        acc_id = self.get_id_by_name(account.name)
        if acc_id:
            print(f"  Info: Account '{account.name}' already exists. Skipping insertion.")
            return  # Account already exists
        
        type_id = self.get_type_id(account.type_name)
        sql = (
            """INSERT INTO tbl_account
                (name, iban_accountNumber, bic_market, startAmount, dateStart, dateEnd, type, dateImport)
                VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())"""
        )
        self.cursor.execute(
            sql,
            (
                account.name,
                account.iban_accountNumber,
                account.bic_market,
                account.startAmount,
                account.dateStart,
                account.dateEnd,
                type_id,
            ),
        )

    def update_clearing_account(self, name: str, clearing_name: str) -> None:
        acc_id = self.get_id_by_name(name)
        clear_id = self.get_id_by_name(clearing_name)
        if acc_id and clear_id:
            self.cursor.execute(
                "UPDATE tbl_account SET clearingAccount = %s WHERE id = %s",
                (clear_id, acc_id),
            )

    def get_account_income(self, year: int, account_name: str):
        from datetime import date
        today = date.today()

        # finding: The string can be simplified by extracting the substring, e.g. column names. The substring can be reused in other queries.
        query = f"""
            SELECT
                cat AS Kategorie, 
                {SQL_COLUMN_HEADER}
            FROM (
                -- Actual transactions up to today
                SELECT
                    view_categoryFullname.fullname AS cat,
                    {SQL_VALUES_INCOME}
                FROM tbl_accountingEntry ae
                    INNER JOIN tbl_transaction t ON ae.transaction = t.id
                    INNER JOIN tbl_account ON tbl_account.id = t.account
                    LEFT JOIN view_categoryFullname ON view_categoryFullname.id = ae.category
                WHERE YEAR(t.dateValue) = %s AND tbl_account.name = %s
                GROUP BY view_categoryFullname.fullname
                UNION ALL
                -- Planning entries after today
                SELECT
                    view_categoryFullname.fullname AS cat,
                    {SQL_VALUES_INCOME_PLANNING}
                FROM tbl_planning p
                    JOIN tbl_planningEntry pe ON pe.planning = p.id
                    INNER JOIN tbl_account ON tbl_account.id = p.account
                    LEFT JOIN view_categoryFullname ON view_categoryFullname.id = p.category
                WHERE YEAR(pe.dateValue) = %s AND tbl_account.name = %s
                GROUP BY view_categoryFullname.fullname
                ) combined
                GROUP BY cat
                HAVING Gesamt > 0
                ORDER BY cat ASC
            """
        
        month_params = self._month_params(today)
        params = tuple(month_params + [year, account_name] + month_params + [year, account_name])
        return self._fetch_report(query, params, year, account_name)

    def get_account_expenses(self, year: int, account_name: str):
        from datetime import date
        today = date.today()

        query = f"""
            SELECT
            cat AS Kategorie, 
            {SQL_COLUMN_HEADER}
            FROM (
            -- Actual transactions up to today
            SELECT
                view_categoryFullname.fullname AS cat,
                {SQL_VALUES_EXPENSE}
            FROM tbl_accountingEntry ae
                INNER JOIN tbl_transaction t ON ae.transaction = t.id
                INNER JOIN tbl_account ON tbl_account.id = t.account
                LEFT JOIN view_categoryFullname ON view_categoryFullname.id = ae.category
            WHERE YEAR(t.dateValue) = %s AND tbl_account.name = %s
            GROUP BY view_categoryFullname.fullname
            UNION ALL
            -- Planning entries after today
            SELECT
                view_categoryFullname.fullname AS cat,
                {SQL_VALUES_EXPENSE_PLANNING}
            FROM tbl_planning p
                JOIN tbl_planningEntry pe ON pe.planning = p.id
                INNER JOIN tbl_account ON tbl_account.id = p.account
                LEFT JOIN view_categoryFullname ON view_categoryFullname.id = p.category
            WHERE YEAR(pe.dateValue) = %s AND tbl_account.name = %s
            GROUP BY view_categoryFullname.fullname
            ) combined
            GROUP BY cat
            HAVING Gesamt < 0
            ORDER BY cat ASC
        """
        
        month_params = self._month_params(today)
        params = tuple(month_params + [year, account_name] + month_params + [year, account_name])
        return self._fetch_report(query, params, year, account_name)

    def get_account_summary(self, year: int, account_name: str):
        from datetime import date
        today = date.today()

        query = f"""
        SELECT
            'Haben' AS Kategorie,
            {SQL_COLUMN_HEADER}
        FROM (
            SELECT
                {SQL_VALUES_INCOME}
            FROM tbl_accountingEntry ae
                INNER JOIN tbl_transaction t ON ae.transaction = t.id
                INNER JOIN tbl_account ON tbl_account.id = t.account
            WHERE YEAR(t.dateValue) = %s AND tbl_account.name = %s
            UNION ALL
            SELECT
                {SQL_VALUES_INCOME_PLANNING}
            FROM tbl_planning p
                JOIN tbl_planningEntry pe ON pe.planning = p.id
                INNER JOIN tbl_account ON tbl_account.id = p.account
            WHERE YEAR(pe.dateValue) = %s AND tbl_account.name = %s
            ) haben_combined
            UNION ALL
            SELECT
                'Soll' AS Kategorie,
                {SQL_COLUMN_HEADER}
            FROM (
            SELECT
                {SQL_VALUES_EXPENSE}
            FROM tbl_accountingEntry ae
                INNER JOIN tbl_transaction t ON ae.transaction = t.id
                INNER JOIN tbl_account ON tbl_account.id = t.account
            WHERE YEAR(t.dateValue) = %s AND tbl_account.name = %s
            UNION ALL
            SELECT
                {SQL_VALUES_EXPENSE_PLANNING}
            FROM tbl_planning p
                JOIN tbl_planningEntry pe ON pe.planning = p.id
                INNER JOIN tbl_account ON tbl_account.id = p.account
            WHERE YEAR(pe.dateValue) = %s AND tbl_account.name = %s
            ) soll_combined
            UNION ALL
            SELECT
                'Gesamt' AS Kategorie,
                {SQL_COLUMN_HEADER}
            FROM (
            SELECT
                {SQL_VALUES_SUMMARY}
            FROM tbl_accountingEntry ae
                INNER JOIN tbl_transaction t ON ae.transaction = t.id
                INNER JOIN tbl_account ON tbl_account.id = t.account
            WHERE YEAR(t.dateValue) = %s AND tbl_account.name = %s
            UNION ALL
            SELECT
                {SQL_VALUES_SUMMARY_PLANNING}
            FROM tbl_planning p
                JOIN tbl_planningEntry pe ON pe.planning = p.id
                INNER JOIN tbl_account ON tbl_account.id = p.account
            WHERE YEAR(pe.dateValue) = %s AND tbl_account.name = %s
            ) gesamt_combined
        """

        month_params = self._month_params(today)
        params = tuple(
            month_params + [year, account_name] + month_params + [year, account_name] +  # Haben
            month_params + [year, account_name] + month_params + [year, account_name] +  # Soll
            month_params + [year, account_name] + month_params + [year, account_name]    # Gesamt
        )

        return self._fetch_report(query, params, year, account_name)
    
    def get_all_giro_income(self, year: int):
        from datetime import date
        today = date.today()

        query = f"""
            SELECT
                cat AS Kategorie,
                {SQL_COLUMN_HEADER}
            FROM (
            -- Actual transactions up to today
            SELECT
                view_categoryFullname.fullname AS cat,
                {SQL_VALUES_INCOME}
            FROM tbl_accountingEntry ae
                INNER JOIN tbl_transaction t ON ae.transaction = t.id
                INNER JOIN tbl_account ON tbl_account.id = t.account
                INNER JOIN tbl_accountType ON tbl_accountType.id = tbl_account.type
                LEFT JOIN view_categoryFullname ON view_categoryFullname.id = ae.category
            WHERE YEAR(t.dateValue) = %s AND tbl_accountType.type = 'Girokonto'
            GROUP BY view_categoryFullname.fullname
            UNION ALL
            -- Planning entries after today
            SELECT
                view_categoryFullname.fullname AS cat,
                {SQL_VALUES_INCOME_PLANNING}
            FROM tbl_planning p
                JOIN tbl_planningEntry pe ON pe.planning = p.id
                INNER JOIN tbl_account ON tbl_account.id = p.account
                INNER JOIN tbl_accountType ON tbl_accountType.id = tbl_account.type
                LEFT JOIN view_categoryFullname ON view_categoryFullname.id = p.category
            WHERE YEAR(pe.dateValue) = %s AND tbl_accountType.type = 'Girokonto'
            GROUP BY view_categoryFullname.fullname
            ) combined
            GROUP BY cat
            HAVING Gesamt > 0
            ORDER BY cat ASC
        """
        
        month_params = self._month_params(today)
        params = tuple(month_params + [year] + month_params + [year])
        return self._fetch_report(query, params, year, "Alle Girokonten")

    def get_all_giro_expense(self, year: int):
        from datetime import date
        today = date.today()

        query = f"""
            SELECT
            cat AS Kategorie, 
            {SQL_COLUMN_HEADER}
            FROM (
            -- Actual transactions up to today
            SELECT
                view_categoryFullname.fullname AS cat,
                {SQL_VALUES_EXPENSE}
            FROM tbl_accountingEntry ae
                INNER JOIN tbl_transaction t ON ae.transaction = t.id
                INNER JOIN tbl_account ON tbl_account.id = t.account
                INNER JOIN tbl_accountType ON tbl_accountType.id = tbl_account.type
                LEFT JOIN view_categoryFullname ON view_categoryFullname.id = ae.category
            WHERE YEAR(t.dateValue) = %s AND tbl_accountType.type = 'Girokonto'
            GROUP BY view_categoryFullname.fullname
            UNION ALL
            -- Planning entries after today
            SELECT
                view_categoryFullname.fullname AS cat,
                {SQL_VALUES_EXPENSE_PLANNING}
            FROM tbl_planning p
                JOIN tbl_planningEntry pe ON pe.planning = p.id
                INNER JOIN tbl_account ON tbl_account.id = p.account
                INNER JOIN tbl_accountType ON tbl_accountType.id = tbl_account.type
                LEFT JOIN view_categoryFullname ON view_categoryFullname.id = p.category
            WHERE YEAR(pe.dateValue) = %s AND tbl_accountType.type = 'Girokonto'
            GROUP BY view_categoryFullname.fullname
            ) combined
            GROUP BY cat
            HAVING Gesamt < 0
            ORDER BY cat ASC
        """
        
        month_params = self._month_params(today)
        params = tuple(month_params + [year] + month_params + [year])
        return self._fetch_report(query, params, year, "Alle Girokonten")

    def get_all_giro_summary(self, year: int):
        from datetime import date
        today = date.today()

        query = f"""
            -- Haben row (income: positive amounts)
            SELECT 'Haben' AS Kategorie,
                {SQL_COLUMN_HEADER}
            FROM (
            SELECT
                {SQL_VALUES_INCOME}
            FROM tbl_accountingEntry ae
                INNER JOIN tbl_transaction t ON ae.transaction = t.id
                INNER JOIN tbl_account ON tbl_account.id = t.account
                INNER JOIN tbl_accountType ON tbl_accountType.id = tbl_account.type
            WHERE YEAR(t.dateValue) = %s AND tbl_accountType.type = 'Girokonto'
            UNION ALL
            SELECT
                {SQL_VALUES_INCOME_PLANNING}
            FROM tbl_planning p
                JOIN tbl_planningEntry pe ON pe.planning = p.id
                INNER JOIN tbl_account ON tbl_account.id = p.account
                INNER JOIN tbl_accountType ON tbl_accountType.id = tbl_account.type
            WHERE YEAR(pe.dateValue) = %s AND tbl_accountType.type = 'Girokonto'
            ) haben_combined
            UNION ALL
            -- Soll row (expenses: negative amounts)
            SELECT 'Soll' AS Kategorie,
            {SQL_COLUMN_HEADER}
            FROM (
            SELECT
                {SQL_VALUES_EXPENSE}
            FROM tbl_accountingEntry ae
                INNER JOIN tbl_transaction t ON ae.transaction = t.id
                INNER JOIN tbl_account ON tbl_account.id = t.account
                INNER JOIN tbl_accountType ON tbl_accountType.id = tbl_account.type
            WHERE YEAR(t.dateValue) = %s AND tbl_accountType.type = 'Girokonto'
            UNION ALL
            SELECT
                {SQL_VALUES_EXPENSE_PLANNING}
            FROM tbl_planning p
                JOIN tbl_planningEntry pe ON pe.planning = p.id
                INNER JOIN tbl_account ON tbl_account.id = p.account
                INNER JOIN tbl_accountType ON tbl_accountType.id = tbl_account.type
            WHERE YEAR(pe.dateValue) = %s AND tbl_accountType.type = 'Girokonto'
            ) soll_combined
            UNION ALL
            -- Gesamt row (net: all amounts)
            SELECT 'Gesamt' AS Kategorie,
            {SQL_COLUMN_HEADER}
            FROM (
            SELECT
                {SQL_VALUES_SUMMARY}
            FROM tbl_accountingEntry ae
                INNER JOIN tbl_transaction t ON ae.transaction = t.id
                INNER JOIN tbl_account ON tbl_account.id = t.account
                INNER JOIN tbl_accountType ON tbl_accountType.id = tbl_account.type
            WHERE YEAR(t.dateValue) = %s AND tbl_accountType.type = 'Girokonto'
            UNION ALL
            SELECT
                {SQL_VALUES_SUMMARY_PLANNING}
            FROM tbl_planning p
                JOIN tbl_planningEntry pe ON pe.planning = p.id
                INNER JOIN tbl_account ON tbl_account.id = p.account
                INNER JOIN tbl_accountType ON tbl_accountType.id = tbl_account.type
            WHERE YEAR(pe.dateValue) = %s AND tbl_accountType.type = 'Girokonto'
            ) gesamt_combined
        """

        month_params = self._month_params(today)
        params = tuple(
            month_params + [year] + month_params + [year] +  # Haben
            month_params + [year] + month_params + [year] +  # Soll
            month_params + [year] + month_params + [year]    # Gesamt
        )

        return self._fetch_report(query, params, year, "Alle Girokonten")

    def get_all_loans_income(self, year: int):
        from datetime import date
        today = date.today()

        query = f"""
            SELECT
            cat AS Kategorie, 
            {SQL_COLUMN_HEADER}
            FROM (
            -- Actual transactions up to today
            SELECT
                view_categoryFullname.fullname AS cat,
                {SQL_VALUES_INCOME}
            FROM tbl_accountingEntry ae
                INNER JOIN tbl_transaction t ON ae.transaction = t.id
                INNER JOIN tbl_account ON tbl_account.id = t.account
                INNER JOIN tbl_accountType ON tbl_accountType.id = tbl_account.type
                LEFT JOIN view_categoryFullname ON view_categoryFullname.id = ae.category
            WHERE YEAR(t.dateValue) = %s AND tbl_accountType.type = 'Darlehen'
            GROUP BY view_categoryFullname.fullname
            UNION ALL
            -- Planning entries after today
            SELECT
                view_categoryFullname.fullname AS cat,
                {SQL_VALUES_INCOME_PLANNING}
            FROM tbl_planning p
                JOIN tbl_planningEntry pe ON pe.planning = p.id
                INNER JOIN tbl_account ON tbl_account.id = p.account
                INNER JOIN tbl_accountType ON tbl_accountType.id = tbl_account.type
                LEFT JOIN view_categoryFullname ON view_categoryFullname.id = p.category
            WHERE YEAR(pe.dateValue) = %s AND tbl_accountType.type = 'Darlehen'
            GROUP BY view_categoryFullname.fullname
            ) combined
            GROUP BY cat
            HAVING Gesamt > 0
            ORDER BY cat ASC
        """
        
        month_params = self._month_params(today)
        params = tuple(month_params + [year] + month_params + [year])
        return self._fetch_report(query, params, year, "Alle Darlehenskonten")

    def get_all_loans_expense(self, year: int):
        from datetime import date
        today = date.today()

        query = f"""
            SELECT
                cat AS Kategorie, 
                {SQL_COLUMN_HEADER}
            FROM (
            -- Actual transactions up to today
            SELECT
                view_categoryFullname.fullname AS cat,
                {SQL_VALUES_EXPENSE}
            FROM tbl_accountingEntry ae
                INNER JOIN tbl_transaction t ON ae.transaction = t.id
                INNER JOIN tbl_account ON tbl_account.id = t.account
                INNER JOIN tbl_accountType ON tbl_accountType.id = tbl_account.type
                LEFT JOIN view_categoryFullname ON view_categoryFullname.id = ae.category
            WHERE YEAR(t.dateValue) = %s AND tbl_accountType.type = 'Darlehen'
            GROUP BY view_categoryFullname.fullname
            UNION ALL
            -- Planning entries after today
            SELECT
                view_categoryFullname.fullname AS cat,
                {SQL_VALUES_EXPENSE_PLANNING}
            FROM tbl_planning p
                JOIN tbl_planningEntry pe ON pe.planning = p.id
                INNER JOIN tbl_account ON tbl_account.id = p.account
                INNER JOIN tbl_accountType ON tbl_accountType.id = tbl_account.type
                LEFT JOIN view_categoryFullname ON view_categoryFullname.id = p.category
            WHERE YEAR(pe.dateValue) = %s AND tbl_accountType.type = 'Darlehen'
            GROUP BY view_categoryFullname.fullname
            ) combined
            GROUP BY cat
            HAVING Gesamt < 0
            ORDER BY cat ASC
        """
        
        month_params = self._month_params(today)
        params = tuple(month_params + [year] + month_params + [year])
        return self._fetch_report(query, params, year, "Alle Darlehenskonten")

    def get_all_loans_summary(self, year: int):
        from datetime import date
        today = date.today()

        query = f"""
            -- Haben row (income: positive amounts)
            SELECT 'Haben' AS Kategorie,
            {SQL_COLUMN_HEADER}
            FROM (
            SELECT
                {SQL_VALUES_INCOME}
            FROM tbl_accountingEntry ae
                INNER JOIN tbl_transaction t ON ae.transaction = t.id
                INNER JOIN tbl_account ON tbl_account.id = t.account
                INNER JOIN tbl_accountType ON tbl_accountType.id = tbl_account.type
            WHERE YEAR(t.dateValue) = %s AND tbl_accountType.type = 'Darlehen'
            UNION ALL
            SELECT
                {SQL_VALUES_INCOME_PLANNING}
            FROM tbl_planning p
                JOIN tbl_planningEntry pe ON pe.planning = p.id
                INNER JOIN tbl_account ON tbl_account.id = p.account
                INNER JOIN tbl_accountType ON tbl_accountType.id = tbl_account.type
            WHERE YEAR(pe.dateValue) = %s AND tbl_accountType.type = 'Darlehen'
            ) haben_combined
            UNION ALL
            -- Soll row (expenses: negative amounts)
            SELECT 'Soll' AS Kategorie,
            {SQL_COLUMN_HEADER}
            FROM (
            SELECT
                {SQL_VALUES_EXPENSE}
            FROM tbl_accountingEntry ae
                INNER JOIN tbl_transaction t ON ae.transaction = t.id
                INNER JOIN tbl_account ON tbl_account.id = t.account
                INNER JOIN tbl_accountType ON tbl_accountType.id = tbl_account.type
            WHERE YEAR(t.dateValue) = %s AND tbl_accountType.type = 'Darlehen'
            UNION ALL
            SELECT
                {SQL_VALUES_EXPENSE_PLANNING}
            FROM tbl_planning p
                JOIN tbl_planningEntry pe ON pe.planning = p.id
                INNER JOIN tbl_account ON tbl_account.id = p.account
                INNER JOIN tbl_accountType ON tbl_accountType.id = tbl_account.type
            WHERE YEAR(pe.dateValue) = %s AND tbl_accountType.type = 'Darlehen'
            ) soll_combined
            UNION ALL
            -- Gesamt row (net: all amounts)
            SELECT 'Gesamt' AS Kategorie,
            {SQL_COLUMN_HEADER}
            FROM (
            SELECT
                {SQL_VALUES_SUMMARY}
            FROM tbl_accountingEntry ae
                INNER JOIN tbl_transaction t ON ae.transaction = t.id
                INNER JOIN tbl_account ON tbl_account.id = t.account
                INNER JOIN tbl_accountType ON tbl_accountType.id = tbl_account.type
            WHERE YEAR(t.dateValue) = %s AND tbl_accountType.type = 'Darlehen'
            UNION ALL
            SELECT
                {SQL_VALUES_SUMMARY_PLANNING}
            FROM tbl_planning p
                JOIN tbl_planningEntry pe ON pe.planning = p.id
                INNER JOIN tbl_account ON tbl_account.id = p.account
                INNER JOIN tbl_accountType ON tbl_accountType.id = tbl_account.type
            WHERE YEAR(pe.dateValue) = %s AND tbl_accountType.type = 'Darlehen'
            ) gesamt_combined
        """

        month_params = self._month_params(today)
        params = tuple(
            month_params + [year] + month_params + [year] +  # Haben
            month_params + [year] + month_params + [year] +  # Soll
            month_params + [year] + month_params + [year]    # Gesamt
        )

        return self._fetch_report(query, params, year, "Alle Darlehenskonten")

    def get_all_accounts_income(self, year: int):
        from datetime import date
        today = date.today()

        query = f"""
            SELECT
            cat AS Kategorie, 
            {SQL_COLUMN_HEADER}
            FROM (
            -- Actual transactions up to today
            SELECT
                view_categoryFullname.fullname AS cat,
                {SQL_VALUES_INCOME}
            FROM tbl_accountingEntry ae
                INNER JOIN tbl_transaction t ON ae.transaction = t.id
                INNER JOIN tbl_account ON tbl_account.id = t.account
                INNER JOIN tbl_accountType ON tbl_accountType.id = tbl_account.type
                LEFT JOIN view_categoryFullname ON view_categoryFullname.id = ae.category
            WHERE YEAR(t.dateValue) = %s AND tbl_accountType.type IN ('Girokonto', 'Darlehen')
            GROUP BY view_categoryFullname.fullname
            UNION ALL
            -- Planning entries after today
            SELECT
                view_categoryFullname.fullname AS cat,
                {SQL_VALUES_INCOME_PLANNING}
            FROM tbl_planning p
                JOIN tbl_planningEntry pe ON pe.planning = p.id
                INNER JOIN tbl_account ON tbl_account.id = p.account
                INNER JOIN tbl_accountType ON tbl_accountType.id = tbl_account.type
                LEFT JOIN view_categoryFullname ON view_categoryFullname.id = p.category
            WHERE YEAR(pe.dateValue) = %s AND tbl_accountType.type IN ('Girokonto', 'Darlehen')
            GROUP BY view_categoryFullname.fullname
            ) combined
            GROUP BY cat
            HAVING Gesamt > 0
            ORDER BY cat ASC
        """
        
        month_params = self._month_params(today)
        params = tuple(month_params + [year] + month_params + [year])
        return self._fetch_report(query, params, year, "Alle Darlehens- und Girokonten")

    def get_all_accounts_expense(self, year: int):#
        from datetime import date
        today = date.today()

        query = f"""
            SELECT
            cat AS Kategorie, 
            {SQL_COLUMN_HEADER}
            FROM (
            -- Actual transactions up to today
            SELECT
                view_categoryFullname.fullname AS cat,
                {SQL_VALUES_EXPENSE}
            FROM tbl_accountingEntry ae
                INNER JOIN tbl_transaction t ON ae.transaction = t.id
                INNER JOIN tbl_account ON tbl_account.id = t.account
                INNER JOIN tbl_accountType ON tbl_accountType.id = tbl_account.type
                LEFT JOIN view_categoryFullname ON view_categoryFullname.id = ae.category
            WHERE YEAR(t.dateValue) = %s AND tbl_accountType.type IN ('Girokonto', 'Darlehen')
            GROUP BY view_categoryFullname.fullname
            UNION ALL
            -- Planning entries after today
            SELECT
                view_categoryFullname.fullname AS cat,
                {SQL_VALUES_EXPENSE_PLANNING}
            FROM tbl_planning p
                JOIN tbl_planningEntry pe ON pe.planning = p.id
                INNER JOIN tbl_account ON tbl_account.id = p.account
                INNER JOIN tbl_accountType ON tbl_accountType.id = tbl_account.type
                LEFT JOIN view_categoryFullname ON view_categoryFullname.id = p.category
            WHERE YEAR(pe.dateValue) = %s AND tbl_accountType.type IN ('Girokonto', 'Darlehen')
            GROUP BY view_categoryFullname.fullname
            ) combined
            GROUP BY cat
            HAVING Gesamt < 0
            ORDER BY cat ASC
        """
        
        month_params = self._month_params(today)
        params = tuple(month_params + [year] + month_params + [year])
        return self._fetch_report(query, params, year, "Alle Darlehens- und Girokonten")

    def get_all_accounts_summary(self, year: int):
        from datetime import date
        today = date.today()

        query = f"""
            -- Haben row (income: positive amounts)
            SELECT 'Haben' AS Kategorie,
            {SQL_COLUMN_HEADER}
            FROM (
            SELECT
                {SQL_VALUES_INCOME}
            FROM tbl_accountingEntry ae
                INNER JOIN tbl_transaction t ON ae.transaction = t.id
                INNER JOIN tbl_account ON tbl_account.id = t.account
                INNER JOIN tbl_accountType ON tbl_accountType.id = tbl_account.type
            WHERE YEAR(t.dateValue) = %s AND tbl_accountType.type IN ('Girokonto', 'Darlehen')
            UNION ALL
            SELECT
                {SQL_VALUES_INCOME_PLANNING}
            FROM tbl_planning p
                JOIN tbl_planningEntry pe ON pe.planning = p.id
                INNER JOIN tbl_account ON tbl_account.id = p.account
                INNER JOIN tbl_accountType ON tbl_accountType.id = tbl_account.type
            WHERE YEAR(pe.dateValue) = %s AND tbl_accountType.type IN ('Girokonto', 'Darlehen')
            ) haben_combined
            UNION ALL
            -- Soll row (expenses: negative amounts)
            SELECT 'Soll' AS Kategorie,
            {SQL_COLUMN_HEADER}
            FROM (
            SELECT
                {SQL_VALUES_EXPENSE}
            FROM tbl_accountingEntry ae
                INNER JOIN tbl_transaction t ON ae.transaction = t.id
                INNER JOIN tbl_account ON tbl_account.id = t.account
                INNER JOIN tbl_accountType ON tbl_accountType.id = tbl_account.type
            WHERE YEAR(t.dateValue) = %s AND tbl_accountType.type IN ('Girokonto', 'Darlehen')
            UNION ALL
            SELECT
                {SQL_VALUES_EXPENSE_PLANNING}
            FROM tbl_planning p
                JOIN tbl_planningEntry pe ON pe.planning = p.id
                INNER JOIN tbl_account ON tbl_account.id = p.account
                INNER JOIN tbl_accountType ON tbl_accountType.id = tbl_account.type
            WHERE YEAR(pe.dateValue) = %s AND tbl_accountType.type IN ('Girokonto', 'Darlehen')
            ) soll_combined
            UNION ALL
            -- Gesamt row (net: all amounts)
            SELECT 'Gesamt' AS Kategorie,
            {SQL_COLUMN_HEADER}
            FROM (
            SELECT
                {SQL_VALUES_SUMMARY}
            FROM tbl_accountingEntry ae
                INNER JOIN tbl_transaction t ON ae.transaction = t.id
                INNER JOIN tbl_account ON tbl_account.id = t.account
                INNER JOIN tbl_accountType ON tbl_accountType.id = tbl_account.type
            WHERE YEAR(t.dateValue) = %s AND tbl_accountType.type IN ('Girokonto', 'Darlehen')
            UNION ALL
            SELECT
                {SQL_VALUES_SUMMARY_PLANNING}
            FROM tbl_planning p
                JOIN tbl_planningEntry pe ON pe.planning = p.id
                INNER JOIN tbl_account ON tbl_account.id = p.account
                INNER JOIN tbl_accountType ON tbl_accountType.id = tbl_account.type
            WHERE YEAR(pe.dateValue) = %s AND tbl_accountType.type IN ('Girokonto', 'Darlehen')
            ) gesamt_combined
        """

        month_params = self._month_params(today)
        params = tuple(
            month_params + [year] + month_params + [year] +  # Haben
            month_params + [year] + month_params + [year] +  # Soll
            month_params + [year] + month_params + [year]    # Gesamt
        )

        return self._fetch_report(query, params, year, "Alle Darlehens- und Girokonten")

    def get_account_list(self, account_type: str = None):

        if account_type is None:
            SQL_ADDITIONAL = ""
        else:
            SQL_ADDITIONAL = "WHERE tbl_accountType.type = %s"

        query = f"""
            SELECT
                tbl_account.name AS name
            FROM tbl_account
            LEFT JOIN tbl_accountType ON tbl_accountType.id = tbl_account.type
            {SQL_ADDITIONAL}
            ORDER BY name ASC
        """
        if account_type is None:
            self.cursor.execute(query)
        else:
            self.cursor.execute(query, (account_type,))
        rows = self.cursor.fetchall()
            
        accounts = [row[0] for row in rows]
            
        return {"accounts": accounts}

    def get_count_accounts(self, search_pattern: str = None) -> int:
        if search_pattern is None:
            search_pattern = '%'
        else:
            search_pattern = f'%{search_pattern}%'

        count_query = """
            SELECT COUNT(DISTINCT tbl_account.id)
            FROM tbl_account
            LEFT JOIN tbl_accountType ON tbl_accountType.id = tbl_account.type
            WHERE tbl_account.name LIKE %s OR tbl_account.iban_accountNumber LIKE %s
        """
        self.cursor.execute(count_query, (search_pattern, search_pattern))
        return self.cursor.fetchone()[0]
    
    def get_accounts_paginated(self, page: int, page_size: int, search_pattern: str = None):
        if search_pattern is None:
            search_pattern = '%'
        else:
            search_pattern = f'%{search_pattern}%'

        offset = (page - 1) * page_size
        query = """
            SELECT 
                tbl_account.id,
                tbl_account.name,
                tbl_account.iban_accountNumber,
                tbl_account.bic_market,
                tbl_account.startAmount,
                tbl_account.dateStart,
                tbl_account.dateEnd,
                tbl_account.type,
                tbl_accountType.type AS type_name,
                tbl_account.clearingAccount
            FROM tbl_account
            LEFT JOIN tbl_accountType ON tbl_accountType.id = tbl_account.type
            WHERE tbl_account.name LIKE %s OR tbl_account.iban_accountNumber LIKE %s
            ORDER BY tbl_account.name ASC
            LIMIT %s OFFSET %s
        """
        
        self.cursor.execute(query, (search_pattern, search_pattern, page_size, offset))
        return self.cursor.fetchall()
    
    def get_account_types(self):
        query = "SELECT id, type FROM tbl_accountType ORDER BY type ASC"
        self.cursor.execute(query)
        rows = self.cursor.fetchall()
        
        types = [{"id": row[0], "type": row[1]} for row in rows]
        return {"types": types}
    
    def get_import_formats(self):
        query = "SELECT id, type FROM tbl_accountImportFormat ORDER BY type ASC"
        self.cursor.execute(query)
        rows = self.cursor.fetchall()
        
        formats = [{"id": row[0], "type": row[1]} for row in rows]
        return {"formats": formats}
    
    def get_account_by_id(self, account_id: int):
        account_query = """
            SELECT 
                tbl_account.id,
                tbl_account.name,
                tbl_account.iban_accountNumber,
                tbl_account.bic_market,
                tbl_account.startAmount,
                tbl_account.dateStart,
                tbl_account.dateEnd,
                tbl_account.type,
                tbl_accountType.type AS type_name,
                tbl_account.clearingAccount
            FROM tbl_account
            LEFT JOIN tbl_accountType ON tbl_accountType.id = tbl_account.type
            WHERE tbl_account.id = %s
        """
        
        self.cursor.execute(account_query, (account_id,))
        return self.cursor.fetchone()
    
    def get_import_settings(self, account_id: int):
        import_query = """
            SELECT 
                tbl_accountImportFormat.id,
                tbl_accountImportPath.path
            FROM tbl_accountImportPath
            LEFT JOIN tbl_accountImportFormat ON tbl_accountImportFormat.id = tbl_accountImportPath.importFormat
            WHERE tbl_accountImportPath.account = %s
            LIMIT 1
        """
        
        self.cursor.execute(import_query, (account_id,))
        return self.cursor.fetchone()
    
    def update_account(self, 
                       name: str, 
                       iban: str, 
                       bic: str,
                       account_type: int, 
                       start_amount: float, 
                       date_start: str, 
                       date_end: str, 
                       clearing_account: bool,
                       account_id: int):
        update_query = """
            UPDATE tbl_account
            SET name = %s,
                iban_accountNumber = %s,
                bic_market = %s,
                type = %s,
                startAmount = %s,
                dateStart = %s,
                dateEnd = %s,
                clearingAccount = %s
            WHERE id = %s
        """
            
        self.cursor.execute(update_query, (
            name,
            iban,
            bic,
            account_type,
            start_amount,
            date_start if date_start else None,
            date_end if date_end else None,
            clearing_account,
            account_id
        ))

        return self.cursor.rowcount

    def get_import_path_by_account_id(self, account_id: int):
        check_query = "SELECT id FROM tbl_accountImportPath WHERE account = %s"
        self.cursor.execute(check_query, (account_id,))
        return self.cursor.fetchone()
    
    def update_import_path(self, path: str, import_format_id: int, account_id: int):
        path_update_query = """
                    UPDATE tbl_accountImportPath
                    SET path = %s, importFormat = %s
                    WHERE account = %s
                """
        self.cursor.execute(path_update_query, (path, import_format_id, account_id))
        return self.cursor.rowcount
    
    def insert_import_path(self, path: str, import_format_id: int, account_id: int):
        path_insert_query = """
                    INSERT INTO tbl_accountImportPath (dateImport, path, account, importFormat)
                    VALUES (NOW(), %s, %s, %s)
                """
        self.cursor.execute(path_insert_query, (path, account_id, import_format_id))
        return self.cursor.rowcount
    
    def delete_import_path_by_account_id(self, account_id: int):
        delete_paths_query = "DELETE FROM tbl_accountImportPath WHERE account = %s"
        self.cursor.execute(delete_paths_query, (account_id,))
        return self.cursor.rowcount

    def delete_account_by_account_id(self, account_id: int):
        delete_query = "DELETE FROM tbl_account WHERE id = %s"
        self.cursor.execute(delete_query, (account_id,))
        return self.cursor.rowcount
        