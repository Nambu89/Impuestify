"""
Test suite for Modelo 303 (IVA) and Modelo 130 (Pago Fraccionado IRPF) tools.

Verifica que las herramientas calculan correctamente las casillas principales.
"""
import asyncio
import sys
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))


# ============================================================
# MODELO 303 TESTS
# ============================================================

async def test_303_basic_21():
    """Test 1: Calculo basico solo 21%"""
    print("\n" + "=" * 60)
    print("TEST 303-1: Calculo basico solo 21%")
    print("=" * 60)

    from app.tools.modelo_303_tool import calculate_modelo_303_tool

    result = await calculate_modelo_303_tool(
        trimestre=1,
        year=2025,
        base_21=10000,
        iva_deducible_bienes_corrientes=500
    )

    assert result["success"], f"Expected success, got: {result}"
    assert result["iva_devengado"]["cuota_21"] == 2100.0, f"Expected 2100, got {result['iva_devengado']['cuota_21']}"
    assert result["iva_devengado"]["total_devengado"] == 2100.0
    assert result["iva_deducible"]["total_deducible"] == 500.0
    assert result["resultado"]["resultado_final"] == 1600.0
    assert result["resultado"]["tipo"] == "A ingresar"

    print(f"  Devengado 21%: {result['iva_devengado']['cuota_21']} EUR")
    print(f"  Total devengado: {result['iva_devengado']['total_devengado']} EUR")
    print(f"  Total deducible: {result['iva_deducible']['total_deducible']} EUR")
    print(f"  Resultado: {result['resultado']['resultado_final']} EUR ({result['resultado']['tipo']})")
    print("  PASS")
    return True


async def test_303_mixed_rates():
    """Test 2: Tipos mixtos (21% + 10% + 4%)"""
    print("\n" + "=" * 60)
    print("TEST 303-2: Tipos mixtos (21% + 10% + 4%)")
    print("=" * 60)

    from app.tools.modelo_303_tool import calculate_modelo_303_tool

    result = await calculate_modelo_303_tool(
        trimestre=2,
        year=2025,
        base_21=5000,
        base_10=3000,
        base_4=2000,
        iva_deducible_bienes_corrientes=800
    )

    assert result["success"]
    assert result["iva_devengado"]["cuota_21"] == 1050.0   # 5000 * 0.21
    assert result["iva_devengado"]["cuota_10"] == 300.0     # 3000 * 0.10
    assert result["iva_devengado"]["cuota_4"] == 80.0       # 2000 * 0.04
    total_devengado = 1050.0 + 300.0 + 80.0
    assert result["iva_devengado"]["total_devengado"] == total_devengado
    assert result["resultado"]["resultado_final"] == total_devengado - 800.0

    print(f"  Cuota 21%: {result['iva_devengado']['cuota_21']} EUR")
    print(f"  Cuota 10%: {result['iva_devengado']['cuota_10']} EUR")
    print(f"  Cuota 4%: {result['iva_devengado']['cuota_4']} EUR")
    print(f"  Total devengado: {result['iva_devengado']['total_devengado']} EUR")
    print(f"  Resultado: {result['resultado']['resultado_final']} EUR")
    print("  PASS")
    return True


async def test_303_negative_t1_t3_compensar():
    """Test 3: Resultado negativo T1-T3 → A compensar"""
    print("\n" + "=" * 60)
    print("TEST 303-3: Resultado negativo T1-T3 -> A compensar")
    print("=" * 60)

    from app.tools.modelo_303_tool import calculate_modelo_303_tool

    result = await calculate_modelo_303_tool(
        trimestre=2,
        year=2025,
        base_21=1000,
        iva_deducible_bienes_corrientes=500,
        iva_deducible_bienes_inversion=200
    )

    assert result["success"]
    # Devengado = 1000 * 0.21 = 210
    # Deducible = 500 + 200 = 700
    # Resultado = 210 - 700 = -490
    assert result["resultado"]["resultado_final"] == -490.0
    assert result["resultado"]["tipo"] == "A compensar"

    print(f"  Resultado: {result['resultado']['resultado_final']} EUR ({result['resultado']['tipo']})")
    print("  PASS")
    return True


