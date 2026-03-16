"""
Tests for admin feedback/contact/ratings/dashboard endpoints.

All tests mock auth and DB via FastAPI dependency_overrides.
Tests cover: permissions, CRUD, stats, pagination, validation, GDPR delete.
"""
import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi.testclient import TestClient
from fastapi import FastAPI, HTTPException


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_owner():
    from app.auth.jwt_handler import TokenData
    return TokenData(user_id="owner-001", email="fernando.prada@proton.me")


@pytest.fixture
def mock_regular_user():
    from app.auth.jwt_handler import TokenData
    return TokenData(user_id="user-regular-001", email="user@example.com")


def _make_admin_app(user_obj, db_obj, forbidden: bool = False):
    """
    Create a FastAPI app with admin router and dependency overrides.
    If `forbidden=True`, _require_owner raises 403 (simulates non-owner access).
    """
    from app.routers.admin import router, _require_owner
    from app.auth.jwt_handler import get_current_user
    from app.database.turso_client import get_db_client

    app = FastAPI()
    app.include_router(router)

    if forbidden:
        async def _override_owner():
            raise HTTPException(status_code=403, detail="Forbidden")
    else:
        async def _override_owner():
            return user_obj

    async def _override_db():
        return db_obj

    app.dependency_overrides[_require_owner] = _override_owner
    app.dependency_overrides[get_db_client] = _override_db

    return app


def _count_db(n: int = 0):
    db = AsyncMock()
    db.execute.return_value = MagicMock(rows=[{"cnt": n}])
    return db


def _rows_db(rows):
    db = AsyncMock()
    db.execute.return_value = MagicMock(rows=rows)
    return db


# ---------------------------------------------------------------------------
# Permission tests — regular user cannot access admin endpoints
# ---------------------------------------------------------------------------

class TestAdminPermissions:
    def test_non_owner_cannot_list_feedback(self, mock_regular_user):
        db = _count_db()
        app = _make_admin_app(mock_regular_user, db, forbidden=True)
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.get("/api/admin/feedback")
        assert resp.status_code == 403

    def test_non_owner_cannot_get_dashboard(self, mock_regular_user):
        db = _count_db()
        app = _make_admin_app(mock_regular_user, db, forbidden=True)
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.get("/api/admin/dashboard")
        assert resp.status_code == 403

    def test_non_owner_cannot_see_feedback_stats(self, mock_regular_user):
        db = _count_db()
        app = _make_admin_app(mock_regular_user, db, forbidden=True)
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.get("/api/admin/feedback/stats")
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

class TestDashboard:
    def test_dashboard_returns_expected_shape(self, mock_owner):
        db = AsyncMock()

        def _side_effect(sql, *args, **kwargs):
            if "plan_type" in sql and "GROUP BY" in sql:
                return MagicMock(rows=[
                    {"plan_type": "particular", "cnt": 8},
                    {"plan_type": "autonomo", "cnt": 4},
                ])
            return MagicMock(rows=[{"cnt": 10}])

        db.execute.side_effect = _side_effect
        app = _make_admin_app(mock_owner, db)
        client = TestClient(app)
        resp = client.get("/api/admin/dashboard")

        assert resp.status_code == 200
        data = resp.json()
        assert "users" in data
        assert "feedback" in data
        assert "ratings" in data
        assert "contact_requests" in data
        assert "total" in data["users"]
        assert "bugs_open" in data["feedback"]
        assert "positive_pct" in data["ratings"]
        assert "pending" in data["contact_requests"]


# ---------------------------------------------------------------------------
# Feedback list and detail
# ---------------------------------------------------------------------------

class TestAdminFeedbackList:
    def test_list_feedback_excludes_screenshot_data(self, mock_owner):
        db = _rows_db([
            {
                "id": "fb-001",
                "type": "bug",
                "title": "Error en calculo",
                "description": "Detalle del error.",
                "page_url": None,
                "status": "new",
                "priority": "normal",
                "admin_notes": None,
                "user_email": "user@example.com",
                "created_at": "2026-03-16T10:00:00",
                "updated_at": "2026-03-16T10:00:00",
            }
        ])
        app = _make_admin_app(mock_owner, db)
        client = TestClient(app)
        resp = client.get("/api/admin/feedback")

        assert resp.status_code == 200
        items = resp.json()
        assert len(items) == 1
        # screenshot_data is intentionally absent in list endpoint
        assert "screenshot_data" not in items[0]
        assert items[0]["id"] == "fb-001"

    def test_list_feedback_supports_type_filter(self, mock_owner):
        db = _rows_db([])
        app = _make_admin_app(mock_owner, db)
        client = TestClient(app)
        resp = client.get("/api/admin/feedback?type=bug")
        assert resp.status_code == 200

    def test_list_feedback_supports_status_filter(self, mock_owner):
        db = _rows_db([])
        app = _make_admin_app(mock_owner, db)
        client = TestClient(app)
        resp = client.get("/api/admin/feedback?status=new")
        assert resp.status_code == 200

    def test_list_feedback_supports_priority_filter(self, mock_owner):
        db = _rows_db([])
        app = _make_admin_app(mock_owner, db)
        client = TestClient(app)
        resp = client.get("/api/admin/feedback?priority=high")
        assert resp.status_code == 200


