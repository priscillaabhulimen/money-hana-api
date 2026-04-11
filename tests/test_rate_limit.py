import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.config import settings
from app.utils.rate_limit import InMemoryRateLimiterMiddleware, RateLimitConfig

# Each fixture call creates a fresh FastAPI app with a fresh middleware instance
# (function-scoped by default), so there is no state leakage between tests.


# The conftest clean_tables fixture is autouse and depends on test_engine (DB).
# Rate-limit tests are database-free, so override it here as a no-op to avoid
# triggering a DB connection attempt.
@pytest_asyncio.fixture(autouse=True)
async def clean_tables():
    yield


@pytest.fixture
def rate_limited_app(monkeypatch):
    monkeypatch.setattr(settings, "rate_limit_enabled", True)

    test_app = FastAPI()
    test_app.add_middleware(
        InMemoryRateLimiterMiddleware,
        config=RateLimitConfig(requests=3, window_seconds=60),
    )

    @test_app.get("/ping")
    async def ping():
        return {"ok": True}

    return test_app


async def test_requests_under_limit_all_pass(rate_limited_app):
    async with AsyncClient(
        transport=ASGITransport(app=rate_limited_app), base_url="http://test"
    ) as client:
        for _ in range(3):
            res = await client.get("/ping")
            assert res.status_code == 200


async def test_rate_limit_headers_present_on_allowed_request(rate_limited_app):
    async with AsyncClient(
        transport=ASGITransport(app=rate_limited_app), base_url="http://test"
    ) as client:
        res = await client.get("/ping")

    assert res.headers["X-RateLimit-Limit"] == "3"
    assert res.headers["X-RateLimit-Remaining"] == "2"
    assert res.headers["X-RateLimit-Window"] == "60"


async def test_remaining_header_decrements(rate_limited_app):
    async with AsyncClient(
        transport=ASGITransport(app=rate_limited_app), base_url="http://test"
    ) as client:
        r1 = await client.get("/ping")
        r2 = await client.get("/ping")
        r3 = await client.get("/ping")

    assert r1.headers["X-RateLimit-Remaining"] == "2"
    assert r2.headers["X-RateLimit-Remaining"] == "1"
    assert r3.headers["X-RateLimit-Remaining"] == "0"


async def test_over_limit_returns_429(rate_limited_app):
    async with AsyncClient(
        transport=ASGITransport(app=rate_limited_app), base_url="http://test"
    ) as client:
        for _ in range(3):
            await client.get("/ping")

        res = await client.get("/ping")

    assert res.status_code == 429
    body = res.json()
    assert body["status"] == "error"
    assert "Too many requests" in body["message"]


async def test_429_includes_retry_after_header(rate_limited_app):
    async with AsyncClient(
        transport=ASGITransport(app=rate_limited_app), base_url="http://test"
    ) as client:
        for _ in range(3):
            await client.get("/ping")

        res = await client.get("/ping")

    assert res.status_code == 429
    assert "Retry-After" in res.headers
    retry_after = int(res.headers["Retry-After"])
    assert 1 <= retry_after <= 60


async def test_rate_limit_disabled_never_throttles(monkeypatch):
    monkeypatch.setattr(settings, "rate_limit_enabled", False)

    test_app = FastAPI()
    test_app.add_middleware(
        InMemoryRateLimiterMiddleware,
        config=RateLimitConfig(requests=2, window_seconds=60),
    )

    @test_app.get("/ping")
    async def ping():
        return {"ok": True}

    async with AsyncClient(
        transport=ASGITransport(app=test_app), base_url="http://test"
    ) as client:
        for _ in range(5):
            res = await client.get("/ping")
            assert res.status_code == 200
