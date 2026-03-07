"""
Modelo 420 Calculator — IGIC (Impuesto General Indirecto Canario).

Legal basis:
- Ley 20/1991, de 7 de junio, de modificacion de los aspectos fiscales del Regimen Economico
  Fiscal de Canarias (RIGC).
- Decreto 268/2011, de 4 de agosto, Reglamento de gestion e inspeccion tributaria de Canarias.
- Orden de 20 de diciembre de 2022 (BOC) por la que se aprueba el Modelo 420.

Key distinction:
- Canarias is NOT part of the EU VAT territory (Art. 6 Directiva IVA).
- Canarias does NOT apply IVA (Impuesto sobre el Valor Anadido).
- IGIC uses 7 rate tiers vs. 3 IVA tiers. Structure is otherwise analogous to Modelo 303.

IGIC rates (Ley 4/2012, art. 27 — vigentes 2025):
  Tipo cero         0 %    Alimentos basicos, medicamentos, agua, transporte publico,
                            VPO, servicios sanitarios y educativos.
  Tipo reducido     3 %    Suministros industriales, quimicos, textiles, minerales,
                            madera, papel, caucho, alimentos elaborados.
  Tipo general      7 %    Tipo residual (todo lo no encuadrado en otro tipo).
  Incrementado 1    9.5 %  Vehiculos de motor, embarcaciones, joyeria.
  Incrementado 2   13.5 %  Bebidas alcoholicas, perfumeria, articulos de piel,
                            electronica de consumo.
  Especial 1       20 %    Tabaco negro.
  Especial 2       35 %    Tabaco rubio / Virginia.

Calculates:
  IGIC devengado (output) by rate tier, adquisiciones extracanarias, inversion sujeto pasivo,
  modificaciones de bases/cuotas, and total devengado.
  IGIC deducible (input) by concept and total deducible.
  Resultado del regimen general, ajustes, and resultado final de liquidacion.

Usage:
    repo = TaxParameterRepository(db)
    calc = Modelo420Calculator(repo)
    result = await calc.calculate(base_7=10000, cuota_corrientes_interiores=700, quarter=2)
"""
from typing import Any, Dict

from app.utils.tax_parameter_repository import TaxParameterRepository


# ---------------------------------------------------------------------------
# Named constants for IGIC rates (Ley 4/2012, art. 27 — vigentes 2025)
# ---------------------------------------------------------------------------
TIPO_CERO = 0.00
TIPO_REDUCIDO = 0.03
TIPO_GENERAL = 0.07
TIPO_INCREMENTADO_1 = 0.095
TIPO_INCREMENTADO_2 = 0.135
TIPO_ESPECIAL_1 = 0.20
TIPO_ESPECIAL_2 = 0.35


