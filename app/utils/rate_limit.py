from __future__ import annotations

import asyncio
import time
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Deque

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware


@dataclass
class RateLimitConfig:
    requests: int
    window_seconds: int


class InMemoryRateLimiterMiddleware(BaseHTTPMiddleware):
    """Simple per-client, sliding-window rate limiter.

    This middleware is process-local and best suited for a single API instance.
    It tracks recent request timestamps within the configured window.
    """

    def __init__(self, app, *, config: RateLimitConfig):
        super().__init__(app)
        self.config = config
        self._request_log: dict[str, Deque[float]] = defaultdict(deque)
        self._lock = asyncio.Lock()

    async def dispatch(self, request: Request, call_next):
        client_key = self._get_client_key(request)
        now = time.monotonic()

        async with self._lock:
            log = self._request_log[client_key]
            cutoff = now - self.config.window_seconds

            while log and log[0] <= cutoff:
                log.popleft()

            if len(log) >= self.config.requests:
                retry_after_seconds = max(1, int(self.config.window_seconds - (now - log[0])))
                return JSONResponse(
                    status_code=429,
                    content={
                        "status": "error",
                        "message": "Too many requests. Please try again later.",
                    },
                    headers={"Retry-After": str(retry_after_seconds)},
                )

            log.append(now)
            remaining = self.config.requests - len(log)

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(self.config.requests)
        response.headers["X-RateLimit-Remaining"] = str(max(0, remaining))
        response.headers["X-RateLimit-Window"] = str(self.config.window_seconds)
        return response

    @staticmethod
    def _get_client_key(request: Request) -> str:
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()

        if request.client and request.client.host:
            return request.client.host

        return "unknown"