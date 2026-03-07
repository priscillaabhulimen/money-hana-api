import uuid
from app.base import Base
from sqlalchemy import Column, Date, DateTime, String, Numeric, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    amount = Column(Numeric(12, 2), nullable=False)
    note = Column(String, nullable=True)
    date = Column(Date, nullable=False)
    category = Column(String, nullable=False)
    transaction_type = Column("type", String, nullable=False)  # "income" or "expense"
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())