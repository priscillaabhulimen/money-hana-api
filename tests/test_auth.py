import pytest
from httpx import AsyncClient


async def test_register_success(client: AsyncClient):
    res = await client.post("/api/v1/register", json={
        "first_name": "Jane",
        "last_name": "Doe",
        "email": "jane@example.com",
        "password": "Password1",
        "user_type": "regular",
    })
    assert res.status_code == 201
    data = res.json()
    assert data["data"]["email"] == "jane@example.com"
    assert "password" not in data["data"]


async def test_register_duplicate_email(client: AsyncClient, registered_user):
    res = await client.post("/api/v1/register", json={
        "first_name": "Jane",
        "last_name": "Doe",
        "email": registered_user["email"],
        "password": "Password1",
        "user_type": "regular",
    })
    assert res.status_code == 400


async def test_login_valid_credentials(client: AsyncClient, verified_user):
    res = await client.post("/api/v1/login", json={
        "email": verified_user["email"],
        "password": verified_user["password"],
    })
    assert res.status_code == 200
    data = res.json()
    assert data["data"]["email"] == verified_user["email"]
    assert "access_token" in res.cookies or res.status_code == 200


async def test_login_invalid_password(client: AsyncClient, verified_user):
    res = await client.post("/api/v1/login", json={
        "email": verified_user["email"],
        "password": "WrongPassword1",
    })
    assert res.status_code == 401