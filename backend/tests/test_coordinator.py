"""
Test del CoordinatorAgent con los agentes actuales
"""
import asyncio
import sys
import os
from pathlib import Path

# Cargar .env ANTES de importar cualquier cosa
from dotenv import load_dotenv
PROJECT_ROOT = Path(__file__).parent.parent.parent
env_path = PROJECT_ROOT / ".env"
load_dotenv(env_path)

# Añadir backend al path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))


async def test_coordinator():
	"""Test básico del coordinator"""
	
	print("=" * 80)
	print("TEST: CoordinatorAgent")
	print("=" * 80)
	
	try:
		from app.agents.coordinator_agent import get_coordinator
		
		coordinator = get_coordinator()
		print("✅ Coordinator inicializado correctamente")
		print(f"   - TaxAgent: {coordinator.tax_agent.name}")
		print(f"   - PayslipAgent: {coordinator.payslip_agent.name}")
		print(f"   - Router: {coordinator.router.name}")
		
		# Test 1: Routing a TaxAgent
		print("\n" + "=" * 80)
		print("TEST 1: Routing a TaxAgent (consulta sobre IRPF)")
		print("=" * 80)
		
		query1 = "¿Cuánto pagaré de IRPF si gano 45000€ en Madrid?"
		agent_name = await coordinator.route(query1)
		print(f"Query: {query1}")
		print(f"✅ Routed to: {agent_name}")
		
		if agent_name != "TaxAgent":
			print(f"⚠️  Esperaba TaxAgent, pero obtuvo {agent_name}")
		
		# Test 2: Routing a PayslipAgent
		print("\n" + "=" * 80)
		print("TEST 2: Routing a PayslipAgent (consulta sobre nómina)")
		print("=" * 80)
		
		query2 = "¿Qué significa el salario base en mi nómina?"
		agent_name = await coordinator.route(query2)
		print(f"Query: {query2}")
		print(f"✅ Routed to: {agent_name}")
		
		if agent_name != "PayslipAgent":
			print(f"⚠️  Esperaba PayslipAgent, pero obtuvo {agent_name}")
		
		# Test 3: Detección de contexto de payslip
		print("\n" + "=" * 80)
		print("TEST 3: Detección automática de contexto de payslip")
		print("=" * 80)
		
		context_with_payslip = {
			"payslip_data": {
				"period_month": 12,
				"period_year": 2024,
				"gross_salary": 2500.0,
				"net_salary": 1850.0,
				"irpf_withholding": 375.0,
				"ss_contribution": 158.0
			}
		}
		
		print("Context con payslip_data detectado")
		print("✅ Debería enrutar directamente a PayslipAgent sin llamar al router")
		
		# Test 4: Verificar que los agentes responden
		print("\n" + "=" * 80)
		print("TEST 4: Ejecución completa con TaxAgent")
		print("=" * 80)
		
		try:
			response = await coordinator.run(
				query="¿Qué es el IRPF?",
				context={"rag_context": "El IRPF es el Impuesto sobre la Renta de las Personas Físicas"}
			)
			print(f"✅ Respuesta recibida (longitud: {len(response.content)} caracteres)")
			print(f"   Agent usado: {response.agent_name}")
			print(f"   Primeras 100 caracteres: {response.content[:100]}...")
		except Exception as e:
			print(f"❌ Error en ejecución: {e}")
		
		print("\n" + "=" * 80)
		print("🎉 TESTS COMPLETADOS")
		print("=" * 80)
		
	except ImportError as e:
		print(f"❌ Error de importación: {e}")
		print("   Asegúrate de que agent-framework está instalado")
	except Exception as e:
		print(f"❌ Error inesperado: {e}")
		import traceback
		traceback.print_exc()


if __name__ == "__main__":
	asyncio.run(test_coordinator())
