"""Tests Ley 7/2024 — Modelo 200 IS ejercicio 2025+.

Auditoria: docs/audits/modelo_200_validation_2026-05.md (bugs H1-H6).
Cubre los 6 ALTA cuando el caller pasa explicitamente ejercicio=2025+.
"""

import pytest

from app.utils.is_simulator import ISInput, ISSimulator

# H1 — Microempresa 17/20 (Ley 7/2024 Disp. Final 8a)


def test_h1_microempresa_2025_17_20():
    r = ISSimulator.calculate(
        ISInput(
            resultado_contable=100_000,
            facturacion_anual=800_000,
            territorio="Madrid",
            ejercicio=2025,
        )
    )
    # 50k al 17% = 8500 + 50k al 20% = 10000 → cuota_integra = 18500
    assert r.cuota_integra == 18_500


def test_h1_microempresa_2024_sigue_23_25():
    """2024 mantiene esquema antiguo 23/25 (sin Ley 7/2024)."""
    r = ISSimulator.calculate(
        ISInput(
            resultado_contable=100_000,
            facturacion_anual=800_000,
            territorio="Madrid",
            ejercicio=2024,
        )
    )
    # 50k al 23% = 11500 + 50k al 25% = 12500 → cuota_integra = 24000
    assert r.cuota_integra == 24_000


# H2 — Nueva creacion 15% PLANO Art. 29.1 LIS (Ley 7/2024)


def test_h2_nueva_creacion_2025_15_plano():
    r = ISSimulator.calculate(
        ISInput(
            resultado_contable=100_000,
            tipo_entidad="nueva_creacion",
            ejercicios_con_bi_positiva=1,
            territorio="Madrid",
            ejercicio=2025,
        )
    )
    # 100k al 15% PLANO = 15000 (NO 15/20 antiguo)
    assert r.cuota_integra == 15_000


def test_h2_nueva_creacion_2024_sigue_15_20():
    r = ISSimulator.calculate(
        ISInput(
            resultado_contable=100_000,
            tipo_entidad="nueva_creacion",
            ejercicios_con_bi_positiva=1,
            territorio="Madrid",
            ejercicio=2024,
        )
    )
    # 50k×15% + 50k×20% = 17500
    assert r.cuota_integra == 17_500


# H3 — Reserva capitalizacion 20-30% (Ley 7/2024 Art. 25 LIS)


def test_h3_reserva_capitalizacion_2025_20pct_base():
    r = ISSimulator.calculate(
        ISInput(
            resultado_contable=100_000,
            incremento_ffpp=50_000,
            territorio="Madrid",
            ejercicio=2025,
        )
    )
    # 50k * 20% = 10000, limitado a 20% BI previa = 20000 → reserva = 10000
    # BI = 100000 - 10000 = 90000
    assert r.reserva_capitalizacion == 10_000
    assert r.base_imponible == 90_000


def test_h3_reserva_capitalizacion_2025_30pct_si_plantilla_10():
    r = ISSimulator.calculate(
        ISInput(
            resultado_contable=100_000,
            incremento_ffpp=50_000,
            incremento_plantilla_pct=12.0,
            territorio="Madrid",
            ejercicio=2025,
        )
    )
    # plantilla>=10% → reserva 30% del incremento = 15000
    # limite 20% BI previa = 20000 → reserva = 15000
    # BI = 85000
    assert r.reserva_capitalizacion == 15_000
    assert r.base_imponible == 85_000


# H4 — BIN tramo 50% para INCN >= 60M (Art. 26 LIS)


def test_h4_bin_limite_50pct_grandes():
    """INCN >= 60M → limite BIN 50% base previa."""
    r = ISSimulator.calculate(
        ISInput(
            resultado_contable=100_000,
            bins_pendientes=100_000,
            facturacion_anual=70_000_000,
            territorio="Madrid",
            ejercicio=2025,
        )
    )
    # 50% de 100k = 50k
    assert r.compensacion_bins == 50_000
    assert r.base_imponible == 50_000


# H5 — Donativos 40% Sociedades (Art. 20 Ley 49/2002, NO 35% IRPF)


def test_h5_donativos_40pct_sociedades_2025():
    r = ISSimulator.calculate(
        ISInput(
            resultado_contable=200_000,
            donativos=10_000,
            territorio="Madrid",
            ejercicio=2025,
        )
    )
    # 10000 * 40% = 4000 (NO 3500 que seria 35%)
    assert r.deducciones_detalle["donativos"] == 4_000


def test_h5_donativos_40pct_sociedades_2024():
    """En 2024 tambien aplica 40% Sociedades (no 35% IRPF)."""
    r = ISSimulator.calculate(
        ISInput(
            resultado_contable=200_000,
            donativos=10_000,
            territorio="Madrid",
            ejercicio=2024,
        )
    )
    assert r.deducciones_detalle["donativos"] == 4_000


# H6 — Microempresa Navarra 19% (LF 26/2016 vigente desde 2025)


def test_h6_navarra_microempresa_2025_19pct():
    r = ISSimulator.calculate(
        ISInput(
            resultado_contable=100_000,
            facturacion_anual=800_000,
            territorio="Navarra",
            ejercicio=2025,
        )
    )
    # 100k al 19% = 19000
    assert r.cuota_integra == 19_000


def test_h6_navarra_microempresa_2024_sigue_23_28():
    r = ISSimulator.calculate(
        ISInput(
            resultado_contable=100_000,
            facturacion_anual=800_000,
            territorio="Navarra",
            ejercicio=2024,
        )
    )
    # 50k×23% + 50k×28% = 11500 + 14000 = 25500
    assert r.cuota_integra == 25_500


# Gipuzkoa NF 1/2025 — 19/17/15


def test_gipuzkoa_2025_general_19pct():
    r = ISSimulator.calculate(
        ISInput(
            resultado_contable=100_000,
            territorio="Gipuzkoa",
            ejercicio=2025,
        )
    )
    # NF 1/2025 → 19% general
    assert r.cuota_integra == 19_000
