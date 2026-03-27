"""
Capital Gains Property Calculator — Ganancias patrimoniales por transmision de inmuebles.

Calculates capital gains from property sales for IRPF, including:
- Art. 33-37 LIRPF: Base computation (precio venta - valor adquisicion)
- Art. 35 LIRPF: Valor de adquisicion = precio + gastos + mejoras - amortizaciones
- Art. 38 LIRPF: Exencion por reinversion en vivienda habitual
- DT 9a LIRPF: Coeficientes de abatimiento para inmuebles adquiridos antes de 31/12/1994
- Casillas 0355-0370 del Modelo 100

The net gain goes to base del ahorro (Art. 46 LIRPF).
"""
from __future__ import annotations

import logging
import math
from datetime import date, datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def _parse_date(date_str: Optional[str]) -> Optional[date]:
    """Parse YYYY-MM-DD date string. Returns None on failure."""
    if not date_str:
        return None
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%d/%m/%Y"):
        try:
            return datetime.strptime(date_str, fmt).date()
        except ValueError:
            continue
    return None


# Coeficiente de abatimiento para inmuebles: 11.11% por ano de permanencia
# que exceda de 2, redondeando por exceso (DT 9a LIRPF).
COEF_ABATIMIENTO_INMUEBLES = 11.11

# Fecha limite para que aplique abatimiento: adquisicion antes de 31/12/1994
FECHA_LIMITE_ABATIMIENTO = date(1994, 12, 31)

# Fecha hasta la que se computa la permanencia para abatimiento: 19/01/2006
FECHA_FIN_PERMANENCIA = date(2006, 1, 19)

# Limite acumulado de valor de transmision desde 01/01/2015 para aplicar abatimiento
LIMITE_ACUMULADO_TRANSMISION = 400_000.0


