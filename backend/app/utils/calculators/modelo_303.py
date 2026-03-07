"""
IVA / Modelo 303 Calculator — Declaracion trimestral del IVA (Regimen General).

Official form: Modelo 303 (AEAT, aprobado por Orden HAP/2215/2013 y sucesivas).
Casillas reference: version vigente ejercicio 2025.

Scope:
- Territorio comun (AEAT)
- Pais Vasco (Modelo 300, same arithmetic, different submission context)
- Navarra (uses this same structure)
- Canarias: NOT covered here (uses IGIC / Modelo 420)
- Ceuta / Melilla: NOT covered here (uses IPSI, deferred implementation)

Only Regimen General is implemented.  Regimen Simplificado (modulos) is
out of scope and would require a separate calculator.

IVA rates are statutory (LIVA art. 90-91) and do NOT come from the database,
so TaxParameterRepository is accepted in __init__ for interface consistency
but is not used in calculations.
"""
from typing import Any, Dict

from app.utils.tax_parameter_repository import TaxParameterRepository

# Statutory IVA rates (LIVA art. 90-91, unchanged since 2012 for general/reduced/superreduced)
_TIPO_GENERAL: float = 21.0
_TIPO_REDUCIDO: float = 10.0
_TIPO_SUPERREDUCIDO: float = 4.0


