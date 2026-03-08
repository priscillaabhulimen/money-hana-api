from pydantic import BaseModel, field_validator
from uuid import UUID
from datetime import datetime
from decimal import Decimal
from app.schemas.enums import ExpenseCategory

class GoalBase(BaseModel):
    model_config = {"extra": "forbid"}

    category: ExpenseCategory
    monthly_limit: Decimal

    @field_validator("category", mode="before")
    @classmethod
    def validate_category(cls, v):
        try:
            return ExpenseCategory(v)
        except ValueError:
            raise ValueError("Invalid category")

class GoalCreate(GoalBase):
    pass

class GoalUpdate(BaseModel):
    model_config = {"extra": "forbid"}
    
    monthly_limit: Decimal | None = None

class GoalResponse(GoalBase):
    model_config = {"from_attributes": True, "extra": "ignore"}

    id: UUID
    user_id: UUID
    current_spend: Decimal
    created_at: datetime
