"""
Pydantic models for API request/response validation
"""

from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, Field
from typing import Optional, List


class AccountData(BaseModel):
    name: str
    iban_accountNumber: str
    bic_market: str
    type: Optional[int] = None
    startAmount: float
    dateStart: str
    dateEnd: Optional[str] = None
    clearingAccount: Optional[int] = None
    importFormat: Optional[int] = None
    importPath: Optional[str] = None


class AccountingEntryUpdate(BaseModel):
    """Request model for updating/creating an accounting entry"""
    id: Optional[int] = None  # None for new entries
    dateImport: datetime
    amount: Decimal
    checked: bool = False
    accountingPlanned: bool = False
    category_name: Optional[str] = None

    class Config:
        from_attributes = True


class RuleTestData(BaseModel):
    """Model for transaction data when testing a rule"""
    description: str
    recipientApplicant: Optional[str] = None
    amount: Optional[str] = None
    iban: Optional[str] = None


class Condition(BaseModel):
    """Single condition in a rule"""
    id: int
    type: str  # contains, equals, startsWith, endsWith, regex, amountRange
    columnName: str  # description, recipientApplicant, amount, iban
    value: Optional[str] = None
    caseSensitive: bool = False
    minAmount: Optional[float] = None
    maxAmount: Optional[float] = None


class ImportRequest(BaseModel):
    """Request model for import operation"""
    account_id: Optional[int] = None  # None means import all accounts


class AutoCategorizeRequest(BaseModel):
    """Request model for auto-categorization"""
    account_id: Optional[int] = None  # None means all accounts


class BulkCheckRequest(BaseModel):
    """Request body for bulk marking transactions checked/unchecked."""
    transaction_ids: List[int]
    checked: bool = True


class RuleData(BaseModel):
    """Complete rule structure"""
    id: Optional[str] = None  # UUID, auto-generated if not provided
    name: str
    description: Optional[str] = None
    conditions: List[Condition]
    conditionLogic: Optional[str] = None  # e.g., "(1 OR 2) AND 3"
    category: int
    accounts: List[int] = []  # Empty = all accounts
    priority: int = 5
    enabled: bool = True


class TestRuleRequest(BaseModel):
    """Payload for testing a rule"""
    rule: RuleData
    transaction: RuleTestData


class TransactionEntriesUpdate(BaseModel):
    """Request model for updating all entries of a transaction"""
    entries: list[AccountingEntryUpdate]


class AccountingEntryResponse(BaseModel):
    """Accounting entry response model"""
    id: int
    dateImport: datetime
    checked: bool
    amount: Decimal
    accountingPlanned: Optional[int] = None
    category: Optional[int] = None
    category_name: Optional[str] = None

    class Config:
        from_attributes = True


class TransactionResponse(BaseModel):
    """Transaction response model"""
    id: int
    dateImport: datetime
    dateValue: datetime
    description: str
    amount: Decimal
    iban: Optional[str] = None
    bic: Optional[str] = None
    recipientApplicant: Optional[str] = None
    account_id: int
    account_name: str
    account_iban: Optional[str] = None
    entries: list[AccountingEntryResponse] = []

    class Config:
        from_attributes = True


class TransactionListResponse(BaseModel):
    """Transaction list response with pagination"""
    transactions: list[TransactionResponse]
    total: int
    page: int = 1
    page_size: int = 50


class ColorPaletteResponse(BaseModel):
    """Color palette for frontend theming"""
    base_background: str = Field(alias="baseBackground")
    detail_background: str = Field(alias="detailBackground")
    border: str
    text: str = Field(alias="textColor")
    primary_accent: str = Field(alias="primaryAccent")
    primary_accent_hover: str = Field(alias="primaryAccentHover")
    primary_accent_pressed: str = Field(alias="primaryAccentPressed")
    selected_text: str = Field(alias="selectedText")
    input_border: str = Field(alias="inputBorder")
    amount_negative: str = Field(alias="amountNegative")
    amount_positive: str = Field(alias="amountPositive")

    class Config:
        populate_by_name = True


class CategoryCreateRequest(BaseModel):
    """Request model for creating a new category"""
    name: str
    parent_id: Optional[int] = None

    class Config:
        from_attributes = True


class CategoryUpdateRequest(BaseModel):
    """Request model for updating a category"""
    name: Optional[str] = None
    parent_id: Optional[int] = None

    class Config:
        from_attributes = True


class PlanningCycleResponse(BaseModel):
    """Planning cycle response model"""
    id: int
    cycle: str

    class Config:
        from_attributes = True


class PlanningResponse(BaseModel):
    """Planning response model"""
    id: int
    dateImport: datetime
    description: Optional[str] = None
    amount: Decimal
    dateStart: datetime
    dateEnd: Optional[datetime] = None
    account_id: int
    account_name: str
    category_id: int
    category_name: Optional[str] = None
    cycle_id: int
    cycle_name: str

    class Config:
        from_attributes = True


class PlanningListResponse(BaseModel):
    """Planning list response"""
    plannings: list[PlanningResponse]
    total: int

    class Config:
        from_attributes = True


class PlanningCreateRequest(BaseModel):
    """Request model for creating a new planning"""
    description: Optional[str] = None
    amount: Decimal
    dateStart: datetime
    dateEnd: Optional[datetime] = None
    account_id: int
    category_id: int
    cycle_id: int

    class Config:
        from_attributes = True


class PlanningUpdateRequest(BaseModel):
    """Request model for updating a planning"""
    description: Optional[str] = None
    amount: Decimal
    dateStart: datetime
    dateEnd: Optional[datetime] = None
    account_id: int
    category_id: int
    cycle_id: int

    class Config:
        from_attributes = True


class PlanningEntryResponse(BaseModel):
    """Planning entry response model"""
    id: int
    dateImport: datetime
    dateValue: datetime
    planning_id: int

    class Config:
        from_attributes = True


class PlanningEntriesResponse(BaseModel):
    """Collection of planning entries for a planning"""
    planning_id: int
    entries: list[PlanningEntryResponse]
    total: int

    class Config:
        from_attributes = True
