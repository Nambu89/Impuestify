"""
Tests for ISD (Impuesto sobre Sucesiones y Donaciones) — 21/21 CCAA coverage.

Verifies the 12 newly added CCAA bonificaciones plus a final coverage check
ensuring all 21 territories (15 CCAA + 4 forales + Ceuta + Melilla) are handled.
"""
import pytest
from app.tools.isd_calculator_tool import calculate_isd, _normalize_ccaa


# ---------------------------------------------------------------------------
# 1. Galicia — 99% sucesiones <= 400K, 99% donaciones <= 200K
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_galicia_sucesion_grupo_ii_bajo_400k():
    """Galicia: 99% bonificacion sucesiones Grupos I-II si base <= 400.000 EUR."""
    result = await calculate_isd(
        amount=300_000,
        operation_type="sucesion",
        relationship="grupo_ii",
        ccaa="Galicia",
    )
    assert result["success"] is True
    pcts = [b["porcentaje"] for b in result["bonificaciones_ccaa"]]
    assert 99.0 in pcts
    assert result["cuota_a_pagar"] < result["cuota_tributaria"] * 0.02


@pytest.mark.asyncio
async def test_galicia_sucesion_grupo_ii_sobre_400k():
    """Galicia: sin bonificacion 99% si herencia > 400.000 EUR."""
    result = await calculate_isd(
        amount=500_000,
        operation_type="sucesion",
        relationship="grupo_ii",
        ccaa="Galicia",
    )
    assert result["success"] is True
    pcts = [b["porcentaje"] for b in result["bonificaciones_ccaa"]]
    assert 99.0 not in pcts


@pytest.mark.asyncio
async def test_galicia_donacion_bajo_200k():
    """Galicia: 99% bonificacion donaciones Grupos I-II si importe <= 200.000 EUR."""
    result = await calculate_isd(
        amount=150_000,
        operation_type="donacion",
        relationship="grupo_ii",
        ccaa="Galicia",
    )
    assert result["success"] is True
    pcts = [b["porcentaje"] for b in result["bonificaciones_ccaa"]]
    assert 99.0 in pcts


# ---------------------------------------------------------------------------
# 2. Castilla y Leon — 99% sucesiones y donaciones Grupos I-II
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_castilla_y_leon_sucesion_grupo_ii():
    """CyL: 99% bonificacion sucesiones Grupos I-II sin limite de base."""
    result = await calculate_isd(
        amount=500_000,
        operation_type="sucesion",
        relationship="grupo_ii",
        ccaa="Castilla y Leon",
    )
    assert result["success"] is True
    pcts = [b["porcentaje"] for b in result["bonificaciones_ccaa"]]
    assert 99.0 in pcts
    assert result["cuota_a_pagar"] < result["cuota_tributaria"] * 0.02


@pytest.mark.asyncio
async def test_castilla_y_leon_donacion_grupo_i():
    """CyL: 99% bonificacion tambien en donaciones Grupos I-II."""
    result = await calculate_isd(
        amount=100_000,
        operation_type="donacion",
        relationship="grupo_i",
        ccaa="Castilla y León",
        recipient_age=18,
    )
    assert result["success"] is True
    pcts = [b["porcentaje"] for b in result["bonificaciones_ccaa"]]
    assert 99.0 in pcts


# ---------------------------------------------------------------------------
# 3. Castilla-La Mancha — 100% sucesiones y donaciones Grupos I-II (2024+)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_castilla_la_mancha_sucesion_grupo_ii():
    """CLM: 100% bonificacion sucesiones Grupos I-II desde 2024."""
    result = await calculate_isd(
        amount=400_000,
        operation_type="sucesion",
        relationship="grupo_ii",
        ccaa="Castilla-La Mancha",
    )
    assert result["success"] is True
    pcts = [b["porcentaje"] for b in result["bonificaciones_ccaa"]]
    assert 100.0 in pcts
    assert result["cuota_a_pagar"] == pytest.approx(0.0, abs=0.02)


@pytest.mark.asyncio
async def test_castilla_la_mancha_donacion_grupo_ii():
    """CLM: 100% bonificacion donaciones Grupos I-II."""
    result = await calculate_isd(
        amount=80_000,
        operation_type="donacion",
        relationship="grupo_ii",
        ccaa="Castilla La Mancha",
    )
    assert result["success"] is True
    pcts = [b["porcentaje"] for b in result["bonificaciones_ccaa"]]
    assert 100.0 in pcts


