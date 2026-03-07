"""Tests for DeclarationExtractor -- extraction of Modelo 303/130/420 from PDF text."""
import pytest
from app.services.declaration_extractor import (
    DeclarationExtractor,
    detect_modelo,
    _parse_spanish_number,
    _extract_metadata,
    _extract_casillas_generic,
)


# ===========================================================================
# Spanish number parsing
# ===========================================================================

class TestParseSpanishNumber:
    def test_spanish_format(self):
        assert _parse_spanish_number("1.234,56") == 1234.56

    def test_large_spanish(self):
        assert _parse_spanish_number("12.345.678,90") == 12345678.90

    def test_simple_comma_decimal(self):
        assert _parse_spanish_number("1234,56") == 1234.56

    def test_integer(self):
        assert _parse_spanish_number("5000") == 5000.0

    def test_negative(self):
        assert _parse_spanish_number("-1.234,56") == -1234.56

    def test_english_format(self):
        assert _parse_spanish_number("1,234.56") == 1234.56

    def test_none(self):
        assert _parse_spanish_number("") is None
        assert _parse_spanish_number(None) is None

    def test_whitespace(self):
        assert _parse_spanish_number(" 100,50 ") == 100.50


# ===========================================================================
# Model detection
# ===========================================================================

class TestDetectModelo:
    def test_detect_303(self):
        assert detect_modelo("MODELO 303 - IVA Autoliquidacion") == "303"

    def test_detect_130(self):
        assert detect_modelo("Modelo 130 - Pago fraccionado IRPF") == "130"

    def test_detect_420(self):
        assert detect_modelo("Modelo 420 - IGIC Canarias") == "420"

    def test_detect_300_as_303(self):
        """Pais Vasco Modelo 300 maps to 303."""
        assert detect_modelo("Modelo 300 - IVA Declaracion") == "303"

    def test_detect_pago_fraccionado(self):
        assert detect_modelo("Pago fraccionado trimestral") == "130"

    def test_detect_igic(self):
        assert detect_modelo("Autoliquidacion IGIC trimestral") == "420"

    def test_detect_iva_autoliquidacion(self):
        assert detect_modelo("Autoliquidacion IVA periodo 2T") == "303"

    def test_unknown(self):
        assert detect_modelo("Documento desconocido") is None


# ===========================================================================
# Metadata extraction
# ===========================================================================

class TestExtractMetadata:
    def test_nif(self):
        meta = _extract_metadata("NIF: B12345678 contribuyente")
        assert meta["nif"] == "B12345678"

    def test_year(self):
        meta = _extract_metadata("Ejercicio: 2025")
        assert meta["year"] == 2025

    def test_quarter(self):
        meta = _extract_metadata("Periodo: 2T")
        assert meta["quarter"] == 2

    def test_quarter_alt(self):
        meta = _extract_metadata("3 Trimestre 2025")
        assert meta["quarter"] == 3

    def test_complementaria(self):
        meta = _extract_metadata("Declaracion complementaria ejercicio 2025")
        assert meta["complementaria"] is True

    def test_not_complementaria(self):
        meta = _extract_metadata("Declaracion ordinaria")
        assert meta["complementaria"] is False

    def test_nombre(self):
        meta = _extract_metadata("Apellidos y nombre: GARCIA LOPEZ JUAN ANTONIO")
        assert "GARCIA LOPEZ" in meta["nombre"]


# ===========================================================================
# Generic casilla extraction
# ===========================================================================

class TestExtractCasillasGeneric:
    def test_bracket_format(self):
        text = "[01] 15.000,00\n[02] 3.500,25\n[03] 11.499,75"
        casillas = _extract_casillas_generic(text)
        assert casillas["1"] == 15000.0
        assert casillas["2"] == 3500.25
        assert casillas["3"] == 11499.75

    def test_casilla_label(self):
        text = "Casilla 07: 10.000,00\nCasilla 09: 2.100,00"
        casillas = _extract_casillas_generic(text)
        assert casillas["7"] == 10000.0
        assert casillas["9"] == 2100.0

    def test_casilla_no(self):
        text = "casilla no 45: 500,00"
        casillas = _extract_casillas_generic(text)
        assert casillas["45"] == 500.0


# ===========================================================================
# Full extraction: Modelo 303
# ===========================================================================

SAMPLE_303_TEXT = """
MODELO 303 - IMPUESTO SOBRE EL VALOR ANADIDO
Autoliquidacion

NIF: B98765432
Apellidos y nombre: LOPEZ MARTINEZ MARIA
Ejercicio: 2025
Periodo: 2T

IVA DEVENGADO
[01] 0,00
[03] 0,00
[04] 0,00
[06] 0,00
[07] 10.000,00
[08] 21
[09] 2.100,00
[27] 2.100,00

IVA DEDUCIBLE
[29] 500,00
[45] 500,00

RESULTADO
[46] 1.600,00
[65] 100,00
[66] 1.600,00
[78] 0,00
[71] 1.600,00
"""


