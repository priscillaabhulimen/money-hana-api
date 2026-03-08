from pydantic import BaseModel, field_validator, Field
from uuid import UUID
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from app.schemas.enums import ExpenseCategory

class GoalBase(BaseModel):
    model_config = {"extra": "forbid"}

    category: ExpenseCategory
    monthly_limit: Decimal = Field(gt=0, max_digits=12, decimal_places=2)

    @field_validator("category", mode="before")
    @classmethod
    def validate_category(cls, v):
        try:
            return ExpenseCategory(v)
        except ValueError:
            raise ValueError("Invalid category")
    

    @field_validator("monthly_limit", mode="before")
    @classmethod
    def normalize_amount(cls, v):
        d = Decimal(str(v))
        return d.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

class GoalCreate(GoalBase):
    pass

class GoalUpdate(BaseModel):
    model_config = {"extra": "forbid"}
    
    monthly_limit: Decimal | None = Field(default=None, gt=0, max_digits=12, decimal_places=2)

    @field_validator("monthly_limit", mode="before")
    @classmethod
    def normalize_amount(cls, v):
        if v is None:
            return v
        d = Decimal(str(v))
        return d.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

class GoalResponse(GoalBase):
    model_config = {"from_attributes": True, "extra": "ignore"}

    id: UUID
    user_id: UUID
    current_spend: Decimal = Decimal(0)
    created_at: datetime