async def test_303_negative_t4_devolver():
    """Test 4: Resultado negativo T4 → A devolver"""
    print("\n" + "=" * 60)
    print("TEST 303-4: Resultado negativo T4 -> A devolver")
    print("=" * 60)

    from app.tools.modelo_303_tool import calculate_modelo_303_tool

    result = await calculate_modelo_303_tool(
        trimestre=4,
        year=2025,
        base_21=1000,
        iva_deducible_bienes_corrientes=500,
        iva_deducible_bienes_inversion=200
    )

    assert result["success"]
    assert result["resultado"]["resultado_final"] == -490.0
    assert result["resultado"]["tipo"] == "A devolver"

    print(f"  Resultado: {result['resultado']['resultado_final']} EUR ({result['resultado']['tipo']})")
    print("  PASS")
    return True


async def test_303_compensacion_anterior():
    """Test 5: Con compensacion de periodos anteriores"""
    print("\n" + "=" * 60)
    print("TEST 303-5: Compensacion de periodos anteriores")
    print("=" * 60)

    from app.tools.modelo_303_tool import calculate_modelo_303_tool

    result = await calculate_modelo_303_tool(
        trimestre=2,
        year=2025,
        base_21=10000,
        iva_deducible_bienes_corrientes=500,
        compensacion_periodos_anteriores=300
    )

    assert result["success"]
    # Devengado = 2100, Deducible = 500, Regimen general = 1600
    # Final = 1600 - 300 = 1300
    assert result["resultado"]["regimen_general"] == 1600.0
    assert result["resultado"]["compensacion_anterior"] == 300.0
    assert result["resultado"]["resultado_final"] == 1300.0

    print(f"  Regimen general: {result['resultado']['regimen_general']} EUR")
    print(f"  Compensacion: {result['resultado']['compensacion_anterior']} EUR")
    print(f"  Resultado final: {result['resultado']['resultado_final']} EUR")
    print("  PASS")
    return True


async def test_303_intracomunitarias():
    """Test 6: Adquisiciones intracomunitarias"""
    print("\n" + "=" * 60)
    print("TEST 303-6: Adquisiciones intracomunitarias")
    print("=" * 60)

    from app.tools.modelo_303_tool import calculate_modelo_303_tool

    result = await calculate_modelo_303_tool(
        trimestre=1,
        year=2025,
        base_21=5000,
        base_adquisiciones_intra=2000,
        tipo_adquisiciones_intra=21,
        iva_deducible_bienes_corrientes=300,
        iva_deducible_intracomunitarias=420
    )

    assert result["success"]
    # Devengado: 5000*0.21 + 2000*0.21 = 1050 + 420 = 1470
    # Deducible: 300 + 420 = 720
    # Resultado: 1470 - 720 = 750
    assert result["iva_devengado"]["cuota_intracomunitaria"] == 420.0
    assert result["iva_devengado"]["total_devengado"] == 1470.0
    assert result["resultado"]["resultado_final"] == 750.0

    print(f"  Cuota intracomunitaria: {result['iva_devengado']['cuota_intracomunitaria']} EUR")
    print(f"  Total devengado: {result['iva_devengado']['total_devengado']} EUR")
    print(f"  Resultado: {result['resultado']['resultado_final']} EUR")
    print("  PASS")
    return True


async def test_303_zero_activity():
    """Test 7: Actividad cero (todo 0)"""
    print("\n" + "=" * 60)
    print("TEST 303-7: Actividad cero")
    print("=" * 60)

    from app.tools.modelo_303_tool import calculate_modelo_303_tool

    result = await calculate_modelo_303_tool(
        trimestre=1,
        year=2025,
        base_21=0,
        iva_deducible_bienes_corrientes=0
    )

    assert result["success"]
    assert result["iva_devengado"]["total_devengado"] == 0.0
    assert result["iva_deducible"]["total_deducible"] == 0.0
    assert result["resultado"]["resultado_final"] == 0.0
    assert result["resultado"]["tipo"] == "Sin actividad"

    print(f"  Resultado: {result['resultado']['resultado_final']} EUR ({result['resultado']['tipo']})")
    print("  PASS")
    return True


async def test_303_restricted_mode():
    """Test 8: restricted_mode=True → retorna bloqueo"""
    print("\n" + "=" * 60)
    print("TEST 303-8: Restricted mode")
    print("=" * 60)

    from app.tools.modelo_303_tool import calculate_modelo_303_tool

    result = await calculate_modelo_303_tool(
        trimestre=1,
        year=2025,
        base_21=10000,
        iva_deducible_bienes_corrientes=500,
        restricted_mode=True
    )

    assert not result["success"]
    assert result["error"] == "restricted"
    assert "autónomos" in result["formatted_response"].lower() or "cuenta ajena" in result["formatted_response"].lower()

    print(f"  Blocked as expected: error={result['error']}")
    print("  PASS")
    return True


