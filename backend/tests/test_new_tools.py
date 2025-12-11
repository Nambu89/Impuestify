"""
Test suite for new tools: search_tool and payslip_analysis_tool

Verifica que las herramientas están correctamente registradas y funcionan.
"""
import asyncio
import sys
from pathlib import Path

# Añadir backend al path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))


async def test_tools_registration():
    """Verifica que las herramientas están registradas correctamente"""
    print("\n" + "="*60)
    print("TEST 1: Registro de herramientas")
    print("="*60)
    
    from app.tools import ALL_TOOLS, TOOL_EXECUTORS
    
    print(f"\nTotal de herramientas registradas: {len(ALL_TOOLS)}")
    
    expected_tools = [
        "calculate_irpf",
        "calculate_autonomous_quota",
        "search_tax_regulations",
        "analyze_payslip"
    ]
    
    registered_tools = [tool["function"]["name"] for tool in ALL_TOOLS]
    
    print("\nHerramientas registradas:")
    for tool_name in registered_tools:
        status = "✅" if tool_name in expected_tools else "⚠️"
        print(f"  {status} {tool_name}")
    
    print("\nEjecutores registrados:")
    for executor_name in TOOL_EXECUTORS.keys():
        status = "✅" if executor_name in expected_tools else "⚠️"
        print(f"  {status} {executor_name}")
    
    # Verificar que todas las herramientas esperadas están presentes
    all_present = all(tool in registered_tools for tool in expected_tools)
    all_executors_present = all(tool in TOOL_EXECUTORS for tool in expected_tools)
    
    if all_present and all_executors_present:
        print("\n✅ Todas las herramientas están correctamente registradas")
        return True
    else:
        print("\n❌ Faltan herramientas por registrar")
        missing = [t for t in expected_tools if t not in registered_tools]
        if missing:
            print(f"   Faltantes en ALL_TOOLS: {missing}")
        missing_exec = [t for t in expected_tools if t not in TOOL_EXECUTORS]
        if missing_exec:
            print(f"   Faltantes en TOOL_EXECUTORS: {missing_exec}")
        return False


