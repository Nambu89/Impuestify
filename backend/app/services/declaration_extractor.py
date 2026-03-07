"""
Declaration Extractor -- Extracts structured data from Modelo 303/130/420 PDFs.

Parses the text extracted from AEAT tax declaration PDFs (via PyMuPDF4LLM) and
maps values to the corresponding casillas for automatic population of
quarterly_declarations.

Supported models:
  - Modelo 303 (IVA quarterly)
  - Modelo 130 (IRPF quarterly prepayment)
  - Modelo 420 (IGIC Canarias quarterly)

The PDFs have a fixed-form layout. AEAT renders casilla labels + values in a
predictable pattern. We exploit both:
  - Casilla number patterns: [01] 12.345,67 or Casilla 01: 12.345,67
  - Label-based patterns: "Base imponible" followed by an amount

Usage:
    extractor = DeclarationExtractor()
    result = extractor.extract(text, modelo="303")
    # result = {"modelo": "303", "casillas": {...}, "metadata": {...}, ...}
"""
import re
import logging
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Spanish number parsing
# ---------------------------------------------------------------------------

def _parse_spanish_number(s: str) -> Optional[float]:
    """
    Parse a Spanish-formatted number: 1.234,56 -> 1234.56
    Also handles: 1234,56 | 1234.56 | 1,234.56 (English) | plain integers.
    """
    if not s:
        return None
    s = s.strip().replace(" ", "").replace("\xa0", "")

    # Negative
    negative = False
    if s.startswith("-"):
        negative = True
        s = s[1:]

    # Spanish format: 1.234,56
    if "," in s and "." in s:
        if s.rindex(",") > s.rindex("."):
            # Spanish: dots=thousands, comma=decimal
            s = s.replace(".", "").replace(",", ".")
        else:
            # English: commas=thousands, dot=decimal
            s = s.replace(",", "")
    elif "," in s:
        # Could be decimal comma (1234,56) or thousands (1,234)
        parts = s.split(",")
        if len(parts) == 2 and len(parts[1]) <= 2:
            s = s.replace(",", ".")
        else:
            s = s.replace(",", "")
    # else: already in a parseable format

    try:
        val = float(s)
        return -val if negative else val
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# Model detection
# ---------------------------------------------------------------------------

_MODEL_PATTERNS = [
    (re.compile(r"modelo\s*303", re.IGNORECASE), "303"),
    (re.compile(r"modelo\s*130", re.IGNORECASE), "130"),
    (re.compile(r"modelo\s*420", re.IGNORECASE), "420"),
    (re.compile(r"modelo\s*300", re.IGNORECASE), "303"),  # Pais Vasco 300 = 303
    (re.compile(r"IGIC", re.IGNORECASE), "420"),
    (re.compile(r"pago\s*fraccionado", re.IGNORECASE), "130"),
    (re.compile(r"autoliquidaci[oó]n.*IVA", re.IGNORECASE), "303"),
]


def detect_modelo(text: str) -> Optional[str]:
    """Detect which modelo a PDF corresponds to from its text."""
    for pattern, modelo in _MODEL_PATTERNS:
        if pattern.search(text):
            return modelo
    return None


# ---------------------------------------------------------------------------
# Metadata extraction
# ---------------------------------------------------------------------------

_RE_NIF = re.compile(r"(?:NIF|N\.I\.F\.)[\s:]*([A-Z0-9]\d{7}[A-Z0-9])", re.IGNORECASE)
_RE_EJERCICIO = re.compile(r"(?:ejercicio|a[ñn]o)[\s:]*(\d{4})", re.IGNORECASE)
_RE_PERIODO = re.compile(
    r"(?:per[ií]odo|trimestre)[\s:]*([1-4])\s*[TtºQq]", re.IGNORECASE
)
_RE_PERIODO_ALT = re.compile(r"\b([1-4])\s*[Tt](?:rimestre)?", re.IGNORECASE)
_RE_COMPLEMENTARIA = re.compile(r"complementaria", re.IGNORECASE)
_RE_NOMBRE = re.compile(
    r"(?:apellidos\s*y\s*nombre|raz[oó]n\s*social|contribuyente)[\s:]*([^\n]{3,60})",
    re.IGNORECASE,
)


def _extract_metadata(text: str) -> Dict[str, Any]:
    """Extract NIF, year, quarter, and name from declaration text."""
    meta: Dict[str, Any] = {}

    m = _RE_NIF.search(text)
    if m:
        meta["nif"] = m.group(1).upper()

    m = _RE_EJERCICIO.search(text)
    if m:
        meta["year"] = int(m.group(1))

    # Try specific "Periodo: 2T" first, then "3 Trimestre" format
    m = _RE_PERIODO.search(text)
    if m:
        meta["quarter"] = int(m.group(1))
    else:
        m = _RE_PERIODO_ALT.search(text)
        if m:
            meta["quarter"] = int(m.group(1))

    meta["complementaria"] = bool(_RE_COMPLEMENTARIA.search(text))

    m = _RE_NOMBRE.search(text)
    if m:
        meta["nombre"] = m.group(1).strip()

    return meta


