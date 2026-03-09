from fastapi import Depends, HTTPException, status, APIRouter
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from datetime import date
from decimal import Decimal
from sqlalchemy import select, func

from app.schemas import GoalCreate, GoalResponse, GoalUpdate, BaseResponse, TransactionType
from app.database import get_db
from app.models import Goal, Transaction
from app.utils import TEMP_USER_ID

router = APIRouter(
    prefix="/api/v1/goals",
    tags=["Goals"],
)

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


@router.get("/", response_model=BaseResponse[list[GoalResponse]])
async def get_goals(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Goal))
    goals = result.scalars().all()
    spend_by_category = await get_current_spend_all(db, TEMP_USER_ID)
    return BaseResponse(data=[enrich_goal_response(g, spend_by_category) for g in goals])


@router.get("/{goal_id}", response_model=BaseResponse[GoalResponse])
async def get_goal(goal_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Goal).where(Goal.id == goal_id))
    goal = result.scalar_one_or_none()
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    spend_by_category = await get_current_spend_all(db, TEMP_USER_ID)
    return BaseResponse(data=enrich_goal_response(goal, spend_by_category))


@router.post("/", response_model=BaseResponse[GoalResponse], status_code=status.HTTP_201_CREATED)
async def create_goal(goal: GoalCreate, db: AsyncSession = Depends(get_db)):
    new_goal = Goal(**goal.model_dump(), user_id=TEMP_USER_ID)
    db.add(new_goal)
    await db.commit()
    await db.refresh(new_goal)
    spend_by_category = await get_current_spend_all(db, TEMP_USER_ID)
    return BaseResponse(data=enrich_goal_response(new_goal, spend_by_category))


@router.patch("/{goal_id}", response_model=BaseResponse[GoalResponse])
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


@router.delete("/{goal_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_goal(goal_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Goal).where(Goal.id == goal_id))
    goal = result.scalar_one_or_none()
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    await db.delete(goal)
    await db.commit()