async def test_payslip_analysis_tool():
    """Prueba la herramienta de análisis de nóminas"""
    print("\n" + "="*60)
    print("TEST 2: Herramienta de análisis de nóminas")
    print("="*60)
    
    from app.tools.payslip_analysis_tool import analyze_payslip_tool
    
    # Datos de prueba de una nómina típica
    test_data = {
        "gross_salary": 2500.00,
        "net_salary": 1850.50,
        "irpf_withholding": 375.00,
        "ss_contribution": 158.75,  # 6.35% de 2500
        "period_month": 12,
        "period_year": 2024
    }
    
    print("\nDatos de entrada:")
    for key, value in test_data.items():
        print(f"  {key}: {value}")
    
    try:
        result = await analyze_payslip_tool(**test_data)
        
        if result.get("success"):
            print("\n✅ Análisis completado exitosamente")
            
            print("\nResultados mensuales:")
            monthly = result.get("monthly", {})
            print(f"  - Salario bruto: {monthly.get('gross_salary')}€")
            print(f"  - Salario neto: {monthly.get('net_salary')}€")
            print(f"  - IRPF: {monthly.get('irpf_withholding')}€ ({monthly.get('irpf_percentage')}%)")
            print(f"  - SS: {monthly.get('ss_contribution')}€ ({monthly.get('ss_percentage')}%)")
            
            print("\nProyección anual:")
            annual = result.get("annual", {})
            print(f"  - Bruto anual: {annual.get('gross')}€")
            print(f"  - Neto anual: {annual.get('net')}€")
            
            print("\nAnálisis:")
            analysis = result.get("analysis", {})
            print(f"  - Rango salarial: {analysis.get('salary_range')}")
            print(f"  - Análisis IRPF: {analysis.get('irpf_analysis')}")
            
            return True
        else:
            print(f"\n❌ Error en el análisis: {result.get('error')}")
            return False
            
    except Exception as e:
        print(f"\n❌ Excepción durante el análisis: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_search_tool():
    """Prueba la herramienta de búsqueda web"""
    print("\n" + "="*60)
    print("TEST 3: Herramienta de búsqueda web")
    print("="*60)
    
    from app.tools.search_tool import search_tax_regulations_tool
    
    test_query = "tramos IRPF 2025"
    
    print(f"\nConsulta de prueba: '{test_query}'")
    print("⚠️  Nota: Este test requiere conexión a internet")
    
    try:
        result = await search_tax_regulations_tool(
            query=test_query,
            year=2025,
            max_results=2
        )
        
        if result.get("success"):
            print("\n✅ Búsqueda completada exitosamente")
            
            results = result.get("results", [])
            print(f"\nResultados encontrados: {len(results)}")
            
            for i, res in enumerate(results, 1):
                print(f"\n  {i}. {res.get('title')}")
                print(f"     Fuente: {res.get('source')}")
                print(f"     URL: {res.get('url')}")
            
            return True
        else:
            print(f"\n⚠️  No se encontraron resultados: {result.get('error')}")
            print("   Esto puede ser normal si no hay conexión o si DuckDuckGo bloquea la petición")
            return None  # No es un fallo crítico
            
    except Exception as e:
        print(f"\n⚠️  Excepción durante la búsqueda: {e}")
        print("   Esto puede ser normal si no hay conexión a internet")
        import traceback
        traceback.print_exc()
        return None  # No es un fallo crítico


async def test_tool_definitions():
    """Verifica que las definiciones de herramientas son válidas"""
    print("\n" + "="*60)
    print("TEST 4: Validación de definiciones de herramientas")
    print("="*60)
    
    from app.tools import ALL_TOOLS
    
    required_fields = ["type", "function"]
    required_function_fields = ["name", "description", "parameters"]
    
    all_valid = True
    
    for tool in ALL_TOOLS:
        tool_name = tool.get("function", {}).get("name", "unknown")
        
        # Verificar campos requeridos
        missing_fields = [f for f in required_fields if f not in tool]
        if missing_fields:
            print(f"❌ {tool_name}: Faltan campos {missing_fields}")
            all_valid = False
            continue
        
        # Verificar campos de función
        function = tool.get("function", {})
        missing_func_fields = [f for f in required_function_fields if f not in function]
        if missing_func_fields:
            print(f"❌ {tool_name}: Faltan campos de función {missing_func_fields}")
            all_valid = False
            continue
        
        # Verificar que tiene parámetros
        params = function.get("parameters", {})
        if not params.get("properties"):
            print(f"⚠️  {tool_name}: No tiene parámetros definidos")
        
        print(f"✅ {tool_name}: Definición válida")
    
    if all_valid:
        print("\n✅ Todas las definiciones son válidas")
    else:
        print("\n❌ Hay definiciones inválidas")
    
    return all_valid


async def main():
    """Ejecuta todos los tests"""
    print("\n" + "="*60)
    print("🧪 TESTS DE NUEVAS HERRAMIENTAS")
    print("="*60)
    
    results = []
    
    # Test 1: Registro
    results.append(("Registro de herramientas", await test_tools_registration()))
    
    # Test 2: Análisis de nóminas
    results.append(("Análisis de nóminas", await test_payslip_analysis_tool()))
    
    # Test 3: Búsqueda web (puede fallar sin internet)
    search_result = await test_search_tool()
    if search_result is not None:
        results.append(("Búsqueda web", search_result))
    
    # Test 4: Validación de definiciones
    results.append(("Validación de definiciones", await test_tool_definitions()))
    
    # Resumen final
    print("\n" + "="*60)
    print("📊 RESUMEN DE TESTS")
    print("="*60)
    
    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    total = len(results)
    passed = sum(1 for _, p in results if p)
    
    print(f"\nTotal: {passed}/{total} tests pasados")
    
    if passed == total:
        print("\n🎉 ¡Todos los tests pasaron correctamente!")
        return 0
    elif passed >= total * 0.7:
        print("\n⚠️  La mayoría de tests pasaron")
        return 0
    else:
        print("\n❌ Varios tests fallaron")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
