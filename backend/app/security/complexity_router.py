"""
LLM Complexity Router for TaxIA

Classifies query complexity to dynamically adjust reasoning effort.
Simple questions get fast responses, complex ones get deeper analysis.

Benefits:
- ~40% token reduction for simple questions
- Faster response times for basic queries
- Better reasoning for complex questions
"""
import re
import logging
from typing import Tuple
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class ComplexityLevel(Enum):
    """Query complexity levels."""
    SIMPLE = "simple"
    MODERATE = "moderate"
    COMPLEX = "complex"


class ReasoningEffort(Enum):
    """OpenAI reasoning effort levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass
class ComplexityResult:
    """Result of complexity classification."""
    level: ComplexityLevel
    reasoning_effort: ReasoningEffort
    confidence: float
    matched_pattern: str = ""


class ComplexityClassifier:
    """
    Classify question complexity for reasoning effort adjustment.
    
    Uses regex patterns for fast, deterministic classification
    without requiring an LLM call.
    
    Mapping:
    - SIMPLE → LOW reasoning (fast, fewer tokens)
    - MODERATE → MEDIUM reasoning (balanced)
    - COMPLEX → HIGH reasoning (deep analysis)
    """
    
    # Simple question patterns (direct lookups, definitions)
    SIMPLE_PATTERNS = [
        r"\b(qué es|que es|cuál es|cual es|define|definición)\b",
        r"\b(cuándo|cuando|fecha|plazo|límite|limite)\s+(es|del|de la|para)\b",
        r"\b(quién|quien|qué|que)\s+(debe|tiene que|puede)\b",
        r"^(hola|hi|hello|buenos días|buenas)\b",
        r"\b(modelo\s+\d+)\b",  # "modelo 303", "modelo 130"
        r"\b(cuánto|cuanto)\s+(es|cuesta|vale)\b",
    ]
    
    # Moderate question patterns (explanations, comparisons)
    MODERATE_PATTERNS = [
        r"\b(explica|explicar|explicación|cómo funciona|como funciona)\b",
        r"\b(diferencia|diferencias|comparar|comparación|versus|vs)\b",
        r"\b(pasos|proceso|procedimiento|cómo se hace|como se hace)\b",
        r"\b(ventajas|desventajas|beneficios|inconvenientes)\b",
        r"\b(por qué|porque|razón|motivo)\b",
        r"\b(ejemplo|ejemplos|caso práctico)\b",
    ]
    
    # Complex question patterns (analysis, evaluation, design)
    COMPLEX_PATTERNS = [
        r"\b(analiza|analizar|análisis|evalúa|evaluar|evaluación)\b",
        r"\b(diseña|diseñar|planifica|planificar|estrategia)\b",
        r"\b(optimiza|optimizar|maximiza|maximizar|minimiza|minimizar)\b",
        r"\b(implicaciones|consecuencias|impacto|efectos)\b",
        r"\b(considerando|teniendo en cuenta|dado que|si.*entonces)\b",
        r"\b(mejor opción|recomendación|qué me recomiendas|qué debería)\b",
        r"\b(varios|múltiples|distintos|diferentes).*(escenarios|opciones|casos)\b",
    ]
    
    def __init__(self):
        """Initialize classifier with compiled patterns."""
        self._simple_patterns = [re.compile(p, re.IGNORECASE) for p in self.SIMPLE_PATTERNS]
        self._moderate_patterns = [re.compile(p, re.IGNORECASE) for p in self.MODERATE_PATTERNS]
        self._complex_patterns = [re.compile(p, re.IGNORECASE) for p in self.COMPLEX_PATTERNS]
    
    def classify(self, query: str) -> ComplexityResult:
        """
        Classify query complexity.
        
        Args:
            query: User's question
            
        Returns:
            ComplexityResult with level and reasoning_effort
        """
        query = query.strip()
        
        # Check patterns in order of specificity (complex first)
        for pattern in self._complex_patterns:
            match = pattern.search(query)
            if match:
                logger.debug(f"🧠 COMPLEX query: {query[:50]}...")
                return ComplexityResult(
                    level=ComplexityLevel.COMPLEX,
                    reasoning_effort=ReasoningEffort.HIGH,
                    confidence=0.9,
                    matched_pattern=match.group()
                )
        
        for pattern in self._moderate_patterns:
            match = pattern.search(query)
            if match:
                logger.debug(f"📊 MODERATE query: {query[:50]}...")
                return ComplexityResult(
                    level=ComplexityLevel.MODERATE,
                    reasoning_effort=ReasoningEffort.MEDIUM,
                    confidence=0.8,
                    matched_pattern=match.group()
                )
        
        for pattern in self._simple_patterns:
            match = pattern.search(query)
            if match:
                logger.debug(f"⚡ SIMPLE query: {query[:50]}...")
                return ComplexityResult(
                    level=ComplexityLevel.SIMPLE,
                    reasoning_effort=ReasoningEffort.LOW,
                    confidence=0.85,
                    matched_pattern=match.group()
                )
        
        # Default to moderate if no pattern matches
        # Length-based heuristic as fallback
        if len(query) < 50:
            return ComplexityResult(
                level=ComplexityLevel.SIMPLE,
                reasoning_effort=ReasoningEffort.LOW,
                confidence=0.5
            )
        elif len(query) > 200:
            return ComplexityResult(
                level=ComplexityLevel.COMPLEX,
                reasoning_effort=ReasoningEffort.HIGH,
                confidence=0.5
            )
        else:
            return ComplexityResult(
                level=ComplexityLevel.MODERATE,
                reasoning_effort=ReasoningEffort.MEDIUM,
                confidence=0.5
            )
    
    def get_reasoning_effort(self, query: str) -> str:
        """
        Convenience method to get reasoning effort string.
        
        Args:
            query: User's question
            
        Returns:
            "low", "medium", or "high"
        """
        result = self.classify(query)
        return result.reasoning_effort.value


# Global instance
complexity_classifier = ComplexityClassifier()


def get_reasoning_effort(query: str) -> str:
    """
    Get reasoning effort for a query.
    
    Args:
        query: User's question
        
    Returns:
        "low", "medium", or "high"
    """
    return complexity_classifier.get_reasoning_effort(query)


def classify_complexity(query: str) -> ComplexityResult:
    """
    Classify query complexity.
    
    Args:
        query: User's question
        
    Returns:
        ComplexityResult with level and reasoning_effort
    """
    return complexity_classifier.classify(query)
