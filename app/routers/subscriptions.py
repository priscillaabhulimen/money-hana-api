from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID
from datetime import date

from app.database import get_db
from app.models import User
from app.models.subscription import Subscription
from app.schemas import BaseResponse, SubscriptionCreate, SubscriptionUpdate, SubscriptionResponse
from app.routers.auth import get_current_user
from app.utils.subscription_dates import calculate_next_due_date

router = APIRouter(
    prefix="/api/v1/subscriptions",
    tags=["Subscriptions"],
)


def _calculate_due(data: SubscriptionCreate | SubscriptionUpdate, from_date: date) -> date:
    return calculate_next_due_date(
        billing_type=data.billing_type,
        frequency=data.frequency,
        anchor_day=data.anchor_day,
        anchor_month=data.anchor_month,
        from_date=from_date,
    )


@router.get("/", response_model=BaseResponse[list[SubscriptionResponse]])
async def get_subscriptions(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Subscription)
        .where(Subscription.user_id == current_user.id)
        .order_by(Subscription.next_due_date.asc())
    )
    subscriptions = result.scalars().all()
    return BaseResponse(data=subscriptions)


@router.post("/", response_model=BaseResponse[SubscriptionResponse], status_code=status.HTTP_201_CREATED)
async def create_subscription(
    payload: SubscriptionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    next_due = _calculate_due(payload, date.today())
    subscription = Subscription(
        **payload.model_dump(),
        user_id=current_user.id,
        next_due_date=next_due,
    )
    db.add(subscription)
    await db.commit()
    await db.refresh(subscription)
    return BaseResponse(data=subscription)


@router.get("/{subscription_id}", response_model=BaseResponse[SubscriptionResponse])
async def get_subscription(
    subscription_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Subscription).where(
            Subscription.id == subscription_id,
            Subscription.user_id == current_user.id,
        )
    )
    subscription = result.scalar_one_or_none()
    if not subscription:
        raise HTTPException(status_code=404, detail="Subscription not found")
    return BaseResponse(data=subscription)


@router.patch("/{subscription_id}", response_model=BaseResponse[SubscriptionResponse])
async def update_subscription(
    subscription_id: UUID,
    payload: SubscriptionUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Subscription).where(
            Subscription.id == subscription_id,
            Subscription.user_id == current_user.id,
        )
    )
    subscription = result.scalar_one_or_none()
    if not subscription:
        raise HTTPException(status_code=404, detail="Subscription not found")

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(subscription, field, value)

    # Recalculate next_due_date if billing fields changed
    billing_fields = {"billing_type", "frequency", "anchor_day", "anchor_month"}
    if billing_fields & update_data.keys():
        subscription.next_due_date = calculate_next_due_date(
            billing_type=subscription.billing_type,
            frequency=subscription.frequency,
            anchor_day=subscription.anchor_day,
            anchor_month=subscription.anchor_month,
            from_date=date.today(),
        )

    await db.commit()
    await db.refresh(subscription)
    return BaseResponse(data=subscription)


@router.delete("/{subscription_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_subscription(
    subscription_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Subscription).where(
            Subscription.id == subscription_id,
            Subscription.user_id == current_user.id,
        )
    )
    subscription = result.scalar_one_or_none()
    if not subscription:
        raise HTTPException(status_code=404, detail="Subscription not found")
    await db.delete(subscription)
    await db.commit()