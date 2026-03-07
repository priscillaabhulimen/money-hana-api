from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID
from app.database import engine, get_db
import logging

from app.schemas.base import BaseResponse, ErrorResponse
from app.schemas.goals import GoalCreate, GoalResponse
from app.models import Goal

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await engine.dispose()

app = FastAPI(title="MoneyHana API", lifespan=lifespan)

ERROR_MESSAGES = {
    "missing": "This field is required",
    "value_error": "Invalid value provided",
    "type_error": "Invalid type provided",
    "string_too_short": "Value is too short",
    "greater_than": "Value must be greater than 0",
    "json_invalid": "Invalid JSON format",
    "extra_forbidden": "Unexpected field provided",
}

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = exc.errors()
    print(exc.errors());
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
        content=ErrorResponse(
            message=exc.detail
        ).model_dump()
    )

@app.get("/health")
async def db_health_check(db: AsyncSession = Depends(get_db)):
    try:
        await db.execute(select(1))
        return {"status": "ok"}
    except Exception:
        logger.exception("Database health check failed")
        raise HTTPException(status_code=503, detail="Database unavailable")
    
TEMP_USER_ID = UUID("ef73d89b-3d2d-4658-8b79-20a06c06d5cd")
    
@app.get("/api/v1/goals", response_model=BaseResponse[list[GoalResponse]])
async def get_goals(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Goal))
    goals = result.scalars().all()
    return BaseResponse(data=goals)

@app.post("/api/v1/goals", response_model=BaseResponse[GoalResponse], status_code=status.HTTP_201_CREATED)
async def create_goal(goal: GoalCreate, db: AsyncSession = Depends(get_db)):
    new_goal = Goal(**goal.model_dump(), user_id=TEMP_USER_ID)
    db.add(new_goal)
    await db.commit()
    await db.refresh(new_goal)
    return BaseResponse(data=new_goal)
