from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import logging

from app.database import engine, get_db, init_models
from app.config import settings
from app.schemas.base import ErrorResponse
from app.utils import ERROR_MESSAGES, custom_openapi
from app.routers import ai_insights, auth, subscriptions, transactions, goals, notifications
from app.utils.digest import send_weekly_digest
from app.utils.lock import DistributedLock

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from app.database import AsyncSessionLocal
from app.utils.cleanup import cleanup_old_insights

scheduler = AsyncIOScheduler()

logger = logging.getLogger(__name__)


async def _assert_auth_tables_ready() -> None:
    async with engine.connect() as conn:
        result = await conn.execute(text("SELECT to_regclass('refresh_tokens')"))
        table_name = result.scalar_one_or_none()

    if table_name is None:
        raise RuntimeError(
            "Missing required table 'refresh_tokens'. Run database migrations/DDL before starting the API."
        )

@asynccontextmanager
async def lifespan(app: FastAPI):
    async def run_cleanup():
        async with AsyncSessionLocal() as db:
            lock = DistributedLock(db, job_id="cleanup_old_insights", ttl_seconds=3600)
            if await lock.acquire():
                try:
                    await cleanup_old_insights(db)
                finally:
                    await lock.release()
            else:
                logger.debug("Skipping cleanup - another instance is running it")

    async def run_digest():
        async with AsyncSessionLocal() as db:
            lock = DistributedLock(db, job_id="weekly_digest", ttl_seconds=3600)
            if await lock.acquire():
                try:
                    await send_weekly_digest(db)
                finally:
                    await lock.release()
            else:
                logger.debug("Skipping digest - another instance is running it")

    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        run_cleanup,
        trigger=CronTrigger(hour=2, minute=0),
        id="cleanup_old_insights",
        replace_existing=True,
    )
    scheduler.add_job(
        run_digest,
        trigger=CronTrigger(day_of_week="mon", hour=8, minute=0),
        id="weekly_digest",
        replace_existing=True,
    )
    scheduler.start()

    if settings.app_env == "development":
        await init_models()
    else:
        await _assert_auth_tables_ready()

    yield

    scheduler.shutdown()
    await engine.dispose()

app = FastAPI(title="MoneyHana API", lifespan=lifespan)

origins = settings.allowed_origins_list

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = exc.errors()
    first = errors[0]
    field = " -> ".join(
        str(loc) for loc in first["loc"]
        if loc != "body" and not isinstance(loc, int)
    )
    error_type = first["type"]
    raw_message = first["msg"]

    friendly = ERROR_MESSAGES.get(error_type, raw_message)
    message = f"{field}: {friendly}" if field else friendly

    return JSONResponse(
        status_code=422,
        content=ErrorResponse(message=message).model_dump()
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(message=exc.detail).model_dump()
    )

app.openapi = lambda: custom_openapi(app)

app.include_router(auth.router)
app.include_router(transactions.router)
app.include_router(goals.router)
app.include_router(ai_insights.router)
app.include_router(subscriptions.router)
app.include_router(notifications.router)


# ── Health ────────────────────────────────────────────────────────────────────

@app.get("/health")
async def db_health_check(db: AsyncSession = Depends(get_db)):
    try:
        await db.execute(text("SELECT 1"))
        return {"status": "ok"}
    except Exception:
        logger.exception("Database health check failed")
        raise HTTPException(status_code=503, detail="Database unavailable")

