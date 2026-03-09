
import asyncio
import logging
from fastapi import Depends, status, APIRouter, HTTPException, Response, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from datetime import timedelta, datetime, timezone
from uuid import UUID, uuid4

from app.database import get_db
from app.config import settings
from app.models import User, RefreshToken
from app.schemas import (
    BaseResponse,
    Register,
    Login,
    UserResponse,
    VerifyEmailRequest,
    ResendVerificationRequest,
)
from app.utils import (
    hash_password,
    verify_password,
    create_access_token,
    decode_access_token,
    DUMMY_PASSWORD_HASH,
    hash_token,
    REFRESH_TOKEN_EXPIRE_DAYS,
)
from app.utils.email import send_verification_email, EmailDeliveryError

router = APIRouter(
    prefix="/api/v1",
    tags=["Auth"],
)
logger = logging.getLogger(__name__)


def _set_auth_cookies(response: Response, access_token: str, refresh_token: str) -> None:
    secure_cookie = settings.app_env != "development"

    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=secure_cookie,
        samesite="lax",
        max_age=settings.auth_access_token_expire_minutes * 60,
        path="/",
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=secure_cookie,
        samesite="lax",
        max_age=REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        path="/api/v1",
    )


def _new_access_token(user: User) -> str:
    return create_access_token(
        {
            "sub": str(user.id),
            "email": user.email,
            "purpose": "access",
        }
    )


def _new_refresh_token(user: User) -> tuple[str, str, datetime]:
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    jti = str(uuid4())
    token = create_access_token(
        {
            "sub": str(user.id),
            "email": user.email,
            "purpose": "refresh",
            "jti": jti,
        },
        expires_delta=timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
    )
    return token, jti, expires_at


async def get_current_user(request: Request, db: AsyncSession = Depends(get_db)) -> User:
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    try:
        payload = decode_access_token(token)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail="Invalid or expired token") from exc

    if payload.get("purpose") not in {None, "access"}:
        raise HTTPException(status_code=401, detail="Invalid token type")

    subject = payload.get("sub")
    if not subject:
        raise HTTPException(status_code=401, detail="Invalid token payload")

    try:
        user_id = UUID(subject)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail="Invalid token payload") from exc

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalars().one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    if not user.is_verified:
        raise HTTPException(status_code=403, detail="Email not verified")

    return user

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
        logger.warning("Registration failed due to integrity constraint", exc_info=True)
        raise HTTPException(status_code=400, detail="Registration could not be completed")

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
    except EmailDeliveryError:
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

@router.post("/login", response_model=BaseResponse[UserResponse])
async def login(data: Login, response: Response, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(User).where(User.email == data.email)
    )
    user = result.scalars().first()
    stored_hash = user.password_hash if user else DUMMY_PASSWORD_HASH
    password_ok = await asyncio.to_thread(verify_password, data.password, stored_hash)
    if not user or not password_ok:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if not user.is_verified:
        raise HTTPException(status_code=403, detail="Email not verified")

    access_token = _new_access_token(user)
    refresh_token, _, refresh_expires_at = _new_refresh_token(user)
    db.add(
        RefreshToken(
            user_id=user.id,
            token_hash=hash_token(refresh_token),
            expires_at=refresh_expires_at,
        )
    )
    await db.commit()
    _set_auth_cookies(response, access_token, refresh_token)

    return BaseResponse(data=UserResponse.model_validate(user))


@router.post("/refresh", response_model=BaseResponse[UserResponse])
async def refresh_session(request: Request, response: Response, db: AsyncSession = Depends(get_db)):
    refresh_cookie = request.cookies.get("refresh_token")
    if not refresh_cookie:
        raise HTTPException(status_code=401, detail="Refresh token missing")

    try:
        payload = decode_access_token(refresh_cookie)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token") from exc

    if payload.get("purpose") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid token type")

    subject = payload.get("sub")
    if not subject:
        raise HTTPException(status_code=401, detail="Invalid token payload")

    try:
        user_id = UUID(subject)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail="Invalid token payload") from exc

    token_hash = hash_token(refresh_cookie)
    now = datetime.now(timezone.utc)

    token_result = await db.execute(
        select(RefreshToken).where(
            RefreshToken.token_hash == token_hash,
            RefreshToken.revoked_at.is_(None),
        )
    )
    token_row = token_result.scalars().one_or_none()
    if not token_row or token_row.user_id != user_id or token_row.expires_at <= now:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    user_result = await db.execute(select(User).where(User.id == user_id))
    user = user_result.scalars().one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    if not user.is_verified:
        raise HTTPException(status_code=403, detail="Email not verified")

    token_row.revoked_at = now
    new_refresh_token, _, new_refresh_expires_at = _new_refresh_token(user)
    db.add(
        RefreshToken(
            user_id=user.id,
            token_hash=hash_token(new_refresh_token),
            expires_at=new_refresh_expires_at,
        )
    )

    access_token = _new_access_token(user)
    await db.commit()
    _set_auth_cookies(response, access_token, new_refresh_token)

    return BaseResponse(data=UserResponse.model_validate(user), message="Session refreshed")


@router.post("/logout", response_model=BaseResponse[dict[str, str]])
async def logout(request: Request, response: Response, db: AsyncSession = Depends(get_db)):
    refresh_cookie = request.cookies.get("refresh_token")
    if refresh_cookie:
        token_hash = hash_token(refresh_cookie)
        token_result = await db.execute(
            select(RefreshToken).where(
                RefreshToken.token_hash == token_hash,
                RefreshToken.revoked_at.is_(None),
            )
        )
        token_row = token_result.scalars().one_or_none()
        if token_row:
            token_row.revoked_at = datetime.now(timezone.utc)
            await db.commit()

    response.delete_cookie("access_token", path="/")
    response.delete_cookie("refresh_token", path="/api/v1")
    return BaseResponse(data={"status": "ok"}, message="Logged out")


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
        message="If this email exists, a verification link has been sent.",
    )