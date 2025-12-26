"""
Pydantic models for API request/response validation
"""

from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, Field
from typing import Optional


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

class CategoryResponse(BaseModel):
    """Category response model"""
    id: int
    name: str
    parent_id: Optional[int] = None
    fullname: Optional[str] = None

    class Config:
        from_attributes = True


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