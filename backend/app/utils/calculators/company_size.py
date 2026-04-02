"""
Company Size Calculator for Impuestify.

Determines company classification (micro/small/medium/large) based on
Spanish Commercial Law (LSC Art. 257-258) + EU Directive 2023/2775.

Inputs: activo_total, cifra_negocios, num_empleados for 2 consecutive years
Outputs: classification, PGC applicable, abbreviated accounts eligibility, audit obligation

The "2 of 3" rule: a company fits a category if it does NOT exceed at least
2 of the 3 thresholds during 2 consecutive fiscal years.
"""
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional


# ---------------------------------------------------------------------------
# Thresholds
# ---------------------------------------------------------------------------

# Thresholds for 2025 (current law before EU Directive transposition)
THRESHOLDS_2025 = {
    "micro": {"activo": 350_000, "negocios": 700_000, "empleados": 10},
    "pequena": {"activo": 4_000_000, "negocios": 8_000_000, "empleados": 50},
    "mediana": {"activo": 20_000_000, "negocios": 40_000_000, "empleados": 250},
}

# Thresholds for 2026+ (Directiva UE 2023/2775 — pending transposition)
THRESHOLDS_2026 = {
    "micro": {"activo": 450_000, "negocios": 900_000, "empleados": 10},
    "pequena": {"activo": 5_000_000, "negocios": 10_000_000, "empleados": 50},
    "mediana": {"activo": 25_000_000, "negocios": 50_000_000, "empleados": 250},
}

# Audit thresholds (Art. 263 LSC) — company must be audited if exceeds 2 of 3
AUDIT_THRESHOLDS_2025 = {"activo": 2_850_000, "negocios": 5_700_000, "empleados": 50}
AUDIT_THRESHOLDS_2026 = {"activo": 3_560_000, "negocios": 7_120_000, "empleados": 50}

# Balance abreviado (Art. 257 LSC) — eligible if does NOT exceed 2 of 3
BALANCE_ABREVIADO_2025 = {"activo": 4_000_000, "negocios": 8_000_000, "empleados": 50}
BALANCE_ABREVIADO_2026 = {"activo": 7_500_000, "negocios": 15_000_000, "empleados": 50}

# PyG abreviada (Art. 258 LSC) — eligible if does NOT exceed 2 of 3
PYG_ABREVIADA_2025 = {"activo": 11_400_000, "negocios": 22_800_000, "empleados": 250}
PYG_ABREVIADA_2026 = {"activo": 14_250_000, "negocios": 28_500_000, "empleados": 250}


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class YearData:
    """Financial data for one fiscal year."""
    activo: float
    negocios: float
    empleados: int


@dataclass
class ThresholdDetail:
    """Comparison of a value against a threshold limit."""
    valor: float
    limite: float
    supera: bool
    porcentaje: float  # percentage of limit used (0-100+)


@dataclass
class CompanySizeResult:
    """Complete result of the company size classification."""
    clasificacion: str  # "micro", "pequena", "mediana", "grande"
    clasificacion_label: str  # "Microempresa", "Pequena empresa", etc.
    pgc_aplicable: str
    pgc_detalle: str
    balance_abreviado: bool
    memoria_abreviada: bool
    pyg_abreviada: bool
    auditoria_obligatoria: bool
    notas: List[str] = field(default_factory=list)
    umbrales_clasificacion: Dict[str, Any] = field(default_factory=dict)
    umbrales_auditoria: Dict[str, Any] = field(default_factory=dict)
    umbrales_balance: Dict[str, Any] = field(default_factory=dict)
    umbrales_pyg: Dict[str, Any] = field(default_factory=dict)
    ejercicio_referencia: str = "2025"
    disclaimer: str = (
        "Informacion orientativa basada en LSC Art. 257-258 y "
        "Directiva UE 2023/2775. Consulte con un asesor profesional."
    )


# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------

def _count_exceeded(data: YearData, thresholds: Dict[str, float]) -> int:
    """Count how many of the 3 thresholds are exceeded by a year's data."""
    count = 0
    if data.activo > thresholds["activo"]:
        count += 1
    if data.negocios > thresholds["negocios"]:
        count += 1
    if data.empleados > thresholds["empleados"]:
        count += 1
    return count


def _fits_category(
    year_1: YearData,
    year_2: YearData,
    thresholds: Dict[str, float],
) -> bool:
    """
    A company fits a category if it does NOT exceed 2 of 3 thresholds
    during BOTH of the 2 consecutive fiscal years.

    LSC rule: the company loses the category when it exceeds 2 of 3
    limits during 2 consecutive years. Conversely, it qualifies if
    at least one year stays within limits (exceeds fewer than 2).
    """
    exceeds_y1 = _count_exceeded(year_1, thresholds) >= 2
    exceeds_y2 = _count_exceeded(year_2, thresholds) >= 2
    # Must exceed in BOTH years to lose the category
    # So it fits if it does NOT exceed in both
    return not (exceeds_y1 and exceeds_y2)


def _make_threshold_detail(
    year_1: YearData,
    year_2: YearData,
    thresholds: Dict[str, float],
) -> Dict[str, Any]:
    """Build threshold comparison details using the average of 2 years."""
    avg_activo = (year_1.activo + year_2.activo) / 2
    avg_negocios = (year_1.negocios + year_2.negocios) / 2
    avg_empleados = (year_1.empleados + year_2.empleados) / 2

    def detail(valor: float, limite: float) -> Dict[str, Any]:
        return {
            "valor": round(valor, 2),
            "limite": limite,
            "supera": valor > limite,
            "porcentaje": round((valor / limite) * 100, 1) if limite > 0 else 0,
        }

    return {
        "activo": detail(avg_activo, thresholds["activo"]),
        "negocios": detail(avg_negocios, thresholds["negocios"]),
        "empleados": detail(avg_empleados, thresholds["empleados"]),
    }


