"""Tests for InvoiceClassifierService — PGC classification with Gemini 3 Flash."""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.invoice_classifier_service import (
    AlternativaPGC,
    ClasificacionPGC,
    InvoiceClassifierService,
)


# ---------------------------------------------------------------------------
# ClasificacionPGC model
# ---------------------------------------------------------------------------


class TestClasificacionPGCModel:
    """Verify Pydantic model creation and validation."""

    def test_create_basic(self):
        result = ClasificacionPGC(
            cuenta_code="629",
            cuenta_nombre="Otros servicios",
            confianza="alta",
            alternativas=[],
            justificacion="Servicio profesional generico",
        )
        assert result.cuenta_code == "629"
        assert result.confianza == "alta"
        assert result.alternativas == []

    def test_create_with_alternatives(self):
        alt = AlternativaPGC(code="623", nombre="Servicios de profesionales independientes")
        result = ClasificacionPGC(
            cuenta_code="629",
            cuenta_nombre="Otros servicios",
            confianza="media",
            alternativas=[alt],
            justificacion="Podria ser tambien 623",
        )
        assert len(result.alternativas) == 1
        assert result.alternativas[0].code == "623"

    def test_alternativa_model(self):
        alt = AlternativaPGC(code="700", nombre="Ventas de mercaderias")
        assert alt.code == "700"
        assert alt.nombre == "Ventas de mercaderias"


# ---------------------------------------------------------------------------
# InvoiceClassifierService.classify
# ---------------------------------------------------------------------------


class TestClassifyInvoice:
    """Test full classify flow with mocked Gemini + mocked DB."""

    MOCK_PGC_ROWS = [
        {"code": "629", "name": "Otros servicios", "keywords": "servicios,asesoria"},
        {"code": "623", "name": "Servicios de profesionales independientes", "keywords": "abogado,consultor"},
        {"code": "621", "name": "Arrendamientos y canones", "keywords": "alquiler,oficina"},
    ]

    GEMINI_RESPONSE = {
        "cuenta_code": "629",
        "cuenta_nombre": "Otros servicios",
        "confianza": "alta",
        "alternativas": [{"code": "623", "nombre": "Servicios de profesionales independientes"}],
        "justificacion": "El concepto corresponde a un servicio profesional generico.",
    }

    @pytest.mark.asyncio
    async def test_classify_invoice(self):
        """Mock DB returns 3 PGC candidates, mock Gemini returns classification."""
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.rows = self.MOCK_PGC_ROWS
        mock_db.execute = AsyncMock(return_value=mock_result)

        with patch("app.services.invoice_classifier_service.genai") as mock_genai:
            mock_client = MagicMock()
            mock_genai.Client.return_value = mock_client

            mock_response = MagicMock()
            mock_response.text = json.dumps(self.GEMINI_RESPONSE)
            mock_client.models.generate_content.return_value = mock_response

            service = InvoiceClassifierService(api_key="test-key", db=mock_db)
            result = await service.classify(
                concepto="Servicio de asesoria fiscal marzo 2026",
                emisor_nombre="Asesores Madrid SL",
                tipo="recibida",
                base_imponible=500.0,
            )

            assert isinstance(result, ClasificacionPGC)
            assert result.cuenta_code == "629"
            assert result.confianza == "alta"
            assert len(result.alternativas) == 1
            assert result.alternativas[0].code == "623"

            # Verify DB was queried for gasto candidates (tipo=recibida)
            mock_db.execute.assert_called_once()
            call_args = mock_db.execute.call_args
            assert "gasto" in call_args[0][1]

    @pytest.mark.asyncio
    async def test_classify_emitida_queries_ingreso(self):
        """tipo=emitida should query for type=ingreso in pgc_accounts."""
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.rows = [
            {"code": "700", "name": "Ventas de mercaderias", "keywords": "ventas"},
        ]
        mock_db.execute = AsyncMock(return_value=mock_result)

        with patch("app.services.invoice_classifier_service.genai") as mock_genai:
            mock_client = MagicMock()
            mock_genai.Client.return_value = mock_client

            mock_response = MagicMock()
            mock_response.text = json.dumps({
                "cuenta_code": "700",
                "cuenta_nombre": "Ventas de mercaderias",
                "confianza": "alta",
                "alternativas": [],
                "justificacion": "Venta directa de producto.",
            })
            mock_client.models.generate_content.return_value = mock_response

            service = InvoiceClassifierService(api_key="test-key", db=mock_db)
            result = await service.classify(
                concepto="Venta de producto X",
                emisor_nombre="Mi empresa SL",
                tipo="emitida",
                base_imponible=1200.0,
            )

            assert result.cuenta_code == "700"
            call_args = mock_db.execute.call_args
            assert "ingreso" in call_args[0][1]

    @pytest.mark.asyncio
    async def test_classify_with_cnae_and_actividad(self):
        """Optional cnae and actividad are forwarded to the prompt."""
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.rows = self.MOCK_PGC_ROWS
        mock_db.execute = AsyncMock(return_value=mock_result)

        with patch("app.services.invoice_classifier_service.genai") as mock_genai:
            mock_client = MagicMock()
            mock_genai.Client.return_value = mock_client

            mock_response = MagicMock()
            mock_response.text = json.dumps(self.GEMINI_RESPONSE)
            mock_client.models.generate_content.return_value = mock_response

            service = InvoiceClassifierService(api_key="test-key", db=mock_db)
            result = await service.classify(
                concepto="Servicio consultoria",
                emisor_nombre="Consultores SL",
                tipo="recibida",
                base_imponible=800.0,
                cnae="6920",
                actividad="Consultoria fiscal",
            )

            assert isinstance(result, ClasificacionPGC)
            # Verify the prompt sent to Gemini includes cnae/actividad
            call_args = mock_client.models.generate_content.call_args
            prompt_content = str(call_args)
            assert "6920" in prompt_content
            assert "Consultoria fiscal" in prompt_content

    @pytest.mark.asyncio
    async def test_classify_no_db_fallback(self):
        """When db is None, classify should still work (no candidates)."""
        with patch("app.services.invoice_classifier_service.genai") as mock_genai:
            mock_client = MagicMock()
            mock_genai.Client.return_value = mock_client

            mock_response = MagicMock()
            mock_response.text = json.dumps(self.GEMINI_RESPONSE)
            mock_client.models.generate_content.return_value = mock_response

            service = InvoiceClassifierService(api_key="test-key", db=None)
            result = await service.classify(
                concepto="Servicio generico",
                emisor_nombre="Empresa SL",
                tipo="recibida",
                base_imponible=300.0,
            )

            assert isinstance(result, ClasificacionPGC)

    @pytest.mark.asyncio
    async def test_classify_gemini_error(self):
        """Gemini API error should raise RuntimeError."""
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.rows = []
        mock_db.execute = AsyncMock(return_value=mock_result)

        with patch("app.services.invoice_classifier_service.genai") as mock_genai:
            mock_client = MagicMock()
            mock_genai.Client.return_value = mock_client
            mock_client.models.generate_content.side_effect = Exception("API down")

            service = InvoiceClassifierService(api_key="test-key", db=mock_db)
            with pytest.raises(RuntimeError, match="Gemini"):
                await service.classify(
                    concepto="Test",
                    emisor_nombre="Test SL",
                    tipo="recibida",
                    base_imponible=100.0,
                )
