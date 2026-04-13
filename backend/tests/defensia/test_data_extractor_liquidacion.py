"""Tests para el extractor de liquidación provisional IRPF."""
import pytest
from unittest.mock import patch
from app.services.defensia_data_extractor import extract_liquidacion_provisional


MOCK_GEMINI_OUTPUT = {
    "referencia": "REF-XXXXX",
    "fecha_acto": "2026-01-30",
    "cuota": 6183.05,
    "intereses_demora": 147.27,
    "total_a_ingresar": 6330.32,
    "ejercicio": 2024,
    "ccaa": "Madrid",
    "tipo_tributo": "IRPF",
    "plazo_recurso_dias": 30,
    "ganancia_patrimonial": 39561.80,
    "gastos_adquisicion_declarados": 12108.80,
    "gastos_adquisicion_admitidos": 11349.55,
    "gastos_transmision_admitidos": 9988.65,
    "motivacion_articulos_citados": ["Art. 38.1 LIRPF", "Art. 41 bis RIRPF"],
}


@patch("app.services.defensia_data_extractor._gemini_extract_liquidacion")
def test_extract_liquidacion_devuelve_campos_esperados(mock_gemini):
    mock_gemini.return_value = dict(MOCK_GEMINI_OUTPUT)
    datos = extract_liquidacion_provisional(b"fake pdf bytes", nombre="liq.pdf")
    assert datos["cuota"] == 6183.05
    assert datos["total_a_ingresar"] == 6330.32
    assert datos["ejercicio"] == 2024
    assert datos["ganancia_patrimonial"] == 39561.80
    assert "Art. 38.1 LIRPF" in datos["motivacion_articulos_citados"]


@patch("app.services.defensia_data_extractor._gemini_extract_liquidacion")
def test_extract_liquidacion_diff_gastos_adquisicion_calculado(mock_gemini):
    mock_gemini.return_value = dict(MOCK_GEMINI_OUTPUT)
    datos = extract_liquidacion_provisional(b"fake pdf bytes", nombre="liq.pdf")
    assert datos["diff_gastos_adquisicion_no_admitidos"] == pytest.approx(759.25, abs=0.01)


@patch("app.services.defensia_data_extractor._gemini_extract_liquidacion")
def test_extract_liquidacion_gemini_error_devuelve_error(mock_gemini):
    mock_gemini.side_effect = Exception("API error")
    datos = extract_liquidacion_provisional(b"fake", nombre="liq.pdf")
    assert "error" in datos
    assert datos["nombre"] == "liq.pdf"