# ============================================================
# MODELO 130 TESTS
# ============================================================

async def test_130_basic():
    """Test 1: Calculo basico"""
    print("\n" + "=" * 60)
    print("TEST 130-1: Calculo basico")
    print("=" * 60)

    from app.tools.modelo_130_tool import calculate_modelo_130_tool

    result = await calculate_modelo_130_tool(
        trimestre=1,
        year=2025,
        ingresos_computables=15000,
        gastos_deducibles=5000
    )

    assert result["success"], f"Expected success, got: {result}"
    # Neto = 15000 - 5000 = 10000
    # 20% = 2000
    # Resultado = 2000 (no retenciones ni pagos anteriores)
    assert result["seccion_i"]["rendimiento_neto"] == 10000.0
    assert result["seccion_i"]["veinte_porciento"] == 2000.0
    assert result["resultado_final"] == 2000.0

    print(f"  Rendimiento neto: {result['seccion_i']['rendimiento_neto']} EUR")
    print(f"  20%: {result['seccion_i']['veinte_porciento']} EUR")
    print(f"  Resultado: {result['resultado_final']} EUR")
    print("  PASS")
    return True


async def test_130_with_retenciones_and_pagos():
    """Test 2: Con retenciones y pagos anteriores"""
    print("\n" + "=" * 60)
    print("TEST 130-2: Con retenciones y pagos anteriores")
    print("=" * 60)

    from app.tools.modelo_130_tool import calculate_modelo_130_tool

    result = await calculate_modelo_130_tool(
        trimestre=2,
        year=2025,
        ingresos_computables=30000,
        gastos_deducibles=10000,
        retenciones_ingresos_cuenta=1500,
        pagos_fraccionados_anteriores=800
    )

    assert result["success"]
    # Neto = 30000 - 10000 = 20000
    # 20% = 4000
    # Resultado seccion I = 4000 - 1500 - 800 = 1700
    assert result["seccion_i"]["rendimiento_neto"] == 20000.0
    assert result["seccion_i"]["veinte_porciento"] == 4000.0
    assert result["seccion_i"]["resultado_seccion"] == 1700.0
    assert result["resultado_final"] == 1700.0

    print(f"  20% neto: {result['seccion_i']['veinte_porciento']} EUR")
    print(f"  Retenciones: {result['seccion_i']['retenciones']} EUR")
    print(f"  Pagos anteriores: {result['seccion_i']['pagos_anteriores']} EUR")
    print(f"  Resultado: {result['resultado_final']} EUR")
    print("  PASS")
    return True


async def test_130_t2_accumulated():
    """Test 3: T2 acumulado con pagos anteriores T1"""
    print("\n" + "=" * 60)
    print("TEST 130-3: T2 acumulado con pagos T1 anteriores")
    print("=" * 60)

    from app.tools.modelo_130_tool import calculate_modelo_130_tool

    # T1: ingresos 10000, gastos 3000, neto 7000, 20% = 1400, resultado = 1400
    # T2 acumulado: ingresos 22000, gastos 7000, neto 15000, 20% = 3000
    # Pagos anteriores (T1) = 1400
    # Resultado T2 = 3000 - 1400 = 1600
    result = await calculate_modelo_130_tool(
        trimestre=2,
        year=2025,
        ingresos_computables=22000,
        gastos_deducibles=7000,
        pagos_fraccionados_anteriores=1400
    )

    assert result["success"]
    assert result["seccion_i"]["rendimiento_neto"] == 15000.0
    assert result["seccion_i"]["veinte_porciento"] == 3000.0
    assert result["resultado_final"] == 1600.0

    print(f"  Neto acumulado: {result['seccion_i']['rendimiento_neto']} EUR")
    print(f"  20% acumulado: {result['seccion_i']['veinte_porciento']} EUR")
    print(f"  Pagos T1: {result['seccion_i']['pagos_anteriores']} EUR")
    print(f"  Resultado T2: {result['resultado_final']} EUR")
    print("  PASS")
    return True


