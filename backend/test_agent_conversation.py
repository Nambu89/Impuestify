"""
Test script para probar el agente completo con conversación real.
Simula queries de usuario para detectar posibles fallos.
"""
import asyncio
import sys
from pathlib import Path
from dotenv import load_dotenv

# Setup
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

# Load env
load_dotenv()

from app.agents.tax_agent import get_tax_agent


async def test_conversation(query: str, test_name: str):
    """Test a single conversation query"""
    print("\n" + "="*70)
    print(f"TEST: {test_name}")
    print("="*70)
    print(f"Query: {query}")
    print("-"*70)
    
    try:
        agent = get_tax_agent()
        
        # Run agent with the query
        response = await agent.run(
            query=query,
            context=None,
            sources=None,
            use_tools=True
        )
        
        print("\n📝 RESPUESTA:")
        print(response.content)
        
        # Check if tool was used
        if response.metadata.get('tool_used'):
            print("\n✅ Tool usado correctamente")
        else:
            print("\n⚠️  No se usó ninguna tool")
        
        return True
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all conversation tests"""
    print("\n" + "="*70)
    print("🧪 TESTING AGENTE COMPLETO CON CONVERSACIONES REALES")
    print("="*70)
    
    tests = [
        # Test 1: Query simple con datos en BD (debería funcionar)
        (
            "Gano 60000€ al año en Madrid en 12 pagas, ¿cuánto pagaré de IRPF?",
            "Query simple - Madrid 2024 (BD local)"
        ),
        
        # Test 2: Query con nombre común de CCAA (test normalización)
        (
            "Si cobro 35000€ brutos al año en valencia, ¿cuánto pago de IRPF?",
            "Normalización CCAA - valencia → Comunitat Valenciana"
        ),
        
        # Test 3: Query con año futuro (debería hacer fallback)
        (
            "Estimación de IRPF para 2025 con 50000€ en Cataluña",
            "Año futuro - Cataluña 2025 (fallback a 2024)"
        ),
        
        # Test 4: Query ambigua (debería preguntar al usuario)
        (
            "¿Cuánto pagaré de IRPF?",
            "Query ambigua - falta información"
        ),
        
        # Test 5: Query con CCAA no normalizada
        (
            "IRPF en la comunidad de madrid con 40000€",
            "Variación de nombre - 'comunidad de madrid'"
        ),
    ]
    
    results = []
    
    for query, test_name in tests:
        success = await test_conversation(query, test_name)
        results.append((test_name, success))
        
        # Pausa entre tests
        await asyncio.sleep(2)
    
    # Summary
    print("\n" + "="*70)
    print("📊 RESUMEN DE TESTS")
    print("="*70)
    
    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    total = len(results)
    passed = sum(1 for _, p in results if p)
    
    print(f"\nTotal: {passed}/{total} tests pasados")
    
    if passed == total:
        print("\n🎉 ¡Todos los tests pasaron!")
        return 0
    elif passed >= total * 0.8:
        print("\n✅ La mayoría de tests pasaron")
        return 0
    else:
        print("\n⚠️  Varios tests fallaron")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