class TestAdminFeedbackDetail:
    def test_detail_includes_screenshot_data(self, mock_owner):
        db = _rows_db([
            {
                "id": "fb-001",
                "type": "bug",
                "title": "Error",
                "description": "Detalle.",
                "page_url": None,
                "screenshot_data": "base64encodedpng...",
                "status": "new",
                "priority": "normal",
                "admin_notes": None,
                "user_email": "user@example.com",
                "created_at": "2026-03-16T10:00:00",
                "updated_at": "2026-03-16T10:00:00",
            }
        ])
        app = _make_admin_app(mock_owner, db)
        client = TestClient(app)
        resp = client.get("/api/admin/feedback/fb-001")

        assert resp.status_code == 200
        data = resp.json()
        assert "screenshot_data" in data
        assert data["screenshot_data"] == "base64encodedpng..."

    def test_detail_404_for_missing_id(self, mock_owner):
        db = _rows_db([])
        app = _make_admin_app(mock_owner, db)
        client = TestClient(app)
        resp = client.get("/api/admin/feedback/nonexistent")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Feedback stats — /feedback/stats must resolve BEFORE /feedback/{id}
# ---------------------------------------------------------------------------

class TestFeedbackStats:
    def test_stats_endpoint_resolves_before_id_route(self, mock_owner):
        """
        If FastAPI confused 'stats' with a feedback ID, it would query the DB
        for id='stats' and return 404. This test ensures /feedback/stats returns
        the stats shape, confirming route ordering is correct.
        """
        db = AsyncMock()
        db.execute.side_effect = [
            MagicMock(rows=[{"type": "bug", "cnt": 5}]),        # by_type query
            MagicMock(rows=[{"status": "new", "cnt": 3}]),      # by_status query
            MagicMock(rows=[{"priority": "normal", "cnt": 5}]), # by_priority query
        ]
        app = _make_admin_app(mock_owner, db)
        client = TestClient(app)
        resp = client.get("/api/admin/feedback/stats")

        # Must return stats dict, NOT a 404 "feedback not found"
        assert resp.status_code == 200
        data = resp.json()
        assert "by_type" in data
        assert "by_status" in data
        assert "by_priority" in data


# ---------------------------------------------------------------------------
# Update feedback
# ---------------------------------------------------------------------------

class TestUpdateFeedback:
    def test_update_status_and_notes(self, mock_owner):
        db = AsyncMock()
        # exists check returns a row, UPDATE returns nothing
        db.execute.side_effect = [MagicMock(rows=[{"id": "fb-001"}]), MagicMock(rows=[])]
        app = _make_admin_app(mock_owner, db)
        client = TestClient(app)
        resp = client.put(
            "/api/admin/feedback/fb-001",
            json={"status": "reviewed", "admin_notes": "Confirmado, lo arreglamos."},
        )
        assert resp.status_code == 200
        assert "actualizado" in resp.json()["message"].lower()

    def test_update_invalid_status_returns_400(self, mock_owner):
        db = AsyncMock()
        db.execute.return_value = MagicMock(rows=[{"id": "fb-001"}])
        app = _make_admin_app(mock_owner, db)
        client = TestClient(app)
        resp = client.put(
            "/api/admin/feedback/fb-001",
            json={"status": "invalid_status"},
        )
        assert resp.status_code == 400

    def test_update_invalid_priority_returns_400(self, mock_owner):
        db = AsyncMock()
        db.execute.return_value = MagicMock(rows=[{"id": "fb-001"}])
        app = _make_admin_app(mock_owner, db)
        client = TestClient(app)
        resp = client.put(
            "/api/admin/feedback/fb-001",
            json={"priority": "supercritical"},
        )
        assert resp.status_code == 400

    def test_update_empty_body_returns_400(self, mock_owner):
        db = AsyncMock()
        db.execute.return_value = MagicMock(rows=[{"id": "fb-001"}])
        app = _make_admin_app(mock_owner, db)
        client = TestClient(app)
        resp = client.put("/api/admin/feedback/fb-001", json={})
        assert resp.status_code == 400

    def test_update_404_for_missing_feedback(self, mock_owner):
        db = _rows_db([])
        app = _make_admin_app(mock_owner, db)
        client = TestClient(app)
        resp = client.put(
            "/api/admin/feedback/nonexistent",
            json={"status": "reviewed"},
        )
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Contact requests
# ---------------------------------------------------------------------------