# ---------------------------------------------------------------------------
# 4. Extremadura — 99% sucesiones Y donaciones con limites por grupo
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_extremadura_sucesion_grupo_i_bajo_limite():
    """Extremadura: 99% sucesiones Grupo I si importe <= 175.000 EUR."""
    result = await calculate_isd(
        amount=150_000,
        operation_type="sucesion",
        relationship="grupo_i",
        ccaa="Extremadura",
        recipient_age=18,
    )
    assert result["success"] is True
    pcts = [b["porcentaje"] for b in result["bonificaciones_ccaa"]]
    assert 99.0 in pcts


@pytest.mark.asyncio
async def test_extremadura_sucesion_grupo_ii_bajo_limite():
    """Extremadura: 99% sucesiones Grupo II (conyuge) si importe <= 325.000 EUR."""
    result = await calculate_isd(
        amount=300_000,
        operation_type="sucesion",
        relationship="grupo_ii",
        ccaa="Extremadura",
    )
    assert result["success"] is True
    pcts = [b["porcentaje"] for b in result["bonificaciones_ccaa"]]
    assert 99.0 in pcts


@pytest.mark.asyncio
async def test_extremadura_sucesion_grupo_ii_sobre_limite():
    """Extremadura: sin bonificacion 99% si herencia conyuge > 325.000 EUR."""
    result = await calculate_isd(
        amount=400_000,
        operation_type="sucesion",
        relationship="grupo_ii",
        ccaa="Extremadura",
    )
    assert result["success"] is True
    pcts = [b["porcentaje"] for b in result["bonificaciones_ccaa"]]
    assert 99.0 not in pcts


@pytest.mark.asyncio
async def test_extremadura_donacion_grupo_ii_bajo_limite():
    """Extremadura: 99% donaciones Grupo II si importe <= 325.000 EUR (DL 1/2018 Art. 15)."""
    result = await calculate_isd(
        amount=200_000,
        operation_type="donacion",
        relationship="grupo_ii",
        ccaa="Extremadura",
    )
    assert result["success"] is True
    pcts = [b["porcentaje"] for b in result["bonificaciones_ccaa"]]
    assert 99.0 in pcts
    assert result["cuota_a_pagar"] < result["cuota_tributaria"] * 0.02


@pytest.mark.asyncio
async def test_extremadura_donacion_grupo_i_bajo_limite():
    """Extremadura: 99% donaciones Grupo I si importe <= 175.000 EUR."""
    result = await calculate_isd(
        amount=100_000,
        operation_type="donacion",
        relationship="grupo_i",
        ccaa="Extremadura",
        recipient_age=15,
    )
    assert result["success"] is True
    pcts = [b["porcentaje"] for b in result["bonificaciones_ccaa"]]
    assert 99.0 in pcts


@pytest.mark.asyncio
async def test_extremadura_donacion_grupo_ii_sobre_limite():
    """Extremadura: sin bonificacion 99% donacion Grupo II > 325.000 EUR."""
    result = await calculate_isd(
        amount=400_000,
        operation_type="donacion",
        relationship="grupo_ii",
        ccaa="Extremadura",
    )
    assert result["success"] is True
    pcts = [b["porcentaje"] for b in result["bonificaciones_ccaa"]]
    assert 99.0 not in pcts


# ---------------------------------------------------------------------------
# 5. Murcia — 99% sucesiones y donaciones Grupos I-II
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_murcia_sucesion_grupo_ii():
    """Murcia: 99% bonificacion sucesiones Grupos I-II."""
    result = await calculate_isd(
        amount=200_000,
        operation_type="sucesion",
        relationship="grupo_ii",
        ccaa="Murcia",
    )
    assert result["success"] is True
    pcts = [b["porcentaje"] for b in result["bonificaciones_ccaa"]]
    assert 99.0 in pcts


@pytest.mark.asyncio
async def test_murcia_donacion_grupo_i():
    """Murcia: 99% bonificacion donaciones Grupo I."""
    result = await calculate_isd(
        amount=60_000,
        operation_type="donacion",
        relationship="grupo_i",
        ccaa="Murcia",
        recipient_age=15,
    )
    assert result["success"] is True
    pcts = [b["porcentaje"] for b in result["bonificaciones_ccaa"]]
    assert 99.0 in pcts


