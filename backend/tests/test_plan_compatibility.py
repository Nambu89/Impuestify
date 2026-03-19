"""
Tests for plan-role compatibility validation — TaxIA/Impuestify

Covers:
- validate_plan_role_compatibility() helper (unit tests)
- update_fiscal_profile endpoint 403/200 behaviour (integration tests)
"""
import sys
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# ---------------------------------------------------------------------------
# Stub heavy deps before importing app modules
# ---------------------------------------------------------------------------

def _ensure_mock(module_name, **attrs):
    """Insert a MagicMock into sys.modules if the real module is absent."""
    if module_name not in sys.modules:
        mock = MagicMock()
        for k, v in attrs.items():
            setattr(mock, k, v)
        sys.modules[module_name] = mock


_ensure_mock("jose")
_ensure_mock("jose.exceptions")
_ensure_mock("bcrypt")
_ensure_mock("slowapi")
_ensure_mock("slowapi.util")
_ensure_mock("slowapi.errors")
_ensure_mock("stripe")


# ---------------------------------------------------------------------------
# Real imports
# ---------------------------------------------------------------------------

from app.services.subscription_service import (  # noqa: E402
    validate_plan_role_compatibility,
    SubscriptionAccess,
    SubscriptionService,
)


# ---------------------------------------------------------------------------
# Unit tests — validate_plan_role_compatibility()
# ---------------------------------------------------------------------------

class TestValidatePlanRoleCompatibility:
    """Unit tests for the standalone helper function."""

    # 1. Particular + asalariado → compatible
    def test_particular_asalariado_ok(self):
        result = validate_plan_role_compatibility("particular", "asalariado")
        assert result is None

    # 2. Particular + autonomo → incompatible, requires autonomo plan
    def test_particular_autonomo_incompatible(self):
        result = validate_plan_role_compatibility("particular", "autonomo")
        assert result is not None
        assert result["required_plan"] == "autonomo"
        assert result["current_plan"] == "particular"

    # 3. None plan (defaults to particular) + autonomo → incompatible
    def test_none_plan_treated_as_particular(self):
        result = validate_plan_role_compatibility(None, "autonomo")
        assert result is not None
        assert result["required_plan"] == "autonomo"
        assert result["current_plan"] == "particular"

    # 4. Particular + pensionista → compatible
    def test_particular_pensionista_ok(self):
        result = validate_plan_role_compatibility("particular", "pensionista")
        assert result is None

    # 5. Particular + creador → incompatible, requires creator plan
    def test_particular_creador_requires_creator(self):
        result = validate_plan_role_compatibility("particular", "creador")
        assert result is not None
        assert result["required_plan"] == "creator"
        assert result["current_plan"] == "particular"

    # 6. Creator + creador → compatible
    def test_creator_creador_ok(self):
        result = validate_plan_role_compatibility("creator", "creador")
        assert result is None

    # 7. Creator + youtuber → compatible
    def test_creator_youtuber_ok(self):
        result = validate_plan_role_compatibility("creator", "youtuber")
        assert result is None

    # 8. Creator + autonomo → incompatible, requires autonomo plan
    def test_creator_autonomo_incompatible(self):
        result = validate_plan_role_compatibility("creator", "autonomo")
        assert result is not None
        assert result["required_plan"] == "autonomo"
        assert result["current_plan"] == "creator"

    # 9. Autonomo + autonomo → compatible (all roles allowed)
    def test_autonomo_autonomo_ok(self):
        result = validate_plan_role_compatibility("autonomo", "autonomo")
        assert result is None

    # 10. Autonomo + creador → compatible
    def test_autonomo_creador_ok(self):
        result = validate_plan_role_compatibility("autonomo", "creador")
        assert result is None

    # 11. is_owner=True bypasses all restrictions
    def test_owner_bypasses_all(self):
        result = validate_plan_role_compatibility("particular", "autonomo", is_owner=True)
        assert result is None

    # 12. Case-insensitive matching
    def test_case_insensitive(self):
        result = validate_plan_role_compatibility("particular", "ASALARIADO")
        assert result is None

    # 13. Extra whitespace in situacion
    def test_strips_whitespace(self):
        result = validate_plan_role_compatibility("particular", "  asalariado  ")
        assert result is None

    # 14. Empty situacion string → treated as allowed (no restriction)
    def test_empty_situacion_ok(self):
        result = validate_plan_role_compatibility("particular", "")
        assert result is None


# ---------------------------------------------------------------------------
# Integration tests — update_fiscal_profile endpoint
# ---------------------------------------------------------------------------
# We mock the subscription service so no DB is needed.
# ---------------------------------------------------------------------------

class FakeRow(dict):
    pass


class FakeResult:
    def __init__(self, rows=None):
        self.rows = rows or []
        self.rowcount = len(self.rows)


def _make_access(plan_type, is_owner=False):
    """Build a SubscriptionAccess object for mocking."""
    return SubscriptionAccess(
        has_access=True,
        is_owner=is_owner,
        plan_type=plan_type,
        status="active",
        reason="active_subscription" if not is_owner else "owner",
    )


@pytest.fixture
def mock_db():
    db = AsyncMock()
    # Default: profile does not exist yet
    db.execute.return_value = FakeResult([])
    return db


