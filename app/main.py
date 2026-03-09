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
from app.routers import auth, transactions, goals

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.app_env == "development":
        await init_models()
    yield
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


# ── Health ────────────────────────────────────────────────────────────────────

@app.get("/health")
async def db_health_check(db: AsyncSession = Depends(get_db)):
    try:
        await db.execute(text("SELECT 1"))
        return {"status": "ok"}
    except Exception:
        logger.exception("Database health check failed")
        raise HTTPException(status_code=503, detail="Database unavailable")

