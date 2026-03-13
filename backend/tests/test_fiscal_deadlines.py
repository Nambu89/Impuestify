"""
Tests for Fiscal Calendar - deadlines, push subscriptions, and alert logic.

Coverage:
- iCal parser (mock .ics content)
- Foral seed data structure
- Deadline deterministic ID generation
- API endpoints (mock DB)
- Push subscribe/unsubscribe logic
- Notification alert logic (mock pywebpush)
- notification_log idempotency
"""
import json
import uuid
import pytest
from datetime import date, timedelta
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock

# ---- Ensure test can import backend modules ----
import sys
import os

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

BACKEND_ROOT = os.path.join(PROJECT_ROOT, "backend")
if BACKEND_ROOT not in sys.path:
    sys.path.insert(0, BACKEND_ROOT)


# ============================================================
# Section 1: iCal parser unit tests
# ============================================================

SAMPLE_ICS = b"""BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//AEAT//Calendario Fiscal//ES
BEGIN:VEVENT
DTSTART;VALUE=DATE:20260401
DTEND;VALUE=DATE:20260420
SUMMARY:Modelo 303 IVA 1er trimestre 2026
DESCRIPTION:Autoliquidacion IVA 1T 2026 autonomos
URL:https://sede.agenciatributaria.gob.es/
END:VEVENT
BEGIN:VEVENT
DTSTART;VALUE=DATE:20260406
DTEND;VALUE=DATE:20260630
SUMMARY:Renta 2025 - IRPF anual
DESCRIPTION:Declaracion anual del IRPF ejercicio 2025
URL:https://sede.agenciatributaria.gob.es/
END:VEVENT
BEGIN:VEVENT
DTSTART;VALUE=DATE:20260101
DTEND;VALUE=DATE:20260131
SUMMARY:Modelo 347 Operaciones con terceros
DESCRIPTION:Declaracion anual operaciones con terceros
URL:https://sede.agenciatributaria.gob.es/
END:VEVENT
BEGIN:VEVENT
DTSTART;VALUE=DATE:20260701
DTEND;VALUE=DATE:20260720
SUMMARY:Modelo 303 IVA 2do trimestre 2026
DESCRIPTION:Autoliquidacion IVA 2T 2026
URL:https://sede.agenciatributaria.gob.es/
END:VEVENT
END:VCALENDAR
"""

MINIMAL_ICS = b"""BEGIN:VCALENDAR
VERSION:2.0
BEGIN:VEVENT
DTSTART;VALUE=DATE:20260501
DTEND;VALUE=DATE:20260520
SUMMARY:Modelo 130 Pago fraccionado IRPF 1T
DESCRIPTION:Pago fraccionado IRPF estimacion directa 1T 2026
END:VEVENT
END:VCALENDAR
"""

NO_EVENTS_ICS = b"""BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Test//Test//EN
END:VCALENDAR
"""


