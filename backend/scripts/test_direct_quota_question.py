"""
Test autonomous quota tool with specific question.
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

async def test_direct_question():
    """Test with direct question about quota."""
    
    print("=" * 60)
    print("Test: Pregunta directa sobre cuota")
    print("=" * 60)
    
    agent = TaxAgent()
    
    # Test with the exact user question
    question = "Ingreso menos de 670€ como autónomo, ¿cuánto tengo que pagar?"
    print(f"\nPregunta: {question}\n")
    
    result = await agent.run(question, use_tools=True)
    print(f"Respuesta:\n{result.content}\n")
    
    # Check if tool was called
    if result.metadata and 'tool_calls' in result.metadata:
        print(f"\n✅ Tool invocado: {result.metadata['tool_calls']}")
    else:
        print("\n❌ Tool NO invocado")
    
    print("=" * 60)

asyncio.run(test_direct_question())
