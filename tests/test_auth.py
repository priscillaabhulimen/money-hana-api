import pytest
from httpx import AsyncClient
from app.routers import auth as auth_router


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


async def test_forgot_password_always_generic(client: AsyncClient):
    res = await client.post("/api/v1/forgot-password", json={"email": "missing@example.com"})
    assert res.status_code == 200
    body = res.json()
    assert body["data"]["status"] == "queued"


async def test_reset_password_success(client: AsyncClient, verified_user, monkeypatch: pytest.MonkeyPatch):
    sent = {"token": None}

    async def fake_send_password_reset_email(email: str, token: str) -> None:
        sent["token"] = token

    monkeypatch.setattr(auth_router, "send_password_reset_email", fake_send_password_reset_email)

    forgot = await client.post("/api/v1/forgot-password", json={"email": verified_user["email"]})
    assert forgot.status_code == 200
    assert sent["token"]

    reset = await client.post(
        "/api/v1/reset-password",
        json={"token": sent["token"], "new_password": "BrandNewPassword1"},
    )
    assert reset.status_code == 200

    old_login = await client.post(
        "/api/v1/login",
        json={"email": verified_user["email"], "password": verified_user["password"]},
    )
    assert old_login.status_code == 401

    new_login = await client.post(
        "/api/v1/login",
        json={"email": verified_user["email"], "password": "BrandNewPassword1"},
    )
    assert new_login.status_code == 200


async def test_reset_password_token_one_time_use(client: AsyncClient, verified_user, monkeypatch: pytest.MonkeyPatch):
    sent = {"token": None}

    async def fake_send_password_reset_email(email: str, token: str) -> None:
        sent["token"] = token

    monkeypatch.setattr(auth_router, "send_password_reset_email", fake_send_password_reset_email)

    await client.post("/api/v1/forgot-password", json={"email": verified_user["email"]})
    assert sent["token"]

    first = await client.post(
        "/api/v1/reset-password",
        json={"token": sent["token"], "new_password": "AnotherNewPassword1"},
    )
    assert first.status_code == 200

    second = await client.post(
        "/api/v1/reset-password",
        json={"token": sent["token"], "new_password": "ShouldFailPassword1"},
    )
    assert second.status_code == 400