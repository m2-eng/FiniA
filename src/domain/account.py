#
# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (c) 2026 m2-eng
# Author: m2-eng
# Co-Author: GitHub Copilot
# License: GNU Affero General Public License v3.0 (AGPL-3.0-only)
# Purpose: Module for account.
#
from dataclasses import dataclass
from datetime import date
from typing import Optional


@dataclass
class Account:
    name: str
    iban_accountNumber: str
    bic_market: str
    startAmount: float = 0.0
    dateStart: Optional[date] = None
    dateEnd: Optional[date] = None
    type_name: str = ""
    clearingAccount: Optional[str] = None
