import pytest_asyncio
import sqlalchemy as sa
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool
from app.main import app as fastapi_app
from app.database import get_db
from app.base import Base
import app.models  # noqa: F401

TEST_DATABASE_URL = "postgresql+asyncpg://postgres:%40ckl3sJ3ns3n@127.0.0.1:5430/moneyhana_test"

test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestSessionLocal = async_sessionmaker(test_engine, expire_on_commit=False)


async def override_get_db():
    async with TestSessionLocal() as session:
        yield session


@pytest_asyncio.fixture(scope="session")
async def test_engine():
    engine = create_async_engine(TEST_DATABASE_URL, poolclass=NullPool)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture(autouse=True)
async def clean_tables(test_engine):
    yield
    async with test_engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            await conn.execute(
                sa.text(f'TRUNCATE TABLE "{table.name}" RESTART IDENTITY CASCADE')
            )


@pytest_asyncio.fixture
async def client(test_engine):
    TestSessionLocal = async_sessionmaker(test_engine, expire_on_commit=False)

    async def override_get_db():
        async with TestSessionLocal() as session:
            yield session

    fastapi_app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(
        transport=ASGITransport(app=fastapi_app),
        base_url="http://test",
    ) as ac:
        yield ac
    fastapi_app.dependency_overrides.clear()

@pytest_asyncio.fixture
async def registered_user(client: AsyncClient):
    payload = {
        "first_name": "Test",
        "last_name": "User",
        "email": "test@example.com",
        "password": "Password1",
        "user_type": "regular",
    }
    await client.post("/api/v1/register", json=payload)
    return payload


@pytest_asyncio.fixture
async def verified_user(client: AsyncClient, registered_user):
    # Manually verify the user in the test DB
    async with TestSessionLocal() as db:
        from sqlalchemy import select, update
        from app.models import User
        await db.execute(
            update(User)
            .where(User.email == registered_user["email"])
            .values(is_verified=True)
        )
        await db.commit()
    return registered_user


@pytest_asyncio.fixture
async def auth_client(client: AsyncClient, verified_user):
    res = await client.post("/api/v1/login", json={
        "email": verified_user["email"],
        "password": verified_user["password"],
    })
    assert res.status_code == 200
    return client


@pytest_asyncio.fixture
async def other_user_transaction(client: AsyncClient, auth_client: AsyncClient, test_engine):
    # Register other user
    payload = {
        "first_name": "Other",
        "last_name": "User",
        "email": "other@example.com",
        "password": "Password1",
        "user_type": "regular",
    }
    await client.post("/api/v1/register", json=payload)

    # Verify other user
    async with async_sessionmaker(test_engine, expire_on_commit=False)() as db:
        from sqlalchemy import update
        from app.models import User
        await db.execute(
            update(User)
            .where(User.email == "other@example.com")
            .values(is_verified=True)
        )
        await db.commit()

    # Create a separate client for the other user so auth_client is not affected
    TestSession = async_sessionmaker(test_engine, expire_on_commit=False)

    async def override_get_db():
        async with TestSession() as session:
            yield session

    fastapi_app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(
        transport=ASGITransport(app=fastapi_app),
        base_url="http://test",
    ) as other_client:
        login_res = await other_client.post("/api/v1/login", json={
            "email": "other@example.com",
            "password": "Password1",
        })
        assert login_res.status_code == 200

        tx_res = await other_client.post("/api/v1/transactions", json={
            "transaction_type": "expense",
            "amount": "50.00",
            "category": "dining",
            "date": "2026-03-01",
            "note": "Other user transaction",
        })
        assert tx_res.status_code == 201

    return tx_res.json()["data"]["id"]
    # Register and verify a second user
    payload = {
        "first_name": "Other",
        "last_name": "User",
        "email": "other@example.com",
        "password": "Password1",
        "user_type": "regular",
    }
    await client.post("/api/v1/register", json=payload)
    async with TestSessionLocal() as db:
        from sqlalchemy import update
        from app.models import User
        await db.execute(
            update(User)
            .where(User.email == "other@example.com")
            .values(is_verified=True)
        )
        await db.commit()

    # Login as other user
    login_res = await client.post("/api/v1/login", json={
        "email": "other@example.com",
        "password": "Password1",
    })
    assert login_res.status_code == 200

    # Create a transaction as other user
    tx_res = await client.post("/api/v1/transactions", json={
        "transaction_type": "expense",
        "amount": "50.00",
        "category": "dining",
        "date": "2026-03-01",
        "note": "Other user transaction",
    })
    assert tx_res.status_code == 201
    return tx_res.json()["data"]["id"]