"""Extractor de datos estructurados de documentos tributarios.

Cada función `extract_*` devuelve un dict tipado con los campos relevantes
del documento. Las funciones usan Gemini Vision internamente y exponen
helpers `_gemini_extract_*` aislados para facilitar mocks en tests.

Cálculos derivados (ej: diff_gastos_adquisicion_no_admitidos) se hacen en
Python puro sobre los campos devueltos por Gemini — cero LLM en esa parte,
para trazabilidad.
"""
from __future__ import annotations
import json
import logging
from typing import Any

logger = logging.getLogger(__name__)


def _parse_gemini_json(raw: str) -> dict[str, Any]:
    """Limpia y parsea la respuesta JSON de Gemini.

    Gemini a veces envuelve el JSON en ```json ... ``` o añade texto extra.
    Esta función aisla la lógica de limpieza para que sea consistente entre
    extractores y fácil de testear.
    """
    cleaned = raw.strip().strip("`")
    if cleaned.startswith("json"):
        cleaned = cleaned[4:].lstrip()
    return json.loads(cleaned)


_PROMPT_LIQUIDACION = """Eres un extractor de datos de liquidaciones provisionales
de IRPF emitidas por la AEAT española. Dado el texto del documento, devuelve un
JSON con los siguientes campos EXACTOS (null si no aparecen):

{
  "referencia": string,
  "fecha_acto": "YYYY-MM-DD",
  "cuota": number,
  "intereses_demora": number,
  "total_a_ingresar": number,
  "ejercicio": integer,
  "ccaa": string (nombre canónico con tildes),
  "tipo_tributo": "IRPF",
  "plazo_recurso_dias": integer,
  "ganancia_patrimonial": number | null,
  "gastos_adquisicion_declarados": number | null,
  "gastos_adquisicion_admitidos": number | null,
  "gastos_transmision_admitidos": number | null,
  "motivacion_articulos_citados": [string]
}

NO inventes valores. Si un campo no aparece literalmente, devuelve null.
Responde SOLO con el JSON, sin texto adicional.

DOCUMENTO:
"""


def _gemini_extract_liquidacion(pdf_bytes: bytes, nombre: str) -> dict[str, Any]:
    """Llama a Gemini Vision sobre el PDF. Aislado para mock en tests."""
    from google import genai
    from app.config import settings

    client = genai.Client(api_key=settings.GOOGLE_GEMINI_API_KEY)
    response = client.models.generate_content(
        model="gemini-3-flash-preview",
        contents=[
            _PROMPT_LIQUIDACION,
            {"inline_data": {"mime_type": "application/pdf", "data": pdf_bytes}},
        ],
    )
    return _parse_gemini_json(response.text)


def extract_liquidacion_provisional(pdf_bytes: bytes, nombre: str) -> dict[str, Any]:
    """Extrae datos de una liquidación provisional IRPF.

    Añade campos derivados calculados en Python puro:
    - diff_gastos_adquisicion_no_admitidos: diferencia entre gastos declarados
      y admitidos por AEAT (> 0 indica un posible argumento por falta de
      motivación específica).
    """
    try:
        datos = _gemini_extract_liquidacion(pdf_bytes, nombre)
    except Exception as exc:
        logger.error("Extracción liquidación falló para %s: %s", nombre, exc)
        return {"error": str(exc), "nombre": nombre}

    declarados = datos.get("gastos_adquisicion_declarados")
    admitidos = datos.get("gastos_adquisicion_admitidos")
    if declarados is not None and admitidos is not None:
        datos["diff_gastos_adquisicion_no_admitidos"] = round(
            declarados - admitidos, 2
        )

    return datos