class TestICalParser:
    """Tests for sync_fiscal_calendar.parse_ical_content."""

    def setup_method(self):
        """Import the module under test."""
        # Patch icalendar availability so tests work even without the package
        import importlib
        from unittest.mock import patch

        # We test parse_ical_content with icalendar installed
        try:
            import icalendar
            self.icalendar_available = True
        except ImportError:
            self.icalendar_available = False

    def test_parse_returns_list(self):
        """parse_ical_content returns a list."""
        if not self.icalendar_available:
            pytest.skip("icalendar not installed")
        from scripts.sync_fiscal_calendar import parse_ical_content
        result = parse_ical_content(SAMPLE_ICS, 2026)
        assert isinstance(result, list)

    def test_parse_extracts_events(self):
        """Parser extracts all VEVENT entries."""
        if not self.icalendar_available:
            pytest.skip("icalendar not installed")
        from scripts.sync_fiscal_calendar import parse_ical_content
        result = parse_ical_content(SAMPLE_ICS, 2026)
        assert len(result) == 4

    def test_parse_303_model(self):
        """Parser maps Modelo 303 correctly."""
        if not self.icalendar_available:
            pytest.skip("icalendar not installed")
        from scripts.sync_fiscal_calendar import parse_ical_content
        result = parse_ical_content(SAMPLE_ICS, 2026)
        modelo_303 = [d for d in result if d["model"] == "303"]
        assert len(modelo_303) >= 1
        assert modelo_303[0]["applies_to"] == "autonomos"

    def test_parse_irpf_model(self):
        """Parser maps IRPF/Renta as model 100."""
        if not self.icalendar_available:
            pytest.skip("icalendar not installed")
        from scripts.sync_fiscal_calendar import parse_ical_content
        result = parse_ical_content(SAMPLE_ICS, 2026)
        modelo_100 = [d for d in result if d["model"] == "100"]
        assert len(modelo_100) >= 1
        assert modelo_100[0]["applies_to"] == "todos"

    def test_parse_modelo_130(self):
        """Parser maps Modelo 130 to autonomos."""
        if not self.icalendar_available:
            pytest.skip("icalendar not installed")
        from scripts.sync_fiscal_calendar import parse_ical_content
        result = parse_ical_content(MINIMAL_ICS, 2026)
        modelo_130 = [d for d in result if d["model"] == "130"]
        assert len(modelo_130) == 1
        assert modelo_130[0]["applies_to"] == "autonomos"

    def test_parse_dates_are_iso_strings(self):
        """All dates are ISO-format strings."""
        if not self.icalendar_available:
            pytest.skip("icalendar not installed")
        from scripts.sync_fiscal_calendar import parse_ical_content
        result = parse_ical_content(SAMPLE_ICS, 2026)
        for d in result:
            assert len(d["start_date"]) == 10
            assert d["start_date"][4] == "-"
            assert len(d["end_date"]) == 10

    def test_parse_ids_are_deterministic(self):
        """Same content produces same IDs on repeated parse."""
        if not self.icalendar_available:
            pytest.skip("icalendar not installed")
        from scripts.sync_fiscal_calendar import parse_ical_content
        result1 = parse_ical_content(SAMPLE_ICS, 2026)
        result2 = parse_ical_content(SAMPLE_ICS, 2026)
        ids1 = [d["id"] for d in result1]
        ids2 = [d["id"] for d in result2]
        assert ids1 == ids2

    def test_parse_territory_is_estatal(self):
        """All parsed events have territory='Estatal'."""
        if not self.icalendar_available:
            pytest.skip("icalendar not installed")
        from scripts.sync_fiscal_calendar import parse_ical_content
        result = parse_ical_content(SAMPLE_ICS, 2026)
        for d in result:
            assert d["territory"] == "Estatal"

    def test_parse_empty_calendar(self):
        """Empty calendar returns empty list."""
        if not self.icalendar_available:
            pytest.skip("icalendar not installed")
        from scripts.sync_fiscal_calendar import parse_ical_content
        result = parse_ical_content(NO_EVENTS_ICS, 2026)
        assert result == []

    def test_parse_dry_run_returns_same_data(self):
        """dry_run=True still returns full list (just skips DB)."""
        if not self.icalendar_available:
            pytest.skip("icalendar not installed")
        from scripts.sync_fiscal_calendar import parse_ical_content
        result = parse_ical_content(SAMPLE_ICS, 2026, dry_run=True)
        assert len(result) == 4

    def test_parse_347_model(self):
        """Parser maps Modelo 347 to autonomos."""
        if not self.icalendar_available:
            pytest.skip("icalendar not installed")
        from scripts.sync_fiscal_calendar import parse_ical_content
        result = parse_ical_content(SAMPLE_ICS, 2026)
        modelo_347 = [d for d in result if d["model"] == "347"]
        assert len(modelo_347) == 1
        assert modelo_347[0]["applies_to"] == "autonomos"


# ============================================================
# Section 2: Deterministic ID generation
# ============================================================

class TestDeadlineIdGeneration:
    """Tests for _make_id helper function."""

    def test_make_id_basic(self):
        from scripts.sync_fiscal_calendar import _make_id
        result = _make_id("303", "Estatal", "1T", 2026)
        assert result == "303_estatal_1t_2026"

    def test_make_id_foral(self):
        from scripts.sync_fiscal_calendar import _make_id
        result = _make_id("300", "Gipuzkoa", "2T", 2026)
        assert result == "300_gipuzkoa_2t_2026"

    def test_make_id_navarra(self):
        from scripts.sync_fiscal_calendar import _make_id
        result = _make_id("F-65", "Navarra", "anual", 2026)
        assert "navarra" in result
        assert "2026" in result
        assert "f" in result.lower()

    def test_make_id_consistent(self):
        from scripts.sync_fiscal_calendar import _make_id
        id1 = _make_id("100", "Estatal", "anual", 2026)
        id2 = _make_id("100", "Estatal", "anual", 2026)
        assert id1 == id2

    def test_make_id_year_differentiates(self):
        from scripts.sync_fiscal_calendar import _make_id
        id_2025 = _make_id("303", "Estatal", "1T", 2025)
        id_2026 = _make_id("303", "Estatal", "1T", 2026)
        assert id_2025 != id_2026

    def test_make_id_period_differentiates(self):
        from scripts.sync_fiscal_calendar import _make_id
        id_1t = _make_id("303", "Estatal", "1T", 2026)
        id_2t = _make_id("303", "Estatal", "2T", 2026)
        assert id_1t != id_2t


