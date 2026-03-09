import uuid
from app.base import Base
from sqlalchemy import Column, DateTime, String, CheckConstraint, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint(
            "user_type IN ('regular', 'premium')",
            name="user_type_check",
        ),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    password_hash = Column(String, nullable=False)
    email = Column(String, nullable=False, unique=True)
    user_type = Column(String, nullable=False, default="regular")
    is_verified = Column(Boolean, nullable=False, default=False, server_default="false")
    email_verified_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())