async def test_130_deduccion_80bis_low():
    """Test 4: Deduccion art. 80 bis (renta <= 9000)"""
    print("\n" + "=" * 60)
    print("TEST 130-4: Deduccion 80 bis (renta <= 9000)")
    print("=" * 60)

    from app.tools.modelo_130_tool import calculate_modelo_130_tool

    result = await calculate_modelo_130_tool(
        trimestre=1,
        year=2025,
        ingresos_computables=5000,
        gastos_deducibles=1000,
        rendimiento_neto_previo_anual=8000  # <= 9000 → 100 EUR deduccion
    )

    assert result["success"]
    # Neto = 4000, 20% = 800
    # Deduccion 80 bis = 100 EUR (renta anterior <= 9000)
    # Resultado = max(800 - 100, 0) = 700
    assert result["deduccion_80bis"] == 100.0
    assert result["resultado_final"] == 700.0

    print(f"  Deduccion 80 bis: {result['deduccion_80bis']} EUR")
    print(f"  Resultado: {result['resultado_final']} EUR")
    print("  PASS")
    return True


async def test_130_deduccion_80bis_graduated():
    """Test 5: Deduccion art. 80 bis (renta entre 9000-12000, graduada)"""
    print("\n" + "=" * 60)
    print("TEST 130-5: Deduccion 80 bis graduada (9000-12000)")
    print("=" * 60)

    from app.tools.modelo_130_tool import calculate_modelo_130_tool

    # Test with 9500 EUR previous year income
    # Bracket: 9000-10000 → 100 - (9500-9000)*0.075 = 100 - 37.5 = 62.5
    result = await calculate_modelo_130_tool(
        trimestre=1,
        year=2025,
        ingresos_computables=5000,
        gastos_deducibles=1000,
        rendimiento_neto_previo_anual=9500
    )

    assert result["success"]
    assert result["deduccion_80bis"] == 62.5
    # Neto = 4000, 20% = 800, resultado = 800 - 62.5 = 737.5
    assert result["resultado_final"] == 737.5

    print(f"  Renta anterior: 9500 EUR")
    print(f"  Deduccion 80 bis: {result['deduccion_80bis']} EUR")
    print(f"  Resultado: {result['resultado_final']} EUR")

    # Test with 11500 EUR → bracket 11000-12000
    # 12.5 - (11500-11000)*0.0125 = 12.5 - 6.25 = 6.25
    result2 = await calculate_modelo_130_tool(
        trimestre=1,
        year=2025,
        ingresos_computables=5000,
        gastos_deducibles=1000,
        rendimiento_neto_previo_anual=11500
    )

    assert result2["success"]
    assert result2["deduccion_80bis"] == 6.25

    print(f"  Renta anterior: 11500 EUR → deduccion: {result2['deduccion_80bis']} EUR")
    print("  PASS")
    return True


async def test_130_no_deduccion_80bis():
    """Test 6: Sin deduccion art. 80 bis (renta > 12000)"""
    print("\n" + "=" * 60)
    print("TEST 130-6: Sin deduccion 80 bis (renta > 12000)")
    print("=" * 60)

    from app.tools.modelo_130_tool import calculate_modelo_130_tool

    result = await calculate_modelo_130_tool(
        trimestre=1,
        year=2025,
        ingresos_computables=15000,
        gastos_deducibles=5000,
        rendimiento_neto_previo_anual=25000  # > 12000 → sin deduccion
    )

    assert result["success"]
    assert result["deduccion_80bis"] == 0.0
    # Neto = 10000, 20% = 2000, sin deduccion → resultado = 2000
    assert result["resultado_final"] == 2000.0

    print(f"  Renta anterior: 25000 EUR → deduccion: 0 EUR")
    print(f"  Resultado: {result['resultado_final']} EUR")
    print("  PASS")
    return True


async def test_130_negative_net():
    """Test 7: Rendimiento neto negativo → resultado 0"""
    print("\n" + "=" * 60)
    print("TEST 130-7: Rendimiento neto negativo")
    print("=" * 60)

    from app.tools.modelo_130_tool import calculate_modelo_130_tool

    result = await calculate_modelo_130_tool(
        trimestre=1,
        year=2025,
        ingresos_computables=3000,
        gastos_deducibles=5000  # Gastos > Ingresos
    )

    assert result["success"]
    # Neto = max(3000 - 5000, 0) = 0
    assert result["seccion_i"]["rendimiento_neto"] == 0.0
    assert result["resultado_final"] == 0.0

    print(f"  Ingresos: 3000, Gastos: 5000")
    print(f"  Rendimiento neto: {result['seccion_i']['rendimiento_neto']} EUR (floor 0)")
    print(f"  Resultado: {result['resultado_final']} EUR")
    print("  PASS")
    return True


