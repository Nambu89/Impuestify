"""
Tests for Plusvalia Municipal (IIVTNU) Calculator.

Covers:
- Metodo objetivo (coeficientes RDL 26/2021, actualizados 2024)
- Metodo real (plusvalia efectiva)
- Comparacion ambos metodos (elige menor)
- Exenciones (divorcio, dacion en pago)
- Edge cases (tenencia 0, 20+, valor catastral suelo = 0)
- STC 182/2021 (no plusvalia → no se paga)
"""
import pytest
import asyncio
from app.utils.calculators.plusvalia_municipal import (
    PlusvaliaMunicipalCalculator,
    COEFICIENTES_MAXIMOS,
)


@pytest.fixture
def calculator():
    return PlusvaliaMunicipalCalculator()


# ---------------------------------------------------------------------------
# 1. Metodo objetivo basico (5 anos tenencia, tipo 30%)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_metodo_objetivo_basico(calculator):
    """5 anos de tenencia, coeficiente 0.20, tipo 30%."""
    result = await calculator.calculate(
        precio_venta=300_000,
        precio_adquisicion=200_000,
        valor_catastral_total=150_000,
        valor_catastral_suelo=60_000,
        anos_tenencia=5,
        tipo_impositivo_municipal=30.0,
    )
    assert result["success"] is True
    assert result["exento"] is False

    obj = result["metodo_objetivo"]
    assert obj["coeficiente"] == 0.20
    assert obj["base_imponible"] == 60_000 * 0.20  # 12,000
    assert obj["cuota"] == 12_000 * 0.30  # 3,600


# ---------------------------------------------------------------------------
# 2. Metodo real basico (ganancia positiva)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_metodo_real_basico(calculator):
    """Ganancia positiva, porcentaje suelo 40%."""
    result = await calculator.calculate(
        precio_venta=300_000,
        precio_adquisicion=200_000,
        valor_catastral_total=150_000,
        valor_catastral_suelo=60_000,  # 40% suelo
        anos_tenencia=5,
        tipo_impositivo_municipal=30.0,
    )
    assert result["success"] is True

    real = result["metodo_real"]
    # Plusvalia total = 300k - 200k = 100k
    assert real["plusvalia_total"] == 100_000
    # Porcentaje suelo = 60k / 150k = 0.4
    assert real["porcentaje_suelo"] == 0.4
    # Base = 100k * 0.4 = 40k
    assert real["base_imponible"] == 40_000
    # Cuota = 40k * 0.30 = 12k
    assert real["cuota"] == 12_000
    assert real["hay_plusvalia"] is True


# ---------------------------------------------------------------------------
# 3. Metodo real sin plusvalia (perdida → exento STC 182/2021)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_metodo_real_sin_plusvalia(calculator):
    """Venta con perdida → exento por STC 182/2021."""
    result = await calculator.calculate(
        precio_venta=180_000,
        precio_adquisicion=250_000,
        valor_catastral_total=150_000,
        valor_catastral_suelo=60_000,
        anos_tenencia=10,
        tipo_impositivo_municipal=30.0,
    )
    assert result["success"] is True
    assert result["exento"] is True
    assert result["cuota_final"] == 0.0
    assert "STC 182/2021" in result["motivo_exencion"]


# ---------------------------------------------------------------------------
# 4. Comparacion ambos metodos → elige menor
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_elige_metodo_menor(calculator):
    """El calculador debe elegir el metodo con cuota mas baja."""
    # Setup: objetivo deberia dar menos que real
    # Catastral suelo = 30k, 2 anos tenencia, coef 0.14
    # Objetivo: 30k * 0.14 * 0.30 = 1,260
    # Real: (250k - 200k) * (30k/100k) * 0.30 = 50k * 0.30 * 0.30 = 4,500
    result = await calculator.calculate(
        precio_venta=250_000,
        precio_adquisicion=200_000,
        valor_catastral_total=100_000,
        valor_catastral_suelo=30_000,
        anos_tenencia=2,
        tipo_impositivo_municipal=30.0,
    )
    assert result["success"] is True
    assert result["metodo_elegido"] == "objetivo"
    assert result["cuota_final"] == 30_000 * 0.14 * 0.30  # 1,260

    # Reverse: real should be lower
    # Catastral suelo alto = 80k, 15 anos, coef 0.45
    # Objetivo: 80k * 0.45 * 0.30 = 10,800
    # Real: (210k - 200k) * (80k/100k) * 0.30 = 10k * 0.80 * 0.30 = 2,400
    result2 = await calculator.calculate(
        precio_venta=210_000,
        precio_adquisicion=200_000,
        valor_catastral_total=100_000,
        valor_catastral_suelo=80_000,
        anos_tenencia=15,
        tipo_impositivo_municipal=30.0,
    )
    assert result2["success"] is True
    assert result2["metodo_elegido"] == "real"
    assert result2["cuota_final"] == 10_000 * 0.80 * 0.30  # 2,400


