"""
Modelo 420 Calculator — IGIC (Impuesto General Indirecto Canario).

Legal basis (vigente 2025+):
- Decreto Legislativo 1/2025, de 9 de octubre, por el que se aprueba el Texto
  Refundido de la Comunidad Autonoma de Canarias del IGIC y AIEM (BOC nº 207
  de 2025-10-20, vigor 2025-10-21).
- Ley 20/1991, de 7 de junio, REF Canarias (marco constitucional).
- Decreto 268/2011, de 4 de agosto, Reglamento de gestion e inspeccion.
- Orden por la que se aprueba anualmente el Modelo 420.

Derogacion 2025-10-21:
- Arts. 51-61 Ley 4/2012 (escala antigua) — DEROGADOS.
- Tipo 13.5% (incrementado_2 antiguo) → 15%.
- Tipo 35% (especial tabaco rubio antiguo) → 20% (unificado tabaco).
- Renombrado "reducido 3%" → "superreducido 3%".
- Anadido "reducido 5%" (Art. 35 TR).
- Anadido "energeticos 1%" (Art. 33 bis TR).

Tipos vigentes 2025+ (TR Decreto Legislativo 1/2025):
  Tipo cero          0 %    Alimentos basicos, medicamentos, agua, transporte
                              publico, VPO, sanitarios, educativos.
  Tipo energeticos   1 %    Suministros gas, electricidad residencial (Art. 33 bis).
  Tipo superreducido 3 %    Suministros industriales, quimicos, textiles,
                              minerales, madera, papel, caucho.
  Tipo reducido      5 %    Alimentos elaborados (Art. 35 TR).
  Tipo general       7 %    Tipo residual.
  Incrementado 1     9.5 %  Vehiculos de motor, embarcaciones, joyeria.
  Incrementado 2    15 %    Bebidas alcoholicas, perfumeria, peleteria,
                              electronica de consumo (sustituye al 13.5%).
  Especial          20 %    Labores del tabaco unificado (Art. 37 TR).

REPEP — Regimen Especial Pequeño Empresario:
- Umbral: 30.000 EUR/ano (volumen operaciones ano anterior).
- Sujetos REPEP estan EXENTOS del Modelo 420.
- La verificacion del umbral se hace en `app/territories/canarias/plugin.py`,
  no en el calculator (separation of concerns).

Calcula:
  IGIC devengado (output) por tipo, adquisiciones extracanarias, inversion
  sujeto pasivo, modificaciones de bases/cuotas, total devengado.
  IGIC deducible (input) por concepto y total deducible.
  Resultado del regimen general, ajustes y resultado final de liquidacion.
"""

from typing import Any

from app.utils.tax_parameter_repository import TaxParameterRepository

# ---------------------------------------------------------------------------
# Constantes — tipos vigentes 2025+ (TR Decreto Legislativo 1/2025)
# ---------------------------------------------------------------------------
TIPO_CERO = 0.00
TIPO_ENERGETICOS = 0.01
TIPO_SUPERREDUCIDO = 0.03
TIPO_REDUCIDO = 0.05
TIPO_GENERAL = 0.07
TIPO_INCREMENTADO_1 = 0.095
TIPO_INCREMENTADO_2 = 0.15
TIPO_ESPECIAL = 0.20


