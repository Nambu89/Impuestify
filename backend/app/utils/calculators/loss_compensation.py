"""
Loss Compensation Calculator — Compensacion de perdidas de ejercicios anteriores.

Art. 48 LIRPF: Base imponible general (GP no derivadas de transmisiones).
Art. 49 LIRPF: Base del ahorro (GP ahorro + RCM).

Plazo: 4 anos. Cross-compensation limit: 25% of the positive balance.
"""
from typing import Dict


# Maximum number of prior years for loss carryforward (Art. 48-49 LIRPF)
MAX_CARRYFORWARD_YEARS = 4


class LossCompensationCalculator:
    """Compensacion de perdidas de ejercicios anteriores (Art. 48-49 LIRPF).

    Two separate mechanisms:

    A) BASE DEL AHORRO (Art. 49):
       - Saldos negativos GP ahorro de 4 anos anteriores
       - Saldos negativos RCM ahorro de 4 anos anteriores
       - Each compensates first against its own type, then cross at 25% limit

    B) BASE GENERAL (Art. 48):
       - Saldos negativos GP general (no derivadas de transmisiones) de 4 anos anteriores
       - Compensate against GP general positivas, then cross at 25% of rendimientos

    Plazo: 4 anos (for year 2024: losses from 2020-2023 are valid)
    Cross-compensation limit: 25% of the positive balance in the other category
    """

    def _filter_valid_losses(
        self,
        perdidas: Dict[int, float],
        year: int,
    ) -> Dict[int, float]:
        """Filter out losses older than MAX_CARRYFORWARD_YEARS and ensure positive values."""
        min_year = year - MAX_CARRYFORWARD_YEARS
        return {
            y: abs(v)
            for y, v in perdidas.items()
            if y >= min_year and y < year and v != 0
        }

    def compensar_ahorro(
        self,
        *,
        rcm_ejercicio: float,
        gp_ahorro_ejercicio: float,
        perdidas_gp_anteriores: Dict[int, float] = None,
        perdidas_rcm_anteriores: Dict[int, float] = None,
        year: int = 2024,
    ) -> Dict:
        """Compensate prior year savings losses against current year balances (Art. 49).

        This method receives the ALREADY Phase-1-compensated saldos (after current year
        cross-compensation). It applies Phase 2: prior year loss carryforward.

        Args:
            rcm_ejercicio: Net RCM after Phase 1 (can be negative).
            gp_ahorro_ejercicio: Net GP ahorro after Phase 1 (can be negative).
            perdidas_gp_anteriores: Prior GP ahorro losses by year {2020: 500, ...}.
                Values should be positive (they represent loss amounts).
            perdidas_rcm_anteriores: Prior RCM losses by year {2020: 200, ...}.
            year: Current fiscal year.

        Returns:
            Dict with compensated balances, consumed amounts, and remaining losses.
        """
        perdidas_gp = self._filter_valid_losses(perdidas_gp_anteriores or {}, year)
        perdidas_rcm = self._filter_valid_losses(perdidas_rcm_anteriores or {}, year)

        gp_consumidas: Dict[int, float] = {}
        rcm_consumidas: Dict[int, float] = {}

        # Working copies
        gp = gp_ahorro_ejercicio
        rcm = rcm_ejercicio

        # --- Phase 2a: Prior GP losses → compensate against GP positivas, then cross at 25% RCM ---
        for y in sorted(perdidas_gp.keys()):
            remaining_loss = perdidas_gp[y]
            consumed = 0.0

            # First: against GP positivas (unlimited)
            if gp > 0 and remaining_loss > 0:
                comp = min(remaining_loss, gp)
                gp -= comp
                remaining_loss -= comp
                consumed += comp

            # Then: cross-compensate against RCM at 25% limit
            if rcm > 0 and remaining_loss > 0:
                max_cross = rcm * 0.25
                comp = min(remaining_loss, max_cross)
                rcm -= comp
                remaining_loss -= comp
                consumed += comp

            if consumed > 0:
                gp_consumidas[y] = round(consumed, 2)
            perdidas_gp[y] = remaining_loss

        # --- Phase 2b: Prior RCM losses → compensate against RCM positivas, then cross at 25% GP ---
        for y in sorted(perdidas_rcm.keys()):
            remaining_loss = perdidas_rcm[y]
            consumed = 0.0

            # First: against RCM positivas (unlimited)
            if rcm > 0 and remaining_loss > 0:
                comp = min(remaining_loss, rcm)
                rcm -= comp
                remaining_loss -= comp
                consumed += comp

            # Then: cross-compensate against GP at 25% limit
            if gp > 0 and remaining_loss > 0:
                max_cross = gp * 0.25
                comp = min(remaining_loss, max_cross)
                gp -= comp
                remaining_loss -= comp
                consumed += comp

            if consumed > 0:
                rcm_consumidas[y] = round(consumed, 2)
            perdidas_rcm[y] = remaining_loss

        # Track current year negative balances that carry forward
        gp_negativo_pendiente = abs(gp) if gp < 0 else 0.0
        rcm_negativo_pendiente = abs(rcm) if rcm < 0 else 0.0

        # Remaining losses for future years
        gp_remanentes = {y: round(v, 2) for y, v in perdidas_gp.items() if v > 0.01}
        rcm_remanentes = {y: round(v, 2) for y, v in perdidas_rcm.items() if v > 0.01}

        # Final values (floor at 0 for base del ahorro computation)
        rcm_final = max(0.0, rcm)
        gp_final = max(0.0, gp)

        return {
            "base_ahorro_compensada": round(rcm_final + gp_final, 2),
            "rcm_final": round(rcm_final, 2),
            "gp_ahorro_final": round(gp_final, 2),
            "gp_consumidas_por_ano": gp_consumidas,
            "rcm_consumidas_por_ano": rcm_consumidas,
            "gp_remanentes": gp_remanentes,
            "rcm_remanentes": rcm_remanentes,
            "gp_negativo_ejercicio_pendiente": round(gp_negativo_pendiente, 2),
            "rcm_negativo_ejercicio_pendiente": round(rcm_negativo_pendiente, 2),
        }

    def compensar_general(
        self,
        *,
        rendimientos_netos: float,
        gp_general_ejercicio: float,
        perdidas_gp_general_anteriores: Dict[int, float] = None,
        year: int = 2024,
    ) -> Dict:
        """Compensate prior year general base losses (Art. 48 LIRPF).

        Handles both current year cross-compensation and prior year carryforward
        for ganancias patrimoniales no derivadas de transmisiones (base general).

        Args:
            rendimientos_netos: Sum of all rendimientos + imputaciones (positive).
            gp_general_ejercicio: Net GP general no derivadas de transmisiones
                (can be negative).
            perdidas_gp_general_anteriores: Prior GP general losses by year.
            year: Current fiscal year.

        Returns:
            Dict with compensated base general and tracking info.
        """
        perdidas_gp = self._filter_valid_losses(
            perdidas_gp_general_anteriores or {}, year
        )

        rend = rendimientos_netos
        gp = gp_general_ejercicio

        # --- Phase 1: Current year cross-compensation ---
        compensacion_cruzada_ejercicio = 0.0
        if gp < 0 and rend > 0:
            # GP negative: compensate against 25% of rendimientos
            max_comp = rend * 0.25
            comp = min(abs(gp), max_comp)
            gp += comp  # becomes less negative or 0
            rend -= comp
            compensacion_cruzada_ejercicio = comp
        elif rend < 0 and gp > 0:
            # Rendimientos negative: compensate against GP (no percentage limit)
            comp = min(abs(rend), gp)
            rend += comp
            gp -= comp
            compensacion_cruzada_ejercicio = comp

        # --- Phase 2: Prior year GP losses ---
        gp_consumidas: Dict[int, float] = {}

        for y in sorted(perdidas_gp.keys()):
            remaining_loss = perdidas_gp[y]
            consumed = 0.0

            # First: against GP positivas (unlimited)
            if gp > 0 and remaining_loss > 0:
                comp = min(remaining_loss, gp)
                gp -= comp
                remaining_loss -= comp
                consumed += comp

            # Then: cross-compensate against rendimientos at 25%
            if rend > 0 and remaining_loss > 0:
                max_cross = rend * 0.25
                comp = min(remaining_loss, max_cross)
                rend -= comp
                remaining_loss -= comp
                consumed += comp

            if consumed > 0:
                gp_consumidas[y] = round(consumed, 2)
            perdidas_gp[y] = remaining_loss

        # Current year GP negative that carries forward
        gp_negativo_pendiente = abs(gp) if gp < 0 else 0.0

        gp_remanentes = {y: round(v, 2) for y, v in perdidas_gp.items() if v > 0.01}

        rend_final = max(0.0, rend)
        gp_final = max(0.0, gp)

        return {
            "base_general_compensada": round(rend_final + gp_final, 2),
            "rendimientos_finales": round(rend_final, 2),
            "gp_general_final": round(gp_final, 2),
            "compensacion_cruzada_ejercicio": round(compensacion_cruzada_ejercicio, 2),
            "gp_consumidas_por_ano": gp_consumidas,
            "gp_remanentes": gp_remanentes,
            "gp_negativo_ejercicio_pendiente": round(gp_negativo_pendiente, 2),
        }
