"""Invoice OCR service using Gemini 3 Flash Vision for Spanish invoice extraction."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Optional

from pydantic import BaseModel

try:
    from google import genai
    from google.genai import types

    GENAI_AVAILABLE = True
except ImportError:
    genai = None  # type: ignore[assignment]
    types = None  # type: ignore[assignment]
    GENAI_AVAILABLE = False


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------


class EmisorReceptor(BaseModel):
    nif_cif: str
    nombre: str
    direccion: Optional[str] = None


class LineaFactura(BaseModel):
    concepto: str
    cantidad: float
    precio_unitario: float
    base_imponible: float


class FacturaExtraida(BaseModel):
    emisor: EmisorReceptor
    receptor: EmisorReceptor
    numero_factura: str
    fecha_factura: str
    fecha_operacion: Optional[str] = None
    lineas: list[LineaFactura]
    base_imponible_total: float
    tipo_iva_pct: float
    cuota_iva: float
    tipo_re_pct: Optional[float] = None
    cuota_re: Optional[float] = None
    retencion_irpf_pct: Optional[float] = None
    retencion_irpf: Optional[float] = None
    total: float
    tipo: Literal["emitida", "recibida"]


# ---------------------------------------------------------------------------
# Extraction result
# ---------------------------------------------------------------------------


@dataclass
class ExtractionResult:
    factura: FacturaExtraida
    confianza: Literal["alta", "media", "baja"]
    errores_validacion: list[str] = field(default_factory=list)
    nif_emisor_valido: bool = False
    nif_receptor_valido: bool = False


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------

_NIF_LETTERS = "TRWAGMYFPDXBNJZSQVHLCKE"
_CIF_PREFIXES = set("ABCDEFGHJNPQRSUVW")


def validate_nif(nif: str | None) -> bool:
    """Validate a Spanish NIF (DNI / NIE / CIF).

    DNI: 8 digits + check letter.
    NIE: X/Y/Z + 7 digits + check letter (X->0, Y->1, Z->2).
    CIF: letter prefix + 7 digits + control char (basic format check).
    """
    if not nif or not isinstance(nif, str):
        return False

    nif = nif.strip().upper()

    if len(nif) < 5:
        return False

    # --- DNI: 8 digits + letter ---
    if len(nif) == 9 and nif[:8].isdigit() and nif[8].isalpha():
        number = int(nif[:8])
        expected = _NIF_LETTERS[number % 23]
        return nif[8] == expected

    # --- NIE: X/Y/Z + 7 digits + letter ---
    if len(nif) == 9 and nif[0] in "XYZ" and nif[1:8].isdigit() and nif[8].isalpha():
        prefix_map = {"X": "0", "Y": "1", "Z": "2"}
        number = int(prefix_map[nif[0]] + nif[1:8])
        expected = _NIF_LETTERS[number % 23]
        return nif[8] == expected

    # --- CIF: letter + 7 digits + control (letter or digit) ---
    if len(nif) == 9 and nif[0] in _CIF_PREFIXES and nif[1:8].isdigit():
        return True  # Basic format validation only

    return False


def validate_iva_math(f: FacturaExtraida) -> list[str]:
    """Check IVA and total arithmetic consistency.

    Tolerances: +/- 0.05 EUR for rounding.
    """
    errors: list[str] = []
    tolerance = 0.05

    # Check cuota_iva == base * tipo_iva_pct / 100
    expected_iva = f.base_imponible_total * f.tipo_iva_pct / 100.0
    if abs(f.cuota_iva - expected_iva) > tolerance:
        errors.append(
            f"Cuota IVA incorrecta: esperado {expected_iva:.2f}, "
            f"encontrado {f.cuota_iva:.2f}"
        )

    # Check total == base + iva + re - irpf
    expected_total = f.base_imponible_total + f.cuota_iva
    if f.cuota_re is not None:
        expected_total += f.cuota_re
    if f.retencion_irpf is not None:
        expected_total -= f.retencion_irpf

    if abs(f.total - expected_total) > tolerance:
        errors.append(
            f"Total incorrecto: esperado {expected_total:.2f}, "
            f"encontrado {f.total:.2f}"
        )

    return errors


def validate_amount_magnitude(f: FacturaExtraida) -> list[str]:
    """Detect if thousand separators were lost (e.g., 4.000 read as 400)."""
    warnings: list[str] = []
    # Check if line items vs totals are inconsistent
    if f.lineas and f.base_imponible_total and f.base_imponible_total > 0:
        sum_lineas = sum(l.base_imponible for l in f.lineas if l.base_imponible)
        if sum_lineas > 0:
            ratio = f.base_imponible_total / sum_lineas
            if ratio < 0.11 or ratio > 9:  # Roughly 10x off
                warnings.append(
                    f"Base imponible ({f.base_imponible_total}) difiere >10x "
                    f"de la suma de líneas ({sum_lineas:.2f}). "
                    f"Posible error en separadores de miles."
                )
    # If total < 10 EUR but has IVA, suspicious for a business invoice
    if f.total and f.total < 10 and f.cuota_iva and f.cuota_iva > 0:
        warnings.append(
            f"Total sospechosamente bajo ({f.total} EUR) para una factura "
            f"con IVA. Verificar separadores de miles."
        )
    return warnings


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------

EXTRACTION_PROMPT = (
    "Extrae todos los datos de esta factura española. "
    "Devuelve JSON estricto según el schema proporcionado. "
    "IMPORTANTE: Todos los importes deben ser números decimales puros "
    "(ej: 4000.50, NO 4.000,50). NO uses separadores de miles. "
    "Usa punto (.) como separador decimal. "
    "Si un campo no aparece, usa null. "
    "Fechas YYYY-MM-DD. Importes en EUR con máximo 2 decimales."
)


class InvoiceOCRService:
    """Extract structured data from Spanish invoices using Gemini Vision."""

    def __init__(self, api_key: str, model: str = "gemini-3-flash-preview"):
        if not GENAI_AVAILABLE:
            raise RuntimeError(
                "google-genai no esta instalado. "
                "Ejecuta: pip install google-genai"
            )
        self.model = model
        self.client = genai.Client(api_key=api_key)

    async def extract_from_bytes(
        self,
        file_bytes: bytes,
        mime_type: str,
    ) -> ExtractionResult:
        """Extract invoice data from PDF or image bytes.

        Args:
            file_bytes: Raw file content (PDF, JPEG, PNG, etc.).
            mime_type: MIME type of the file (e.g. "application/pdf").

        Returns:
            ExtractionResult with parsed invoice, confidence, and validation.

        Raises:
            RuntimeError: If the Gemini API call fails.
        """
        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=[
                    types.Part.from_bytes(data=file_bytes, mime_type=mime_type),
                    EXTRACTION_PROMPT,
                ],
                config={
                    "response_mime_type": "application/json",
                    "response_json_schema": FacturaExtraida.model_json_schema(),
                },
            )
            factura = FacturaExtraida.model_validate_json(response.text)
        except Exception as exc:
            raise RuntimeError(f"Gemini extraction failed: {exc}") from exc

        # Validate NIFs
        nif_emisor_ok = validate_nif(factura.emisor.nif_cif)
        nif_receptor_ok = validate_nif(factura.receptor.nif_cif)

        # Validate IVA math
        math_errors = validate_iva_math(factura)

        # Validate amount magnitude (thousand separator misreads)
        magnitude_warnings = validate_amount_magnitude(factura)

        all_errors = math_errors + magnitude_warnings

        # Determine confidence
        confianza = self._compute_confidence(
            nif_emisor_ok, nif_receptor_ok, all_errors
        )

        # Force "baja" if magnitude warnings exist
        if magnitude_warnings and confianza != "baja":
            confianza = "baja"

        return ExtractionResult(
            factura=factura,
            confianza=confianza,
            errores_validacion=all_errors,
            nif_emisor_valido=nif_emisor_ok,
            nif_receptor_valido=nif_receptor_ok,
        )

    @staticmethod
    def _compute_confidence(
        nif_emisor_ok: bool,
        nif_receptor_ok: bool,
        math_errors: list[str],
    ) -> Literal["alta", "media", "baja"]:
        """Heuristic confidence level based on validation results."""
        issues = 0
        if not nif_emisor_ok:
            issues += 1
        if not nif_receptor_ok:
            issues += 1
        issues += len(math_errors)

        if issues == 0:
            return "alta"
        elif issues <= 1:
            return "media"
        else:
            return "baja"
