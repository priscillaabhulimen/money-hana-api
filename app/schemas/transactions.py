import datetime
from uuid import UUID
from decimal import Decimal
from typing import Union

from pydantic import BaseModel, field_validator

from app.schemas.enums import TransactionType, ExpenseCategory, IncomeCategory

class TransactionBase(BaseModel):
    model_config = {"extra": "forbid"}

    transaction_type: TransactionType
    category: Union[ExpenseCategory, IncomeCategory]
    amount: Decimal
    date: datetime.date
    note: str | None = None

    @field_validator("date", mode="before")
    @classmethod
    def validate_date(cls, v):
        if isinstance(v, datetime.date):
            return v
        try:
            return datetime.datetime.strptime(v, "%Y-%m-%d").date()
        except Exception:
            raise ValueError("Invalid date format")

    @field_validator("category", mode="before")
    @classmethod
    def validate_category(cls, v):
        try:
            if cls.transaction_type == TransactionType.expense:
                return ExpenseCategory(v)
            else:
                return IncomeCategory(v)
        except ValueError:
            raise ValueError("Invalid category")

    @field_validator("transaction_type", mode="before")
    @classmethod
    def validate_transaction_type(cls, v):
        try:
            return TransactionType(v)
        except ValueError:
            raise ValueError("Invalid transaction type")

class TransactionCreate(TransactionBase):
    pass

class TransactionUpdate(BaseModel):
    model_config = {"extra": "forbid"}

    transaction_type: TransactionType | None = None
    category: Union[ExpenseCategory, IncomeCategory] | None = None
    amount: Decimal | None = None
    date: datetime.date | None = None
    note: str | None = None

    @field_validator("category", mode="before")
    @classmethod
    def validate_category(cls, v):
        try:
            if v is None:
                return v
            
            if cls.transaction_type == TransactionType.expense:
                return ExpenseCategory(v)
            else:
                return IncomeCategory(v)
        except ValueError:
            raise ValueError("Invalid category")

    @field_validator("transaction_type", mode="before")
    @classmethod
    def validate_transaction_type(cls, v):
        if v is None:
            return v
        
        try:
            return TransactionType(v)
        except ValueError:
            raise ValueError("Invalid transaction type")

class TransactionResponse(TransactionBase):
    model_config = {"from_attributes": True, "extra": "ignore"}

    id: UUID
    user_id: UUID
    created_at: datetime.datetime