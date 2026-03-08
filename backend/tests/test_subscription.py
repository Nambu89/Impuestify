"""
Tests for Subscription System — TaxIA/Impuestify

Tests cover:
- SubscriptionService.check_access() with various statuses
- content_restriction.detect_autonomo_query()
- Subscription guard dependency behavior
"""
import sys
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta
from dataclasses import asdict


# ---------------------------------------------------------------------------
# Patch heavy dependencies before importing app modules.
# subscription_service only needs app.config (pydantic Settings).
# content_restriction has no heavy deps.
# ---------------------------------------------------------------------------

def _ensure_mock(module_name, **attrs):
    """Insert a MagicMock into sys.modules if the real module is absent."""
    if module_name not in sys.modules:
        mock = MagicMock()
        for k, v in attrs.items():
            setattr(mock, k, v)
        sys.modules[module_name] = mock

# These may not be installed in the test venv
_ensure_mock("jose")
_ensure_mock("jose.exceptions")
_ensure_mock("bcrypt")
_ensure_mock("slowapi")
_ensure_mock("slowapi.util")
_ensure_mock("slowapi.errors")
_ensure_mock("stripe")

# ---------------------------------------------------------------------------
# Direct imports from the real modules
# ---------------------------------------------------------------------------

from app.services.subscription_service import SubscriptionService, SubscriptionAccess  # noqa: E402
from app.security.content_restriction import (  # noqa: E402
    detect_autonomo_query,
    get_autonomo_block_response,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

class FakeRow(dict):
    """Dict subclass that supports both dict access and .get()."""
    pass


class FakeResult:
    """Mimics Turso query result."""
    def __init__(self, rows=None):
        self.rows = rows or []
        self.rowcount = len(self.rows)


@pytest.fixture
def mock_db():
    """Create a mock database client."""
    db = AsyncMock()
    return db


@pytest.fixture
def service(mock_db):
    """Create a SubscriptionService with mocked DB."""
    return SubscriptionService(db=mock_db)


# ---------------------------------------------------------------------------
# check_access() tests
# ---------------------------------------------------------------------------

class TestCheckAccess:
    """Tests for SubscriptionService.check_access()."""

    @pytest.mark.asyncio
    async def test_owner_by_email(self, service):
        """Owner email gets full access regardless of DB state."""
        with patch("app.services.subscription_service.settings") as mock_settings:
            mock_settings.OWNER_EMAIL = "owner@example.com"

            access = await service.check_access(
                user_id="user-1", email="owner@example.com"
            )

        assert access.has_access is True
        assert access.is_owner is True
        assert access.status == "active"
        assert access.reason == "owner"

    @pytest.mark.asyncio
    async def test_owner_by_email_case_insensitive(self, service):
        """Owner email matching is case-insensitive."""
        with patch("app.services.subscription_service.settings") as mock_settings:
            mock_settings.OWNER_EMAIL = "owner@example.com"

            access = await service.check_access(
                user_id="user-1", email="OWNER@Example.COM"
            )

        assert access.has_access is True
        assert access.is_owner is True

    @pytest.mark.asyncio
    async def test_owner_by_db_flag(self, service, mock_db):
        """User with is_owner=True in DB gets full access."""
        with patch("app.services.subscription_service.settings") as mock_settings:
            mock_settings.OWNER_EMAIL = "other@example.com"

            mock_db.execute.return_value = FakeResult([
                FakeRow({"is_owner": True, "plan_type": "owner", "status": "active", "current_period_end": None})
            ])

            access = await service.check_access(
                user_id="user-1", email="user@example.com"
            )

        assert access.has_access is True
        assert access.is_owner is True
        assert access.reason == "owner"

    @pytest.mark.asyncio
    async def test_active_subscription(self, service, mock_db):
        """User with active subscription has access."""
        with patch("app.services.subscription_service.settings") as mock_settings:
            mock_settings.OWNER_EMAIL = "other@example.com"

            mock_db.execute.return_value = FakeResult([
                FakeRow({"is_owner": False, "plan_type": "particular", "status": "active", "current_period_end": None})
            ])

            access = await service.check_access(
                user_id="user-2", email="user@example.com"
            )

        assert access.has_access is True
        assert access.is_owner is False
        assert access.status == "active"
        assert access.reason == "active_subscription"

    @pytest.mark.asyncio
    async def test_grace_period_valid(self, service, mock_db):
        """User in grace period with future end date has access."""
        future_date = (datetime.utcnow() + timedelta(days=365)).isoformat()

        with patch("app.services.subscription_service.settings") as mock_settings:
            mock_settings.OWNER_EMAIL = "other@example.com"

            mock_db.execute.return_value = FakeResult([
                FakeRow({
                    "is_owner": False,
                    "plan_type": "particular",
                    "status": "grace_period",
                    "current_period_end": future_date,
                })
            ])

            access = await service.check_access(
                user_id="user-3", email="user@example.com"
            )

        assert access.has_access is True
        assert access.status == "grace_period"
        assert access.reason == "grace_period"

    @pytest.mark.asyncio
    async def test_grace_period_expired(self, service, mock_db):
        """User in grace period with past end date has NO access."""
        past_date = (datetime.utcnow() - timedelta(days=1)).isoformat()

        with patch("app.services.subscription_service.settings") as mock_settings:
            mock_settings.OWNER_EMAIL = "other@example.com"

            mock_db.execute.return_value = FakeResult([
                FakeRow({
                    "is_owner": False,
                    "plan_type": "particular",
                    "status": "grace_period",
                    "current_period_end": past_date,
                })
            ])

            access = await service.check_access(
                user_id="user-4", email="user@example.com"
            )

        assert access.has_access is False
        assert access.reason == "no_active_subscription"

    @pytest.mark.asyncio
    async def test_inactive_subscription(self, service, mock_db):
        """User with inactive subscription has NO access."""
        with patch("app.services.subscription_service.settings") as mock_settings:
            mock_settings.OWNER_EMAIL = "other@example.com"

            mock_db.execute.return_value = FakeResult([
                FakeRow({"is_owner": False, "plan_type": "particular", "status": "inactive", "current_period_end": None})
            ])

            access = await service.check_access(
                user_id="user-5", email="user@example.com"
            )

        assert access.has_access is False
        assert access.status == "inactive"
        assert access.reason == "no_active_subscription"

    @pytest.mark.asyncio
    async def test_canceled_subscription(self, service, mock_db):
        """User with canceled subscription has NO access."""
        with patch("app.services.subscription_service.settings") as mock_settings:
            mock_settings.OWNER_EMAIL = "other@example.com"

            mock_db.execute.return_value = FakeResult([
                FakeRow({"is_owner": False, "plan_type": "particular", "status": "canceled", "current_period_end": None})
            ])

            access = await service.check_access(
                user_id="user-6", email="user@example.com"
            )

        assert access.has_access is False
        assert access.status == "canceled"

    @pytest.mark.asyncio
    async def test_user_not_found(self, service, mock_db):
        """Non-existent user has NO access."""
        with patch("app.services.subscription_service.settings") as mock_settings:
            mock_settings.OWNER_EMAIL = "other@example.com"

            mock_db.execute.return_value = FakeResult([])

            access = await service.check_access(
                user_id="nonexistent", email="nobody@example.com"
            )

        assert access.has_access is False
        assert access.reason == "user_not_found"

    @pytest.mark.asyncio
    async def test_past_due_no_access(self, service, mock_db):
        """User with past_due status has NO access."""
        with patch("app.services.subscription_service.settings") as mock_settings:
            mock_settings.OWNER_EMAIL = "other@example.com"

            mock_db.execute.return_value = FakeResult([
                FakeRow({"is_owner": False, "plan_type": "particular", "status": "past_due", "current_period_end": None})
            ])

            access = await service.check_access(
                user_id="user-7", email="user@example.com"
            )

        assert access.has_access is False
        assert access.status == "past_due"


# ---------------------------------------------------------------------------
# detect_autonomo_query() tests
# ---------------------------------------------------------------------------

class TestDetectAutonomoQuery:
    """Tests for content_restriction.detect_autonomo_query()."""

    def test_direct_autonomo_mention(self):
        assert detect_autonomo_query("¿Cuánto paga un autónomo?") is True

    def test_cuota_autonomos(self):
        assert detect_autonomo_query("¿Cuál es la cuota de autónomos en 2025?") is True

    def test_modelo_130_action(self):
        # General question about modelo 130 is now allowed; only action-specific blocked
        assert detect_autonomo_query("¿Qué es el modelo 130?") is False
        assert detect_autonomo_query("presentar modelo 130") is True

    def test_modelo_303_action(self):
        # General question about modelo 303 is now allowed; only action-specific blocked
        assert detect_autonomo_query("¿Qué es el modelo 303?") is False
        assert detect_autonomo_query("rellenar modelo 303") is True

    def test_iva_trimestral(self):
        assert detect_autonomo_query("¿Cuándo hay que pagar el IVA trimestral?") is True

    def test_facturacion(self):
        assert detect_autonomo_query("¿Cómo emitir factura como freelance?") is True

    def test_estimacion_directa(self):
        assert detect_autonomo_query("¿Qué es la estimación directa?") is True

    def test_tarifa_plana(self):
        assert detect_autonomo_query("¿Puedo acogerme a la tarifa plana autónomos?") is True

    def test_reta(self):
        assert detect_autonomo_query("¿Cómo funciona el RETA?") is True

    def test_case_insensitive(self):
        assert detect_autonomo_query("SOY AUTÓNOMO Y QUIERO SABER MI CUOTA") is True

    # Negative cases — salaried worker queries that should NOT be blocked

    def test_irpf_asalariado(self):
        assert detect_autonomo_query("¿Cómo calculo el IRPF de mi nómina?") is False

    def test_nomina_question(self):
        assert detect_autonomo_query("¿Es correcto el IRPF de mi nómina?") is False

    def test_modelo_100(self):
        assert detect_autonomo_query("¿Cuándo presento el modelo 100?") is False

    def test_aeat_notification(self):
        assert detect_autonomo_query("Me ha llegado una notificación de la AEAT") is False

    def test_generic_tax_question(self):
        assert detect_autonomo_query("¿Qué es el IRPF?") is False

    def test_deduccion_vivienda(self):
        assert detect_autonomo_query("¿Puedo deducir la hipoteca en la renta?") is False

    def test_empty_string(self):
        assert detect_autonomo_query("") is False


# ---------------------------------------------------------------------------
# get_autonomo_block_response() tests
# ---------------------------------------------------------------------------

class TestAutonomoBlockResponse:
    """Tests for the autonomo block response message."""

    def test_response_not_empty(self):
        response = get_autonomo_block_response()
        assert len(response) > 0

    def test_response_contains_contact_link(self):
        response = get_autonomo_block_response()
        assert "/contact?type=autonomo" in response

    def test_response_mentions_salaried(self):
        response = get_autonomo_block_response()
        assert "trabajador por cuenta ajena" in response.lower()

    def test_response_mentions_plan_features(self):
        response = get_autonomo_block_response()
        assert "nóminas" in response.lower() or "nominas" in response.lower()
        assert "irpf" in response.lower()


# ---------------------------------------------------------------------------
# SubscriptionAccess dataclass tests
# ---------------------------------------------------------------------------

class TestSubscriptionAccess:
    """Tests for the SubscriptionAccess dataclass."""

    def test_default_values(self):
        access = SubscriptionAccess(has_access=False, is_owner=False)
        assert access.has_access is False
        assert access.is_owner is False
        assert access.plan_type is None
        assert access.status is None
        assert access.reason == "no_subscription"

    def test_owner_access(self):
        access = SubscriptionAccess(
            has_access=True, is_owner=True, plan_type="owner",
            status="active", reason="owner"
        )
        assert access.has_access is True
        assert access.is_owner is True
        assert access.plan_type == "owner"


# ---------------------------------------------------------------------------
# grant_grace_period() tests
# ---------------------------------------------------------------------------

class TestGrantGracePeriod:
    """Tests for SubscriptionService.grant_grace_period()."""

    @pytest.mark.asyncio
    async def test_grant_grace_period(self, service, mock_db):
        """grant_grace_period updates the subscription record."""
        mock_db.execute.return_value = FakeResult()

        await service.grant_grace_period("user-1")

        mock_db.execute.assert_called_once()
        call_args = mock_db.execute.call_args
        sql = call_args[0][0]
        params = call_args[0][1]

        assert "grace_period" in sql
        assert params[0] == "2026-12-31T23:59:59"
        assert params[1] == "user-1"

    @pytest.mark.asyncio
    async def test_grant_grace_period_custom_date(self, service, mock_db):
        """grant_grace_period accepts custom end date."""
        mock_db.execute.return_value = FakeResult()

        await service.grant_grace_period("user-1", end_date="2027-06-30T23:59:59")

        call_args = mock_db.execute.call_args
        params = call_args[0][1]
        assert params[0] == "2027-06-30T23:59:59"
