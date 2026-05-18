"""
Modelo 455 Calculator — AIEM aplicado a operadores ZEC (Zona Especial Canaria).

Legal basis (vigente 2025+):
- Decreto Legislativo 1/2025, de 13 de octubre — Texto Refundido IGIC + AIEM
  (BOC nº 207 de 2025-10-20). Refunde la regulacion AIEM y delimita el
  tratamiento de las entregas de mercancias por entidades ZEC sujetas al
  arbitrio.
- Ley 19/1994, de 6 de julio, de modificacion del Regimen Economico y
  Fiscal de Canarias (Titulo V — ZEC).
- Real Decreto 1758/2007, Reglamento de la ZEC.

Diferencias clave Modelo 450 vs Modelo 455:
- 450: productores canarios "ordinarios" (regimen general) declaran
       trimestralmente las entregas de mercancias sujetas a AIEM.
- 455: entidades ZEC con autorizacion para producir/entregar mercancias
       en Canarias declaran sus operaciones AIEM. Periodicidad ANUAL por
       defecto (sin perjuicio de obligaciones trimestrales en supuestos
       concretos definidos por la ATC). Plazo: 1-30 de enero del ano
       siguiente al ejercicio declarado.

Casos de uso:
- Una entidad ZEC manufactura conservas en Tenerife: tributa AIEM via 455
  anual (en lugar del 450 trimestral) si su autorizacion ZEC asi lo
  determina.
- Si la entidad ZEC importa mercancias para uso/consumo propio: AIEM se
  liquida en aduana via DUA (NO via 455).

Estructura del Modelo 455 (anual):
- Operaciones agregadas por epigrafe ZEC autorizado.
- Tipos AIEM identicos al Modelo 450 (5 / 10 / 15 / 25 %).
- Resultado: cuota_devengada_anual - compensaciones + ajustes anuales.

NO existe deduccion de cuotas soportadas: AIEM es monofasico.
"""

from __future__ import annotations

from typing import Any

from app.utils.calculators.modelo_450 import (
    AIEM_TIPOS_POR_EPIGRAFE,  # noqa: F401  (re-exportado para tests)
    ALLOWED_AIEM_RATES,
    TIPO_AIEM_ESPECIAL,
    TIPO_AIEM_GENERAL,
    TIPO_AIEM_INTERMEDIO,
    TIPO_AIEM_REDUCIDO,
    lookup_tipo_aiem,
)
from app.utils.tax_parameter_repository import TaxParameterRepository

# Plazo Modelo 455 anual: 1-30 enero ano siguiente (Orden ATC anual).
PLAZO_MODELO_455_ANUAL: dict[str, Any] = {
    "mes_fin": 1,
    "dia_fin": 30,
    "anio_siguiente": True,
}


def _resolve_year(year: int | None) -> int:
    if year is None:
        return 2025
    return int(year)