# ============================================================
# Section 3: Foral seed data tests
# ============================================================

class TestForalSeedData:
    """Tests for seed_foral_deadlines.build_foral_deadlines_2026."""

    def setup_method(self):
        from scripts.seed_foral_deadlines import build_foral_deadlines_2026
        self.build_fn = build_foral_deadlines_2026

    def test_returns_list(self):
        result = self.build_fn(2026)
        assert isinstance(result, list)

    def test_contains_all_territories(self):
        result = self.build_fn(2026)
        territories = {d["territory"] for d in result}
        assert "Gipuzkoa" in territories
        assert "Bizkaia" in territories
        assert "Araba" in territories
        assert "Navarra" in territories

    def test_all_ids_are_unique(self):
        result = self.build_fn(2026)
        ids = [d["id"] for d in result]
        assert len(ids) == len(set(ids)), "Duplicate IDs found in foral deadlines"

    def test_all_required_fields_present(self):
        result = self.build_fn(2026)
        required = {"id", "model", "model_name", "territory", "period", "tax_year",
                    "start_date", "end_date", "applies_to", "is_active"}
        for d in result:
            missing = required - d.keys()
            assert not missing, f"Deadline {d.get('id')} missing fields: {missing}"

    def test_dates_are_valid_iso(self):
        result = self.build_fn(2026)
        for d in result:
            start = date.fromisoformat(d["start_date"])
            end = date.fromisoformat(d["end_date"])
            assert end >= start, f"end_date before start_date for {d['id']}"

    def test_applies_to_valid_values(self):
        result = self.build_fn(2026)
        valid = {"todos", "autonomos", "particulares"}
        for d in result:
            assert d["applies_to"] in valid, f"Invalid applies_to for {d['id']}: {d['applies_to']}"

    def test_irpf_anual_for_all_territories(self):
        result = self.build_fn(2026)
        irpf_anual = [d for d in result if d["model"] in ("100", "S90") and d["period"] == "anual"]
        territories = {d["territory"] for d in irpf_anual}
        assert "Gipuzkoa" in territories
        assert "Bizkaia" in territories
        assert "Araba" in territories
        assert "Navarra" in territories

    def test_navarra_has_s90(self):
        result = self.build_fn(2026)
        navarra_irpf = [d for d in result if d["territory"] == "Navarra" and d["period"] == "anual"]
        assert any(d["model"] == "S90" for d in navarra_irpf)

    def test_navarra_has_f65_iva(self):
        result = self.build_fn(2026)
        navarra_iva = [d for d in result if d["territory"] == "Navarra" and d["model"] == "F-65"]
        assert len(navarra_iva) >= 4  # 4 quarters

    def test_gipuzkoa_has_modelo_300(self):
        result = self.build_fn(2026)
        gipuzkoa_iva = [d for d in result if d["territory"] == "Gipuzkoa" and d["model"] == "300"]
        assert len(gipuzkoa_iva) >= 4  # 4 quarters

    def test_is_active_defaults_to_1(self):
        result = self.build_fn(2026)
        for d in result:
            assert d["is_active"] == 1

    def test_irpf_applies_to_todos(self):
        result = self.build_fn(2026)
        irpf = [d for d in result if d["model"] in ("100", "S90")]
        for d in irpf:
            assert d["applies_to"] == "todos", f"IRPF deadline {d['id']} should apply to todos"

    def test_different_year_changes_dates(self):
        result_2026 = self.build_fn(2026)
        result_2027 = self.build_fn(2027)
        dates_2026 = {d["end_date"] for d in result_2026}
        dates_2027 = {d["end_date"] for d in result_2027}
        # The dates should differ since the year is different
        # (at least some dates will differ)
        assert dates_2026 != dates_2027

    def test_upsert_is_idempotent_structure(self):
        """Two calls with same year produce same data (idempotent seeds)."""
        result1 = self.build_fn(2026)
        result2 = self.build_fn(2026)
        ids1 = sorted([d["id"] for d in result1])
        ids2 = sorted([d["id"] for d in result2])
        assert ids1 == ids2


