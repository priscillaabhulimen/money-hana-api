from pydantic import BaseModel, field_validator, model_validator
from uuid import UUID
from datetime import date, datetime
from decimal import Decimal
from typing import Literal
from app.schemas.enums import ExpenseCategory


class SubscriptionBase(BaseModel):
    model_config = {"extra": "forbid"}

    name: str
    category: str
    amount: Decimal
    description: str | None = None
    billing_type: Literal["fixed_date", "periodic"]
    frequency: Literal["weekly", "monthly", "yearly"]
    anchor_day: int | None = None
    anchor_month: int | None = None
    is_trial: bool = False
    trial_ends_at: date | None = None

    @field_validator("category")
    @classmethod
    def validate_category(cls, v):
        try:
            ExpenseCategory(v)
        except ValueError:
            raise ValueError(f"Invalid expense category: {v}")
        return v

    @field_validator("anchor_day")
    @classmethod
    def validate_anchor_day(cls, v):
        if v is not None and not (1 <= v <= 31):
            raise ValueError("anchor_day must be between 1 and 31")
        return v

    @field_validator("anchor_month")
    @classmethod
    def validate_anchor_month(cls, v):
        if v is not None and not (1 <= v <= 12):
            raise ValueError("anchor_month must be between 1 and 12")
        return v

    @model_validator(mode="after")
    def validate_anchor_fields(self):
        if self.billing_type == "fixed_date":
            if self.frequency in ("weekly", "monthly") and self.anchor_day is None:
                raise ValueError(f"anchor_day is required for fixed_date {self.frequency} billing")
            if self.frequency == "yearly" and (self.anchor_day is None or self.anchor_month is None):
                raise ValueError("anchor_day and anchor_month are required for fixed_date yearly billing")
        return self


class SubscriptionCreate(SubscriptionBase):
    pass


class SubscriptionUpdate(BaseModel):
    model_config = {"extra": "forbid"}

    name: str | None = None
    category: str | None = None
    amount: Decimal | None = None
    description: str | None = None
    billing_type: Literal["fixed_date", "periodic"] | None = None
    frequency: Literal["weekly", "monthly", "yearly"] | None = None
    anchor_day: int | None = None
    anchor_month: int | None = None
    is_trial: bool | None = None
    trial_ends_at: date | None = None
    is_active: bool | None = None

    @field_validator("category")
    @classmethod
    def validate_category(cls, v):
        if v is None:
            return v
        try:
            ExpenseCategory(v)
        except ValueError:
            raise ValueError(f"Invalid expense category: {v}")
        return v

    @field_validator("anchor_day")
    @classmethod
    def validate_anchor_day(cls, v):
        if v is not None and not (1 <= v <= 31):
            raise ValueError("anchor_day must be between 1 and 31")
        return v

    @field_validator("anchor_month")
    @classmethod
    def validate_anchor_month(cls, v):
        if v is not None and not (1 <= v <= 12):
            raise ValueError("anchor_month must be between 1 and 12")
        return v


class SubscriptionResponse(BaseModel):
    model_config = {"from_attributes": True, "extra": "ignore"}

    id: UUID
    user_id: UUID
    name: str
    category: str
    amount: Decimal
    description: str | None
    billing_type: str
    frequency: str
    anchor_day: int | None
    anchor_month: int | None
    next_due_date: date
    is_trial: bool
    trial_ends_at: date | None
    is_active: bool
    created_at: datetime