class PropertyCapitalGainsCalculator:
    """Calculates capital gains from property sales (Art. 33-38 + DT 9a LIRPF).

    Each sale (VentaInmueble) is processed independently:
    1. Compute ganancia bruta = valor transmision - valor adquisicion
    2. Apply DT 9a abatimiento if pre-1994 acquisition (up to 400K cumulative limit)
    3. Apply Art. 38 reinversion vivienda habitual exemption
    4. Net gain goes to base del ahorro
    """

    async def calculate(
        self,
        *,
        ventas: List[Dict[str, Any]],
        valor_transmision_previo_2015: float = 0,
        year: int = 2025,
    ) -> Dict[str, Any]:
        """Calculate capital gains from property sales.

        Args:
            ventas: List of property sale dicts, each with:
                - tipo: "vivienda_habitual" | "otro"
                - precio_venta: Sale price (EUR)
                - precio_adquisicion: Purchase price (EUR)
                - fecha_adquisicion: Acquisition date (YYYY-MM-DD)
                - fecha_venta: Sale date (YYYY-MM-DD)
                - gastos_adquisicion: Acquisition costs (notary, registry, ITP)
                - gastos_venta: Sale costs (plusvalia municipal, agency)
                - mejoras: Capital improvements
                - amortizaciones: Accumulated depreciation (if was rented)
                - reinversion_vivienda_habitual: Whether reinvesting in new home
                - importe_reinversion: Amount reinvested
            valor_transmision_previo_2015: Cumulative sale amounts since 01/01/2015
                from prior years (for the 400K abatimiento limit).
            year: Fiscal year.

        Returns:
            Dict with ganancia_bruta_total, abatimiento_total,
            exencion_reinversion_total, ganancia_neta_total, and desglose per sale.
        """
        if not ventas:
            return self._empty_result()

        desglose: List[Dict[str, Any]] = []
        ganancia_bruta_total = 0.0
        abatimiento_total = 0.0
        exencion_reinversion_total = 0.0
        ganancia_neta_total = 0.0
        avisos: List[str] = []

        # Track cumulative valor transmision for DT 9a 400K limit
        valor_transmision_acumulado = valor_transmision_previo_2015

        for idx, venta in enumerate(ventas):
            resultado_venta = self._process_venta(
                venta, idx, valor_transmision_acumulado, year
            )
            desglose.append(resultado_venta)

            ganancia_bruta_total += resultado_venta["ganancia_bruta"]
            abatimiento_total += resultado_venta["abatimiento"]
            exencion_reinversion_total += resultado_venta["exencion_reinversion"]
            ganancia_neta_total += resultado_venta["ganancia_neta"]
            if resultado_venta.get("aviso_reinversion"):
                avisos.append(resultado_venta["aviso_reinversion"])

            # Accumulate valor transmision for next sale's 400K limit check
            valor_transmision_acumulado += resultado_venta["precio_venta"]

        result = {
            "ganancia_bruta_total": round(ganancia_bruta_total, 2),
            "abatimiento_total": round(abatimiento_total, 2),
            "exencion_reinversion_total": round(exencion_reinversion_total, 2),
            "ganancia_neta_total": round(max(0.0, ganancia_neta_total), 2),
            "num_ventas": len(ventas),
            "desglose": desglose,
        }
        if avisos:
            result["avisos"] = avisos
        return result

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _process_venta(
        self,
        venta: Dict[str, Any],
        idx: int,
        valor_transmision_acumulado: float,
        year: int,
    ) -> Dict[str, Any]:
        """Process a single property sale."""
        tipo = venta.get("tipo", "otro")
        precio_venta = float(venta.get("precio_venta", 0))
        precio_adquisicion = float(venta.get("precio_adquisicion", 0))
        gastos_adquisicion = float(venta.get("gastos_adquisicion", 0))
        gastos_venta = float(venta.get("gastos_venta", 0))
        mejoras = float(venta.get("mejoras", 0))
        amortizaciones = float(venta.get("amortizaciones", 0))
        reinversion = bool(venta.get("reinversion_vivienda_habitual", False))
        importe_reinversion = float(venta.get("importe_reinversion", 0))

        fecha_adquisicion = _parse_date(venta.get("fecha_adquisicion"))
        fecha_venta = _parse_date(venta.get("fecha_venta"))
        fecha_nueva_adquisicion = _parse_date(venta.get("fecha_nueva_adquisicion"))

        # --- 1. Valor de transmision (Art. 35.2 LIRPF) ---
        # Valor transmision = precio_venta - gastos_venta
        valor_transmision = precio_venta - gastos_venta

        # --- 2. Valor de adquisicion (Art. 35.1 LIRPF) ---
        # Valor adquisicion = precio_adquisicion + gastos + mejoras - amortizaciones
        valor_adquisicion = (
            precio_adquisicion + gastos_adquisicion + mejoras - amortizaciones
        )

        # --- 3. Ganancia bruta ---
        ganancia_bruta = valor_transmision - valor_adquisicion

        # If loss, no abatimiento or reinversion applies
        if ganancia_bruta <= 0:
            return {
                "indice": idx,
                "tipo": tipo,
                "precio_venta": round(precio_venta, 2),
                "valor_transmision": round(valor_transmision, 2),
                "valor_adquisicion": round(valor_adquisicion, 2),
                "ganancia_bruta": round(ganancia_bruta, 2),
                "aplica_abatimiento": False,
                "coeficiente_abatimiento_pct": 0.0,
                "abatimiento": 0.0,
                "aplica_reinversion": False,
                "exencion_reinversion": 0.0,
                "ganancia_neta": round(ganancia_bruta, 2),
            }

        # --- 4. Coeficientes de abatimiento DT 9a ---
        aplica_abatimiento = False
        coeficiente_pct = 0.0
        abatimiento = 0.0

        if fecha_adquisicion and fecha_adquisicion <= FECHA_LIMITE_ABATIMIENTO:
            # Check 400K cumulative limit
            if (valor_transmision_acumulado + precio_venta) <= LIMITE_ACUMULADO_TRANSMISION:
                aplica_abatimiento = True
                coeficiente_pct = self._calcular_coeficiente_abatimiento(
                    fecha_adquisicion
                )
                # Abatimiento reduces the gain (capped at 100%)
                coeficiente_pct = min(coeficiente_pct, 100.0)
                abatimiento = round(ganancia_bruta * (coeficiente_pct / 100.0), 2)

        ganancia_tras_abatimiento = ganancia_bruta - abatimiento

        # --- 5. Exencion por reinversion en vivienda habitual (Art. 38) ---
        aplica_reinversion = False
        exencion_reinversion = 0.0
        aviso_reinversion: Optional[str] = None

        if (
            reinversion
            and tipo == "vivienda_habitual"
            and importe_reinversion > 0
            and ganancia_tras_abatimiento > 0
        ):
            # Art. 38.1 LIRPF: reinversion must happen within 24 months of sale
            reinversion_valida = True
            if fecha_venta and fecha_nueva_adquisicion:
                plazo_dias = (fecha_nueva_adquisicion - fecha_venta).days
                plazo_limite = 730  # ~24 months (365.25 * 2)
                if plazo_dias < 0 or plazo_dias > plazo_limite:
                    reinversion_valida = False
                    aviso_reinversion = (
                        f"Venta {idx}: la fecha de nueva adquisicion "
                        f"({fecha_nueva_adquisicion.isoformat()}) esta fuera del "
                        f"plazo de 24 meses desde la venta "
                        f"({fecha_venta.isoformat()}). "
                        f"Art. 38.1 LIRPF: no aplica exencion por reinversion."
                    )
                    logger.warning(
                        "Reinversion fuera de plazo: venta=%s, nueva_adq=%s, dias=%d",
                        fecha_venta, fecha_nueva_adquisicion, plazo_dias,
                    )
            elif fecha_venta and not fecha_nueva_adquisicion:
                # User has not yet acquired — still within 24-month window (or unknown)
                aviso_reinversion = (
                    f"Venta {idx}: reinversion declarada pero sin fecha de nueva "
                    f"adquisicion. Recuerde que dispone de 24 meses desde la venta "
                    f"({fecha_venta.isoformat()}) para reinvertir en nueva vivienda "
                    f"habitual (Art. 38.1 LIRPF)."
                )

            if reinversion_valida:
                aplica_reinversion = True
                # Proportional exemption: ganancia * (importe_reinversion / precio_venta)
                if precio_venta > 0:
                    ratio = min(importe_reinversion / precio_venta, 1.0)
                    exencion_reinversion = round(ganancia_tras_abatimiento * ratio, 2)

        ganancia_neta = ganancia_tras_abatimiento - exencion_reinversion

        result = {
            "indice": idx,
            "tipo": tipo,
            "precio_venta": round(precio_venta, 2),
            "valor_transmision": round(valor_transmision, 2),
            "valor_adquisicion": round(valor_adquisicion, 2),
            "ganancia_bruta": round(ganancia_bruta, 2),
            "aplica_abatimiento": aplica_abatimiento,
            "coeficiente_abatimiento_pct": round(coeficiente_pct, 2),
            "abatimiento": round(abatimiento, 2),
            "aplica_reinversion": aplica_reinversion,
            "exencion_reinversion": round(exencion_reinversion, 2),
            "ganancia_neta": round(ganancia_neta, 2),
        }
        if aviso_reinversion:
            result["aviso_reinversion"] = aviso_reinversion
        return result

    @staticmethod
    def _calcular_coeficiente_abatimiento(fecha_adquisicion: date) -> float:
        """Calculate DT 9a abatimiento coefficient for properties.

        Reduction: 11.11% per year of holding that exceeds 2 years,
        counting from acquisition date to 19/01/2006, rounding up
        the number of years.

        Args:
            fecha_adquisicion: Property acquisition date (must be <= 31/12/1994).

        Returns:
            Reduction percentage (0-100). E.g., 55.55 means 55.55% of
            the gain is abated.
        """
        # Compute years of holding from acquisition to 19/01/2006
        # Round up to the next full year (per DT 9a, "por exceso")
        delta = FECHA_FIN_PERMANENCIA - fecha_adquisicion
        total_days = delta.days
        if total_days <= 0:
            return 0.0

        # Years rounded up (ceiling)
        anios_tenencia = math.ceil(total_days / 365.25)

        # Abatimiento only applies for years exceeding 2
        anios_reduccion = max(0, anios_tenencia - 2)

        coeficiente = anios_reduccion * COEF_ABATIMIENTO_INMUEBLES

        return min(coeficiente, 100.0)

    @staticmethod
    def _empty_result() -> Dict[str, Any]:
        """Return empty result when no sales provided."""
        return {
            "ganancia_bruta_total": 0.0,
            "abatimiento_total": 0.0,
            "exencion_reinversion_total": 0.0,
            "ganancia_neta_total": 0.0,
            "num_ventas": 0,
            "desglose": [],
        }
