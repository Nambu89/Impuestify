"""
Follow-up Detector for TaxIA

Heuristic-based classifier that determines if a user query is:
- "clarification": user asks to explain/clarify previous answer → SKIP RAG
- "modification": user modifies parameters (income, CCAA, etc.) → RAG with expanded query
- "new_topic": unrelated new question → normal RAG

Zero latency (no API calls), pure pattern matching.
"""
import re
from typing import List, Dict, Literal

FollowUpType = Literal["clarification", "modification", "new_topic"]

# Clarification signals: user wants the same info explained differently
_CLARIFICATION_PATTERNS = [
    r"^(explica|explícame|explicame|aclara|aclárame)",
    r"^(no entiendo|no lo entiendo|no me queda claro)",
    r"^(qué quiere decir|que quiere decir|qué significa|que significa)",
    r"^(puedes repetir|repite|repíteme)",
    r"^(a qué te refieres|a que te refieres)",
    r"^(cómo es eso|como es eso|en qué sentido|en que sentido)",
    r"^(más detalle|mas detalle|detalla|amplía|amplia)",
    r"^(por qué|por que|y por qué|y por que)\??$",
    r"^(y eso)\??$",
    r"^(resume|resúmeme|resumeme)",
]

# Connectors that suggest continuation of previous topic
_CONTINUATION_CONNECTORS = [
    "y si ", "y los ", "y las ", "y el ", "y la ", "y esos ", "y esas ",
    "y ese ", "y esa ", "entonces ", "pero ", "aunque ", "sin embargo ",
    "en ese caso ", "en mi caso ", "y en ", "y con ",
]

# Pronouns that reference previous context
_REFERENCE_PRONOUNS = re.compile(
    r"\b(eso|esos|esas|ese|esa|esto|estos|estas|este|esta|lo mismo|lo anterior|lo de antes)\b",
    re.IGNORECASE
)

# Fiscal keywords that suggest a substantive (non-clarification) query
_FISCAL_KEYWORDS = re.compile(
    r"\b(irpf|iva|isrl|renta|nómina|nomina|autónomo|autonomo|deducción|deduccion|"
    r"hacienda|aeat|modelo\s*\d{3}|hipoteca|alquiler|donación|donacion|"
    r"minusvalía|minusvalia|discapacidad|maternidad|paternidad|"
    r"inversión|inversion|plan\s*de\s*pensiones|seguridad\s*social|"
    r"comunidad|ccaa|madrid|cataluña|cataluna|andalucía|andalucia|"
    r"valencia|aragón|aragon|navarra|bizkaia|gipuzkoa|araba|"
    r"ceuta|melilla|galicia|asturias|cantabria|murcia|extremadura|"
    r"castilla|baleares|canarias|rioja)\b",
    re.IGNORECASE
)

# Modification signals: numbers, currencies, or CCAA changes
_MODIFICATION_PATTERNS = re.compile(
    r"(\d[\d.,]*\s*€|\d[\d.,]*\s*euros?|\d{4,}|\bcambio\b|\bcambi[oa]\b|\bsi\s+cobr[oa]\b|\bsi\s+gan[oa]\b|\bsi\s+viv[oa]\b)",
    re.IGNORECASE
)


def classify_followup(
    query: str,
    conversation_history: List[Dict[str, str]],
) -> FollowUpType:
    """
    Classify a user query as clarification, modification, or new_topic.

    Args:
        query: Current user message
        conversation_history: List of {"role": ..., "content": ...} dicts

    Returns:
        "clarification" | "modification" | "new_topic"
    """
    # No history → always new topic
    if not conversation_history or len(conversation_history) < 2:
        return "new_topic"

    q = query.strip().lower()

    # Very short queries with reference pronouns → likely clarification
    if len(q) < 40 and _REFERENCE_PRONOUNS.search(q):
        # But if it also has modification patterns (numbers), it's a modification
        if _MODIFICATION_PATTERNS.search(q):
            return "modification"
        return "clarification"

    # Explicit clarification patterns
    for pattern in _CLARIFICATION_PATTERNS:
        if re.search(pattern, q, re.IGNORECASE):
            return "clarification"

    # Continuation connectors → check if modification or clarification
    for connector in _CONTINUATION_CONNECTORS:
        if q.startswith(connector):
            if _MODIFICATION_PATTERNS.search(q):
                return "modification"
            # Short continuation without fiscal keywords → clarification
            if len(q) < 60 and not _FISCAL_KEYWORDS.search(q):
                return "clarification"
            return "modification"

    # Short query (< 30 chars) without fiscal keywords → likely clarification
    if len(q) < 30 and not _FISCAL_KEYWORDS.search(q) and not _MODIFICATION_PATTERNS.search(q):
        # Only if it doesn't look like a standalone question
        if "?" in q or not any(q.startswith(w) for w in ["cuánto", "cuanto", "cómo", "como", "dónde", "donde", "qué", "que", "cuál", "cual"]):
            return "clarification"

    # Long query with multiple fiscal keywords → new topic
    if len(q) > 80 and len(_FISCAL_KEYWORDS.findall(q)) >= 2:
        return "new_topic"

    # Default: new topic (safest — runs full RAG)
    return "new_topic"
