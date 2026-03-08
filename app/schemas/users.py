from pydantic import BaseModel, field_validator, EmailStr
from uuid import UUID
from datetime import datetime
from app.schemas.enums import UserType

class UserBase(BaseModel):
    model_config = {"extra": "forbid"}

    first_name: str
    last_name: str
    email: EmailStr
    user_type: UserType = UserType.regular

    @field_validator("user_type", mode="before")
    @classmethod
    def validate_user_type(cls, v):
        try:
            return UserType(v)
        except ValueError:
            raise ValueError("Invalid user type")
        
class Register(UserBase):
    password: str

class Login(BaseModel):
    model_config = {"extra": "forbid"}
    
    email: EmailStr
    password: str

class UserResponse(UserBase):
    model_config = {"from_attributes": True, "extra": "ignore"}

    id: UUID
    created_at: datetime