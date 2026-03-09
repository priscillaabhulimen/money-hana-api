
import asyncio
import logging
from fastapi import Depends, status, APIRouter, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from datetime import timedelta, datetime, timezone
from uuid import UUID

from app.database import get_db
from app.models import User
from app.schemas import (
    BaseResponse,
    Register,
    Login,
    UserResponse,
    AuthResponse,
    VerifyEmailRequest,
    ResendVerificationRequest,
)
from app.utils import hash_password, verify, create_access_token, decode_access_token
from app.utils.email import send_verification_email, EmailDeliveryError

router = APIRouter(
    prefix="/api/v1",
    tags=["Auth"],
)
logger = logging.getLogger(__name__)

@router.post("/register", status_code=status.HTTP_201_CREATED, response_model=BaseResponse[UserResponse])
async def register_user(user: Register, db: AsyncSession = Depends(get_db)):
    hashed_password = await asyncio.to_thread(hash_password, user.password)
    new_user = User(
        first_name=user.first_name,
        last_name=user.last_name,
        email=user.email,
        password_hash=hashed_password,
        user_type=user.user_type.value,
        is_verified=False,
    )
    db.add(new_user)
    try:
        await db.commit()
        await db.refresh(new_user)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Email already registered")

    verification_token = create_access_token(
        {
            "sub": str(new_user.id),
            "email": new_user.email,
            "purpose": "email_verify",
        },
        expires_delta=timedelta(hours=24),
    )
    try:
        await send_verification_email(new_user.email, verification_token)
    except EmailDeliveryError as exc:
        return BaseResponse(
            data=UserResponse.model_validate(new_user),
            message=(
                "Registration successful, but verification email could not be sent. "
                "Please check email provider settings and use resend verification."
            ),
        )

    return BaseResponse(
        data=UserResponse.model_validate(new_user),
        message="Registration successful. Please verify your email.",
    )

@router.post("/login", response_model=BaseResponse[AuthResponse])
async def login(data: Login, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(User).where(User.email == data.email)
    )
    user = result.scalars().first()
    password_ok = user and await asyncio.to_thread(verify, data.password, user.password_hash)
    if not user or not password_ok:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if not user.is_verified:
        raise HTTPException(status_code=403, detail="Email not verified")

    access_token = create_access_token({"sub": str(user.id), "email": user.email})
    response_data = AuthResponse(
        id=user.id,
        first_name=user.first_name,
        last_name=user.last_name,
        email=user.email,
        user_type=user.user_type,
        is_verified=user.is_verified,
        created_at=user.created_at,
        access_token=access_token,
    )
    return BaseResponse(data=response_data)


@router.post("/verify-email", response_model=BaseResponse[dict[str, str]])
async def verify_email(payload: VerifyEmailRequest, db: AsyncSession = Depends(get_db)):
    try:
        token_payload = decode_access_token(payload.token)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if token_payload.get("purpose") != "email_verify":
        raise HTTPException(status_code=400, detail="Invalid verification token")

    subject = token_payload.get("sub")
    if not subject:
        raise HTTPException(status_code=400, detail="Invalid verification token")

    try:
        user_id = UUID(subject)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid verification token") from exc

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalars().one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if not user.is_verified:
        user.is_verified = True
        user.email_verified_at = datetime.now(timezone.utc)
        await db.commit()

    return BaseResponse(
        data={"status": "verified"},
        message="Email verification successful.",
    )


@router.post("/resend-verification", response_model=BaseResponse[dict[str, str]])
async def resend_verification(payload: ResendVerificationRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == payload.email))
    user = result.scalars().first()
    if not user:
        return BaseResponse(
            data={"status": "queued"},
            message="If this email exists, a verification link has been sent.",
        )

    if user.is_verified:
        return BaseResponse(
            data={"status": "queued"},
            message="If this email exists, a verification link has been sent.",
        )

    verification_token = create_access_token(
        {
            "sub": str(user.id),
            "email": user.email,
            "purpose": "email_verify",
        },
        expires_delta=timedelta(hours=24),
    )
    try:
        await send_verification_email(user.email, verification_token)
    except EmailDeliveryError:
        logger.exception("Verification email resend failed")
        raise HTTPException(status_code=502, detail="Failed to send verification email")

    return BaseResponse(
        data={"status": "queued"},
        message="Verification email sent.",
    )