class TestExtract303:
    def setup_method(self):
        self.extractor = DeclarationExtractor()

    def test_full_extraction(self):
        result = self.extractor.extract(SAMPLE_303_TEXT)
        assert result.success is True
        assert result.modelo == "303"
        assert result.metadata["nif"] == "B98765432"
        assert result.metadata["year"] == 2025
        assert result.metadata["quarter"] == 2

    def test_key_fields(self):
        result = self.extractor.extract(SAMPLE_303_TEXT)
        f = result.fields
        assert f["base_21"] == 10000.0
        assert f["cuota_21"] == 2100.0
        assert f["total_devengado"] == 2100.0
        assert f["total_deducible"] == 500.0
        assert f["resultado_liquidacion"] == 1600.0

    def test_confidence_high(self):
        result = self.extractor.extract(SAMPLE_303_TEXT)
        assert result.confidence >= 0.8

    def test_to_form_data(self):
        result = self.extractor.extract(SAMPLE_303_TEXT)
        form = result.to_form_data()
        assert form["base_21"] == 10000.0
        assert form["territory"] == "Comun"
        assert "extraction_confidence" in form


# ===========================================================================
# Full extraction: Modelo 130
# ===========================================================================

SAMPLE_130_TEXT = """
MODELO 130 - PAGO FRACCIONADO IRPF
Estimacion directa

NIF: 12345678A
Apellidos y nombre: PEREZ RUIZ CARLOS
Ejercicio: 2025
Periodo: 1T

SECCION I: Actividades economicas en estimacion directa
[01] 30.000,00
[02] 10.000,00
[03] 20.000,00
[04] 4.000,00
[05] 1.500,00
[06] 0,00
[07] 2.500,00

SECCION III: Total liquidacion
[12] 2.500,00
[13] 0,00
[16] 400,00
[19] 2.100,00
"""


class TestExtract130:
    def setup_method(self):
        self.extractor = DeclarationExtractor()

    def test_full_extraction(self):
        result = self.extractor.extract(SAMPLE_130_TEXT)
        assert result.success is True
        assert result.modelo == "130"
        assert result.metadata["nif"] == "12345678A"
        assert result.metadata["quarter"] == 1

    def test_key_fields(self):
        result = self.extractor.extract(SAMPLE_130_TEXT)
        f = result.fields
        assert f["ingresos_acumulados"] == 30000.0
        assert f["gastos_acumulados"] == 10000.0
        assert f["rendimiento_neto"] == 20000.0
        assert f["resultado_final"] == 2100.0

    def test_territory_comun(self):
        result = self.extractor.extract(SAMPLE_130_TEXT)
        assert result.territory == "Comun"

    def test_territory_ceuta(self):
        text = SAMPLE_130_TEXT.replace("Estimacion directa", "Residente en Ceuta")
        result = self.extractor.extract(text)
        assert result.territory == "Ceuta/Melilla"

    def test_territory_araba(self):
        text = SAMPLE_130_TEXT.replace("Estimacion directa", "Diputacion Foral de Araba")
        result = self.extractor.extract(text)
        assert result.territory == "Araba"

    def test_confidence(self):
        result = self.extractor.extract(SAMPLE_130_TEXT)
        assert result.confidence >= 0.7


# ===========================================================================
# Full extraction: Modelo 420
# ===========================================================================

SAMPLE_420_TEXT = """
MODELO 420 - IGIC CANARIAS
Autoliquidacion trimestral

NIF: A11111111
Ejercicio: 2025
Periodo: 3T

IGIC DEVENGADO
Tipo general 7%
Base imponible: 20.000,00
Cuota: 1.400,00
Total IGIC devengado: 1.400,00

IGIC DEDUCIBLE
Total a deducir: 300,00

RESULTADO
Resultado de la liquidacion: 1.100,00
"""


class TestExtract420:
    def setup_method(self):
        self.extractor = DeclarationExtractor()

    def test_full_extraction(self):
        result = self.extractor.extract(SAMPLE_420_TEXT)
        assert result.success is True
        assert result.modelo == "420"

    def test_key_fields(self):
        result = self.extractor.extract(SAMPLE_420_TEXT)
        f = result.fields
        assert f.get("total_devengado") == 1400.0
        assert f.get("total_deducible") == 300.0
        assert f.get("resultado_liquidacion") == 1100.0


# ===========================================================================
# Edge cases
# ===========================================================================

class TestEdgeCases:
    def setup_method(self):
        self.extractor = DeclarationExtractor()

    def test_empty_text(self):
        result = self.extractor.extract("")
        assert result.success is False
        assert "too short" in result.error

    def test_unknown_model(self):
        result = self.extractor.extract("Este es un documento largo sin modelo identificable. " * 5)
        assert result.success is False
        assert "Could not detect" in result.error

    def test_explicit_modelo_hint(self):
        """Can force modelo via hint even if auto-detect would fail."""
        text = "[07] 10.000,00\n[09] 2.100,00\n[27] 2.100,00\n[45] 0,00\n[71] 2.100,00\n" + "x " * 30
        result = self.extractor.extract(text, modelo="303")
        assert result.success is True
        assert result.modelo == "303"
        assert result.fields.get("base_21") == 10000.0

    def test_modelo_with_label_fallback(self):
        """Label-based extraction as fallback when casillas not found."""
        text = """Modelo 303
        Ejercicio: 2025
        Periodo: 1T
        Total IVA devengado: 3.500,00
        Total a deducir: 1.200,00
        Resultado de la liquidacion: 2.300,00
        """ + "padding " * 10
        result = self.extractor.extract(text)
        assert result.success is True
        assert result.fields.get("total_devengado") == 3500.0
        assert result.fields.get("resultado_liquidacion") == 2300.0