class Modelo455Calculator:
    """
    Calculadora autoliquidacion AIEM para operadores ZEC (Modelo 455).

    Periodicidad: ANUAL por defecto. Algunos casos especificos pueden
    requerir presentacion trimestral segun resolucion ATC — el calculator
    soporta ambas modalidades via el parametro `periodicidad`.
    """

    def __init__(self, repo: TaxParameterRepository | None = None) -> None:
        self._repo = repo

    async def calculate(
        self,
        *,
        bienes_anuales: list[dict[str, Any]] | None = None,
        epigrafe_zec: str | None = None,
        cuotas_compensar_anteriores: float = 0.0,
        rectificacion_bases: float = 0.0,
        rectificacion_cuotas: float = 0.0,
        regularizacion_anual: float = 0.0,
        resultado_anterior_complementaria: float = 0.0,
        year: int | None = None,
        periodicidad: str = "anual",  # 'anual' (default) | 'trimestral'
        quarter: int | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Calcula la autoliquidacion AIEM ZEC (Modelo 455).

        Args:
            bienes_anuales: lista de operaciones agregadas anuales por bien:
                {
                    "epigrafe_iae": "4151" (opcional),
                    "descripcion": "Conservas pescado" (opcional),
                    "base_imponible": 250000.0 (obligatorio),
                    "tipo_aiem": 0.15 (opcional — fallback a lookup),
                }
            epigrafe_zec: epigrafe de la autorizacion ZEC (informativo).
            cuotas_compensar_anteriores: cuotas negativas arrastradas (>= 0).
            rectificacion_bases / rectificacion_cuotas: ajustes anuales.
            regularizacion_anual: ajuste anual final.
            resultado_anterior_complementaria: si es complementaria.
            year: ejercicio fiscal (default 2025).
            periodicidad: 'anual' (default) o 'trimestral' (excepcional).
            quarter: 1-4 si periodicidad = 'trimestral'.

        Returns:
            Dict con desglose por bien, total devengado, resultado liquidacion,
            warnings (epigrafes sin tipo conocido), plazo de presentacion.
        """
        # -------------------------------------------------------------------
        # 0. Validaciones
        # -------------------------------------------------------------------
        if periodicidad not in ("anual", "trimestral"):
            raise ValueError(
                f"periodicidad debe ser 'anual' o 'trimestral', recibido: " f"{periodicidad!r}"
            )
        if periodicidad == "trimestral":
            if quarter not in (1, 2, 3, 4):
                raise ValueError(
                    f"En periodicidad trimestral, quarter debe estar entre "
                    f"1 y 4. Recibido: {quarter}"
                )

        year_resolved = _resolve_year(year)
        if year_resolved < 2010 or year_resolved > 2099:
            raise ValueError(f"year fuera de rango razonable: {year_resolved}")

        if cuotas_compensar_anteriores < 0:
            raise ValueError("cuotas_compensar_anteriores debe ser >= 0.")

        bienes = bienes_anuales or []

        # -------------------------------------------------------------------
        # 1. DEVENGADO — iterar sobre cada bien
        # -------------------------------------------------------------------
        desglose_bienes: list[dict[str, Any]] = []
        warnings: list[str] = []
        total_base = 0.0
        total_cuota = 0.0

        for idx, bien in enumerate(bienes, start=1):
            if not isinstance(bien, dict):
                raise ValueError(
                    f"bienes_anuales[{idx - 1}] debe ser un dict, recibido: "
                    f"{type(bien).__name__}"
                )
            base = float(bien.get("base_imponible", 0.0))
            if base < 0:
                raise ValueError(
                    f"bienes_anuales[{idx - 1}].base_imponible no puede ser " f"negativa: {base}"
                )

            epigrafe = str(bien.get("epigrafe_iae", "") or "").strip()
            descripcion = str(bien.get("descripcion", "") or "").strip()
            tipo_manual = bien.get("tipo_aiem")

            tipo_aplicado: float | None = None
            origen_tipo = "manual"

            if tipo_manual is not None:
                tipo_aplicado = float(tipo_manual)
                origen_tipo = "manual"
            elif epigrafe:
                tipo_lookup = lookup_tipo_aiem(epigrafe)
                if tipo_lookup is not None:
                    tipo_aplicado = tipo_lookup
                    origen_tipo = "lookup"

            if tipo_aplicado is None:
                warnings.append(
                    f"Bien #{idx} ({descripcion or epigrafe or 'sin id'}): "
                    "sin tipo_aiem y epigrafe no reconocido. Indica tipo_aiem "
                    "manualmente segun Anexo IV TR Decreto Legislativo 1/2025."
                )
                desglose_bienes.append(
                    {
                        "indice": idx,
                        "epigrafe_iae": epigrafe or None,
                        "descripcion": descripcion or None,
                        "base_imponible": round(base, 2),
                        "tipo_aiem": None,
                        "cuota_aiem": 0.0,
                        "origen_tipo": "desconocido",
                        "warning": True,
                    }
                )
                continue

            tipo_clamped = max(0.0, min(tipo_aplicado, 1.0))
            if tipo_clamped not in ALLOWED_AIEM_RATES:
                warnings.append(
                    f"Bien #{idx}: tipo {tipo_clamped:.2%} fuera de la lista "
                    f"oficial ({', '.join(f'{r:.0%}' for r in ALLOWED_AIEM_RATES)})."
                )
            cuota = round(base * tipo_clamped, 2)
            total_base += base
            total_cuota += cuota

            desglose_bienes.append(
                {
                    "indice": idx,
                    "epigrafe_iae": epigrafe or None,
                    "descripcion": descripcion or None,
                    "base_imponible": round(base, 2),
                    "tipo_aiem": round(tipo_clamped, 4),
                    "cuota_aiem": cuota,
                    "origen_tipo": origen_tipo,
                    "warning": False,
                }
            )

        total_base = round(total_base, 2)
        total_cuota = round(total_cuota, 2)

        # -------------------------------------------------------------------
        # 2. AJUSTES y RESULTADO
        # -------------------------------------------------------------------
        rectificacion_bases = round(float(rectificacion_bases), 2)
        rectificacion_cuotas = round(float(rectificacion_cuotas), 2)

        cuota_devengada_ajustada = round(total_cuota + rectificacion_cuotas, 2)

        cuotas_compensar_aplicadas = max(0.0, round(float(cuotas_compensar_anteriores), 2))

        # En 455 anual la regularizacion anual SIEMPRE aplica (es la
        # liquidacion del ejercicio completo). En 455 trimestral solo en T4.
        if periodicidad == "anual":
            regularizacion_anual_aplicada = round(float(regularizacion_anual), 2)
        else:
            regularizacion_anual_aplicada = (
                round(float(regularizacion_anual), 2) if quarter == 4 else 0.0
            )

        resultado_liquidacion = round(
            cuota_devengada_ajustada - cuotas_compensar_aplicadas + regularizacion_anual_aplicada,
            2,
        )

        cuota_diferencial_complementaria = round(
            resultado_liquidacion - float(resultado_anterior_complementaria),
            2,
        )

        # -------------------------------------------------------------------
        # 3. Plazo
        # -------------------------------------------------------------------
        if periodicidad == "anual":
            plazo_str = f"del 1 al 30 de enero de {year_resolved + 1}"
            periodo_label = "ANUAL"
        else:
            from app.utils.calculators.modelo_450 import PLAZOS_MODELO_450

            plazo_meta = PLAZOS_MODELO_450[quarter]  # type: ignore[index]
            mes_label = [
                "enero",
                "febrero",
                "marzo",
                "abril",
                "mayo",
                "junio",
                "julio",
                "agosto",
                "septiembre",
                "octubre",
                "noviembre",
                "diciembre",
            ][plazo_meta["mes_fin"] - 1]
            plazo_str = f"del 1 al {plazo_meta['dia_fin']} de {mes_label}"
            if plazo_meta["anio_siguiente"]:
                plazo_str += f" de {year_resolved + 1}"
            periodo_label = plazo_meta["trimestre"]

        return {
            "modelo": "455",
            "territorio": "Canarias",
            "organismo": "ATC",
            "regimen": "ZEC",
            "epigrafe_zec": epigrafe_zec,
            "periodicidad": periodicidad,
            "quarter": quarter if periodicidad == "trimestral" else None,
            "year": year_resolved,
            "periodo_label": periodo_label,
            "plazo_presentacion": plazo_str,
            "desglose_bienes": desglose_bienes,
            "total_base_imponible": total_base,
            "total_cuota_devengada": total_cuota,
            "rectificacion_bases": rectificacion_bases,
            "rectificacion_cuotas": rectificacion_cuotas,
            "cuota_devengada_ajustada": cuota_devengada_ajustada,
            "cuotas_compensar_anteriores": cuotas_compensar_aplicadas,
            "regularizacion_anual": regularizacion_anual_aplicada,
            "resultado_liquidacion": resultado_liquidacion,
            "resultado_anterior_complementaria": round(float(resultado_anterior_complementaria), 2),
            "cuota_diferencial_complementaria": cuota_diferencial_complementaria,
            "warnings": warnings,
            "aiem_rates": {
                "tipo_reducido": TIPO_AIEM_REDUCIDO,
                "tipo_intermedio": TIPO_AIEM_INTERMEDIO,
                "tipo_general": TIPO_AIEM_GENERAL,
                "tipo_especial": TIPO_AIEM_ESPECIAL,
            },
        }
