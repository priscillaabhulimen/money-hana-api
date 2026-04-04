import pytest
from httpx import AsyncClient
from datetime import date, timedelta
from decimal import Decimal
from sqlalchemy import select
from app.models import Subscription, User
from conftest import TestSessionLocal


# ── Create (POST /subscriptions) ──────────────────────────────────────────────


async def test_create_subscription_periodic_valid(auth_client: AsyncClient):
    """Create periodic subscription with valid data."""
    res = await auth_client.post("/api/v1/subscriptions/", json={
        "name": "Netflix",
        "category": "entertainment",
        "amount": "15.99",
        "billing_type": "periodic",
        "frequency": "monthly",
    })
    assert res.status_code == 201
    data = res.json()["data"]
    assert data["name"] == "Netflix"
    assert float(data["amount"]) == 15.99
    assert data["billing_type"] == "periodic"
    assert data["frequency"] == "monthly"
    assert "next_due_date" in data
    assert data["is_active"] == True


async def test_create_subscription_fixed_monthly_valid(auth_client: AsyncClient):
    """Create fixed-date monthly subscription with anchor_day."""
    res = await auth_client.post("/api/v1/subscriptions/", json={
        "name": "Rent",
        "category": "utilities_bills",
        "amount": "1200.00",
        "billing_type": "fixed_date",
        "frequency": "monthly",
        "anchor_day": 15,
    })
    assert res.status_code == 201
    data = res.json()["data"]
    assert data["anchor_day"] == 15
    assert data["billing_type"] == "fixed_date"
    assert data["frequency"] == "monthly"
    # next_due_date should be on the 15th
    next_due = date.fromisoformat(data["next_due_date"])
    assert next_due.day == 15


async def test_create_subscription_fixed_yearly_valid(auth_client: AsyncClient):
    """Create fixed-date yearly subscription with anchor_day and anchor_month."""
    res = await auth_client.post("/api/v1/subscriptions/", json={
        "name": "Car Insurance",
        "category": "subscriptions",
        "amount": "800.00",
        "billing_type": "fixed_date",
        "frequency": "yearly",
        "anchor_day": 20,
        "anchor_month": 6,
    })
    assert res.status_code == 201
    data = res.json()["data"]
    assert data["anchor_day"] == 20
    assert data["anchor_month"] == 6
    next_due = date.fromisoformat(data["next_due_date"])
    assert next_due.month == 6
    assert next_due.day == 20


async def test_create_subscription_invalid_category(auth_client: AsyncClient):
    """Reject subscription with invalid category."""
    res = await auth_client.post("/api/v1/subscriptions/", json={
        "name": "Invalid",
        "category": "invalid_category",
        "amount": "10.00",
        "billing_type": "periodic",
        "frequency": "monthly",
    })
    assert res.status_code == 422


async def test_create_subscription_missing_anchor_day_for_fixed_monthly(auth_client: AsyncClient):
    """Reject fixed-date monthly without anchor_day."""
    res = await auth_client.post("/api/v1/subscriptions/", json={
        "name": "No Anchor",
        "category": "entertainment",
        "amount": "10.00",
        "billing_type": "fixed_date",
        "frequency": "monthly",
    })
    assert res.status_code == 422


async def test_create_subscription_missing_anchor_month_for_fixed_yearly(auth_client: AsyncClient):
    """Reject fixed-date yearly without anchor_month."""
    res = await auth_client.post("/api/v1/subscriptions/", json={
        "name": "No Anchor Month",
        "category": "entertainment",
        "amount": "10.00",
        "billing_type": "fixed_date",
        "frequency": "yearly",
        "anchor_day": 15,
    })
    assert res.status_code == 422


async def test_create_subscription_invalid_anchor_day(auth_client: AsyncClient):
    """Reject with invalid anchor_day (> 31)."""
    res = await auth_client.post("/api/v1/subscriptions/", json={
        "name": "Invalid Day",
        "category": "entertainment",
        "amount": "10.00",
        "billing_type": "fixed_date",
        "frequency": "monthly",
        "anchor_day": 32,
    })
    assert res.status_code == 422