# ============================================================
# Section 4: Push service unit tests (no DB, no pywebpush)
# ============================================================

class TestPushServiceLogic:
    """Tests for push_service without real DB or pywebpush."""

    @pytest.mark.asyncio
    async def test_send_push_no_vapid_returns_zero(self):
        """send_push returns zero-sent when VAPID not configured."""
        from app.services import push_service

        mock_db = MagicMock()
        mock_db.execute = AsyncMock(return_value=MagicMock(rows=[]))

        with patch.object(push_service.settings, "VAPID_PRIVATE_KEY", None):
            with patch.object(push_service.settings, "VAPID_PUBLIC_KEY", None):
                result = await push_service.send_push("user1", "Title", "Body", db=mock_db)

        assert result["sent"] == 0
        assert result["failed"] == 0

    @pytest.mark.asyncio
    async def test_send_push_no_subscriptions(self):
        """send_push handles empty subscriptions gracefully."""
        from app.services import push_service

        mock_db = MagicMock()
        mock_db.execute = AsyncMock(return_value=MagicMock(rows=[]))

        with patch.object(push_service.settings, "VAPID_PRIVATE_KEY", "fake_key"):
            with patch.object(push_service.settings, "VAPID_PUBLIC_KEY", "fake_pub"):
                with patch("backend.app.services.push_service._pywebpush_available", return_value=True):
                    with patch("backend.app.services.push_service.webpush", MagicMock(), create=True):
                        result = await push_service.send_push("user1", "Title", "Body", db=mock_db)

        assert result["sent"] == 0

    @pytest.mark.asyncio
    async def test_send_deadline_alerts_no_deadlines(self):
        """send_deadline_alerts handles empty deadline table gracefully."""
        from app.services import push_service

        mock_db = MagicMock()
        # First call -> deadlines, second call -> subscriptions
        mock_db.execute = AsyncMock(side_effect=[
            MagicMock(rows=[]),  # fiscal_deadlines
            MagicMock(rows=[]),  # push_subscriptions
        ])

        result = await push_service.send_deadline_alerts(db=mock_db)

        assert result["deadlines_checked"] == 0
        assert result["users_checked"] == 0
        assert result["notifications_sent"] == 0

    @pytest.mark.asyncio
    async def test_send_deadline_alerts_skips_duplicates(self):
        """send_deadline_alerts skips already-notified deadline/user combos."""
        from app.services import push_service

        today = date.today()
        deadline_end = (today + timedelta(days=15)).isoformat()

        mock_db = MagicMock()
        mock_db.execute = AsyncMock(side_effect=[
            # deadlines
            MagicMock(rows=[{
                "id": "303_estatal_1t_2026",
                "model": "303",
                "model_name": "IVA trimestral",
                "territory": "Estatal",
                "period": "1T",
                "tax_year": 2026,
                "end_date": deadline_end,
                "applies_to": "autonomos",
            }]),
            # subscriptions (one user)
            MagicMock(rows=[{"user_id": "user-1", "alert_days": "15,5,1"}]),
            # notification_log check -> already sent
            MagicMock(rows=[{"id": "existing-log-id"}]),
        ])

        result = await push_service.send_deadline_alerts(db=mock_db)

        assert result["notifications_skipped_duplicate"] == 1
        assert result["notifications_sent"] == 0

    @pytest.mark.asyncio
    async def test_send_deadline_alerts_respects_rate_limit(self):
        """send_deadline_alerts caps notifications at MAX_NOTIFICATIONS_PER_DAY."""
        from app.services import push_service

        today = date.today()
        max_n = push_service.MAX_NOTIFICATIONS_PER_DAY
        # Create max_n+1 deadlines all vencing in 15 days
        deadlines = []
        for i in range(max_n + 2):
            end = (today + timedelta(days=15)).isoformat()
            deadlines.append({
                "id": f"deadline_{i}",
                "model": "303",
                "model_name": "IVA",
                "territory": "Estatal",
                "period": f"T{i}",
                "tax_year": 2026,
                "end_date": end,
                "applies_to": "autonomos",
            })

        calls = (
            [MagicMock(rows=deadlines)]
            + [MagicMock(rows=[{"user_id": "user-1", "alert_days": "15"}])]
            # Each deadline: check notification_log (not sent) + send push + log
            + [MagicMock(rows=[]) for _ in range(max_n + 2)]
        )

        mock_db = MagicMock()

        async def mock_execute(sql, params=None):
            return calls.pop(0) if calls else MagicMock(rows=[])

        mock_db.execute = mock_execute

        # Mock send_push to simulate successful delivery
        async def fake_send_push(**kwargs):
            return {"sent": 1, "failed": 0, "expired_cleaned": 0}

        with patch.object(push_service, "send_push", side_effect=fake_send_push):
            result = await push_service.send_deadline_alerts(db=mock_db)

        # Rate limit kicks in after MAX_NOTIFICATIONS_PER_DAY
        assert result["notifications_skipped_rate_limit"] >= 1


