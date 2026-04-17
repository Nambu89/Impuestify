"""Tests para DocumentClassifier — usa fast-path regex + fallback Gemini."""
from unittest.mock import patch
from app.models.defensia import TipoDocumento
from app.services.defensia_document_classifier import (
    DocumentClassifier, ClassificationResult,
)


def test_classifier_usa_fast_path_si_regex_identifica():
    classifier = DocumentClassifier()
    texto = "NOTIFICACIÓN DE RESOLUCIÓN CON LIQUIDACIÓN PROVISIONAL"
    result = classifier.classify_text(texto)
    assert result.tipo == TipoDocumento.LIQUIDACION_PROVISIONAL
    assert result.confianza >= 0.95
    assert result.fuente == "regex"


@patch("app.services.defensia_document_classifier._gemini_classify")
def test_classifier_fallback_gemini_si_regex_otros(mock_gemini):
    mock_gemini.return_value = ClassificationResult(
        tipo=TipoDocumento.SENTENCIA_JUDICIAL,
        confianza=0.87,
        fuente="gemini",
    )
    classifier = DocumentClassifier()
    result = classifier.classify_text("Texto ambiguo sin encabezado reconocible")
    assert result.tipo == TipoDocumento.SENTENCIA_JUDICIAL
    assert result.fuente == "gemini"
    mock_gemini.assert_called_once()


@patch("app.services.defensia_document_classifier._gemini_classify")
def test_classifier_devuelve_otros_si_gemini_falla(mock_gemini):
    mock_gemini.side_effect = Exception("API error")
    classifier = DocumentClassifier()
    result = classifier.classify_text("Texto cualquiera")
    assert result.tipo == TipoDocumento.OTROS
    assert result.fuente == "fallback"
    assert result.confianza == 0.0
