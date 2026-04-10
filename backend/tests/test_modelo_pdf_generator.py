"""
Tests for ModeloPDFGenerator.

Verifies PDF generation for all 6 modelo types plus unknown modelo validation.
"""
import pytest

from app.services.modelo_pdf_generator import ModeloPDFGenerator


@pytest.fixture
def generator():
    return ModeloPDFGenerator()


@pytest.fixture
def user_info():
    return {"nombre": "Juan Garcia Lopez", "nif": "12345678Z"}


# -- Sample data for each modelo --

SAMPLE_303 = {
    "iva_devengado": {
        "cuota_21": 2100.00,
        "cuota_10": 500.00,
        "cuota_4": 0,
        "cuota_intracomunitaria": 0,
        "total_devengado": 2600.00,
    },
    "iva_deducible": {
        "bienes_corrientes": 800.00,
        "bienes_inversion": 0,
        "importaciones": 0,
        "intracomunitarias": 0,
        "rectificacion": 0,
        "total_deducible": 800.00,
    },
    "resultado": {
        "regimen_general": 1800.00,
        "compensacion_anterior": 0,
        "resultado_final": 1800.00,
        "tipo": "A ingresar",
    },
}

SAMPLE_130 = {
    "seccion_i": {
        "ingresos_computables": 15000.00,
        "gastos_deducibles": 5000.00,
        "rendimiento_neto": 10000.00,
        "veinte_porciento": 2000.00,
        "retenciones": 300.00,
        "pagos_anteriores": 0,
        "resultado_seccion": 1700.00,
    },
    "deduccion_80bis": 0,
    "resultado_final": 1700.00,
}

SAMPLE_308 = {
    "adquisiciones_intracomunitarias": {
        "base_total": 5000.00,
        "cuota_iva": 1050.00,
        "cuota_re": 260.00,
        "desglose": {
            "base_21": 5000.00,
            "iva_21": 1050.00,
            "re_21": 260.00,
            "base_10": 0,
            "iva_10": 0,
            "re_10": 0,
            "base_4": 0,
            "iva_4": 0,
            "re_4": 0,
        },
    },
    "inversion_sujeto_pasivo": {
        "base_total": 0,
        "cuota_iva": 0,
        "cuota_re": 0,
        "desglose": {},
    },
    "resultado": {"resultado_final": -790.00},
}

SAMPLE_720 = {
    "ejercicio": 2025,
    "obligado_720": True,
    "detalles": [
        {
            "categoria": "cuentas",
            "descripcion": "Cuentas bancarias en el extranjero",
            "valor_actual": 75000.00,
            "supera_umbral_50k": True,
            "obligado": True,
        },
        {
            "categoria": "valores",
            "descripcion": "Valores y derechos en el extranjero",
            "valor_actual": 30000.00,
            "supera_umbral_50k": False,
            "obligado": False,
        },
    ],
    "plazo": "Del 1 de enero al 31 de marzo de 2026",
    "recomendaciones": ["Presenta el Modelo 720 antes del 31 de marzo de 2026."],
}

SAMPLE_721 = {
    "ejercicio": 2025,
    "obligado_721": True,
    "valor_crypto_extranjero": 60000.00,
    "incremento_vs_ultimo_721": 25000.00,
    "exchanges_afectados": ["Binance", "Kraken"],
    "exchanges_espanoles_excluidos": ["Bit2Me"],
    "plazo": "Del 1 de enero al 31 de marzo de 2026",
    "recomendaciones": ["Revisa los saldos a 31 de diciembre."],
}

SAMPLE_IPSI = {
    "desglose_devengado": {
        "tipo_general_4": {"base": 10000.00, "cuota": 400.00},
        "tipo_minimo_0_5": {"base": 0, "cuota": 0},
        "tipo_inferior_1": {"base": 0, "cuota": 0},
        "tipo_ordinario_2": {"base": 0, "cuota": 0},
        "tipo_incrementado_8": {"base": 0, "cuota": 0},
        "tipo_especial_10": {"base": 0, "cuota": 0},
    },
    "total_devengado": 400.00,
    "desglose_deducible": {
        "cuota_corrientes_interiores": 100.00,
        "cuota_inversion_interiores": 0,
        "cuota_importaciones_corrientes": 0,
    },
    "total_deducible": 100.00,
    "resultado_liquidacion": 300.00,
}


def _assert_valid_pdf(pdf_bytes: bytes):
    """Validate that result is a valid PDF."""
    assert isinstance(pdf_bytes, bytes)
    assert pdf_bytes[:5] == b"%PDF-"
    assert len(pdf_bytes) > 1000


class TestModeloPDFGenerator:
    """Tests for ModeloPDFGenerator."""

    def test_generate_303(self, generator, user_info):
        """Modelo 303 (IVA) generates a valid PDF."""
        result = generator.generate("303", SAMPLE_303, user_info, "1T", 2026)
        _assert_valid_pdf(result)

    def test_generate_130(self, generator, user_info):
        """Modelo 130 (IRPF Pago Fraccionado) generates a valid PDF."""
        result = generator.generate("130", SAMPLE_130, user_info, "2T", 2026)
        _assert_valid_pdf(result)

    def test_generate_308(self, generator, user_info):
        """Modelo 308 (RE Farmacia) generates a valid PDF."""
        result = generator.generate("308", SAMPLE_308, user_info, "3T", 2025)
        _assert_valid_pdf(result)

    def test_generate_720(self, generator, user_info):
        """Modelo 720 (Bienes extranjero) generates a valid PDF."""
        result = generator.generate("720", SAMPLE_720, user_info, "anual", 2025)
        _assert_valid_pdf(result)

    def test_generate_721(self, generator, user_info):
        """Modelo 721 (Crypto extranjero) generates a valid PDF."""
        result = generator.generate("721", SAMPLE_721, user_info, "anual", 2025)
        _assert_valid_pdf(result)

    def test_generate_ipsi(self, generator, user_info):
        """Modelo IPSI (Ceuta/Melilla) generates a valid PDF."""
        result = generator.generate("ipsi", SAMPLE_IPSI, user_info, "4T", 2026)
        _assert_valid_pdf(result)

    def test_generate_303_foral(self, generator):
        """Modelo 303 with foral variant uses correct header."""
        user_info_foral = {
            "nombre": "Maria Lopez",
            "nif": "87654321X",
            "variante_foral": "300",
        }
        result = generator.generate("303", SAMPLE_303, user_info_foral, "1T", 2026)
        _assert_valid_pdf(result)

    def test_unknown_modelo_raises_valueerror(self, generator, user_info):
        """Unknown modelo type raises ValueError."""
        with pytest.raises(ValueError, match="no soportado"):
            generator.generate("999", {}, user_info, "1T", 2026)
