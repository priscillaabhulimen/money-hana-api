import uuid
from app.base import Base
from sqlalchemy import Column, Date, DateTime, String, Numeric, ForeignKey, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

class Transaction(Base):
    __tablename__ = "transactions"
    __table_args__ = (
        CheckConstraint("amount > 0", name="transaction_amount_check"),
        CheckConstraint(
            "transaction_type IN ('income', 'expense')",
            name="transaction_type_check",
        ),
        CheckConstraint(
            "(" 
            "(transaction_type = 'income' AND category IN ('salary_wages', 'returns', 'gift', 'other'))"
            " OR "
            "(transaction_type = 'expense' AND category IN ('groceries', 'dining', 'transport', 'entertainment', 'utilities_bills', 'education', 'subscriptions', 'other'))"
            ")",
            name="transaction_category_check",
        ),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    amount = Column(Numeric(12, 2), nullable=False)
    note = Column(String, nullable=True)
    date = Column(Date, nullable=False)
    category = Column(String, nullable=False)
    transaction_type = Column(String, nullable=False)  # "income" or "expense"
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())