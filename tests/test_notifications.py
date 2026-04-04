import pytest
from httpx import AsyncClient
from sqlalchemy import select
from datetime import date, timedelta
from app.models import Subscription, Transaction, User
from conftest import TestSessionLocal


# Helper to create test subscriptions in the database
async def create_test_sub(name: str, category: str, amount: float, next_due_date: date, is_active: bool = True):
    """Helper to create a subscription directly in the test database."""
    async with TestSessionLocal() as db:
        result = await db.execute(select(User).limit(1))
        user = result.scalar_one()
        
        sub = Subscription(
            user_id=user.id,
            name=name,
            category=category,
            amount=amount,
            billing_type="periodic",
            frequency="monthly",
            next_due_date=next_due_date,
            is_active=is_active,
        )
        db.add(sub)
        await db.commit()
        await db.refresh(sub)
        return sub.id


# ──GET /notifications ────────────────────────────────────────────────────────


async def test_get_notifications_none_due(auth_client: AsyncClient):
    """No notifications when no subscriptions are due."""
    # Create a future-dated subscription
    await create_test_sub("Not Due", "entertainment", 10.00, date.today() + timedelta(days=1))
    
    res = await auth_client.get("/api/v1/notifications")
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data["data"], list)
    assert len(data["data"]) == 0


async def test_get_notifications_due_today_and_overdue(auth_client: AsyncClient):
    """Notifications returned for due and overdue subscriptions, sorted by date."""
    # Create due subscriptions
    await create_test_sub("Overdue", "entertainment", 10.00, date.today() - timedelta(days=1))
    await create_test_sub("Today", "entertainment", 10.00, date.today())
    
    res = await auth_client.get("/api/v1/notifications")
    assert res.status_code == 200
    notifications = res.json()["data"]
    assert len(notifications) == 2
    # Should be ordered with yesterday's first (oldest first)
    assert notifications[0]["next_due_date"] < notifications[1]["next_due_date"]


# ── POST /notifications/{subscription_id}/confirm ────────────────────────────


async def test_confirm_payment_success(auth_client: AsyncClient):
    """Confirming payment creates an expense transaction and advances due_date."""
    sub_id = await create_test_sub("Test Sub", "entertainment", 15.99, date.today())
    
    res = await auth_client.post(f"/api/v1/notifications/{sub_id}/confirm")
    assert res.status_code == 200
    
    subscription_data = res.json()["data"]
    assert subscription_data["next_due_date"] > str(date.today())
    assert subscription_data["name"] == "Test Sub"


async def test_confirm_payment_not_yet_due_rejected(auth_client: AsyncClient):
    """Cannot confirm payment for subscription not yet due."""
    sub_id = await create_test_sub("Future Sub", "entertainment", 10.00, date.today() + timedelta(days=1))
    
    res = await auth_client.post(f"/api/v1/notifications/{sub_id}/confirm")
    assert res.status_code == 400
    assert "not yet due" in res.json()["message"].lower()


async def test_confirm_payment_nonexistent_subscription(auth_client: AsyncClient):
    """Confirming nonexistent subscription returns 404."""
    fake_id = "00000000-0000-0000-0000-000000000000"
    res = await auth_client.post(f"/api/v1/notifications/{fake_id}/confirm")
    assert res.status_code == 404


async def test_confirm_payment_inactive_subscription(auth_client: AsyncClient):
    """Cannot confirm inactive subscription."""
    sub_id = await create_test_sub("Inactive", "entertainment", 11.99, date.today(), is_active=False)
    res = await auth_client.post(f"/api/v1/notifications/{sub_id}/confirm")
    assert res.status_code == 404


# ── POST /notifications/{subscription_id}/dismiss ────────────────────────────


async def test_dismiss_payment_success(auth_client: AsyncClient):
    """Dismissing payment advances due date without creating transaction."""
    sub_id = await create_test_sub("Dismiss Test", "entertainment", 10.00, date.today())
    
    res = await auth_client.post(f"/api/v1/notifications/{sub_id}/dismiss")
    assert res.status_code == 200
    
    subscription_data = res.json()["data"]
    assert subscription_data["next_due_date"] > str(date.today())
    assert subscription_data["name"] == "Dismiss Test"


async def test_dismiss_payment_not_yet_due_rejected(auth_client: AsyncClient):
    """Cannot dismiss payment for subscription not yet due."""
    sub_id = await create_test_sub("Future Sub", "entertainment", 10.00, date.today() + timedelta(days=5))
    
    res = await auth_client.post(f"/api/v1/notifications/{sub_id}/dismiss")
    assert res.status_code == 400
    assert "not yet due" in res.json()["message"].lower()


async def test_dismiss_payment_nonexistent_subscription(auth_client: AsyncClient):
    """Dismissing nonexistent subscription returns 404."""
    fake_id = "00000000-0000-0000-0000-000000000000"
    res = await auth_client.post(f"/api/v1/notifications/{fake_id}/dismiss")
    assert res.status_code == 404


async def test_dismiss_payment_inactive_subscription(auth_client: AsyncClient):
    """Cannot dismiss inactive subscription."""
    sub_id = await create_test_sub("Inactive Dismiss", "entertainment", 19.99, date.today(), is_active=False)
    res = await auth_client.post(f"/api/v1/notifications/{sub_id}/dismiss")
    assert res.status_code == 404


# ── Confirm vs Dismiss Behavior ────────────────────────────────────────────────


async def test_confirm_vs_dismiss_both_advance_date(auth_client: AsyncClient):
    """Both confirm and dismiss advance the next_due_date."""
    sub1_id = await create_test_sub("Confirm Test", "entertainment", 10.00, date.today())
    sub2_id = await create_test_sub("Dismiss Test2", "entertainment", 10.00, date.today() - timedelta(days=1))
    
    res1 = await auth_client.post(f"/api/v1/notifications/{sub1_id}/confirm")
    confirm_new_date = res1.json()["data"]["next_due_date"]
    
    res2 = await auth_client.post(f"/api/v1/notifications/{sub2_id}/dismiss")
    dismiss_new_date = res2.json()["data"]["next_due_date"]
    
    assert confirm_new_date > str(date.today())
    assert dismiss_new_date > str(date.today() - timedelta(days=1))

