import logging
from datetime import date, timedelta
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import User
from app.models.subscription import Subscription
from app.utils.email import send_email, EmailDeliveryError
from app.utils.email_templates import digest_email

logger = logging.getLogger(__name__)


async def send_weekly_digest(db: AsyncSession) -> None:
    today = date.today()
    week_end = today + timedelta(days=7)

    # Fetch all users
    users_result = await db.execute(select(User))
    users = users_result.scalars().all()

    for user in users:
        # Fetch active subscriptions due this week
        subs_result = await db.execute(
            select(Subscription).where(
                Subscription.user_id == user.id,
                Subscription.is_active == True,
                Subscription.next_due_date >= today,
                Subscription.next_due_date <= week_end,
            )
        )
        subscriptions = subs_result.scalars().all()

        if not subscriptions:
            continue

        due_subscriptions = []
        trial_subscriptions = []

        for sub in subscriptions:
            entry = {
                "name": sub.name,
                "category": sub.category.replace("_", " ").title(),
                "amount": f"{sub.amount:,.2f}",
                "due_date": sub.next_due_date.strftime("%b %d"),
                "trial_ends_at": sub.trial_ends_at.strftime("%b %d") if sub.trial_ends_at else None,
            }
            if sub.is_trial and sub.trial_ends_at and sub.trial_ends_at <= week_end:
                trial_subscriptions.append(entry)
            else:
                due_subscriptions.append(entry)

        if not due_subscriptions and not trial_subscriptions:
            continue

        try:
            await send_email(
                to=user.email,
                subject="Your payments due this week — MoneyHana",
                html=digest_email(
                    first_name=user.first_name,
                    due_subscriptions=due_subscriptions,
                    trial_subscriptions=trial_subscriptions,
                ),
            )
            logger.info(f"Digest sent to {user.email}")
        except EmailDeliveryError:
            logger.exception(f"Failed to send digest to {user.email}")