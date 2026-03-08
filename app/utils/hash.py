import os
import jwt

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from dotenv import load_dotenv
from passlib.context import CryptContext


# Load local .env for utility usage in contexts where app.database is not imported first.
load_dotenv(Path(__file__).resolve().parents[2] / ".env")

SECRET_KEY = os.getenv("AUTH_SECRET_KEY") or os.getenv("JWT_SECRET_KEY")
ALGORITHM = os.getenv("AUTH_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("AUTH_ACCESS_TOKEN_EXPIRE_MINUTES", "30"))

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash(password: str) -> str:
    return pwd_context.hash(password)

def verify(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict[str, Any], expires_delta: timedelta | None = None) -> str:
    if not SECRET_KEY:
        raise ValueError("AUTH_SECRET_KEY is not set")

    payload = data.copy()
    now = datetime.now(timezone.utc)
    expire = now + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    payload.update({"iat": now, "exp": expire})
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any]:
    if not SECRET_KEY:
        raise ValueError("AUTH_SECRET_KEY is not set")

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
