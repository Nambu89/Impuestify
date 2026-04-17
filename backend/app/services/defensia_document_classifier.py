"""Clasificador de documentos tributarios.

Estrategia de dos niveles:
1. Regex determinista rápido (defensia_document_taxonomy) — 0 coste LLM.
2. Fallback a Gemini Vision cuando el regex no identifica.

El clasificador devuelve siempre un ClassificationResult con la fuente
(regex, gemini, fallback) para trazabilidad.
"""
from __future__ import annotations
import json
import logging
from dataclasses import dataclass
from app.models.defensia import TipoDocumento
from app.services.defensia_document_taxonomy import clasificar_por_texto

logger = logging.getLogger(__name__)


@dataclass
class ClassificationResult:
    tipo: TipoDocumento
    confianza: float
    fuente: str  # "regex" | "gemini" | "fallback"


_GEMINI_PROMPT = """Eres un clasificador de documentos tributarios españoles.
Dado el texto siguiente, identifica el tipo de documento. Responde SOLO con un
JSON con esta forma exacta:
{"tipo": "<uno de los valores permitidos>", "confianza": 0.0-1.0}

Valores permitidos:
- REQUERIMIENTO
- PROPUESTA_LIQUIDACION
- LIQUIDACION_PROVISIONAL
- ACUERDO_INICIO_SANCIONADOR
- PROPUESTA_SANCION
- ACUERDO_IMPOSICION_SANCION
- ESCRITO_ALEGACIONES_USUARIO
- ESCRITO_REPOSICION_USUARIO
- ESCRITO_RECLAMACION_TEAR_USUARIO
- ACTA_INSPECCION
- PROVIDENCIA_APREMIO
- RESOLUCION_TEAR
- RESOLUCION_TEAC
- SENTENCIA_JUDICIAL
- JUSTIFICANTE_PAGO
- FACTURA
- ESCRITURA
- LIBRO_REGISTRO
- OTROS

TEXTO:
"""


def _gemini_classify(texto: str) -> ClassificationResult:
    """Llama a Gemini Vision para clasificar.

    Aislado en función propia para facilitar el mock en tests.
    Reutiliza el cliente google-genai ya configurado en el proyecto (ver
    backend/app/services/invoice_ocr_service.py).
    """
    from google import genai
    from app.config import settings

    client = genai.Client(api_key=settings.GOOGLE_GEMINI_API_KEY)
    texto_truncado = texto[:8000]
    response = client.models.generate_content(
        model="gemini-3-flash-preview",
        contents=_GEMINI_PROMPT + texto_truncado,
    )
    raw = response.text.strip().strip("`")
    if raw.startswith("json"):
        raw = raw[4:].lstrip()
    payload = json.loads(raw)
    tipo = TipoDocumento(payload["tipo"])
    confianza = float(payload.get("confianza", 0.5))
    return ClassificationResult(tipo=tipo, confianza=confianza, fuente="gemini")


class DocumentClassifier:
    """Clasificador fachada. Usa fast-path regex y fallback Gemini."""

    def classify_text(self, texto: str) -> ClassificationResult:
        tipo_regex = clasificar_por_texto(texto)
        if tipo_regex != TipoDocumento.OTROS:
            return ClassificationResult(
                tipo=tipo_regex, confianza=0.95, fuente="regex"
            )
        try:
            return _gemini_classify(texto)
        except Exception as exc:
            logger.warning("Gemini classification failed: %s", exc)
            return ClassificationResult(
                tipo=TipoDocumento.OTROS, confianza=0.0, fuente="fallback"
            )