def _exceeds_both_years(
    year_1: YearData,
    year_2: YearData,
    thresholds: Dict[str, float],
) -> bool:
    """True if the company exceeds 2 of 3 thresholds in BOTH years."""
    return (
        _count_exceeded(year_1, thresholds) >= 2
        and _count_exceeded(year_2, thresholds) >= 2
    )


def classify_company(
    year_1: YearData,
    year_2: YearData,
    ejercicio: int = 2025,
) -> CompanySizeResult:
    """
    Classify a company based on 2 consecutive fiscal years.

    Args:
        year_1: Data for the earlier fiscal year (N-1).
        year_2: Data for the later fiscal year (N).
        ejercicio: Reference fiscal year to select thresholds (2025 or 2026+).

    Returns:
        CompanySizeResult with full classification details.
    """
    # Select thresholds by year
    if ejercicio >= 2026:
        thresholds = THRESHOLDS_2026
        audit_th = AUDIT_THRESHOLDS_2026
        balance_th = BALANCE_ABREVIADO_2026
        pyg_th = PYG_ABREVIADA_2026
        ref = "2026"
    else:
        thresholds = THRESHOLDS_2025
        audit_th = AUDIT_THRESHOLDS_2025
        balance_th = BALANCE_ABREVIADO_2025
        pyg_th = PYG_ABREVIADA_2025
        ref = "2025"

    # Classify: try from smallest to largest
    if _fits_category(year_1, year_2, thresholds["micro"]):
        clasificacion = "micro"
        label = "Microempresa"
    elif _fits_category(year_1, year_2, thresholds["pequena"]):
        clasificacion = "pequena"
        label = "Pequena empresa"
    elif _fits_category(year_1, year_2, thresholds["mediana"]):
        clasificacion = "mediana"
        label = "Mediana empresa"
    else:
        clasificacion = "grande"
        label = "Gran empresa"

    # PGC applicable
    if clasificacion in ("micro", "pequena"):
        pgc = "PGC PYMES (RD 1515/2007)"
        pgc_detalle = (
            "Puede aplicar el Plan General de Contabilidad de PYMES. "
            "Tambien puede optar por el PGC Normal si lo prefiere."
        )
    else:
        pgc = "PGC Normal (RD 1514/2007)"
        pgc_detalle = (
            "Debe aplicar el Plan General de Contabilidad Normal."
        )

    # Balance abreviado (Art. 257)
    balance_abreviado = _fits_category(year_1, year_2, balance_th)

    # Memoria abreviada follows balance abreviado
    memoria_abreviada = balance_abreviado

    # PyG abreviada (Art. 258)
    pyg_abreviada = _fits_category(year_1, year_2, pyg_th)

    # Audit obligation (Art. 263) — obligatory if exceeds 2 of 3 in both years
    auditoria = _exceeds_both_years(year_1, year_2, audit_th)

    # Build notes
    notas: List[str] = []
    if clasificacion == "micro":
        notas.append(
            "Como microempresa, puede aplicar los criterios simplificados del PGC PYMES."
        )
    if clasificacion in ("micro", "pequena"):
        notas.append(
            "Puede formular balance, memoria y estado de cambios en patrimonio neto abreviados."
        )
        notas.append(
            "No esta obligada a depositar el informe de gestion en el Registro Mercantil."
        )
    if clasificacion == "mediana":
        notas.append(
            "Debe aplicar el PGC Normal pero puede formular balance abreviado si cumple los umbrales del Art. 257."
        )
    if clasificacion == "grande":
        notas.append(
            "Debe aplicar el PGC Normal con cuentas anuales completas."
        )
        notas.append(
            "Esta obligada a elaborar el informe de gestion y el estado de flujos de efectivo."
        )
    if auditoria:
        notas.append(
            "Esta obligada a someter sus cuentas anuales a auditoria (Art. 263 LSC)."
        )
    else:
        notas.append(
            "No esta obligada a auditar sus cuentas anuales."
        )

    if ejercicio >= 2026:
        notas.append(
            "Umbrales 2026: se aplican los limites actualizados por la Directiva UE 2023/2775 "
            "(pendiente de transposicion al derecho espanol)."
        )

    # Build threshold details for the classification level
    cls_thresholds = thresholds.get(clasificacion, thresholds.get("mediana", {}))

    return CompanySizeResult(
        clasificacion=clasificacion,
        clasificacion_label=label,
        pgc_aplicable=pgc,
        pgc_detalle=pgc_detalle,
        balance_abreviado=balance_abreviado,
        memoria_abreviada=memoria_abreviada,
        pyg_abreviada=pyg_abreviada,
        auditoria_obligatoria=auditoria,
        notas=notas,
        umbrales_clasificacion=_make_threshold_detail(year_1, year_2, cls_thresholds),
        umbrales_auditoria=_make_threshold_detail(year_1, year_2, audit_th),
        umbrales_balance=_make_threshold_detail(year_1, year_2, balance_th),
        umbrales_pyg=_make_threshold_detail(year_1, year_2, pyg_th),
        ejercicio_referencia=ref,
    )
