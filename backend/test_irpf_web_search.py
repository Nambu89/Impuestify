"""
Test script for IRPF calculator with web search fallback.

Tests the complete flow:
1. BD local (should work for 2024)
2. Web search + extraction (for 2025)
3. Previous year fallback
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

from app.tools.irpf_calculator_tool import calculate_irpf_tool


async def test_local_db():
    """Test 1: Should work with local DB (2024 data exists)"""
    print("\n" + "="*60)
    print("TEST 1: BD Local - Madrid 2024")
    print("="*60)
    
    result = await calculate_irpf_tool(
        base_imponible=52690,  # 60k brutos - reducciones
        comunidad_autonoma="Madrid",  # Common name (will be normalized)
        year=2024
    )
    
    if result.get("success"):
        print("✅ SUCCESS")
        print(f"   Cuota total: {result['cuota_total']}€")
        print(f"   Source: {result.get('source')}")
    else:
        print("❌ FAILED")
        print(f"   Error: {result.get('error')}")
    
    return result.get("success")


async def test_web_extraction():
    """Test 2: Should try web extraction (2025 data doesn't exist in DB)"""
    print("\n" + "="*60)
    print("TEST 2: Web Extraction - Madrid 2025")
    print("="*60)
    print("⚠️  This test requires internet connection")
    print("⚠️  May take 10-15 seconds (web scraping + LLM extraction)")
    
    result = await calculate_irpf_tool(
        base_imponible=52690,
        comunidad_autonoma="Madrid",
        year=2025
    )
    
    if result.get("success"):
        print("✅ SUCCESS")
        print(f"   Cuota total: {result['cuota_total']}€")
        print(f"   Source: {result.get('source')}")
        if result.get('source_url'):
            print(f"   URL: {result['source_url']}")
    else:
        print("⚠️  FAILED (expected if web extraction doesn't work)")
        print(f"   Error: {result.get('error')}")
    
    return result.get("success")


async def test_normalization():
    """Test 3: Should normalize CCAA names"""
    print("\n" + "="*60)
    print("TEST 3: CCAA Normalization - 'valencia' → 'Comunitat Valenciana'")
    print("="*60)
    
    result = await calculate_irpf_tool(
        base_imponible=35000,
        comunidad_autonoma="valencia",  # Lowercase, common name
        year=2024
    )
    
    if result.get("success"):
        print("✅ SUCCESS")
        # Extract CCAA name from formatted response
        formatted = result.get('formatted_response', '')
        if 'Comunidad Autónoma**: ' in formatted:
            ccaa_name = formatted.split('Comunidad Autónoma**: ')[1].split('\n')[0]
        else:
            ccaa_name = 'Unknown'
        print(f"   Normalized to: {ccaa_name}")
        print(f"   Cuota total: {result['cuota_total']}€")
    else:
        print("❌ FAILED")
        print(f"   Error: {result.get('error')}")
    
    return result.get("success")


async def test_fallback_to_previous_year():
    """Test 4: Should fallback to previous year if current year not available"""
    print("\n" + "="*60)
    print("TEST 4: Fallback to Previous Year - Aragón 2026")
    print("="*60)
    
    result = await calculate_irpf_tool(
        base_imponible=35000,
        comunidad_autonoma="Aragón",
        year=2026  # Future year, should fallback to 2024 or 2025
    )
    
    if result.get("success"):
        print("✅ SUCCESS (with fallback)")
        print(f"   Year used: {result['year']}")
        print(f"   Cuota total: {result['cuota_total']}€")
        if "⚠️" in result.get('formatted_response', ''):
            print("   ⚠️  Warning about fallback detected")
    else:
        print("❌ FAILED")
        print(f"   Error: {result.get('error')}")
    
    return result.get("success")


async def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("🧪 TESTING IRPF CALCULATOR WITH WEB SEARCH")
    print("="*60)
    
    results = []
    
    # Test 1: Local DB
    results.append(("BD Local (2024)", await test_local_db()))
    
    # Test 2: Web extraction (may fail without internet or if extraction doesn't work)
    results.append(("Web Extraction (2025)", await test_web_extraction()))
    
    # Test 3: Normalization
    results.append(("CCAA Normalization", await test_normalization()))
    
    # Test 4: Fallback
    results.append(("Fallback to Previous Year", await test_fallback_to_previous_year()))
    
    # Summary
    print("\n" + "="*60)
    print("📊 TEST SUMMARY")
    print("="*60)
    
    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    total = len(results)
    passed = sum(1 for _, p in results if p)
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed >= 3:  # At least 3 out of 4 (web extraction may fail)
        print("\n🎉 Implementation working correctly!")
        return 0
    else:
        print("\n⚠️  Some tests failed")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