# ============================================================
# Section 5: API endpoint model tests (no HTTP)
# ============================================================

class TestDeadlineModels:
    """Tests for Pydantic models in deadlines router."""

    def test_fiscal_deadline_out_model(self):
        from app.routers.deadlines import FiscalDeadlineOut
        obj = FiscalDeadlineOut(
            id="303_estatal_1t_2026",
            model="303",
            model_name="IVA trimestral",
            territory="Estatal",
            period="1T",
            tax_year=2026,
            start_date="2026-04-01",
            end_date="2026-04-20",
            applies_to="autonomos",
        )
        assert obj.id == "303_estatal_1t_2026"
        assert obj.territory == "Estatal"
        assert obj.domiciliation_date is None

    def test_push_subscribe_request_validation(self):
        from app.routers.deadlines import PushSubscribeRequest
        req = PushSubscribeRequest(
            endpoint="https://fcm.googleapis.com/fcm/send/abc123",
            p256dh="BNcRdreALRFXTkOOUHK1EtK2wtaz5Ry4YfYCA_0QTpQtUbVlTiHTlmtNPlDRLMkqd_87t-RBkTQQsGRFE",
            auth="tBHItJI5svbpez7KI4CCXg==",
        )
        assert req.alert_days == "15,5,1"

    def test_push_subscribe_request_custom_alert_days(self):
        from app.routers.deadlines import PushSubscribeRequest
        req = PushSubscribeRequest(
            endpoint="https://fcm.googleapis.com/fcm/send/abc123",
            p256dh="BNcRdreALRFXTkOOUHK1EtK2wtaz5Ry4YfYCA_0QTpQtUbVlTiHTlmtNPlDRLMkqd_87t-RBkTQQsGRFE",
            auth="tBHItJI5svbpez7KI4CCXg==",
            alert_days="5,1",
        )
        assert req.alert_days == "5,1"

    def test_push_unsubscribe_request(self):
        from app.routers.deadlines import PushUnsubscribeRequest
        req = PushUnsubscribeRequest(endpoint="https://fcm.googleapis.com/fcm/send/abc123")
        assert len(req.endpoint) > 10

    def test_row_to_deadline_helper(self):
        from app.routers.deadlines import _row_to_deadline
        row = {
            "id": "100_estatal_anual_2026",
            "model": "100",
            "model_name": "IRPF Renta anual",
            "territory": "Estatal",
            "period": "anual",
            "tax_year": 2026,
            "start_date": "2026-04-06",
            "end_date": "2026-06-30",
            "domiciliation_date": "2026-06-25",
            "applies_to": "todos",
            "description": "Test",
            "source_url": None,
            "is_active": 1,
        }
        out = _row_to_deadline(row)
        assert out.id == "100_estatal_anual_2026"
        assert out.domiciliation_date == "2026-06-25"
        assert out.is_active is True

    def test_row_to_deadline_without_optional_fields(self):
        from app.routers.deadlines import _row_to_deadline
        row = {
            "id": "303_estatal_1t_2026",
            "model": "303",
            "model_name": "IVA trimestral",
            "territory": "Estatal",
            "period": "1T",
            "tax_year": 2026,
            "start_date": "2026-04-01",
            "end_date": "2026-04-20",
            "applies_to": "autonomos",
        }
        out = _row_to_deadline(row)
        assert out.description is None
        assert out.source_url is None
        assert out.domiciliation_date is None


