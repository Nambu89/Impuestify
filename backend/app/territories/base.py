"""Abstract base class for territory plugins."""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ScaleData:
    """IRPF scale brackets for a jurisdiction."""
    jurisdiction: str
    year: int
    scale_type: str  # 'general', 'autonomica', 'foral'
    brackets: List[Dict[str, float]]  # [{base_hasta, cuota_integra, resto_base, tipo_aplicable}]


@dataclass
class SimulationResult:
    """Result of a full IRPF simulation."""
    base_imponible_general: float = 0.0
    base_imponible_ahorro: float = 0.0
    cuota_integra: float = 0.0
    cuota_liquida: float = 0.0
    resultado: float = 0.0  # positive = a pagar, negative = a devolver
    tipo_resultado: str = "a_pagar"
    desglose: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MinimosConfig:
    """Personal and family minimum configuration."""
    contribuyente: float = 0.0
    descendientes: List[float] = field(default_factory=list)
    ascendiente_65: float = 0.0
    ascendiente_75: float = 0.0
    apply_as: str = "base_reduction"  # 'base_reduction' (comun) or 'quota_deduction' (foral)


@dataclass
class Deadline:
    """Fiscal deadline."""
    modelo: str
    description: str
    date: str  # ISO format YYYY-MM-DD
    period: str  # 'Q1', 'Q2', 'Q3', 'Q4', 'annual'


@dataclass
class ModelObligation:
    """A fiscal model that a taxpayer must (or may) file."""
    modelo: str            # "303", "130", "100", "420", etc.
    nombre: str            # "IVA trimestral"
    descripcion: str       # "Declaracion trimestral del IVA"
    periodicidad: str      # "trimestral", "anual", "mensual"
    aplica_si: str         # "autonomo", "sociedad", "todos", "retenedor"
    obligatorio: bool      # True if mandatory, False if conditional/optional
    deadlines: List[Deadline] = field(default_factory=list)
    notas: Optional[str] = None
    organismo: str = "AEAT"  # "AEAT", "ATC", "DFG", "DFB", "DFA", "HTN", "Ciudad Autonoma"


# ── 2026 Deadlines (hardcoded) ──────────────────────────────────
DEADLINES_2026 = {
    "trimestral": [
        Deadline(modelo="", description="1T (enero-marzo)", date="2026-04-20", period="Q1"),
        Deadline(modelo="", description="2T (abril-junio)", date="2026-07-20", period="Q2"),
        Deadline(modelo="", description="3T (julio-septiembre)", date="2026-10-20", period="Q3"),
        Deadline(modelo="", description="4T (octubre-diciembre)", date="2027-01-30", period="Q4"),
    ],
    "renta_100": [
        Deadline(modelo="100", description="Declaracion de la Renta 2025", date="2026-06-30", period="annual"),
    ],
    "is_200": [
        Deadline(modelo="200", description="Impuesto sobre Sociedades 2025", date="2026-07-25", period="annual"),
    ],
    "resumen_390": [
        Deadline(modelo="390", description="Resumen anual IVA", date="2026-01-30", period="annual"),
    ],
    "resumen_190": [
        Deadline(modelo="190", description="Resumen anual retenciones", date="2026-01-30", period="annual"),
    ],
    "resumen_180": [
        Deadline(modelo="180", description="Resumen anual retenciones alquiler", date="2026-01-30", period="annual"),
    ],
    "resumen_193": [
        Deadline(modelo="193", description="Resumen anual retenciones capital mobiliario", date="2026-01-30", period="annual"),
    ],
    "modelo_347": [
        Deadline(modelo="347", description="Operaciones con terceros >3.005,06 EUR", date="2026-02-28", period="annual"),
    ],
    "modelo_720": [
        Deadline(modelo="720", description="Declaracion bienes en el extranjero", date="2026-03-31", period="annual"),
    ],
}


def _trimestral_deadlines(modelo: str) -> List[Deadline]:
    """Return 4 quarterly deadlines for a modelo in 2026."""
    return [
        Deadline(modelo=modelo, description=d.description, date=d.date, period=d.period)
        for d in DEADLINES_2026["trimestral"]
    ]