# ---------------------------------------------------------------------------
# Casilla extraction (generic)
# ---------------------------------------------------------------------------

# Pattern: [01] or Casilla 01 or casilla nº 01, followed by amount
_RE_CASILLA_BRACKET = re.compile(
    r"\[(\d{1,3})\]\s*[-:]?\s*(-?\d[\d.,]*)",
)
_RE_CASILLA_LABEL = re.compile(
    r"casilla\s*(?:n[ºo°]?\s*)?(\d{1,3})\s*[-:]?\s*(-?\d[\d.,]*)",
    re.IGNORECASE,
)
# Pattern: number at end of a line with a casilla-like label before it
_RE_CASILLA_LINE = re.compile(
    r"(\d{1,3})\s+(-?\d{1,3}(?:\.\d{3})*(?:,\d{2})?)\s*€?\s*$",
    re.MULTILINE,
)


def _extract_casillas_generic(text: str) -> Dict[str, float]:
    """
    Extract casilla→value pairs from text using multiple pattern strategies.
    Returns dict like {"01": 12345.67, "03": 500.0, ...}
    """
    casillas: Dict[str, float] = {}

    # Strategy 1: [01] 1.234,56
    for m in _RE_CASILLA_BRACKET.finditer(text):
        num = m.group(1).lstrip("0") or "0"
        val = _parse_spanish_number(m.group(2))
        if val is not None:
            casillas[num] = val

    # Strategy 2: Casilla 01: 1.234,56
    for m in _RE_CASILLA_LABEL.finditer(text):
        num = m.group(1).lstrip("0") or "0"
        val = _parse_spanish_number(m.group(2))
        if val is not None:
            casillas[num] = val

    return casillas


# ---------------------------------------------------------------------------
# Label-based extraction (contextual)
# ---------------------------------------------------------------------------

def _find_amount_after(text: str, pattern: re.Pattern) -> Optional[float]:
    """Find the first number after a regex pattern match."""
    m = pattern.search(text)
    if not m:
        return None
    # Look for a number within 100 chars after the match
    rest = text[m.end():m.end() + 100]
    num_match = re.search(r"(-?\d{1,3}(?:\.\d{3})*(?:,\d{2})?)\s*€?", rest)
    if num_match:
        return _parse_spanish_number(num_match.group(1))
    return None


# ---------------------------------------------------------------------------
# Modelo 303 specific extraction
# ---------------------------------------------------------------------------

_303_LABEL_PATTERNS = {
    "base_4": re.compile(r"base\s*imponible.*?4\s*%", re.IGNORECASE),
    "cuota_4": re.compile(r"cuota.*?4\s*%", re.IGNORECASE),
    "base_10": re.compile(r"base\s*imponible.*?10\s*%", re.IGNORECASE),
    "cuota_10": re.compile(r"cuota.*?10\s*%", re.IGNORECASE),
    "base_21": re.compile(r"base\s*imponible.*?21\s*%", re.IGNORECASE),
    "cuota_21": re.compile(r"cuota.*?21\s*%", re.IGNORECASE),
    "total_devengado": re.compile(r"total\s*(?:IVA\s*)?devengado", re.IGNORECASE),
    "total_deducible": re.compile(r"total\s*a\s*deducir", re.IGNORECASE),
    "resultado_regimen_general": re.compile(r"resultado\s*r[eé]gimen\s*general", re.IGNORECASE),
    "resultado_liquidacion": re.compile(r"resultado\s*(?:de\s*la\s*)?liquidaci[oó]n", re.IGNORECASE),
    "atribucion_estado": re.compile(r"atribuible\s*(?:al\s*)?estado", re.IGNORECASE),
    "cuotas_compensar": re.compile(r"cuotas\s*a\s*compensar", re.IGNORECASE),
}