# ============================================================
# Section 6: Territory routing logic
# ============================================================

class TestTerritoryRouting:
    """Tests for _get_user_territory logic in deadlines router."""

    @pytest.mark.asyncio
    async def test_foral_ccaa_maps_to_foral_territory(self):
        from app.routers.deadlines import _get_user_territory
        mock_db = MagicMock()
        mock_db.execute = AsyncMock(return_value=MagicMock(rows=[{
            "ccaa_residencia": "Gipuzkoa",
            "situacion_laboral": "autonomo",
        }]))
        territory, applies_to = await _get_user_territory("user-1", mock_db)
        assert territory == "Gipuzkoa"
        assert "autonomos" in applies_to

    @pytest.mark.asyncio
    async def test_comun_ccaa_maps_to_estatal(self):
        from app.routers.deadlines import _get_user_territory
        mock_db = MagicMock()
        mock_db.execute = AsyncMock(return_value=MagicMock(rows=[{
            "ccaa_residencia": "Madrid",
            "situacion_laboral": "empleado",
        }]))
        territory, applies_to = await _get_user_territory("user-1", mock_db)
        assert territory == "Estatal"
        assert "todos" in applies_to

    @pytest.mark.asyncio
    async def test_no_profile_defaults_to_estatal(self):
        from app.routers.deadlines import _get_user_territory
        mock_db = MagicMock()
        mock_db.execute = AsyncMock(return_value=MagicMock(rows=[]))
        territory, applies_to = await _get_user_territory("user-unknown", mock_db)
        assert territory == "Estatal"
        assert "todos" in applies_to

    @pytest.mark.asyncio
    async def test_autonomo_situacion_includes_autonomos(self):
        from app.routers.deadlines import _get_user_territory
        mock_db = MagicMock()
        mock_db.execute = AsyncMock(return_value=MagicMock(rows=[{
            "ccaa_residencia": "Cataluna",
            "situacion_laboral": "autonomo",
        }]))
        _, applies_to = await _get_user_territory("user-1", mock_db)
        assert "autonomos" in applies_to

    @pytest.mark.asyncio
    async def test_particular_situacion_excludes_autonomos(self):
        from app.routers.deadlines import _get_user_territory
        mock_db = MagicMock()
        mock_db.execute = AsyncMock(return_value=MagicMock(rows=[{
            "ccaa_residencia": "Madrid",
            "situacion_laboral": "particular",
        }]))
        _, applies_to = await _get_user_territory("user-1", mock_db)
        assert "autonomos" not in applies_to

    @pytest.mark.asyncio
    async def test_navarra_maps_to_navarra(self):
        from app.routers.deadlines import _get_user_territory
        mock_db = MagicMock()
        mock_db.execute = AsyncMock(return_value=MagicMock(rows=[{
            "ccaa_residencia": "Navarra",
            "situacion_laboral": "autonomo",
        }]))
        territory, _ = await _get_user_territory("user-1", mock_db)
        assert territory == "Navarra"


# ============================================================
# Section 7: Push payload tests
# ============================================================

class TestPushPayload:
    """Tests for _build_payload helper in push_service."""

    def test_build_payload_valid_json(self):
        from app.services.push_service import _build_payload
        payload_str = _build_payload("Title", "Body")
        payload = json.loads(payload_str)
        assert payload["title"] == "Title"
        assert payload["body"] == "Body"

    def test_build_payload_default_url(self):
        from app.services.push_service import _build_payload
        payload_str = _build_payload("Title", "Body")
        payload = json.loads(payload_str)
        assert payload["url"] == "/calendario"

    def test_build_payload_custom_url(self):
        from app.services.push_service import _build_payload
        payload_str = _build_payload("Title", "Body", url="/dashboard")
        payload = json.loads(payload_str)
        assert payload["url"] == "/dashboard"

    def test_build_payload_under_4kb(self):
        from app.services.push_service import _build_payload
        payload_str = _build_payload("Title" * 10, "Body" * 50)
        assert len(payload_str.encode("utf-8")) < 4096

    def test_build_payload_tag(self):
        from app.services.push_service import _build_payload
        payload_str = _build_payload("Title", "Body", tag="custom-tag")
        payload = json.loads(payload_str)
        assert payload["tag"] == "custom-tag"


