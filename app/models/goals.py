import uuid
from app.base import Base
from sqlalchemy import Column, DateTime, String, Numeric, ForeignKey, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

class Goal(Base):
    __tablename__ = "goals"
    __table_args__ = (
        CheckConstraint("monthly_limit > 0", name="goals_monthly_limit_check"),
        CheckConstraint(
            "category IN ('groceries', 'dining', 'transport', 'entertainment', 'utilities_bills', 'education', 'subscriptions', 'other')",
            name="goals_category_check",
        ),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    category = Column(String, nullable=False)
    monthly_limit = Column(Numeric(12, 2), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())