async def test_130_restricted_mode():
    """Test 8: restricted_mode=True → retorna bloqueo"""
    print("\n" + "=" * 60)
    print("TEST 130-8: Restricted mode")
    print("=" * 60)

    from app.tools.modelo_130_tool import calculate_modelo_130_tool

    result = await calculate_modelo_130_tool(
        trimestre=1,
        year=2025,
        ingresos_computables=15000,
        gastos_deducibles=5000,
        restricted_mode=True
    )

    assert not result["success"]
    assert result["error"] == "restricted"
    assert "autónomos" in result["formatted_response"].lower() or "cuenta ajena" in result["formatted_response"].lower()

    print(f"  Blocked as expected: error={result['error']}")
    print("  PASS")
    return True


# ============================================================
# REGISTRATION TEST
# ============================================================

async def test_tools_registration():
    """Verifica que ambas herramientas estan registradas"""
    print("\n" + "=" * 60)
    print("TEST REG: Registro de herramientas")
    print("=" * 60)

    from app.tools import ALL_TOOLS, TOOL_EXECUTORS

    registered_names = [t["function"]["name"] for t in ALL_TOOLS]

    assert "calculate_modelo_303" in registered_names, "calculate_modelo_303 not in ALL_TOOLS"
    assert "calculate_modelo_130" in registered_names, "calculate_modelo_130 not in ALL_TOOLS"
    assert "calculate_modelo_303" in TOOL_EXECUTORS, "calculate_modelo_303 not in TOOL_EXECUTORS"
    assert "calculate_modelo_130" in TOOL_EXECUTORS, "calculate_modelo_130 not in TOOL_EXECUTORS"

    print(f"  Total tools: {len(ALL_TOOLS)}")
    print(f"  Total executors: {len(TOOL_EXECUTORS)}")
    print(f"  303 registered: YES")
    print(f"  130 registered: YES")
    print("  PASS")
    return True


# ============================================================
# MAIN
# ============================================================

async def main():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("  TESTS: Modelo 303 (IVA) + Modelo 130 (Pago Fraccionado)")
    print("=" * 60)

    results = []

    # Registration
    results.append(("REG: Registro", await test_tools_registration()))

    # Modelo 303 tests
    results.append(("303-1: Basico 21%", await test_303_basic_21()))
    results.append(("303-2: Tipos mixtos", await test_303_mixed_rates()))
    results.append(("303-3: Negativo T1-T3 compensar", await test_303_negative_t1_t3_compensar()))
    results.append(("303-4: Negativo T4 devolver", await test_303_negative_t4_devolver()))
    results.append(("303-5: Compensacion anterior", await test_303_compensacion_anterior()))
    results.append(("303-6: Intracomunitarias", await test_303_intracomunitarias()))
    results.append(("303-7: Actividad cero", await test_303_zero_activity()))
    results.append(("303-8: Restricted mode", await test_303_restricted_mode()))

    # Modelo 130 tests
    results.append(("130-1: Basico", await test_130_basic()))
    results.append(("130-2: Retenciones y pagos", await test_130_with_retenciones_and_pagos()))
    results.append(("130-3: T2 acumulado", await test_130_t2_accumulated()))
    results.append(("130-4: 80bis <= 9000", await test_130_deduccion_80bis_low()))
    results.append(("130-5: 80bis graduada", await test_130_deduccion_80bis_graduated()))
    results.append(("130-6: Sin 80bis > 12000", await test_130_no_deduccion_80bis()))
    results.append(("130-7: Neto negativo", await test_130_negative_net()))
    results.append(("130-8: Restricted mode", await test_130_restricted_mode()))

    # Summary
    print("\n" + "=" * 60)
    print("  RESUMEN")
    print("=" * 60)

    passed = 0
    failed = 0
    for name, ok in results:
        status = "PASS" if ok else "FAIL"
        print(f"  {status}: {name}")
        if ok:
            passed += 1
        else:
            failed += 1

    print(f"\n  Total: {passed}/{len(results)} passed")

    if failed == 0:
        print("\n  Todos los tests pasaron correctamente!")
        return 0
    else:
        print(f"\n  {failed} tests fallaron")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
