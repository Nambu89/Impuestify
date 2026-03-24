"""
MPYF Calculator — Mínimo Personal y Familiar (LIRPF arts. 57-61).

XSD Modelo 100 casillas: 0511-0520.

Calculates the personal and family minimum that reduces the tax liability.
Each CCAA may have different amounts (loaded from tax_parameters with
jurisdiction fallback to Estatal).
"""
from typing import Any, Dict, List, Optional

from app.utils.tax_parameter_repository import TaxParameterRepository


class MPYFCalculator:
    """Calculates the Personal and Family Minimum (LIRPF arts. 57-61)."""

    def __init__(self, repo: TaxParameterRepository):
        self._repo = repo

    async def calculate(
        self,
        *,
        jurisdiction: str = "Estatal",
        year: int = 2024,
        edad_contribuyente: int = 35,
        num_descendientes: int = 0,
        anios_nacimiento_desc: Optional[List[int]] = None,
        custodia_compartida: bool = False,
        num_ascendientes_65: int = 0,
        num_ascendientes_75: int = 0,
        discapacidad_contribuyente: int = 0,
        # --- XSD Gap: Discapacidad descendientes (Art. 60.2 LIRPF, casilla 0519) ---
        num_descendientes_discapacidad_33: int = 0,
        num_descendientes_discapacidad_65: int = 0,
        # --- XSD Gap: Discapacidad ascendientes (Art. 60.3 LIRPF, casilla 0520) ---
        num_ascendientes_discapacidad_33: int = 0,
        num_ascendientes_discapacidad_65: int = 0,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Calculate MPYF for both state and autonomous level.

        Args:
            jurisdiction: CCAA name (for autonomous-level MPYF).
            year: Fiscal year.
            edad_contribuyente: Taxpayer's age (affects minimum: >65, >75).
            num_descendientes: Number of dependent children.
            anios_nacimiento_desc: Birth years of children (for <3 years bonus).
            custodia_compartida: Shared custody divides child minimums by 2.
            num_ascendientes_65: Dependent ascendants >65.
            num_ascendientes_75: Dependent ascendants >75.
            discapacidad_contribuyente: Disability percentage (0, 33-64, 65+).

        Returns:
            Dict with mpyf_estatal and mpyf_autonomico amounts.
        """
        # State-level always needed
        est_params = await self._repo.get_params("mpyf", year, "Estatal")
        # Autonomous: use CCAA override if exists, else Estatal
        aut_params = await self._repo.get_with_fallback("mpyf", year, jurisdiction)

        mpyf_estatal = self._compute(
            est_params, edad_contribuyente, num_descendientes,
            anios_nacimiento_desc, custodia_compartida,
            num_ascendientes_65, num_ascendientes_75,
            discapacidad_contribuyente, year,
            num_descendientes_discapacidad_33, num_descendientes_discapacidad_65,
            num_ascendientes_discapacidad_33, num_ascendientes_discapacidad_65,
        )
        mpyf_autonomico = self._compute(
            aut_params, edad_contribuyente, num_descendientes,
            anios_nacimiento_desc, custodia_compartida,
            num_ascendientes_65, num_ascendientes_75,
            discapacidad_contribuyente, year,
            num_descendientes_discapacidad_33, num_descendientes_discapacidad_65,
            num_ascendientes_discapacidad_33, num_ascendientes_discapacidad_65,
        )

        return {
            "mpyf_estatal": round(mpyf_estatal, 2),
            "mpyf_autonomico": round(mpyf_autonomico, 2),
        }

    @staticmethod
    def _compute(
        params: Dict[str, float],
        edad: int,
        n_desc: int,
        anios: Optional[List[int]],
        custodia: bool,
        asc65: int,
        asc75: int,
        disc: int,
        year: int,
        n_desc_disc_33: int = 0,
        n_desc_disc_65: int = 0,
        n_asc_disc_33: int = 0,
        n_asc_disc_65: int = 0,
    ) -> float:
        """Compute total MPYF from a set of parameter amounts."""
        total = 0.0

        # Taxpayer minimum (art. 57)
        if edad >= 75:
            total += params.get("contribuyente_75", 0)
        elif edad >= 65:
            total += params.get("contribuyente_65", 0)
        else:
            total += params.get("contribuyente", 0)

        # Descendants (art. 58)
        divisor = 2.0 if custodia else 1.0
        desc_keys = [
            "descendiente_1",
            "descendiente_2",
            "descendiente_3",
            "descendiente_4_plus",
        ]
        anios = anios or []
        for i in range(n_desc):
            key = desc_keys[min(i, 3)]
            total += params.get(key, 0) / divisor
            # Additional for children under 3 years old
            if i < len(anios) and (year - anios[i]) < 3:
                total += params.get("descendiente_menor_3", 0) / divisor

        # Ascendants (art. 59)
        total += asc75 * params.get("ascendiente_75", 0)
        total += asc65 * params.get("ascendiente_65", 0)

        # Disability of taxpayer (art. 60.1)
        if disc >= 65:
            total += params.get("discapacidad_65_plus", 0)
            total += params.get("gastos_asistencia", 0)
        elif disc >= 33:
            total += params.get("discapacidad_33_65", 0)

        # Disability of descendants (art. 60.2, casilla 0519)
        # 33-64%: 3,000 EUR per descendant; 65%+: 9,000 + 3,000 gastos asistencia
        minimo_discapacidad_desc = 0
        minimo_discapacidad_desc += n_desc_disc_33 * params.get("discapacidad_33_65", 3000)
        minimo_discapacidad_desc += n_desc_disc_65 * (
            params.get("discapacidad_65_plus", 9000)
            + params.get("gastos_asistencia", 3000)
        )
        total += minimo_discapacidad_desc

        # Disability of ascendants (art. 60.3, casilla 0520)
        # Same amounts as descendants
        minimo_discapacidad_asc = 0
        minimo_discapacidad_asc += n_asc_disc_33 * params.get("discapacidad_33_65", 3000)
        minimo_discapacidad_asc += n_asc_disc_65 * (
            params.get("discapacidad_65_plus", 9000)
            + params.get("gastos_asistencia", 3000)
        )
        total += minimo_discapacidad_asc

        return total
