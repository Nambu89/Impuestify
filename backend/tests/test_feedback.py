"""
Tests for Feedback and Chat Rating endpoints (user-facing).

All tests run without a real database or real auth — everything is mocked
via FastAPI dependency_overrides (the correct approach for Depends() injection).
Tests cover: creation, listing, rate limiting, duplicate rating, validation.
"""
import asyncio
import base64
import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi.testclient import TestClient
from fastapi import FastAPI, HTTPException


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def valid_png_b64():
    """1x1 pixel transparent PNG — valid magic bytes, tiny size."""
    raw = (
        b"\x89PNG\r\n\x1a\n"
        b"\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
        b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\n"
        b"IDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4"
        b"\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    return base64.b64encode(raw).decode()


@pytest.fixture
def valid_jpeg_b64():
    """Minimal JPEG magic bytes followed by filler — passes magic check."""
    raw = b"\xff\xd8\xff" + b"\x00" * 20
    return base64.b64encode(raw).decode()


@pytest.fixture
def mock_user():
    from app.auth.jwt_handler import TokenData
    return TokenData(user_id="user-test-001", email="user@example.com")


# ---------------------------------------------------------------------------
# Build a wired app with dependency overrides
# ---------------------------------------------------------------------------

def _make_app(mock_user_obj, mock_db_obj):
    """
    Create a fresh FastAPI app with the feedback router mounted and
    dependency overrides applied so tests never touch real auth or DB.
    """
    from app.routers.feedback import router
    from app.auth.jwt_handler import get_current_user
    from app.database.turso_client import get_db_client

    app = FastAPI()
    app.include_router(router)

    async def _override_user():
        return mock_user_obj

    async def _override_db():
        return mock_db_obj

    app.dependency_overrides[get_current_user] = _override_user
    app.dependency_overrides[get_db_client] = _override_db

    return app


def _make_db(count: int = 0, rows=None):
    """Return an AsyncMock DB that returns `rows` (or a count row) for any execute."""
    db = AsyncMock()
    if rows is not None:
        db.execute.return_value = MagicMock(rows=rows)
    else:
        db.execute.return_value = MagicMock(rows=[{"cnt": count}])
    return db


# ---------------------------------------------------------------------------
# POST /api/feedback — happy path
# ---------------------------------------------------------------------------

class TestCreateFeedback:
    def test_create_bug_report_returns_201(self, mock_user, valid_png_b64):
        db = _make_db(count=0)
        # First call returns count=0 (rate limit check), second call is INSERT (no rows needed)
        db.execute.side_effect = [
            MagicMock(rows=[{"cnt": 0}]),  # rate limit SELECT
            MagicMock(rows=[]),             # INSERT
        ]
        app = _make_app(mock_user, db)
        client = TestClient(app)
        resp = client.post(
            "/api/feedback",
            json={
                "type": "bug",
                "title": "Boton no funciona",
                "description": "Al hacer click en el boton de enviar nada ocurre.",
                "page_url": "https://impuestify.com/dashboard",
                "screenshot_data": valid_png_b64,
            },
        )
        assert resp.status_code == 201
        body = resp.json()
        assert "id" in body
        assert "Gracias" in body["message"]

    def test_create_feature_request(self, mock_user):
        db = AsyncMock()
        db.execute.side_effect = [MagicMock(rows=[{"cnt": 0}]), MagicMock(rows=[])]
        app = _make_app(mock_user, db)
        client = TestClient(app)
        resp = client.post(
            "/api/feedback",
            json={
                "type": "feature",
                "title": "Exportar a Excel",
                "description": "Me gustaria poder exportar el calculo de IRPF a formato Excel.",
            },
        )
        assert resp.status_code == 201

    def test_create_general_feedback_no_screenshot(self, mock_user):
        db = AsyncMock()
        db.execute.side_effect = [MagicMock(rows=[{"cnt": 0}]), MagicMock(rows=[])]
        app = _make_app(mock_user, db)
        client = TestClient(app)
        resp = client.post(
            "/api/feedback",
            json={
                "type": "general",
                "title": "Muy buena herramienta",
                "description": "La herramienta es muy util para gestionar mis impuestos como autonomo.",
            },
        )
        assert resp.status_code == 201


# ---------------------------------------------------------------------------
# POST /api/feedback — validation errors (Pydantic, no DB calls needed)
# ---------------------------------------------------------------------------

class TestCreateFeedbackValidation:
    def test_invalid_type_returns_422(self, mock_user):
        db = _make_db()
        app = _make_app(mock_user, db)
        client = TestClient(app)
        resp = client.post(
            "/api/feedback",
            json={"type": "invalid_type", "title": "X" * 10, "description": "Y" * 10},
        )
        assert resp.status_code == 422

    def test_title_too_short_returns_422(self, mock_user):
        db = _make_db()
        app = _make_app(mock_user, db)
        client = TestClient(app)
        resp = client.post(
            "/api/feedback",
            json={"type": "bug", "title": "ab", "description": "Y" * 10},
        )
        assert resp.status_code == 422

    def test_title_too_long_returns_422(self, mock_user):
        db = _make_db()
        app = _make_app(mock_user, db)
        client = TestClient(app)
        resp = client.post(
            "/api/feedback",
            json={"type": "bug", "title": "T" * 101, "description": "Y" * 10},
        )
        assert resp.status_code == 422

    def test_description_too_short_returns_422(self, mock_user):
        db = _make_db()
        app = _make_app(mock_user, db)
        client = TestClient(app)
        resp = client.post(
            "/api/feedback",
            json={"type": "bug", "title": "Titulo correcto", "description": "corto"},
        )
        assert resp.status_code == 422

    def test_screenshot_not_image_returns_422(self, mock_user):
        """Base64 that decodes to non-image bytes must be rejected at Pydantic validation."""
        db = _make_db()
        app = _make_app(mock_user, db)
        client = TestClient(app)
        fake_b64 = base64.b64encode(b"this is not an image at all").decode()
        resp = client.post(
            "/api/feedback",
            json={
                "type": "bug",
                "title": "Titulo correcto",
                "description": "Descripcion suficientemente larga.",
                "screenshot_data": fake_b64,
            },
        )
        assert resp.status_code == 422

    def test_screenshot_invalid_base64_returns_422(self, mock_user):
        db = _make_db()
        app = _make_app(mock_user, db)
        client = TestClient(app)
        resp = client.post(
            "/api/feedback",
            json={
                "type": "bug",
                "title": "Titulo correcto",
                "description": "Descripcion suficientemente larga.",
                "screenshot_data": "not-valid-base64!!!",
            },
        )
        assert resp.status_code == 422

    def test_screenshot_data_uri_prefix_accepted(self, mock_user, valid_png_b64):
        """Clients may send 'data:image/png;base64,...' — the validator must accept it."""
        db = AsyncMock()
        db.execute.side_effect = [MagicMock(rows=[{"cnt": 0}]), MagicMock(rows=[])]
        app = _make_app(mock_user, db)
        client = TestClient(app)
        data_uri = f"data:image/png;base64,{valid_png_b64}"
        resp = client.post(
            "/api/feedback",
            json={
                "type": "bug",
                "title": "Titulo correcto",
                "description": "Descripcion suficientemente larga.",
                "screenshot_data": data_uri,
            },
        )
        assert resp.status_code == 201

    def test_jpeg_screenshot_accepted(self, mock_user, valid_jpeg_b64):
        db = AsyncMock()
        db.execute.side_effect = [MagicMock(rows=[{"cnt": 0}]), MagicMock(rows=[])]
        app = _make_app(mock_user, db)
        client = TestClient(app)
        resp = client.post(
            "/api/feedback",
            json={
                "type": "bug",
                "title": "Screenshot JPEG adjunto",
                "description": "Al hacer click nada ocurre en la pagina.",
                "screenshot_data": valid_jpeg_b64,
            },
        )
        assert resp.status_code == 201


# ---------------------------------------------------------------------------
# POST /api/feedback — rate limiting (10/day)
# ---------------------------------------------------------------------------

class TestFeedbackRateLimit:
    def test_rate_limit_exceeded_returns_429(self, mock_user):
        db = AsyncMock()
        # COUNT returns 10 — already at daily limit
        db.execute.return_value = MagicMock(rows=[{"cnt": 10}])
        app = _make_app(mock_user, db)
        client = TestClient(app)
        resp = client.post(
            "/api/feedback",
            json={
                "type": "bug",
                "title": "Undecimo feedback hoy",
                "description": "Descripcion suficientemente larga.",
            },
        )
        assert resp.status_code == 429
        assert "limite" in resp.json()["detail"].lower()

    def test_rate_limit_not_exceeded_at_9(self, mock_user):
        db = AsyncMock()
        db.execute.side_effect = [MagicMock(rows=[{"cnt": 9}]), MagicMock(rows=[])]
        app = _make_app(mock_user, db)
        client = TestClient(app)
        resp = client.post(
            "/api/feedback",
            json={
                "type": "general",
                "title": "Decimo feedback del dia",
                "description": "Descripcion suficientemente larga para pasar la validacion.",
            },
        )
        assert resp.status_code == 201


# ---------------------------------------------------------------------------
# GET /api/feedback/my
# ---------------------------------------------------------------------------

class TestListMyFeedback:
    def test_returns_own_feedbacks(self, mock_user):
        db = _make_db(rows=[
            {
                "id": "fb-001",
                "type": "bug",
                "title": "Error en calculo",
                "description": "Calculo incorrecto de IRPF.",
                "page_url": None,
                "status": "new",
                "priority": "normal",
                "created_at": "2026-03-16T10:00:00",
                "updated_at": "2026-03-16T10:00:00",
            }
        ])
        app = _make_app(mock_user, db)
        client = TestClient(app)
        resp = client.get("/api/feedback/my")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["id"] == "fb-001"
        assert data[0]["type"] == "bug"
        # screenshot_data must NOT be in the list response
        assert "screenshot_data" not in data[0]

    def test_returns_empty_list_when_no_feedback(self, mock_user):
        db = _make_db(rows=[])
        app = _make_app(mock_user, db)
        client = TestClient(app)
        resp = client.get("/api/feedback/my")
        assert resp.status_code == 200
        assert resp.json() == []


# ---------------------------------------------------------------------------
# POST /api/chat-rating
# ---------------------------------------------------------------------------

class TestChatRating:
    def test_thumbs_up_returns_201(self, mock_user):
        db = AsyncMock()
        # No existing rating, then INSERT
        db.execute.side_effect = [MagicMock(rows=[]), MagicMock(rows=[])]
        app = _make_app(mock_user, db)
        client = TestClient(app)
        resp = client.post("/api/chat-rating", json={"message_id": "msg-001", "rating": 1})
        assert resp.status_code == 201
        assert "id" in resp.json()

    def test_thumbs_down_returns_201(self, mock_user):
        db = AsyncMock()
        db.execute.side_effect = [MagicMock(rows=[]), MagicMock(rows=[])]
        app = _make_app(mock_user, db)
        client = TestClient(app)
        resp = client.post(
            "/api/chat-rating",
            json={"message_id": "msg-002", "rating": -1, "comment": "Respuesta incorrecta"},
        )
        assert resp.status_code == 201

    def test_duplicate_rating_returns_409(self, mock_user):
        db = _make_db(rows=[{"id": "existing-rating-id"}])
        app = _make_app(mock_user, db)
        client = TestClient(app)
        resp = client.post(
            "/api/chat-rating",
            json={"message_id": "msg-already-rated", "rating": 1},
        )
        assert resp.status_code == 409

    def test_invalid_rating_value_returns_422(self, mock_user):
        db = _make_db()
        app = _make_app(mock_user, db)
        client = TestClient(app)
        resp = client.post("/api/chat-rating", json={"message_id": "msg-003", "rating": 5})
        assert resp.status_code == 422

    def test_zero_rating_returns_422(self, mock_user):
        db = _make_db()
        app = _make_app(mock_user, db)
        client = TestClient(app)
        resp = client.post("/api/chat-rating", json={"message_id": "msg-004", "rating": 0})
        assert resp.status_code == 422

    def test_rating_with_conversation_id(self, mock_user):
        db = AsyncMock()
        db.execute.side_effect = [MagicMock(rows=[]), MagicMock(rows=[])]
        app = _make_app(mock_user, db)
        client = TestClient(app)
        resp = client.post(
            "/api/chat-rating",
            json={
                "message_id": "msg-005",
                "conversation_id": "conv-abc",
                "rating": 1,
                "comment": "Excelente respuesta",
            },
        )
        assert resp.status_code == 201


# ---------------------------------------------------------------------------
# Authentication guard: unauthenticated users get 401
# ---------------------------------------------------------------------------

class TestAuthRequired:
    def test_feedback_requires_auth(self):
        from app.routers.feedback import router
        from app.auth.jwt_handler import get_current_user
        from app.database.turso_client import get_db_client

        app = FastAPI()
        app.include_router(router)

        async def _raise_401():
            raise HTTPException(status_code=401, detail="Not authenticated")

        app.dependency_overrides[get_current_user] = _raise_401

        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post(
            "/api/feedback",
            json={"type": "bug", "title": "Test titulo aqui", "description": "Descripcion larga aqui."},
        )
        assert resp.status_code == 401

    def test_list_my_requires_auth(self):
        from app.routers.feedback import router
        from app.auth.jwt_handler import get_current_user

        app = FastAPI()
        app.include_router(router)

        async def _raise_401():
            raise HTTPException(status_code=401, detail="Not authenticated")

        app.dependency_overrides[get_current_user] = _raise_401

        client = TestClient(app, raise_server_exceptions=False)
        resp = client.get("/api/feedback/my")
        assert resp.status_code == 401