# ---------------------------------------------------------------------------
# 6. Canarias — 99.9% sucesiones y donaciones Grupos I-II
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_canarias_sucesion_grupo_ii():
    """Canarias: 99.9% bonificacion sucesiones Grupos I-II."""
    result = await calculate_isd(
        amount=200_000,
        operation_type="sucesion",
        relationship="grupo_ii",
        ccaa="Canarias",
    )
    assert result["success"] is True
    pcts = [b["porcentaje"] for b in result["bonificaciones_ccaa"]]
    assert 99.9 in pcts
    # Cuota a pagar should be ~0.1% of cuota_tributaria
    assert result["cuota_a_pagar"] < result["cuota_tributaria"] * 0.002


@pytest.mark.asyncio
async def test_canarias_donacion_grupo_i():
    """Canarias: 99.9% bonificacion donaciones Grupo I."""
    result = await calculate_isd(
        amount=100_000,
        operation_type="donacion",
        relationship="grupo_i",
        ccaa="Canarias",
        recipient_age=16,
    )
    assert result["success"] is True
    pcts = [b["porcentaje"] for b in result["bonificaciones_ccaa"]]
    assert 99.9 in pcts


# ---------------------------------------------------------------------------
# 7. Asturias — escalonada: 100% <=300K, 95% <=450K, 90% <=600K (Grupo II)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_asturias_grupo_i_100pct():
    """Asturias: 100% bonificacion Grupo I (menores 21)."""
    result = await calculate_isd(
        amount=200_000,
        operation_type="sucesion",
        relationship="grupo_i",
        ccaa="Asturias",
        recipient_age=15,
    )
    assert result["success"] is True
    pcts = [b["porcentaje"] for b in result["bonificaciones_ccaa"]]
    assert 100.0 in pcts
    assert result["cuota_a_pagar"] == pytest.approx(0.0, abs=0.02)


@pytest.mark.asyncio
async def test_asturias_grupo_ii_sucesion_baja():
    """Asturias: base_liquidable <= 300K -> 100% bonificacion Grupo II sucesiones."""
    result = await calculate_isd(
        amount=200_000,
        operation_type="sucesion",
        relationship="grupo_ii",
        ccaa="Asturias",
    )
    assert result["success"] is True
    # base_liquidable = 200.000 - 15.956,87 = 184.043,13 <= 300K
    pcts = [b["porcentaje"] for b in result["bonificaciones_ccaa"]]
    assert 100.0 in pcts


@pytest.mark.asyncio
async def test_asturias_grupo_ii_sucesion_media():
    """Asturias: base_liquidable 300K-450K -> 95% bonificacion Grupo II."""
    result = await calculate_isd(
        amount=350_000,
        operation_type="sucesion",
        relationship="grupo_ii",
        ccaa="Asturias",
    )
    assert result["success"] is True
    # base_liquidable = 350.000 - 15.956,87 = 334.043,13 => 300K < x <= 450K
    pcts = [b["porcentaje"] for b in result["bonificaciones_ccaa"]]
    assert 95.0 in pcts


@pytest.mark.asyncio
async def test_asturias_grupo_ii_donacion():
    """Asturias: 95% bonificacion donaciones Grupo II (DL 2/2014)."""
    result = await calculate_isd(
        amount=150_000,
        operation_type="donacion",
        relationship="grupo_ii",
        ccaa="Asturias",
    )
    assert result["success"] is True
    pcts = [b["porcentaje"] for b in result["bonificaciones_ccaa"]]
    assert 95.0 in pcts
    assert result["cuota_a_pagar"] < result["cuota_tributaria"] * 0.06


@pytest.mark.asyncio
async def test_asturias_grupo_i_donacion():
    """Asturias: 100% bonificacion donaciones Grupo I (same as sucesion)."""
    result = await calculate_isd(
        amount=100_000,
        operation_type="donacion",
        relationship="grupo_i",
        ccaa="Asturias",
        recipient_age=15,
    )
    assert result["success"] is True
    pcts = [b["porcentaje"] for b in result["bonificaciones_ccaa"]]
    assert 100.0 in pcts


# ---------------------------------------------------------------------------
# 8. Cantabria — 100% sucesiones y donaciones Grupos I-II (2024+)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_cantabria_sucesion_grupo_ii():
    """Cantabria: 100% bonificacion sucesiones Grupos I-II desde 2024."""
    result = await calculate_isd(
        amount=250_000,
        operation_type="sucesion",
        relationship="grupo_ii",
        ccaa="Cantabria",
    )
    assert result["success"] is True
    pcts = [b["porcentaje"] for b in result["bonificaciones_ccaa"]]
    assert 100.0 in pcts
    assert result["cuota_a_pagar"] == pytest.approx(0.0, abs=0.02)


