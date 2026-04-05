"""Tests for InvoiceOCRService — Gemini 3 Flash Vision invoice extraction."""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.invoice_ocr_service import (
    EmisorReceptor,
    ExtractionResult,
    FacturaExtraida,
    InvoiceOCRService,
    LineaFactura,
    validate_iva_math,
    validate_nif,
)


# ---------------------------------------------------------------------------
# validate_nif
# ---------------------------------------------------------------------------

class TestValidateNif:
    """NIF/CIF/NIE validation tests."""

    def test_valid_dni(self):
        # 12345678 mod 23 = 14 -> letter Z
        assert validate_nif("12345678Z") is True

    def test_invalid_dni_letter(self):
        assert validate_nif("12345678A") is False

    def test_valid_nie_x(self):
        # X0000000 -> 00000000 mod 23 = 0 -> T
        assert validate_nif("X0000000T") is True

    def test_valid_nie_y(self):
        # Y0000000 -> 10000000 mod 23 = 10000000 % 23
        remainder = 10000000 % 23
        letters = "TRWAGMYFPDXBNJZSQVHLCKE"
        expected = letters[remainder]
        assert validate_nif(f"Y0000000{expected}") is True

    def test_valid_nie_z(self):
        remainder = 20000000 % 23
        letters = "TRWAGMYFPDXBNJZSQVHLCKE"
        expected = letters[remainder]
        assert validate_nif(f"Z0000000{expected}") is True

    def test_cif_valid_format(self):
        assert validate_nif("B12345678") is True

    def test_cif_invalid_prefix(self):
        # '1' is not a valid CIF prefix letter
        assert validate_nif("112345678") is False

    def test_short_nif(self):
        assert validate_nif("1234") is False

    def test_empty_nif(self):
        assert validate_nif("") is False

    def test_none_nif(self):
        assert validate_nif(None) is False

    def test_nif_with_spaces(self):
        # Should handle stripped input
        assert validate_nif("  12345678Z  ") is True


# ---------------------------------------------------------------------------
# validate_iva_math
# ---------------------------------------------------------------------------

class TestValidateIvaMath:
    """IVA arithmetic validation tests."""

    def _make_factura(self, **overrides) -> FacturaExtraida:
        defaults = dict(
            emisor=EmisorReceptor(nif_cif="B12345678", nombre="Acme SL"),
            receptor=EmisorReceptor(nif_cif="12345678Z", nombre="Juan"),
            numero_factura="F-001",
            fecha_factura="2026-01-15",
            lineas=[
                LineaFactura(
                    concepto="Servicio",
                    cantidad=1,
                    precio_unitario=100.0,
                    base_imponible=100.0,
                )
            ],
            base_imponible_total=100.0,
            tipo_iva_pct=21.0,
            cuota_iva=21.0,
            total=121.0,
            tipo="recibida",
        )
        defaults.update(overrides)
        return FacturaExtraida(**defaults)

    def test_correct_21_iva(self):
        f = self._make_factura()
        errors = validate_iva_math(f)
        assert errors == []

    def test_iva_mismatch(self):
        f = self._make_factura(cuota_iva=20.0)  # should be 21
        errors = validate_iva_math(f)
        assert any("IVA" in e for e in errors)

    def test_total_mismatch(self):
        f = self._make_factura(total=999.0)
        errors = validate_iva_math(f)
        assert any("total" in e.lower() for e in errors)

    def test_total_with_irpf_retention(self):
        # base 100 + iva 21 - irpf 15 = 106
        f = self._make_factura(
            retencion_irpf_pct=15.0,
            retencion_irpf=15.0,
            total=106.0,
        )
        errors = validate_iva_math(f)
        assert errors == []

    def test_total_with_re(self):
        # base 100 + iva 21 + re 5.2 = 126.2
        f = self._make_factura(
            tipo_re_pct=5.2,
            cuota_re=5.2,
            total=126.2,
        )
        errors = validate_iva_math(f)
        assert errors == []

    def test_tolerance_ok(self):
        # Within 0.05 tolerance
        f = self._make_factura(cuota_iva=21.04)
        errors = validate_iva_math(f)
        assert errors == []

    def test_tolerance_exceeded(self):
        f = self._make_factura(cuota_iva=21.10)
        errors = validate_iva_math(f)
        assert len(errors) > 0


# ---------------------------------------------------------------------------
# InvoiceOCRService.extract_from_bytes
# ---------------------------------------------------------------------------