async def test_create_subscription_invalid_anchor_month(auth_client: AsyncClient):
    """Reject with invalid anchor_month (> 12)."""
    res = await auth_client.post("/api/v1/subscriptions/", json={
        "name": "Invalid Month",
        "category": "entertainment",
        "amount": "10.00",
        "billing_type": "fixed_date",
        "frequency": "yearly",
        "anchor_day": 15,
        "anchor_month": 13,
    })
    assert res.status_code == 422


async def test_create_subscription_sets_user_id(auth_client: AsyncClient):
    """Subscription is associated with current user."""
    res = await auth_client.post("/api/v1/subscriptions/", json={
        "name": "Test User Sub",
        "category": "entertainment",
        "amount": "5.00",
        "billing_type": "periodic",
        "frequency": "monthly",
    })
    assert res.status_code == 201
    sub_id = res.json()["data"]["id"]
    
    # Verify it belongs to the authenticated user
    res = await auth_client.get(f"/api/v1/subscriptions/{sub_id}")
    assert res.status_code == 200


# ── Read (GET /subscriptions) ─────────────────────────────────────────────────


async def test_get_subscriptions_list(auth_client: AsyncClient):
    """Get list of user's subscriptions."""
    # Create two subscriptions
    await auth_client.post("/api/v1/subscriptions/", json={
        "name": "Sub 1",
        "category": "entertainment",
        "amount": "10.00",
        "billing_type": "periodic",
        "frequency": "monthly",
    })
    await auth_client.post("/api/v1/subscriptions/", json={
        "name": "Sub 2",
        "category": "utilities_bills",
        "amount": "50.00",
        "billing_type": "periodic",
        "frequency": "monthly",
    })
    
    res = await auth_client.get("/api/v1/subscriptions/")
    assert res.status_code == 200
    data = res.json()["data"]
    assert len(data) >= 2
    names = [s["name"] for s in data]
    assert "Sub 1" in names
    assert "Sub 2" in names


async def test_get_subscriptions_sorted_by_due_date(auth_client: AsyncClient):
    """Subscriptions are returned sorted by next_due_date."""
    # Create subs with different due dates
    await auth_client.post("/api/v1/subscriptions/", json={
        "name": "Due Later",
        "category": "entertainment",
        "amount": "10.00",
        "billing_type": "fixed_date",
        "frequency": "monthly",
        "anchor_day": 20,
    })
    await auth_client.post("/api/v1/subscriptions/", json={
        "name": "Due Earlier",
        "category": "entertainment",
        "amount": "5.00",
        "billing_type": "fixed_date",
        "frequency": "monthly",
        "anchor_day": 10,
    })
    
    res = await auth_client.get("/api/v1/subscriptions/")
    assert res.status_code == 200
    subs = res.json()["data"]
    # Filter to just the two we created
    filtered = [s for s in subs if s["name"] in ["Due Earlier", "Due Later"]]
    assert len(filtered) == 2
    assert filtered[0]["next_due_date"] <= filtered[1]["next_due_date"]


async def test_get_single_subscription(auth_client: AsyncClient):
    """Get a single subscription by ID."""
    create_res = await auth_client.post("/api/v1/subscriptions/", json={
        "name": "Get Test",
        "category": "entertainment",
        "amount": "7.99",
        "billing_type": "periodic",
        "frequency": "monthly",
    })
    sub_id = create_res.json()["data"]["id"]
    
    res = await auth_client.get(f"/api/v1/subscriptions/{sub_id}")
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["id"] == sub_id
    assert data["name"] == "Get Test"
    assert float(data["amount"]) == 7.99


async def test_get_nonexistent_subscription(auth_client: AsyncClient):
    """Getting nonexistent subscription returns 404."""
    fake_id = "00000000-0000-0000-0000-000000000000"
    res = await auth_client.get(f"/api/v1/subscriptions/{fake_id}")
    assert res.status_code == 404


async def test_get_other_user_subscription_not_found(auth_client: AsyncClient):
    """Cannot access another user's subscription."""
    # Create a subscription as the first user
    create_res = await auth_client.post("/api/v1/subscriptions/", json={
        "name": "Secret Sub",
        "category": "entertainment",
        "amount": "10.00",
        "billing_type": "periodic",
        "frequency": "monthly",
    })
    sub_id = create_res.json()["data"]["id"]
    
    # Try to access with a fake UUID (as if different user)
    fake_id = "99999999-9999-9999-9999-999999999999"
    res = await auth_client.get(f"/api/v1/subscriptions/{fake_id}")
    assert res.status_code == 404


