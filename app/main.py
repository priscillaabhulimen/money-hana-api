from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException, Request, status, Query
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.openapi.utils import get_openapi
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, text
from datetime import date
from decimal import Decimal
from uuid import UUID
import logging
import os

from app.database import engine, get_db
from app.schemas.base import BaseResponse, ErrorResponse, PaginatedResponse
from app.schemas.goals import GoalCreate, GoalResponse, GoalUpdate
from app.schemas.transactions import TransactionCreate, TransactionResponse, TransactionUpdate
from app.schemas.enums import ExpenseCategory, IncomeCategory, TransactionType
from app.models import Goal, Transaction

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await engine.dispose()


app = FastAPI(title="MoneyHana API", lifespan=lifespan)

origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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


def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title="MoneyHana API",
        version="1.0.0",
        routes=app.routes,
    )

    for path in openapi_schema["paths"].values():
        for method in path.values():
            if "422" in method.get("responses", {}):
                method["responses"]["422"] = {
                    "description": "Validation Error",
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/ErrorResponse"
                            }
                        }
                    }
                }

    openapi_schema["components"]["schemas"]["ErrorResponse"] = {
        "type": "object",
        "properties": {
            "status": {"type": "string", "example": "error"},
            "message": {"type": "string", "example": "Invalid category"}
        },
        "required": ["status", "message"]
    }

    for schema_name in ["HTTPValidationError", "ValidationError"]:
        openapi_schema["components"]["schemas"].pop(schema_name, None)

    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi


# ── Health ────────────────────────────────────────────────────────────────────

@app.get("/health")
async def db_health_check(db: AsyncSession = Depends(get_db)):
    try:
        await db.execute(text("SELECT 1"))
        return {"status": "ok"}
    except Exception:
        logger.exception("Database health check failed")
        raise HTTPException(status_code=503, detail="Database unavailable")


# TODO: Replace with real user management in Week 4
TEMP_USER_ID = UUID("ef73d89b-3d2d-4658-8b79-20a06c06d5cd")


# ── Goals ─────────────────────────────────────────────────────────────────────

async def get_current_spend_all(db: AsyncSession, user_id: UUID) -> dict[str, Decimal]:
    today = date.today()
    first_of_month = today.replace(day=1)
    if today.month == 12:
        first_of_next_month = today.replace(year=today.year + 1, month=1, day=1)
    else:
        first_of_next_month = today.replace(month=today.month + 1, day=1)

    result = await db.execute(
        select(
            Transaction.category,
            func.coalesce(func.sum(Transaction.amount), 0).label("total")
        )
        .where(
            Transaction.user_id == user_id,
            Transaction.transaction_type == TransactionType.expense,
            Transaction.date >= first_of_month,
            Transaction.date < first_of_next_month,
        )
        .group_by(Transaction.category)
    )
    return {row.category: row.total for row in result.all()}

def enrich_goal_response(goal: Goal, spend_by_category: dict[str, Decimal]) -> GoalResponse:
    goal_response = GoalResponse.model_validate(goal)
    goal_response.current_spend = spend_by_category.get(goal.category, Decimal(0))
    return goal_response


@app.get("/api/v1/goals", response_model=BaseResponse[list[GoalResponse]])
async def get_goals(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Goal))
    goals = result.scalars().all()
    spend_by_category = await get_current_spend_all(db, TEMP_USER_ID)
    return BaseResponse(data=[enrich_goal_response(g, spend_by_category) for g in goals])


@app.get("/api/v1/goals/{goal_id}", response_model=BaseResponse[GoalResponse])
async def get_goal(goal_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Goal).where(Goal.id == goal_id))
    goal = result.scalar_one_or_none()
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    spend_by_category = await get_current_spend_all(db, TEMP_USER_ID)
    return BaseResponse(data=enrich_goal_response(goal, spend_by_category))


@app.post("/api/v1/goals", response_model=BaseResponse[GoalResponse], status_code=status.HTTP_201_CREATED)
async def create_goal(goal: GoalCreate, db: AsyncSession = Depends(get_db)):
    new_goal = Goal(**goal.model_dump(), user_id=TEMP_USER_ID)
    db.add(new_goal)
    await db.commit()
    await db.refresh(new_goal)
    spend_by_category = await get_current_spend_all(db, TEMP_USER_ID)
    return BaseResponse(data=enrich_goal_response(new_goal, spend_by_category))


