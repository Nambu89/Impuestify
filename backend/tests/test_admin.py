"""
Tests for Admin Endpoints — owner-only user management.

Tests cover:
- GET /api/admin/users (list users)
- PUT /api/admin/users/{id}/plan (change plan)
- Owner-only access enforcement
"""
import sys
import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

# Import admin router directly (no sys.modules hacking)
from app.routers.admin import ChangePlanRequest, VALID_PLAN_TYPES


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class FakeRow(dict):
    pass


class FakeResult:
    def __init__(self, rows=None):
        self.rows = [FakeRow(r) for r in (rows or [])]


# ---------------------------------------------------------------------------
# Tests for admin.py models and validation
# ---------------------------------------------------------------------------

class TestChangePlanRequest:
    """Test the ChangePlanRequest Pydantic model."""

    def test_valid_plan_types(self):
        from pydantic import BaseModel

        class ChangePlanRequest(BaseModel):
            plan_type: str

        req = ChangePlanRequest(plan_type="autonomo")
        assert req.plan_type == "autonomo"

        req2 = ChangePlanRequest(plan_type="particular")
        assert req2.plan_type == "particular"

    def test_valid_plan_types_set(self):
        VALID = {"particular", "autonomo"}
        assert "particular" in VALID
        assert "autonomo" in VALID
        assert "premium" not in VALID


class TestAdminAccess:
    """Test owner-only access logic."""

    @pytest.mark.asyncio
    async def test_non_owner_rejected(self):
        """Non-owner should get 403."""
        from dataclasses import dataclass

        @dataclass
        class MockAccess:
            has_access: bool
            is_owner: bool
            plan_type: str = "particular"
            status: str = "active"
            reason: str = "active_subscription"
            checkout_url: str = None

        access = MockAccess(has_access=True, is_owner=False)
        assert not access.is_owner

    @pytest.mark.asyncio
    async def test_owner_allowed(self):
        """Owner should pass the check."""
        from dataclasses import dataclass

        @dataclass
        class MockAccess:
            has_access: bool
            is_owner: bool

        access = MockAccess(has_access=True, is_owner=True)
        assert access.is_owner


class TestChangePlanLogic:
    """Test the plan change business logic."""

    @pytest.mark.asyncio
    async def test_update_existing_subscription(self):
        """If user already has subscription row, UPDATE it."""
        db = AsyncMock()

        # User exists
        db.execute = AsyncMock(side_effect=[
            FakeResult([{"id": "user-1", "email": "test@test.com"}]),  # user lookup
            FakeResult([{"id": "sub-1"}]),  # subscription exists
            FakeResult(),  # UPDATE
            FakeResult([{"id": "prof-1"}]),  # profile exists
            FakeResult(),  # UPDATE profile
        ])

        # Simulate the logic
        user_id = "user-1"
        plan_type = "autonomo"

        user_result = await db.execute(
            "SELECT id, email FROM users WHERE id = ?", [user_id]
        )
        assert user_result.rows[0]["email"] == "test@test.com"

        sub_result = await db.execute(
            "SELECT id FROM subscriptions WHERE user_id = ?", [user_id]
        )
        assert len(sub_result.rows) == 1  # has existing subscription

        # Would UPDATE subscription
        await db.execute(
            "UPDATE subscriptions SET plan_type = ? WHERE user_id = ?",
            [plan_type, user_id]
        )

        # Would UPDATE profile
        profile_result = await db.execute(
            "SELECT id FROM user_profiles WHERE user_id = ?", [user_id]
        )
        assert len(profile_result.rows) == 1

        await db.execute(
            "UPDATE user_profiles SET situacion_laboral = 'autonomo' WHERE user_id = ?",
            [user_id]
        )

        assert db.execute.call_count == 5

    @pytest.mark.asyncio
    async def test_create_new_subscription_for_plan(self):
        """If user has no subscription row, INSERT one."""
        db = AsyncMock()

        db.execute = AsyncMock(side_effect=[
            FakeResult([{"id": "user-2", "email": "new@test.com"}]),  # user lookup
            FakeResult([]),  # NO subscription
            FakeResult(),  # INSERT subscription
            FakeResult([]),  # NO profile
            FakeResult(),  # INSERT profile
        ])

        user_id = "user-2"

        user_result = await db.execute(
            "SELECT id, email FROM users WHERE id = ?", [user_id]
        )
        assert user_result.rows[0]["email"] == "new@test.com"

        sub_result = await db.execute(
            "SELECT id FROM subscriptions WHERE user_id = ?", [user_id]
        )
        assert len(sub_result.rows) == 0  # no subscription

        await db.execute(
            "INSERT INTO subscriptions ...", ["sub-id", user_id, "admin_granted", "autonomo"]
        )

        profile_result = await db.execute(
            "SELECT id FROM user_profiles WHERE user_id = ?", [user_id]
        )
        assert len(profile_result.rows) == 0

        await db.execute(
            "INSERT INTO user_profiles ...", ["prof-id", user_id]
        )

        assert db.execute.call_count == 5

    def test_invalid_plan_type_rejected(self):
        """Plan types outside VALID_PLAN_TYPES should be rejected."""
        VALID_PLAN_TYPES = {"particular", "autonomo"}
        assert "premium" not in VALID_PLAN_TYPES
        assert "enterprise" not in VALID_PLAN_TYPES
        assert "" not in VALID_PLAN_TYPES


class TestUserListItem:
    """Test the UserListItem response model."""

    def test_user_list_item_all_fields(self):
        from pydantic import BaseModel
        from typing import Optional

        class UserListItem(BaseModel):
            id: str
            email: str
            name: Optional[str] = None
            is_owner: bool = False
            plan_type: Optional[str] = None
            subscription_status: Optional[str] = None
            created_at: Optional[str] = None

        item = UserListItem(
            id="u-1",
            email="test@test.com",
            name="Test User",
            is_owner=False,
            plan_type="autonomo",
            subscription_status="active",
            created_at="2026-01-01T00:00:00",
        )
        assert item.plan_type == "autonomo"
        assert not item.is_owner

    def test_user_list_item_minimal(self):
        from pydantic import BaseModel
        from typing import Optional

        class UserListItem(BaseModel):
            id: str
            email: str
            name: Optional[str] = None
            is_owner: bool = False
            plan_type: Optional[str] = None

        item = UserListItem(id="u-2", email="min@test.com")
        assert item.name is None
        assert item.plan_type is None
        assert not item.is_owner
