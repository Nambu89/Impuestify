"""Tests para el extractor de propuesta de liquidación."""
from unittest.mock import patch
from app.services.defensia_data_extractor import extract_propuesta_liquidacion


MOCK = {
    "referencia": "REF",
    "fecha_acto": "2025-12-10",
    "plazo_alegaciones_dias": 10,
    "cuota_propuesta": 6183.05,
    "ejercicio": 2024,
    "tipo_tributo": "IRPF",
    "ajustes_propuestos": [
        {"concepto": "exencion_reinversion_vivienda_habitual", "ajuste": "denegada"},
    ],
}


@patch("app.services.defensia_data_extractor._gemini_extract_propuesta")
def test_extract_propuesta_devuelve_campos(mock_g):
    mock_g.return_value = dict(MOCK)
    d = extract_propuesta_liquidacion(b"pdf", "prop.pdf")
    assert d["plazo_alegaciones_dias"] == 10
    assert d["cuota_propuesta"] == 6183.05
    assert d["ajustes_propuestos"][0]["ajuste"] == "denegada"


@patch("app.services.defensia_data_extractor._gemini_extract_propuesta")
def test_extract_propuesta_error(mock_g):
    mock_g.side_effect = RuntimeError("network")
    d = extract_propuesta_liquidacion(b"pdf", "prop.pdf")
    assert "error" in d
    assert d["nombre"] == "prop.pdf"