def _make_mock_sub_service(plan_type, is_owner=False):
    """Return an async mock get_subscription_service() that yields the given access."""
    service = AsyncMock(spec=SubscriptionService)
    service.check_access.return_value = _make_access(plan_type, is_owner)
    return service


def _mock_current_user(user_id="user-123", email="test@impuestify.com"):
    user = MagicMock()
    user.user_id = user_id
    user.email = email
    return user


# We import the router after stubs are in place.
from app.routers.user_rights import update_fiscal_profile  # noqa: E402
from app.routers.user_rights import FiscalProfileRequest   # noqa: E402
from fastapi import HTTPException                          # noqa: E402


async def _call_endpoint(body_data: dict, plan_type: str, is_owner: bool = False):
    """Helper to call update_fiscal_profile with mocked deps."""
    body = FiscalProfileRequest(**body_data)
    current_user = _mock_current_user()
    mock_db = AsyncMock()
    mock_db.execute.return_value = FakeResult([])  # no existing profile

    mock_service = _make_mock_sub_service(plan_type, is_owner)

    with patch(
        "app.routers.user_rights.get_subscription_service",
        return_value=mock_service,
    ):
        return await update_fiscal_profile(body=body, current_user=current_user, db=mock_db)


class TestUpdateFiscalProfilePlanCheck:
    """Integration tests: plan-role check inside update_fiscal_profile endpoint."""

    # T1. Particular + asalariado → 200
    @pytest.mark.asyncio
    async def test_particular_asalariado_ok(self):
        result = await _call_endpoint({"situacion_laboral": "asalariado"}, "particular")
        assert result["message"] == "Perfil fiscal guardado correctamente"

    # T2. Particular + autonomo → 403 with correct body
    @pytest.mark.asyncio
    async def test_particular_autonomo_403(self):
        with pytest.raises(HTTPException) as exc_info:
            await _call_endpoint({"situacion_laboral": "autonomo"}, "particular")
        exc = exc_info.value
        assert exc.status_code == 403
        assert exc.detail["detail"] == "plan_incompatible"
        assert exc.detail["required_plan"] == "autonomo"
        assert exc.detail["current_plan"] == "particular"
        assert exc.detail["upgrade_url"] == "/subscribe"

    # T3. Particular + creador → 403
    @pytest.mark.asyncio
    async def test_particular_creador_403(self):
        with pytest.raises(HTTPException) as exc_info:
            await _call_endpoint({"situacion_laboral": "creador"}, "particular")
        exc = exc_info.value
        assert exc.status_code == 403
        assert exc.detail["required_plan"] == "creator"

    # T4. Creator + creador → 200
    @pytest.mark.asyncio
    async def test_creator_creador_ok(self):
        result = await _call_endpoint({"situacion_laboral": "creador"}, "creator")
        assert result["message"] == "Perfil fiscal guardado correctamente"

    # T5. Creator + autonomo → 403
    @pytest.mark.asyncio
    async def test_creator_autonomo_403(self):
        with pytest.raises(HTTPException) as exc_info:
            await _call_endpoint({"situacion_laboral": "autonomo"}, "creator")
        exc = exc_info.value
        assert exc.status_code == 403
        assert exc.detail["required_plan"] == "autonomo"

    # T6. Autonomo + autonomo → 200
    @pytest.mark.asyncio
    async def test_autonomo_autonomo_ok(self):
        result = await _call_endpoint({"situacion_laboral": "autonomo"}, "autonomo")
        assert result["message"] == "Perfil fiscal guardado correctamente"

    # T7. Owner with particular plan + autonomo → 200 (bypassed)
    @pytest.mark.asyncio
    async def test_owner_bypasses_restriction(self):
        result = await _call_endpoint(
            {"situacion_laboral": "autonomo"}, "particular", is_owner=True
        )
        assert result["message"] == "Perfil fiscal guardado correctamente"

    # T8. No situacion_laboral in request → no check, 200
    @pytest.mark.asyncio
    async def test_no_situacion_skips_check(self):
        # Subscription service should NOT be called if situacion is absent
        body = FiscalProfileRequest(ccaa_residencia="Madrid")
        current_user = _mock_current_user()
        mock_db = AsyncMock()
        mock_db.execute.return_value = FakeResult([])

        mock_service = AsyncMock(spec=SubscriptionService)

        with patch(
            "app.routers.user_rights.get_subscription_service",
            return_value=mock_service,
        ):
            result = await update_fiscal_profile(
                body=body, current_user=current_user, db=mock_db
            )

        mock_service.check_access.assert_not_called()
        assert result["message"] == "Perfil fiscal guardado correctamente"

    # T9. 403 detail contains user-visible message with tildes
    @pytest.mark.asyncio
    async def test_403_message_has_plan_name(self):
        with pytest.raises(HTTPException) as exc_info:
            await _call_endpoint({"situacion_laboral": "autonomo"}, "particular")
        message = exc_info.value.detail["message"]
        assert "Particular" in message or "particular" in message.lower()
        assert "autónomo" in message or "autonomo" in message.lower()

    # T10. Desempleado allowed on particular plan
    @pytest.mark.asyncio
    async def test_particular_desempleado_ok(self):
        result = await _call_endpoint({"situacion_laboral": "desempleado"}, "particular")
        assert result["message"] == "Perfil fiscal guardado correctamente"