# ── Update (PATCH /subscriptions/{id}) ────────────────────────────────────────


async def test_update_subscription_name(auth_client: AsyncClient):
    """Update subscription name."""
    create_res = await auth_client.post("/api/v1/subscriptions/", json={
        "name": "Old Name",
        "category": "entertainment",
        "amount": "10.00",
        "billing_type": "periodic",
        "frequency": "monthly",
    })
    sub_id = create_res.json()["data"]["id"]
    
    res = await auth_client.patch(f"/api/v1/subscriptions/{sub_id}", json={
        "name": "New Name"
    })
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["name"] == "New Name"


async def test_update_subscription_amount(auth_client: AsyncClient):
    """Update subscription amount."""
    create_res = await auth_client.post("/api/v1/subscriptions/", json={
        "name": "Amount Test",
        "category": "entertainment",
        "amount": "10.00",
        "billing_type": "periodic",
        "frequency": "monthly",
    })
    sub_id = create_res.json()["data"]["id"]
    
    res = await auth_client.patch(f"/api/v1/subscriptions/{sub_id}", json={
        "amount": "20.00"
    })
    assert res.status_code == 200
    data = res.json()["data"]
    assert float(data["amount"]) == 20.00


async def test_update_subscription_is_active(auth_client: AsyncClient):
    """Update subscription is_active status."""
    create_res = await auth_client.post("/api/v1/subscriptions/", json={
        "name": "Active Test",
        "category": "entertainment",
        "amount": "10.00",
        "billing_type": "periodic",
        "frequency": "monthly",
    })
    sub_id = create_res.json()["data"]["id"]
    
    res = await auth_client.patch(f"/api/v1/subscriptions/{sub_id}", json={
        "is_active": False
    })
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["is_active"] == False


async def test_update_subscription_recalculates_due_date_on_frequency_change(auth_client: AsyncClient):
    """Changing billing fields recalculates next_due_date."""
    create_res = await auth_client.post("/api/v1/subscriptions/", json={
        "name": "Recalc Test",
        "category": "entertainment",
        "amount": "10.00",
        "billing_type": "periodic",
        "frequency": "monthly",
    })
    sub_id = create_res.json()["data"]["id"]
    original_due = create_res.json()["data"]["next_due_date"]
    
    # Change frequency to weekly
    res = await auth_client.patch(f"/api/v1/subscriptions/{sub_id}", json={
        "frequency": "weekly"
    })
    assert res.status_code == 200
    new_due = res.json()["data"]["next_due_date"]
    # Due date should change (weekly is sooner than monthly)
    assert new_due != original_due


async def test_update_subscription_recalculates_due_date_on_anchor_change(auth_client: AsyncClient):
    """Changing anchor_day recalculates next_due_date."""
    create_res = await auth_client.post("/api/v1/subscriptions/", json={
        "name": "Anchor Test",
        "category": "entertainment",
        "amount": "10.00",
        "billing_type": "fixed_date",
        "frequency": "monthly",
        "anchor_day": 10,
    })
    sub_id = create_res.json()["data"]["id"]
    original_due = date.fromisoformat(create_res.json()["data"]["next_due_date"])
    
    # Change anchor_day to 25
    res = await auth_client.patch(f"/api/v1/subscriptions/{sub_id}", json={
        "anchor_day": 25
    })
    assert res.status_code == 200
    new_due = date.fromisoformat(res.json()["data"]["next_due_date"])
    assert new_due.day == 25


async def test_update_nonexistent_subscription(auth_client: AsyncClient):
    """Updating nonexistent subscription returns 404."""
    fake_id = "00000000-0000-0000-0000-000000000000"
    res = await auth_client.patch(f"/api/v1/subscriptions/{fake_id}", json={
        "name": "Should Fail"
    })
    assert res.status_code == 404


async def test_update_other_user_subscription_not_found(auth_client: AsyncClient):
    """Cannot update another user's subscription."""
    fake_id = "99999999-9999-9999-9999-999999999999"
    res = await auth_client.patch(f"/api/v1/subscriptions/{fake_id}", json={
        "name": "Hacked"
    })
    assert res.status_code == 404