class TerritoryPlugin(ABC):
    """
    Abstract base for territory-specific fiscal logic.

    Each plugin encapsulates IRPF scales, deductions, indirect taxes,
    and RAG filtering for a fiscal regime.
    """
    territories: List[str] = []
    regime: str = ""

    @abstractmethod
    async def get_irpf_scales(self, year: int) -> List[ScaleData]:
        """Return IRPF scale brackets for this territory."""
        ...

    @abstractmethod
    async def simulate_irpf(self, profile: Dict[str, Any], db) -> SimulationResult:
        """Run full IRPF simulation using territory-specific rules."""
        ...

    @abstractmethod
    async def get_deductions(self, ccaa: str, year: int, db) -> List[Dict[str, Any]]:
        """Return applicable deductions for a CCAA within this regime."""
        ...

    @abstractmethod
    def get_indirect_tax_model(self, ccaa: str = None) -> str:
        """Return the indirect tax modelo: '303' (IVA), '420' (IGIC), 'ipsi', etc.

        Args:
            ccaa: Optional sub-territory for regimes where the model varies
                  (e.g. Gipuzkoa uses '300' vs Bizkaia/Araba '303').
        """
        ...

    def get_renta_model(self, ccaa: str = None) -> str:
        """Return IRPF annual model number. Default: '100'."""
        return "100"

    def get_is_model(self) -> str:
        """Return IS (Impuesto de Sociedades) model number. Default: '200'."""
        return "200"

    def get_retenciones_model(self) -> str:
        """Return retenciones trimestrales model number. Default: '111'."""
        return "111"

    @abstractmethod
    def get_minimos_personales(self) -> MinimosConfig:
        """Return personal/family minimum configuration."""
        ...

    def get_rag_filters(self, ccaa: str) -> Dict[str, Any]:
        """Return RAG search filters for this territory. Override for specifics."""
        return {"territory": ccaa, "regime": self.regime}

    def get_upcoming_deadlines(self) -> List[Deadline]:
        """Return upcoming fiscal deadlines. Override per territory."""
        return []

    def supports(self, ccaa: str) -> bool:
        """Check if this plugin handles the given CCAA."""
        return ccaa in self.territories

    def get_model_obligations(self, profile: Dict[str, Any]) -> List[ModelObligation]:
        """Return list of fiscal model obligations based on taxpayer profile.

        Default implementation covers common regime (AEAT).
        Territory plugins override to substitute their own models.

        Profile keys:
            - situacion_laboral: "particular" | "autonomo" | "sociedad" | "farmaceutico"
            - tiene_empleados: bool
            - tiene_alquileres: bool
            - estimacion: "directa_simplificada" | "directa_normal" | "objetiva"
            - tiene_ops_intracomunitarias: bool
            - tiene_ops_terceros_3005: bool (optional, for modelo 347)
            - paga_dividendos: bool (optional, for sociedad)
        """
        situacion = profile.get("situacion_laboral", "particular")
        tiene_empleados = profile.get("tiene_empleados", False)
        tiene_alquileres = profile.get("tiene_alquileres", False)
        estimacion = profile.get("estimacion", "directa_simplificada")
        ops_intra = profile.get("tiene_ops_intracomunitarias", False)
        ops_terceros = profile.get("tiene_ops_terceros_3005", False)
        paga_dividendos = profile.get("paga_dividendos", False)
        ccaa = profile.get("ccaa")

        obligations: List[ModelObligation] = []

        # ── IVA model (varies by territory) ──
        iva_modelo = self.get_indirect_tax_model(ccaa)
        renta_modelo = self.get_renta_model(ccaa)
        is_modelo = self.get_is_model()
        retenciones_modelo = self.get_retenciones_model()

        # ── Particular: only renta anual ──
        if situacion == "particular":
            obligations.append(ModelObligation(
                modelo=renta_modelo,
                nombre=f"Modelo {renta_modelo} - IRPF",
                descripcion="Declaracion anual del Impuesto sobre la Renta de las Personas Fisicas",
                periodicidad="anual",
                aplica_si="particular",
                obligatorio=True,
                deadlines=DEADLINES_2026.get("renta_100", []),
            ))
            return obligations

        # ── Autonomo ──
        if situacion == "autonomo":
            # IVA trimestral
            obligations.append(ModelObligation(
                modelo=iva_modelo,
                nombre=f"Modelo {iva_modelo} - Impuesto indirecto trimestral",
                descripcion="Autoliquidacion trimestral del impuesto indirecto",
                periodicidad="trimestral",
                aplica_si="autonomo",
                obligatorio=True,
                deadlines=_trimestral_deadlines(iva_modelo),
            ))

            # Pago fraccionado IRPF
            pago_frac = "131" if estimacion == "objetiva" else "130"
            obligations.append(ModelObligation(
                modelo=pago_frac,
                nombre=f"Modelo {pago_frac} - Pago fraccionado IRPF",
                descripcion="Pago fraccionado trimestral a cuenta del IRPF" + (
                    " (estimacion objetiva)" if pago_frac == "131" else " (estimacion directa)"
                ),
                periodicidad="trimestral",
                aplica_si="autonomo",
                obligatorio=True,
                deadlines=_trimestral_deadlines(pago_frac),
            ))

            # Renta anual
            obligations.append(ModelObligation(
                modelo=renta_modelo,
                nombre=f"Modelo {renta_modelo} - IRPF",
                descripcion="Declaracion anual del IRPF",
                periodicidad="anual",
                aplica_si="autonomo",
                obligatorio=True,
                deadlines=DEADLINES_2026.get("renta_100", []),
            ))

            # Retenciones si tiene empleados
            if tiene_empleados:
                obligations.append(ModelObligation(
                    modelo=retenciones_modelo,
                    nombre=f"Modelo {retenciones_modelo} - Retenciones trabajo",
                    descripcion="Retenciones e ingresos a cuenta del trabajo personal",
                    periodicidad="trimestral",
                    aplica_si="retenedor",
                    obligatorio=True,
                    deadlines=_trimestral_deadlines(retenciones_modelo),
                ))
                obligations.append(ModelObligation(
                    modelo="190",
                    nombre="Modelo 190 - Resumen anual retenciones",
                    descripcion="Resumen anual de retenciones e ingresos a cuenta del trabajo",
                    periodicidad="anual",
                    aplica_si="retenedor",
                    obligatorio=True,
                    deadlines=DEADLINES_2026.get("resumen_190", []),
                ))

            # Retenciones alquiler si tiene alquileres
            if tiene_alquileres:
                obligations.append(ModelObligation(
                    modelo="115",
                    nombre="Modelo 115 - Retenciones alquiler",
                    descripcion="Retenciones por alquiler de inmuebles urbanos",
                    periodicidad="trimestral",
                    aplica_si="autonomo",
                    obligatorio=True,
                    deadlines=_trimestral_deadlines("115"),
                ))
                obligations.append(ModelObligation(
                    modelo="180",
                    nombre="Modelo 180 - Resumen anual alquiler",
                    descripcion="Resumen anual de retenciones por alquiler de inmuebles",
                    periodicidad="anual",
                    aplica_si="autonomo",
                    obligatorio=True,
                    deadlines=DEADLINES_2026.get("resumen_180", []),
                ))

            # Operaciones intracomunitarias
            if ops_intra:
                obligations.append(ModelObligation(
                    modelo="349",
                    nombre="Modelo 349 - Operaciones intracomunitarias",
                    descripcion="Declaracion recapitulativa de operaciones intracomunitarias",
                    periodicidad="trimestral",
                    aplica_si="autonomo",
                    obligatorio=True,
                    deadlines=_trimestral_deadlines("349"),
                ))

            # Operaciones con terceros >3.005,06 EUR
            if ops_terceros:
                obligations.append(ModelObligation(
                    modelo="347",
                    nombre="Modelo 347 - Operaciones con terceros",
                    descripcion="Declaracion anual de operaciones con terceros superiores a 3.005,06 EUR",
                    periodicidad="anual",
                    aplica_si="autonomo",
                    obligatorio=True,
                    deadlines=DEADLINES_2026.get("modelo_347", []),
                ))

            return obligations

        # ── Farmaceutico (Recargo de Equivalencia — no 303/390) ──
        if situacion == "farmaceutico":
            # Pago fraccionado IRPF (same as autonomo)
            pago_frac = "131" if estimacion == "objetiva" else "130"
            obligations.append(ModelObligation(
                modelo=pago_frac,
                nombre=f"Modelo {pago_frac} - Pago fraccionado IRPF",
                descripcion="Pago fraccionado trimestral a cuenta del IRPF" + (
                    " (estimacion objetiva)" if pago_frac == "131" else " (estimacion directa)"
                ),
                periodicidad="trimestral",
                aplica_si="farmaceutico",
                obligatorio=True,
                deadlines=_trimestral_deadlines(pago_frac),
            ))

            # Renta anual
            obligations.append(ModelObligation(
                modelo=renta_modelo,
                nombre=f"Modelo {renta_modelo} - IRPF",
                descripcion="Declaracion anual del IRPF",
                periodicidad="anual",
                aplica_si="farmaceutico",
                obligatorio=True,
                deadlines=DEADLINES_2026.get("renta_100", []),
            ))

            # Retenciones si tiene empleados
            if tiene_empleados:
                obligations.append(ModelObligation(
                    modelo=retenciones_modelo,
                    nombre=f"Modelo {retenciones_modelo} - Retenciones trabajo",
                    descripcion="Retenciones e ingresos a cuenta del trabajo personal",
                    periodicidad="trimestral",
                    aplica_si="retenedor",
                    obligatorio=True,
                    deadlines=_trimestral_deadlines(retenciones_modelo),
                ))
                obligations.append(ModelObligation(
                    modelo="190",
                    nombre="Modelo 190 - Resumen anual retenciones",
                    descripcion="Resumen anual de retenciones e ingresos a cuenta del trabajo",
                    periodicidad="anual",
                    aplica_si="retenedor",
                    obligatorio=True,
                    deadlines=DEADLINES_2026.get("resumen_190", []),
                ))

            # Retenciones alquiler si tiene alquileres
            if tiene_alquileres:
                obligations.append(ModelObligation(
                    modelo="115",
                    nombre="Modelo 115 - Retenciones alquiler",
                    descripcion="Retenciones por alquiler de inmuebles urbanos",
                    periodicidad="trimestral",
                    aplica_si="farmaceutico",
                    obligatorio=True,
                    deadlines=_trimestral_deadlines("115"),
                ))
                obligations.append(ModelObligation(
                    modelo="180",
                    nombre="Modelo 180 - Resumen anual alquiler",
                    descripcion="Resumen anual de retenciones por alquiler de inmuebles",
                    periodicidad="anual",
                    aplica_si="farmaceutico",
                    obligatorio=True,
                    deadlines=DEADLINES_2026.get("resumen_180", []),
                ))

            # Operaciones con terceros >3.005,06 EUR
            if ops_terceros:
                obligations.append(ModelObligation(
                    modelo="347",
                    nombre="Modelo 347 - Operaciones con terceros",
                    descripcion="Declaracion anual de operaciones con terceros superiores a 3.005,06 EUR",
                    periodicidad="anual",
                    aplica_si="farmaceutico",
                    obligatorio=True,
                    deadlines=DEADLINES_2026.get("modelo_347", []),
                ))

            # NOTE: No 303 (IVA) and no 390 (resumen anual IVA)
            # The farmaceutico is under Recargo de Equivalencia (Art. 154-163 LIVA)
            # IVA + RE is charged by suppliers; the farmaceutico does not file IVA returns
            for ob in obligations:
                if ob.notas is None:
                    ob.notas = ""
            obligations[0].notas = (
                (obligations[0].notas or "") +
                " Sujeto a Recargo de Equivalencia (Art. 154-163 LIVA) — no presenta Modelo 303 (IVA) ni 390. "
                "El IVA + RE lo ingresa el proveedor."
            ).strip()

            return obligations

        # ── Sociedad ──
        if situacion == "sociedad":
            # IS anual
            obligations.append(ModelObligation(
                modelo=is_modelo,
                nombre=f"Modelo {is_modelo} - Impuesto sobre Sociedades",
                descripcion="Declaracion anual del Impuesto sobre Sociedades",
                periodicidad="anual",
                aplica_si="sociedad",
                obligatorio=True,
                deadlines=DEADLINES_2026.get("is_200", []),
            ))

            # Pagos fraccionados IS (modelo 202)
            obligations.append(ModelObligation(
                modelo="202",
                nombre="Modelo 202 - Pago fraccionado IS",
                descripcion="Pago fraccionado a cuenta del Impuesto sobre Sociedades",
                periodicidad="trimestral",
                aplica_si="sociedad",
                obligatorio=True,
                deadlines=_trimestral_deadlines("202"),
                notas="Solo si facturacion >6M EUR o resultado a ingresar en el ejercicio anterior",
            ))

            # IVA trimestral
            obligations.append(ModelObligation(
                modelo=iva_modelo,
                nombre=f"Modelo {iva_modelo} - Impuesto indirecto trimestral",
                descripcion="Autoliquidacion trimestral del impuesto indirecto",
                periodicidad="trimestral",
                aplica_si="sociedad",
                obligatorio=True,
                deadlines=_trimestral_deadlines(iva_modelo),
            ))

            # Retenciones trabajo (siempre para sociedades)
            obligations.append(ModelObligation(
                modelo=retenciones_modelo,
                nombre=f"Modelo {retenciones_modelo} - Retenciones trabajo",
                descripcion="Retenciones e ingresos a cuenta del trabajo personal",
                periodicidad="trimestral",
                aplica_si="sociedad",
                obligatorio=True,
                deadlines=_trimestral_deadlines(retenciones_modelo),
            ))
            obligations.append(ModelObligation(
                modelo="190",
                nombre="Modelo 190 - Resumen anual retenciones",
                descripcion="Resumen anual de retenciones del trabajo",
                periodicidad="anual",
                aplica_si="sociedad",
                obligatorio=True,
                deadlines=DEADLINES_2026.get("resumen_190", []),
            ))

            # Retenciones alquiler
            if tiene_alquileres:
                obligations.append(ModelObligation(
                    modelo="115",
                    nombre="Modelo 115 - Retenciones alquiler",
                    descripcion="Retenciones por alquiler de inmuebles urbanos",
                    periodicidad="trimestral",
                    aplica_si="sociedad",
                    obligatorio=True,
                    deadlines=_trimestral_deadlines("115"),
                ))
                obligations.append(ModelObligation(
                    modelo="180",
                    nombre="Modelo 180 - Resumen anual alquiler",
                    descripcion="Resumen anual de retenciones por alquiler",
                    periodicidad="anual",
                    aplica_si="sociedad",
                    obligatorio=True,
                    deadlines=DEADLINES_2026.get("resumen_180", []),
                ))

            # Dividendos
            if paga_dividendos:
                obligations.append(ModelObligation(
                    modelo="123",
                    nombre="Modelo 123 - Retenciones capital mobiliario",
                    descripcion="Retenciones sobre dividendos y rendimientos del capital mobiliario",
                    periodicidad="trimestral",
                    aplica_si="sociedad",
                    obligatorio=True,
                    deadlines=_trimestral_deadlines("123"),
                ))
                obligations.append(ModelObligation(
                    modelo="193",
                    nombre="Modelo 193 - Resumen anual capital mobiliario",
                    descripcion="Resumen anual de retenciones del capital mobiliario",
                    periodicidad="anual",
                    aplica_si="sociedad",
                    obligatorio=True,
                    deadlines=DEADLINES_2026.get("resumen_193", []),
                ))

            # Operaciones intracomunitarias
            if ops_intra:
                obligations.append(ModelObligation(
                    modelo="349",
                    nombre="Modelo 349 - Operaciones intracomunitarias",
                    descripcion="Declaracion recapitulativa de operaciones intracomunitarias",
                    periodicidad="trimestral",
                    aplica_si="sociedad",
                    obligatorio=True,
                    deadlines=_trimestral_deadlines("349"),
                ))

            return obligations

        return obligations
