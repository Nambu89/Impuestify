"""
Query Contextualizer for TaxIA

For follow-up queries classified as "modification", extracts key terms
from the last exchange (numbers, CCAA, fiscal concepts) and combines
them with the current query to produce a better RAG search query.

Heuristic-only, no LLM calls.
"""
import re
from typing import List, Dict

# Patterns to extract from conversation history
_NUMBER_PATTERN = re.compile(r"\b(\d[\d.,]*)\s*(€|euros?|EUR)?\b")
_CCAA_PATTERN = re.compile(
    r"\b(madrid|cataluña|cataluna|andalucía|andalucia|valencia|valenciana|"
    r"aragón|aragon|navarra|bizkaia|gipuzkoa|araba|álava|alava|"
    r"ceuta|melilla|galicia|asturias|cantabria|murcia|extremadura|"
    r"castilla[- ]la mancha|castilla[- ]león|castilla[- ]leon|"
    r"baleares|canarias|rioja|país vasco|pais vasco|euskadi)\b",
    re.IGNORECASE
)
_FISCAL_CONCEPT_PATTERN = re.compile(
    r"\b(irpf|iva|renta|nómina|nomina|autónomo|autonomo|"
    r"deducción|deduccion|deducciones|hipoteca|alquiler|"
    r"modelo\s*\d{3}|cuota|retención|retencion|"
    r"base\s*imponible|rendimiento|actividad\s*económica|actividad\s*economica|"
    r"ingresos|gastos|vivienda\s*habitual|"
    r"plan\s*de\s*pensiones|seguridad\s*social|cuenta\s*ahorro)\b",
    re.IGNORECASE
)


def contextualize_query(
    query: str,
    conversation_history: List[Dict[str, str]],
    last_rag_query: str = "",
) -> str:
    """
    Expand a follow-up query with context from the last exchange.

    Args:
        query: Current user query (e.g., "y esos 6000€?")
        conversation_history: Recent messages [{"role":..., "content":...}]
        last_rag_query: The query used for the last RAG search (if available)

    Returns:
        Expanded query string for RAG search
    """
    # Collect context terms from last 2-4 messages
    context_terms = set()
    recent = conversation_history[-4:] if len(conversation_history) >= 4 else conversation_history

    for msg in recent:
        content = msg.get("content", "")

        # Extract CCAA mentions
        for match in _CCAA_PATTERN.finditer(content):
            context_terms.add(match.group(0).strip())

        # Extract fiscal concepts
        for match in _FISCAL_CONCEPT_PATTERN.finditer(content):
            context_terms.add(match.group(0).strip().lower())

    # Extract numbers from current query (user is asking about specific amounts)
    current_numbers = [m.group(0).strip() for m in _NUMBER_PATTERN.finditer(query)]

    # Extract numbers from history for context (if not already in query)
    if not current_numbers:
        for msg in recent:
            content = msg.get("content", "")
            for match in _NUMBER_PATTERN.finditer(content):
                num_str = match.group(0).strip()
                # Only keep significant numbers (> 100, likely financial)
                try:
                    num_val = float(match.group(1).replace(".", "").replace(",", "."))
                    if num_val >= 100:
                        context_terms.add(num_str)
                except (ValueError, IndexError):
                    pass

    # If we have the last RAG query, extract its core terms too
    if last_rag_query:
        for match in _FISCAL_CONCEPT_PATTERN.finditer(last_rag_query):
            context_terms.add(match.group(0).strip().lower())

    # Build expanded query: original query + context terms
    # Remove duplicates between query and context
    query_lower = query.lower()
    unique_terms = [t for t in context_terms if t.lower() not in query_lower]

    if unique_terms:
        expanded = f"{query} {' '.join(unique_terms)}"
        return expanded.strip()

    return query
