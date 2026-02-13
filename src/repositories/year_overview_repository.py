#
# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (c) 2026 m2-eng
# Author: m2-eng
# Co-Author: GitHub Copilot
# License: GNU Affero General Public License v3.0 (AGPL-3.0-only)
# Purpose: Module for year overview repository.
#
from __future__ import annotations

from datetime import date
from typing import Tuple

from repositories.base import BaseRepository
from repositories.error_handling import execute_fetchall_with_retry, handle_repository_errors

MONTH_NAMES = [
    "Januar",
    "Februar",
    "März",
    "April",
    "Mai",
    "Juni",
    "Juli",
    "August",
    "September",
    "Oktober",
    "November",
    "Dezember",
]


def _account_balance_month_expr(label: str, comparator: str) -> str:
    return f"""
              (
                COALESCE((SELECT SUM(ae.amount)
                          FROM tbl_transaction t2
                          LEFT JOIN tbl_accountingEntry ae ON ae.transaction = t2.id
                          WHERE t2.account = a.id AND t2.dateValue <= %s
                            AND EXTRACT(YEAR_MONTH FROM t2.dateValue) {comparator} %s), 0)
              + COALESCE((SELECT SUM(p.amount)
                          FROM tbl_planning p
                          JOIN tbl_planningEntry pe ON pe.planning = p.id
                          WHERE p.account = a.id AND pe.dateValue > %s
                            AND EXTRACT(YEAR_MONTH FROM pe.dateValue) {comparator} %s), 0)
              + a.startAmount
              ) AS {label}
    """


def _account_balance_delta_month_expr(label: str, comparator: str) -> str:
    return f"""
              (
                COALESCE((SELECT SUM(ae.amount) FROM tbl_transaction t2
                          LEFT JOIN tbl_accountingEntry ae ON ae.transaction = t2.id
                          WHERE t2.account = a.id AND t2.dateValue <= %s
                            AND EXTRACT(YEAR_MONTH FROM t2.dateValue) {comparator} %s), 0)
              + COALESCE((SELECT SUM(p.amount) FROM tbl_planning p
                          JOIN tbl_planningEntry pe ON pe.planning = p.id
                          WHERE p.account = a.id AND pe.dateValue > %s
                            AND EXTRACT(YEAR_MONTH FROM pe.dateValue) {comparator} %s), 0)
              ) AS {label}
    """


def _extend_month_params(params: list, today: date, month_values: list[int]) -> None:
    for month_value in month_values:
        params.extend([today, month_value, today, month_value])


