from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from app.base import Base
from app.config import settings

engine = create_async_engine(settings.database_url, echo=settings.debug_sql)
async_session_maker = async_sessionmaker(engine, expire_on_commit=False)


async def init_models() -> None:
    # Ensure all model metadata is registered before create_all.
    import app.models  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        yield session