# ---------------------------------------------------------------------------
# 5. Tenencia < 1 ano
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_tenencia_menos_1_ano(calculator):
    """Tenencia 0 anos (menos de 1 ano), coeficiente 0.15."""
    result = await calculator.calculate(
        precio_venta=300_000,
        precio_adquisicion=250_000,
        valor_catastral_total=100_000,
        valor_catastral_suelo=40_000,
        anos_tenencia=0,
        tipo_impositivo_municipal=30.0,
    )
    assert result["success"] is True
    obj = result["metodo_objetivo"]
    assert obj["coeficiente"] == 0.15
    assert obj["base_imponible"] == 40_000 * 0.15  # 6,000


# ---------------------------------------------------------------------------
# 6. Tenencia 20+ anos (coeficiente maximo)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_tenencia_20_plus(calculator):
    """Tenencia >= 20 anos, coeficiente 0.60."""
    result = await calculator.calculate(
        precio_venta=500_000,
        precio_adquisicion=100_000,
        valor_catastral_total=200_000,
        valor_catastral_suelo=80_000,
        anos_tenencia=25,
        tipo_impositivo_municipal=30.0,
    )
    assert result["success"] is True
    obj = result["metodo_objetivo"]
    assert obj["coeficiente"] == 0.60
    assert obj["base_imponible"] == 80_000 * 0.60  # 48,000

    # Also test exactly 20
    result20 = await calculator.calculate(
        precio_venta=500_000,
        precio_adquisicion=100_000,
        valor_catastral_total=200_000,
        valor_catastral_suelo=80_000,
        anos_tenencia=20,
        tipo_impositivo_municipal=30.0,
    )
    assert result20["metodo_objetivo"]["coeficiente"] == 0.60


# ---------------------------------------------------------------------------
# 7. Tipo municipal diferente a 30% (ej: Madrid 29%)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_tipo_municipal_madrid_29(calculator):
    """Madrid aplica 29% en lugar del maximo 30%."""
    result = await calculator.calculate(
        precio_venta=400_000,
        precio_adquisicion=300_000,
        valor_catastral_total=200_000,
        valor_catastral_suelo=80_000,
        anos_tenencia=10,
        tipo_impositivo_municipal=29.0,
    )
    assert result["success"] is True
    obj = result["metodo_objetivo"]
    assert obj["tipo_impositivo"] == 29.0
    # Coef 10 anos = 0.22
    expected_base = 80_000 * 0.22  # 17,600
    expected_cuota = expected_base * 0.29  # 5,104
    assert obj["base_imponible"] == expected_base
    assert obj["cuota"] == expected_cuota


# ---------------------------------------------------------------------------
# 8. Exencion por dacion en pago
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_exencion_dacion_pago(calculator):
    """Dacion en pago de vivienda habitual → exento."""
    result = await calculator.calculate(
        precio_venta=200_000,
        precio_adquisicion=300_000,
        valor_catastral_total=150_000,
        valor_catastral_suelo=60_000,
        anos_tenencia=8,
        es_vivienda_habitual_dacion=True,
    )
    assert result["success"] is True
    assert result["exento"] is True
    assert result["cuota_final"] == 0.0
    assert "dacion" in result["motivo_exencion"].lower()


# ---------------------------------------------------------------------------
# 9. Exencion por divorcio
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_exencion_divorcio(calculator):
    """Transmision entre conyuges por divorcio → exento."""
    result = await calculator.calculate(
        precio_venta=350_000,
        precio_adquisicion=200_000,
        valor_catastral_total=180_000,
        valor_catastral_suelo=72_000,
        anos_tenencia=12,
        es_divorcio=True,
    )
    assert result["success"] is True
    assert result["exento"] is True
    assert result["cuota_final"] == 0.0
    assert "divorcio" in result["motivo_exencion"].lower() or "matrimonial" in result["motivo_exencion"].lower()


# ---------------------------------------------------------------------------
# 10. Edge: valor catastral suelo = 0
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_valor_catastral_suelo_cero(calculator):
    """Valor catastral suelo 0 → base 0 en ambos metodos."""
    result = await calculator.calculate(
        precio_venta=300_000,
        precio_adquisicion=200_000,
        valor_catastral_total=150_000,
        valor_catastral_suelo=0,
        anos_tenencia=5,
        tipo_impositivo_municipal=30.0,
    )
    assert result["success"] is True
    obj = result["metodo_objetivo"]
    assert obj["base_imponible"] == 0.0
    assert obj["cuota"] == 0.0


