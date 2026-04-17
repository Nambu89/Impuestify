"""Tests para el extractor de acuerdo de imposición de sanción."""
from unittest.mock import patch
from app.services.defensia_data_extractor import extract_acuerdo_sancion


MOCK_OUT = {
    "referencia": "REF-SANCION",
    "fecha_acto": "2026-04-07",
    "importe_sancion": 3393.52,
    "base_sancion_191": 6183.05,
    "porcentaje_191": 50.0,
    "calificacion_191": "leve",
    "base_sancion_194": 2013.39,
    "porcentaje_194": 15.0,
    "calificacion_194": "grave",
    "articulos_tipicos": ["Art. 191 LGT", "Art. 194.1 LGT"],
    "reducciones_aplicadas": 0,
    "motivacion_culpabilidad": "negligencia",
    "plazo_recurso_dias": 30,
}


@patch("app.services.defensia_data_extractor._gemini_extract_sancion")
def test_extract_sancion_todos_campos(mock_gemini):
    mock_gemini.return_value = dict(MOCK_OUT)
    datos = extract_acuerdo_sancion(b"pdf", nombre="sancion.pdf")
    assert datos["importe_sancion"] == 3393.52
    assert datos["calificacion_191"] == "leve"
    assert "Art. 191 LGT" in datos["articulos_tipicos"]


@patch("app.services.defensia_data_extractor._gemini_extract_sancion")
def test_extract_sancion_detecta_doble_tipicidad_191_194(mock_gemini):
    mock_gemini.return_value = dict(MOCK_OUT)
    datos = extract_acuerdo_sancion(b"pdf", nombre="sancion.pdf")
    assert datos["tiene_doble_tipicidad_191_194"] is True


@patch("app.services.defensia_data_extractor._gemini_extract_sancion")
def test_extract_sancion_solo_191_no_doble_tipicidad(mock_gemini):
    out = dict(MOCK_OUT)
    out["base_sancion_194"] = None
    out["porcentaje_194"] = None
    out["calificacion_194"] = None
    mock_gemini.return_value = out
    datos = extract_acuerdo_sancion(b"pdf", nombre="sancion.pdf")
    assert datos["tiene_doble_tipicidad_191_194"] is False
