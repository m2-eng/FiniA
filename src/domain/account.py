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
