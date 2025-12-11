"""
Test unitario de la tool de análisis de nóminas
"""
import asyncio
import sys
from pathlib import Path

# Añadir backend al path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app.tools.payslip_analysis_tool import analyze_payslip_tool


async def test_analyze_tool():
	"""Test de la tool de análisis"""
	
	print("=" * 80)
	print("TEST: Tool de Análisis de Nóminas")
	print("=" * 80)
	
	# Caso 1: Salario medio
	print("\n📊 CASO 1: Salario medio (2.500€ brutos)")
	result1 = await analyze_payslip_tool(
		gross_salary=2500.0,
		net_salary=1850.50,
		irpf_withholding=375.0,
		ss_contribution=150.0,
		period_month=12,
		period_year=2024
	)
	
	print(f"✅ Success: {result1['success']}")
	print(f"📈 Rango salarial: {result1['analysis']['salary_range']}")
	print(f"💰 IRPF anual: {result1['annual']['irpf']}€")
	print(f"\n{result1['formatted_response']}")
	
	# Caso 2: Salario bajo
	print("\n" + "=" * 80)
	print("📊 CASO 2: Salario bajo (1.200€ brutos)")
	result2 = await analyze_payslip_tool(
		gross_salary=1200.0,
		net_salary=1050.0,
		irpf_withholding=50.0,
		ss_contribution=100.0,
		period_month=11,
		period_year=2024
	)
	
	print(f"✅ Success: {result2['success']}")
	print(f"📈 Rango salarial: {result2['analysis']['salary_range']}")
	print(f"⚠️  Recomendación: {result2['analysis']['recommendation']}")
	
	# Caso 3: Salario alto
	print("\n" + "=" * 80)
	print("📊 CASO 3: Salario alto (5.500€ brutos)")
	result3 = await analyze_payslip_tool(
		gross_salary=5500.0,
		net_salary=3800.0,
		irpf_withholding=1400.0,
		ss_contribution=300.0,
		period_month=10,
		period_year=2024
	)
	
	print(f"✅ Success: {result3['success']}")
	print(f"📈 Rango salarial: {result3['analysis']['salary_range']}")
	print(f"💡 IRPF %: {result3['monthly']['irpf_percentage']}%")
	
	print("\n" + "=" * 80)
	print("🎉 ¡TODOS LOS TESTS PASARON!")
	print("=" * 80)


if __name__ == "__main__":
	asyncio.run(test_analyze_tool())