class Modelo420Calculator:
    """
    Calculates the IGIC quarterly self-assessment (Modelo 420) for Canarias.

    The calculator mirrors the structure of Modelo 303 (IVA) but uses the 7-tier
    IGIC rate schedule instead of the 3-tier IVA schedule.

    Args:
        repo: TaxParameterRepository — accepted for protocol consistency.
              Not used internally: IGIC rates are statutory constants, not DB params.
    """

    def __init__(self, repo: TaxParameterRepository) -> None:
        self._repo = repo  # Kept for protocol consistency; not queried.

    async def calculate(
        self,
        *,
        # --- IGIC DEVENGADO: bases imponibles por tipo ---
        base_0: float = 0.0,
        base_3: float = 0.0,
        base_7: float = 0.0,
        base_9_5: float = 0.0,
        base_13_5: float = 0.0,
        base_20: float = 0.0,
        base_35: float = 0.0,
        # Adquisiciones extracanarias (equiv. intracomunitarias en IVA)
        base_extracanarias: float = 0.0,
        tipo_extracanarias: float = TIPO_GENERAL,
        # Inversion del sujeto pasivo
        base_inversion_sp: float = 0.0,
        # Modificaciones de bases y cuotas devengadas
        mod_bases: float = 0.0,
        mod_cuotas: float = 0.0,
        # --- IGIC DEDUCIBLE: cuotas soportadas por concepto ---
        cuota_corrientes_interiores: float = 0.0,
        cuota_inversion_interiores: float = 0.0,
        cuota_importaciones_corrientes: float = 0.0,
        cuota_importaciones_inversion: float = 0.0,
        cuota_extracanarias_corrientes: float = 0.0,
        cuota_extracanarias_inversion: float = 0.0,
        rectificacion_deducciones: float = 0.0,
        compensacion_agricultura: float = 0.0,
        regularizacion_inversion: float = 0.0,
        regularizacion_prorrata: float = 0.0,
        # --- RESULTADO: ajustes finales ---
        cuotas_compensar_anteriores: float = 0.0,
        regularizacion_anual: float = 0.0,
        resultado_anterior_complementaria: float = 0.0,
        # --- Control ---
        quarter: int = 1,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """
        Calculate the IGIC quarterly self-assessment (Modelo 420).

        IGIC DEVENGADO (output):
            base_0: Base imponible al tipo cero (0 %).
                Alimentos basicos, medicamentos, agua, transporte publico, VPO,
                servicios sanitarios y educativos.
            base_3: Base imponible al tipo reducido (3 %).
                Suministros industriales, quimicos, textiles, minerales, madera, papel,
                caucho, alimentos elaborados.
            base_7: Base imponible al tipo general (7 %).
                Tipo residual para operaciones no encuadradas en otros tipos.
            base_9_5: Base imponible al tipo incrementado 1 (9.5 %).
                Vehiculos de motor, embarcaciones, joyeria.
            base_13_5: Base imponible al tipo incrementado 2 (13.5 %).
                Bebidas alcoholicas, perfumeria, articulos de piel, electronica de consumo.
            base_20: Base imponible al tipo especial 1 (20 %). Tabaco negro.
            base_35: Base imponible al tipo especial 2 (35 %). Tabaco rubio / Virginia.
            base_extracanarias: Base imponible por adquisiciones de bienes o servicios
                fuera de Canarias (equivalente intracomunitario en IVA).
            tipo_extracanarias: Tipo aplicable a adquisiciones extracanarias (decimal 0.0–1.0).
                Por defecto 0.07 (tipo general). Usar el tipo que corresponda al bien/servicio.
            base_inversion_sp: Base imponible en operaciones con inversion del sujeto pasivo.
                El tipo aplicado es el general (7 %) salvo indicacion contraria via kwargs.
            mod_bases: Modificaciones de bases imponibles de periodos anteriores.
                Puede ser negativo (rectificacion a la baja).
            mod_cuotas: Modificaciones de cuotas devengadas de periodos anteriores.
                Puede ser negativo (rectificacion a la baja).

        IGIC DEDUCIBLE (input):
            cuota_corrientes_interiores: Cuotas IGIC soportadas en operaciones corrientes interiores.
            cuota_inversion_interiores: Cuotas IGIC soportadas en bienes de inversion interiores.
            cuota_importaciones_corrientes: Cuotas IGIC en importaciones de bienes corrientes.
            cuota_importaciones_inversion: Cuotas IGIC en importaciones de bienes de inversion.
            cuota_extracanarias_corrientes: Cuotas en adquisiciones extracanarias corrientes.
            cuota_extracanarias_inversion: Cuotas en adquisiciones extracanarias de inversion.
            rectificacion_deducciones: Rectificacion de deducciones de periodos anteriores.
                Puede ser negativo si se rectifica al alza o al objeto de devolucion.
            compensacion_agricultura: Compensaciones del regimen especial de agricultura,
                ganaderia y pesca (REAGP), Art. 59 Ley 20/1991.
            regularizacion_inversion: Regularizacion de bienes de inversion, Arts. 109-113 RIGC.
            regularizacion_prorrata: Regularizacion anual de la prorrata (solo 4T).

        RESULTADO:
            cuotas_compensar_anteriores: Cuotas a compensar de autoliquidaciones anteriores
                (siempre >= 0; se ignoran valores negativos).
            regularizacion_anual: Importe de la regularizacion anual de la prorrata.
                Solo se aplica cuando quarter == 4.
            resultado_anterior_complementaria: Resultado de la autoliquidacion anterior
                en caso de que la presente sea complementaria. Default 0.
            quarter: Trimestre de la autoliquidacion (1-4).

        Returns:
            Dict with:
            - desglose_devengado (dict): breakdown of IGIC output by tier and concept.
            - total_devengado (float): total IGIC devengado.
            - desglose_deducible (dict): breakdown of IGIC input by concept.
            - total_deducible (float): total IGIC deducible.
            - resultado_regimen_general (float): devengado - deducible.
            - cuotas_compensar_anteriores (float): applied from previous periods.
            - regularizacion_anual (float): applied only in Q4.
            - resultado_liquidacion (float): final amount payable (+) or to compensate (-).
            - resultado_anterior_complementaria (float): prior result if complementary.
            - cuota_diferencial_complementaria (float): net of complementary filing.
            - quarter (int): period number.
            - igic_rates (dict): statutory rates used in the calculation.
        """
        # -----------------------------------------------------------------------
        # 1. IGIC DEVENGADO — cuotas por tipo de gravamen
        # -----------------------------------------------------------------------
        cuota_0 = round(base_0 * TIPO_CERO, 2)
        cuota_3 = round(base_3 * TIPO_REDUCIDO, 2)
        cuota_7 = round(base_7 * TIPO_GENERAL, 2)
        cuota_9_5 = round(base_9_5 * TIPO_INCREMENTADO_1, 2)
        cuota_13_5 = round(base_13_5 * TIPO_INCREMENTADO_2, 2)
        cuota_20 = round(base_20 * TIPO_ESPECIAL_1, 2)
        cuota_35 = round(base_35 * TIPO_ESPECIAL_2, 2)

        # Adquisiciones extracanarias — tipo variable segun naturaleza del bien/servicio
        tipo_extracanarias_clamped = max(0.0, min(float(tipo_extracanarias), 1.0))
        cuota_extracanarias = round(base_extracanarias * tipo_extracanarias_clamped, 2)

        # Inversion del sujeto pasivo — tipo general por defecto (Art. 19 Ley 20/1991)
        cuota_inversion_sp = round(base_inversion_sp * TIPO_GENERAL, 2)

        total_devengado = round(
            cuota_0
            + cuota_3
            + cuota_7
            + cuota_9_5
            + cuota_13_5
            + cuota_20
            + cuota_35
            + cuota_extracanarias
            + cuota_inversion_sp
            + mod_cuotas,
            2,
        )

        desglose_devengado: Dict[str, Any] = {
            "tipo_cero": {
                "base": round(base_0, 2),
                "tipo": TIPO_CERO,
                "cuota": cuota_0,
            },
            "tipo_reducido": {
                "base": round(base_3, 2),
                "tipo": TIPO_REDUCIDO,
                "cuota": cuota_3,
            },
            "tipo_general": {
                "base": round(base_7, 2),
                "tipo": TIPO_GENERAL,
                "cuota": cuota_7,
            },
            "tipo_incrementado_1": {
                "base": round(base_9_5, 2),
                "tipo": TIPO_INCREMENTADO_1,
                "cuota": cuota_9_5,
            },
            "tipo_incrementado_2": {
                "base": round(base_13_5, 2),
                "tipo": TIPO_INCREMENTADO_2,
                "cuota": cuota_13_5,
            },
            "tipo_especial_1_tabaco_negro": {
                "base": round(base_20, 2),
                "tipo": TIPO_ESPECIAL_1,
                "cuota": cuota_20,
            },
            "tipo_especial_2_tabaco_rubio": {
                "base": round(base_35, 2),
                "tipo": TIPO_ESPECIAL_2,
                "cuota": cuota_35,
            },
            "adquisiciones_extracanarias": {
                "base": round(base_extracanarias, 2),
                "tipo": round(tipo_extracanarias_clamped, 4),
                "cuota": cuota_extracanarias,
            },
            "inversion_sujeto_pasivo": {
                "base": round(base_inversion_sp, 2),
                "tipo": TIPO_GENERAL,
                "cuota": cuota_inversion_sp,
            },
            "modificacion_bases": round(mod_bases, 2),
            "modificacion_cuotas": round(mod_cuotas, 2),
        }

        # -----------------------------------------------------------------------
        # 2. IGIC DEDUCIBLE — cuotas soportadas por concepto
        # -----------------------------------------------------------------------
        total_deducible = round(
            cuota_corrientes_interiores
            + cuota_inversion_interiores
            + cuota_importaciones_corrientes
            + cuota_importaciones_inversion
            + cuota_extracanarias_corrientes
            + cuota_extracanarias_inversion
            + rectificacion_deducciones
            + compensacion_agricultura
            + regularizacion_inversion
            + regularizacion_prorrata,
            2,
        )

        desglose_deducible: Dict[str, Any] = {
            "cuota_corrientes_interiores": round(cuota_corrientes_interiores, 2),
            "cuota_inversion_interiores": round(cuota_inversion_interiores, 2),
            "cuota_importaciones_corrientes": round(cuota_importaciones_corrientes, 2),
            "cuota_importaciones_inversion": round(cuota_importaciones_inversion, 2),
            "cuota_extracanarias_corrientes": round(cuota_extracanarias_corrientes, 2),
            "cuota_extracanarias_inversion": round(cuota_extracanarias_inversion, 2),
            "rectificacion_deducciones": round(rectificacion_deducciones, 2),
            "compensacion_agricultura": round(compensacion_agricultura, 2),
            "regularizacion_inversion": round(regularizacion_inversion, 2),
            "regularizacion_prorrata": round(regularizacion_prorrata, 2),
        }

        # -----------------------------------------------------------------------
        # 3. RESULTADO
        # -----------------------------------------------------------------------
        resultado_regimen_general = round(total_devengado - total_deducible, 2)

        # Compensacion de cuotas de periodos anteriores — nunca puede ser negativa
        cuotas_compensar_aplicadas = max(0.0, round(float(cuotas_compensar_anteriores), 2))

        # Regularizacion anual de la prorrata — exclusiva del 4T (Ley 20/1991, art. 37)
        regularizacion_anual_aplicada = round(float(regularizacion_anual), 2) if quarter == 4 else 0.0

        resultado_liquidacion = round(
            resultado_regimen_general
            - cuotas_compensar_aplicadas
            + regularizacion_anual_aplicada,
            2,
        )

        # Autoliquidacion complementaria: diferencia neta respecto a la anterior
        cuota_diferencial_complementaria = round(
            resultado_liquidacion - float(resultado_anterior_complementaria), 2
        )

        return {
            # --- Devengado ---
            "desglose_devengado": desglose_devengado,
            "total_devengado": total_devengado,
            # --- Deducible ---
            "desglose_deducible": desglose_deducible,
            "total_deducible": total_deducible,
            # --- Resultado ---
            "resultado_regimen_general": resultado_regimen_general,
            "cuotas_compensar_anteriores": cuotas_compensar_aplicadas,
            "regularizacion_anual": regularizacion_anual_aplicada,
            "resultado_liquidacion": resultado_liquidacion,
            # --- Complementaria ---
            "resultado_anterior_complementaria": round(float(resultado_anterior_complementaria), 2),
            "cuota_diferencial_complementaria": cuota_diferencial_complementaria,
            # --- Metadatos ---
            "quarter": quarter,
            "igic_rates": {
                "tipo_cero": TIPO_CERO,
                "tipo_reducido": TIPO_REDUCIDO,
                "tipo_general": TIPO_GENERAL,
                "tipo_incrementado_1": TIPO_INCREMENTADO_1,
                "tipo_incrementado_2": TIPO_INCREMENTADO_2,
                "tipo_especial_1": TIPO_ESPECIAL_1,
                "tipo_especial_2": TIPO_ESPECIAL_2,
            },
        }
