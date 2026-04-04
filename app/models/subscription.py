import uuid
from sqlalchemy import String, Boolean, Integer, Date, Numeric, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime, date
from app.base import Base


class Subscription(Base):
    __tablename__ = "subscriptions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    category: Mapped[str] = mapped_column(String, nullable=False)
    amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    description: Mapped[str | None] = mapped_column(String, nullable=True)
    billing_type: Mapped[str] = mapped_column(String, nullable=False)  # fixed_date | periodic
    frequency: Mapped[str] = mapped_column(String, nullable=False)  # weekly | monthly | yearly
    anchor_day: Mapped[int | None] = mapped_column(Integer, nullable=True)
    anchor_month: Mapped[int | None] = mapped_column(Integer, nullable=True)
    next_due_date: Mapped[date] = mapped_column(Date, nullable=False)
    is_trial: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    trial_ends_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(server_default="now()", nullable=False)