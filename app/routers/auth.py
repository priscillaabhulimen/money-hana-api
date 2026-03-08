
from fastapi import Depends, status, APIRouter, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from app.database import get_db
from app.models import User
from app.schemas import BaseResponse, Register, Login, UserResponse, AuthResponse
from app.utils import hash, verify, create_access_token

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

@router.post("/login", response_model=BaseResponse[AuthResponse])
async def login(data: Login, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(User).where(User.email == data.email)
    )
    user = result.scalars().first()
    if not user or not verify(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    access_token = create_access_token({"sub": str(user.id), "email": user.email})
    response_data = AuthResponse(
        id=user.id,
        first_name=user.first_name,
        last_name=user.last_name,
        email=user.email,
        user_type=user.user_type,
        created_at=user.created_at,
        access_token=access_token,
    )
    return BaseResponse(data=response_data)