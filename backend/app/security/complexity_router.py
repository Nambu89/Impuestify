"""
LLM Complexity Router for TaxIA

Classifies query complexity to dynamically adjust reasoning effort.
Simple questions get fast responses, complex ones get deeper analysis.

Benefits:
- ~40% token reduction for simple questions
- Faster response times for basic queries
- Better reasoning for complex questions
"""
import logging
from typing import Tuple, Optional
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
    model: str = "gpt-5-mini"  # Default to cheaper model
    reasoning: str = ""       # Explanation for the choice


class ComplexityClassifier:
    """
    Classify question complexity for reasoning effort adjustment.
    
    Uses Groq (llama-3.1-8b-instant) to analyze intent.
    
    Mapping:
    - SIMPLE -> gpt-5-mini
    - COMPLEX -> gpt-5
    """
    
    def __init__(self):
        """
        Initialize the complexity classifier with Groq client.
        """
        from groq import Groq
        from app.config import settings
        
        self.client = None
        if settings.GROQ_API_KEY:
            try:
                self.client = Groq(api_key=settings.GROQ_API_KEY)
                logger.info(f"✅ Complexity Router initialized with Groq model: {settings.GROQ_MODEL_ROUTER}")
            except Exception as e:
                logger.error(f"❌ Failed to initialize Groq client for Router: {e}")
        else:
            logger.warning("⚠️ GROQ_API_KEY not found. Complexity Router will fail.")

    def classify(self, query: str) -> ComplexityResult:
        """
        Classify query complexity using Groq LLM.
        
        Args:
            query: User query text
            
        Returns:
            ComplexityResult with level, reasoning, and selected model
        """
        if not self.client:
            return ComplexityResult(
                level=ComplexityLevel.MODERATE,
                reasoning_effort=ReasoningEffort.MEDIUM,
                confidence=0.0,
                model="gpt-5-mini",
                reasoning="Router disabled (no API key)"
            )

        try:
            from app.config import settings
            
            system_prompt = """You are an intelligent router for a Tax AI assistant.
Analyze the user query and determine its complexity.

Rules:
1. **COMPLEX** -> Use 'gpt-5'.
   - Detailed tax analysis, multi-step reasoning, ambiguous scenarios, legal interpretation.
   - Keywords: "Liquidación", "Inspección", "Recurso", "Sanción compleja", "Planificación fiscal".
   
2. **SIMPLE/MODERATE** -> Use 'gpt-5-mini'.
   - Definitions, simple calculations, lookup facts, greeting, general info.
   - Keywords: "Calendario", "Plazo", "Qué es", "Cuota autónomo simple".

Output JSON ONLY:
{
  "level": "SIMPLE" | "MODERATE" | "COMPLEX",
  "reasoning_effort": "low" | "medium" | "high",
  "model": "gpt-5-mini" | "gpt-5",
  "explanation": "Brief reason"
}"""

            completion = self.client.chat.completions.create(
                model=settings.GROQ_MODEL_ROUTER,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": query}
                ],
                temperature=0.1,
                response_format={"type": "json_object"}
            )
            
            import json
            response_data = json.loads(completion.choices[0].message.content)
            
            # Map string to Enum
            level_str = response_data.get("level", "MODERATE").lower()
            effort_str = response_data.get("reasoning_effort", "medium").lower()
            
            # Safe Enum conversion
            level = next((m for m in ComplexityLevel if m.value == level_str), ComplexityLevel.MODERATE)
            effort = next((m for m in ReasoningEffort if m.value == effort_str), ReasoningEffort.MEDIUM)
            
            return ComplexityResult(
                level=level,
                reasoning_effort=effort,
                confidence=0.95,
                model=response_data.get("model", "gpt-5-mini"),
                reasoning=response_data.get("explanation", "AI Classification")
            )

        except Exception as e:
            logger.error(f"❌ Groq Router Error: {e}")
            # Fallback to safe default
            return ComplexityResult(
                level=ComplexityLevel.COMPLEX,
                reasoning_effort=ReasoningEffort.HIGH,
                confidence=0.0,
                model="gpt-5", # Fail safe to best model
                reasoning=f"Error: {str(e)}"
            )

    def get_reasoning_effort(self, query: str) -> str:
        """Helper to get just the reasoning effort string"""
        result = self.classify(query)
        return result.reasoning_effort.value


# Global instance
complexity_classifier = ComplexityClassifier()


def get_reasoning_effort(query: str) -> str:
    """Helper to get full result"""
    return complexity_classifier.get_reasoning_effort(query)


def classify_complexity(query: str) -> ComplexityResult:
    """Helper to get full result"""
    return complexity_classifier.classify(query)