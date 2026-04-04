from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID
from datetime import date

from app.database import get_db
from app.models import User, Transaction
from app.models.subscription import Subscription
from app.schemas import BaseResponse, SubscriptionResponse
from app.schemas.enums import TransactionType
from app.routers.auth import get_current_user
from app.utils.subscription_dates import advance_due_date

router = APIRouter(
    prefix="/api/v1/notifications",
    tags=["Notifications"],
)


@router.get("/", response_model=BaseResponse[list[SubscriptionResponse]])
async def get_notifications(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Returns subscriptions where next_due_date has passed and is_active is true."""
    result = await db.execute(
        select(Subscription).where(
            Subscription.user_id == current_user.id,
            Subscription.is_active == True,
            Subscription.next_due_date <= date.today(),
        ).order_by(Subscription.next_due_date.asc())
    )
    subscriptions = result.scalars().all()
    return BaseResponse(data=subscriptions)


@router.post("/{subscription_id}/confirm", response_model=BaseResponse[SubscriptionResponse])
@router.post("/{subscription_id}/confirm/", response_model=BaseResponse[SubscriptionResponse])
async def confirm_payment(
    subscription_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Confirms payment — creates an expense transaction and advances next_due_date."""
    result = await db.execute(
        select(Subscription).where(
            Subscription.id == subscription_id,
            Subscription.user_id == current_user.id,
            Subscription.is_active == True,
        )
    )
    subscription = result.scalar_one_or_none()
    if not subscription:
        raise HTTPException(status_code=404, detail="Subscription not found")

    if subscription.next_due_date > date.today():
        raise HTTPException(status_code=400, detail="Payment is not yet due")

    # Create expense transaction
    transaction = Transaction(
        user_id=current_user.id,
        transaction_type=TransactionType.expense,
        amount=subscription.amount,
        category=subscription.category,
        date=subscription.next_due_date,
        note=f"{subscription.name} — auto-logged from subscription",
    )
    db.add(transaction)

    # Advance due date
    subscription.next_due_date = advance_due_date(subscription)

    await db.commit()
    await db.refresh(subscription)
    return BaseResponse(
        data=subscription,
        message="Payment confirmed and logged as an expense.",
    )


@router.post("/{subscription_id}/dismiss", response_model=BaseResponse[SubscriptionResponse])
@router.post("/{subscription_id}/dismiss/", response_model=BaseResponse[SubscriptionResponse])
async def dismiss_payment(
    subscription_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Dismisses notification — advances next_due_date without creating a transaction."""
    result = await db.execute(
        select(Subscription).where(
            Subscription.id == subscription_id,
            Subscription.user_id == current_user.id,
            Subscription.is_active == True,
        )
    )
    subscription = result.scalar_one_or_none()
    if not subscription:
        raise HTTPException(status_code=404, detail="Subscription not found")

    if subscription.next_due_date > date.today():
        raise HTTPException(status_code=400, detail="Payment is not yet due")

    subscription.next_due_date = advance_due_date(subscription)

    await db.commit()
    await db.refresh(subscription)
    return BaseResponse(
        data=subscription,
        message="Payment dismissed. Due date advanced to next cycle.",
    )