class YearOverviewRepository(BaseRepository):
    @handle_repository_errors("fetch data")
    def _fetch_dicts(self, query: str, params: Tuple) -> list[dict]:
        rows, description = execute_fetchall_with_retry(self.cursor, query, params, retries=1)
        columns = [col[0] for col in description]
        return [dict(zip(columns, row)) for row in rows]

    def get_available_years(self) -> list[int]:
        query = """
            SELECT DISTINCT YEAR(tbl_transaction.dateValue) AS year
            FROM tbl_transaction
            WHERE YEAR(tbl_transaction.dateValue) <= (YEAR(CURDATE())+1)
            ORDER BY YEAR(tbl_transaction.dateValue) DESC
        """
        self.cursor.execute(query)
        rows = self.cursor.fetchall()
        return [row[0] for row in rows]

    def get_account_balances(self, year: int) -> list[dict]:
        today = date.today()
        month_thresholds = [year * 100 + month for month in range(1, 13)]
        year_end_threshold = year * 100 + 12

        month_sql = ",\n".join(
            _account_balance_month_expr(label, "<") for label in MONTH_NAMES
        )

        query = f"""
            SELECT
              a.name AS Konto,
              {month_sql},
              (
                COALESCE((SELECT SUM(ae.amount)
                          FROM tbl_transaction t2
                          LEFT JOIN tbl_accountingEntry ae ON ae.transaction = t2.id
                          WHERE t2.account = a.id
                            AND t2.dateValue <= %s
                            AND EXTRACT(YEAR_MONTH FROM t2.dateValue) <= %s), 0)
              + COALESCE((SELECT SUM(p.amount)
                          FROM tbl_planning p
                          JOIN tbl_planningEntry pe ON pe.planning = p.id
                          WHERE p.account = a.id
                            AND pe.dateValue > %s
                            AND EXTRACT(YEAR_MONTH FROM pe.dateValue) <= %s), 0)
              + a.startAmount
              ) AS Jahresabschluss
            FROM tbl_account a
            WHERE YEAR(a.dateStart) <= %s
              AND (YEAR(a.dateEnd) >= %s OR ISNULL(a.dateEnd))
              AND a.type IN (1)
            ORDER BY Konto ASC
        """

        params = []
        _extend_month_params(params, today, month_thresholds)
        params.extend([today, year_end_threshold, today, year_end_threshold])
        params.extend([year, year])

        return self._fetch_dicts(query, tuple(params))

    def get_account_balances_monthly(self, year: int) -> list[dict]:
        today = date.today()
        month_equals = [year * 100 + month for month in range(1, 13)]

        month_sql = ",\n".join(
            _account_balance_delta_month_expr(label, "=") for label in MONTH_NAMES
        )

        query = f"""
            SELECT
              a.name AS Konto,
              {month_sql},
              (
                COALESCE((SELECT SUM(ae.amount) FROM tbl_transaction t2
                          LEFT JOIN tbl_accountingEntry ae ON ae.transaction = t2.id
                          WHERE t2.account = a.id AND t2.dateValue <= %s AND YEAR(t2.dateValue) = %s), 0)
              + COALESCE((SELECT SUM(p.amount) FROM tbl_planning p
                          JOIN tbl_planningEntry pe ON pe.planning = p.id
                          WHERE p.account = a.id AND pe.dateValue > %s AND YEAR(pe.dateValue) = %s), 0)
              ) AS Jahresbilanz
            FROM tbl_account a
            WHERE YEAR(a.dateStart) <= %s
              AND (YEAR(a.dateEnd) >= %s OR ISNULL(a.dateEnd))
              AND a.type IN (1)
            ORDER BY Konto ASC
        """

        params = []
        _extend_month_params(params, today, month_equals)
        params.extend([today, year, today, year])
        params.extend([year, year])

        return self._fetch_dicts(query, tuple(params))

    def get_investments(self, year: int) -> list[dict]:
        today = date.today()
        month_dates = [f"{year}-{month:02d}-01" for month in range(1, 13)]

        def month_column(label: str, month_date: str) -> str:
            return f"""
            (
              CASE
                WHEN LAST_DAY(%s) <= %s THEN
                  COALESCE((SELECT SUM(ae.amount)
                            FROM tbl_transaction t2
                            LEFT JOIN tbl_accountingEntry ae ON ae.transaction = t2.id
                            WHERE t2.account = tbl_account.id
                              AND t2.dateValue <= LAST_DAY(%s)), 0)
                  + tbl_account.startAmount
                ELSE
                  COALESCE((SELECT SUM(ae.amount)
                            FROM tbl_transaction t2
                            LEFT JOIN tbl_accountingEntry ae ON ae.transaction = t2.id
                            WHERE t2.account = tbl_account.id
                              AND t2.dateValue <= %s), 0)
                  + COALESCE((SELECT SUM(p.amount)
                              FROM tbl_planning p
                              JOIN tbl_planningEntry pe ON pe.planning = p.id
                              WHERE p.account = tbl_account.id
                                AND pe.dateValue > %s
                                AND pe.dateValue <= LAST_DAY(%s)), 0)
                  + tbl_account.startAmount
              END
            ) AS {label}
            """

        month_sql_parts = [
            month_column("Januar", month_dates[0]),
            month_column("Februar", month_dates[1]),
            month_column("März", month_dates[2]),
            month_column("April", month_dates[3]),
            month_column("Mai", month_dates[4]),
            month_column("Juni", month_dates[5]),
            month_column("Juli", month_dates[6]),
            month_column("August", month_dates[7]),
            month_column("September", month_dates[8]),
            month_column("Oktober", month_dates[9]),
            month_column("November", month_dates[10]),
            month_column("Dezember", month_dates[11]),
        ]

        month_sql = ",\n          ".join(month_sql_parts)

        query = f"""
            SELECT
              tbl_account.name AS Konto,
              {month_sql},
              (
                COALESCE((SELECT SUM(ae.amount)
                          FROM tbl_transaction t2
                          LEFT JOIN tbl_accountingEntry ae ON ae.transaction = t2.id
                          WHERE t2.account = tbl_account.id
                            AND t2.dateValue <= %s
                            AND YEAR(t2.dateValue) = %s), 0)
                + COALESCE((SELECT SUM(p.amount)
                            FROM tbl_planning p
                            JOIN tbl_planningEntry pe ON pe.planning = p.id
                            WHERE p.account = tbl_account.id
                              AND pe.dateValue > %s
                              AND YEAR(pe.dateValue) = %s), 0)
              ) AS Jahresbilanz
            FROM tbl_account
            WHERE YEAR(tbl_account.dateStart) <= %s
              AND (YEAR(tbl_account.dateEnd) >= %s OR ISNULL(tbl_account.dateEnd))
              AND tbl_account.type = 5
            ORDER BY Konto ASC
        """

        params = []
        for month_date in month_dates:
            params.extend([month_date, today, month_date, today, today, month_date])

        params.extend([today, year, today, year, year, year])

        return self._fetch_dicts(query, tuple(params))

    def get_loans(self, year: int) -> list[dict]:
        today = date.today()
        month_dates = [f"{year}-{month:02d}-01" for month in range(1, 13)]

        def month_column(label: str, month_date: str) -> str:
            return f"""
            (
              CASE
                WHEN LAST_DAY(%s) <= %s THEN
                  COALESCE((SELECT SUM(ae.amount)
                            FROM tbl_transaction t2
                            LEFT JOIN tbl_accountingEntry ae ON ae.transaction = t2.id
                            WHERE t2.account = tbl_account.id
                              AND t2.dateValue <= LAST_DAY(%s)), 0)
                  + tbl_account.startAmount
                ELSE
                  COALESCE((SELECT SUM(ae.amount)
                            FROM tbl_transaction t2
                            LEFT JOIN tbl_accountingEntry ae ON ae.transaction = t2.id
                            WHERE t2.account = tbl_account.id
                              AND t2.dateValue <= %s), 0)
                  + COALESCE((SELECT SUM(p.amount)
                              FROM tbl_planning p
                              JOIN tbl_planningEntry pe ON pe.planning = p.id
                              WHERE p.account = tbl_account.id
                                AND pe.dateValue > %s
                                AND pe.dateValue <= LAST_DAY(%s)), 0)
                  + tbl_account.startAmount
              END
            ) AS {label}
            """

        month_sql_parts = [
            month_column("Januar", month_dates[0]),
            month_column("Februar", month_dates[1]),
            month_column("März", month_dates[2]),
            month_column("April", month_dates[3]),
            month_column("Mai", month_dates[4]),
            month_column("Juni", month_dates[5]),
            month_column("Juli", month_dates[6]),
            month_column("August", month_dates[7]),
            month_column("September", month_dates[8]),
            month_column("Oktober", month_dates[9]),
            month_column("November", month_dates[10]),
            month_column("Dezember", month_dates[11]),
        ]

        month_sql = ",\n          ".join(month_sql_parts)

        query = f"""
            SELECT
              tbl_account.name AS Konto,
              {month_sql},
              (
                COALESCE((SELECT SUM(ae.amount)
                          FROM tbl_transaction t2
                          LEFT JOIN tbl_accountingEntry ae ON ae.transaction = t2.id
                          WHERE t2.account = tbl_account.id
                            AND t2.dateValue <= %s
                            AND YEAR(t2.dateValue) = %s), 0)
                + COALESCE((SELECT SUM(p.amount)
                            FROM tbl_planning p
                            JOIN tbl_planningEntry pe ON pe.planning = p.id
                            WHERE p.account = tbl_account.id
                              AND pe.dateValue > %s
                              AND YEAR(pe.dateValue) = %s), 0)
              ) AS Jahresbilanz
            FROM tbl_account
            WHERE YEAR(tbl_account.dateStart) <= %s
              AND (YEAR(tbl_account.dateEnd) >= %s OR ISNULL(tbl_account.dateEnd))
              AND tbl_account.type = 3
            ORDER BY Konto ASC
        """

        params = []
        for month_date in month_dates:
            params.extend([month_date, today, month_date, today, today, month_date])

        params.extend([today, year, today, year, year, year])

        return self._fetch_dicts(query, tuple(params))

    def get_securities_overview(self, year: int) -> list[dict]:
        query = """
            SELECT 
                vsms.share_name AS Wertpapier,
                COALESCE(MAX(CASE WHEN MONTH(vsms.month_end_date) = 1 THEN vsms.portfolio_value END), 0) AS Januar,
                COALESCE(MAX(CASE WHEN MONTH(vsms.month_end_date) = 2 THEN vsms.portfolio_value END), 0) AS Februar,
                COALESCE(MAX(CASE WHEN MONTH(vsms.month_end_date) = 3 THEN vsms.portfolio_value END), 0) AS März,
                COALESCE(MAX(CASE WHEN MONTH(vsms.month_end_date) = 4 THEN vsms.portfolio_value END), 0) AS April,
                COALESCE(MAX(CASE WHEN MONTH(vsms.month_end_date) = 5 THEN vsms.portfolio_value END), 0) AS Mai,
                COALESCE(MAX(CASE WHEN MONTH(vsms.month_end_date) = 6 THEN vsms.portfolio_value END), 0) AS Juni,
                COALESCE(MAX(CASE WHEN MONTH(vsms.month_end_date) = 7 THEN vsms.portfolio_value END), 0) AS Juli,
                COALESCE(MAX(CASE WHEN MONTH(vsms.month_end_date) = 8 THEN vsms.portfolio_value END), 0) AS August,
                COALESCE(MAX(CASE WHEN MONTH(vsms.month_end_date) = 9 THEN vsms.portfolio_value END), 0) AS September,
                COALESCE(MAX(CASE WHEN MONTH(vsms.month_end_date) = 10 THEN vsms.portfolio_value END), 0) AS Oktober,
                COALESCE(MAX(CASE WHEN MONTH(vsms.month_end_date) = 11 THEN vsms.portfolio_value END), 0) AS November,
                COALESCE(MAX(CASE WHEN MONTH(vsms.month_end_date) = 12 THEN vsms.portfolio_value END), 0) AS Dezember,
                COALESCE(
                    (SELECT SUM(ae.amount)
                     FROM tbl_shareTransaction st
                     JOIN tbl_accountingEntry ae ON st.accountingEntry = ae.id
                     JOIN tbl_category cat ON ae.category = cat.id
                     JOIN tbl_transaction t ON ae.transaction = t.id
                     WHERE st.share = vsms.share_id
                       AND cat.name = 'Dividende (Wertpapiere)'
                       AND YEAR(t.dateValue) = %s
                    ), 0
                ) AS Dividende
            FROM view_shareMonthlySnapshot vsms
            WHERE YEAR(vsms.month_end_date) = %s
            GROUP BY vsms.share_id, vsms.share_name
            HAVING MAX(vsms.volume) > 0
            ORDER BY vsms.share_name ASC
        """

        params = (year, year)
        return self._fetch_dicts(query, params)

    def get_assets_month_end(self, year: int) -> list[dict]:
        today = date.today()
        month_dates = [f"{year}-{month:02d}-01" for month in range(1, 13)]

        def month_sum_column(label: str, month_date: str, account_type_name: str) -> str:
            return f"""
            (
              CASE
                WHEN LAST_DAY(%s) <= %s THEN
                  COALESCE((SELECT SUM(ae.amount)
                            FROM tbl_transaction t2
                            LEFT JOIN tbl_accountingEntry ae ON ae.transaction = t2.id
                            INNER JOIN tbl_account a ON a.id = t2.account
                            INNER JOIN tbl_accountType at ON at.id = a.type
                            WHERE at.type = %s
                              AND t2.dateValue <= LAST_DAY(%s)
                          ), 0)
                  + COALESCE((SELECT SUM(a.startAmount)
                              FROM tbl_account a
                              INNER JOIN tbl_accountType at ON at.id = a.type
                              WHERE at.type = %s
                            ), 0)
                ELSE
                  COALESCE((SELECT SUM(ae.amount)
                            FROM tbl_transaction t2
                            LEFT JOIN tbl_accountingEntry ae ON ae.transaction = t2.id
                            INNER JOIN tbl_account a ON a.id = t2.account
                            INNER JOIN tbl_accountType at ON at.id = a.type
                            WHERE at.type = %s
                              AND t2.dateValue <= %s
                          ), 0)
                  + COALESCE((SELECT SUM(p.amount)
                              FROM tbl_planning p
                              JOIN tbl_planningEntry pe ON pe.planning = p.id
                              INNER JOIN tbl_account a ON a.id = p.account
                              INNER JOIN tbl_accountType at ON at.id = a.type
                              WHERE at.type = %s
                                AND pe.dateValue > %s
                                AND pe.dateValue <= LAST_DAY(%s)
                            ), 0)
                  + COALESCE((SELECT SUM(a.startAmount)
                              FROM tbl_account a
                              INNER JOIN tbl_accountType at ON at.id = a.type
                              WHERE at.type = %s
                            ), 0)
              END
            ) AS {label}
            """

        giro_month_sql_parts = [
            month_sum_column("Januar", month_dates[0], "Girokonto"),
            month_sum_column("Februar", month_dates[1], "Girokonto"),
            month_sum_column("März", month_dates[2], "Girokonto"),
            month_sum_column("April", month_dates[3], "Girokonto"),
            month_sum_column("Mai", month_dates[4], "Girokonto"),
            month_sum_column("Juni", month_dates[5], "Girokonto"),
            month_sum_column("Juli", month_dates[6], "Girokonto"),
            month_sum_column("August", month_dates[7], "Girokonto"),
            month_sum_column("September", month_dates[8], "Girokonto"),
            month_sum_column("Oktober", month_dates[9], "Girokonto"),
            month_sum_column("November", month_dates[10], "Girokonto"),
            month_sum_column("Dezember", month_dates[11], "Girokonto"),
        ]

        darlehen_month_sql_parts = [
            month_sum_column("Januar", month_dates[0], "Darlehen"),
            month_sum_column("Februar", month_dates[1], "Darlehen"),
            month_sum_column("März", month_dates[2], "Darlehen"),
            month_sum_column("April", month_dates[3], "Darlehen"),
            month_sum_column("Mai", month_dates[4], "Darlehen"),
            month_sum_column("Juni", month_dates[5], "Darlehen"),
            month_sum_column("Juli", month_dates[6], "Darlehen"),
            month_sum_column("August", month_dates[7], "Darlehen"),
            month_sum_column("September", month_dates[8], "Darlehen"),
            month_sum_column("Oktober", month_dates[9], "Darlehen"),
            month_sum_column("November", month_dates[10], "Darlehen"),
            month_sum_column("Dezember", month_dates[11], "Darlehen"),
        ]

        giro_month_sql = ",\n          ".join(giro_month_sql_parts)
        darlehen_month_sql = ",\n          ".join(darlehen_month_sql_parts)

        securities_month_sql = """
            COALESCE(MAX(CASE WHEN MONTH(month_end_date) = 1 THEN portfolio_value_sum END), 0) AS Januar,
            COALESCE(MAX(CASE WHEN MONTH(month_end_date) = 2 THEN portfolio_value_sum END), 0) AS Februar,
            COALESCE(MAX(CASE WHEN MONTH(month_end_date) = 3 THEN portfolio_value_sum END), 0) AS März,
            COALESCE(MAX(CASE WHEN MONTH(month_end_date) = 4 THEN portfolio_value_sum END), 0) AS April,
            COALESCE(MAX(CASE WHEN MONTH(month_end_date) = 5 THEN portfolio_value_sum END), 0) AS Mai,
            COALESCE(MAX(CASE WHEN MONTH(month_end_date) = 6 THEN portfolio_value_sum END), 0) AS Juni,
            COALESCE(MAX(CASE WHEN MONTH(month_end_date) = 7 THEN portfolio_value_sum END), 0) AS Juli,
            COALESCE(MAX(CASE WHEN MONTH(month_end_date) = 8 THEN portfolio_value_sum END), 0) AS August,
            COALESCE(MAX(CASE WHEN MONTH(month_end_date) = 9 THEN portfolio_value_sum END), 0) AS September,
            COALESCE(MAX(CASE WHEN MONTH(month_end_date) = 10 THEN portfolio_value_sum END), 0) AS Oktober,
            COALESCE(MAX(CASE WHEN MONTH(month_end_date) = 11 THEN portfolio_value_sum END), 0) AS November,
            COALESCE(MAX(CASE WHEN MONTH(month_end_date) = 12 THEN portfolio_value_sum END), 0) AS Dezember
        """

        def year_begin_sum_subselect(account_type_name: str) -> str:
            return f"""
              (SELECT
                COALESCE((SELECT SUM(a.startAmount)
                          FROM tbl_account a
                          INNER JOIN tbl_accountType at ON at.id = a.type
                          WHERE at.type = %s), 0)
                + COALESCE((SELECT SUM(ae.amount)
                            FROM tbl_transaction t2
                            LEFT JOIN tbl_accountingEntry ae ON ae.transaction = t2.id
                            INNER JOIN tbl_account a ON a.id = t2.account
                            INNER JOIN tbl_accountType at ON at.id = a.type
                            WHERE at.type = %s
                              AND t2.dateValue < %s), 0))
            """

        def year_end_sum_expr(account_type_name: str) -> str:
            return f"""
            (
              CASE
                WHEN LAST_DAY(%s) <= %s THEN
                  COALESCE((SELECT SUM(ae.amount)
                            FROM tbl_transaction t2
                            LEFT JOIN tbl_accountingEntry ae ON ae.transaction = t2.id
                            INNER JOIN tbl_account a ON a.id = t2.account
                            INNER JOIN tbl_accountType at ON at.id = a.type
                            WHERE at.type = %s
                              AND t2.dateValue <= LAST_DAY(%s)), 0)
                  + COALESCE((SELECT SUM(a.startAmount)
                              FROM tbl_account a
                              INNER JOIN tbl_accountType at ON at.id = a.type
                              WHERE at.type = %s), 0)
                ELSE
                  COALESCE((SELECT SUM(ae.amount)
                            FROM tbl_transaction t2
                            LEFT JOIN tbl_accountingEntry ae ON ae.transaction = t2.id
                            INNER JOIN tbl_account a ON a.id = t2.account
                            INNER JOIN tbl_accountType at ON at.id = a.type
                            WHERE at.type = %s AND t2.dateValue <= %s), 0)
                  + COALESCE((SELECT SUM(p.amount)
                              FROM tbl_planning p
                              JOIN tbl_planningEntry pe ON pe.planning = p.id
                              INNER JOIN tbl_account a ON a.id = p.account
                              INNER JOIN tbl_accountType at ON at.id = a.type
                              WHERE at.type = %s AND pe.dateValue > %s AND YEAR(pe.dateValue) = %s), 0)
                  + COALESCE((SELECT SUM(a.startAmount)
                              FROM tbl_account a
                              INNER JOIN tbl_accountType at ON at.id = a.type
                              WHERE at.type = %s), 0)
              END
            )
            """

        query = f"""
            SELECT 'Kontostand' AS `Vermögen Ende des Monats`,
                   {giro_month_sql},
                   (
                     {year_end_sum_expr('Girokonto')}
                     - {year_begin_sum_subselect('Girokonto')}
                   ) AS Jahresbilanz
            UNION ALL
            SELECT 'Darlehen' AS `Vermögen Ende des Monats`,
                   {darlehen_month_sql},
                   (
                     {year_end_sum_expr('Darlehen')}
                     - {year_begin_sum_subselect('Darlehen')}
                   ) AS Jahresbilanz
            UNION ALL
            SELECT 'Wertpapiere' AS `Vermögen Ende des Monats`,
                   {securities_month_sql},
                   COALESCE(MAX(CASE WHEN MONTH(month_end_date) = 12 THEN portfolio_value_sum END), 0)
                   - COALESCE((SELECT SUM(portfolio_value)
                               FROM view_shareMonthlySnapshot
                               WHERE YEAR(month_end_date) = %s AND MONTH(month_end_date) = 12), 0) AS Jahresbilanz
            FROM (
              SELECT month_end_date, SUM(portfolio_value) AS portfolio_value_sum
              FROM view_shareMonthlySnapshot
              WHERE YEAR(month_end_date) = %s
              GROUP BY month_end_date
            ) s
            """

        params: list = []
        year_first_day = f"{year}-01-01"
        dec_first = f"{year}-12-01"

        for month_date in month_dates:
            params.extend([
                month_date,
                today,
                "Girokonto",
                month_date,
                "Girokonto",
                "Girokonto",
                today,
                "Girokonto",
                today,
                month_date,
                "Girokonto",
            ])

        params.extend([
            dec_first,
            today,
            "Girokonto",
            dec_first,
            "Girokonto",
            "Girokonto",
            today,
            "Girokonto",
            today,
            year,
            "Girokonto",
        ])
        params.extend(["Girokonto", "Girokonto", year_first_day])

        for month_date in month_dates:
            params.extend([
                month_date,
                today,
                "Darlehen",
                month_date,
                "Darlehen",
                "Darlehen",
                today,
                "Darlehen",
                today,
                month_date,
                "Darlehen",
            ])

        params.extend([
            dec_first,
            today,
            "Darlehen",
            dec_first,
            "Darlehen",
            "Darlehen",
            today,
            "Darlehen",
            today,
            year,
            "Darlehen",
        ])
        params.extend(["Darlehen", "Darlehen", year_first_day])

        previous_year = year - 1
        params.extend([previous_year, year])

        return self._fetch_dicts(query, tuple(params))
