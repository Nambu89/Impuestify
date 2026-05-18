"""
Tests for IRPF ahorro scale — Bug 98 fix (sesión 40).

Ley 7/2024 (vigente 1-ene-2025, AEAT INFORMA enero 2025) eleva el último
tramo de la escala estatal del ahorro (>300.000 EUR) del 14% al 15%.

Estos tests verifican:
1. Reproducción cifra a cifra del caso práctico AEAT (Manual Renta 2024,
   Cap. 15) — BLG 23.900 EUR Aragón, sólo la porción estatal y del ahorro
   estatal del ejemplo (la única que es independiente de la escala
   autonómica de Aragón cargada en BD).
2. Diferencia paramétrica 2024 vs 2025 para bases del ahorro >300.000 EUR:
   2024 último tramo 14%, 2025 último tramo 15%.
3. Que la escala estatal 2025 cargada en `populate_tax_parameters.py`
   tiene exactamente el tramo 5 al 15%.

Sin dependencias DB: el cálculo se prueba con `SavingsIncomeCalculator._apply_scale`
y las constantes del módulo `populate_tax_parameters`.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))


# Escala AEAT del ahorro 2024 (Manual Renta 2024, Art. 66.1 LIRPF redacción Ley 11/2020)
AHORRO_2024 = [
    {
        "tramo_num": 1,
        "base_hasta": 6000,
        "cuota_integra": 0,
        "resto_base": 6000,
        "tipo_aplicable": 9.5,
    },
    {
        "tramo_num": 2,
        "base_hasta": 50000,
        "cuota_integra": 570,
        "resto_base": 44000,
        "tipo_aplicable": 10.5,
    },
    {
        "tramo_num": 3,
        "base_hasta": 200000,
        "cuota_integra": 5190,
        "resto_base": 150000,
        "tipo_aplicable": 11.5,
    },
    {
        "tramo_num": 4,
        "base_hasta": 300000,
        "cuota_integra": 22440,
        "resto_base": 100000,
        "tipo_aplicable": 13.5,
    },
    {
        "tramo_num": 5,
        "base_hasta": 999999,
        "cuota_integra": 35940,
        "resto_base": 699999,
        "tipo_aplicable": 14,
    },
]

# Escala AEAT del ahorro 2025 (Ley 7/2024, AEAT INFORMA enero 2025)
AHORRO_2025 = [
    {
        "tramo_num": 1,
        "base_hasta": 6000,
        "cuota_integra": 0,
        "resto_base": 6000,
        "tipo_aplicable": 9.5,
    },
    {
        "tramo_num": 2,
        "base_hasta": 50000,
        "cuota_integra": 570,
        "resto_base": 44000,
        "tipo_aplicable": 10.5,
    },
    {
        "tramo_num": 3,
        "base_hasta": 200000,
        "cuota_integra": 5190,
        "resto_base": 150000,
        "tipo_aplicable": 11.5,
    },
    {
        "tramo_num": 4,
        "base_hasta": 300000,
        "cuota_integra": 22440,
        "resto_base": 100000,
        "tipo_aplicable": 13.5,
    },
    {
        "tramo_num": 5,
        "base_hasta": 999999,
        "cuota_integra": 35940,
        "resto_base": 699999,
        "tipo_aplicable": 15,
    },
]


# ─────────────────────────────────────────────────────────────
# 1. Caso AEAT — BLG 23.900 Aragón (validación analítica estatal)
# ─────────────────────────────────────────────────────────────


def test_caso_aeat_blg_23900_estatal_general():
    """
    Manual Práctico Renta 2024, Cap. 15 — caso práctico cuotas íntegras.
    Datos: BLG 23.900 EUR, BL ahorro 2.800 EUR, MPYF 5.550 EUR, Aragón.
    Resultado AEAT estatal:
      - Cuota íntegra estatal sobre BLG 23.900 = 2.667,75 EUR
      - MPYF 5.550 al 9,5% = 527,25 EUR
      - Cuota líquida estatal general = 2.140,50 EUR
      - Cuota íntegra ahorro estatal sobre 2.800 EUR (al 9,5%) = 266,00 EUR

    Reproducción analítica de la escala estatal general 2024:
      tramo 1 (12.450 al 9,5%) = 1.182,75
      tramo 2 (7.750 al 12%)   =   930,00
      tramo 3 (3.700 al 15%)   =   555,00
      total                    = 2.667,75 ✓
    """
    # Cuota íntegra estatal sobre BLG 23.900 — escala general estatal 2024
    blg = 23_900
    cuota_tramo1 = 12_450 * 0.095
    cuota_tramo2 = (20_200 - 12_450) * 0.12
    cuota_tramo3 = (blg - 20_200) * 0.15
    cuota_integra_estatal = cuota_tramo1 + cuota_tramo2 + cuota_tramo3
    assert round(cuota_integra_estatal, 2) == 2667.75

    # MPYF 5.550 al primer tramo estatal (9,5%)
    mpyf = 5_550
    cuota_mpyf = mpyf * 0.095
    assert round(cuota_mpyf, 2) == 527.25

    # Cuota líquida estatal general (Manual AEAT)
    cuota_liquida_estatal = cuota_integra_estatal - cuota_mpyf
    assert round(cuota_liquida_estatal, 2) == 2140.50

    # Cuota íntegra estatal del ahorro: 2.800 EUR cae en el tramo 1 al 9,5%
    bl_ahorro = 2_800
    cuota_ahorro_estatal = bl_ahorro * 0.095
    assert round(cuota_ahorro_estatal, 2) == 266.00


# ─────────────────────────────────────────────────────────────
# 2. Diferencia paramétrica 2024 vs 2025 — bases >300K EUR
# ─────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "base, cuota_2024_esperada, cuota_2025_esperada",
    [
        # Justo por encima del umbral (300.001) → 1 EUR al tipo del último tramo
        (300_001, 35_940 + 0.14, 35_940 + 0.15),
        # Exactamente 350.000 → 50.000 EUR al tipo del último tramo
        (350_000, 35_940 + 50_000 * 0.14, 35_940 + 50_000 * 0.15),
        # Caso estresado 1.000.000 → 700.000 EUR al tipo del último tramo
        (1_000_000, 35_940 + 700_000 * 0.14, 35_940 + 700_000 * 0.15),
    ],
)
def test_ahorro_2024_vs_2025_top_bracket_diferencia(base, cuota_2024_esperada, cuota_2025_esperada):
    """
    Para bases del ahorro >300.000 EUR la cuota debe diferir entre 2024 y 2025
    por la subida del último tramo del 14% al 15% (Ley 7/2024).
    """
    from app.utils.calculators.savings_income import SavingsIncomeCalculator

    cuota_2024, _ = SavingsIncomeCalculator._apply_scale(base, AHORRO_2024)
    cuota_2025, _ = SavingsIncomeCalculator._apply_scale(base, AHORRO_2025)

    assert cuota_2024 == pytest.approx(cuota_2024_esperada, abs=0.01)
    assert cuota_2025 == pytest.approx(cuota_2025_esperada, abs=0.01)
    # 2025 SIEMPRE > 2024 en el último tramo (porque sube 1 punto)
    assert cuota_2025 > cuota_2024
    # Diferencia exacta: 1% sobre el exceso por encima de 300.000
    exceso = base - 300_000
    assert (cuota_2025 - cuota_2024) == pytest.approx(exceso * 0.01, abs=0.01)


def test_ahorro_2024_vs_2025_misma_cuota_si_base_le_300k():
    """
    Para bases del ahorro <=300.000 EUR, la cuota debe ser idéntica en 2024 y 2025
    (los tramos 1-4 no han cambiado).
    """
    from app.utils.calculators.savings_income import SavingsIncomeCalculator

    for base in [2_800, 6_000, 50_000, 200_000, 300_000]:
        c_24, _ = SavingsIncomeCalculator._apply_scale(base, AHORRO_2024)
        c_25, _ = SavingsIncomeCalculator._apply_scale(base, AHORRO_2025)
        assert c_24 == pytest.approx(c_25, abs=0.001), (
            f"Cuota debería coincidir en 2024 y 2025 para base={base} "
            f"(2024={c_24}, 2025={c_25})"
        )


# ─────────────────────────────────────────────────────────────
# 3. La constante del seed populate_tax_parameters carga el 15%
# ─────────────────────────────────────────────────────────────


def test_populate_tax_parameters_ahorro_2025_top_bracket_es_15pct():
    """
    `populate_tax_parameters.py` debe definir la escala del ahorro 2025
    con el último tramo al 15% (Ley 7/2024), no heredar literalmente del 14% de 2024.
    """
    from scripts.populate_tax_parameters import (
        AHORRO_AUTONOMICO_2025,
        AHORRO_ESTATAL_2024,
        AHORRO_ESTATAL_2025,
    )

    # 2024 mantiene 14%
    assert AHORRO_ESTATAL_2024[-1][-1] == 14, "2024 debe seguir en 14% (campaña cerrada)"

    # 2025 sube a 15% en estatal y autonómico
    assert AHORRO_ESTATAL_2025[-1][-1] == 15, (
        "Bug 98: escala estatal del ahorro 2025 último tramo debe ser 15% "
        "(Ley 7/2024, AEAT INFORMA enero 2025)"
    )
    assert (
        AHORRO_AUTONOMICO_2025[-1][-1] == 15
    ), "Bug 98: escala autonómica complementaria del ahorro 2025 último tramo debe ser 15%"

    # Tramos 1-4 no han cambiado
    for tramo_2024, tramo_2025 in zip(AHORRO_ESTATAL_2024[:-1], AHORRO_ESTATAL_2025[:-1], strict=False):
        assert tramo_2024 == tramo_2025, (
            f"Tramos 1-4 no han cambiado entre 2024 y 2025 (Ley 7/2024 sólo afecta al tramo 5). "
            f"2024={tramo_2024}, 2025={tramo_2025}"
        )
