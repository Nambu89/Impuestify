"""
CLI script to run the CompetitorAnalysisAgent interactively.

Usage:
    cd backend
    python scripts/competitor_analysis.py

    # Or with a direct query:
    python scripts/competitor_analysis.py "Compara Impuestify con TaxDown"
"""
import sys
import os
import asyncio

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))

from app.agents.competitor_analysis_agent import CompetitorAnalysisAgent


EXAMPLE_QUERIES = [
    "Compara Impuestify con TaxDown en todas las categorías",
    "¿Qué huecos tenemos respecto a la competencia?",
    "¿Qué ventajas únicas tiene Impuestify?",
    "Dame sugerencias de mejora para IA y tecnología",
    "Analiza nuestra posición de mercado (DAFO completo)",
    "¿Cómo funciona la integración con AEAT y cómo conseguir el estatus de Colaborador Social?",
    "Compara precios: Impuestify vs Declarando vs Taxfix",
    "Dame un roadmap de producto para competir con TaxDown",
    "¿Qué hace TaxDown mejor que nosotros?",
    "Estrategia go-to-market para 2026",
]


async def run_query(agent: CompetitorAnalysisAgent, query: str):
    """Run a single query and print the response."""
    print(f"\n{'='*80}")
    print(f"QUERY: {query}")
    print(f"{'='*80}\n")

    response = await agent.run(query=query)

    print(response.content)
    print(f"\n{'─'*40}")
    print(f"Agent: {response.agent_name}")
    print(f"Tools used: {response.metadata.get('tools_used', False)}")
    print(f"Tool rounds: {response.metadata.get('tool_rounds', 0)}")
    print(f"{'─'*40}\n")

    return response


async def interactive_mode(agent: CompetitorAnalysisAgent):
    """Run in interactive mode."""
    print("\n" + "="*60)
    print("  IMPUESTIFY - Competitor Analysis Agent")
    print("  Agente de Análisis Competitivo")
    print("="*60)
    print("\nEjemplos de consultas:")
    for i, q in enumerate(EXAMPLE_QUERIES, 1):
        print(f"  {i}. {q}")
    print(f"\nEscribe 'salir' o 'exit' para terminar.")
    print(f"Escribe un número (1-{len(EXAMPLE_QUERIES)}) para usar un ejemplo.\n")

    conversation_history = []

    while True:
        try:
            user_input = input("Tu pregunta > ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nHasta luego.")
            break

        if not user_input:
            continue

        if user_input.lower() in ("salir", "exit", "quit", "q"):
            print("Hasta luego.")
            break

        # Check if user typed a number for example query
        if user_input.isdigit():
            idx = int(user_input) - 1
            if 0 <= idx < len(EXAMPLE_QUERIES):
                user_input = EXAMPLE_QUERIES[idx]
                print(f"  → {user_input}")

        response = await agent.run(
            query=user_input,
            conversation_history=conversation_history,
        )

        print(f"\n{response.content}\n")

        # Maintain conversation history
        conversation_history.append({"role": "user", "content": user_input})
        conversation_history.append({"role": "assistant", "content": response.content})

        # Keep last 10 exchanges
        if len(conversation_history) > 20:
            conversation_history = conversation_history[-20:]


async def main():
    agent = CompetitorAnalysisAgent()

    if len(sys.argv) > 1:
        # Direct query mode
        query = " ".join(sys.argv[1:])
        await run_query(agent, query)
    else:
        # Interactive mode
        await interactive_mode(agent)


if __name__ == "__main__":
    asyncio.run(main())