@pytest.mark.asyncio
async def test_cantabria_donacion_grupo_ii():
    """Cantabria: 100% bonificacion donaciones Grupos I-II."""
    result = await calculate_isd(
        amount=80_000,
        operation_type="donacion",
        relationship="grupo_ii",
        ccaa="Cantabria",
    )
    assert result["success"] is True
    pcts = [b["porcentaje"] for b in result["bonificaciones_ccaa"]]
    assert 100.0 in pcts


# ---------------------------------------------------------------------------
# 9. La Rioja — 99% sucesiones y donaciones Grupos I-II
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_la_rioja_sucesion_grupo_ii():
    """La Rioja: 99% bonificacion sucesiones Grupos I-II."""
    result = await calculate_isd(
        amount=200_000,
        operation_type="sucesion",
        relationship="grupo_ii",
        ccaa="La Rioja",
    )
    assert result["success"] is True
    pcts = [b["porcentaje"] for b in result["bonificaciones_ccaa"]]
    assert 99.0 in pcts


@pytest.mark.asyncio
async def test_la_rioja_donacion_grupo_i():
    """La Rioja: 99% bonificacion donaciones Grupo I."""
    result = await calculate_isd(
        amount=50_000,
        operation_type="donacion",
        relationship="grupo_i",
        ccaa="Rioja",  # test alias
        recipient_age=19,
    )
    assert result["success"] is True
    pcts = [b["porcentaje"] for b in result["bonificaciones_ccaa"]]
    assert 99.0 in pcts


# ---------------------------------------------------------------------------
# 10. Baleares — 99% sucesiones <= 3M, 75% donaciones
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_baleares_sucesion_grupo_ii():
    """Baleares: 99% bonificacion sucesiones Grupos I-II si base <= 3M EUR."""
    result = await calculate_isd(
        amount=500_000,
        operation_type="sucesion",
        relationship="grupo_ii",
        ccaa="Baleares",
    )
    assert result["success"] is True
    pcts = [b["porcentaje"] for b in result["bonificaciones_ccaa"]]
    assert 99.0 in pcts


@pytest.mark.asyncio
async def test_baleares_donacion_grupo_ii():
    """Baleares: 75% bonificacion donaciones Grupos I-II."""
    result = await calculate_isd(
        amount=100_000,
        operation_type="donacion",
        relationship="grupo_ii",
        ccaa="Illes Balears",  # test alias
    )
    assert result["success"] is True
    pcts = [b["porcentaje"] for b in result["bonificaciones_ccaa"]]
    assert 75.0 in pcts


# ---------------------------------------------------------------------------
# 11. Ceuta — 50% bonificacion general (Art. 23 bis)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_ceuta_sucesion_grupo_ii():
    """Ceuta: 50% bonificacion general Art. 23 bis Ley 29/1987."""
    result = await calculate_isd(
        amount=200_000,
        operation_type="sucesion",
        relationship="grupo_ii",
        ccaa="Ceuta",
    )
    assert result["success"] is True
    pcts = [b["porcentaje"] for b in result["bonificaciones_ccaa"]]
    assert 50.0 in pcts
    # Cuota a pagar = 50% of cuota tributaria
    assert result["cuota_a_pagar"] == pytest.approx(
        result["cuota_tributaria"] * 0.50, abs=1.0
    )


@pytest.mark.asyncio
async def test_ceuta_donacion_grupo_iv():
    """Ceuta: 50% bonificacion aplica incluso a grupo IV (extraños)."""
    result = await calculate_isd(
        amount=50_000,
        operation_type="donacion",
        relationship="grupo_iv",
        ccaa="Ceuta",
    )
    assert result["success"] is True
    pcts = [b["porcentaje"] for b in result["bonificaciones_ccaa"]]
    assert 50.0 in pcts


# ---------------------------------------------------------------------------
# 12. Melilla — 50% bonificacion general (Art. 23 bis)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_melilla_sucesion_grupo_ii():
    """Melilla: 50% bonificacion general Art. 23 bis Ley 29/1987."""
    result = await calculate_isd(
        amount=200_000,
        operation_type="sucesion",
        relationship="grupo_ii",
        ccaa="Melilla",
    )
    assert result["success"] is True
    pcts = [b["porcentaje"] for b in result["bonificaciones_ccaa"]]
    assert 50.0 in pcts