# ---------------------------------------------------------------------------
# Tabla parametrica por ejercicio — IGIC_RATES_BY_YEAR
# ---------------------------------------------------------------------------
# 2024 mantiene escala antigua (Ley 4/2012 art. 27 — derogada 2025-10-21).
# 2025+ aplica el TR Decreto Legislativo 1/2025.
IGIC_RATES_BY_YEAR: dict[int, dict[str, float]] = {
    2024: {
        "cero": 0.00,
        "energeticos": 0.01,  # ya existia parcialmente
        "superreducido": 0.03,  # antes "reducido"
        "reducido": 0.05,  # ya existia
        "general": 0.07,
        "incrementado_1": 0.095,
        "incrementado_2": 0.135,  # DEROGADO 2025
        "especial": 0.20,  # tabaco negro
        "especial_tabaco_rubio_legacy": 0.35,  # DEROGADO 2025
    },
    2025: {
        "cero": 0.00,
        "energeticos": 0.01,
        "superreducido": 0.03,
        "reducido": 0.05,
        "general": 0.07,
        "incrementado_1": 0.095,
        "incrementado_2": 0.15,  # NUEVO 2025
        "especial": 0.20,  # tabaco unificado
    },
    2026: {
        "cero": 0.00,
        "energeticos": 0.01,
        "superreducido": 0.03,
        "reducido": 0.05,
        "general": 0.07,
        "incrementado_1": 0.095,
        "incrementado_2": 0.15,
        "especial": 0.20,
    },
}


# Tipos derogados — accesibles solo para auditoria de ejercicios <2025.
DEROGATED_RATES_2024: dict[str, float] = {
    "incrementado_2_old": 0.135,
    "especial_tabaco_rubio_old": 0.35,
}


# Plazos Modelo 420 (Art. 71 RIGC + Orden anual ATC):
# T1: 1-20 abril; T2: 1-20 julio; T3: 1-20 octubre; T4: 1-30 enero ano siguiente.
PLAZOS_MODELO_420: dict[int, dict[str, Any]] = {
    1: {"trimestre": "T1", "mes_fin": 4, "dia_fin": 20, "anio_siguiente": False},
    2: {"trimestre": "T2", "mes_fin": 7, "dia_fin": 20, "anio_siguiente": False},
    3: {"trimestre": "T3", "mes_fin": 10, "dia_fin": 20, "anio_siguiente": False},
    4: {"trimestre": "T4", "mes_fin": 1, "dia_fin": 30, "anio_siguiente": True},
}


# REPEP — Regimen Especial Pequeño Empresario IGIC.
# Umbral exencion: 30.000 EUR/ano (volumen operaciones ano anterior).
REPEP_THRESHOLD_EUR = 30000.0


def _resolve_year(year: int | None) -> int:
    """Devuelve el year a aplicar; default = 2025 (esquema vigente)."""
    if year is None:
        return 2025
    return int(year)


def _rate_incrementado_2(year: int) -> float:
    """13.5% para 2024, 15% para 2025+."""
    if year < 2025:
        return DEROGATED_RATES_2024["incrementado_2_old"]
    return TIPO_INCREMENTADO_2


def _rate_especial(year: int, tabaco_rubio_legacy: bool) -> float:
    """
    Tipo especial: 20% por defecto.
    Si year<2025 y tabaco_rubio_legacy=True → 35% (esquema antiguo).
    En 2025+ el flag legacy se ignora (tabaco unificado al 20%).
    """
    if year < 2025 and tabaco_rubio_legacy:
        return DEROGATED_RATES_2024["especial_tabaco_rubio_old"]
    return TIPO_ESPECIAL


