"""
Modelo IPSI Calculator — Impuesto sobre la Produccion, los Servicios y la Importacion.

Legal basis:
- Ley 8/1991, de 25 de marzo (regimen economico y fiscal de Ceuta)
- Ley 13/1996, de 30 de diciembre (Melilla)
- Ordenanzas fiscales locales de cada ciudad autonoma (actualizadas anualmente)

Key distinction:
- Ceuta and Melilla are NOT part of the EU VAT territory.
- They do NOT apply IVA (Impuesto sobre el Valor Anadido).
- IPSI uses 6 rate tiers: 0.5%, 1%, 2%, 4%, 8%, 10%.
- Each city has its own ordenanza fiscal that determines which rate applies
  to each category of goods/services.
- General rate: Ceuta ~3%, Melilla ~4% (varies by ordenanza fiscal vigente).

The calculator accepts tax bases by rate tier (the user selects the applicable rate
based on their city's ordenanza fiscal). It does NOT auto-assign rates by territory.

Usage:
    calc = ModeloIpsiCalculator(repo=None)
    result = await calc.calculate(
        territorio="Ceuta", base_4=10000,
        cuota_corrientes_interiores=300, quarter=2, year=2025
    )
"""
from typing import Any, Dict

from app.utils.tax_parameter_repository import TaxParameterRepository


# ---------------------------------------------------------------------------
# IPSI rate constants (Ley 8/1991, art. 43 — rango legal vigente)
# ---------------------------------------------------------------------------
TIPO_MINIMO = 0.005       # 0.5%
TIPO_REDUCIDO = 0.01      # 1%
TIPO_BONIFICADO = 0.02    # 2%
TIPO_GENERAL = 0.04       # 4%
TIPO_INCREMENTADO = 0.08  # 8%
TIPO_ESPECIAL = 0.10      # 10%