@app.patch("/api/v1/goals/{goal_id}", response_model=BaseResponse[GoalResponse])
async def update_goal(goal_id: UUID, goal_update: GoalUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Goal).where(Goal.id == goal_id))
    goal = result.scalar_one_or_none()
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    for field, value in goal_update.model_dump(exclude_unset=True).items():
        setattr(goal, field, value)
    await db.commit()
    await db.refresh(goal)
    spend_by_category = await get_current_spend_all(db, TEMP_USER_ID)
    return BaseResponse(data=enrich_goal_response(goal, spend_by_category))


@app.delete("/api/v1/goals/{goal_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_goal(goal_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Goal).where(Goal.id == goal_id))
    goal = result.scalar_one_or_none()
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    await db.delete(goal)
    await db.commit()


# ── Transactions ──────────────────────────────────────────────────────────────

@app.get("/api/v1/transactions", response_model=PaginatedResponse[list[TransactionResponse]])
async def get_transactions(
    db: AsyncSession = Depends(get_db),
    limit: int = Query(default=30, ge=1, le=100),
    page: int = Query(default=1, ge=1),
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
):
    offset = (page - 1) * limit

    filters = []
    if start_date:
        filters.append(Transaction.date >= start_date)
    if end_date:
        filters.append(Transaction.date <= end_date)

    total_result = await db.execute(
        select(func.count()).select_from(Transaction).where(*filters)
    )
    total = total_result.scalar()

    result = await db.execute(
        select(Transaction)
        .where(*filters)
        .order_by(Transaction.date.desc())
        .limit(limit)
        .offset(offset)
    )
    transactions = result.scalars().all()
    return PaginatedResponse(data=transactions, total=total, limit=limit, page=page)


@app.get("/api/v1/transactions/{transaction_id}", response_model=BaseResponse[TransactionResponse])
async def get_transaction(transaction_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Transaction).where(Transaction.id == transaction_id))
    transaction = result.scalar_one_or_none()
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return BaseResponse(data=TransactionResponse.model_validate(transaction))


@app.post("/api/v1/transactions", response_model=BaseResponse[TransactionResponse], status_code=status.HTTP_201_CREATED)
async def create_transaction(transaction: TransactionCreate, db: AsyncSession = Depends(get_db)):
    new_transaction = Transaction(**transaction.model_dump(), user_id=TEMP_USER_ID)
    db.add(new_transaction)
    await db.commit()
    await db.refresh(new_transaction)
    return BaseResponse(data=new_transaction)


@app.patch("/api/v1/transactions/{transaction_id}", response_model=BaseResponse[TransactionResponse])
async def update_transaction(transaction_id: UUID, transaction_update: TransactionUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Transaction).where(Transaction.id == transaction_id))
    transaction = result.scalar_one_or_none()
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")

    effective_type = (
        transaction_update.transaction_type
        if transaction_update.transaction_type is not None
        else transaction.transaction_type
    )
    category_to_validate = (
        transaction_update.category
        if transaction_update.category is not None
        else transaction.category
    )
    if effective_type and category_to_validate is not None:
        if effective_type == TransactionType.expense:
            try:
                ExpenseCategory(category_to_validate)
            except ValueError:
                raise HTTPException(status_code=422, detail="Invalid category for expense transaction")
        elif effective_type == TransactionType.income:
            try:
                IncomeCategory(category_to_validate)
            except ValueError:
                raise HTTPException(status_code=422, detail="Invalid category for income transaction")

    for field, value in transaction_update.model_dump(exclude_unset=True).items():
        setattr(transaction, field, value)

    await db.commit()
    await db.refresh(transaction)
    return BaseResponse(data=transaction)


@app.delete("/api/v1/transactions/{transaction_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_transaction(transaction_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Transaction).where(Transaction.id == transaction_id))
    transaction = result.scalar_one_or_none()
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    await db.delete(transaction)
    await db.commit()