class TestContactRequests:
    def test_list_contact_requests(self, mock_owner):
        db = _rows_db([
            {
                "id": "cr-001",
                "user_id": "u-001",
                "email": "user@example.com",
                "name": "Juan",
                "message": "Quiero informacion sobre el plan autonomo.",
                "request_type": "autonomo_interest",
                "status": "pending",
                "created_at": "2026-03-16T09:00:00",
            }
        ])
        app = _make_admin_app(mock_owner, db)
        client = TestClient(app)
        resp = client.get("/api/admin/contact-requests")

        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["email"] == "user@example.com"

    def test_mark_contact_request_as_responded(self, mock_owner):
        db = AsyncMock()
        db.execute.side_effect = [
            MagicMock(rows=[{"id": "cr-001"}]),  # exists check
            MagicMock(rows=[]),                    # UPDATE
        ]
        app = _make_admin_app(mock_owner, db)
        client = TestClient(app)
        resp = client.put(
            "/api/admin/contact-requests/cr-001",
            json={"status": "responded"},
        )
        assert resp.status_code == 200

    def test_invalid_contact_status_returns_400(self, mock_owner):
        db = _count_db()
        app = _make_admin_app(mock_owner, db)
        client = TestClient(app)
        resp = client.put(
            "/api/admin/contact-requests/cr-001",
            json={"status": "deleted"},
        )
        assert resp.status_code == 400

    def test_contact_request_filter_by_status(self, mock_owner):
        db = _rows_db([])
        app = _make_admin_app(mock_owner, db)
        client = TestClient(app)
        resp = client.get("/api/admin/contact-requests?status=pending")
        assert resp.status_code == 200

    def test_contact_request_404(self, mock_owner):
        db = _rows_db([])
        app = _make_admin_app(mock_owner, db)
        client = TestClient(app)
        resp = client.put(
            "/api/admin/contact-requests/nonexistent",
            json={"status": "responded"},
        )
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Chat ratings — /chat-ratings/stats must resolve BEFORE /chat-ratings
# ---------------------------------------------------------------------------

class TestChatRatingsAdmin:
    def test_stats_resolves_before_list_route(self, mock_owner):
        """
        Ensure /api/admin/chat-ratings/stats does not accidentally match
        the /api/admin/chat-ratings route.
        """
        db = _count_db(100)
        app = _make_admin_app(mock_owner, db)
        client = TestClient(app)
        resp = client.get("/api/admin/chat-ratings/stats")

        assert resp.status_code == 200
        data = resp.json()
        assert "total" in data
        assert "positive_pct" in data
        assert "negative_pct" in data
        assert "trend_30d" in data

    def test_list_chat_ratings(self, mock_owner):
        db = _rows_db([
            {
                "id": "cr-001",
                "user_id": "u-001",
                "user_email": "user@example.com",
                "message_id": "msg-001",
                "conversation_id": "conv-001",
                "rating": 1,
                "comment": None,
                "created_at": "2026-03-16T11:00:00",
            }
        ])
        app = _make_admin_app(mock_owner, db)
        client = TestClient(app)
        resp = client.get("/api/admin/chat-ratings")

        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["rating"] == 1

    def test_filter_by_rating_value(self, mock_owner):
        db = _rows_db([])
        app = _make_admin_app(mock_owner, db)
        client = TestClient(app)
        resp = client.get("/api/admin/chat-ratings?rating=-1")
        assert resp.status_code == 200

    def test_filter_invalid_rating_returns_400(self, mock_owner):
        db = _count_db()
        app = _make_admin_app(mock_owner, db)
        client = TestClient(app)
        resp = client.get("/api/admin/chat-ratings?rating=5")
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# GDPR: deleting account also removes feedback and chat_ratings
# ---------------------------------------------------------------------------

class TestGDPRDelete:
    """
    Verify that user_rights.delete_user_account issues DELETE statements
    for both 'feedback' and 'chat_ratings' tables.
    """

    def test_gdpr_deletes_feedback_and_ratings(self):
        from app.routers.user_rights import delete_user_account
        from app.auth.jwt_handler import TokenData

        mock_user = TokenData(user_id="user-gdpr-001", email="gdpr@test.com")
        mock_db = AsyncMock()
        # All SELECT COUNT queries return 0
        mock_db.execute.return_value = MagicMock(rows=[{"count": 0, "cnt": 0}])

        async def _run():
            return await delete_user_account(current_user=mock_user, db=mock_db)

        result = asyncio.run(_run())

        # Collect all SQL strings executed
        executed_sqls = [call.args[0] for call in mock_db.execute.call_args_list]
        combined = " ".join(executed_sqls)

        assert "feedback" in combined, "GDPR delete must include feedback table"
        assert "chat_ratings" in combined, "GDPR delete must include chat_ratings table"

    def test_gdpr_response_shape(self):
        from app.routers.user_rights import delete_user_account
        from app.auth.jwt_handler import TokenData

        mock_user = TokenData(user_id="user-gdpr-002", email="gdpr2@test.com")
        mock_db = AsyncMock()
        mock_db.execute.return_value = MagicMock(rows=[{"count": 3, "cnt": 3}])

        async def _run():
            return await delete_user_account(current_user=mock_user, db=mock_db)

        result = asyncio.run(_run())
        assert result.user_id == "user-gdpr-002"
        assert "deleted" in result.message.lower()
