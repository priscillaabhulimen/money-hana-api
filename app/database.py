from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from dotenv import load_dotenv
import os
from pathlib import Path

load_dotenv(Path(__file__).parent.parent / ".env")

DATABASE_URL = os.getenv("DATABASE_URL")
_engine = None
_async_session_maker = None

def get_engine():
    """
    Lazily create and return the async database engine.
    """
    global _engine, _async_session_maker

    if _engine is None:
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            raise RuntimeError(
                "DATABASE_URL environment variable is not set. Please configure it in your environment or .env file."
            )

        _engine = create_async_engine(database_url, echo=True)
        _async_session_maker = async_sessionmaker(_engine, expire_on_commit=False)

    return _engine

def get_async_session_maker():
    """
    Lazily create and return the async session maker.
    """
    global _async_session_maker

    if _async_session_maker is None:
        # Ensure engine and session maker are initialized
        get_engine()

    return _async_session_maker

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async_session_maker = get_async_session_maker()
    async with async_session_maker() as session:
        yield session
