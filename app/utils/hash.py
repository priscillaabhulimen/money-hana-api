import jwt
import bcrypt
import hashlib

from datetime import datetime, timedelta, timezone
from typing import Any
from app.config import settings

SECRET_KEY = settings.auth_secret_key
ALGORITHM = settings.auth_algorithm
ACCESS_TOKEN_EXPIRE_MINUTES = settings.auth_access_token_expire_minutes


def _password_digest(password: str) -> bytes:
    # Pre-hash avoids bcrypt's 72-byte input limit while keeping deterministic verification.
    # Use hexdigest to avoid embedded null bytes that could be misinterpreted by some bcrypt implementations.
    return hashlib.sha256(password.encode("utf-8")).hexdigest().encode("ascii")

def hash_password(password: str) -> str:
    return bcrypt.hashpw(_password_digest(password), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(
            _password_digest(plain_password),
            hashed_password.encode("utf-8"),
        )
    except ValueError:
        return False


# Use a throwaway hash so missing-user and wrong-password paths do equivalent
# bcrypt work, reducing timing side-channel leakage during login.
DUMMY_PASSWORD_HASH = hash_password("moneyhana_dummy_password")

# Backward compatibility alias.
verify = verify_password


def create_access_token(data: dict[str, Any], expires_delta: timedelta | None = None) -> str:
    payload = data.copy()
    now = datetime.now(timezone.utc)
    expire = now + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    payload.update({"iat": now, "exp": expire})
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any]:
    try:
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM],
            options={"require": ["exp"]},
        )
    except jwt.ExpiredSignatureError as exc:
        raise ValueError("Token has expired") from exc
    except jwt.InvalidTokenError as exc:
        raise ValueError("Invalid token") from exc

    return payload
