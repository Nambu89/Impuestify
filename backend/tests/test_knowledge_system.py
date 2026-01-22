"""
Test script for autonomous quota tool and RAG system.
"""
import asyncio
import os
import sys
from pathlib import Path

backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from dotenv import load_dotenv
load_dotenv(backend_dir.parent / ".env")

from app.agents.tax_agent import TaxAgent

async def test_system():
    """Test the autonomous quota tool and RAG."""
    
    print("=" * 60)
    print("TaxIA - Sistema de Pruebas")
    print("=" * 60)
    
    # Instantiate TaxAgent
    agent = TaxAgent()
    
    # Test 1: Cuota de autónomos con tool
    print("\n📊 TEST 1: Cuota de Autónomos 2025")
    print("-" * 60)
    question1 = "¿Cuánto pago de autónomos si gano 1500€ netos al mes en 2025?"
    print(f"Pregunta: {question1}\n")
    
    result1 = await agent.run(question1, use_tools=True)
    print(f"Respuesta:\n{result1.content}\n")
    
    # Test 2: Bonificación Ceuta
    print("\n🎁 TEST 2: Bonificación Ceuta")
    print("-" * 60)
    question2 = "Soy autónomo en Ceuta con ingresos de 2000€ mensuales. ¿Qué cuota pago?"
    print(f"Pregunta: {question2}\n")
    
    result2 = await agent.run(question2, use_tools=True)
    print(f"Respuesta:\n{result2.content}\n")
    
    # Test 3: IPSI (RAG)
    print("\n📦 TEST 3: IPSI - Venta a Península")
    print("-" * 60)
    question3 = "Vendo productos desde Melilla a Madrid. ¿Qué impuesto aplico en la factura?"
    print(f"Pregunta: {question3}\n")
    
    result3 = await agent.run(question3, use_tools=True)
    print(f"Respuesta:\n{result3.content}\n")
    
    print("=" * 60)
    print("✅ Tests completados")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(test_system())