class Modelo303Calculator:
    """
    Calculates the quarterly IVA self-assessment (Modelo 303, Regimen General).

    Each instance is stateless beyond the (unused) repository reference;
    all state lives in the ``calculate`` call.
    """

    def __init__(self, repo: TaxParameterRepository) -> None:
        # Kept for interface consistency with the rest of the calculator package.
        self._repo = repo

    async def calculate(
        self,
        *,
        # --- IVA DEVENGADO (output tax) ---
        base_4: float = 0.0,
        base_10: float = 0.0,
        base_21: float = 0.0,
        # Adquisiciones intracomunitarias de bienes / servicios (casillas 10-12)
        base_intracomunitarias: float = 0.0,
        tipo_intracomunitarias: float = 0.0,   # variable %, e.g. 21.0
        # Inversion del sujeto pasivo — ISP (casillas 13-14)
        base_inversion_sp: float = 0.0,
        tipo_inversion_sp: float = 21.0,       # normally 21% unless service is reduced
        # Modificacion de bases y cuotas de periodos anteriores (casillas 15-16)
        mod_bases: float = 0.0,
        mod_cuotas: float = 0.0,               # signed: negative = rectification in favour
        # --- IVA DEDUCIBLE (input tax) ---
        # Corrientes interiores (casillas 28-29): base informativa + deductible quota
        base_corrientes_interiores: float = 0.0,
        cuota_corrientes_interiores: float = 0.0,
        # Bienes de inversion interiores (casillas 30-31)
        base_inversion_interiores: float = 0.0,
        cuota_inversion_interiores: float = 0.0,
        # Importaciones corrientes (casillas 32-33)
        base_importaciones_corrientes: float = 0.0,
        cuota_importaciones_corrientes: float = 0.0,
        # Importaciones de bienes de inversion (casillas 34-35)
        base_importaciones_inversion: float = 0.0,
        cuota_importaciones_inversion: float = 0.0,
        # Adquisiciones intracomunitarias corrientes (casillas 36-37)
        base_intracom_corrientes: float = 0.0,
        cuota_intracom_corrientes: float = 0.0,
        # Adquisiciones intracomunitarias de inversion (casillas 38-39)
        base_intracom_inversion: float = 0.0,
        cuota_intracom_inversion: float = 0.0,
        # Rectificacion de deducciones (casillas 40-41), signed
        base_rectificacion_deducciones: float = 0.0,
        rectificacion_deducciones: float = 0.0,
        # Compensaciones regimen especial agricultura, ganaderia y pesca (casilla 42)
        compensacion_agricultura: float = 0.0,
        # Regularizacion bienes de inversion por regla de prorrata (casilla 43), signed
        regularizacion_inversion: float = 0.0,
        # Regularizacion por aplicacion del porcentaje definitivo de prorrata (casilla 44), signed
        regularizacion_prorrata: float = 0.0,
        # --- RESULTADO ---
        # Porcentaje de atribucion al Estado (casilla 65)
        # 100% for territorio comun; <100% for companies operating in multiple territories
        pct_atribucion_estado: float = 100.0,
        # IVA a la importacion liquidado por la Aduana pendiente de ingreso (casilla 77)
        iva_aduana_pendiente: float = 0.0,
        # Cuotas a compensar de periodos anteriores (casilla 78), >= 0
        cuotas_compensar_anteriores: float = 0.0,
        # Regularizacion anual (casilla 68): ONLY filled in 4T; signed
        regularizacion_anual: float = 0.0,
        # Para declaracion complementaria: resultado de la declaracion anterior (casilla 70)
        resultado_anterior_complementaria: float = 0.0,
        # Metadata
        quarter: int = 1,         # 1-4
        year: int = 2025,
        territory: str = "comun",  # 'comun' | 'araba' | 'bizkaia' | 'gipuzkoa' | 'navarra'
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """
        Compute all Modelo 303 casillas and return the full self-assessment.

        Args:
            base_4: Base imponible al tipo superreducido 4% (casilla 01).
            base_10: Base imponible al tipo reducido 10% (casilla 04).
            base_21: Base imponible al tipo general 21% (casilla 07).
            base_intracomunitarias: Base de adquisiciones intracomunitarias (casilla 10).
            tipo_intracomunitarias: Tipo aplicado a las adquisiciones intracomunitarias (casilla 11),
                expressed as a percentage, e.g. 21.0.  The corresponding cuota (casilla 12)
                is calculated automatically.
            base_inversion_sp: Base de operaciones en inversion del sujeto pasivo (casilla 13).
            tipo_inversion_sp: Tipo aplicado a la ISP (casilla 13 bis), default 21%.
                The cuota (casilla 14) is calculated automatically.
            mod_bases: Modificacion de bases imponibles de periodos anteriores (casilla 15), signed.
            mod_cuotas: Modificacion de cuotas de periodos anteriores (casilla 16), signed.
                Negative value = rectification in favour of the taxpayer.
            base_corrientes_interiores: Base de IVA soportado en operaciones corrientes
                interiores, purely informative (casilla 28).
            cuota_corrientes_interiores: Cuota soportada en operaciones corrientes interiores
                deducible (casilla 29).
            base_inversion_interiores: Base de bienes de inversion interiores (casilla 30),
                informative.
            cuota_inversion_interiores: Cuota deducible de bienes de inversion interiores
                (casilla 31).
            base_importaciones_corrientes: Base de importaciones corrientes (casilla 32),
                informative.
            cuota_importaciones_corrientes: Cuota deducible de importaciones corrientes
                (casilla 33).
            base_importaciones_inversion: Base de importaciones de bienes de inversion
                (casilla 34), informative.
            cuota_importaciones_inversion: Cuota deducible de importaciones de inversion
                (casilla 35).
            base_intracom_corrientes: Base de adquisiciones intracomunitarias corrientes
                (casilla 36), informative.
            cuota_intracom_corrientes: Cuota deducible de adquisiciones intracomunitarias
                corrientes (casilla 37).
            base_intracom_inversion: Base de adquisiciones intracomunitarias de inversion
                (casilla 38), informative.
            cuota_intracom_inversion: Cuota deducible de adquisiciones intracomunitarias
                de inversion (casilla 39).
            base_rectificacion_deducciones: Base de las cuotas deducibles rectificadas
                (casilla 40), informative, signed.
            rectificacion_deducciones: Cuota neta de rectificacion de deducciones (casilla 41),
                signed.  Positive = additional deduction; negative = reduction of prior deduction.
            compensacion_agricultura: Compensaciones del regimen especial de agricultura,
                ganaderia y pesca satisfechas (casilla 42).
            regularizacion_inversion: Regularizacion de bienes de inversion (art. 107-110 LIVA),
                (casilla 43), signed.
            regularizacion_prorrata: Regularizacion por variacion del porcentaje definitivo de
                prorrata (casilla 44), signed.  Only filled in 4T.
            pct_atribucion_estado: Percentage of the result attributable to Estado / territorio
                comun (casilla 65).  100.0 for most declarants.
            iva_aduana_pendiente: Cuotas de IVA a la importacion liquidadas por la Aduana
                pendientes de ingreso (casilla 77).
            cuotas_compensar_anteriores: Cuotas a compensar de periodos anteriores (casilla 78).
                Must be >= 0.
            regularizacion_anual: Regularizacion cuotas art. 80.cinco.5a LIVA (casilla 68).
                Only applicable in 4T.  Signed.
            resultado_anterior_complementaria: Resultado de la declaracion anterior cuando se
                presenta declaracion complementaria (casilla 70).
            quarter: Fiscal quarter (1-4).  Affects whether regularizacion_anual is allowed.
            year: Fiscal year.
            territory: Territory identifier for informational purposes.
                'comun' | 'araba' | 'bizkaia' | 'gipuzkoa' | 'navarra'

        Returns:
            Dict containing every casilla value plus structured breakdowns:
            - casilla_01 … casilla_71: individual form field values
            - total_devengado, total_deducible, resultado_regimen_general
            - resultado_liquidacion: final settlement amount (positive = to pay, negative = to refund/compensate)
            - desglose_devengado: dict with per-rate and per-concept breakdown of output tax
            - desglose_deducible: dict with per-concept breakdown of deductible input tax
            - territory, quarter, year
        """
        # ------------------------------------------------------------------
        # 1. IVA DEVENGADO (output tax)
        # ------------------------------------------------------------------

        # Casillas 01-03: tipo superreducido 4%
        casilla_01 = round(base_4, 2)
        casilla_02 = _TIPO_SUPERREDUCIDO
        casilla_03 = round(base_4 * _TIPO_SUPERREDUCIDO / 100, 2)

        # Casillas 04-06: tipo reducido 10%
        casilla_04 = round(base_10, 2)
        casilla_05 = _TIPO_REDUCIDO
        casilla_06 = round(base_10 * _TIPO_REDUCIDO / 100, 2)

        # Casillas 07-09: tipo general 21%
        casilla_07 = round(base_21, 2)
        casilla_08 = _TIPO_GENERAL
        casilla_09 = round(base_21 * _TIPO_GENERAL / 100, 2)

        # Casillas 10-12: adquisiciones intracomunitarias
        casilla_10 = round(base_intracomunitarias, 2)
        casilla_11 = round(tipo_intracomunitarias, 2)
        casilla_12 = round(base_intracomunitarias * tipo_intracomunitarias / 100, 2)

        # Casillas 13-14: inversion del sujeto pasivo
        casilla_13 = round(base_inversion_sp, 2)
        casilla_14 = round(base_inversion_sp * tipo_inversion_sp / 100, 2)

        # Casillas 15-16: modificacion de bases y cuotas (+/-)
        casilla_15 = round(mod_bases, 2)
        casilla_16 = round(mod_cuotas, 2)

        # Casilla 27: TOTAL IVA DEVENGADO
        casilla_27 = round(
            casilla_03
            + casilla_06
            + casilla_09
            + casilla_12
            + casilla_14
            + casilla_16,
            2,
        )

        # ------------------------------------------------------------------
        # 2. IVA DEDUCIBLE (input tax)
        # ------------------------------------------------------------------

        # Casillas 28-29: bienes/servicios corrientes interiores
        casilla_28 = round(base_corrientes_interiores, 2)       # informative base
        casilla_29 = round(cuota_corrientes_interiores, 2)

        # Casillas 30-31: bienes de inversion interiores
        casilla_30 = round(base_inversion_interiores, 2)        # informative base
        casilla_31 = round(cuota_inversion_interiores, 2)

        # Casillas 32-33: importaciones corrientes
        casilla_32 = round(base_importaciones_corrientes, 2)    # informative base
        casilla_33 = round(cuota_importaciones_corrientes, 2)

        # Casillas 34-35: importaciones de bienes de inversion
        casilla_34 = round(base_importaciones_inversion, 2)     # informative base
        casilla_35 = round(cuota_importaciones_inversion, 2)

        # Casillas 36-37: adquisiciones intracomunitarias corrientes
        casilla_36 = round(base_intracom_corrientes, 2)         # informative base
        casilla_37 = round(cuota_intracom_corrientes, 2)

        # Casillas 38-39: adquisiciones intracomunitarias de inversion
        casilla_38 = round(base_intracom_inversion, 2)          # informative base
        casilla_39 = round(cuota_intracom_inversion, 2)

        # Casillas 40-41: rectificacion de deducciones (+/-)
        casilla_40 = round(base_rectificacion_deducciones, 2)   # informative base
        casilla_41 = round(rectificacion_deducciones, 2)

        # Casilla 42: compensaciones regimen especial agricultura
        casilla_42 = round(compensacion_agricultura, 2)

        # Casilla 43: regularizacion bienes de inversion (+/-)
        casilla_43 = round(regularizacion_inversion, 2)

        # Casilla 44: regularizacion prorrata (+/-)
        casilla_44 = round(regularizacion_prorrata, 2)

        # Casilla 45: TOTAL A DEDUCIR
        casilla_45 = round(
            casilla_29
            + casilla_31
            + casilla_33
            + casilla_35
            + casilla_37
            + casilla_39
            + casilla_41
            + casilla_42
            + casilla_43
            + casilla_44,
            2,
        )

        # ------------------------------------------------------------------
        # 3. RESULTADO
        # ------------------------------------------------------------------

        # Casilla 46: resultado regimen general = devengado - deducible
        casilla_46 = round(casilla_27 - casilla_45, 2)

        # Casilla 64: suma de resultados (= casilla_46; no simplificado)
        casilla_64 = casilla_46

        # Casilla 65: % atribucion territorio comun
        casilla_65 = round(pct_atribucion_estado, 4)

        # Casilla 66: importe atribuible al Estado
        casilla_66 = round(casilla_64 * casilla_65 / 100, 2)

        # Casilla 77: IVA importacion Aduana pendiente de ingreso
        casilla_77 = round(iva_aduana_pendiente, 2)

        # Casilla 78: cuotas a compensar de periodos anteriores (>= 0)
        cuotas_compensar_anteriores = max(0.0, cuotas_compensar_anteriores)
        casilla_78 = round(cuotas_compensar_anteriores, 2)

        # Casilla 68: regularizacion anual (solo 4T; ignored in other quarters)
        if quarter == 4:
            casilla_68 = round(regularizacion_anual, 2)
        else:
            casilla_68 = 0.0

        # Casilla 69: resultado previo = 66 + 77 - 78 + 68
        casilla_69 = round(casilla_66 + casilla_77 - casilla_78 + casilla_68, 2)

        # Casilla 70: resultado declaracion anterior (complementaria)
        casilla_70 = round(resultado_anterior_complementaria, 2)

        # Casilla 71: RESULTADO LIQUIDACION
        casilla_71 = round(casilla_69 - casilla_70, 2)

        # ------------------------------------------------------------------
        # 4. Descriptive breakdowns
        # ------------------------------------------------------------------
        desglose_devengado = {
            "superreducido_4pct": {
                "base": casilla_01,
                "tipo": casilla_02,
                "cuota": casilla_03,
            },
            "reducido_10pct": {
                "base": casilla_04,
                "tipo": casilla_05,
                "cuota": casilla_06,
            },
            "general_21pct": {
                "base": casilla_07,
                "tipo": casilla_08,
                "cuota": casilla_09,
            },
            "intracomunitarias": {
                "base": casilla_10,
                "tipo": casilla_11,
                "cuota": casilla_12,
            },
            "inversion_sujeto_pasivo": {
                "base": casilla_13,
                "cuota": casilla_14,
            },
            "modificacion_bases_cuotas": {
                "bases": casilla_15,
                "cuotas": casilla_16,
            },
            "total_devengado": casilla_27,
        }

        desglose_deducible = {
            "corrientes_interiores": {
                "base_informativa": casilla_28,
                "cuota": casilla_29,
            },
            "inversion_interiores": {
                "base_informativa": casilla_30,
                "cuota": casilla_31,
            },
            "importaciones_corrientes": {
                "base_informativa": casilla_32,
                "cuota": casilla_33,
            },
            "importaciones_inversion": {
                "base_informativa": casilla_34,
                "cuota": casilla_35,
            },
            "intracom_corrientes": {
                "base_informativa": casilla_36,
                "cuota": casilla_37,
            },
            "intracom_inversion": {
                "base_informativa": casilla_38,
                "cuota": casilla_39,
            },
            "rectificacion_deducciones": {
                "base_informativa": casilla_40,
                "cuota": casilla_41,
            },
            "compensacion_agricultura": casilla_42,
            "regularizacion_bienes_inversion": casilla_43,
            "regularizacion_prorrata": casilla_44,
            "total_deducible": casilla_45,
        }

        return {
            # --- IVA devengado ---
            "casilla_01": casilla_01,
            "casilla_02": casilla_02,
            "casilla_03": casilla_03,
            "casilla_04": casilla_04,
            "casilla_05": casilla_05,
            "casilla_06": casilla_06,
            "casilla_07": casilla_07,
            "casilla_08": casilla_08,
            "casilla_09": casilla_09,
            "casilla_10": casilla_10,
            "casilla_11": casilla_11,
            "casilla_12": casilla_12,
            "casilla_13": casilla_13,
            "casilla_14": casilla_14,
            "casilla_15": casilla_15,
            "casilla_16": casilla_16,
            "casilla_27": casilla_27,
            # --- IVA deducible ---
            "casilla_28": casilla_28,
            "casilla_29": casilla_29,
            "casilla_30": casilla_30,
            "casilla_31": casilla_31,
            "casilla_32": casilla_32,
            "casilla_33": casilla_33,
            "casilla_34": casilla_34,
            "casilla_35": casilla_35,
            "casilla_36": casilla_36,
            "casilla_37": casilla_37,
            "casilla_38": casilla_38,
            "casilla_39": casilla_39,
            "casilla_40": casilla_40,
            "casilla_41": casilla_41,
            "casilla_42": casilla_42,
            "casilla_43": casilla_43,
            "casilla_44": casilla_44,
            "casilla_45": casilla_45,
            # --- Resultado ---
            "casilla_46": casilla_46,
            "casilla_64": casilla_64,
            "casilla_65": casilla_65,
            "casilla_66": casilla_66,
            "casilla_68": casilla_68,
            "casilla_69": casilla_69,
            "casilla_70": casilla_70,
            "casilla_71": casilla_71,
            "casilla_77": casilla_77,
            "casilla_78": casilla_78,
            # --- Summary fields ---
            "total_devengado": casilla_27,
            "total_deducible": casilla_45,
            "resultado_regimen_general": casilla_46,
            "resultado_liquidacion": casilla_71,
            # --- Breakdowns ---
            "desglose_devengado": desglose_devengado,
            "desglose_deducible": desglose_deducible,
            # --- Metadata ---
            "territory": territory,
            "quarter": quarter,
            "year": year,
        }
