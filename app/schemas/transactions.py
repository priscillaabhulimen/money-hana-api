import datetime
from uuid import UUID
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation

from pydantic import BaseModel, field_validator, model_validator, Field

from app.schemas.enums import TransactionType, ExpenseCategory, IncomeCategory


class TransactionBase(BaseModel):
    model_config = {"extra": "forbid"}

    transaction_type: TransactionType
    category: str
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
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

    @field_validator("transaction_type", mode="before")
    @classmethod
    def validate_transaction_type(cls, v):
        try:
            return TransactionType(v)
        except ValueError:
            raise ValueError("Invalid transaction type")

    @field_validator("amount", mode="before")
    @classmethod
    def normalize_amount(cls, v):
        try:
            d = Decimal(str(v))
        except (InvalidOperation, ValueError, TypeError):
            raise ValueError("Invalid amount")
        return d.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    @model_validator(mode="after")
    def validate_category_matches_type(self):
        if self.transaction_type == TransactionType.expense:
            try:
                ExpenseCategory(self.category)
            except ValueError:
                raise ValueError("Invalid category")
        elif self.transaction_type == TransactionType.income:
            try:
                IncomeCategory(self.category)
            except ValueError:
                raise ValueError("Invalid category")
        return self


class TransactionCreate(TransactionBase):
    pass


class TransactionUpdate(BaseModel):
    model_config = {"extra": "forbid"}

    transaction_type: TransactionType | None = None
    category: str | None = None
    amount: Decimal | None = Field(default=None, gt=0, max_digits=12, decimal_places=2)
    date: datetime.date | None = None
    note: str | None = None

    # Note: category/type cross-validation is intentionally handled in the
    # update_transaction endpoint in main.py, where the existing transaction
    # record is available to resolve the effective transaction_type.

    @field_validator("date", mode="before")
    @classmethod
    def validate_date(cls, v):
        if v is None:
            return v
        if isinstance(v, datetime.date):
            return v
        try:
            return datetime.datetime.strptime(v, "%Y-%m-%d").date()
        except Exception:
            raise ValueError("Invalid date format")
    
    @field_validator("amount", mode="before")
    @classmethod
    def normalize_amount(cls, v):
        if v is None:
            return v
        try:
            d = Decimal(str(v))
        except (InvalidOperation, ValueError, TypeError):
            raise ValueError("Invalid amount")
        return d.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

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