def _extract_303(text: str, casillas: Dict[str, float]) -> Dict[str, Any]:
    """Extract Modelo 303 specific fields."""
    result: Dict[str, Any] = {"modelo": "303"}

    # Map casillas to field names
    casilla_map = {
        "1": "base_4", "3": "cuota_4",
        "4": "base_10", "6": "cuota_10",
        "7": "base_21", "9": "cuota_21",
        "10": "base_intracomunitarias", "12": "cuota_intracomunitarias",
        "13": "base_inversion_sp", "14": "cuota_inversion_sp",
        "27": "total_devengado",
        "45": "total_deducible",
        "46": "resultado_regimen_general",
        "65": "pct_atribucion_estado",
        "66": "atribucion_estado",
        "78": "cuotas_compensar_anteriores",
        "68": "regularizacion_anual",
        "71": "resultado_liquidacion",
        "70": "resultado_anterior_complementaria",
    }

    fields: Dict[str, float] = {}
    for cas_num, field_name in casilla_map.items():
        if cas_num in casillas:
            fields[field_name] = casillas[cas_num]

    # Fallback: label-based extraction for missing fields
    for field_name, pattern in _303_LABEL_PATTERNS.items():
        if field_name not in fields:
            val = _find_amount_after(text, pattern)
            if val is not None:
                fields[field_name] = val

    result["fields"] = fields
    result["casillas_raw"] = casillas
    return result


# ---------------------------------------------------------------------------
# Modelo 130 specific extraction
# ---------------------------------------------------------------------------

_130_LABEL_PATTERNS = {
    "ingresos_acumulados": re.compile(
        r"(?:ingresos\s*computables|rendimientos\s*[ií]ntegros)", re.IGNORECASE
    ),
    "gastos_acumulados": re.compile(r"gastos\s*(?:fiscalmente\s*)?deducibles", re.IGNORECASE),
    "rendimiento_neto": re.compile(r"rendimiento\s*neto", re.IGNORECASE),
    "retenciones_acumuladas": re.compile(r"retenciones?\s*(?:e\s*ingresos\s*a\s*cuenta)?", re.IGNORECASE),
    "pagos_anteriores": re.compile(r"pagos\s*fraccionados\s*anteriores", re.IGNORECASE),
    "resultado": re.compile(r"resultado\s*(?:de\s*la\s*)?(?:autoliquidaci[oó]n|liquidaci[oó]n)", re.IGNORECASE),
    "deduccion_art80bis": re.compile(r"art[ií]culo\s*80\s*bis|deducci[oó]n.*80\s*bis", re.IGNORECASE),
    "deduccion_vivienda": re.compile(r"deducci[oó]n.*vivienda\s*habitual", re.IGNORECASE),
}


def _extract_130(text: str, casillas: Dict[str, float]) -> Dict[str, Any]:
    """Extract Modelo 130 specific fields."""
    result: Dict[str, Any] = {"modelo": "130"}

    casilla_map = {
        "1": "ingresos_acumulados",
        "2": "gastos_acumulados",
        "3": "rendimiento_neto",
        "4": "cuota_20pct",
        "5": "retenciones_acumuladas",
        "6": "pagos_anteriores",
        "7": "resultado_seccion_i",
        "12": "total_liquidacion",
        "13": "deduccion_art80bis",
        "16": "deduccion_vivienda",
        "19": "resultado_final",
    }

    fields: Dict[str, float] = {}
    for cas_num, field_name in casilla_map.items():
        if cas_num in casillas:
            fields[field_name] = casillas[cas_num]

    # Fallback: label-based
    for field_name, pattern in _130_LABEL_PATTERNS.items():
        if field_name not in fields:
            val = _find_amount_after(text, pattern)
            if val is not None:
                fields[field_name] = val

    # Detect territory from text
    territory = "Comun"
    if re.search(r"ceuta|melilla", text, re.IGNORECASE):
        territory = "Ceuta/Melilla"
    elif re.search(r"araba|[aá]lava", text, re.IGNORECASE):
        territory = "Araba"
    elif re.search(r"gipuzkoa|guip[uú]zcoa", text, re.IGNORECASE):
        territory = "Gipuzkoa"
    elif re.search(r"bizkaia|vizcaya", text, re.IGNORECASE):
        territory = "Bizkaia"
    elif re.search(r"navarra", text, re.IGNORECASE):
        territory = "Navarra"

    result["fields"] = fields
    result["territory"] = territory
    result["casillas_raw"] = casillas
    return result


# ---------------------------------------------------------------------------
# Modelo 420 specific extraction
# ---------------------------------------------------------------------------

_420_LABEL_PATTERNS = {
    "base_0": re.compile(r"tipo\s*cero|0\s*%.*base", re.IGNORECASE),
    "base_3": re.compile(r"tipo\s*reducido|3\s*%.*base", re.IGNORECASE),
    "base_7": re.compile(r"tipo\s*general|7\s*%.*base", re.IGNORECASE),
    "total_devengado": re.compile(r"total\s*(?:IGIC\s*)?devengado", re.IGNORECASE),
    "total_deducible": re.compile(r"total\s*a\s*deducir", re.IGNORECASE),
    "resultado_liquidacion": re.compile(r"resultado\s*(?:de\s*la\s*)?liquidaci[oó]n", re.IGNORECASE),
}