async def test_update_subscription_invalid_category(auth_client: AsyncClient):
    """Updating with invalid category fails."""
    create_res = await auth_client.post("/api/v1/subscriptions/", json={
        "name": "Category Test",
        "category": "entertainment",
        "amount": "10.00",
        "billing_type": "periodic",
        "frequency": "monthly",
    })
    sub_id = create_res.json()["data"]["id"]
    
    res = await auth_client.patch(f"/api/v1/subscriptions/{sub_id}", json={
        "category": "bad_category"
    })
    assert res.status_code == 422


# ── Delete (DELETE /subscriptions/{id}) ──────────────────────────────────────


async def test_delete_subscription_success(auth_client: AsyncClient):
    """Delete subscription successfully."""
    create_res = await auth_client.post("/api/v1/subscriptions/", json={
        "name": "Delete Me",
        "category": "entertainment",
        "amount": "10.00",
        "billing_type": "periodic",
        "frequency": "monthly",
    })
    sub_id = create_res.json()["data"]["id"]
    
    res = await auth_client.delete(f"/api/v1/subscriptions/{sub_id}")
    assert res.status_code == 204
    
    # Verify it's gone
    res = await auth_client.get(f"/api/v1/subscriptions/{sub_id}")
    assert res.status_code == 404


async def test_delete_nonexistent_subscription(auth_client: AsyncClient):
    """Deleting nonexistent subscription returns 404."""
    fake_id = "00000000-0000-0000-0000-000000000000"
    res = await auth_client.delete(f"/api/v1/subscriptions/{fake_id}")
    assert res.status_code == 404


async def test_delete_other_user_subscription_not_found(auth_client: AsyncClient):
    """Cannot delete another user's subscription."""
    fake_id = "99999999-9999-9999-9999-999999999999"
    res = await auth_client.delete(f"/api/v1/subscriptions/{fake_id}")
    assert res.status_code == 404


# ── Authorization & Isolation ────────────────────────────────────────────────


async def test_subscriptions_only_show_own_subscriptions(auth_client: AsyncClient):
    """User only sees their own subscriptions in list."""
    # Create multiple subscriptions for the authenticated user
    name1 = "My Sub 1"
    name2 = "My Sub 2"
    
    await auth_client.post("/api/v1/subscriptions/", json={
        "name": name1,
        "category": "entertainment",
        "amount": "10.00",
        "billing_type": "periodic",
        "frequency": "monthly",
    })
    
    await auth_client.post("/api/v1/subscriptions/", json={
        "name": name2,
        "category": "utilities_bills",
        "amount": "50.00",
        "billing_type": "periodic",
        "frequency": "monthly",
    })
    
    # List subscriptions - should see both
    res = await auth_client.get("/api/v1/subscriptions/")
    assert res.status_code == 200
    subs = res.json()["data"]
    names = [s["name"] for s in subs]
    assert name1 in names
    assert name2 in names


async def test_unauthenticated_cannot_create_subscription(client: AsyncClient):
    """Unauthenticated user cannot create subscription."""
    res = await client.post("/api/v1/subscriptions/", json={
        "name": "Hacked",
        "category": "entertainment",
        "amount": "10.00",
        "billing_type": "periodic",
        "frequency": "monthly",
    })
    assert res.status_code == 401


async def test_unauthenticated_cannot_list_subscriptions(client: AsyncClient):
    """Unauthenticated user cannot list subscriptions."""
    res = await client.get("/api/v1/subscriptions/")
    assert res.status_code == 401


async def test_unauthenticated_cannot_get_subscription(client: AsyncClient):
    """Unauthenticated user cannot get a subscription."""
    fake_id = "00000000-0000-0000-0000-000000000000"
    res = await client.get(f"/api/v1/subscriptions/{fake_id}")
    assert res.status_code == 401


async def test_unauthenticated_cannot_update_subscription(client: AsyncClient):
    """Unauthenticated user cannot update subscription."""
    fake_id = "00000000-0000-0000-0000-000000000000"
    res = await client.patch(f"/api/v1/subscriptions/{fake_id}", json={"name": "Hacked"})
    assert res.status_code == 401


async def test_unauthenticated_cannot_delete_subscription(client: AsyncClient):
    """Unauthenticated user cannot delete subscription."""
    fake_id = "00000000-0000-0000-0000-000000000000"
    res = await client.delete(f"/api/v1/subscriptions/{fake_id}")
    assert res.status_code == 401
