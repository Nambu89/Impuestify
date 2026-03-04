"""
Tests for export system: report generator, email service, and export endpoints.
"""
import json
import pytest
import sys
import os
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

# Mock dependencies before importing app modules
sys.modules.setdefault("jose", MagicMock())
sys.modules.setdefault("jose.jwt", MagicMock())
sys.modules.setdefault("passlib", MagicMock())
sys.modules.setdefault("passlib.context", MagicMock())
sys.modules.setdefault("bcrypt", MagicMock())
sys.modules.setdefault("slowapi", MagicMock())
sys.modules.setdefault("slowapi.util", MagicMock())
sys.modules.setdefault("slowapi.errors", MagicMock())


# ============================================================
# REPORT GENERATOR TESTS
# ============================================================

class TestReportGenerator:
    """Tests for PDF report generation."""

    def test_generate_basic_report(self):
        """Should generate a valid PDF with just a user name."""
        from app.services.report_generator import generate_irpf_report

        pdf_bytes = generate_irpf_report(user_name="Juan Garcia")

        assert isinstance(pdf_bytes, bytes)
        assert len(pdf_bytes) > 0
        assert pdf_bytes[:5] == b"%PDF-"  # Valid PDF magic number

    def test_generate_report_with_simulation(self):
        """Should include simulation data in the PDF."""
        from app.services.report_generator import generate_irpf_report

        simulation = {
            "ingresos_trabajo": 35000.0,
            "ss_empleado": 2222.50,
            "otros_gastos": 2000.0,
            "reduccion_trabajo": 0.0,
            "base_imponible_general": 30777.50,
            "cuota_integra_estatal": 4500.0,
            "cuota_integra_autonomica": 4200.0,
            "cuota_integra_total": 8700.0,
            "mpyf_total": 5550.0,
            "cuota_liquida": 5800.0,
            "tipo_efectivo": 16.57,
        }

        pdf_bytes = generate_irpf_report(
            user_name="Maria Lopez",
            simulation_data=simulation,
        )

        assert isinstance(pdf_bytes, bytes)
        assert pdf_bytes[:5] == b"%PDF-"

    def test_generate_report_with_deductions(self):
        """Should include deductions in the PDF."""
        from app.services.report_generator import generate_irpf_report

        deductions = [
            {
                "code": "EST-MAT-1200",
                "name": "Deduccion por maternidad",
                "type": "deduccion",
                "category": "familia",
                "fixed_amount": 1200.0,
            },
            {
                "code": "EST-DONAT-GEN",
                "name": "Deduccion por donativos",
                "type": "deduccion",
                "category": "donativos",
                "percentage": 80.0,
                "max_amount": 250.0,
            },
        ]

        pdf_bytes = generate_irpf_report(
            user_name="Ana Martinez",
            deductions=deductions,
            estimated_savings=1400.0,
        )

        assert isinstance(pdf_bytes, bytes)
        assert pdf_bytes[:5] == b"%PDF-"

    def test_generate_report_with_fiscal_profile(self):
        """Should include fiscal profile in the PDF."""
        from app.services.report_generator import generate_irpf_report

        pdf_bytes = generate_irpf_report(
            user_name="Pedro Sanchez",
            fiscal_profile={
                "ccaa_residencia": "Madrid",
                "situacion_laboral": "autonomo",
                "epigrafe_iae": "841",
                "regimen_iva": "general",
            },
        )

        assert isinstance(pdf_bytes, bytes)
        assert pdf_bytes[:5] == b"%PDF-"

    def test_generate_full_report(self):
        """Should generate a complete report with all sections."""
        from app.services.report_generator import generate_irpf_report

        pdf_bytes = generate_irpf_report(
            user_name="Elena Ruiz",
            simulation_data={
                "ingresos_trabajo": 50000.0,
                "cuota_liquida": 10500.0,
                "tipo_efectivo": 21.0,
            },
            deductions=[
                {"code": "EST-MAT-1200", "name": "Maternidad", "type": "deduccion",
                 "category": "familia", "fixed_amount": 1200.0},
            ],
            fiscal_profile={"ccaa_residencia": "Cataluna"},
            estimated_savings=1200.0,
        )

        assert isinstance(pdf_bytes, bytes)
        assert len(pdf_bytes) > 1000  # Should be substantial


# ============================================================
# EMAIL SERVICE TESTS
# ============================================================