def _extract_420(text: str, casillas: Dict[str, float]) -> Dict[str, Any]:
    """Extract Modelo 420 specific fields."""
    result: Dict[str, Any] = {"modelo": "420"}

    fields: Dict[str, float] = {}

    # Label-based (420 doesn't use standard casilla numbers like 303)
    for field_name, pattern in _420_LABEL_PATTERNS.items():
        val = _find_amount_after(text, pattern)
        if val is not None:
            fields[field_name] = val

    # Also try casilla-based
    for cas_num, val in casillas.items():
        fields[f"casilla_{cas_num}"] = val

    result["fields"] = fields
    result["casillas_raw"] = casillas
    return result


# ---------------------------------------------------------------------------
# Main extractor class
# ---------------------------------------------------------------------------

@dataclass
class ExtractionResult:
    """Result of extracting data from a declaration PDF."""
    success: bool
    modelo: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    fields: Dict[str, float] = field(default_factory=dict)
    casillas_raw: Dict[str, float] = field(default_factory=dict)
    territory: str = "Comun"
    confidence: float = 0.0
    error: Optional[str] = None

    def to_form_data(self) -> Dict[str, Any]:
        """Convert extracted fields to form_data format for DeclarationService.save()."""
        data: Dict[str, Any] = {}
        data.update(self.fields)
        data.update(self.metadata)
        data["territory"] = self.territory
        data["extraction_confidence"] = self.confidence
        return data


class DeclarationExtractor:
    """
    Extracts structured data from Spanish tax declaration PDFs.

    Supports Modelos 303, 130, and 420. Auto-detects the model from the text,
    then applies model-specific casilla mapping and label-based extraction.
    """

    def extract(self, text: str, modelo: Optional[str] = None) -> ExtractionResult:
        """
        Extract declaration data from PDF text.

        Args:
            text: Full text extracted from the PDF (via PyMuPDF4LLM).
            modelo: Optional model hint ("303", "130", "420"). If None, auto-detect.

        Returns:
            ExtractionResult with extracted fields, metadata, and confidence score.
        """
        if not text or len(text.strip()) < 50:
            return ExtractionResult(
                success=False,
                error="Text too short or empty for declaration extraction",
            )

        # 1. Detect or confirm modelo
        detected = detect_modelo(text)
        modelo = modelo or detected

        if not modelo:
            return ExtractionResult(
                success=False,
                error="Could not detect declaration model (303/130/420) from text",
            )

        # 2. Extract metadata
        metadata = _extract_metadata(text)

        # 3. Extract casillas (generic)
        casillas = _extract_casillas_generic(text)

        # 4. Model-specific extraction
        if modelo == "303":
            specific = _extract_303(text, casillas)
        elif modelo == "130":
            specific = _extract_130(text, casillas)
        elif modelo == "420":
            specific = _extract_420(text, casillas)
        else:
            return ExtractionResult(
                success=False,
                error=f"Unsupported modelo: {modelo}",
            )

        # 5. Calculate confidence
        fields = specific.get("fields", {})
        confidence = self._calculate_confidence(modelo, fields, casillas)

        territory = specific.get("territory", "Comun")

        logger.info(
            "Extracted %s: %d fields, %d raw casillas, confidence=%.2f",
            modelo, len(fields), len(casillas), confidence,
        )

        return ExtractionResult(
            success=True,
            modelo=modelo,
            metadata=metadata,
            fields=fields,
            casillas_raw=casillas,
            territory=territory,
            confidence=confidence,
        )

    def _calculate_confidence(
        self, modelo: str, fields: Dict[str, float], casillas: Dict[str, float]
    ) -> float:
        """
        Calculate extraction confidence (0.0 - 1.0).

        Based on how many key fields were found for each model.
        """
        if modelo == "303":
            key_fields = [
                "base_21", "cuota_21", "total_devengado",
                "total_deducible", "resultado_liquidacion",
            ]
        elif modelo == "130":
            key_fields = [
                "ingresos_acumulados", "gastos_acumulados",
                "rendimiento_neto", "resultado_final",
            ]
        elif modelo == "420":
            key_fields = [
                "base_7", "total_devengado",
                "total_deducible", "resultado_liquidacion",
            ]
        else:
            return 0.0

        found = sum(1 for f in key_fields if f in fields)
        base_confidence = found / len(key_fields) if key_fields else 0

        # Bonus for having raw casillas
        casilla_bonus = min(len(casillas) / 10, 0.2)

        return min(1.0, round(base_confidence + casilla_bonus, 2))