class Modelo420Calculator:
    """
    Calculadora autoliquidacion trimestral IGIC (Modelo 420) para Canarias.

    La estructura mimica el Modelo 303 (IVA peninsular) pero usa la escala
    parametrizada por ejercicio del TR Decreto Legislativo 1/2025.
    """

    def __init__(self, repo: TaxParameterRepository | None) -> None:
        self._repo = repo  # Reservado para futuras consultas a parametros.

    async def calculate(
        self,
        *,
        # --- IGIC DEVENGADO: bases imponibles por tipo (nombres canonicos) ---
        base_cero: float = 0.0,
        base_energeticos: float = 0.0,
        base_superreducido: float = 0.0,
        base_reducido: float = 0.0,
        base_general: float = 0.0,
        base_incrementado_1: float = 0.0,
        base_incrementado_2: float = 0.0,
        base_especial: float = 0.0,
        # --- Aliases legacy (retro-compat con callers anteriores al refactor) ---
        base_0: float = 0.0,  # alias base_cero
        base_3: float = 0.0,  # alias base_superreducido
        base_7: float = 0.0,  # alias base_general
        base_9_5: float = 0.0,  # alias base_incrementado_1
        base_13_5: float = 0.0,  # alias base_incrementado_2 (year=2024)
        base_20: float = 0.0,  # alias base_especial
        base_35: float = 0.0,  # alias base_especial con tabaco_rubio_legacy=True
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
        year: int | None = None,
        tabaco_rubio_legacy: bool = False,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Calcula la autoliquidacion trimestral IGIC (Modelo 420)."""
        # -------------------------------------------------------------------
        # 0. Aliases legacy → nombres canonicos (no rompe callers antiguos)
        # -------------------------------------------------------------------
        if base_0 and not base_cero:
            base_cero = base_0
        if base_3 and not base_superreducido:
            base_superreducido = base_3
        if base_7 and not base_general:
            base_general = base_7
        if base_9_5 and not base_incrementado_1:
            base_incrementado_1 = base_9_5
        if base_13_5 and not base_incrementado_2:
            base_incrementado_2 = base_13_5
        if base_20 and not base_especial:
            base_especial = base_20
        if base_35 and not base_especial:
            base_especial = base_35
            tabaco_rubio_legacy = True

        # -------------------------------------------------------------------
        # 0.b Validaciones
        # -------------------------------------------------------------------
        bases = {
            "base_cero": base_cero,
            "base_energeticos": base_energeticos,
            "base_superreducido": base_superreducido,
            "base_reducido": base_reducido,
            "base_general": base_general,
            "base_incrementado_1": base_incrementado_1,
            "base_incrementado_2": base_incrementado_2,
            "base_especial": base_especial,
            "base_extracanarias": base_extracanarias,
            "base_inversion_sp": base_inversion_sp,
        }
        for name, val in bases.items():
            if val < 0:
                raise ValueError(f"La base imponible '{name}' no puede ser negativa: {val}")

        if quarter not in (1, 2, 3, 4):
            raise ValueError(f"quarter debe estar entre 1 y 4, recibido: {quarter}")

        year_resolved = _resolve_year(year)
        if year_resolved < 2010 or year_resolved > 2099:
            raise ValueError(f"year fuera de rango razonable: {year_resolved}")

        # -------------------------------------------------------------------
        # 1. Resolver tipos para el ejercicio
        # -------------------------------------------------------------------
        rate_incrementado_2 = _rate_incrementado_2(year_resolved)
        rate_especial = _rate_especial(year_resolved, tabaco_rubio_legacy)

        # -------------------------------------------------------------------
        # 2. IGIC DEVENGADO
        # -------------------------------------------------------------------
        cuota_cero = round(base_cero * TIPO_CERO, 2)
        cuota_energeticos = round(base_energeticos * TIPO_ENERGETICOS, 2)
        cuota_superreducido = round(base_superreducido * TIPO_SUPERREDUCIDO, 2)
        cuota_reducido = round(base_reducido * TIPO_REDUCIDO, 2)
        cuota_general = round(base_general * TIPO_GENERAL, 2)
        cuota_incrementado_1 = round(base_incrementado_1 * TIPO_INCREMENTADO_1, 2)
        cuota_incrementado_2 = round(base_incrementado_2 * rate_incrementado_2, 2)
        cuota_especial = round(base_especial * rate_especial, 2)

        # Adquisiciones extracanarias — tipo variable
        tipo_extracanarias_clamped = max(0.0, min(float(tipo_extracanarias), 1.0))
        cuota_extracanarias = round(base_extracanarias * tipo_extracanarias_clamped, 2)

        # Inversion sujeto pasivo — tipo general por defecto (Art. 19 Ley 20/1991)
        cuota_inversion_sp = round(base_inversion_sp * TIPO_GENERAL, 2)

        total_devengado = round(
            cuota_cero
            + cuota_energeticos
            + cuota_superreducido
            + cuota_reducido
            + cuota_general
            + cuota_incrementado_1
            + cuota_incrementado_2
            + cuota_especial
            + cuota_extracanarias
            + cuota_inversion_sp
            + mod_cuotas,
            2,
        )

        desglose_devengado: dict[str, Any] = {
            "tipo_cero": {
                "base": round(base_cero, 2),
                "tipo": TIPO_CERO,
                "cuota": cuota_cero,
            },
            "tipo_energeticos": {
                "base": round(base_energeticos, 2),
                "tipo": TIPO_ENERGETICOS,
                "cuota": cuota_energeticos,
            },
            "tipo_superreducido": {
                "base": round(base_superreducido, 2),
                "tipo": TIPO_SUPERREDUCIDO,
                "cuota": cuota_superreducido,
            },
            "tipo_reducido": {
                "base": round(base_reducido, 2),
                "tipo": TIPO_REDUCIDO,
                "cuota": cuota_reducido,
            },
            "tipo_general": {
                "base": round(base_general, 2),
                "tipo": TIPO_GENERAL,
                "cuota": cuota_general,
            },
            "tipo_incrementado_1": {
                "base": round(base_incrementado_1, 2),
                "tipo": TIPO_INCREMENTADO_1,
                "cuota": cuota_incrementado_1,
            },
            "tipo_incrementado_2": {
                "base": round(base_incrementado_2, 2),
                "tipo": rate_incrementado_2,
                "cuota": cuota_incrementado_2,
            },
            "tipo_especial": {
                "base": round(base_especial, 2),
                "tipo": rate_especial,
                "cuota": cuota_especial,
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

        # -------------------------------------------------------------------
        # 3. IGIC DEDUCIBLE
        # -------------------------------------------------------------------
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

        desglose_deducible: dict[str, Any] = {
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

        # -------------------------------------------------------------------
        # 4. RESULTADO
        # -------------------------------------------------------------------
        resultado_regimen_general = round(total_devengado - total_deducible, 2)

        cuotas_compensar_aplicadas = max(0.0, round(float(cuotas_compensar_anteriores), 2))

        # Regularizacion anual exclusiva del 4T (TR Decreto Legislativo 1/2025).
        regularizacion_anual_aplicada = (
            round(float(regularizacion_anual), 2) if quarter == 4 else 0.0
        )

        resultado_liquidacion = round(
            resultado_regimen_general - cuotas_compensar_aplicadas + regularizacion_anual_aplicada,
            2,
        )

        cuota_diferencial_complementaria = round(
            resultado_liquidacion - float(resultado_anterior_complementaria), 2
        )

        # -------------------------------------------------------------------
        # 5. RATES expuestos en output
        # -------------------------------------------------------------------
        # En 2025+ NO exponer claves del esquema derogado (tipo_especial_2 etc).
        igic_rates: dict[str, float] = {
            "tipo_cero": TIPO_CERO,
            "tipo_energeticos": TIPO_ENERGETICOS,
            "tipo_superreducido": TIPO_SUPERREDUCIDO,
            "tipo_reducido": TIPO_REDUCIDO,
            "tipo_general": TIPO_GENERAL,
            "tipo_incrementado_1": TIPO_INCREMENTADO_1,
            "tipo_incrementado_2": rate_incrementado_2,
            "tipo_especial": rate_especial,
        }

        return {
            "desglose_devengado": desglose_devengado,
            "total_devengado": total_devengado,
            "desglose_deducible": desglose_deducible,
            "total_deducible": total_deducible,
            "resultado_regimen_general": resultado_regimen_general,
            "cuotas_compensar_anteriores": cuotas_compensar_aplicadas,
            "regularizacion_anual": regularizacion_anual_aplicada,
            "resultado_liquidacion": resultado_liquidacion,
            "resultado_anterior_complementaria": round(float(resultado_anterior_complementaria), 2),
            "cuota_diferencial_complementaria": cuota_diferencial_complementaria,
            "quarter": quarter,
            "year": year_resolved,
            "igic_rates": igic_rates,
        }