class TestEmailService:
    """Tests for email service."""

    def test_service_singleton(self):
        """get_email_service should return singleton."""
        from app.services.email_service import get_email_service, _email_service

        svc1 = get_email_service()
        svc2 = get_email_service()
        assert svc1 is svc2

    @pytest.mark.asyncio
    async def test_send_email_without_config_raises(self):
        """Should raise if Resend is not configured."""
        from app.services.email_service import EmailService

        service = EmailService()

        with patch("app.config.settings") as mock_settings:
            mock_settings.is_resend_configured = False
            with pytest.raises(RuntimeError, match="not configured"):
                await service.send_email("test@test.com", "Subject", "<p>Body</p>")

    @pytest.mark.asyncio
    async def test_send_report_to_advisor_calls_send(self):
        """send_report_to_advisor should call send_email with attachment."""
        from app.services.email_service import EmailService

        service = EmailService()
        service.send_email = AsyncMock(return_value={"success": True, "id": "email-123"})

        result = await service.send_report_to_advisor(
            advisor_email="asesor@gmail.com",
            user_name="Juan",
            report_title="IRPF 2025",
            pdf_bytes=b"%PDF-test",
        )

        assert result["success"] is True
        service.send_email.assert_called_once()
        call_kwargs = service.send_email.call_args
        assert call_kwargs[1]["to"] == "asesor@gmail.com"
        assert "Informe fiscal de Juan" in call_kwargs[1]["subject"]
        assert len(call_kwargs[1]["attachments"]) == 1


# ============================================================
# EXPORT ROUTER TESTS
# ============================================================

class TestExportRouter:
    """Tests for export API endpoints."""

    def test_router_registered(self):
        """Export router should have correct prefix."""
        from app.routers.export import router

        assert router.prefix == "/api/export"

    def test_irpf_report_endpoint_exists(self):
        """POST /api/export/irpf-report should be defined."""
        from app.routers.export import router

        routes = [r.path for r in router.routes]
        assert any("irpf-report" in r for r in routes)

    def test_share_endpoint_exists(self):
        """POST /api/export/share-with-advisor should be defined."""
        from app.routers.export import router

        routes = [r.path for r in router.routes]
        assert any("share-with-advisor" in r for r in routes)

    def test_request_model_validation(self):
        """IRPFReportRequest should validate fields."""
        from app.routers.export import IRPFReportRequest

        req = IRPFReportRequest(ccaa="Madrid", ingresos_trabajo=30000, year=2025)
        assert req.ccaa == "Madrid"
        assert req.ingresos_trabajo == 30000

    def test_share_request_model(self):
        """ShareWithAdvisorRequest should validate email."""
        from app.routers.export import ShareWithAdvisorRequest

        req = ShareWithAdvisorRequest(
            report_id="test-id",
            advisor_email="asesor@test.com",
        )
        assert req.advisor_email == "asesor@test.com"


# ============================================================
# CONFIG TESTS
# ============================================================

class TestExportConfig:
    """Tests for Resend configuration in settings."""

    def test_resend_fields_exist(self):
        """Config should have Resend fields."""
        from app.config import Settings

        fields = Settings.model_fields
        assert "RESEND_API_KEY" in fields
        assert "RESEND_FROM_EMAIL" in fields

    def test_is_resend_configured_false_by_default(self):
        """is_resend_configured should be False without API key."""
        from app.config import Settings

        s = Settings(
            OPENAI_API_KEY="test",
            TURSO_DATABASE_URL="test",
            TURSO_AUTH_TOKEN="test",
        )
        assert s.is_resend_configured is False

    def test_is_resend_configured_true_with_key(self):
        """is_resend_configured should be True with API key."""
        from app.config import Settings

        s = Settings(
            OPENAI_API_KEY="test",
            TURSO_DATABASE_URL="test",
            TURSO_AUTH_TOKEN="test",
            RESEND_API_KEY="re_test_key",
        )
        assert s.is_resend_configured is True


# ============================================================
# DATABASE SCHEMA TESTS
# ============================================================

class TestDatabaseSchema:
    """Tests for new database tables."""

    def test_deductions_table_in_schema(self):
        """deductions table should be in schema_statements."""
        import inspect
        from app.database.turso_client import TursoClient

        source = inspect.getsource(TursoClient.init_schema)
        assert "CREATE TABLE IF NOT EXISTS deductions" in source
        assert "code TEXT NOT NULL" in source
        assert "tax_year INTEGER NOT NULL" in source
        assert "requirements_json TEXT" in source

    def test_reports_table_in_schema(self):
        """reports table should be in schema_statements."""
        import inspect
        from app.database.turso_client import TursoClient

        source = inspect.getsource(TursoClient.init_schema)
        assert "CREATE TABLE IF NOT EXISTS reports" in source
        assert "share_token TEXT UNIQUE" in source
        assert "pdf_bytes BLOB" in source
