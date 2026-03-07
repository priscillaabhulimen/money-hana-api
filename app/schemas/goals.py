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

class GoalResponse(GoalBase):
    id: UUID
    user_id: UUID
    created_at: datetime

    model_config = {"from_attributes": True}