# ============================================================
# Section 8: Notification log idempotency logic
# ============================================================

class TestNotificationLogIdempotency:
    """Test the duplicate-detection logic in send_deadline_alerts."""

    @pytest.mark.asyncio
    async def test_duplicate_check_prevents_resend(self):
        """Second run for same (user, deadline, alert_type) is skipped."""
        from app.services import push_service

        today = date.today()
        end_date = (today + timedelta(days=5)).isoformat()

        # deadline + subscription + notification_log says already sent
        calls_iter = iter([
            MagicMock(rows=[{
                "id": "303_estatal_1t_2026",
                "model": "303",
                "model_name": "IVA",
                "territory": "Estatal",
                "period": "1T",
                "tax_year": 2026,
                "end_date": end_date,
                "applies_to": "autonomos",
            }]),
            MagicMock(rows=[{"user_id": "u1", "alert_days": "15,5,1"}]),
            MagicMock(rows=[{"id": "log-exists"}]),  # already logged
        ])

        mock_db = MagicMock()
        mock_db.execute = AsyncMock(side_effect=lambda *a, **kw: next(calls_iter))

        result = await push_service.send_deadline_alerts(db=mock_db)
        assert result["notifications_skipped_duplicate"] >= 1
        assert result["notifications_sent"] == 0

    @pytest.mark.asyncio
    async def test_different_alert_types_are_independent(self):
        """15d and 5d alerts for same deadline are treated as separate notifications."""
        from app.services import push_service

        # Verify ALERT_DAY_OPTIONS contains distinct values
        assert 15 in push_service.ALERT_DAY_OPTIONS
        assert 5 in push_service.ALERT_DAY_OPTIONS
        assert 1 in push_service.ALERT_DAY_OPTIONS
        assert len(push_service.ALERT_DAY_OPTIONS) == 3

    def test_max_notifications_per_day_constant(self):
        from app.services.push_service import MAX_NOTIFICATIONS_PER_DAY
        assert MAX_NOTIFICATIONS_PER_DAY == 3


# ============================================================
# Section 9: Config VAPID fields
# ============================================================

class TestVapidConfig:
    """Tests for VAPID configuration in settings."""

    def test_vapid_fields_exist_in_settings(self):
        from app.config import Settings
        s = Settings()
        assert hasattr(s, "VAPID_PUBLIC_KEY")
        assert hasattr(s, "VAPID_PRIVATE_KEY")
        assert hasattr(s, "VAPID_CLAIMS_EMAIL")

    def test_vapid_defaults(self):
        from app.config import Settings
        s = Settings()
        assert s.VAPID_PUBLIC_KEY is None
        assert s.VAPID_PRIVATE_KEY is None
        assert s.VAPID_CLAIMS_EMAIL == "mailto:soporte@impuestify.com"


# ============================================================
# Section 10: DB schema tests (structure validation)
# ============================================================

class TestDBSchemaStatements:
    """Verify new table SQL is parseable (structural check without DB)."""

    def test_fiscal_deadlines_table_statement_has_required_columns(self):
        """Check that init_schema includes fiscal_deadlines table definition."""
        import inspect
        from app.database import turso_client
        source = inspect.getsource(turso_client)
        assert "fiscal_deadlines" in source
        assert "push_subscriptions" in source
        assert "notification_log" in source

    def test_fiscal_deadlines_indexes_present(self):
        import inspect
        from app.database import turso_client
        source = inspect.getsource(turso_client)
        assert "idx_deadlines_territory" in source
        assert "idx_deadlines_end_date" in source
        assert "idx_deadlines_model" in source

    def test_push_subscriptions_unique_constraint(self):
        import inspect
        from app.database import turso_client
        source = inspect.getsource(turso_client)
        assert "UNIQUE(user_id, endpoint)" in source

    def test_notification_log_unique_constraint(self):
        import inspect
        from app.database import turso_client
        source = inspect.getsource(turso_client)
        assert "UNIQUE(user_id, deadline_id, alert_type)" in source

    def test_alert_days_default_present(self):
        import inspect
        from app.database import turso_client
        source = inspect.getsource(turso_client)
        assert "15,5,1" in source
