"""
Servicio para clasificar facturas en cuentas del Plan General Contable (PGC).
Usa Gemini 3 Flash para elegir la cuenta PGC mas apropiada dados los datos
de la factura y las cuentas candidatas de la tabla pgc_accounts.
"""

import json
import logging
from typing import Optional

from pydantic import BaseModel

logger = logging.getLogger(__name__)

try:
    from google import genai
except ImportError:
    genai = None  # type: ignore[assignment]
    logger.warning(
        "google-genai not installed. InvoiceClassifierService will not work. "
        "Install with: pip install google-genai"
    )


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------


class AlternativaPGC(BaseModel):
    """Una cuenta PGC alternativa sugerida por el clasificador."""
    code: str
    nombre: str


class ClasificacionPGC(BaseModel):
    """Resultado de la clasificacion PGC de una factura."""
    cuenta_code: str
    cuenta_nombre: str
    confianza: str  # "alta", "media", "baja"
    alternativas: list[AlternativaPGC] = []
    justificacion: str


# ---------------------------------------------------------------------------
# JSON schema for Gemini structured output
# ---------------------------------------------------------------------------

CLASSIFICATION_SCHEMA = {
    "type": "object",
    "properties": {
        "cuenta_code": {"type": "string"},
        "cuenta_nombre": {"type": "string"},
        "confianza": {"type": "string", "enum": ["alta", "media", "baja"]},
        "alternativas": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "code": {"type": "string"},
                    "nombre": {"type": "string"},
                },
                "required": ["code", "nombre"],
            },
        },
        "justificacion": {"type": "string"},
    },
    "required": ["cuenta_code", "cuenta_nombre", "confianza", "justificacion"],
}


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class InvoiceClassifierService:
    """Clasifica facturas en cuentas PGC usando Gemini."""

    def __init__(
        self,
        api_key: str,
        db=None,
        model: str = "gemini-3-flash-preview",
    ):
        if genai is None:
            raise ImportError(
                "google-genai package is required. Install with: pip install google-genai"
            )
        self.client = genai.Client(api_key=api_key)
        self.model = model
        self.db = db

    async def _get_candidate_accounts(self, tipo: str) -> list[dict]:
        """
        Queries pgc_accounts for candidate accounts based on invoice type.

        Args:
            tipo: 'recibida' (expense/gasto) or 'emitida' (income/ingreso)

        Returns:
            List of dicts with code, name, keywords.
        """
        if self.db is None:
            return []

        account_type = "gasto" if tipo == "recibida" else "ingreso"

        result = await self.db.execute(
            "SELECT code, name, keywords FROM pgc_accounts "
            "WHERE type = ? AND is_active = 1 ORDER BY code",
            [account_type],
        )

        return [
            {"code": row["code"], "name": row["name"], "keywords": row.get("keywords", "")}
            for row in (result.rows or [])
        ]

    async def classify(
        self,
        concepto: str,
        emisor_nombre: str,
        tipo: str,
        base_imponible: float,
        cnae: str = "",
        actividad: str = "",
    ) -> ClasificacionPGC:
        """
        Clasifica una factura en una cuenta PGC.

        Args:
            concepto: Descripcion/concepto de la factura.
            emisor_nombre: Nombre del emisor de la factura.
            tipo: 'recibida' o 'emitida'.
            base_imponible: Importe base en EUR.
            cnae: Codigo CNAE del usuario (opcional).
            actividad: Descripcion de la actividad economica (opcional).

        Returns:
            ClasificacionPGC con la cuenta elegida, confianza y alternativas.

        Raises:
            RuntimeError: Si Gemini falla.
        """
        candidates = await self._get_candidate_accounts(tipo)

        tipo_label = "gasto" if tipo == "recibida" else "ingreso"

        # Build candidates text
        if candidates:
            candidates_text = "\n".join(
                f"- {c['code']} {c['name']} (palabras clave: {c.get('keywords', '')})"
                for c in candidates
            )
        else:
            candidates_text = "(sin candidatas disponibles — elige la cuenta PGC mas apropiada)"

        # Build prompt
        prompt_lines = [
            "Clasifica esta factura en una cuenta del Plan General Contable espanol.",
            "",
            "Datos de la factura:",
            f"- Concepto: {concepto}",
            f"- Emisor: {emisor_nombre}",
            f"- Tipo: {tipo} ({tipo_label})",
            f"- Importe base: {base_imponible} EUR",
        ]

        if actividad:
            prompt_lines.append(f"- Actividad del usuario: {actividad}")
        if cnae:
            prompt_lines.append(f"- CNAE: {cnae}")

        prompt_lines.extend([
            "",
            "Cuentas PGC candidatas:",
            candidates_text,
            "",
            'Elige la cuenta mas apropiada. Si no estas seguro, indica confianza "media" o "baja" y da alternativas.',
        ])

        prompt = "\n".join(prompt_lines)

        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
                config={
                    "response_mime_type": "application/json",
                    "response_schema": CLASSIFICATION_SCHEMA,
                },
            )

            data = json.loads(response.text)

            alternativas = [
                AlternativaPGC(code=a["code"], nombre=a["nombre"])
                for a in data.get("alternativas", [])
            ]

            return ClasificacionPGC(
                cuenta_code=data["cuenta_code"],
                cuenta_nombre=data["cuenta_nombre"],
                confianza=data["confianza"],
                alternativas=alternativas,
                justificacion=data["justificacion"],
            )

        except Exception as e:
            logger.error("Gemini classification failed: %s", e, exc_info=True)
            raise RuntimeError(f"Gemini classification error: {e}") from e
