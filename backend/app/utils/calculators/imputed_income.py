"""
Imputed Income Calculator — Renta imputada de inmuebles urbanos (Art. 85 LIRPF).

Owners of non-rented urban properties (other than primary residence, properties
used in economic activity, or properties under construction) must include a
percentage of their valor catastral as income in the general tax base.

Rates:
- 1.1% if valor catastral was revised in the last 10 years
- 2.0% if valor catastral has NOT been revised
- 1.1% of 50% of max(valor_adquisicion, 0) if no valor catastral exists

Supports:
- Multiple properties with individual prorrateo (days + ownership %)
- Usufruct vs nudo propietario distinction
- Usage filtering (only "disposicion" properties impute income)
- Legacy single-value path for backwards compatibility
"""
import calendar
from typing import Any, Dict, List, Optional


class ImputedIncomeCalculator:
    """Renta imputada de inmuebles urbanos (Art. 85 LIRPF).

    Supports multiple properties with individual fields:
    - valor_catastral, valor_adquisicion
    - revision_catastral (bool): True if valor catastral revisado en los 10 anos anteriores
    - dias_disposicion (1-366): days the property was at owner's disposal
    - porcentaje_titularidad (0-100): ownership percentage
    - es_usufructuario (bool): True = usufructuario imputa, False = nudo propietario NO imputa
    - uso: "disposicion" | "arrendado" | "vivienda_habitual" | "afecto" | "en_construccion"

    Formula per property:
        If uso != "disposicion" -> skip (no imputation)
        If not es_usufructuario -> skip (nudo propietario does not impute)

        If valor_catastral > 0:
            base = valor_catastral
            rate = 1.1% if revision_catastral else 2%
        Else:
            base = 50% * max(valor_adquisicion, 0)
            rate = 1.1% (always when no catastral value)

        renta = base * rate * (dias_disposicion / dias_ano) * (porcentaje_titularidad / 100)

    Total renta imputada = sum of all properties
    """

    def calculate(
        self,
        *,
        inmuebles: Optional[List[Dict[str, Any]]] = None,
        valor_catastral_total: float = 0,
        valor_catastral_revisado: bool = True,
        year: int = 2024,
    ) -> Dict[str, Any]:
        """Calculate imputed income for urban properties.

        Args:
            inmuebles: List of property dicts with per-property fields.
                Each dict may contain:
                    - valor_catastral (float, default 0)
                    - valor_adquisicion (float, default 0)
                    - revision_catastral (bool, default True)
                    - dias_disposicion (int, default full year)
                    - porcentaje_titularidad (float, default 100)
                    - es_usufructuario (bool, default True)
                    - uso (str, default "disposicion")
            valor_catastral_total: Legacy aggregate field (used only if
                inmuebles is empty/None).
            valor_catastral_revisado: Legacy flag for the aggregate field.
            year: Tax year (used to determine leap year for day prorrateo).

        Returns:
            Dict with renta_imputada_total, detalle_inmuebles, and
            num_inmuebles_imputados.
        """
        dias_ano = 366 if calendar.isleap(year) else 365

        # --- New per-property path ---
        if inmuebles:
            return self._calculate_per_property(inmuebles, dias_ano)

        # --- Legacy aggregate path ---
        if valor_catastral_total > 0:
            rate = 0.011 if valor_catastral_revisado else 0.02
            renta = round(valor_catastral_total * rate, 2)
            return {
                "renta_imputada_total": renta,
                "detalle_inmuebles": [
                    {
                        "indice": 0,
                        "valor_catastral": valor_catastral_total,
                        "porcentaje_aplicado": rate * 100,
                        "dias_disposicion": dias_ano,
                        "porcentaje_titularidad": 100.0,
                        "renta_imputada": renta,
                    }
                ],
                "num_inmuebles_imputados": 1,
            }

        # --- Nothing to impute ---
        return {
            "renta_imputada_total": 0.0,
            "detalle_inmuebles": [],
            "num_inmuebles_imputados": 0,
        }

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _calculate_per_property(
        self,
        inmuebles: List[Dict[str, Any]],
        dias_ano: int,
    ) -> Dict[str, Any]:
        """Process each property individually and aggregate results."""
        detalle: List[Dict[str, Any]] = []
        total = 0.0

        for idx, prop in enumerate(inmuebles):
            uso = prop.get("uso", "disposicion")
            es_usufructuario = prop.get("es_usufructuario", True)

            # Only "disposicion" properties generate imputed income
            if uso != "disposicion":
                continue

            # Nudo propietario does not impute — only usufructuario
            if not es_usufructuario:
                continue

            valor_catastral = float(prop.get("valor_catastral", 0))
            valor_adquisicion = float(prop.get("valor_adquisicion", 0))
            revision_catastral = prop.get("revision_catastral", True)
            dias_disposicion = int(prop.get("dias_disposicion", dias_ano))
            porcentaje_titularidad = float(prop.get("porcentaje_titularidad", 100))

            # Clamp days to valid range
            dias_disposicion = max(0, min(dias_disposicion, dias_ano))
            # Clamp ownership to 0-100
            porcentaje_titularidad = max(0.0, min(porcentaje_titularidad, 100.0))

            # Determine base and rate
            if valor_catastral > 0:
                base = valor_catastral
                rate = 0.011 if revision_catastral else 0.02
            else:
                base = 0.5 * max(valor_adquisicion, 0)
                rate = 0.011  # always 1.1% when no catastral value

            renta = round(
                base * rate * (dias_disposicion / dias_ano) * (porcentaje_titularidad / 100),
                2,
            )

            detalle.append({
                "indice": idx,
                "valor_catastral": valor_catastral,
                "porcentaje_aplicado": round(rate * 100, 1),
                "dias_disposicion": dias_disposicion,
                "porcentaje_titularidad": porcentaje_titularidad,
                "renta_imputada": renta,
            })
            total += renta

        return {
            "renta_imputada_total": round(total, 2),
            "detalle_inmuebles": detalle,
            "num_inmuebles_imputados": len(detalle),
        }
