
from fastapi import Depends, status, APIRouter, HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from app.database import get_db
from app.models import User
from app.schemas import BaseResponse, Register, UserResponse, Login
from app.utils import hash, verify

router = APIRouter(
    prefix="/api/v1",
    tags=["Auth"],
)

@router.post("/register", status_code=status.HTTP_201_CREATED, response_model=BaseResponse[UserResponse])
async def register_user(user: Register, db: AsyncSession = Depends(get_db)):
    hashed_password = hash(user.password)
    new_user = User(
        first_name=user.first_name,
        last_name=user.last_name,
        email=user.email,
        password_hash=hashed_password,
        user_type=user.user_type.value
    )
    db.add(new_user)
    try:
        await db.commit()
        await db.refresh(new_user)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Email already registered")
    return BaseResponse(data=UserResponse.model_validate(new_user))

@router.post("/login", response_model=BaseResponse[UserResponse])
async def login(data: Login, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        text("SELECT * FROM users WHERE email = :email"),
        {"email": data.email}
    )
    user = result.scalar_one_or_none()
    if not user or not verify(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    return BaseResponse(data=UserResponse.model_validate(user))