@pytest.mark.asyncio
async def test_melilla_donacion_grupo_iii():
    """Melilla: 50% bonificacion aplica a grupo III (hermanos, sobrinos)."""
    result = await calculate_isd(
        amount=80_000,
        operation_type="donacion",
        relationship="grupo_iii",
        ccaa="Melilla",
    )
    assert result["success"] is True
    pcts = [b["porcentaje"] for b in result["bonificaciones_ccaa"]]
    assert 50.0 in pcts


# ---------------------------------------------------------------------------
# Final coverage test: all 21 territories produce valid results
# ---------------------------------------------------------------------------

ALL_CCAA = [
    "Madrid", "Andalucía", "Cataluña", "Valencia", "Aragón",
    "Araba", "Bizkaia", "Gipuzkoa", "Navarra",
    "Galicia", "Castilla y León", "Castilla-La Mancha", "Extremadura",
    "Murcia", "Canarias", "Asturias", "Cantabria", "La Rioja",
    "Baleares", "Ceuta", "Melilla",
]


@pytest.mark.asyncio
@pytest.mark.parametrize("ccaa", ALL_CCAA)
async def test_cobertura_21_ccaa_sucesion(ccaa):
    """Smoke test: sucesion grupo_ii en cada una de las 21 CCAA produce resultado valido."""
    result = await calculate_isd(
        amount=200_000,
        operation_type="sucesion",
        relationship="grupo_ii",
        ccaa=ccaa,
    )
    assert result["success"] is True, f"Failed for {ccaa}"
    assert result["cuota_a_pagar"] >= 0.0, f"Negative cuota for {ccaa}"
    assert "formatted_response" in result
    assert len(result["formatted_response"]) > 50


@pytest.mark.asyncio
@pytest.mark.parametrize("ccaa", ALL_CCAA)
async def test_cobertura_21_ccaa_donacion(ccaa):
    """Smoke test: donacion grupo_ii en cada una de las 21 CCAA produce resultado valido."""
    result = await calculate_isd(
        amount=100_000,
        operation_type="donacion",
        relationship="grupo_ii",
        ccaa=ccaa,
    )
    assert result["success"] is True, f"Failed for {ccaa}"
    assert result["cuota_a_pagar"] >= 0.0, f"Negative cuota for {ccaa}"


@pytest.mark.asyncio
async def test_todas_las_ccaa_tienen_bonificacion():
    """
    Verify that EVERY CCAA in the 21-territory list produces at least one
    bonificacion for sucesion grupo_ii (except the ones with specific limits
    that may not apply, like Extremadura > 325K or Galicia > 400K).
    Use a 100.000 EUR amount which is within all CCAA limits.
    """
    ccaa_sin_bonificacion_especifica = set()

    for ccaa in ALL_CCAA:
        result = await calculate_isd(
            amount=100_000,
            operation_type="sucesion",
            relationship="grupo_ii",
            ccaa=ccaa,
        )
        assert result["success"] is True
        if len(result["bonificaciones_ccaa"]) == 0:
            ccaa_sin_bonificacion_especifica.add(ccaa)

    # All 21 CCAA should have at least one bonificacion for 100K sucesion grupo_ii
    assert len(ccaa_sin_bonificacion_especifica) == 0, (
        f"CCAA sin bonificacion para 100K sucesion grupo_ii: {ccaa_sin_bonificacion_especifica}"
    )


@pytest.mark.asyncio
async def test_normativa_nueva_ccaa_incluida():
    """
    Verify that the normativa_aplicable field references the correct
    CCAA-specific legal framework for newly added territories.
    """
    test_cases = {
        "Galicia": "Galicia",
        "Castilla y León": "Castilla y León",
        "Castilla-La Mancha": "Castilla-La Mancha",
        "Extremadura": "Extremadura",
        "Murcia": "Murcia",
        "Canarias": "Canarias",
        "Asturias": "Asturias",
        "Cantabria": "Cantabria",
        "La Rioja": "La Rioja",
        "Baleares": "Balears",  # partial match for "Illes Balears"
        "Ceuta": "Ceuta",
        "Melilla": "Melilla",
    }
    for ccaa, expected_fragment in test_cases.items():
        result = await calculate_isd(
            amount=100_000,
            operation_type="sucesion",
            relationship="grupo_ii",
            ccaa=ccaa,
        )
        assert result["success"] is True
        normativa = result["normativa_aplicable"]
        assert expected_fragment in normativa, (
            f"Normativa for {ccaa} does not contain '{expected_fragment}': {normativa}"
        )
