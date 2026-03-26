import pytest
from httpx import AsyncClient


async def test_get_transactions_unauthenticated(client: AsyncClient):
    res = await client.get("/api/v1/transactions")
    assert res.status_code == 401


async def test_get_transactions_authenticated(auth_client: AsyncClient):
    res = await auth_client.get("/api/v1/transactions")
    assert res.status_code == 200
    data = res.json()
    assert "data" in data
    assert isinstance(data["data"], list)


async def test_get_transactions_only_own(auth_client: AsyncClient, other_user_transaction):
    res = await auth_client.get("/api/v1/transactions")
    assert res.status_code == 200
    ids = [t["id"] for t in res.json()["data"]]
    assert other_user_transaction not in ids


async def test_create_transaction(auth_client: AsyncClient):
    res = await auth_client.post("/api/v1/transactions", json={
        "transaction_type": "expense",
        "amount": "75.00",
        "category": "groceries",
        "date": "2026-03-01",
        "note": "Test transaction",
    })
    assert res.status_code == 201
    data = res.json()
    assert data["data"]["category"] == "groceries"
    assert float(data["data"]["amount"]) == 75.00


async def test_delete_other_users_transaction(auth_client: AsyncClient, other_user_transaction):
    res = await auth_client.delete(f"/api/v1/transactions/{other_user_transaction}")
    assert res.status_code in (403, 404)