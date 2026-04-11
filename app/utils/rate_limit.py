from __future__ import annotations

import asyncio
import time
from collections import OrderedDict, deque
from dataclasses import dataclass
from typing import Deque

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import settings


@dataclass
class RateLimitConfig:
    requests: int
    window_seconds: int


class InMemoryRateLimiterMiddleware(BaseHTTPMiddleware):
    """Sliding-window, per-client in-memory rate limiter.

    Uses per-client asyncio locks so unrelated clients do not block each other.
    Empty client deques are evicted after their window expires, and an LRU cap
    (`_MAX_CLIENTS`) prevents unbounded memory growth from high-cardinality keys.

    Process-local — for multi-instance deployments use a shared backend (e.g. Redis).

    The enabled/disabled state is read from `settings.rate_limit_enabled` on every
    request so it can be toggled in tests without rebuilding the middleware stack.
    """

    _MAX_CLIENTS = 10_000

    def __init__(self, app, *, config: RateLimitConfig):
        super().__init__(app)
        self.config = config
        # OrderedDict gives O(1) LRU move_to_end / popitem(last=False).
        self._logs: OrderedDict[str, Deque[float]] = OrderedDict()
        # Per-client locks: no await between check and assignment, so no
        # context-switch can race here in the single-threaded asyncio loop.
        self._client_locks: dict[str, asyncio.Lock] = {}

    def _get_client_lock(self, key: str) -> asyncio.Lock:
        if key not in self._client_locks:
            self._client_locks[key] = asyncio.Lock()
        return self._client_locks[key]

    async def dispatch(self, request: Request, call_next):
        if not settings.rate_limit_enabled:
            return await call_next(request)

        client_key = self._get_client_key(request)
        lock = self._get_client_lock(client_key)
        now = time.monotonic()
        remaining = 0

        async with lock:
            log = self._logs.get(client_key)

            if log is not None:
                cutoff = now - self.config.window_seconds
                while log and log[0] <= cutoff:
                    log.popleft()
                if not log:
                    # All window entries expired — evict the key to reclaim memory.
                    del self._logs[client_key]
                    log = None

            if log is not None and len(log) >= self.config.requests:
                retry_after_seconds = max(1, int(self.config.window_seconds - (now - log[0])))
                return JSONResponse(
                    status_code=429,
                    content={
                        "status": "error",
                        "message": "Too many requests. Please try again later.",
                    },
                    headers={"Retry-After": str(retry_after_seconds)},
                )

            if log is None:
                # Enforce LRU cap before inserting a new key.
                if len(self._logs) >= self._MAX_CLIENTS:
                    self._logs.popitem(last=False)
                log = deque()
                self._logs[client_key] = log
            else:
                self._logs.move_to_end(client_key)

            log.append(now)
            remaining = self.config.requests - len(log)

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(self.config.requests)
        response.headers["X-RateLimit-Remaining"] = str(max(0, remaining))
        response.headers["X-RateLimit-Window"] = str(self.config.window_seconds)
        return response

    @staticmethod
    def _get_client_key(request: Request) -> str:
        if request.client and request.client.host:
            return request.client.host
        return "unknown"