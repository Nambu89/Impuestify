"""Tests para el extractor de escritos del contribuyente."""
from unittest.mock import patch
from app.services.defensia_data_extractor import extract_escrito_usuario


MOCK = {
    "tipo_escrito": "reclamacion_tear",
    "referencia_acto_impugnado": "202410049560746N",
    "fecha_presentacion": "2026-02-01",
    "organo_destinatario": "TEAR Madrid",
    "pretension_principal": "anulacion liquidacion",
    "argumentos_invocados": ["interpretacion razonable", "motivacion insuficiente"],
    "tributo": "IRPF",
    "ejercicio": 2024,
}


@patch("app.services.defensia_data_extractor._gemini_extract_escrito_usuario")
def test_extract_escrito_usuario_identifica_reclamacion(mock_g):
    mock_g.return_value = dict(MOCK)
    d = extract_escrito_usuario(b"pdf", "reclamacion.pdf")
    assert d["tipo_escrito"] == "reclamacion_tear"
    assert "motivacion insuficiente" in d["argumentos_invocados"]


@patch("app.services.defensia_data_extractor._gemini_extract_escrito_usuario")
def test_extract_escrito_usuario_error(mock_g):
    mock_g.side_effect = Exception("x")
    d = extract_escrito_usuario(b"pdf", "x.pdf")
    assert "error" in d