class ModeloIpsiCalculator:
    """
    Calculates the IPSI quarterly self-assessment for Ceuta and Melilla.

    The calculator mirrors the structure of Modelo 420 (IGIC) but uses the
    6-tier IPSI rate schedule. Both cities share the same legal rate range
    but their ordenanzas fiscales may assign different rates to the same
    category of goods/services.

    Args:
        repo: TaxParameterRepository — accepted for protocol consistency.
              Not used internally: IPSI rates are statutory constants.
    """

    def __init__(self, repo: TaxParameterRepository) -> None:
        self._repo = repo

    async def calculate(
        self,
        *,
        territorio: str = "Ceuta",
        # --- IPSI DEVENGADO: bases imponibles por tipo ---
        base_0_5: float = 0.0,
        base_1: float = 0.0,
        base_2: float = 0.0,
        base_4: float = 0.0,
        base_8: float = 0.0,
        base_10: float = 0.0,
        # Importaciones
        base_importaciones: float = 0.0,
        tipo_importaciones: float = TIPO_GENERAL,
        # Inversion del sujeto pasivo
        base_inversion_sp: float = 0.0,
        tipo_inversion_sp: float = TIPO_GENERAL,
        # Modificaciones de bases y cuotas devengadas
        mod_bases: float = 0.0,
        mod_cuotas: float = 0.0,
        # --- IPSI DEDUCIBLE: cuotas soportadas por concepto ---
        cuota_corrientes_interiores: float = 0.0,
        cuota_inversion_interiores: float = 0.0,
        cuota_importaciones_corrientes: float = 0.0,
        cuota_importaciones_inversion: float = 0.0,
        rectificacion_deducciones: float = 0.0,
        regularizacion_inversion: float = 0.0,
        regularizacion_prorrata: float = 0.0,
        # --- RESULTADO: ajustes finales ---
        cuotas_compensar_anteriores: float = 0.0,
        regularizacion_anual: float = 0.0,
        resultado_anterior_complementaria: float = 0.0,
        # --- Control ---
        quarter: int = 1,
        year: int = 2025,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """
        Calculate the IPSI quarterly self-assessment.

        IPSI DEVENGADO (output):
            base_0_5: Base imponible al 0.5% (tipo minimo).
            base_1: Base imponible al 1% (tipo reducido).
            base_2: Base imponible al 2% (tipo bonificado).
            base_4: Base imponible al 4% (tipo general).
            base_8: Base imponible al 8% (tipo incrementado).
            base_10: Base imponible al 10% (tipo especial).
            base_importaciones: Base imponible por importaciones.
            tipo_importaciones: Tipo aplicable a importaciones (decimal).
            base_inversion_sp: Base en operaciones con inversion del sujeto pasivo.
            tipo_inversion_sp: Tipo para ISP (decimal).
            mod_bases: Modificaciones de bases de periodos anteriores.
            mod_cuotas: Modificaciones de cuotas de periodos anteriores.

        IPSI DEDUCIBLE (input):
            cuota_corrientes_interiores: Cuotas IPSI soportadas en operaciones corrientes.
            cuota_inversion_interiores: Cuotas IPSI en bienes de inversion.
            cuota_importaciones_corrientes: Cuotas IPSI en importaciones corrientes.
            cuota_importaciones_inversion: Cuotas IPSI en importaciones de inversion.
            rectificacion_deducciones: Rectificacion de deducciones anteriores.
            regularizacion_inversion: Regularizacion de bienes de inversion.
            regularizacion_prorrata: Regularizacion de la prorrata (solo 4T).

        RESULTADO:
            cuotas_compensar_anteriores: Cuotas a compensar de periodos anteriores (>= 0).
            regularizacion_anual: Regularizacion anual (solo 4T).
            resultado_anterior_complementaria: Resultado anterior si complementaria.
            quarter: Trimestre (1-4).
            year: Ano fiscal.
            territorio: "Ceuta" o "Melilla".

        Returns:
            Dict with desglose_devengado, total_devengado, desglose_deducible,
            total_deducible, resultado_regimen_general, resultado_liquidacion, etc.
        """
        # -----------------------------------------------------------------------
        # 1. IPSI DEVENGADO — cuotas por tipo de gravamen
        # -----------------------------------------------------------------------
        cuota_0_5 = round(base_0_5 * TIPO_MINIMO, 2)
        cuota_1 = round(base_1 * TIPO_REDUCIDO, 2)
        cuota_2 = round(base_2 * TIPO_BONIFICADO, 2)
        cuota_4 = round(base_4 * TIPO_GENERAL, 2)
        cuota_8 = round(base_8 * TIPO_INCREMENTADO, 2)
        cuota_10 = round(base_10 * TIPO_ESPECIAL, 2)

        # Importaciones — tipo variable
        tipo_imp_clamped = max(0.0, min(float(tipo_importaciones), 1.0))
        cuota_importaciones = round(base_importaciones * tipo_imp_clamped, 2)

        # Inversion del sujeto pasivo
        tipo_isp_clamped = max(0.0, min(float(tipo_inversion_sp), 1.0))
        cuota_isp = round(base_inversion_sp * tipo_isp_clamped, 2)

        total_devengado = round(
            cuota_0_5
            + cuota_1
            + cuota_2
            + cuota_4
            + cuota_8
            + cuota_10
            + cuota_importaciones
            + cuota_isp
            + mod_cuotas,
            2,
        )

        desglose_devengado: Dict[str, Any] = {
            "tipo_minimo_0_5": {
                "base": round(base_0_5, 2),
                "tipo": TIPO_MINIMO,
                "cuota": cuota_0_5,
            },
            "tipo_reducido_1": {
                "base": round(base_1, 2),
                "tipo": TIPO_REDUCIDO,
                "cuota": cuota_1,
            },
            "tipo_bonificado_2": {
                "base": round(base_2, 2),
                "tipo": TIPO_BONIFICADO,
                "cuota": cuota_2,
            },
            "tipo_general_4": {
                "base": round(base_4, 2),
                "tipo": TIPO_GENERAL,
                "cuota": cuota_4,
            },
            "tipo_incrementado_8": {
                "base": round(base_8, 2),
                "tipo": TIPO_INCREMENTADO,
                "cuota": cuota_8,
            },
            "tipo_especial_10": {
                "base": round(base_10, 2),
                "tipo": TIPO_ESPECIAL,
                "cuota": cuota_10,
            },
            "importaciones": {
                "base": round(base_importaciones, 2),
                "tipo": round(tipo_imp_clamped, 4),
                "cuota": cuota_importaciones,
            },
            "inversion_sujeto_pasivo": {
                "base": round(base_inversion_sp, 2),
                "tipo": round(tipo_isp_clamped, 4),
                "cuota": cuota_isp,
            },
            "modificacion_bases": round(mod_bases, 2),
            "modificacion_cuotas": round(mod_cuotas, 2),
        }

        # -----------------------------------------------------------------------
        # 2. IPSI DEDUCIBLE — cuotas soportadas por concepto
        # -----------------------------------------------------------------------
        total_deducible = round(
            cuota_corrientes_interiores
            + cuota_inversion_interiores
            + cuota_importaciones_corrientes
            + cuota_importaciones_inversion
            + rectificacion_deducciones
            + regularizacion_inversion
            + regularizacion_prorrata,
            2,
        )

        desglose_deducible: Dict[str, Any] = {
            "cuota_corrientes_interiores": round(cuota_corrientes_interiores, 2),
            "cuota_inversion_interiores": round(cuota_inversion_interiores, 2),
            "cuota_importaciones_corrientes": round(cuota_importaciones_corrientes, 2),
            "cuota_importaciones_inversion": round(cuota_importaciones_inversion, 2),
            "rectificacion_deducciones": round(rectificacion_deducciones, 2),
            "regularizacion_inversion": round(regularizacion_inversion, 2),
            "regularizacion_prorrata": round(regularizacion_prorrata, 2),
        }

        # -----------------------------------------------------------------------
        # 3. RESULTADO
        # -----------------------------------------------------------------------
        resultado_regimen_general = round(total_devengado - total_deducible, 2)

        cuotas_compensar_aplicadas = max(0.0, round(float(cuotas_compensar_anteriores), 2))

        regularizacion_anual_aplicada = (
            round(float(regularizacion_anual), 2) if quarter == 4 else 0.0
        )

        resultado_liquidacion = round(
            resultado_regimen_general
            - cuotas_compensar_aplicadas
            + regularizacion_anual_aplicada,
            2,
        )

        cuota_diferencial_complementaria = round(
            resultado_liquidacion - float(resultado_anterior_complementaria), 2
        )

        return {
            "territorio": territorio,
            "desglose_devengado": desglose_devengado,
            "total_devengado": total_devengado,
            "desglose_deducible": desglose_deducible,
            "total_deducible": total_deducible,
            "resultado_regimen_general": resultado_regimen_general,
            "cuotas_compensar_anteriores": cuotas_compensar_aplicadas,
            "regularizacion_anual": regularizacion_anual_aplicada,
            "resultado_liquidacion": resultado_liquidacion,
            "resultado_anterior_complementaria": round(
                float(resultado_anterior_complementaria), 2
            ),
            "cuota_diferencial_complementaria": cuota_diferencial_complementaria,
            "quarter": quarter,
            "year": year,
            "ipsi_rates": {
                "tipo_minimo": TIPO_MINIMO,
                "tipo_reducido": TIPO_REDUCIDO,
                "tipo_bonificado": TIPO_BONIFICADO,
                "tipo_general": TIPO_GENERAL,
                "tipo_incrementado": TIPO_INCREMENTADO,
                "tipo_especial": TIPO_ESPECIAL,
            },
        }