# ---------------------------------------------------------------------------
# 11. Edge: anos tenencia = 0
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_anos_tenencia_cero(calculator):
    """0 anos de tenencia (compra-venta inmediata), coef 0.15."""
    result = await calculator.calculate(
        precio_venta=200_000,
        precio_adquisicion=180_000,
        valor_catastral_total=100_000,
        valor_catastral_suelo=40_000,
        anos_tenencia=0,
        tipo_impositivo_municipal=30.0,
    )
    assert result["success"] is True
    assert result["metodo_objetivo"]["coeficiente"] == 0.15
    assert result["metodo_objetivo"]["anos_tenencia"] == 0


# ---------------------------------------------------------------------------
# 12. Todos los coeficientes maximos del RDL 26/2021 (2024)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_coeficientes_tabla_completa(calculator):
    """Verifica que todos los coeficientes maximos son correctos."""
    expected = {
        0: 0.15, 1: 0.15, 2: 0.14, 3: 0.15, 4: 0.17,
        5: 0.20, 6: 0.20, 7: 0.20, 8: 0.22, 9: 0.22,
        10: 0.22, 11: 0.22, 12: 0.23, 13: 0.26, 14: 0.36,
        15: 0.45, 16: 0.52, 17: 0.60, 18: 0.60, 19: 0.60,
        20: 0.60,
    }
    for anos, coef in expected.items():
        assert COEFICIENTES_MAXIMOS[anos] == coef, (
            f"Coeficiente para {anos} anos: esperado {coef}, "
            f"obtenido {COEFICIENTES_MAXIMOS[anos]}"
        )


# ---------------------------------------------------------------------------
# 13. Tipo impositivo clamped al maximo legal
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_tipo_impositivo_clamped(calculator):
    """Si se pasa tipo > 30%, se clampea a 30%."""
    result = await calculator.calculate(
        precio_venta=300_000,
        precio_adquisicion=200_000,
        valor_catastral_total=150_000,
        valor_catastral_suelo=60_000,
        anos_tenencia=5,
        tipo_impositivo_municipal=35.0,  # > 30% legal
    )
    assert result["success"] is True
    assert result["metodo_objetivo"]["tipo_impositivo"] == 30.0


# ---------------------------------------------------------------------------
# 14. Validacion: tipo impositivo <= 0
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_tipo_impositivo_cero(calculator):
    """Tipo impositivo 0 o negativo → error."""
    result = await calculator.calculate(
        precio_venta=300_000,
        precio_adquisicion=200_000,
        valor_catastral_total=150_000,
        valor_catastral_suelo=60_000,
        anos_tenencia=5,
        tipo_impositivo_municipal=0.0,
    )
    assert result["success"] is False
    assert "positivo" in result["error"].lower()


# ---------------------------------------------------------------------------
# 15. Formatted response presente
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_formatted_response(calculator):
    """Verifica que formatted_response esta presente y contiene datos clave."""
    result = await calculator.calculate(
        precio_venta=300_000,
        precio_adquisicion=200_000,
        valor_catastral_total=150_000,
        valor_catastral_suelo=60_000,
        anos_tenencia=5,
        tipo_impositivo_municipal=30.0,
    )
    assert "formatted_response" in result
    resp = result["formatted_response"]
    assert "Metodo objetivo" in resp or "objetivo" in resp.lower()
    assert "Metodo real" in resp or "real" in resp.lower()
    assert "EUR" in resp


# ---------------------------------------------------------------------------
# 16. Validacion: valores catastrales negativos
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_valores_catastrales_negativos(calculator):
    """Valores catastrales negativos → error."""
    result = await calculator.calculate(
        precio_venta=300_000,
        precio_adquisicion=200_000,
        valor_catastral_total=-100,
        valor_catastral_suelo=60_000,
        anos_tenencia=5,
    )
    assert result["success"] is False


# ---------------------------------------------------------------------------
# 17. Valor catastral total = 0 (edge case para metodo real)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_valor_catastral_total_cero(calculator):
    """Valor catastral total 0 → metodo real devuelve 0 sin division por cero."""
    result = await calculator.calculate(
        precio_venta=300_000,
        precio_adquisicion=200_000,
        valor_catastral_total=0,
        valor_catastral_suelo=0,
        anos_tenencia=5,
        tipo_impositivo_municipal=30.0,
    )
    assert result["success"] is True
    real = result["metodo_real"]
    assert real["cuota"] == 0.0
