"""Tests para el extractor de requerimiento."""
from unittest.mock import patch
from app.services.defensia_data_extractor import extract_requerimiento


MOCK = {
    "referencia": "REF-REQ",
    "fecha_acto": "2025-11-03",
    "plazo_aportar_docs_dias": 10,
    "documentacion_solicitada": ["escrituras", "facturas gastos", "sentencia"],
    "ejercicio": 2024,
    "tipo_procedimiento": "comprobacion_limitada",
    "alcance": "ganancia patrimonial transmision inmueble",
}


@patch("app.services.defensia_data_extractor._gemini_extract_requerimiento")
def test_extract_requerimiento_campos(mock_g):
    mock_g.return_value = dict(MOCK)
    d = extract_requerimiento(b"pdf", "req.pdf")
    assert d["plazo_aportar_docs_dias"] == 10
    assert "escrituras" in d["documentacion_solicitada"]
    assert d["tipo_procedimiento"] == "comprobacion_limitada"


@patch("app.services.defensia_data_extractor._gemini_extract_requerimiento")
def test_extract_requerimiento_error(mock_g):
    mock_g.side_effect = Exception("boom")
    d = extract_requerimiento(b"pdf", "req.pdf")
    assert "error" in d
    assert d["nombre"] == "req.pdf"