class TestInvoiceOCRService:
    """Integration-style tests with mocked Gemini client."""

    SAMPLE_RESPONSE = {
        "emisor": {"nif_cif": "B12345678", "nombre": "Acme SL", "direccion": "Calle Mayor 1"},
        "receptor": {"nif_cif": "12345678Z", "nombre": "Juan Lopez"},
        "numero_factura": "F-2026-001",
        "fecha_factura": "2026-03-15",
        "fecha_operacion": None,
        "lineas": [
            {
                "concepto": "Consultoria fiscal",
                "cantidad": 10,
                "precio_unitario": 50.0,
                "base_imponible": 500.0,
            }
        ],
        "base_imponible_total": 500.0,
        "tipo_iva_pct": 21.0,
        "cuota_iva": 105.0,
        "tipo_re_pct": None,
        "cuota_re": None,
        "retencion_irpf_pct": 15.0,
        "retencion_irpf": 75.0,
        "total": 530.0,
        "tipo": "recibida",
    }

    @pytest.mark.asyncio
    async def test_extract_success(self):
        with patch("app.services.invoice_ocr_service.genai") as mock_genai:
            mock_client = MagicMock()
            mock_genai.Client.return_value = mock_client

            mock_response = MagicMock()
            mock_response.text = json.dumps(self.SAMPLE_RESPONSE)
            mock_client.models.generate_content.return_value = mock_response

            service = InvoiceOCRService(api_key="test-key")
            result = await service.extract_from_bytes(b"fake-pdf", "application/pdf")

            assert isinstance(result, ExtractionResult)
            assert result.factura.numero_factura == "F-2026-001"
            assert result.factura.base_imponible_total == 500.0
            assert result.factura.total == 530.0
            assert result.nif_emisor_valido is True
            assert result.nif_receptor_valido is True
            assert result.confianza == "alta"
            assert result.errores_validacion == []

    @pytest.mark.asyncio
    async def test_extract_with_iva_error(self):
        bad_response = dict(self.SAMPLE_RESPONSE)
        bad_response["cuota_iva"] = 999.0  # wrong

        with patch("app.services.invoice_ocr_service.genai") as mock_genai:
            mock_client = MagicMock()
            mock_genai.Client.return_value = mock_client

            mock_response = MagicMock()
            mock_response.text = json.dumps(bad_response)
            mock_client.models.generate_content.return_value = mock_response

            service = InvoiceOCRService(api_key="test-key")
            result = await service.extract_from_bytes(b"fake-pdf", "application/pdf")

            assert result.confianza == "baja"
            assert len(result.errores_validacion) > 0

    @pytest.mark.asyncio
    async def test_extract_invalid_nif(self):
        bad_response = dict(self.SAMPLE_RESPONSE)
        bad_response["emisor"] = {"nif_cif": "XXXXXXXXX", "nombre": "Bad Co"}

        with patch("app.services.invoice_ocr_service.genai") as mock_genai:
            mock_client = MagicMock()
            mock_genai.Client.return_value = mock_client

            mock_response = MagicMock()
            mock_response.text = json.dumps(bad_response)
            mock_client.models.generate_content.return_value = mock_response

            service = InvoiceOCRService(api_key="test-key")
            result = await service.extract_from_bytes(b"fake-img", "image/jpeg")

            assert result.nif_emisor_valido is False
            assert result.confianza in ("media", "baja")

    @pytest.mark.asyncio
    async def test_extract_gemini_error(self):
        with patch("app.services.invoice_ocr_service.genai") as mock_genai:
            mock_client = MagicMock()
            mock_genai.Client.return_value = mock_client
            mock_client.models.generate_content.side_effect = Exception("API down")

            service = InvoiceOCRService(api_key="test-key")
            with pytest.raises(RuntimeError, match="Gemini"):
                await service.extract_from_bytes(b"fake", "application/pdf")

    @pytest.mark.asyncio
    async def test_custom_model(self):
        with patch("app.services.invoice_ocr_service.genai") as mock_genai:
            mock_client = MagicMock()
            mock_genai.Client.return_value = mock_client

            mock_response = MagicMock()
            mock_response.text = json.dumps(self.SAMPLE_RESPONSE)
            mock_client.models.generate_content.return_value = mock_response

            service = InvoiceOCRService(api_key="k", model="gemini-2.5-flash")
            await service.extract_from_bytes(b"data", "application/pdf")

            call_kwargs = mock_client.models.generate_content.call_args
            assert call_kwargs.kwargs.get("model") == "gemini-2.5-flash" or \
                   call_kwargs[1].get("model") == "gemini-2.5-flash"
